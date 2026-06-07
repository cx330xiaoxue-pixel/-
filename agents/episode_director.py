"""
影视导演 Agent — 智能分集规划与剧集结构设计（升级版分集架构师）

职责:
  - 整合冲突分析 + 影视节奏引擎
  - 智能拆分/合并小说章节，适配不同影视格式
  - 生成每集的开篇钩子、中段冲突、结尾悬念
  - 标注核心看点、剧情伏笔、招商审核参考备注
  - 替代简单比例映射的 EpisodeArchitect

与 EpisodeArchitect 的区别:
  - EpisodeArchitect: 简单比例映射（ch_count / target_eps）
  - EpisodeDirector: 基于冲突节点的智能拆分 + 剧集结构设计

使用:
  agent = EpisodeDirector(config)
  result = agent.execute(chapters=..., elements=..., target_format="long_drama")
"""

import json
import os
from datetime import datetime
from typing import Optional

from .base_agent import BaseAgent


class EpisodeDirector(BaseAgent):
    """影视导演 Agent — 智能分集与剧集结构设计"""

    agent_name = "episode-director"
    agent_display_name = "影视导演"
    agent_description = "基于冲突节点智能拆分章节，适配影视节奏，生成剧集钩子/冲突/悬念/看点/伏笔"
    phase = "plan"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from skills.conflict_analyzer import ConflictAnalyzerSkill
        from skills.episode_rhythm import EpisodeRhythmSkill
        self.conflict_analyzer = ConflictAnalyzerSkill()
        self.rhythm_engine = EpisodeRhythmSkill()

    def execute(
        self,
        chapters: list[dict] = None,
        elements: list[dict] = None,
        target_format: str = "long_drama",
        target_episodes: int = None,
        adaptation_mode: str = "balanced",
        cliffhanger_required: bool = True,
        generate_investor_notes: bool = True,
        use_llm: bool = True,
        state_manager=None,
        **kwargs,
    ) -> dict:
        """
        执行智能分集规划。

        Args:
            chapters: 章节信息 [{chapter_id, chapter_title, element_count, ...}]
            elements: 所有结构化元素（需含 chapter_id）
            target_format: 目标格式 short_drama | long_drama
            target_episodes: 目标集数（None=自动决定）
            adaptation_mode: 适应度模式（影响场景压缩程度）
            cliffhanger_required: 每集是否必须有悬念结尾
            generate_investor_notes: 是否生成招商备注
            use_llm: 是否使用 LLM 增强
            state_manager: AgentStateManager 实例

        Returns:
            {status, episodes, conflict_nodes, narrative_arc, episode_plan_path, ...}
        """
        self.state_manager = state_manager or self.state_manager

        if not chapters or not elements:
            return {"status": "failed", "error": "未提供章节或元素数据"}

        self.log(
            f"智能分集规划: {len(chapters)} 章, "
            f"{len(elements)} 个元素, 格式={target_format}"
        )

        # Step 1: 检测冲突节点
        self.log("检测冲突节点...")
        conflict_nodes = self.conflict_analyzer.detect_conflict_nodes(
            elements=elements,
            chapters=chapters,
        )

        twist_count = sum(1 for n in conflict_nodes if n["type"] == "major_twist")
        cliff_count = sum(1 for n in conflict_nodes if n["type"] == "cliffhanger")
        scene_shift_count = sum(1 for n in conflict_nodes if n["type"] == "scene_shift")
        self.log(
            f"检测到 {len(conflict_nodes)} 个冲突节点 "
            f"(转折:{twist_count}, 悬念:{cliff_count}, 场景切换:{scene_shift_count})"
        )

        # Step 2: 构建叙事弧线
        self.log("构建叙事弧线...")
        narrative_arc = self.conflict_analyzer.build_narrative_arc(
            chapters=chapters,
            conflict_nodes=conflict_nodes,
        )

        # Step 3: 节奏拆分
        self.log(f"按{target_format}格式拆分...")
        max_chapters = self.get_config("episode_rhythm.max_chapters_per_episode", 5)
        min_conflict = self.get_config("episode_rhythm.min_conflict_per_episode", 1)

        episodes = self.rhythm_engine.plan_episodes_by_rhythm(
            chapters=chapters,
            elements=elements,
            conflict_nodes=conflict_nodes,
            target_format=target_format,
            min_conflict_per_episode=min_conflict,
            max_chapters_per_episode=max_chapters,
            cliffhanger_required=cliffhanger_required,
        )

        # Step 4: LLM 增强（可选）
        if use_llm and episodes:
            self.log("LLM 增强剧集标注...")
            episodes = self._llm_enhance_episodes(
                episodes, elements, target_format, adaptation_mode
            )

        # Step 5: 生成招商备注
        investor_notes = {}
        if generate_investor_notes:
            for ep in episodes:
                notes = self.rhythm_engine.generate_investor_notes(ep)
                investor_notes[ep["episode_id"]] = notes

        # Step 6: 生成报告并保存
        report = self._generate_plan_report(
            episodes, conflict_nodes, narrative_arc, target_format
        )

        output_dir = self.get_config("output.output_dir", "./output")
        project_name = (
            self.state_manager.project_name
            if self.state_manager else "未命名"
        )
        full_output_dir = os.path.join(output_dir, project_name)
        planning_dir = os.path.join(full_output_dir, "planning")
        os.makedirs(planning_dir, exist_ok=True)

        # 保存分集规划
        plan_path = os.path.join(planning_dir, "episode-plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(report)

        # 保存冲突节点数据
        conflict_path = os.path.join(
            os.path.dirname(planning_dir) or full_output_dir,
            "analysis", "conflict-nodes.json"
        )
        os.makedirs(os.path.dirname(conflict_path), exist_ok=True)
        with open(conflict_path, "w", encoding="utf-8") as f:
            json.dump(conflict_nodes, f, ensure_ascii=False, indent=2)

        # 保存剧集标注
        annotations_path = os.path.join(planning_dir, "episode-annotations.json")
        annotations = []
        for ep in episodes:
            annotations.append({
                "episode_id": ep["episode_id"],
                "chapters_range": ep["chapters_range"],
                "opening_hook": ep["opening_hook"],
                "mid_conflict": ep["mid_conflict"],
                "cliffhanger": ep["cliffhanger"],
                "highlights": ep["core_highlights"],
                "foreshadowing": ep["foreshadowing"],
                "investor_notes": investor_notes.get(ep["episode_id"], ""),
            })
        with open(annotations_path, "w", encoding="utf-8") as f:
            json.dump(annotations, f, ensure_ascii=False, indent=2)

        # 保存状态
        self.save_state("last_plan", {
            "timestamp": datetime.now().isoformat(),
            "chapters": len(chapters),
            "episodes": len(episodes),
            "target_format": target_format,
            "conflict_nodes": len(conflict_nodes),
        })

        self.log(f"分集规划完成: {len(chapters)}章 → {len(episodes)}集 ({target_format})")

        return {
            "status": "completed",
            "episode_count": len(episodes),
            "chapter_count": len(chapters),
            "conflict_node_count": len(conflict_nodes),
            "conflict_nodes": conflict_nodes,
            "narrative_arc": narrative_arc,
            "episodes": episodes,
            "episode_plan_path": plan_path,
            "conflict_nodes_path": conflict_path,
            "annotations_path": annotations_path,
            "target_format": target_format,
            "message": (
                f"智能分集完成: {len(chapters)}章 → {len(episodes)}集, "
                f"检测到 {len(conflict_nodes)} 个冲突节点, "
                f"格式: {target_format}"
            ),
        }

    # ═══════════════════════════════════════════════════════════

    def _llm_enhance_episodes(
        self,
        episodes: list[dict],
        elements: list[dict],
        target_format: str,
        adaptation_mode: str,
    ) -> list[dict]:
        """使用 LLM 为剧集标注生成更有创意的内容"""
        if not episodes:
            return episodes

        # 只处理前5集作为示例
        sample_eps = episodes[:min(5, len(episodes))]

        eps_text = []
        for ep in sample_eps:
            eps_text.append(
                f"第{ep['episode_id']}集 | {ep['chapters_range']} | "
                f"{ep['chapter_count']}章 | 预估{ep.get('duration_estimate','?')}\n"
                f"  当前钩子: {ep['opening_hook'][:100]}\n"
                f"  当前冲突: {ep['mid_conflict'][:100]}\n"
                f"  当前悬念: {ep['cliffhanger'][:100]}"
            )

        prompt = f"""你是资深电视剧导演和编剧。请为以下分集方案润色剧集钩子、冲突和悬念描述，使其更具吸引力。

格式: {target_format} ({'短剧3-5分钟/集' if target_format == 'short_drama' else '长剧45分钟/集'})
改编风格: {adaptation_mode}

分集方案:
{chr(10).join(eps_text)}

请输出JSON:
{{
  "enhancements": [
    {{
      "episode_id": 1,
      "enhanced_hook": "润色后的开篇钩子（30字以内，吸引观众）",
      "enhanced_conflict": "润色后的中段冲突描述（50字以内）",
      "enhanced_cliffhanger": "润色后的结尾悬念（30字以内，让观众迫不及待想看下一集）",
      "creative_title": "本集创意标题（4-10字）",
      "logline": "一句话宣传语（15-30字）"
    }}
  ]
}}"""

        try:
            result = self.call_llm(prompt, use_light=False, expect_json=True)
            if isinstance(result, dict):
                enhancements = result.get("enhancements", [])
                enhance_map = {e["episode_id"]: e for e in enhancements}
                for ep in episodes:
                    enh = enhance_map.get(ep["episode_id"], {})
                    if enh.get("enhanced_hook"):
                        ep["opening_hook"] = enh["enhanced_hook"]
                    if enh.get("enhanced_conflict"):
                        ep["mid_conflict"] = enh["enhanced_conflict"]
                    if enh.get("enhanced_cliffhanger"):
                        ep["cliffhanger"] = enh["enhanced_cliffhanger"]
                    if enh.get("creative_title"):
                        ep["creative_title"] = enh["creative_title"]
                    if enh.get("logline"):
                        ep["logline"] = enh["logline"]
        except Exception as e:
            self.log(f"LLM 增强剧集失败: {e}", level="warning")

        return episodes

    def _generate_plan_report(
        self,
        episodes: list[dict],
        conflict_nodes: list[dict],
        narrative_arc: dict,
        target_format: str,
    ) -> str:
        """生成分集规划 Markdown 报告"""
        report = []
        report.append(f"# 智能分集规划报告\n")
        report.append(f"**格式**: {target_format}")
        report.append(f"**总集数**: {len(episodes)}")
        report.append(f"**叙事弧线**: {narrative_arc.get('arc_type', '未知')}")
        report.append(f"**冲突节点总数**: {len(conflict_nodes)}\n")
        report.append("---\n")

        # 叙事弧线
        if narrative_arc.get("phases"):
            report.append("## 叙事弧线\n")
            for phase in narrative_arc["phases"]:
                report.append(f"- **{phase['phase']}** ({phase['chapter_range']}): {phase['description']}")

            report.append("\n### 关键转折点\n")
            for tp in narrative_arc.get("turning_points", []):
                report.append(f"- 第{tp['chapter_id']}章 [{tp['type']}]: {tp['description'][:100]}")

        report.append("\n---\n")

        # 逐集详情
        report.append("## 逐集规划\n")
        for ep in episodes:
            ep_id = ep["episode_id"]
            report.append(f"### 第{ep_id}集 — {ep.get('creative_title', '')}")
            report.append(f"- **覆盖章节**: {ep['chapters_range']} ({ep['chapter_count']}章)")
            report.append(f"- **预估时长**: {ep.get('duration_estimate', '未知')}")
            report.append(f"- **预估场景数**: {ep.get('scene_count_estimate', '?')}")
            report.append(f"- **冲突节点**: {ep.get('conflict_node_count', 0)}个")
            report.append(f"- **开篇钩子**: {ep.get('opening_hook', '')[:150]}")
            report.append(f"- **中段冲突**: {ep.get('mid_conflict', '')[:150]}")
            report.append(f"- **结尾悬念**: {ep.get('cliffhanger', '')[:150]}")

            # 看点
            highlights = ep.get("core_highlights", [])
            if highlights:
                report.append(f"\n**核心看点**:")
                for h in highlights:
                    report.append(f"  - {h}")

            # 伏笔
            foreshadowing = ep.get("foreshadowing", [])
            if foreshadowing:
                report.append(f"\n**剧情伏笔**:")
                for f in foreshadowing:
                    report.append(f"  - [{f.get('type', '?')}] {f.get('description', '')[:100]}")

            # 角色
            top_chars = ep.get("top_characters", [])
            if top_chars:
                report.append(f"\n**核心角色**: {', '.join(c['name'] for c in top_chars[:3])}")

            report.append("")

        return "\n".join(report)


def create_episode_director(config: dict = None, **kwargs) -> EpisodeDirector:
    """创建影视导演 Agent 实例"""
    return EpisodeDirector(config=config, **kwargs)
