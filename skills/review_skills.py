"""
审核技能合集 — 剧本审核、合规检查、对比审核、连续性记录

包含:
  - ScriptReviewSkill: 业务审核（情节逻辑、人物一致、节奏、对白质量）
  - ComplianceReviewSkill: 合规审核（内容安全、平台规范、敏感词）
  - ComparativeReviewSkill: 与参考剧本的质量对比
  - ContinuityRecordSkill: 跨集连续性检查
"""

import os
import re
from collections import Counter, defaultdict
from typing import Optional

# ═══════════════════════════════════════════════════════════════
# 通用审核维度定义
# ═══════════════════════════════════════════════════════════════

REVIEW_DIMENSIONS = {
    "plot_logic": {
        "name": "情节逻辑",
        "weight": 25,
        "description": "事件因果链是否清晰、转折是否合理、是否有逻辑漏洞",
    },
    "character_consistency": {
        "name": "人物一致性",
        "weight": 20,
        "description": "角色行为是否符合其性格设定、前后是否一致",
    },
    "pacing": {
        "name": "节奏把控",
        "weight": 15,
        "description": "场景节奏是否合理、信息密度是否得当、是否有拖沓",
    },
    "dialogue_quality": {
        "name": "对白质量",
        "weight": 15,
        "description": "对白是否自然、有无角色辨识度、潜台词是否到位",
    },
    "visual_potential": {
        "name": "视觉潜力",
        "weight": 10,
        "description": "内容是否适合影视化呈现、视觉元素是否丰富",
    },
    "emotional_impact": {
        "name": "情感冲击",
        "weight": 10,
        "description": "情感节点是否有效、能否引起观众共鸣",
    },
    "hook_quality": {
        "name": "悬念钩子",
        "weight": 5,
        "description": "章末悬念是否有效、能否促使观众继续观看",
    },
}

COMPARISON_DIMENSIONS = [
    {"name": "开场力度", "key": "opening_impact", "weight": 20},
    {"name": "冲突密度", "key": "conflict_density", "weight": 20},
    {"name": "对白犀利度", "key": "dialogue_sharpness", "weight": 15},
    {"name": "节奏感", "key": "pacing", "weight": 15},
    {"name": "钩子质量", "key": "hook_quality", "weight": 15},
    {"name": "角色魅力", "key": "character_appeal", "weight": 15},
]


# ═══════════════════════════════════════════════════════════════
# 1. ScriptReviewSkill — 业务审核
# ═══════════════════════════════════════════════════════════════

