"""
小说分析 Agent — Phase 1: 改编分析 (~analyze)

职责:
  - 调用 llm_extractor 做全文结构化抽取
  - 分析叙事结构（三幕/四幕/章回体）、POV、节奏
  - 分析人物网络、关系图、角色功能（原型分类）
  - 评估改编潜力并提出建议
  - 产出 analysis/analysis-report.md 和 analysis/insight-report.md

使用:
  agent = NovelAnalyzer(config)
  result = agent.execute(title="剑影江湖", author="江湖客")
"""

import os
from datetime import datetime
from typing import Optional

from .base_agent import BaseAgent


class NovelAnalyzer(BaseAgent):
    """小说分析 Agent — 深度分析叙事结构、人物网络与改编潜力"""

    agent_name = "novel-analyzer"
    agent_display_name = "小说分析师"
    agent_description = "分析小说的叙事结构、人物网络、节奏与改编潜力，产出分析报告"
    phase = "analyze"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # 延迟导入
        from skills.adaptation_analysis import AdaptationAnalysisSkill
        self.skill = AdaptationAnalysisSkill()

    def execute(
        self,
        title: str = "",
        author: str = "",
        llm_extractor=None,
        rule_extractor=None,
        character_tracker=None,
        state_manager=None,
        source_dir: str = None,
        all_elements: list = None,
        world_summary: str = "",
        use_llm: bool = True,
        **kwargs,
    ) -> dict:
        """
        执行小说改编分析。

        Args:
            title: 作品标题
            author: 原作者
            llm_extractor: LLMExtractor 实例
            rule_extractor: RuleExtractor 实例
            character_tracker: CharacterTracker 实例
            state_manager: AgentStateManager 实例
            source_dir: 源材料目录（如果 all_elements 未提供）
            all_elements: 已提取的元素列表（跳过抽取步骤）
            world_summary: 世界观摘要（来自知识收编阶段）
            use_llm: 是否使用 LLM 增强

        Returns:
            {status, analysis_report_path, structure, network, potential, ...}
        """
        self.state_manager = state_manager or self.state_manager
        self.log(f"开始分析: 《{title}》(作者: {author or '未知'})")

        # Step 1: 获取/抽取结构化数据
        if all_elements is None:
            all_elements = self._extract_all(
                source_dir=source_dir,
                llm_extractor=llm_extractor,
                rule_extractor=rule_extractor,
                character_tracker=character_tracker,
                use_llm=use_llm,
            )

        if not all_elements:
            return {
                "status": "failed",
                "error": "未能提取任何结构化数据，请检查源材料",
            }

        chapter_ids = sorted(set(e.get("chapter_id", 0) for e in all_elements))
        chapter_count = len(chapter_ids)
        self.log(f"数据就绪: {len(all_elements)} 个元素, {chapter_count} 个章节")

        # Step 2: 叙事结构分析
        self.log("分析叙事结构...")
        structure = self.skill.analyze_narrative_structure(all_elements, chapter_count)

        # Step 3: 人物网络分析
        self.log("分析人物网络...")
        network = self.skill.analyze_character_network(all_elements, character_tracker)

        # Step 4: LLM 增强分析（可选）
        if use_llm:
            self.log("LLM 增强分析...")
            structure, network = self._llm_enhance_analysis(
                all_elements, structure, network, title
            )

        # Step 5: 改编潜力评估
        self.log("评估改编潜力...")
        potential = self.skill.assess_adaptation_potential(structure, network)

        # Step 6: 生成报告
        self.log("生成分析报告...")
        report = self.skill.generate_analysis_report(
            title=title,
            author=author,
            structure=structure,
            network=network,
            potential=potential,
            world_summary=world_summary,
        )

        # 保存报告
        output_dir = self.get_config("output.output_dir", "./output")
        project_name = self.state_manager.project_name if self.state_manager else title
        full_output_dir = os.path.join(output_dir, project_name)
        report_path = self.skill.save_report(report, full_output_dir, title)

        # 保存状态
        self.save_state("last_analysis", {
            "title": title,
            "author": author,
            "timestamp": datetime.now().isoformat(),
            "chapter_count": chapter_count,
            "total_elements": len(all_elements),
            "overall_score": potential.get("overall_score", 0),
        })

        self.log(f"分析完成: 综合评分 {potential.get('overall_score', 0)}/10")

        return {
            "status": "completed",
            "title": title,
            "author": author,
            "chapter_count": chapter_count,
            "total_elements": len(all_elements),
            "structure": structure,
            "network": network,
            "potential": potential,
            "analysis_report_path": report_path,
            "message": (
                f"改编分析完成: {chapter_count} 章, {network['total_characters']} 个角色, "
                f"综合评分 {potential.get('overall_score', 0)}/10, "
                f"建议媒介: {potential.get('recommended_medium', '未知')}"
            ),
        }

    # ═══════════════════════════════════════════════════════════
    # 数据抽取
    # ═══════════════════════════════════════════════════════════

    def _extract_all(
        self,
        source_dir: str = None,
        llm_extractor=None,
        rule_extractor=None,
        character_tracker=None,
        use_llm: bool = True,
    ) -> list:
        """
        从源目录批量抽取所有章节的结构化数据。

        优先使用 LLM 抽取器（需要 API Key），
        降级时使用规则抽取器。
        """
        source_dir = source_dir or self.get_config("knowledge.sources_dir", "./sources")
        if not source_dir or not os.path.isdir(source_dir):
            self.log("源目录不存在，尝试使用 sample_novel", level="warning")
            source_dir = "./sample_novel"

        # 扫描文件
        files = []
        for root, _, filenames in sorted(os.walk(source_dir)):
            for fn in sorted(filenames):
                if fn.endswith(".txt"):
                    files.append(os.path.join(root, fn))

        if not files:
            self.log("未找到 .txt 文件", level="error")
            return []

        self.log(f"发现 {len(files)} 个文本文件")

        all_elements = []
        extractor = llm_extractor if (use_llm and llm_extractor) else rule_extractor

        for i, fpath in enumerate(files, start=1):
            # 从文件名推断章节标题
            basename = os.path.splitext(os.path.basename(fpath))[0]
            chapter_title = basename

            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    text = f.read()
            except UnicodeDecodeError:
                self.log(f"跳过非 UTF-8 文件: {fpath}", level="warning")
                continue

            if extractor:
                self.log(f"抽取第{i}章: {chapter_title} ({len(text)} 字符)")
                try:
                    elements = extractor.extract_from_chapter(
                        chapter_text=text,
                        chapter_id=i,
                        chapter_title=chapter_title,
                    )
                    all_elements.extend(elements)

                    # 同时更新角色追踪器
                    if character_tracker:
                        characters = extractor.extract_characters_from_chapter(text, i)
                        if characters:
                            character_tracker.merge_extracted_characters(characters, i)
                        character_tracker.update_from_elements(elements, i)

                except Exception as e:
                    self.log(f"第{i}章抽取失败: {e}", level="error")
            else:
                self.log(f"无可用抽取器，跳过第{i}章", level="warning")

        return all_elements

    # ═══════════════════════════════════════════════════════════
    # LLM 增强分析
    # ═══════════════════════════════════════════════════════════

    def _llm_enhance_analysis(
        self,
        elements: list,
        structure: dict,
        network: dict,
        title: str = "",
    ) -> tuple:
        """使用 LLM 对初步分析结果进行增强"""
        # 构建分析摘要
        brief = self._build_analysis_brief(elements, structure, network)

        prompt = f"""你是一位资深的影视改编顾问。基于以下小说分析摘要，请提供专业的改编建议。

{brief}

请输出 JSON:
{{
  "narrative_assessment": "对叙事结构的专业评估（100-200字）",
  "character_highlights": "最值得保留的核心角色及其独特价值",
  "adaptation_risks": ["改编风险1", "改编风险2", "改编风险3"],
  "unique_selling_points": ["独特卖点1", "独特卖点2", "独特卖点3"],
  "target_audience": "目标受众描述",
  "comparable_works": ["可类比的作品1", "作品2"],
  "structural_changes_needed": "建议的结构调整",
  "pacing_recommendation": "节奏调整建议"
}}"""

        try:
            enhanced = self.call_llm(prompt, use_light=False, expect_json=True)
            if isinstance(enhanced, dict):
                structure["llm_assessment"] = enhanced.get("narrative_assessment", "")
                network["character_highlights"] = enhanced.get("character_highlights", "")
                structure["adaptation_risks"] = enhanced.get("adaptation_risks", [])
                structure["unique_selling_points"] = enhanced.get("unique_selling_points", [])
                structure["target_audience"] = enhanced.get("target_audience", "")
                structure["comparable_works"] = enhanced.get("comparable_works", [])
                structure["structural_changes_needed"] = enhanced.get("structural_changes_needed", "")
                structure["pacing_recommendation"] = enhanced.get("pacing_recommendation", "")
        except Exception as e:
            self.log(f"LLM 增强分析失败: {e}", level="warning")

        return structure, network

    def _build_analysis_brief(self, elements: list, structure: dict, network: dict) -> str:
        """构建分析摘要供 LLM 使用"""
        # 角色摘要
        main_chars = network.get("main_characters", [])[:8]
        char_text = "\n".join(
            f"- {c['name']}: 出场{c['appearances']}次 ({c['share']}%)"
            for c in main_chars
        )

        # 情节摘要（取关键 narration 元素）
        key_narrations = [
            e for e in elements
            if e.get("type") in ("narration", "description")
            and len(e.get("text", "")) > 50
        ][:10]
        plot_text = "\n".join(
            f"- {e['text'][:120]}..."
            for e in key_narrations
        )

        return f"""
作品: {structure.get('title', '未知')}
章节数: {structure.get('chapter_count', 0)}
总元素数: {structure.get('total_elements', 0)}
叙事风格: {structure.get('narrative_style', '未知')}
POV类型: {structure.get('pov_type', '未知')}
节奏: {structure.get('pacing', '未知')}
对白占比: {structure.get('dialogue_ratio', 0)}%
叙述占比: {structure.get('narration_ratio', 0)}%
动作占比: {structure.get('action_ratio', 0)}%

主要角色:
{char_text}

关键情节片段:
{plot_text}
"""


# ═══════════════════════════════════════════════════════════════
# 便捷工厂
# ═══════════════════════════════════════════════════════════════

def create_novel_analyzer(config: dict = None, **kwargs) -> NovelAnalyzer:
    """创建小说分析 Agent 实例"""
    return NovelAnalyzer(config=config, **kwargs)
