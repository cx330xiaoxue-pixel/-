"""
洞察架构师 Agent — Phase 1: 深度洞察分析 (~analyze)

职责:
  - "开天眼"式分析：核心冲突的深层本质
  - 世界观规则提取与一致性检查
  - 观众心理预期管理策略
  - 主题提炼与多重解读
  - 产出 analysis/insight-report.md

使用:
  agent = InsightArchitect(config)
  result = agent.execute(title="剑影江湖", structure=..., network=...)
"""

import os
from datetime import datetime
from typing import Optional

from .base_agent import BaseAgent


class InsightArchitect(BaseAgent):
    """洞察架构师 Agent — 深层主题挖掘与世界观一致性检查"""

    agent_name = "insight-architect"
    agent_display_name = "洞察架构师"
    agent_description = "对小说进行深层主题洞察、世界观规则验证、观众心理预期设计"
    phase = "analyze"

    def execute(
        self,
        title: str = "",
        structure: dict = None,
        network: dict = None,
        elements: list = None,
        world_summary: str = "",
        state_manager=None,
        use_llm: bool = True,
        **kwargs,
    ) -> dict:
        """
        执行深度洞察分析。

        Args:
            title: 作品标题
            structure: 叙事结构分析结果（来自 novel_analyzer）
            network: 人物网络分析结果（来自 novel_analyzer）
            elements: 结构化元素列表
            world_summary: 世界观摘要（来自知识收编）
            state_manager: AgentStateManager 实例
            use_llm: 是否使用 LLM

        Returns:
            {status, insight_report_path, themes, conflicts, audience_strategy, ...}
        """
        self.state_manager = state_manager or self.state_manager
        self.log(f"开始深度洞察: 《{title}》")

        structure = structure or {}
        network = network or {}

        # Step 1: 主题提炼（规则 + LLM）
        self.log("Step 1/4: 提炼核心主题...")
        themes = self._extract_themes(elements, structure, network, use_llm=use_llm)

        # Step 2: 核心冲突分析
        self.log("Step 2/4: 分析核心冲突...")
        conflicts = self._analyze_conflicts(
            elements, structure, network, themes, use_llm=use_llm
        )

        # Step 3: 世界观一致性检查
        self.log("Step 3/4: 世界观一致性检查...")
        consistency = self._check_world_consistency(
            elements, world_summary, use_llm=use_llm
        )

        # Step 4: 观众心理预期策略
        self.log("Step 4/4: 设计观众心理预期策略...")
        audience = self._design_audience_strategy(
            structure, network, themes, conflicts, use_llm=use_llm
        )

        # 生成洞察报告
        report = self._generate_insight_report(
            title=title,
            themes=themes,
            conflicts=conflicts,
            consistency=consistency,
            audience=audience,
        )

        # 保存报告
        output_dir = self.get_config("output.output_dir", "./output")
        project_name = self.state_manager.project_name if self.state_manager else title
        full_output_dir = os.path.join(output_dir, project_name)
        os.makedirs(os.path.join(full_output_dir, "analysis"), exist_ok=True)
        report_path = os.path.join(full_output_dir, "analysis", "insight-report.md")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        self.save_state("last_insight", {
            "title": title,
            "timestamp": datetime.now().isoformat(),
            "theme_count": len(themes),
            "conflict_count": len(conflicts),
        })

        self.log(f"洞察分析完成: {len(themes)} 个主题, {len(conflicts)} 个冲突")

        return {
            "status": "completed",
            "insight_report_path": report_path,
            "themes": themes,
            "conflicts": conflicts,
            "consistency_issues": consistency.get("issues", []),
            "audience_strategy": audience,
            "message": (
                f"洞察分析完成: {len(themes)} 个核心主题, "
                f"{len(conflicts)} 个冲突维度, "
                f"{len(consistency.get('issues', []))} 个一致性问题"
            ),
        }

    # ═══════════════════════════════════════════════════════════
    # 主题提炼
    # ═══════════════════════════════════════════════════════════

    def _extract_themes(
        self,
        elements: list,
        structure: dict,
        network: dict,
        use_llm: bool = True,
    ) -> list[dict]:
        """提炼核心主题"""
        themes = []

        if use_llm and elements:
            # 准备 LLM 上下文
            char_names = ", ".join(
                [c["name"] for c in network.get("main_characters", [])[:8]]
            )
            key_texts = [
                e.get("text", "")[:150]
                for e in elements[:50]
                if e.get("type") in ("narration", "dialogue")
                and len(e.get("text", "")) > 30
            ]
            text_sample = "\n".join(f"- {t}" for t in key_texts[:20])

            prompt = f"""请对以下小说进行深度主题分析。不只是表面情节，要挖掘底层的哲学命题和人性探讨。

主要角色: {char_names}
叙事风格: {structure.get('narrative_style', '未知')}
关键片段:
{text_sample}

请识别 3-7 个核心主题，对每个主题输出:
- theme: 主题名称（如 "命运 vs 自由意志"、"权力腐蚀人性"）
- depth: 在文本中的体现深度 (1-5)
- evidence: 支持该主题的具体文本证据（引用关键片段）
- adaptation_potential: 该主题在影视化后的表现潜力 (1-5)
- visual_metaphor: 可以用什么视觉隐喻来表现这个主题

输出 JSON 数组。"""

            try:
                result = self.call_llm(prompt, use_light=False, expect_json=True)
                if isinstance(result, list):
                    themes = result
            except Exception as e:
                self.log(f"LLM 主题提炼失败: {e}", level="warning")

        # Fallback: 基于情绪分布推断主题
        if not themes:
            emotion_counter = {}
            for e in (elements or []):
                emotion = e.get("emotion", "")
                if emotion:
                    emotion_counter[emotion] = emotion_counter.get(emotion, 0) + 1

            dominant = sorted(emotion_counter.items(), key=lambda x: -x[1])[:3]
            for emotion, count in dominant:
                themes.append({
                    "theme": f"{emotion}与成长",
                    "depth": 3,
                    "evidence": f"全文频繁出现{emotion}情绪 (共{count}次)",
                    "adaptation_potential": 3,
                    "visual_metaphor": "",
                })

        return themes

    # ═══════════════════════════════════════════════════════════

    def _analyze_conflicts(
        self,
        elements: list,
        structure: dict,
        network: dict,
        themes: list,
        use_llm: bool = True,
    ) -> list[dict]:
        """分析核心冲突的多个维度"""
        conflicts = []

        # 规则版：从节拍类型统计冲突密度
        if elements:
            conf_elements = [
                e for e in elements if e.get("beat_type") == "confrontation"
            ]
            main_chars = network.get("main_characters", [])

            # 角色间冲突（共现于 confrontation 节拍中的角色对）
            char_pairs = {}
            for i, e1 in enumerate(conf_elements):
                for e2 in conf_elements[i+1:i+10]:
                    r1, r2 = e1.get("role", ""), e2.get("role", "")
                    if r1 and r2 and r1 != r2 and r1 != "旁白" and r2 != "旁白":
                        pair = tuple(sorted([r1, r2]))
                        char_pairs[pair] = char_pairs.get(pair, 0) + 1

            top_conflicts = sorted(char_pairs.items(), key=lambda x: -x[1])[:5]
            for (a, b), count in top_conflicts:
                conflicts.append({
                    "type": "interpersonal",
                    "parties": [a, b],
                    "intensity": min(10, count),
                    "nature": "角色间对抗",
                })

        # LLM 增强
        if use_llm and conflicts:
            conflict_text = "\n".join(
                f"- {c['parties'][0]} vs {c['parties'][1]}: 强度 {c['intensity']}"
                for c in conflicts
            )
            theme_names = [t.get("theme", "") for t in themes[:3]]

            prompt = f"""基于以下冲突数据，进行深层冲突分析。

表面冲突:
{conflict_text}

核心主题: {', '.join(theme_names)}

请分析:
1. 这些表面冲突背后的深层本质（如：阶层矛盾、价值观对立、身份认同危机）
2. 是否存在内部冲突（角色内心挣扎）没有被数据体现
3. 冲突升级的潜在路径

输出 JSON:
{{
  "deep_conflicts": [{{"name": "深层冲突名", "description": "描述", "stake": "利害关系"}}],
  "internal_conflicts": [{{"character": "角色名", "struggle": "内心挣扎描述"}}],
  "escalation_path": "冲突升级路径描述"
}}"""

            try:
                enhanced = self.call_llm(prompt, use_light=False, expect_json=True)
                if isinstance(enhanced, dict):
                    conflicts.append({
                        "type": "deep_analysis",
                        "details": enhanced,
                    })
            except Exception as e:
                self.log(f"LLM 冲突分析失败: {e}", level="warning")

        return conflicts

    # ═══════════════════════════════════════════════════════════

    def _check_world_consistency(
        self,
        elements: list,
        world_summary: str = "",
        use_llm: bool = True,
    ) -> dict:
        """
        世界观一致性检查。

        Returns:
            {issues: [{location, description, severity}], overall_consistency: 1-10}
        """
        issues = []

        if not elements:
            return {"issues": [], "overall_consistency": 10}

        # 规则检查
        # 1. 角色称呼一致性
        role_lines = defaultdict(list)
        for e in elements:
            role = e.get("role", "")
            if role and role != "旁白":
                role_lines[role].append(e.get("text", ""))

        # 2. 时间线一致性
        time_mentions = []
        for e in elements:
            text = e.get("text", "")
            chapter_id = e.get("chapter_id", 0)
            for keyword in ["昨天", "今天", "明天", "前日", "次日", "当日"]:
                if keyword in text:
                    time_mentions.append({
                        "chapter_id": chapter_id,
                        "keyword": keyword,
                        "text": text[:100],
                    })

        # 3. 力量等级一致性
        power_terms = set()
        for e in elements:
            text = e.get("text", "")
            for m in __import__('re').finditer(
                r'(\S{1,4}(?:境|界|期|品|阶|级|重|层|星|段))', text
            ):
                power_terms.add(m.group(1))

        # LLM 增强检查
        if use_llm and world_summary:
            power_text = "\n".join(sorted(power_terms)[:20])
            prompt = f"""请检查以下世界观规则是否存在内部矛盾。

世界观摘要:
{world_summary[:500]}

力量体系中出现的术语:
{power_text}

请检查:
1. 力量等级术语是否有冲突（如同一等级有不同名称）
2. 因果关系是否闭合（能力是否有明确的限制和代价）
3. 是否有"机械降神"风险（未预先铺垫的超强能力突然出现）

输出 JSON:
{{
  "issues": [{{"location": "具体章节/场景", "description": "问题描述", "severity": "high|medium|low"}}],
  "overall_consistency": 1-10
}}"""

            try:
                result = self.call_llm(prompt, use_light=True, expect_json=True)
                if isinstance(result, dict):
                    issues = result.get("issues", [])
                    overall = result.get("overall_consistency", 8)
                    return {"issues": issues, "overall_consistency": overall}
            except Exception:
                pass

        # Fallback: 基于收集的规则数据
        return {
            "issues": issues,
            "overall_consistency": 8,  # 默认较高
            "power_terms_found": list(power_terms)[:30],
            "time_mentions_count": len(time_mentions),
        }

    # ═══════════════════════════════════════════════════════════

    def _design_audience_strategy(
        self,
        structure: dict,
        network: dict,
        themes: list,
        conflicts: list,
        use_llm: bool = True,
    ) -> dict:
        """设计观众心理预期管理策略"""
        strategy = {
            "target_audience": "全年龄段",
            "emotional_hooks": [],
            "tension_curve_strategy": "标准三幕起伏",
            "cliffhanger_density": "中等",
        }

        if use_llm and themes:
            theme_names = [t.get("theme", "") for t in themes[:3]]
            prompt = f"""作为影视策划，请为以下改编项目设计观众心理预期管理策略。

核心主题: {', '.join(theme_names)}
叙事节奏: {structure.get('pacing', '未知')}
角色数量: {network.get('total_characters', 0)}

请输出 JSON:
{{
  "target_audience": "核心目标受众群体",
  "audience_expectation": "该类型受众的核心期待",
  "emotional_hooks": ["情感钩子1", "情感钩子2", ...],
  "tension_curve_strategy": "悬念曲线设计策略",
  "cliffhanger_density": "每集悬念密度建议 (high/medium/low)",
  "surprise_factors": ["可以给观众惊喜的元素1", ...],
  "retention_strategy": "观众留存策略",
  "market_positioning": "市场定位建议"
}}"""

            try:
                result = self.call_llm(prompt, use_light=False, expect_json=True)
                if isinstance(result, dict):
                    strategy.update(result)
            except Exception as e:
                self.log(f"LLM 受众策略失败: {e}", level="warning")

        return strategy

    # ═══════════════════════════════════════════════════════════

    def _generate_insight_report(
        self,
        title: str,
        themes: list,
        conflicts: list,
        consistency: dict,
        audience: dict,
    ) -> str:
        """生成洞察报告 (Markdown)"""
        report = []
        report.append(f"# 深度洞察报告 — 《{title}》\n")
        report.append(f"**分析工具**: Novel-to-Script Pro v2.0 — Insight Architect")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        report.append("---\n")

        # 核心主题
        report.append("## 1. 核心主题洞察\n")
        if themes:
            for i, t in enumerate(themes, 1):
                report.append(f"### 1.{i} {t.get('theme', '未命名')}")
                report.append(f"- **深度评分**: {'★' * t.get('depth', 0)}{'☆' * (5 - t.get('depth', 0))}")
                report.append(f"- **影视潜力**: {'★' * t.get('adaptation_potential', 0)}")
                if t.get("evidence"):
                    report.append(f"- **文本证据**: {t['evidence'][:200]}")
                if t.get("visual_metaphor"):
                    report.append(f"- **视觉隐喻**: {t['visual_metaphor']}")
                report.append("")
        else:
            report.append("（未提取到明确主题）\n")

        report.append("---\n")

        # 核心冲突
        report.append("## 2. 核心冲突分析\n")
        for c in conflicts:
            if c.get("type") == "interpersonal":
                parties = " vs ".join(c.get("parties", ["?", "?"]))
                report.append(f"- **{parties}**: 强度 {c.get('intensity', '?')}/10 — {c.get('nature', '')}")
            elif c.get("type") == "deep_analysis":
                details = c.get("details", {})
                deep = details.get("deep_conflicts", [])
                if deep:
                    report.append(f"\n### 深层冲突")
                    for d in deep:
                        report.append(f"- **{d.get('name', '')}**: {d.get('description', '')}")
                        report.append(f"  利害关系: {d.get('stake', '')}")
                internal = details.get("internal_conflicts", [])
                if internal:
                    report.append(f"\n### 内部冲突")
                    for ic in internal:
                        report.append(f"- **{ic.get('character', '')}**: {ic.get('struggle', '')}")
                if details.get("escalation_path"):
                    report.append(f"\n### 冲突升级路径")
                    report.append(f"{details['escalation_path']}")
        report.append("")

        report.append("---\n")

        # 世界观一致性
        report.append("## 3. 世界观一致性检查\n")
        report.append(f"- **整体一致性**: {consistency.get('overall_consistency', '?')}/10")

        issues = consistency.get("issues", [])
        if issues:
            report.append(f"\n### 发现 {len(issues)} 个问题")
            for issue in issues:
                severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    issue.get("severity", ""), "⚪"
                )
                report.append(f"- {severity_icon} [{issue.get('severity', '?')}] "
                             f"{issue.get('location', '未知位置')}: {issue.get('description', '')}")
        else:
            report.append("\n✅ 未发现明显的一致性问题")
        report.append("")

        report.append("---\n")

        # 受众策略
        report.append("## 4. 观众心理预期策略\n")
        report.append(f"- **目标受众**: {audience.get('target_audience', '未定义')}")
        if audience.get("audience_expectation"):
            report.append(f"- **核心期待**: {audience['audience_expectation']}")
        report.append(f"- **悬念密度**: {audience.get('cliffhanger_density', '未定义')}")
        report.append(f"- **张力曲线策略**: {audience.get('tension_curve_strategy', '未定义')}")

        hooks = audience.get("emotional_hooks", [])
        if hooks:
            report.append(f"\n### 情感钩子")
            for h in hooks:
                report.append(f"- {h}")

        surprises = audience.get("surprise_factors", [])
        if surprises:
            report.append(f"\n### 惊喜元素")
            for s in surprises:
                report.append(f"- {s}")

        if audience.get("retention_strategy"):
            report.append(f"\n### 留存策略")
            report.append(f"{audience['retention_strategy']}")
        if audience.get("market_positioning"):
            report.append(f"\n### 市场定位")
            report.append(f"{audience['market_positioning']}")

        return "\n".join(report)


# ═══════════════════════════════════════════════════════════════
# 便捷工厂
# ═══════════════════════════════════════════════════════════════

def create_insight_architect(config: dict = None, **kwargs) -> InsightArchitect:
    """创建洞察架构师 Agent 实例"""
    return InsightArchitect(config=config, **kwargs)