class ScriptReviewSkill:
    """剧本业务审核技能"""

    def review(self, elements: list, script_meta: dict = None) -> dict:
        """
        对剧本进行多维度业务审核。

        Returns:
            {overall_score, dimensions: {...}, issues: [...], verdict: PASS/FAIL/REVISE}
        """
        issues = []
        dimension_scores = {}

        # 1. 情节逻辑
        logic_result = self._check_plot_logic(elements)
        dimension_scores["plot_logic"] = logic_result
        issues.extend(logic_result.get("issues", []))

        # 2. 人物一致性
        char_result = self._check_character_consistency(elements)
        dimension_scores["character_consistency"] = char_result
        issues.extend(char_result.get("issues", []))

        # 3. 节奏
        pacing_result = self._check_pacing(elements)
        dimension_scores["pacing"] = pacing_result
        issues.extend(pacing_result.get("issues", []))

        # 4. 对白质量
        dialogue_result = self._check_dialogue_quality(elements)
        dimension_scores["dialogue_quality"] = dialogue_result
        issues.extend(dialogue_result.get("issues", []))

        # 5. 视觉潜力
        visual_result = self._check_visual_potential(elements)
        dimension_scores["visual_potential"] = visual_result

        # 6. 情感冲击
        emotion_result = self._check_emotional_impact(elements)
        dimension_scores["emotional_impact"] = emotion_result

        # 7. 钩子质量
        hook_result = self._check_hook_quality(elements)
        dimension_scores["hook_quality"] = hook_result

        # 计算加权总分
        overall = self._calculate_weighted_score(dimension_scores)

        # 判定
        verdict = self._determine_verdict(overall, issues)

        return {
            "overall_score": round(overall, 1),
            "dimensions": dimension_scores,
            "issues": issues,
            "issue_count": len(issues),
            "verdict": verdict,
            "suggestions": self._compile_suggestions(issues),
        }

    def _check_plot_logic(self, elements: list) -> dict:
        """检查情节逻辑"""
        issues = []
        score = 8.0

        # 检查因果关系完整性
        beat_sequence = [e.get("beat_type", "") for e in elements]
        setup_count = beat_sequence.count("setup")
        payoff_count = beat_sequence.count("payoff")

        if setup_count > payoff_count * 2:
            issues.append({
                "type": "plot_logic",
                "severity": "medium",
                "description": f"铺垫({setup_count})远多于收尾({payoff_count})，可能存在未解决的伏笔",
            })
            score -= 1.5

        if payoff_count == 0 and len(elements) > 20:
            issues.append({
                "type": "plot_logic",
                "severity": "high",
                "description": "没有检测到 payoff 节拍，情节缺乏收束感",
            })
            score -= 2.0

        # 检查 revelation 是否合理分布
        revelation_positions = [
            i for i, b in enumerate(beat_sequence) if b == "revelation"
        ]
        if revelation_positions and len(elements) > 10:
            # 揭示应分布在中后段
            early_revelations = [p for p in revelation_positions
                                if p < len(elements) * 0.2]
            if early_revelations:
                issues.append({
                    "type": "plot_logic",
                    "severity": "medium",
                    "description": "关键揭示出现在剧本开头，可能削弱悬念感",
                })
                score -= 1.0

        return {"score": max(1, round(score, 1)), "issues": issues}

    def _check_character_consistency(self, elements: list) -> dict:
        """检查人物一致性"""
        issues = []
        score = 8.0

        # 按角色统计情绪
        role_emotions = defaultdict(list)
        for e in elements:
            role = e.get("role", "")
            emotion = e.get("emotion", "")
            if role and role != "旁白" and emotion:
                role_emotions[role].append(emotion)

        for role, emotions in role_emotions.items():
            if len(emotions) >= 3:
                unique = len(set(emotions))
                # 如果角色情绪过于单一或过于跳跃
                if unique == 1:
                    issues.append({
                        "type": "character_consistency",
                        "severity": "low",
                        "description": f"角色「{role}」情绪始终为「{emotions[0]}」，缺乏层次",
                    })
                    score -= 0.5
                elif unique > len(emotions) * 0.8:
                    issues.append({
                        "type": "character_consistency",
                        "severity": "medium",
                        "description": f"角色「{role}」情绪切换过于频繁，可能缺乏一致性",
                    })
                    score -= 1.0

        return {"score": max(1, round(score, 1)), "issues": issues}

    def _check_pacing(self, elements: list) -> dict:
        """检查节奏"""
        issues = []
        score = 7.0

        types = [e.get("type", "") for e in elements]
        total = max(len(elements), 1)

        dialogue_ratio = types.count("dialogue") / total
        action_ratio = types.count("action") / total
        narration_ratio = (types.count("narration") + types.count("description")) / total

        if narration_ratio > 0.6:
            issues.append({
                "type": "pacing",
                "severity": "medium",
                "description": f"叙述占比过高({narration_ratio:.0%})，节奏可能偏慢",
            })
            score -= 1.5
        if action_ratio < 0.05 and total > 50:
            issues.append({
                "type": "pacing",
                "severity": "low",
                "description": "动作元素过少，动态感不足",
            })
            score -= 1.0

        # 检查长段连续同类型元素
        consecutive_same = 0
        for i in range(1, len(types)):
            if types[i] == types[i-1] == "narration":
                consecutive_same += 1
        if consecutive_same > total * 0.3:
            issues.append({
                "type": "pacing",
                "severity": "medium",
                "description": "连续叙述段落过长，建议用对白或动作打断",
            })
            score -= 1.0

        return {"score": max(1, round(score, 1)), "issues": issues}

    def _check_dialogue_quality(self, elements: list) -> dict:
        """检查对白质量"""
        issues = []
        score = 7.0

        dialogues = [e for e in elements if e.get("type") == "dialogue"]
        if not dialogues:
            return {"score": 5.0, "issues": [{
                "type": "dialogue_quality",
                "severity": "high",
                "description": "完全没有对白，剧本可能不可用",
            }]}

        # 检查是否有潜台词
        with_subtext = sum(1 for d in dialogues if d.get("subtext"))
        subtext_ratio = with_subtext / max(len(dialogues), 1)

        if subtext_ratio < 0.2:
            issues.append({
                "type": "dialogue_quality",
                "severity": "medium",
                "description": f"仅{subtext_ratio:.0%}的对白有潜台词标注，对白可能过于直白",
            })
            score -= 1.5

        # 检查对白长度
        long_dialogues = [d for d in dialogues if len(d.get("text", "")) > 100]
        if len(long_dialogues) > len(dialogues) * 0.2:
            issues.append({
                "type": "dialogue_quality",
                "severity": "low",
                "description": f"{len(long_dialogues)}句对白超过100字，可能过于冗长",
            })
            score -= 1.0

        # 检查角色辨识度：同一角色对白的情绪多样性
        role_dialogues = defaultdict(list)
        for d in dialogues:
            role = d.get("role", "")
            if role and role != "旁白":
                role_dialogues[role].append(d.get("emotion", ""))

        for role, emotions in role_dialogues.items():
            if len(emotions) >= 3 and len(set(emotions)) == 1:
                issues.append({
                    "type": "dialogue_quality",
                    "severity": "low",
                    "description": f"角色「{role}」的所有对白都是同一情绪，缺乏变化",
                })
                score -= 0.5

        return {"score": max(1, round(score, 1)), "issues": issues}

    def _check_visual_potential(self, elements: list) -> dict:
        """检查视觉潜力"""
        score = 7.0
        with_hints = sum(1 for e in elements if e.get("visual_hint"))
        ratio = with_hints / max(len(elements), 1)
        if ratio > 0.3:
            score = 9.0
        elif ratio > 0.1:
            score = 7.5
        return {"score": score, "visual_hint_coverage": round(ratio * 100, 1)}

    def _check_emotional_impact(self, elements: list) -> dict:
        """检查情感冲击"""
        score = 7.0
        emotions = [e.get("emotion", "") for e in elements if e.get("emotion")]
        if emotions:
            unique_emotions = len(set(emotions))
            if unique_emotions >= 5:
                score = 8.5
            elif unique_emotions >= 3:
                score = 7.5
            else:
                score = 5.0
        return {
            "score": score,
            "emotion_diversity": len(set(emotions)) if emotions else 0,
        }

    def _check_hook_quality(self, elements: list) -> dict:
        """检查悬念钩子质量"""
        score = 6.0
        tail = elements[-15:]
        suspense_kw = ["突然", "忽然", "却", "然而", "但", "不料",
                       "谁知", "没想到", "竟然", "难道"]
        hooks_found = sum(
            1 for e in tail
            for kw in suspense_kw
            if kw in e.get("text", "")
        )
        if hooks_found >= 2:
            score = 8.0
        elif hooks_found == 1:
            score = 7.0
        return {"score": score, "suspense_markers_in_tail": hooks_found}

    def _calculate_weighted_score(self, dimension_scores: dict) -> float:
        """计算加权总分"""
        total_weight = 0
        weighted_sum = 0
        for dim_key, dim_info in REVIEW_DIMENSIONS.items():
            if dim_key in dimension_scores:
                score = dimension_scores[dim_key].get("score", 5)
                weight = dim_info["weight"]
                weighted_sum += score * weight
                total_weight += weight
        return weighted_sum / max(total_weight, 1)

    def _determine_verdict(self, overall: float, issues: list) -> str:
        """判定审核结果"""
        high_issues = sum(1 for i in issues if i.get("severity") == "high")
        if overall >= 8.0 and high_issues == 0:
            return "PASS"
        elif overall >= 6.0 and high_issues <= 2:
            return "REVISE"
        else:
            return "FAIL"

    def _compile_suggestions(self, issues: list) -> list[str]:
        """汇总修改建议"""
        suggestions = []
        for issue in issues:
            suggestions.append(
                f"[{issue.get('severity', '?')}] {issue.get('description', '')}"
            )
        return suggestions


