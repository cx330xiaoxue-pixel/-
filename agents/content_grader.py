"""
内容分级 Agent — 对提取元素进行 S/A/B 三级智能分拣

职责:
  - 包装 ContentGradingSkill 为管线 Agent
  - 规则引擎快速分拣 + LLM 边界案例复核
  - 支持 strict / balanced / loose 三种适应度模式
  - 产出分级统计和过滤后元素列表

使用:
  agent = ContentGrader(config)
  result = agent.execute(elements=elements, mode="balanced", character_network={...})
"""

import json
import os
from datetime import datetime
from typing import Optional

from .base_agent import BaseAgent


class ContentGrader(BaseAgent):
    """内容分级 Agent — S/A/B 三级权重分拣"""

    agent_name = "content-grader"
    agent_display_name = "内容分级师"
    agent_description = "对小说提取元素进行S/A/B三级权重分拣，过滤冗余、压缩辅助、保留核心"
    phase = "write"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from skills.content_grading import ContentGradingSkill
        self.skill = ContentGradingSkill()

    def execute(
        self,
        elements: list[dict] = None,
        mode: str = "balanced",
        character_network: dict = None,
        chapter_boundaries: list = None,
        use_llm: bool = True,
        state_manager=None,
        **kwargs,
    ) -> dict:
        """
        执行内容分级。

        Args:
            elements: 提取的结构化元素列表
            mode: 适应度模式 strict | balanced | loose
            character_network: 角色网络分析结果（含 main_characters）
            chapter_boundaries: 章节边界索引
            use_llm: 是否使用 LLM 复核边界案例
            state_manager: AgentStateManager 实例

        Returns:
            {status, graded_elements, stats, filtered_count, ...}
        """
        self.state_manager = state_manager or self.state_manager

        if not elements:
            return {"status": "failed", "error": "未提供元素列表"}

        # 从 config 获取默认模式
        if not mode:
            mode = self.get_config("content_grading.mode", "balanced")

        self.log(f"开始内容分级: {len(elements)} 个元素, 模式={mode}")

        # Step 1: 构建角色重要性映射
        character_importance = self._build_character_importance(
            character_network, elements
        )

        # Step 2: 规则引擎分拣
        self.log("规则引擎分拣中...")
        graded = self.skill.grade_elements(
            elements=elements,
            mode=mode,
            character_importance=character_importance,
            chapter_boundaries=chapter_boundaries,
        )

        # Step 3: LLM 复核边界案例（置信度低的）
        borderline = [
            e for e in graded
            if 0.3 < e.get("grade_confidence", 1.0) < 0.6
        ]
        if use_llm and borderline:
            self.log(f"LLM 复核 {len(borderline)} 个边界案例...")
            resolved = self._llm_resolve_ambiguous(borderline, mode)
            # 用LLM结果更新边界案例
            for i, elem in enumerate(graded):
                if elem in borderline:
                    resolved_grade = resolved.get(
                        str(elem.get("global_id", i)), None
                    )
                    if resolved_grade:
                        elem["content_grade"] = resolved_grade["grade"]
                        elem["grade_confidence"] = resolved_grade["confidence"]
                        elem["llm_reviewed"] = True

        # Step 4: 应用分级（过滤/压缩）
        max_chars = self.get_config(
            "content_grading.max_merged_narration_chars", 50
        )
        processed = self.skill.apply_grading_to_elements(
            graded, mode=mode, max_merged_chars=max_chars
        )

        # Step 5: 生成统计
        stats = self.skill.get_grading_report(graded)
        filtered_count = len(elements) - len(processed)

        self.log(
            f"分级完成: S={stats['S_count']}, A={stats['A_count']}, "
            f"B={stats['B_count']} | 过滤/合并 {filtered_count} 个元素"
        )

        # 保存状态
        self.save_state("last_grading", {
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "total_elements": len(elements),
            "stats": stats,
            "filtered_count": filtered_count,
        })

        return {
            "status": "completed",
            "mode": mode,
            "total_elements": len(elements),
            "graded_elements": graded,
            "processed_elements": processed,
            "stats": stats,
            "filtered_count": filtered_count,
            "condensed_count": stats["A_count"],
            "preserved_count": stats["S_count"],
            "message": (
                f"内容分级完成: 保留 {stats['S_count']} 个核心元素, "
                f"压缩 {stats['A_count']} 个辅助元素, "
                f"过滤 {filtered_count} 个冗余元素 "
                f"(模式: {mode})"
            ),
        }

    # ═══════════════════════════════════════════════════════════

    def _build_character_importance(
        self,
        character_network: dict,
        elements: list,
    ) -> dict[str, float]:
        """
        从角色网络分析结果构建角色重要性映射。

        主角 = 1.0, 重要配角 = 0.7, 配角 = 0.4, 龙套 = 0.1
        """
        importance = {}

        if character_network:
            main_chars = character_network.get("main_characters", [])
            if main_chars:
                # 第一个主角
                importance[main_chars[0]["name"]] = 1.0
                # 第二第三个重要角色
                for ch in main_chars[1:3]:
                    importance[ch["name"]] = 0.7
                # 其余
                for ch in main_chars[3:]:
                    importance[ch["name"]] = 0.4

        # 从元素中补充未覆盖的角色
        from collections import Counter
        role_counts = Counter()
        for elem in elements:
            role = elem.get("role", "").strip()
            if role and role != "旁白":
                role_counts[role] += 1

        total = sum(role_counts.values()) or 1
        for role, count in role_counts.most_common(20):
            if role not in importance:
                share = count / total
                if share > 0.1:
                    importance[role] = 0.6
                elif share > 0.05:
                    importance[role] = 0.4
                else:
                    importance[role] = 0.2

        return importance

    def _llm_resolve_ambiguous(
        self,
        borderline_elements: list[dict],
        mode: str,
    ) -> dict:
        """使用 LLM 对边界案例进行二次判定"""
        if not borderline_elements:
            return {}

        # 构建 LLM prompt
        items_text = []
        for elem in borderline_elements[:20]:  # 最多处理20个
            items_text.append(
                f"ID:{elem.get('global_id', '?')} | "
                f"Type:{elem.get('type','?')} | "
                f"Beat:{elem.get('beat_type','?')} | "
                f"Role:{elem.get('role','?')} | "
                f"Score:{elem.get('grade_score',0):.2f} | "
                f"Text:{elem.get('text','')[:150]}"
            )

        prompt = f"""你是剧本分析专家。请对以下边界案例进行最终分级（S/A/B）。

当前适应度模式: {mode}
- S级 = 核心剧情（冲突、关键对话、动作、转折）
- A级 = 辅助剧情（环境、神态、设定铺垫）
- B级 = 冗余内容（重复、无意义心理、灌水）

待判定的边界案例:
{chr(10).join(items_text)}

请输出JSON:
{{
  "decisions": [
    {{"id": "元素ID", "grade": "S|A|B", "confidence": 0.0-1.0, "reason": "判定理由"}}
  ]
}}"""

        try:
            result = self.call_llm(
                prompt=prompt,
                use_light=True,
                expect_json=True,
            )
            if isinstance(result, dict):
                decisions = result.get("decisions", [])
                return {
                    str(d["id"]): {"grade": d["grade"],
                                   "confidence": d["confidence"]}
                    for d in decisions
                }
        except Exception as e:
            self.log(f"LLM 边界复核失败: {e}", level="warning")

        return {}


def create_content_grader(config: dict = None, **kwargs) -> ContentGrader:
    """创建内容分级 Agent 实例"""
    return ContentGrader(config=config, **kwargs)
