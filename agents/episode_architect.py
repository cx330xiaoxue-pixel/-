"""
分集架构师 Agent — Phase 2: 分集规划 (~plan)

职责:
  - 将小说章节映射为电视剧集
  - 每集设计：核心冲突、悬念钩子、角色进度
  - 规划全剧关键转折点
  - 产出 planning/episode-plan.md

使用:
  agent = EpisodeArchitect(config)
  result = agent.execute(episodes=40, chapter_count=120, all_elements=...)
"""

import os
from datetime import datetime

from .base_agent import BaseAgent


class EpisodeArchitect(BaseAgent):
    """分集架构师 Agent — 章节→集映射与全剧结构设计"""

    agent_name = "episode-architect"
    agent_display_name = "分集架构师"
    agent_description = "将小说章节映射为电视剧集，设计每集核心冲突、悬念和角色进度"
    phase = "plan"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from skills.episode_planning import EpisodePlanningSkill
        self.skill = EpisodePlanningSkill()

    def execute(
        self,
        episodes: int = 40,
        chapter_count: int = None,
        all_elements: list = None,
        structure: dict = None,
        network: dict = None,
        state_manager=None,
        use_llm: bool = True,
        emotion_style: str = "standard",
        **kwargs,
    ) -> dict:
        """
        执行分集规划。

        Args:
            episodes: 目标集数
            chapter_count: 小说总章节数
            all_elements: 所有结构化元素
            structure: 叙事结构分析结果
            network: 人物网络分析结果
            state_manager: AgentStateManager 实例
            use_llm: 是否使用 LLM
            emotion_style: 情绪风格

        Returns:
            {status, episode_plan, plan_report_path, series_structure, ...}
        """
        self.state_manager = state_manager or self.state_manager

        # 确定章节数
        if chapter_count is None and all_elements:
            chapter_ids = set(e.get("chapter_id", 0) for e in all_elements)
            chapter_count = len(chapter_ids)
        chapter_count = chapter_count or 1

        self.log(f"分集规划: {chapter_count} 章 → {episodes} 集")

        # Step 1: 统计每章的数据
        chapter_elements = {}
        chapter_emotions = {}
        if all_elements:
            for e in all_elements:
                ch_id = e.get("chapter_id", 1)
                chapter_elements[ch_id] = chapter_elements.get(ch_id, 0) + 1
                if e.get("emotion"):
                    if ch_id not in chapter_emotions:
                        chapter_emotions[ch_id] = []
                    chapter_emotions[ch_id].append(e["emotion"])

        # Step 2: 章节 → 集映射
        self.log("映射章节到集...")
        episode_plan = self.skill.map_chapters_to_episodes(
            chapter_count=chapter_count,
            target_episodes=episodes,
            chapter_elements=chapter_elements,
            chapter_emotions=chapter_emotions,
        )

        # Step 3: 情绪曲线
        self.log("设计情绪曲线...")
        emotion_curves = self.skill.design_emotion_curve(
            episodes=episode_plan,
            style=emotion_style,
            chapter_emotions=chapter_emotions,
        )

        # Step 4: 悬念钩子
        self.log("生成悬念钩子...")
        hooks = self.skill.generate_hooks(
            episodes=episode_plan,
            all_elements=all_elements,
        )

        # Step 5: 全剧结构
        self.log("设计全剧结构...")
        series_structure = self.skill.design_series_structure(
            episodes=episode_plan,
            total_episodes=episodes,
        )

        # Step 6: LLM 增强（可选）
        if use_llm:
            self.log("LLM 增强分集规划...")
            episode_plan = self._llm_enhance_episodes(
                episode_plan, structure, network
            )

        # Step 7: 生成报告
        title = (
            self.state_manager.project_name
            if self.state_manager else "未命名"
        )
        report = self.skill.generate_episode_plan_report(
            title=title,
            episodes=episode_plan,
            series_structure=series_structure,
            hooks=hooks,
            emotion_curves=emotion_curves,
        )

        # 保存报告
        output_dir = self.get_config("output.output_dir", "./output")
        project_name = self.state_manager.project_name if self.state_manager else title
        full_output_dir = os.path.join(output_dir, project_name)
        os.makedirs(os.path.join(full_output_dir, "planning"), exist_ok=True)
        plan_path = os.path.join(full_output_dir, "planning", "episode-plan.md")

        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(report)

        # 保存情绪曲线数据（JSON，供后续使用）
        import json
        curve_path = os.path.join(full_output_dir, "planning", "emotion-curve.json")
        with open(curve_path, "w", encoding="utf-8") as f:
            json.dump(emotion_curves, f, ensure_ascii=False, indent=2)

        self.save_state("last_plan", {
            "timestamp": datetime.now().isoformat(),
            "chapter_count": chapter_count,
            "target_episodes": episodes,
            "actual_episodes": len(episode_plan),
        })

        self.log(f"分集规划完成: {len(episode_plan)} 集")

        return {
            "status": "completed",
            "episode_count": len(episode_plan),
            "chapter_count": chapter_count,
            "episode_plan": episode_plan,
            "emotion_curves": emotion_curves,
            "hooks": hooks,
            "series_structure": series_structure,
            "plan_report_path": plan_path,
            "emotion_curve_path": curve_path,
            "message": (
                f"分集规划完成: {chapter_count} 章映射为 "
                f"{len(episode_plan)} 集，情绪风格: {emotion_style}"
            ),
        }

    # ═══════════════════════════════════════════════════════════

    def _llm_enhance_episodes(
        self,
        episodes: list[dict],
        structure: dict = None,
        network: dict = None,
    ) -> list[dict]:
        """使用 LLM 为每集生成更有创意的标题和核心冲突描述"""
        if not episodes:
            return episodes

        # 只处理前几集作为示例（避免 token 过大）
        sample_eps = episodes[:min(5, len(episodes))]
        ep_summaries = "\n".join(
            f"第{ep['episode_id']}集: 覆盖{ep['chapters_range']} ({ep['chapter_count']}章)"
            for ep in sample_eps
        )

        prompt = f"""你是一位资深电视剧编剧。基于以下分集规划，为每集生成更吸引人的标题和核心冲突描述。

叙事风格: {structure.get('narrative_style', '未知') if structure else '未知'}
主要角色: {', '.join(c['name'] for c in (network or {}).get('main_characters', [])[:5]) if network else '未知'}

分集规划:
{ep_summaries}

请为每集输出 JSON:
[
  {{
    "episode_id": 1,
    "title": "创意标题（吸引眼球）",
    "logline": "一句话概括本集（30字以内）",
    "core_conflict": "本集核心冲突描述",
    "character_focus": "本集重点塑造的角色",
    "emotional_beat": "本集的情感主调"
  }}
]"""

        try:
            enhanced = self.call_llm(prompt, use_light=False, expect_json=True)
            if isinstance(enhanced, list):
                enhance_map = {item.get("episode_id"): item for item in enhanced}
                for ep in episodes:
                    enh = enhance_map.get(ep["episode_id"], {})
                    if enh.get("title"):
                        ep["episode_title_hint"] = enh["title"]
                    if enh.get("logline"):
                        ep["logline"] = enh["logline"]
                    if enh.get("core_conflict"):
                        ep["core_conflict"] = enh["core_conflict"]
                    if enh.get("character_focus"):
                        ep["character_focus"] = enh["character_focus"]
        except Exception as e:
            self.log(f"LLM 增强分集失败: {e}", level="warning")

        return episodes


def create_episode_architect(config: dict = None, **kwargs) -> EpisodeArchitect:
    """创建分集架构师 Agent 实例"""
    return EpisodeArchitect(config=config, **kwargs)
