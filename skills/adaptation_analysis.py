"""
改编分析 Skill — 叙事结构分析、人物网络分析、改编潜力评估

可被 novel-analyzer Agent 和其他 Agent 复用的核心分析技能。
"""

import os
from collections import Counter, defaultdict
from typing import Optional


class AdaptationAnalysisSkill:
    """改编分析核心技能——叙事结构、人物网络、改编评估"""

    def __init__(self):
        pass

    # ═══════════════════════════════════════════════════════════
    # 叙事结构分析
    # ═══════════════════════════════════════════════════════════

    def analyze_narrative_structure(
        self, elements: list, chapter_count: int
    ) -> dict:
        """
        分析叙事结构：POV、节奏、章节密度。

        Args:
            elements: 提取的结构化元素列表
            chapter_count: 总章节数

        Returns:
            {structure_type, pov, pacing, chapter_density, act_breakdown}
        """
        # POV 分析（谁说话最多）
        pov_counter = Counter()
        dialogue_characters = set()
        for elem in elements:
            role = elem.get("role", "")
            if role and role != "旁白":
                pov_counter[role] += 1
                if elem.get("type") == "dialogue":
                    dialogue_characters.add(role)

        top_pov = pov_counter.most_common(5)
        total_role_appearances = sum(pov_counter.values())
        pov_distribution = {
            name: round(count / max(total_role_appearances, 1) * 100, 1)
            for name, count in top_pov
        }

        # 对白/叙述比例 → 推断叙事风格
        dialogue_count = sum(1 for e in elements if e.get("type") == "dialogue")
        narration_count = sum(1 for e in elements if e.get("type") in ("narration", "description"))
        action_count = sum(1 for e in elements if e.get("type") == "action")
        total = max(len(elements), 1)

        dialogue_ratio = dialogue_count / total
        narration_ratio = narration_count / total

        # 叙事风格推断
        if dialogue_ratio > 0.4:
            narrative_style = "对话驱动型（适合直接改编剧本）"
        elif narration_ratio > 0.6:
            narrative_style = "叙述密集型（需要大量视觉化转换）"
        else:
            narrative_style = "均衡型"

        # POV 类型
        if len(dialogue_characters) <= 3:
            pov_type = "有限第三人称 / 第一人称"
        elif len(dialogue_characters) <= 8:
            pov_type = "多角色视角"
        else:
            pov_type = "群像全景视角"

        # 节拍类型分布 → 节奏
        beat_counter = Counter(e.get("beat_type", "") for e in elements if e.get("beat_type"))
        dominant_beat = beat_counter.most_common(1)
        pacing = "中等节奏"
        if dominant_beat:
            if dominant_beat[0][0] == "confrontation" and dominant_beat[0][1] / total > 0.3:
                pacing = "快节奏（高冲突密度）"
            elif dominant_beat[0][0] in ("setup", "transition") and dominant_beat[0][1] / total > 0.5:
                pacing = "慢节奏（铺垫为主）"

        # 三幕/四幕推断（基于章节比例）
        act_breakdown = self._estimate_act_structure(chapter_count, elements)

        return {
            "narrative_style": narrative_style,
            "pov_type": pov_type,
            "pov_distribution": pov_distribution,
            "dialogue_ratio": round(dialogue_ratio * 100, 1),
            "narration_ratio": round(narration_ratio * 100, 1),
            "action_ratio": round(action_count / total * 100, 1),
            "pacing": pacing,
            "dominant_beat": dominant_beat[0] if dominant_beat else ("unknown", 0),
            "act_breakdown": act_breakdown,
            "total_elements": total,
            "chapter_count": chapter_count,
        }

    def _estimate_act_structure(self, chapter_count: int, elements: list) -> dict:
        """根据章节数和元素分布推断幕结构"""
        # 统计每章的元素数
        chapter_elements = defaultdict(int)
        for e in elements:
            chapter_elements[e.get("chapter_id", 1)] += 1

        sorted_chapters = sorted(chapter_elements.keys())

        # 经典三幕：Setup (25%) → Confrontation (50%) → Resolution (25%)
        if chapter_count >= 3:
            act1_end = max(1, int(chapter_count * 0.25))
            act2_end = max(act1_end + 1, int(chapter_count * 0.75))
            return {
                "structure": "三幕结构（预估）",
                "act1_setup": f"第1-{act1_end}章",
                "act2_confrontation": f"第{act1_end+1}-{act2_end}章",
                "act3_resolution": f"第{act2_end+1}-{chapter_count}章",
            }
        else:
            return {"structure": "短篇/单幕（章节数不足3）"}

    # ═══════════════════════════════════════════════════════════
    # 人物网络分析
    # ═══════════════════════════════════════════════════════════

    def analyze_character_network(
        self, elements: list, character_tracker=None
    ) -> dict:
        """
        分析人物关系网络。

        Returns:
            {main_characters, relationship_density, centrality, archetypes}
        """
        # 角色出场统计
        role_appearances = Counter()
        role_emotions = defaultdict(list)
        role_types = defaultdict(set)

        for elem in elements:
            role = elem.get("role", "")
            if role and role != "旁白":
                role_appearances[role] += 1
            if elem.get("emotion"):
                role_emotions[role].append(elem["emotion"])
            if elem.get("type"):
                role_types[role].add(elem["type"])

        total_appearances = sum(role_appearances.values())
        total_roles = len(role_appearances)

        # 主角识别（出场次数 > 总次数的 10%）
        main_threshold = total_appearances * 0.10
        main_characters = [
            {"name": name, "appearances": count,
             "share": round(count / max(total_appearances, 1) * 100, 1)}
            for name, count in role_appearances.most_common()
            if count >= main_threshold
        ]

        # 角色功能分类（原型）
        archetypes = {}
        for name, count in role_appearances.most_common(10):
            if count >= total_appearances * 0.15:
                archetypes[name] = "protagonist"
            elif count >= total_appearances * 0.05:
                archetypes[name] = "supporting"
            else:
                archetypes[name] = "minor"

        # 关系密度
        relationship_density = min(1.0, len(role_appearances) / max(total_elements := len(elements), 1) * 10)

        # 从 CharacterTracker 补充
        tracker_data = {}
        if character_tracker:
            tracker_data = {
                "total_tracked": len(character_tracker.characters),
                "relationships": len(character_tracker.relationships),
                "arc_characters": [
                    name for name, char in character_tracker.characters.items()
                    if char.get("arc_stage") in ("development", "crisis_or_transformation")
                ],
            }

        return {
            "total_characters": total_roles,
            "main_characters": main_characters,
            "archetypes": archetypes,
            "relationship_density": round(relationship_density, 2),
            "character_tracker_data": tracker_data,
            "emotion_diversity": {
                name: len(set(emotions))
                for name, emotions in role_emotions.items()
                if len(emotions) >= 5
            },
        }

    # ═══════════════════════════════════════════════════════════
    # 改编潜力评估
    # ═══════════════════════════════════════════════════════════

    def assess_adaptation_potential(self, structure: dict, network: dict) -> dict:
        """
        评估小说的改编潜力。

        Returns:
            {overall_score, dimensions: {dialogue, conflict, visual, character, structure}}
        """
        scores = {}

        # 对白密度（对白越多，越容易改编）
        dialogue_ratio = structure.get("dialogue_ratio", 0)
        scores["dialogue"] = min(10, dialogue_ratio / 5)

        # 冲突密度（confrontation 节拍比例）
        dominant_beat = structure.get("dominant_beat", ("", 0))
        beat_name, beat_count = dominant_beat
        if beat_name == "confrontation":
            scores["conflict"] = min(10, beat_count / max(structure.get("total_elements", 1), 1) * 30)
        else:
            scores["conflict"] = 5

        # 视觉潜力（action 比例）
        action_ratio = structure.get("action_ratio", 0)
        scores["visual"] = min(10, action_ratio / 5 + 3)

        # 角色丰富度
        total_chars = network.get("total_characters", 0)
        scores["character"] = min(10, total_chars / 3) if total_chars >= 3 else total_chars * 2

        # 结构完整度
        chapter_count = structure.get("chapter_count", 1)
        scores["structure_score"] = min(10, chapter_count / 5) if chapter_count >= 3 else 3

        overall = sum(scores.values()) / len(scores)

        # 改编建议
        suggestions = []
        if dialogue_ratio < 20:
            suggestions.append("对白密度偏低，改编时需大量创作新对白")
        if action_ratio < 10:
            suggestions.append("动作描写较少，建议在剧本中增强视觉冲突")
        if total_chars > 20:
            suggestions.append("角色数量较多，建议合并/删减次要角色以适应影视时长")
        if chapter_count < 5:
            suggestions.append("章节较少，适合改编为电影而非电视剧")

        return {
            "overall_score": round(overall, 1),
            "dimension_scores": scores,
            "suggestions": suggestions,
            "recommended_medium": (
                "film" if chapter_count <= 10
                else "tv_series" if chapter_count <= 100
                else "web_series"
            ),
        }

    # ═══════════════════════════════════════════════════════════
    # 报告生成
    # ═══════════════════════════════════════════════════════════

    def generate_analysis_report(
        self,
        title: str,
        author: str,
        structure: dict,
        network: dict,
        potential: dict,
        world_summary: str = "",
    ) -> str:
        """生成 Markdown 格式的分析报告"""
        report = []
        report.append(f"# 改编分析报告 — 《{title}》\n")
        report.append(f"**原著作者**: {author or '未知'}")
        report.append(f"**分析工具**: Novel-to-Script Pro v2.0\n")
        report.append("---\n")

        # 叙事结构
        report.append("## 1. 叙事结构分析\n")
        report.append(f"- **叙事风格**: {structure.get('narrative_style', '未知')}")
        report.append(f"- **视角类型**: {structure.get('pov_type', '未知')}")
        report.append(f"- **整体节奏**: {structure.get('pacing', '未知')}")
        report.append(f"- **对白占比**: {structure.get('dialogue_ratio', 0)}%")
        report.append(f"- **叙述占比**: {structure.get('narration_ratio', 0)}%")
        report.append(f"- **动作占比**: {structure.get('action_ratio', 0)}%")
        report.append(f"- **总元素数**: {structure.get('total_elements', 0)}")
        report.append(f"- **总章节数**: {structure.get('chapter_count', 0)}")

        # 幕结构
        acts = structure.get("act_breakdown", {})
        if acts:
            report.append(f"\n### 幕结构\n")
            report.append(f"- **结构**: {acts.get('structure', '未知')}")
            for key in ["act1_setup", "act2_confrontation", "act3_resolution"]:
                if key in acts:
                    report.append(f"- **{key}**: {acts[key]}")

        # POV 分布
        pov = structure.get("pov_distribution", {})
        if pov:
            report.append(f"\n### POV 分布\n")
            for name, share in list(pov.items())[:8]:
                report.append(f"- {name}: {share}%")

        report.append("\n---\n")

        # 人物网络
        report.append("## 2. 人物网络分析\n")
        report.append(f"- **总角色数**: {network.get('total_characters', 0)}")
        report.append(f"- **关系密度**: {network.get('relationship_density', 0)}")

        main_chars = network.get("main_characters", [])
        if main_chars:
            report.append(f"\n### 主要角色\n")
            for char in main_chars[:10]:
                report.append(f"- **{char['name']}**: 出场 {char['appearances']} 次 ({char['share']}%)")

        archetypes = network.get("archetypes", {})
        if archetypes:
            report.append(f"\n### 角色功能分类\n")
            for name, atype in archetypes.items():
                report.append(f"- {name}: {atype}")

        report.append("\n---\n")

        # 改编潜力
        report.append("## 3. 改编潜力评估\n")
        report.append(f"- **综合评分**: {potential.get('overall_score', 0)}/10")
        report.append(f"- **建议媒介**: {potential.get('recommended_medium', '未知')}")

        dims = potential.get("dimension_scores", {})
        if dims:
            report.append(f"\n### 各维度评分\n")
            dim_labels = {
                "dialogue": "对白密度", "conflict": "冲突密度",
                "visual": "视觉潜力", "character": "角色丰富度",
                "structure_score": "结构完整度",
            }
            for key, score in dims.items():
                label = dim_labels.get(key, key)
                bar = "█" * int(score) + "░" * (10 - int(score))
                report.append(f"- {label}: {bar} {score}/10")

        suggestions = potential.get("suggestions", [])
        if suggestions:
            report.append(f"\n### 改编建议\n")
            for s in suggestions:
                report.append(f"- ⚠️ {s}")

        # 世界观（如果有）
        if world_summary:
            report.append("\n---\n")
            report.append("## 4. 世界观概述\n")
            report.append(world_summary)

        return "\n".join(report)

    def save_report(self, report: str, output_dir: str, title: str) -> str:
        """保存分析报告到文件"""
        os.makedirs(os.path.join(output_dir, "analysis"), exist_ok=True)
        path = os.path.join(output_dir, "analysis", "analysis-report.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(report)
        return path
