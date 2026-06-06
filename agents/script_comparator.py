"""
剧本对比 Agent — Phase 4: 与爆款参考剧本逐一对比

职责:
  - 与参考剧本逐一对比（开场力度、冲突密度、对白犀利度、节奏、钩子质量）
  - 量化每个维度的差距
  - 产出 review/one-by-one-comparison-ep{N:02d}.md

使用:
  agent = ScriptComparator(config)
  result = agent.execute(episode=1, script_elements=..., references=...)
"""

import os
from datetime import datetime

from .base_agent import BaseAgent


class ScriptComparator(BaseAgent):
    """剧本对比 Agent — 与爆款参考的多维度量化对比"""

    agent_name = "script-comparator"
    agent_display_name = "剧本对比师"
    agent_description = "将当前剧本与爆款参考剧本逐一对比，量化差距并提出改进建议"
    phase = "review"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from skills.review_skills import ComparativeReviewSkill
        self.skill = ComparativeReviewSkill()

    def execute(
        self,
        episode: int = 1,
        script_elements: list = None,
        script_path: str = None,
        references: list = None,
        state_manager=None,
        use_llm: bool = True,
        **kwargs,
    ) -> dict:
        """
        执行与参考剧本的逐一对比。

        Args:
            episode: 集数
            script_elements: 剧本元素
            script_path: 剧本路径
            references: 爆款参考列表
            state_manager: AgentStateManager
            use_llm: LLM 增强

        Returns:
            {status, comparisons, report_path, ...}
        """
        self.state_manager = state_manager or self.state_manager

        # 加载
        if script_elements is None and script_path:
            script_elements = self._load_elements(script_path)
        script_elements = script_elements or []
        references = references or self._get_default_references()

        self.log(f"对比第{episode}集 vs {len(references)} 个参考剧本")

        # 规则对比
        comparison = self.skill.compare(script_elements, references)

        # LLM 增强
        llm_details = {}
        if use_llm:
            self.log("LLM 深度对比...")
            llm_details = self._llm_deep_comparison(
                script_elements, references, comparison
            )

        # 生成报告
        report = self._generate_report(
            episode=episode,
            comparison=comparison,
            llm_details=llm_details,
        )

        # 保存
        output_dir = self.get_config("output.output_dir", "./output")
        project_name = self.state_manager.project_name if self.state_manager else "untitled"
        full_output_dir = os.path.join(output_dir, project_name)
        os.makedirs(os.path.join(full_output_dir, "review"), exist_ok=True)
        report_path = os.path.join(
            full_output_dir, "review", f"one-by-one-comparison-ep{episode:02d}.md"
        )

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        self.log(f"对比完成: {len(references)} 个参考, 评估 {comparison.get('overall_assessment', '')}")

        return {
            "status": "completed",
            "episode": episode,
            "references_compared": len(references),
            "comparison": comparison,
            "llm_insights": llm_details,
            "report_path": report_path,
            "message": f"剧本对比完成: vs {len(references)} 个参考, {comparison.get('overall_assessment', '')}",
        }

    def _load_elements(self, path: str) -> list:
        try:
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                script = yaml.safe_load(f)
            elements = []
            for ch in script.get("script", {}).get("chapters", []):
                for scene in ch.get("scenes", []):
                    elements.extend(scene.get("elements", []))
            return elements
        except Exception:
            return []

    def _get_default_references(self) -> list:
        """获取默认参考"""
        from skills.script_writing import ScriptWritingSkill
        skill = ScriptWritingSkill()
        return skill.retrieve_references(query="开场 冲突 高潮", top_k=5)

    def _llm_deep_comparison(
        self,
        elements: list,
        references: list,
        comparison: dict,
    ) -> dict:
        """LLM 深度对比分析"""
        metrics = comparison.get("current_metrics", {})
        ref_names = [r.get("title", "?") for r in references]

        prompt = f"""你是剧本评审专家。以下是当前剧本与爆款参考的对比数据：

当前剧本指标:
- 开场力度: {metrics.get('opening_impact', '?')}/10
- 冲突密度: {metrics.get('conflict_density', '?')}/10
- 对白犀利度: {metrics.get('dialogue_sharpness', '?')}/10
- 节奏感: {metrics.get('pacing', '?')}/10
- 钩子质量: {metrics.get('hook_quality', '?')}/10
- 角色魅力: {metrics.get('character_appeal', '?')}/10

对比参考: {', '.join(ref_names)}
总体评估: {comparison.get('overall_assessment', '')}

请给出：
1. 与每个参考剧本相比，当前剧本最需要补强的 2 个维度
2. 具体的追赶建议
3. 可以"弯道超车"的差异化优势方向

输出 JSON:
{{
  "weakest_dimensions": ["维度1", "维度2"],
  "improvement_plan": "具体追赶计划",
  "differentiation_strategy": "差异化策略",
  "target_score": {{"dimension": score}}
}}"""

        try:
            result = self.call_llm(prompt, use_light=False, expect_json=True)
            return result if isinstance(result, dict) else {}
        except Exception as e:
            self.log(f"LLM 对比失败: {e}", level="warning")
            return {}

    def _generate_report(
        self,
        episode: int,
        comparison: dict,
        llm_details: dict,
    ) -> str:
        """生成对比报告"""
        report = []
        report.append(f"# 剧本对比报告 — 第{episode}集\n")
        report.append(f"**对比时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append(f"**总体评估**: {comparison.get('overall_assessment', '')}\n")
        report.append("---\n")

        # 当前指标
        metrics = comparison.get("current_metrics", {})
        report.append("## 1. 当前剧本质量指标\n")
        metric_labels = {
            "opening_impact": "开场力度",
            "conflict_density": "冲突密度",
            "dialogue_sharpness": "对白犀利度",
            "pacing": "节奏感",
            "hook_quality": "钩子质量",
            "character_appeal": "角色魅力",
        }
        for key, label in metric_labels.items():
            score = metrics.get(key, "?")
            bar = "█" * int(float(score)) + "░" * (10 - int(float(score)))
            report.append(f"- **{label}**: {bar} {score}/10")
        report.append("")

        # 逐一对比
        report.append("## 2. 逐一对比详情\n")
        for comp in comparison.get("comparisons", []):
            ref_title = comp.get("reference_title", "?")
            avg_gap = comp.get("average_gap", 0)
            report.append(f"### vs 《{ref_title}》— 平均差距 {avg_gap:+.1f}\n")

            for dim_key, dim_data in comp.get("dimensions", {}).items():
                name = dim_data.get("dimension", dim_key)
                current = dim_data.get("current", "?")
                ref = dim_data.get("reference", "?")
                gap = dim_data.get("gap", 0)
                status = dim_data.get("status", "?")
                icon = {"above": "🟢", "on_par": "🟡", "below": "🔴"}.get(status, "⚪")
                report.append(f"| {icon} {name} | 当前 {current} | 参考 {ref} | 差距 {gap:+.1f} |")
            report.append("")

        # LLM 洞察
        if llm_details:
            report.append("---\n")
            report.append("## 3. AI 深度分析\n")
            if llm_details.get("improvement_plan"):
                report.append(f"### 追赶计划\n{llm_details['improvement_plan']}\n")
            if llm_details.get("differentiation_strategy"):
                report.append(f"### 差异化策略\n{llm_details['differentiation_strategy']}\n")
            weakest = llm_details.get("weakest_dimensions", [])
            if weakest:
                report.append(f"### 最需补强维度\n")
                for w in weakest:
                    report.append(f"- {w}")

        return "\n".join(report)


def create_script_comparator(config: dict = None, **kwargs) -> ScriptComparator:
    return ScriptComparator(config=config, **kwargs)