# ═══════════════════════════════════════════════════════════════
# 2. ComplianceReviewSkill — 合规审核
# ═══════════════════════════════════════════════════════════════

class ComplianceReviewSkill:
    """内容合规审核技能"""

    # 敏感词库（示例）
    SENSITIVE_KEYWORDS = {
        "violence_extreme": ["虐杀", "肢解", "斩首", "活埋", "剥皮"],
        "pornography": ["裸体", "淫秽", "色情"],
        "politics_sensitive": [],  # 实际使用时从配置加载
        "drug_abuse": ["吸毒", "嗑药", "毒品", "海洛因", "冰毒"],
        "gambling_detail": ["赌博技巧", "出千方法"],
    }

    # 平台规范（广电总局常见规范）
    PLATFORM_RULES = {
        "time_travel": {
            "pattern": r"(?:穿越|重生|转世)(?!.*正能量)",
            "rule": "穿越/重生题材需有正向价值导向",
        },
        "superstition": {
            "pattern": r"(?:鬼魂|妖怪|神仙|法术|符咒)(?!.*破除迷信)",
            "rule": "涉及灵异元素需有科学解释或正向引导",
        },
        "violence_glorify": {
            "pattern": r"(?:杀人|报仇|血洗|屠)(?!.*正义)",
            "rule": "不得美化暴力行为",
        },
    }

    def check(self, text: str, target_platform: str = "generic") -> dict:
        """
        对文本进行合规检查。

        Returns:
            {passed, issues: [...], risk_level: low/medium/high}
        """
        issues = []

        # 敏感词检查
        for category, keywords in self.SENSITIVE_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    issues.append({
                        "category": category,
                        "keyword": kw,
                        "severity": "high",
                        "description": f"包含敏感词「{kw}」(类别: {category})",
                        "suggestion": "建议删除或修改相关表述",
                    })

        # 平台规范检查
        if target_platform != "generic":
            for rule_name, rule_info in self.PLATFORM_RULES.items():
                if re.search(rule_info["pattern"], text):
                    issues.append({
                        "category": "platform_rule",
                        "rule": rule_name,
                        "severity": "medium",
                        "description": rule_info["rule"],
                        "suggestion": "请根据平台规范调整内容",
                    })

        # 风险评级
        high_count = sum(1 for i in issues if i.get("severity") == "high")
        if high_count > 0:
            risk_level = "high"
        elif issues:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "passed": risk_level != "high",
            "issues": issues,
            "issue_count": len(issues),
            "risk_level": risk_level,
        }


