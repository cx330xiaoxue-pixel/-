"""
冲突节点分析技能 — 跨章节叙事断点检测

功能:
  - 分析跨章节叙事流，识别自然断点
  - 检测冲突密度变化、场景切换、情绪峰值、悬念结尾
  - 为智能分集提供最优拆分/合并点
  - 构建跨章节叙事弧线

使用:
  analyzer = ConflictAnalyzerSkill()
  nodes = analyzer.detect_conflict_nodes(elements, chapters)
  breakpoints = analyzer.find_natural_breakpoints(chapters, nodes, target_episodes=10)
"""

from collections import Counter, defaultdict
from typing import Optional


class ConflictAnalyzerSkill:
    """冲突节点分析技能 — 叙事断点检测与弧线构建"""

    # 冲突密度计算权重
    BEAT_WEIGHTS = {
        "confrontation": 1.0,
        "revelation": 0.8,
        "payoff": 0.6,
        "setup": 0.2,
        "transition": 0.05,
    }

    # 场景切换检测关键词
    SCENE_SHIFT_MARKERS = [
        "与此同时", "另一边", "画面一转", "场景切换", "镜头转向",
        "却说", "话说", "暂且", "且说", "再说",
        "数日后", "几日后", "次日", "第二天", "翌日", "第二天一早",
        "一个月后", "半年后", "一年后", "时光飞逝",
    ]

    # 悬念结尾标记
    CLIFFHANGER_PATTERNS = [
        # 疑问/反问
        "?", "？",
        # 未完成动作
        "正要", "刚想", "还未来得及",
        # 突然中断
        "突然", "忽然", "猛地",
        # 新威胁/未知
        "一个黑影", "一道身影", "一个人影", "陌生的声音",
        "却不知", "殊不知", "哪知", "怎料",
        # 危险预兆
        "危机", "危险", "不妙", "不好",
    ]

    def __init__(self):
        pass

    # ═══════════════════════════════════════════════════════════
    # 主入口：检测所有冲突节点
    # ═══════════════════════════════════════════════════════════

    def detect_conflict_nodes(
        self,
        elements: list[dict],
        chapters: list[dict] = None,
    ) -> list[dict]:
        """
        检测所有叙事冲突节点。

        Args:
            elements: 所有结构化元素（需含 chapter_id）
            chapters: 章节信息 [{chapter_id, chapter_title, element_count, ...}]

        Returns:
            [{node_id, type, chapter_id, position, intensity, description, elements_slice}]
        """
        # 按章节分组
        chapter_groups = defaultdict(list)
        for elem in elements:
            ch_id = elem.get("chapter_id", 1)
            chapter_groups[ch_id].append(elem)

        chapter_ids = sorted(chapter_groups.keys())
        if not chapter_ids:
            return []

        nodes = []
        node_counter = 0

        # ── 检测1: 每章的冲突密度 ──
        densities = {}
        for ch_id in chapter_ids:
            ch_elements = chapter_groups[ch_id]
            densities[ch_id] = self.compute_conflict_density(ch_elements)

        # ── 检测2: 冲突密度突变（major_twist）──
        prev_density = 0
        for i, ch_id in enumerate(chapter_ids):
            density = densities[ch_id]
            if i > 0 and density - prev_density > 0.15:
                node_counter += 1
                nodes.append({
                    "node_id": f"NODE-{node_counter:03d}",
                    "type": "major_twist",
                    "chapter_id": ch_id,
                    "position": 0.1,  # 章首密度突增 → 转折在章首
                    "intensity": round(density - prev_density, 2),
                    "description": f"第{ch_id}章冲突密度突增({prev_density:.2f}→{density:.2f})",
                    "related_chapters": [ch_id - 1, ch_id],
                })
            prev_density = density

        # ── 检测3: 场景切换 (scene_shift) ──
        for elem in elements:
            text = elem.get("text", "")
            for marker in self.SCENE_SHIFT_MARKERS:
                if marker in text:
                    ch_id = elem.get("chapter_id", 1)
                    # 找该元素在章节中的位置
                    ch_elems = chapter_groups[ch_id]
                    pos = ch_elems.index(elem) / max(len(ch_elems), 1) if elem in ch_elems else 0.5
                    node_counter += 1
                    nodes.append({
                        "node_id": f"NODE-{node_counter:03d}",
                        "type": "scene_shift",
                        "chapter_id": ch_id,
                        "position": round(pos, 2),
                        "intensity": 0.3,
                        "description": f"第{ch_id}章场景切换: {text[:80]}",
                        "related_chapters": [ch_id],
                    })
                    break  # 一个元素只触发一个节点

        # ── 检测4: 情绪峰值 (emotional_peak) ──
        for ch_id in chapter_ids:
            ch_elements = chapter_groups[ch_id]
            emotion_intensity = self._find_emotion_peak(ch_elements)
            if emotion_intensity:
                node_counter += 1
                nodes.append({
                    "node_id": f"NODE-{node_counter:03d}",
                    "type": "emotional_peak",
                    "chapter_id": ch_id,
                    "position": emotion_intensity["position"],
                    "intensity": emotion_intensity["intensity"],
                    "description": f"第{ch_id}章情绪峰值: {emotion_intensity['emotion']}",
                    "related_chapters": [ch_id],
                })

        # ── 检测5: 章末悬念 (cliffhanger) ──
        for ch_id in chapter_ids:
            ch_elements = chapter_groups[ch_id]
            cliff = self.detect_cliffhanger_elements(ch_elements)
            if cliff["is_cliffhanger"]:
                node_counter += 1
                nodes.append({
                    "node_id": f"NODE-{node_counter:03d}",
                    "type": "cliffhanger",
                    "chapter_id": ch_id,
                    "position": 0.9,  # 章末
                    "intensity": cliff["confidence"],
                    "description": f"第{ch_id}章章末悬念: {cliff['snippet'][:100]}",
                    "related_chapters": [ch_id, ch_id + 1] if ch_id < max(chapter_ids) else [ch_id],
                    "suspense_snippet": cliff["snippet"],
                })

        # ── 检测6: 子情节收束 (resolution_point) ──
        for ch_id in chapter_ids:
            ch_elements = chapter_groups[ch_id]
            resolution = self._detect_resolution(ch_elements)
            if resolution:
                node_counter += 1
                nodes.append({
                    "node_id": f"NODE-{node_counter:03d}",
                    "type": "resolution_point",
                    "chapter_id": ch_id,
                    "position": resolution["position"],
                    "intensity": resolution["confidence"],
                    "description": f"第{ch_id}章情节收束: {resolution['snippet'][:80]}",
                    "related_chapters": [ch_id],
                })

        # 按章节和位置排序
        nodes.sort(key=lambda n: (n["chapter_id"], n["position"]))
        return nodes

    # ═══════════════════════════════════════════════════════════
    # 冲突密度计算
    # ═══════════════════════════════════════════════════════════

    def compute_conflict_density(self, chapter_elements: list[dict]) -> float:
        """
        计算章节冲突密度 (0-1)。

        confrontations + revelations 的比例（加权）。
        """
        if not chapter_elements:
            return 0.0

        total_weight = 0.0
        max_weight = len(chapter_elements) * 1.0  # 最大可能权重

        for elem in chapter_elements:
            beat = elem.get("beat_type", "")
            weight = self.BEAT_WEIGHTS.get(beat, 0.1)
            total_weight += weight

        return min(1.0, total_weight / max(max_weight, 1))

    # ═══════════════════════════════════════════════════════════
    # 自然断点查找
    # ═══════════════════════════════════════════════════════════

    def find_natural_breakpoints(
        self,
        chapters: list[dict],
        conflict_nodes: list[dict],
        target_episodes: int = None,
        min_chapters_per_episode: int = 1,
        max_chapters_per_episode: int = 5,
    ) -> list[int]:
        """
        寻找最优的章节拆分/合并点。

        Args:
            chapters: 章节信息列表 [{chapter_id, ...}]
            conflict_nodes: 冲突节点列表
            target_episodes: 目标集数
            min_chapters_per_episode: 每集最小章节数
            max_chapters_per_episode: 每集最大章节数

        Returns:
            断点章节ID列表（在哪个章节之后断开），如 [3, 6] 表示 ch1-3→ep1, ch4-6→ep2, ch7-end→ep3
        """
        if not chapters:
            return []

        chapter_ids = sorted(ch.get("chapter_id", i + 1)
                             for i, ch in enumerate(chapters))
        total_chapters = len(chapter_ids)

        if total_chapters <= 1:
            return []

        # 为每个章间间隙评分（章i和章i+1之间的断点评分）
        gap_scores = {}
        for i in range(len(chapter_ids) - 1):
            ch_id = chapter_ids[i]
            next_ch_id = chapter_ids[i + 1]
            score = self._score_gap(ch_id, next_ch_id, conflict_nodes)
            gap_scores[ch_id] = score

        # 根据目标集数选择最优断点
        if target_episodes is None:
            target_episodes = max(1, total_chapters // 2)

        # 需要 target_episodes - 1 个断点
        num_breakpoints = target_episodes - 1

        # 按评分排序，选最高的断点
        sorted_gaps = sorted(gap_scores.items(), key=lambda x: -x[1])

        # 约束：断点之间至少间隔 min_chapters，最多 max_chapters
        selected = []
        occupied = set()

        for gap_ch, score in sorted_gaps:
            if len(selected) >= num_breakpoints:
                break

            gap_idx = chapter_ids.index(gap_ch) if gap_ch in chapter_ids else -1
            if gap_idx < 0:
                continue

            # 检查间隔约束
            too_close = False
            for sel_ch in selected:
                sel_idx = chapter_ids.index(sel_ch) if sel_ch in chapter_ids else -1
                if sel_idx >= 0:
                    dist = abs(gap_idx - sel_idx)
                    if dist < min_chapters_per_episode:
                        too_close = True
                        break

            if too_close:
                continue

            # 检查是否会使某段过长
            selected.append(gap_ch)
            occupied.add(gap_idx)

        # 排序选中的断点
        selected.sort(key=lambda ch: chapter_ids.index(ch) if ch in chapter_ids else 999)
        return selected

    def _score_gap(
        self, ch_id: int, next_ch_id: int, conflict_nodes: list[dict]
    ) -> float:
        """
        评分两个章节之间的断点适合度。

        高分: 章末有cliffhanger、下一章场景切换、冲突密度变化大
        """
        score = 0.0

        for node in conflict_nodes:
            n_ch = node["chapter_id"]
            n_type = node["type"]

            # 当前章末有cliffhanger → 强断点
            if n_ch == ch_id and n_type == "cliffhanger":
                score += 3.0 * node.get("intensity", 0.5)

            # 当前章末有情绪峰值 → 好断点
            if n_ch == ch_id and n_type == "emotional_peak":
                if node.get("position", 0) > 0.7:  # 章末位置
                    score += 1.5

            # 下一章有场景切换 → 好断点
            if n_ch == next_ch_id and n_type == "scene_shift":
                score += 2.0

            # 下一章有重大转折 → 适合新集开篇
            if n_ch == next_ch_id and n_type == "major_twist":
                score += 2.5

            # 当前章有收束 → 适合集末
            if n_ch == ch_id and n_type == "resolution_point":
                score += 1.5

        return score

    # ═══════════════════════════════════════════════════════════
    # 悬念检测
    # ═══════════════════════════════════════════════════════════

    def detect_cliffhanger_elements(
        self, chapter_tail_elements: list[dict]
    ) -> dict:
        """
        检测章末元素是否构成悬念结尾。

        Args:
            chapter_tail_elements: 章末20%的元素

        Returns:
            {is_cliffhanger, confidence, snippet, pattern_type}
        """
        if not chapter_tail_elements:
            return {"is_cliffhanger": False, "confidence": 0.0, "snippet": "", "pattern_type": ""}

        # 取最后15个元素
        tail = chapter_tail_elements[-15:] if len(chapter_tail_elements) > 15 else chapter_tail_elements

        cliff_signals = 0
        total_signals = 0
        snippet = ""
        pattern_type = ""

        for elem in reversed(tail):
            text = elem.get("text", "")
            etype = elem.get("type", "")
            beat = elem.get("beat_type", "")

            total_signals += 1

            # 信号1: 疑问句结尾
            if "?" in text or "？" in text:
                cliff_signals += 2
                if not snippet:
                    snippet = text[:150]
                if not pattern_type:
                    pattern_type = "疑问式悬念"

            # 信号2: 未完成动作
            for marker in ["正要", "刚想", "还未来得及", "尚未", "还不等"]:
                if marker in text:
                    cliff_signals += 1
                    if not snippet:
                        snippet = text[:150]
                    if not pattern_type:
                        pattern_type = "中断式悬念"

            # 信号3: confrontation/revelation beat
            if beat in ("confrontation", "revelation"):
                cliff_signals += 1

            # 信号4: 突然转折
            twist_count = sum(1 for kw in ["突然", "忽然", "不料", "没想到", "谁知"]
                             if kw in text)
            cliff_signals += twist_count

            # 信号5: 新元素/未知引入
            for marker in ["一个黑影", "一道身影", "陌生的", "却不知", "殊不知"]:
                if marker in text:
                    cliff_signals += 1
                    if not pattern_type:
                        pattern_type = "揭示式悬念"

        confidence = min(1.0, cliff_signals / max(total_signals, 1) * 2)

        if not snippet:
            # 取最后一条非空文本
            for elem in reversed(tail):
                text = elem.get("text", "").strip()
                if len(text) > 10:
                    snippet = text[:150]
                    break

        return {
            "is_cliffhanger": confidence >= 0.3,
            "confidence": round(confidence, 2),
            "snippet": snippet,
            "pattern_type": pattern_type or ("弱悬念" if confidence >= 0.1 else ""),
        }

    # ═══════════════════════════════════════════════════════════
    # 情绪峰值检测
    # ═══════════════════════════════════════════════════════════

    def _find_emotion_peak(self, chapter_elements: list[dict]) -> Optional[dict]:
        """找到章节中的情绪峰值"""
        if not chapter_elements:
            return None

        # 统计每段的情绪
        emotion_streak = []
        max_streak_len = 0
        max_streak_pos = 0
        current_streak = 0
        current_start = 0

        for i, elem in enumerate(chapter_elements):
            if elem.get("emotion"):
                if current_streak == 0:
                    current_start = i
                current_streak += 1
            else:
                if current_streak > max_streak_len:
                    max_streak_len = current_streak
                    max_streak_pos = current_start
                current_streak = 0

        if current_streak > max_streak_len:
            max_streak_len = current_streak
            max_streak_pos = current_start

        if max_streak_len < 2:
            return None

        # 取该段的情绪值
        peak_emotions = []
        for elem in chapter_elements[max_streak_pos:max_streak_pos + max_streak_len]:
            if elem.get("emotion"):
                peak_emotions.append(elem["emotion"])

        if not peak_emotions:
            return None

        dominant = Counter(peak_emotions).most_common(1)[0]

        # 强度: 冲突类情绪 > 平静类
        high_intensity_emotions = {"愤怒", "恐惧", "紧张", "惊讶", "厌恶", "嫉妒"}
        is_high = dominant[0] in high_intensity_emotions

        return {
            "position": round(max_streak_pos / len(chapter_elements), 2),
            "emotion": dominant[0],
            "intensity": round(min(1.0, (max_streak_len / 5) * (0.8 if is_high else 0.5)), 2),
        }

    # ═══════════════════════════════════════════════════════════
    # 收束点检测
    # ═══════════════════════════════════════════════════════════

    def _detect_resolution(self, chapter_elements: list[dict]) -> Optional[dict]:
        """检测子情节收束点"""
        if not chapter_elements:
            return None

        # payoff beat 且靠近章末 → 收束点
        for i, elem in enumerate(reversed(chapter_elements)):
            if elem.get("beat_type") == "payoff":
                pos_from_start = len(chapter_elements) - i - 1
                return {
                    "position": round(pos_from_start / len(chapter_elements), 2),
                    "confidence": 0.6 if pos_from_start / len(chapter_elements) > 0.6 else 0.4,
                    "snippet": elem.get("text", "")[:120],
                }

        return None

    # ═══════════════════════════════════════════════════════════
    # 叙事弧线构建
    # ═══════════════════════════════════════════════════════════

    def build_narrative_arc(
        self,
        chapters: list[dict],
        conflict_nodes: list[dict],
    ) -> dict:
        """
        构建跨章节叙事弧线。

        Returns:
            {arc_type, phases: [{chapter_range, phase_name, description}], turning_points}
        """
        if not chapters:
            return {"arc_type": "unknown", "phases": [], "turning_points": []}

        chapter_ids = [ch.get("chapter_id", i + 1)
                       for i, ch in enumerate(chapters)]
        total = len(chapter_ids)

        # 提取关键转折点
        turning_points = [n for n in conflict_nodes
                          if n["type"] in ("major_twist", "resolution_point")]

        # 分类弧线阶段
        phases = []
        if total >= 3:
            act1_end = max(1, total // 4)
            act2_mid = total // 2
            act3_start = total * 3 // 4
            phases = [
                {"chapter_range": f"1-{act1_end}", "phase": "建立",
                 "description": "引入世界观、主要角色、核心冲突"},
                {"chapter_range": f"{act1_end+1}-{act2_mid}", "phase": "对抗升级",
                 "description": "冲突加剧，角色面临越来越大的挑战"},
                {"chapter_range": f"{act2_mid+1}-{act3_start}", "phase": "危机",
                 "description": "局势急转直下，至暗时刻"},
                {"chapter_range": f"{act3_start+1}-{total}", "phase": "高潮与收束",
                 "description": "最终对决，情节收束"},
            ]

        arc_type = "三幕结构" if total >= 3 else "短篇单幕"

        return {
            "arc_type": arc_type,
            "total_chapters": total,
            "phases": phases,
            "turning_points": [
                {"chapter_id": tp["chapter_id"], "type": tp["type"],
                 "description": tp["description"]}
                for tp in turning_points
            ],
        }
