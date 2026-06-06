"""
剧本写手 Agent — Phase 3: 剧本生成 (~write N)

职责:
  - 爆款参考检索，注入生成上下文
  - 基于分集大纲生成完整剧本元素 (Schema v2.0)
  - 支持 Show Don't Tell 转换
  - 回改机制（根据审核反馈修改）
  - 产出 scripts/ep{N:02d}_script.yaml

使用:
  agent = ScriptWriter(config)
  result = agent.execute(episode=1, episode_plan=..., all_elements=...)
"""

import os
from datetime import datetime

from .base_agent import BaseAgent


class ScriptWriter(BaseAgent):
    """剧本写手 Agent — 逐集生成完整剧本"""

    agent_name = "script-writer"
    agent_display_name = "剧本写手"
    agent_description = "基于分集大纲生成完整剧本，融合爆款参考和影视化技巧"
    phase = "write"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from skills.script_writing import ScriptWritingSkill
        self.skill = ScriptWritingSkill(
            hit_scripts_dir=self.get_config(
                "knowledge.hit_scripts_dir", "./knowledge/hit_scripts"
            )
        )

    def execute(
        self,
        episode: int = 1,
        episode_plan: list = None,
        all_elements: list = None,
        character_tracker=None,
        script_builder=None,
        state_manager=None,
        revision_round: int = 0,
        review_feedback: dict = None,
        use_llm: bool = True,
        **kwargs,
    ) -> dict:
        """
        生成单集剧本。

        Args:
            episode: 集数
            episode_plan: 分集规划（来自 episode_architect）
            all_elements: 所有章节的结构化元素
            character_tracker: CharacterTracker 实例
            script_builder: ScriptBuilder 实例
            state_manager: AgentStateManager 实例
            revision_round: 回改轮次（0=初稿）
            review_feedback: 审核反馈（回改时使用）
            use_llm: 是否使用 LLM

        Returns:
            {status, script_yaml, script_path, episode, revision_round, ...}
        """
        self.state_manager = state_manager or self.state_manager
        self.log(f"生成第{episode}集剧本 (第{revision_round}轮)")

        # Step 1: 获取该集的规划信息
        ep_plan = self._get_episode_plan(episode, episode_plan)
        if not ep_plan:
            return {"status": "failed", "error": f"找不到第{episode}集的分集规划"}

        # Step 2: 收集该集对应的元素
        ep_elements = self._filter_elements_for_episode(
            all_elements or [], ep_plan
        )

        self.log(f"收集到 {len(ep_elements)} 个元素 (覆盖章节 {ep_plan.get('chapter_ids', [])})")

        # Step 3: 检索爆款参考
        self.log("检索爆款参考...")
        references = self._retrieve_references(ep_plan, ep_elements)

        # Step 4: 风格分析
        self.log("分析文本风格...")
        style = self.skill.analyze_style(ep_elements)

        # Step 5: 生成剧本（LLM）
        if use_llm:
            self.log("LLM 生成剧本...")
            script_elements = self._llm_generate_script(
                episode=episode,
                ep_plan=ep_plan,
                elements=ep_elements,
                references=references,
                style=style,
                feedback=review_feedback,
                character_tracker=character_tracker,
            )
        else:
            # 无 LLM：直接用原始元素
            script_elements = ep_elements

        # Step 6: Show Don't Tell 转换
        self.log("Show Don't Tell 转换...")
        script_elements = self._apply_show_dont_tell(script_elements)

        # Step 7: 构建 Schema v2.0 剧本
        self.log("构建 YAML 剧本...")
        script_yaml = self._build_script(
            episode=episode,
            ep_plan=ep_plan,
            elements=script_elements,
            character_tracker=character_tracker,
            script_builder=script_builder,
            references=references,
            style=style,
            revision_round=revision_round,
        )

        # Step 8: 保存
        output_dir = self.get_config("output.output_dir", "./output")
        project_name = self.state_manager.project_name if self.state_manager else "untitled"
        full_output_dir = os.path.join(output_dir, project_name)
        os.makedirs(os.path.join(full_output_dir, "scripts"), exist_ok=True)

        script_filename = f"ep{episode:02d}_script.yaml"
        if revision_round > 0:
            script_filename = f"ep{episode:02d}_script_r{revision_round}.yaml"
        script_path = os.path.join(full_output_dir, "scripts", script_filename)

        if script_builder:
            script_builder.save(script_yaml, script_path)
        else:
            self._save_script_raw(script_yaml, script_path)

        self.save_state(f"last_write_ep{episode}", {
            "timestamp": datetime.now().isoformat(),
            "episode": episode,
            "revision_round": revision_round,
            "elements_count": len(script_elements),
            "script_path": script_path,
        })

        self.log(f"第{episode}集剧本生成完成 → {script_path}")

        return {
            "status": "completed",
            "episode": episode,
            "revision_round": revision_round,
            "element_count": len(script_elements),
            "script": script_yaml,
            "script_path": script_path,
            "references_used": [r["title"] for r in references[:3]],
            "style": style,
            "message": (
                f"第{episode}集剧本生成完成 ({len(script_elements)} 个元素, "
                f"参考 {len(references)} 个爆款剧本)"
            ),
        }

    # ═══════════════════════════════════════════════════════════

    def _get_episode_plan(self, episode: int, episode_plan: list) -> dict:
        """从分集规划中获取该集信息"""
        if not episode_plan:
            return {}
        for ep in episode_plan:
            if ep.get("episode_id") == episode:
                return ep
        return {}

    def _filter_elements_for_episode(
        self, all_elements: list, ep_plan: dict
    ) -> list:
        """筛选属于该集的元素"""
        chapter_ids = set(ep_plan.get("chapter_ids", []))
        if not chapter_ids:
            return all_elements
        return [
            e for e in all_elements
            if e.get("chapter_id") in chapter_ids
        ]

    def _retrieve_references(
        self, ep_plan: dict, elements: list
    ) -> list[dict]:
        """检索爆款参考"""
        # 构建查询
        query_parts = []
        if ep_plan.get("core_conflict"):
            query_parts.append(ep_plan["core_conflict"])
        if ep_plan.get("emotional_beat"):
            query_parts.append(ep_plan["emotional_beat"])

        # 从元素中提取关键场景
        key_elements = [
            e for e in elements
            if e.get("beat_type") in ("confrontation", "revelation", "payoff")
        ]
        for e in key_elements[:3]:
            query_parts.append(e.get("text", "")[:50])

        query = " ".join(query_parts) if query_parts else "开场 冲突 高潮"

        return self.skill.retrieve_references(
            query=query,
            top_k=self.get_config("pipeline.reference_script_count", 5),
        )

    def _apply_show_dont_tell(self, elements: list) -> list:
        """对元素应用 Show Don't Tell 转换"""
        for elem in elements:
            text = elem.get("text", "")
            if text and len(text) > 20:
                result = self.skill.convert_show_dont_tell(text)
                if result["has_changes"]:
                    elem["text"] = result["converted"]
                    # 将原文本保存为注释
                    if result["original"] != result["converted"]:
                        elem["original_text"] = result["original"]
        return elements

    def _build_script(
        self,
        episode: int,
        ep_plan: dict,
        elements: list,
        character_tracker=None,
        script_builder=None,
        references: list = None,
        style: dict = None,
        revision_round: int = 0,
    ) -> dict:
        """使用 ScriptBuilder 构建 Schema v2.0 剧本"""
        if script_builder:
            # 使用 ScriptBuilder 的完整管线
            script = script_builder.build(
                all_elements=elements,
                character_tracker=character_tracker,
            )
            # 添加本集特有信息
            script["script"]["metadata"]["revision_round"] = revision_round
            if ep_plan.get("logline"):
                script["script"]["metadata"]["episode_logline"] = ep_plan["logline"]
            return script

        # Fallback: 手动构建简化版
        return self._build_script_manual(
            episode=episode,
            ep_plan=ep_plan,
            elements=elements,
            references=references,
            style=style,
            revision_round=revision_round,
        )

    def _build_script_manual(
        self,
        episode: int,
        ep_plan: dict,
        elements: list,
        references: list = None,
        style: dict = None,
        revision_round: int = 0,
    ) -> dict:
        """手动构建剧本（无 ScriptBuilder 时的 fallback）"""
        from builders.schema_v2 import create_skeleton_script

        script = create_skeleton_script()
        meta = script["script"]["metadata"]
        meta["total_chapters_adapted"] = ep_plan.get("chapter_count", 0)
        meta["adapted_chapter_ids"] = ep_plan.get("chapter_ids", [])
        meta["revision_round"] = revision_round

        # 将元素分场景
        scenes = self.skill.elements_to_scene_script(
            elements=elements,
            scene_id=f"{episode}.1",
            characters_present=list(set(
                e.get("role", "") for e in elements
                if e.get("role") and e.get("role") != "旁白"
            )),
        )

        script["script"]["chapters"] = [{
            "chapter_id": episode,
            "chapter_title": ep_plan.get("episode_title_hint", f"第{episode}集"),
            "source_chapter": ep_plan.get("start_chapter", episode),
            "summary": ep_plan.get("logline", ""),
            "scene_count": 1,
            "element_count": len(elements),
            "scenes": [scenes],
        }]

        return script

    def _save_script_raw(self, script: dict, path: str):
        """保存剧本为 YAML（无 ScriptBuilder 时）"""
        import yaml
        header = (
            f"# Novel-to-Script Pro v2.0\n"
            f"# 生成时间: {datetime.now().isoformat()}\n"
            f"# Schema: 2.0\n\n"
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(header)
            yaml.dump(script, f, allow_unicode=True, default_flow_style=False,
                      sort_keys=False, indent=2)

    # ═══════════════════════════════════════════════════════════
    # LLM 剧本生成
    # ═══════════════════════════════════════════════════════════

    def _llm_generate_script(
        self,
        episode: int,
        ep_plan: dict,
        elements: list,
        references: list,
        style: dict,
        feedback: dict = None,
        character_tracker=None,
    ) -> list:
        """使用 LLM 生成/增强剧本元素"""
        # 构建上下文
        context = self._build_generation_context(
            episode, ep_plan, elements, references, style, feedback, character_tracker
        )

        prompt = f"""你是一位资深影视编剧。请基于以下信息，生成第{episode}集的剧本元素。

{context}

要求：
1. 保留原文的核心情节和角色
2. 对白要有潜台词（subtext），不要直白表达情感
3. 动作描写要具体可拍，每一个"心里想"都要转化为外部表现
4. 标注每个元素的 beat_type（setup/confrontation/payoff/transition/revelation）
5. 为关键场景提供 visual_hint（镜头建议）

请以 JSON 数组格式输出剧本元素，每个元素包含：
- type: dialogue/narration/action/description
- role: 角色名或"旁白"
- text: 内容文本
- emotion: 情绪标签
- action: 动作描述
- subtext: 潜台词（仅 dialogue）
- beat_type: 节拍类型
- visual_hint: 视觉化提示

这是第{revision_round if feedback else 0}轮{'回改' if feedback else '初稿'}。
{f'修改要求: {feedback.get("suggestions", "")}' if feedback else ''}"""

        try:
            result = self.call_llm(prompt, use_light=False, expect_json=True, max_tokens=16384)
            if isinstance(result, list) and len(result) > 0:
                # 标注集数
                for i, elem in enumerate(result):
                    elem["episode_id"] = episode
                    elem["global_id"] = i + 1
                return result
        except Exception as e:
            self.log(f"LLM 生成失败，使用原始元素: {e}", level="warning")

        return elements  # Fallback

    def _build_generation_context(
        self,
        episode: int,
        ep_plan: dict,
        elements: list,
        references: list,
        style: dict,
        feedback: dict = None,
        character_tracker=None,
    ) -> str:
        """构建 LLM 剧本生成的上下文"""
        parts = []

        # 分集规划
        parts.append(f"## 分集规划")
        parts.append(f"- 集数: 第{episode}集")
        parts.append(f"- 标题: {ep_plan.get('episode_title_hint', '未命名')}")
        parts.append(f"- 一句话梗概: {ep_plan.get('logline', '无')}")
        parts.append(f"- 核心冲突: {ep_plan.get('core_conflict', '无')}")
        parts.append(f"- 角色重点: {ep_plan.get('character_focus', '无')}")
        parts.append(f"- 幕结构: {ep_plan.get('act_structure', '无')}")
        parts.append("")

        # 源材料元素（取关键部分）
        parts.append(f"## 源材料 ({len(elements)} 个元素)")
        # 只取前30个关键元素作为示例
        sample = elements[:30]
        for e in sample:
            role = e.get("role", "")
            text = e.get("text", "")[:100]
            beat = e.get("beat_type", "")
            parts.append(f"[{e.get('type', '?')}|{beat}] {role}: {text}")
        if len(elements) > 30:
            parts.append(f"... (还有 {len(elements) - 30} 个元素)")
        parts.append("")

        # 爆款参考
        if references:
            parts.append(f"## 爆款参考 ({len(references)} 个)")
            for i, ref in enumerate(references[:3], 1):
                parts.append(f"{i}. 《{ref['title']}》 [{ref.get('scene_type', '')}]")
                parts.append(f"   {ref.get('content', '')[:150]}")
                if ref.get("notes"):
                    parts.append(f"   💡 {ref['notes']}")
            parts.append("")

        # 风格分析
        if style:
            parts.append(f"## 风格分析")
            parts.append(f"- 风格类型: {style.get('style_category', '未知')}")
            for s in style.get("suggestions", [])[:3]:
                parts.append(f"- ⚠️ {s}")
            parts.append("")

        # 角色信息
        if character_tracker:
            chars = character_tracker.get_all_characters()
            if chars:
                parts.append(f"## 角色档案")
                for c in chars[:8]:
                    parts.append(
                        f"- {c.get('name', '?')} [{c.get('role_type', '?')}]: "
                        f"{c.get('description', '')[:80]}"
                    )
                parts.append("")

        return "\n".join(parts)


def create_script_writer(config: dict = None, **kwargs) -> ScriptWriter:
    """创建剧本写手 Agent 实例"""
    return ScriptWriter(config=config, **kwargs)
