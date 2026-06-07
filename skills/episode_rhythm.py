"""
影视节奏引擎技能 — 基于冲突分析结果的智能分集

功能:
  - 按影视节奏标准拆分/合并章节，适配不同格式
  - 短剧(3-5min/集): 1-2场景，强悬念结尾
  - 长剧(45min/集): 8-12场景，完整三幕结构
  - 自动生成开篇钩子、中段冲突、结尾悬念
  - 自动标注核心看点、剧情伏笔、招商审核参考备注

使用:
  engine = EpisodeRhythmSkill()
  plan = engine.plan_episodes_by_rhythm(chapters, conflict_nodes, target_format="long_drama")
"""

from collections import defaultdict
from typing import Optional


class EpisodeRhythmSkill:
    """影视节奏引擎 — 智能分集与剧集结构设计"""

    # 短剧模板（3-5分钟）
    SHORT_DRAMA_TEMPLATE = {
        "duration": "3-5分钟",
        "scenes_per_episode": (1, 3),
        "structure": ["opening_hook", "mini_conflict", "cliffhanger"],
        "description": "短视频格式 — 快速入戏，强冲突，每集结尾必留悬念",
    }

    # 长剧模板（45分钟）
    LONG_DRAMA_TEMPLATE = {
        "duration": "45分钟",
        "scenes_per_episode": (8, 15),
        "structure": ["cold_open", "act1_setup", "act2_confrontation",
                      "act3_climax", "cliffhanger"],
        "description": "标准电视剧格式 — 完整三幕，多层次冲突，角色弧线推进",
    }

    def __init__(self):
        pass

    # ═══════════════════════════════════════════════════════════
    # 主入口：按节奏规划分集
    # ═══════════════════════════════════════════════════════════

    def plan_episodes_by_rhythm(
        self,
        chapters: list[dict],
        elements: list[dict],
        conflict_nodes: list[dict],
        target_format: str = "long_drama",
        min_conflict_per_episode: int = 1,
        max_chapters_per_episode: int = 5,
        cliffhanger_required: bool = True,
    ) -> list[dict]:
        """
        按影视节奏规划分集方案。

        Args:
            chapters: 章节信息 [{chapter_id, chapter_title, element_count, ...}]
            elements: 所有结构化元素（需含 chapter_id）
            conflict_nodes: 冲突节点列表
            target_format: "short_drama" | "long_drama"
            min_conflict_per_episode: 每集最小冲突节点数
            max_chapters_per_episode: 每集最大覆盖章节数
            cliffhanger_required: 每集是否必须有悬念结尾

        Returns:
            [{episode_id, chapters_range, chapter_ids, scene_count_estimate,
              duration_estimate, opening_hook, mid_conflict, cliffhanger,
              act_structure, conflict_nodes_in_episode, highlights, foreshadowing}]
        """
        if not chapters:
            return []

        from .conflict_analyzer import ConflictAnalyzerSkill
        analyzer = ConflictAnalyzerSkill()

        # 选择模板
        template = (self.SHORT_DRAMA_TEMPLATE if target_format == "short_drama"
                    else self.LONG_DRAMA_TEMPLATE)

        # 按章节分组元素
        chapter_elements = defaultdict(list)
        for elem in elements:
            ch_id = elem.get("chapter_id", 1)
            chapter_elements[ch_id].append(elem)

        chapter_ids = sorted(ch.get("chapter_id", i + 1)
                             for i, ch in enumerate(chapters))

        # 寻找最优断点
        if target_format == "short_drama":
            breakpoints = self._find_short_drama_breakpoints(
                chapter_ids, conflict_nodes, chapter_elements,
                min_conflict_per_episode
            )
        else:
            breakpoints = analyzer.find_natural_breakpoints(
                chapters, conflict_nodes,
                target_episodes=None,  # 自动决定
                min_chapters_per_episode=1,
                max_chapters_per_episode=max_chapters_per_episode,
            )

        # 构建分集方案
        episodes = []
        episode_id = 0
        current_start = chapter_ids[0]

        all_breakpoints = sorted(breakpoints) + [chapter_ids[-1]]

        for bp in all_breakpoints:
            # 找到当前集覆盖的章节范围
            bp_idx = chapter_ids.index(bp) if bp in chapter_ids else -1
            if bp_idx < 0:
                continue

            end_ch = bp
            ep_chapter_ids = [ch for ch in chapter_ids
                              if current_start <= ch <= end_ch]

            if not ep_chapter_ids:
                continue

            episode_id += 1

            # 收集本集元素
            ep_elements = []
            for ch_id in ep_chapter_ids:
                ep_elements.extend(chapter_elements.get(ch_id, []))

            # 本集冲突节点
            ep_nodes = [n for n in conflict_nodes
                        if n["chapter_id"] in ep_chapter_ids]

            # 场景数估算
            scene_estimate = self._estimate_scene_count(
                ep_elements, target_format
            )

            # 时长估算
            duration_estimate = self._estimate_duration(
                scene_estimate, target_format
            )

            # ── 生成剧集结构标注 ──
            opening_hook = self.generate_opening_hook(
                ep_elements[:max(1, len(ep_elements) // 5)])  # 前20%元素

            mid_conflict = self.generate_mid_conflict(
                ep_elements, ep_nodes)

            cliffhanger = ""
            if cliffhanger_required or episode_id < len(breakpoints):
                tail_start = max(0, len(ep_elements) - max(1, len(ep_elements) // 5))
                cliffhanger = self.generate_cliffhanger(
                    ep_elements[tail_start:])

            # ── 标注 ──
            # 提取角色重要性
            character_counts = defaultdict(int)
            for elem in ep_elements:
                role = elem.get("role", "")
                if role and role != "旁白":
                    character_counts[role] += 1
            top_characters = sorted(character_counts.items(),
                                    key=lambda x: -x[1])[:5]

            highlights = self.annotate_highlights(
                ep_elements, [c[0] for c in top_characters])

            foreshadowing = self.annotate_foreshadowing(
                ep_elements, elements, episode_id)

            # 剧集结构
            act_structure = self._build_act_structure(
                ep_chapter_ids, ep_elements, target_format)

            episodes.append({
                "episode_id": episode_id,
                "chapters_range": f"第{ep_chapter_ids[0]}-{ep_chapter_ids[-1]}章",
                "chapter_ids": ep_chapter_ids,
                "chapter_count": len(ep_chapter_ids),
                "element_count": len(ep_elements),
                "scene_count_estimate": scene_estimate,
                "duration_estimate": duration_estimate,
                "conflict_node_count": len(ep_nodes),
                "conflict_nodes": [
                    {"id": n["node_id"], "type": n["type"],
                     "chapter": n["chapter_id"], "desc": n["description"]}
                    for n in ep_nodes
                ],
                "act_structure": act_structure,
                "opening_hook": opening_hook,
                "mid_conflict": mid_conflict,
                "cliffhanger": cliffhanger,
                "core_highlights": highlights,
                "foreshadowing": foreshadowing,
                "top_characters": [{"name": name, "appearances": count}
                                   for name, count in top_characters],
            })

            # 下一集起始章节
            next_start_idx = chapter_ids.index(end_ch) + 1
            if next_start_idx < len(chapter_ids):
                current_start = chapter_ids[next_start_idx]
            else:
                break

        return episodes

    # ═══════════════════════════════════════════════════════════
    # 格式适配
    # ═══════════════════════════════════════════════════════════

    def fit_short_drama(
        self,
        chapters: list[dict],
        conflict_nodes: list[dict],
    ) -> list[dict]:
        """适配短剧格式 (3-5min/集)"""
        return self.plan_episodes_by_rhythm(
            chapters=chapters,
            elements=[],  # 简化版不使用elements
            conflict_nodes=conflict_nodes,
            target_format="short_drama",
            min_conflict_per_episode=1,
            max_chapters_per_episode=2,
            cliffhanger_required=True,
        )

    def fit_long_drama(
        self,
        chapters: list[dict],
        conflict_nodes: list[dict],
    ) -> list[dict]:
        """适配长剧格式 (45min/集)"""
        return self.plan_episodes_by_rhythm(
            chapters=chapters,
            elements=[],
            conflict_nodes=conflict_nodes,
            target_format="long_drama",
            min_conflict_per_episode=1,
            max_chapters_per_episode=5,
            cliffhanger_required=True,
        )

    def _find_short_drama_breakpoints(
        self,
        chapter_ids: list[int],
        conflict_nodes: list[dict],
        chapter_elements: dict[int, list],
        min_conflict: int = 1,
    ) -> list[int]:
        """
        为短剧格式找断点：优先在高冲突节点处断开。
        短剧特点：每个cliffhanger后都应该是一集结束。
        """
        breakpoints = []

        for i, ch_id in enumerate(chapter_ids):
            if i == len(chapter_ids) - 1:
                break

            # 检查当前章是否有强cliffhanger
            cliff_nodes = [n for n in conflict_nodes
                           if n["chapter_id"] == ch_id
                           and n["type"] == "cliffhanger"
                           and n.get("intensity", 0) > 0.4]

            # 检查当前章是否有major_twist
            twist_nodes = [n for n in conflict_nodes
                           if n["chapter_id"] == ch_id
                           and n["type"] == "major_twist"]

            if cliff_nodes or twist_nodes:
                breakpoints.append(ch_id)
                continue

            # 每2章至少一个断点（短剧节奏快）
            if i > 0 and (i + 1) % 2 == 0:
                breakpoints.append(ch_id)

        return breakpoints

    # ═══════════════════════════════════════════════════════════
    # 估算方法
    # ═══════════════════════════════════════════════════════════

    def _estimate_scene_count(
        self, elements: list[dict], target_format: str
    ) -> int:
        """根据元素数估算场景数"""
        if not elements:
            return 1

        # 粗略: 每10-15个元素 ≈ 1个场景
        raw_scenes = max(1, len(elements) // 12)

        if target_format == "short_drama":
            return min(3, raw_scenes)
        else:
            return min(15, raw_scenes)

    def _estimate_duration(
        self, scene_count: int, target_format: str
    ) -> str:
        """根据场景数估算时长"""
        if target_format == "short_drama":
            minutes = scene_count * 2  # 短剧每场景约2分钟
            return f"{max(2, minutes)}分钟"
        else:
            minutes = scene_count * 4  # 长剧每场景约4分钟
            return f"{max(10, minutes)}分钟"

    # ═══════════════════════════════════════════════════════════
    # 剧集结构标注
    # ═══════════════════════════════════════════════════════════

    def generate_opening_hook(self, opening_elements: list[dict]) -> str:
        """
        从集首元素生成开篇钩子描述。

        Args:
            opening_elements: 集首20%的元素

        Returns:
            钩子描述文本
        """
        if not opening_elements:
            return "[开篇] 以角色日常场景引入"

        # 找第一个dialogue或action
        hook_elem = None
        for elem in opening_elements:
            if elem.get("type") in ("dialogue", "action"):
                hook_elem = elem
                break

        if not hook_elem:
            hook_elem = opening_elements[0]

        text = hook_elem.get("text", "")[:120]
        etype = hook_elem.get("type", "")
        role = hook_elem.get("role", "角色")

        if etype == "dialogue":
            return f"[开篇钩子] {role}的对白引入冲突: \"{text[:80]}\""
        elif etype == "action":
            return f"[开篇钩子] 以{role}的动作为切入: {text[:80]}"
        elif etype == "narration":
            return f"[开篇钩子] 情境建立: {text[:80]}"
        else:
            return f"[开篇钩子] 场景切入: {text[:80]}"

    def generate_mid_conflict(
        self,
        episode_elements: list[dict],
        episode_nodes: list[dict] = None,
    ) -> str:
        """
        生成本集中段冲突描述。

        找中间位置的confrontation/revelation节点。
        """
        if not episode_elements:
            return "[中段冲突] 待定"

        mid_start = len(episode_elements) // 3
        mid_end = len(episode_elements) * 2 // 3
        mid_elements = episode_elements[mid_start:mid_end]

        # 优先找中段的冲突节点
        if episode_nodes:
            mid_nodes = [n for n in episode_nodes
                         if n["type"] in ("major_twist", "emotional_peak")]
            if mid_nodes:
                n = mid_nodes[0]
                return f"[中段冲突] 第{n['chapter_id']}章: {n['description'][:100]}"

        # 找 confrontation beat
        for elem in mid_elements:
            if elem.get("beat_type") == "confrontation":
                text = elem.get("text", "")[:100]
                role = elem.get("role", "")
                if role and role != "旁白":
                    return f"[中段冲突] {role}的冲突: {text}"
                return f"[中段冲突] {text}"

        # 找 dialogue
        dialogue_count = sum(1 for e in mid_elements
                             if e.get("type") == "dialogue")
        if dialogue_count > 5:
            return f"[中段冲突] 角色对话密集区({dialogue_count}段对白)，冲突逐步升级"

        return "[中段冲突] 情节推进中，冲突酝酿"

    def generate_cliffhanger(self, tail_elements: list[dict]) -> str:
        """
        从集末元素生成结尾悬念描述。
        """
        if not tail_elements:
            return "[结尾悬念] 待定"

        from .conflict_analyzer import ConflictAnalyzerSkill
        analyzer = ConflictAnalyzerSkill()
        cliff_result = analyzer.detect_cliffhanger_elements(tail_elements)

        if cliff_result["is_cliffhanger"]:
            ptype = cliff_result["pattern_type"]
            snippet = cliff_result["snippet"][:120]
            return f"[结尾{ptype}] {snippet}"

        # 无自然悬念 → 找最后的重要事件
        for elem in reversed(tail_elements):
            if elem.get("beat_type") in ("confrontation", "revelation"):
                text = elem.get("text", "")[:100]
                return f"[结尾悬念] 冲突未完: {text}"

        return "[结尾悬念] 以角色情感或环境画面收尾，为下一集埋下情绪伏笔"

    # ═══════════════════════════════════════════════════════════
    # 看点与伏笔标注
    # ═══════════════════════════════════════════════════════════

    def annotate_highlights(
        self,
        episode_elements: list[dict],
        top_characters: list[str] = None,
    ) -> list[str]:
        """
        标注本集核心看点。

        规则:
          1. 最密集的confrontation区域
          2. 重要角色的关键对白
          3. revelation类型的揭示场景
        """
        highlights = []
        top_characters = top_characters or []

        # 找confrontation beat
        confrontations = [e for e in episode_elements
                          if e.get("beat_type") == "confrontation"]
        if confrontations:
            highlights.append(f"🔥 冲突场面: {len(confrontations)}个冲突节拍")

        # 找revelation
        revelations = [e for e in episode_elements
                        if e.get("beat_type") == "revelation"]
        if revelations:
            r = revelations[0]
            text = r.get("text", "")[:80]
            highlights.append(f"💡 剧情揭示: {text}")

        # 重要角色的对话量
        character_dialogues = defaultdict(int)
        for elem in episode_elements:
            if elem.get("type") == "dialogue":
                role = elem.get("role", "")
                if role in top_characters[:3]:
                    character_dialogues[role] += 1

        for char, count in sorted(character_dialogues.items(),
                                   key=lambda x: -x[1])[:2]:
            highlights.append(f"🎭 {char}核心戏份: {count}段对白")

        # 动作场面
        actions = [e for e in episode_elements if e.get("type") == "action"]
        combat_actions = [e for e in actions
                          if any(kw in e.get("text", "")
                                 for kw in ["出剑", "拔刀", "攻击", "战斗", "斩杀",
                                            "袭来", "对决", "爆发"])]
        if combat_actions:
            highlights.append(f"⚔️ 动作场面: {len(combat_actions)}个动作镜头")

        if not highlights:
            highlights.append("📖 剧情推进集")

        return highlights

    def annotate_foreshadowing(
        self,
        episode_elements: list[dict],
        all_elements: list[dict],
        current_episode_id: int,
    ) -> list[dict]:
        """
        标注本集的剧情伏笔。

        检测条件:
          1. 提到未解释的人/物/事件
          2. 角色做出承诺/预言
          3. 关键道具/信息首次出现
        """
        foreshadowing = []

        # 检测预言/承诺类
        for elem in episode_elements:
            text = elem.get("text", "")
            etype = elem.get("type", "")

            if etype != "dialogue":
                continue

        # 检测未解的悬念元素
        unresolved_markers = [
            "日后", "将来", "总有一天", "迟早", "早晚",
            "会回来的", "还会再见的", "不会就这样结束",
            "这只是开始", "真正的", "背后还有",
        ]

        for elem in episode_elements:
            text = elem.get("text", "")
            for marker in unresolved_markers:
                if marker in text:
                    foreshadowing.append({
                        "description": f"伏笔: {text[:100]}",
                        "related_episode": current_episode_id,
                        "payoff_episode": None,  # LLM后期填充
                        "type": "unresolved_thread",
                        "confidence": 0.5,
                    })
                    break

        # 检测关键道具/信息首次出现
        key_item_markers = ["秘籍", "宝图", "信物", "令牌", "丹药",
                            "遗物", "密信", "口诀", "法宝", "传承"]
        for elem in episode_elements:
            text = elem.get("text", "")
            for marker in key_item_markers:
                if marker in text:
                    foreshadowing.append({
                        "description": f"关键道具/信息: {text[:100]}",
                        "related_episode": current_episode_id,
                        "payoff_episode": None,
                        "type": "key_item",
                        "confidence": 0.6,
                    })
                    break

        # 去重
        seen = set()
        unique = []
        for f in foreshadowing:
            if f["description"][:50] not in seen:
                seen.add(f["description"][:50])
                unique.append(f)
        return unique[:3]  # 每集最多3个伏笔标注

    # ═══════════════════════════════════════════════════════════
    # 招商审核备注
    # ═══════════════════════════════════════════════════════════

    def generate_investor_notes(
        self,
        episode: dict,
        series_context: dict = None,
    ) -> str:
        """
        生成招商/审核参考备注。

        Args:
            episode: 分集信息
            series_context: 全剧上下文

        Returns:
            招商参考备注文本
        """
        notes = []
        notes.append(f"## 第{episode['episode_id']}集 招商/审核参考\n")

        # 基础信息
        notes.append(f"- **覆盖章节**: {episode['chapters_range']}")
        notes.append(f"- **预估时长**: {episode.get('duration_estimate', '未知')}")
        notes.append(f"- **场景数**: {episode.get('scene_count_estimate', '?')}")

        # 核心看点
        highlights = episode.get("core_highlights", [])
        if highlights:
            notes.append(f"\n### 核心看点")
            for h in highlights:
                notes.append(f"- {h}")

        # 冲突强度
        nodes = episode.get("conflict_nodes", [])
        if nodes:
            twists = [n for n in nodes if n.get("type") == "major_twist"]
            cliffs = [n for n in nodes if n.get("type") == "cliffhanger"]
            notes.append(f"\n### 冲突强度")
            notes.append(f"- 转折点: {len(twists)}个")
            notes.append(f"- 悬念钩子: {len(cliffs)}个")
            notes.append(f"- 冲突节点总数: {len(nodes)}个")

        # 核心角色
        top_chars = episode.get("top_characters", [])
        if top_chars:
            notes.append(f"\n### 核心角色 ({len(top_chars)}人)")
            for ch in top_chars[:5]:
                notes.append(f"- {ch['name']}: {ch['appearances']}次出场")

        # 伏笔
        foreshadowing = episode.get("foreshadowing", [])
        if foreshadowing:
            notes.append(f"\n### 剧情伏笔 ({len(foreshadowing)}个)")
            for f in foreshadowing:
                notes.append(f"- [{f.get('type', '?')}] {f.get('description', '')[:80]}")

        # 开场/冲突/悬念
        notes.append(f"\n### 剧集结构")
        notes.append(f"- **开篇钩子**: {episode.get('opening_hook', '待定')[:120]}")
        notes.append(f"- **中段冲突**: {episode.get('mid_conflict', '待定')[:120]}")
        notes.append(f"- **结尾悬念**: {episode.get('cliffhanger', '待定')[:120]}")

        # 剧集结构分析
        act = episode.get("act_structure", {})
        if act:
            notes.append(f"\n### 幕结构")
            for act_name, act_desc in act.items():
                notes.append(f"- **{act_name}**: {act_desc}")

        return "\n".join(notes)

    def _build_act_structure(
        self,
        chapter_ids: list[int],
        elements: list[dict],
        target_format: str,
    ) -> dict:
        """构建剧集的幕结构描述"""
        if target_format == "short_drama":
            return {
                "冷开场": f"第{chapter_ids[0]}章开篇",
                "冲突点": f"第{chapter_ids[len(chapter_ids)//2]}章",
                "悬念结尾": f"第{chapter_ids[-1]}章章末",
            }
        else:
            return {
                "Act 1 (建立)": f"第{chapter_ids[0]}章",
                "Act 2 (对抗)": f"第{chapter_ids[1] if len(chapter_ids) > 1 else chapter_ids[0]}-{chapter_ids[-2] if len(chapter_ids) > 2 else chapter_ids[-1]}章",
                "Act 3 (高潮)": f"第{chapter_ids[-1]}章",
            }
