"""
审核导演 Agent — Phase 4: 多维度审核 (~review N)

职责:
  - 业务审核：情节逻辑、人物一致性、节奏、对白质量
  - 合规审核：内容安全、平台规范、敏感词
  - 对比审核：与参考剧本的质量差距
  - FAIL/REVISE 时回写具体修改建议
  - 产出 review/review-ep{N:02d}.md

使用:
  agent = ReviewDirector(config)
  result = agent.execute(episode=1, script_elements=..., script_path=...)
"""

import os
from datetime import datetime

from .base_agent import BaseAgent


class ReviewDirector(BaseAgent):
    """审核导演 Agent — 多维度审核与修改建议"""

    agent_name = "review-director"
    agent_display_name = "审核导演"
    agent_description = "对剧本进行业务审核、合规审核、对比审核，给出 PASS/FAIL/REVISE 判定"
    phase = "review"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from skills.review_skills import (
            ScriptReviewSkill,
            ComplianceReviewSkill,
            ComparativeReviewSkill,
        )
        self.script_review = ScriptReviewSkill()
        self.compliance_review = ComplianceReviewSkill()
        self.comparative_review = ComparativeReviewSkill()

    def execute(
        self,
        episode: int = 1,
        script_elements: list = None,
        script_path: str = None,
        references: list = None,
        state_manager=None,
        schema_validator=None,
        use_llm: bool = True,
        **kwargs,
    ) -> dict:
        """
        执行多维度审核。

        Args:
            episode: 集数
            script_elements: 剧本元素列表
            script_path: 剧本 YAML 路径（备选）
            references: 爆款参考列表
            state_manager: AgentStateManager 实例
            schema_validator: SchemaValidator 实例
            use_llm: 是否使用 LLM 增强

        Returns:
            {status, passed, verdict, review_report_path, ...}
        """
        self.state_manager = state_manager or self.state_manager

        # 加载剧本
        if script_elements is None and script_path:
            script_elements = self._load_elements(script_path)
        script_elements = script_elements or []

        self.log(f"审核第{episode}集: {len(script_elements)} 个元素")

        # Step 1: Schema 校验
        schema_issues = []
        if schema_validator and script_path:
            self.log("Schema 校验...")
            try:
                import yaml
                with open(script_path, "r", encoding="utf-8") as f:
                    script = yaml.safe_load(f)
                is_valid, errors, warnings = schema_validator.validate(script)
                schema_issues = [{"type": "schema_error", "detail": e} for e in errors]
                schema_issues += [{"type": "schema_warning", "detail": w} for w in warnings]
            except Exception as e:
                schema_issues.append({"type": "schema_error", "detail": str(e)})

        # Step 2: 业务审核
        self.log("业务审核...")
        business_result = self.script_review.review(script_elements)

        # Step 3: 合规审核
        self.log("合规审核...")
        all_text = " ".join(e.get("text", "") for e in script_elements)
        target_platform = self.get_config("compliance.target_platform", "generic")
        compliance_result = self.compliance_review.check(all_text, target_platform)

        # Step 4: 对比审核
        comparison_result = {}
        if references:
            self.log(f"对比审核 ({len(references)} 个参考)...")
            comparison_result = self.comparative_review.compare(
                script_elements, references
            )

        # Step 5: LLM 增强审核
        llm_insights = {}
        if use_llm:
            self.log("LLM 增强审核...")
            llm_insights = self._llm_enhanced_review(
                script_elements, business_result, compliance_result
            )

        # Step 6: 综合判定
        overall_verdict = self._final_verdict(
            business_result, compliance_result, schema_issues
        )

        # Step 7: 生成审核报告
        report = self._generate_report(
            episode=episode,
            business=business_result,
            compliance=compliance_result,
            comparison=comparison_result,
            schema_issues=schema_issues,
            llm_insights=llm_insights,
            verdict=overall_verdict,
        )

        # 保存报告
        output_dir = self.get_config("output.output_dir", "./output")
        project_name = self.state_manager.project_name if self.state_manager else "untitled"
        full_output_dir = os.path.join(output_dir, project_name)
        os.makedirs(os.path.join(full_output_dir, "review"), exist_ok=True)
        report_path = os.path.join(
            full_output_dir, "review", f"review-ep{episode:02d}.md"
        )

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        self.save_state(f"last_review_ep{episode}", {
            "timestamp": datetime.now().isoformat(),
            "episode": episode,
            "verdict": overall_verdict["verdict"],
            "business_score": business_result.get("overall_score", 0),
        })

        self.log(
            f"审核完成: {overall_verdict['verdict']} "
            f"(业务{business_result.get('overall_score', 0)}/10, "
            f"问题{business_result.get('issue_count', 0)}个)"
        )

        return {
            "status": "completed",
            "episode": episode,
            "passed": overall_verdict["verdict"] == "PASS",
            "verdict": overall_verdict["verdict"],
            "business_score": business_result.get("overall_score", 0),
            "business_issues": business_result.get("issue_count", 0),
            "compliance_passed": compliance_result.get("passed", True),
            "compliance_risk": compliance_result.get("risk_level", "low"),
            "schema_issues": len(schema_issues),
            "review_report_path": report_path,
            "suggestions": business_result.get("suggestions", []),
            "verdict_detail": overall_verdict,
            "message": (
                f"第{episode}集审核: {overall_verdict['verdict']} "
                f"(业务{business_result.get('overall_score', 0)}/10, "
                f"合规{'通过' if compliance_result.get('passed') else '不通过'})"
            ),
        }

    def _load_elements(self, path: str) -> list:
        """从 YAML 加载元素"""
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

    def _final_verdict(
        self, business: dict, compliance: dict, schema_issues: list
    ) -> dict:
        """综合判定"""
        reasons = []

        b_score = business.get("overall_score", 0)
        b_verdict = business.get("verdict", "PASS")
        c_passed = compliance.get("passed", True)
        c_risk = compliance.get("risk_level", "low")
        schema_ok = len(schema_issues) == 0

        if not schema_ok:
            reasons.append(f"Schema 校验发现 {len(schema_issues)} 个问题")
        if b_verdict == "FAIL":
            reasons.append(f"业务审核不通过 (评分 {b_score}/10)")
        elif b_verdict == "REVISE":
            reasons.append(f"业务审核需修改 (评分 {b_score}/10)")
        if not c_passed:
            reasons.append(f"合规审核不通过 (风险: {c_risk})")

        if not reasons:
            return {"verdict": "PASS", "reasons": ["所有检查通过"]}
        elif b_verdict == "FAIL" or not c_passed:
            return {"verdict": "FAIL", "reasons": reasons}
        else:
            return {"verdict": "REVISE", "reasons": reasons}

    def _llm_enhanced_review(
        self, elements: list, business: dict, compliance: dict
    ) -> dict:
        """LLM 增强审核"""
        if not elements:
            return {}

        # 选取关键问题上下文
        issue_texts = "\n".join(
            f"- [{i.get('severity', '?')}] {i.get('description', '')}"
            for i in business.get("issues", [])[:10]
        )

        text_sample = "\n".join(
            f"[{e.get('type', '?')}] {e.get('role', '?')}: {e.get('text', '')[:80]}"
            for e in elements[:15]
        )

        prompt = f"""你是剧本审核专家。基于以下信息给出专业评审意见。

剧本片段:
{text_sample}

已发现的规则问题:
{issue_texts}

当前业务评分: {business.get('overall_score', 0)}/10

请从专业编剧角度给出:
1. 最需要优先解决的 3 个问题
2. 每集的节奏建议
3. 一句总结评价

输出 JSON:
{{
  "top_priorities": ["问题1", "问题2", "问题3"],
  "pacing_advice": "节奏建议",
  "one_line_verdict": "一句话评价"
}}"""

        try:
            result = self.call_llm(prompt, use_light=False, expect_json=True)
            return result if isinstance(result, dict) else {}
        except Exception as e:
            self.log(f"LLM 审核失败: {e}", level="warning")
            return {}

    def _generate_report(
        self,
        episode: int,
        business: dict,
        compliance: dict,
        comparison: dict,
        schema_issues: list,
        llm_insights: dict,
        verdict: dict,
    ) -> str:
        """生成审核报告"""
        report = []
        report.append(f"# 审核报告 — 第{episode}集\n")
        report.append(f"**审核时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append(f"**审核工具**: Novel-to-Script Pro v2.0 — Review Director\n")
        report.append(f"## 综合判定: {verdict['verdict']}\n")
        for r in verdict.get("reasons", []):
            report.append(f"- {r}")
        report.append("\n---\n")

        # 业务审核
        report.append("## 1. 业务审核\n")
        report.append(f"**综合评分**: {business.get('overall_score', '?')}/10\n")
        for dim_key, dim_info in [
            ("plot_logic", "情节逻辑"),
            ("character_consistency", "人物一致性"),
            ("pacing", "节奏把控"),
            ("dialogue_quality", "对白质量"),
            ("visual_potential", "视觉潜力"),
            ("emotional_impact", "情感冲击"),
            ("hook_quality", "悬念钩子"),
        ]:
            dim_data = business.get("dimensions", {}).get(dim_key, {})
            score = dim_data.get("score", "?")
            report.append(f"- **{dim_info}**: {score}/10")

        issues = business.get("issues", [])
        if issues:
            report.append(f"\n### 发现的问题 ({len(issues)} 个)\n")
            for i, issue in enumerate(issues, 1):
                severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    issue.get("severity", ""), "⚪"
                )
                report.append(f"{i}. {severity_icon} **[{issue.get('type', '?')}]** "
                             f"{issue.get('description', '')}")

        suggestions = business.get("suggestions", [])
        if suggestions:
            report.append(f"\n### 修改建议\n")
            for s in suggestions[:10]:
                report.append(f"- {s}")

        report.append("\n---\n")

        # 合规审核
        report.append("## 2. 合规审核\n")
        report.append(f"- **状态**: {'✅ 通过' if compliance.get('passed') else '❌ 不通过'}")
        report.append(f"- **风险等级**: {compliance.get('risk_level', '?')}")

        c_issues = compliance.get("issues", [])
        if c_issues:
            report.append(f"\n### 合规问题 ({len(c_issues)} 个)\n")
            for i, issue in enumerate(c_issues, 1):
                report.append(f"{i}. **[{issue.get('category', '?')}]** "
                             f"{issue.get('description', '')}")

        report.append("\n---\n")

        # 对比审核
        if comparison:
            report.append("## 3. 对比审核\n")
            report.append(f"**总体评估**: {comparison.get('overall_assessment', '')}\n")
            for comp in comparison.get("comparisons", []):
                report.append(f"### vs 《{comp.get('reference_title', '?')}》")
                report.append(f"平均差距: {comp.get('average_gap', 0):+.1f}\n")
                for dim_key, dim_data in comp.get("dimensions", {}).items():
                    dim_name = dim_data.get("dimension", dim_key)
                    current = dim_data.get("current", "?")
                    ref = dim_data.get("reference", "?")
                    gap = dim_data.get("gap", 0)
                    status = dim_data.get("status", "?")
                    icon = {"above": "🟢", "on_par": "🟡", "below": "🔴"}.get(status, "⚪")
                    report.append(f"- {icon} **{dim_name}**: {current} vs {ref} (差距 {gap:+.1f})")
                report.append("")

        # Schema 问题
        if schema_issues:
            report.append("\n---\n")
            report.append(f"## 4. Schema 校验 ({len(schema_issues)} 个问题)\n")
            for issue in schema_issues[:20]:
                report.append(f"- {issue.get('detail', str(issue))}")

        # LLM 洞察
        if llm_insights:
            report.append("\n---\n")
            report.append("## 5. AI 评审意见\n")
            if llm_insights.get("one_line_verdict"):
                report.append(f"> {llm_insights['one_line_verdict']}\n")
            if llm_insights.get("pacing_advice"):
                report.append(f"**节奏建议**: {llm_insights['pacing_advice']}\n")
            priorities = llm_insights.get("top_priorities", [])
            if priorities:
                report.append("**优先解决**:")
                for p in priorities:
                    report.append(f"- {p}")

        return "\n".join(report)


def create_review_director(config: dict = None, **kwargs) -> ReviewDirector:
    """创建审核导演 Agent 实例"""
    return ReviewDirector(config=config, **kwargs)