# ═══════════════════════════════════════════════════════════════
# 3. ComparativeReviewSkill — 对比审核
# ═══════════════════════════════════════════════════════════════

class ComparativeReviewSkill:
    """与爆款参考剧本的对比审核"""

    def compare(self, script_elements: list, references: list[dict]) -> dict:
        """
        将当前剧本与参考剧本进行多维度对比。

        Returns:
            {comparisons: [...], overall_gap, strengths, weaknesses}
        """
        # 分析当前剧本
        current_metrics = self._extract_metrics(script_elements)

        comparisons = []
        for ref in references:
            ref_metrics = self._estimate_ref_metrics(ref)
            dim_scores = {}

            for dim in COMPARISON_DIMENSIONS:
                key = dim["key"]
                current_val = current_metrics.get(key, 5)
                ref_val = ref_metrics.get(key, 7)
                gap = round(current_val - ref_val, 1)
                dim_scores[key] = {
                    "dimension": dim["name"],
                    "current": round(current_val, 1),
                    "reference": ref_val,
                    "gap": gap,
                    "status": "above" if gap > 0 else ("on_par" if gap == 0 else "below"),
                }

            comparisons.append({
                "reference_title": ref.get("title", "未知"),
                "dimensions": dim_scores,
                "average_gap": round(
                    sum(d["gap"] for d in dim_scores.values()) / len(dim_scores), 1
                ),
            })

        return {
            "comparisons": comparisons,
            "current_metrics": current_metrics,
            "overall_assessment": self._assess_overall(comparisons),
        }

    def _extract_metrics(self, elements: list) -> dict:
        """从当前剧本提取质量指标"""
        total = max(len(elements), 1)

        types = [e.get("type", "") for e in elements]
        beats = [e.get("beat_type", "") for e in elements]
        dialogues = [e for e in elements if e.get("type") == "dialogue"]

        # 开场力度：前10%元素中 confrontation 比例
        opening_slice = elements[:max(1, total // 10)]
        opening_conf = sum(1 for e in opening_slice
                          if e.get("beat_type") == "confrontation")
        opening_impact = min(10, opening_conf / max(len(opening_slice), 1) * 20 + 3)

        # 冲突密度
        conflict_density = min(10, beats.count("confrontation") / total * 25 + 3)

        # 对白犀利度
        dialogue_sharpness = 5.0
        if dialogues:
            avg_len = sum(len(d.get("text", "")) for d in dialogues) / len(dialogues)
            subtext_ratio = sum(1 for d in dialogues if d.get("subtext")) / len(dialogues)
            dialogue_sharpness = min(10, (20 / max(avg_len, 1)) * 5 + subtext_ratio * 5)

        # 节奏感
        pacing = min(10, (
            types.count("action") / total * 15 +
            types.count("dialogue") / total * 5 +
            4
        ))

        # 钩子质量
        tail = elements[-10:]
        hooks = sum(1 for e in tail for kw in
                   ["突然", "却", "然而", "竟然", "难道"]
                   if kw in e.get("text", ""))
        hook_quality = min(10, hooks * 2 + 4)

        # 角色魅力（情绪多样性）
        role_emotions = defaultdict(set)
        for e in elements:
            role = e.get("role", "")
            emotion = e.get("emotion", "")
            if role and role != "旁白" and emotion:
                role_emotions[role].add(emotion)
        avg_emotion_diversity = (
            sum(len(v) for v in role_emotions.values()) /
            max(len(role_emotions), 1)
        )
        character_appeal = min(10, avg_emotion_diversity * 2 + 3)

        return {
            "opening_impact": round(opening_impact, 1),
            "conflict_density": round(conflict_density, 1),
            "dialogue_sharpness": round(dialogue_sharpness, 1),
            "pacing": round(pacing, 1),
            "hook_quality": round(hook_quality, 1),
            "character_appeal": round(character_appeal, 1),
        }

    def _estimate_ref_metrics(self, ref: dict) -> dict:
        """估算参考剧本的质量指标（基于内容启发式）"""
        content = ref.get("content", "")
        notes = ref.get("notes", "")

        # 基于参考描述进行简单估算
        scores = {
            "opening_impact": 7.0,
            "conflict_density": 7.0,
            "dialogue_sharpness": 7.0,
            "pacing": 7.0,
            "hook_quality": 7.0,
            "character_appeal": 7.0,
        }

        # 根据 notes 中的关键词调整
        if "经典" in notes:
            for key in scores:
                scores[key] = min(10, scores[key] + 1)
        if "典范" in notes:
            for key in scores:
                scores[key] = min(10, scores[key] + 1.5)

        return scores

    def _assess_overall(self, comparisons: list) -> str:
        """生成总体评估"""
        if not comparisons:
            return "无参考剧本可供对比"
        avg_gap = sum(c["average_gap"] for c in comparisons) / len(comparisons)
        if avg_gap > 0:
            return f"整体优于参考水平 (+{avg_gap:.1f})"
        elif avg_gap > -1:
            return f"与参考水平基本持平 ({avg_gap:.1f})"
        else:
            return f"与参考存在差距 ({avg_gap:.1f})，建议针对性改进"


# ═══════════════════════════════════════════════════════════════
# 4. ContinuityRecordSkill — 连续性记录
# ═══════════════════════════════════════════════════════════════

class ContinuityRecordSkill:
    """跨集连续性检查技能"""

    def check_continuity(
        self,
        current_elements: list,
        previous_records: dict,
        current_episode: int,
    ) -> dict:
        """
        检查当前集与之前各集的一致性。

        Args:
            current_elements: 当前集的元素
            previous_records: 之前的连续性记录
            current_episode: 当前集数

        Returns:
            {issues, updates, summary}
        """
        issues = []
        updates = {}

        # 1. 角色称呼一致性
        current_roles = set()
        for e in current_elements:
            role = e.get("role", "")
            if role and role != "旁白":
                current_roles.add(role)

        prev_roles = set(previous_records.get("character_states", {}).keys())
        new_roles = current_roles - prev_roles
        missing_roles = prev_roles - current_roles

        if new_roles:
            updates["new_characters"] = list(new_roles)
        if missing_roles and current_episode > 1:
            issues.append({
                "type": "character_continuity",
                "severity": "low",
                "description": f"以下角色未在本集出场: {', '.join(sorted(missing_roles))}",
            })

        # 2. 道具连续性
        current_props = self._detect_props(current_elements)
        prev_props = previous_records.get("props_inventory", {})
        for prop in current_props:
            if prop in prev_props:
                prev_status = prev_props[prop].get("status", "")
                if prev_status == "destroyed":
                    issues.append({
                        "type": "prop_continuity",
                        "severity": "high",
                        "description": f"道具「{prop}」在之前已被销毁，本集不应出现",
                    })

        # 3. 时间线检查
        time_mentions = self._detect_time_mentions(current_elements)
        prev_timeline = previous_records.get("timeline", [])
        if prev_timeline and time_mentions:
            last_event_time = prev_timeline[-1].get("timestamp_desc", "")
            for tm in time_mentions:
                if tm.get("keyword") in ("昨天", "前日") and current_episode <= 1:
                    issues.append({
                        "type": "timeline_continuity",
                        "severity": "medium",
                        "description": f"第一集不应出现「{tm['keyword']}」等回溯时间词",
                    })

        return {
            "issues": issues,
            "updates": updates,
            "current_roles": list(current_roles),
            "current_props": list(current_props),
            "time_mentions": time_mentions,
            "summary": (
                f"连续性检查: {len(issues)} 个问题, "
                f"{len(new_roles) if new_roles else 0} 个新角色, "
                f"{len(missing_roles) if missing_roles else 0} 个角色未出场"
            ),
        }

    def update_records(
        self, records: dict, current_elements: list, episode: int, updates: dict
    ):
        """更新连续性记录"""
        # 更新角色状态
        if "character_states" not in records:
            records["character_states"] = {}
        for e in current_elements:
            role = e.get("role", "")
            if role and role != "旁白":
                records["character_states"][role] = {
                    "last_seen_episode": episode,
                    "last_emotion": e.get("emotion", ""),
                    "last_action": e.get("action", ""),
                }

        # 更新道具清单
        if "props_inventory" not in records:
            records["props_inventory"] = {}
        for prop in self._detect_props(current_elements):
            records["props_inventory"][prop] = {
                "last_seen_episode": episode,
                "status": "active",
            }

        return records

    def _detect_props(self, elements: list) -> set:
        """检测元素中的道具"""
        prop_kw = ["剑", "刀", "枪", "药", "信", "玉", "簪", "扇", "酒", "茶",
                   "书", "琴", "棋", "画", "镜", "铃", "符", "丹", "戒", "令"]
        props = set()
        for e in elements:
            text = e.get("text", "")
            for kw in prop_kw:
                if kw in text:
                    props.add(kw)
        return props

    def _detect_time_mentions(self, elements: list) -> list:
        """检测时间词"""
        time_kw = ["昨天", "今天", "明天", "前日", "次日", "当日", "三天前", "数日前"]
        mentions = []
        for e in elements:
            text = e.get("text", "")
            for kw in time_kw:
                if kw in text:
                    mentions.append({
                        "keyword": kw,
                        "text": text[:100],
                    })
        return mentions
