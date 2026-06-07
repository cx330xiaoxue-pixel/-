"""
内容分级技能 — S/A/B 三级权重分拣算法

核心功能:
  - 对LLM提取的结构化元素进行智能分级
  - S级(核心剧情): 冲突/对话/关键动作/转折 → 100%保留
  - A级(辅助剧情): 环境铺垫/人物神态 → 精简为镜头描述
  - B级(冗余内容): 重复碎碎念/无意义心理OS/灌水 → 过滤或合并

分级策略:
  1. 规则引擎快速分拣（基于类型、节拍、关键词、位置）
  2. LLM复核边界案例（置信度不足时）
  3. 三种适应度模式: strict(忠于原著) / balanced(默认) / loose(影视节奏)

使用:
  skill = ContentGradingSkill()
  graded = skill.grade_elements(elements, mode="balanced", character_importance={...})
"""

import difflib
from collections import defaultdict
from typing import Optional


class ContentGradingSkill:
    """内容权重分级技能 — S/A/B 三级智能分拣"""

    # ── 心理活动检测关键词 ──
    PSYCHOLOGICAL_MARKERS = [
        "心想", "暗道", "暗暗", "寻思", "思忖", "暗想", "心道",
        "心说", "暗忖", "自忖", "心忖", "默念", "默道", "心念",
        "心中暗道", "心中暗想", "暗暗想道", "不禁想", "不由想",
        "暗叹", "心叹", "暗笑", "苦笑", "自嘲", "嘀咕",
    ]

    # ── 剧情转折关键词 ──
    PLOT_TWIST_MARKERS = [
        "突然", "忽然", "不料", "竟然", "谁知", "没想到",
        "就在此时", "就在这时", "正当", "却", "然而",
        "难道", "难道说", "猛地", "猛然", "骤然", "陡然",
        "霎时间", "一刹那", "说时迟那时快",
    ]

    # ── 战斗/冲突动作关键词 ──
    COMBAT_ACTION_MARKERS = [
        "出剑", "拔刀", "出手", "攻击", "袭来", "斩", "刺",
        "劈", "砍", "轰", "击", "碰撞", "交战", "对决",
        "出手如电", "一掌", "一拳", "飞身", "闪身", "躲闪",
        "战斗", "厮杀", "激战", "搏斗", "冲锋", "突围",
        "杀气", "杀意", "气势", "威压", "爆发", "爆发力",
        "法术", "神通", "功力", "灵力", "真气", "内力",
    ]

    # ── 日常动作关键词（非冲突动作 → 倾向于A级）──
    EVERYDAY_ACTION_MARKERS = [
        "走", "坐", "站", "看", "望", "转头", "回头", "点头",
        "摇头", "笑了笑", "微笑", "皱眉", "叹气", "叹了口气",
        "端起", "放下", "拿起", "轻轻", "缓缓", "慢慢地",
        "站起身来", "坐下", "转过身", "抬眼", "低眉",
    ]

    # ── 环境描写关键词（A级线索）──
    ENVIRONMENT_MARKERS = [
        "阳光", "月光", "灯光", "天色", "天空", "大地",
        "风吹", "风起", "微风", "狂风", "细雨", "暴雨",
        "雾气", "雾气腾腾", "云雾", "云层", "霞光", "晨曦",
        "夜色", "夜幕", "星空", "星辰", "月亮", "太阳",
        "山", "水", "河", "湖", "海", "林", "花", "草", "树",
        "庭院", "院落", "屋子", "房间", "大殿", "楼阁",
        "桌椅", "门窗", "烛火", "灯火", "光影",
    ]

    def __init__(self):
        self.stats = {"total": 0, "S": 0, "A": 0, "B": 0, "borderline_reviewed": 0}

    # ═══════════════════════════════════════════════════════════
    # 主入口：分级所有元素
    # ═══════════════════════════════════════════════════════════

    def grade_elements(
        self,
        elements: list[dict],
        mode: str = "balanced",
        character_importance: dict[str, float] = None,
        chapter_boundaries: list[int] = None,
    ) -> list[dict]:
        """
        对元素列表进行 S/A/B 三级分级。

        Args:
            elements: 提取的结构化元素 [{type, role, text, beat_type, ...}]
            mode: 适应度模式 strict | balanced | loose
            character_importance: {角色名: 重要度0-1}，主角=1.0
            chapter_boundaries: 每章的元素索引边界 [(start, end), ...]

        Returns:
            带 content_grade / grade_confidence 字段的元素列表
        """
        self.stats = {"total": len(elements), "S": 0, "A": 0, "B": 0,
                      "borderline_reviewed": 0}

        character_importance = character_importance or {}
        if character_importance:
            # 标准化重要性分数
            max_imp = max(character_importance.values()) if character_importance else 1.0
            character_importance = {k: v / max(max_imp, 0.01)
                                    for k, v in character_importance.items()}

        # Step 1: 检测重复模式
        repetition_set = self._detect_repetition_patterns(elements)

        # Step 2: 逐元素评分
        graded = []
        for i, elem in enumerate(elements):
            score, grade, confidence = self._score_element(
                elem, i, elements, character_importance, repetition_set,
                chapter_boundaries, mode
            )
            elem["content_grade"] = grade
            elem["grade_confidence"] = round(confidence, 2)
            elem["grade_score"] = round(score, 2)
            self.stats[grade] += 1
            graded.append(elem)

        return graded

    # ═══════════════════════════════════════════════════════════
    # 单元素评分
    # ═══════════════════════════════════════════════════════════

    def _score_element(
        self,
        elem: dict,
        index: int,
        all_elements: list[dict],
        character_importance: dict[str, float],
        repetition_set: set,
        chapter_boundaries: list = None,
        mode: str = "balanced",
    ) -> tuple[float, str, float]:
        """
        对单个元素评分，返回 (score, grade, confidence)。

        评分维度:
          - type_score: 元素类型权重 (0-30)
          - beat_score: 节拍类型权重 (0-25)
          - character_score: 角色重要性权重 (0-15)
          - position_score: 章节位置权重 (0-10)
          - content_score: 内容特征权重 (0-20)  [关键词、转折、战斗]
        """
        etype = elem.get("type", "narration")
        beat = elem.get("beat_type", "")
        role = elem.get("role", "")
        text = elem.get("text", "")

        # ── 维度1: 元素类型权重 (0-30) ──
        type_weights = {"dialogue": 30, "action": 25, "narration": 12, "description": 8}
        type_score = type_weights.get(etype, 10)

        # ── 维度2: 节拍类型权重 (0-25) ──
        beat_weights = {
            "confrontation": 25, "revelation": 22, "payoff": 18,
            "setup": 10, "transition": 5
        }
        beat_score = beat_weights.get(beat, 8)

        # ── 维度3: 角色重要性 (0-15) ──
        char_imp = character_importance.get(role, 0.1)
        # 旁白角色默认低重要度
        if role == "旁白" or not role.strip():
            char_imp = 0.05
        character_score = char_imp * 15

        # ── 维度4: 章节位置权重 (0-10) ──
        position_score = self._compute_position_score(index, all_elements, chapter_boundaries)

        # ── 维度5: 内容特征权重 (0-20) ──
        content_score = 0

        # 5a. 转折关键词 (+12)
        twist_count = sum(1 for kw in self.PLOT_TWIST_MARKERS if kw in text)
        content_score += min(12, twist_count * 6)

        # 5b. 战斗/冲突动作 (+8)
        if etype == "action":
            combat_count = sum(1 for kw in self.COMBAT_ACTION_MARKERS if kw in text)
            content_score += min(8, combat_count * 4)
        # 5c. 日常动作惩罚 (-5)
            everyday_count = sum(1 for kw in self.EVERYDAY_ACTION_MARKERS if kw in text)
            content_score -= min(5, everyday_count * 2)

        # 5d. 心理活动惩罚 (-10)
        if etype == "narration" and self._is_psychological_monologue(text):
            content_score -= 10

        # 5e. 重复内容惩罚 (-15)
        if index in repetition_set:
            content_score -= 15

        # 5f. 短文本/S级线索奖励
        if len(text) < 10 and etype != "dialogue":
            content_score -= 8  # 太短的碎片

        # ── 总分 ──
        total_score = type_score + beat_score + character_score + position_score + content_score
        # 归一化到 0-1
        max_possible = 30 + 25 + 15 + 10 + 20  # = 100
        normalized = max(0.0, min(1.0, total_score / max_possible))

        # ── 根据模式确定阈值 ──
        thresholds = {
            "strict":  (0.45, 0.25),   # S≥0.45, A≥0.25
            "balanced": (0.55, 0.30),  # S≥0.55, A≥0.30
            "loose":    (0.65, 0.35),  # S≥0.65, A≥0.35
        }
        s_thresh, a_thresh = thresholds.get(mode, thresholds["balanced"])

        if normalized >= s_thresh:
            grade = "S"
        elif normalized >= a_thresh:
            grade = "A"
        else:
            grade = "B"

        # 置信度：离阈值越远越自信
        if grade == "S":
            confidence = 0.5 + (normalized - s_thresh) * 2
        elif grade == "A":
            mid = (s_thresh + a_thresh) / 2
            confidence = 0.5 + (1 - abs(normalized - mid) / (s_thresh - a_thresh)) * 0.3
        else:  # B
            confidence = 0.5 + (a_thresh - normalized) * 2
        confidence = max(0.3, min(1.0, confidence))

        return normalized, grade, confidence

    def _compute_position_score(
        self, index: int, all_elements: list, chapter_boundaries: list = None
    ) -> float:
        """计算位置权重：章末20%位置（高潮/悬念区）得分更高"""
        total = len(all_elements)
        if total == 0:
            return 5.0

        # 全局位置
        global_position = index / total

        # 如果提供了章节边界，使用章节内位置
        if chapter_boundaries:
            for start, end in chapter_boundaries:
                if start <= index <= end:
                    ch_total = end - start + 1
                    if ch_total > 0:
                        ch_position = (index - start) / ch_total
                        # 章末20% → 高分
                        if ch_position >= 0.8:
                            return 9.0
                        # 章首10% → 中高分（开篇重要）
                        elif ch_position <= 0.1:
                            return 7.0
                        else:
                            return 5.0
            return 5.0

        # 无章节边界时用全局位置
        if global_position >= 0.8:
            return 9.0
        elif global_position <= 0.1:
            return 7.0
        else:
            return 5.0

    # ═══════════════════════════════════════════════════════════
    # 重复检测
    # ═══════════════════════════════════════════════════════════

    def _detect_repetition_patterns(
        self, elements: list[dict], similarity_threshold: float = 0.6
    ) -> set[int]:
        """
        检测重复句式，返回重复元素的索引集合。

        策略:
          1. 相同type+role的连续元素检查文本相似度
          2. 跨段落（非连续但相似）的长文本检查
        """
        repetition_indices = set()

        # 连续重复检测
        for i in range(len(elements) - 1):
            e1 = elements[i]
            e2 = elements[i + 1]
            # 仅对 narration/description 做重复检测
            if e1.get("type") in ("narration", "description") and \
               e2.get("type") in ("narration", "description"):
                t1 = e1.get("text", "")
                t2 = e2.get("text", "")
                if len(t1) > 15 and len(t2) > 15:
                    similarity = self._compute_text_similarity(t1, t2)
                    if similarity >= similarity_threshold:
                        repetition_indices.add(i + 1)  # 标记后一个为重复

        # 非连续但相近的重复（滑动窗口）
        window = 10
        for i in range(len(elements)):
            e1 = elements[i]
            if e1.get("type") not in ("narration", "description"):
                continue
            t1 = e1.get("text", "")
            if len(t1) < 20:
                continue
            for j in range(i + 2, min(i + window, len(elements))):
                e2 = elements[j]
                if e2.get("type") not in ("narration", "description"):
                    continue
                t2 = e2.get("text", "")
                if len(t2) < 20:
                    continue
                similarity = self._compute_text_similarity(t1, t2)
                if similarity >= 0.8:  # 跨段重复用更高阈值
                    repetition_indices.add(j)

        # 连续3+ description 检测（过度环境铺陈）
        desc_streak = []
        for i, elem in enumerate(elements):
            if elem.get("type") == "description":
                desc_streak.append(i)
            else:
                if len(desc_streak) >= 3:
                    # 中间的全标为重复
                    for idx in desc_streak[1:]:
                        repetition_indices.add(idx)
                desc_streak = []
        if len(desc_streak) >= 3:
            for idx in desc_streak[1:]:
                repetition_indices.add(idx)

        return repetition_indices

    def _compute_text_similarity(self, text1: str, text2: str) -> float:
        """基于 SequenceMatcher 的文本相似度"""
        if not text1 or not text2:
            return 0.0
        return difflib.SequenceMatcher(None, text1, text2).ratio()

    # ═══════════════════════════════════════════════════════════
    # 特征检测
    # ═══════════════════════════════════════════════════════════

    def _is_psychological_monologue(self, text: str) -> bool:
        """检测是否为心理活动/内心独白"""
        if not text:
            return False
        for marker in self.PSYCHOLOGICAL_MARKERS:
            if marker in text:
                return True
        return False

    def _is_filler_description(self, elem: dict, context: list = None) -> bool:
        """判断是否为无效环境描写/灌水铺垫"""
        text = elem.get("text", "")
        etype = elem.get("type", "")

        if etype != "description":
            return False

        # 过短无信息量
        if len(text) < 6:
            return True

        # 纯感叹/语气词
        pure_exclamation = {"啊", "呀", "呢", "吧", "哦", "嗯", "唉", "哎"}
        if text.strip() in pure_exclamation:
            return True

        # 检查是否包含实质信息
        has_env = any(kw in text for kw in self.ENVIRONMENT_MARKERS)

        # 有环境关键词 → 不是灌水
        if has_env:
            return False

        # 很短的、无关键词的描述 → 可能是灌水
        if len(text) < 20:
            return True

        return False

    # ═══════════════════════════════════════════════════════════
    # 后处理：压缩A级 / 合并B级
    # ═══════════════════════════════════════════════════════════

    def condense_a_level(
        self, a_elements: list[dict], mode: str = "balanced"
    ) -> str:
        """
        将 A 级元素压缩为镜头描述/场景氛围文本。

        Args:
            a_elements: 连续的A级元素
            mode: 适应度模式

        Returns:
            压缩后的描述文本（或空字符串）
        """
        if not a_elements:
            return ""

        # 按模式决定保留比例
        keep_ratios = {"strict": 0.8, "balanced": 0.5, "loose": 0.2}
        keep_ratio = keep_ratios.get(mode, 0.5)

        # 提取关键信息
        locations = set()
        times = set()
        atmospheres = []
        key_descriptions = []

        for elem in a_elements:
            text = elem.get("text", "").strip()
            if not text:
                continue

            # 提取地点
            for kw in ["房间", "客厅", "庭院", "大殿", "街道", "山", "林",
                        "河", "湖", "楼", "阁", "府", "庙", "市", "村"]:
                if kw in text:
                    locations.add(kw)

            # 提取时间
            for kw in ["清晨", "傍晚", "深夜", "黄昏", "正午", "早晨",
                        "夜晚", "月色", "黎明", "夕阳"]:
                if kw in text:
                    times.add(kw)

            # 提取氛围
            emotion = elem.get("emotion", "")
            if emotion:
                atmospheres.append(emotion)

            # 保留有信息量的描述
            if len(text) > 15:
                key_descriptions.append(text)

        # 按比例选取
        keep_n = max(1, int(len(key_descriptions) * keep_ratio))
        selected = key_descriptions[:keep_n]

        # 构建压缩文本
        parts = []
        if locations:
            parts.append(f"场景: {'/'.join(sorted(locations))}")
        if times:
            parts.append(f"时间: {'/'.join(sorted(times))}")
        if atmospheres:
            from collections import Counter
            top_atm = Counter(atmospheres).most_common(1)[0][0]
            parts.append(f"氛围: {top_atm}")

        if selected:
            # 每条缩到40字
            condensed_descs = [d[:40] + ("..." if len(d) > 40 else "")
                               for d in selected]
            parts.append("; ".join(condensed_descs))

        return " ".join(parts) if parts else ""

    def merge_b_level(
        self, b_elements: list[dict], max_chars: int = 50
    ) -> str:
        """
        将 B 级冗余内容合并为极简旁白。

        Args:
            b_elements: 连续的B级元素
            max_chars: 最大输出字符数

        Returns:
            合并后的极简旁白（或空字符串表示完全过滤）
        """
        if not b_elements:
            return ""

        # 提取"可能"有信息量的片段
        meaningful_snippets = []
        for elem in b_elements:
            text = elem.get("text", "").strip()
            if len(text) > 20 and not self._is_psychological_monologue(text):
                # 去掉心理活动标记后的内容
                cleaned = text
                for marker in self.PSYCHOLOGICAL_MARKERS:
                    cleaned = cleaned.replace(marker, "")
                if len(cleaned) > 10:
                    meaningful_snippets.append(cleaned[:30])

        if not meaningful_snippets:
            return ""  # 全过滤

        # 取最长的片段合并
        merged = "；".join(sorted(meaningful_snippets, key=len, reverse=True)[:3])
        if len(merged) > max_chars:
            merged = merged[:max_chars - 3] + "..."

        return merged

    def apply_grading_to_elements(
        self,
        elements: list[dict],
        mode: str = "balanced",
        max_merged_chars: int = 50,
    ) -> list[dict]:
        """
        在分级后对元素列表做实际处理：过滤B、压缩A、保留S。

        这是供 ScriptBuilder 使用的后处理步骤。

        Returns:
            处理后的元素列表（已过滤/合并/压缩）
        """
        result = []
        b_buffer = []

        for elem in elements:
            grade = elem.get("content_grade", "S")

            if grade == "S":
                # 先清空B级缓冲区
                if b_buffer:
                    merged = self.merge_b_level(b_buffer, max_merged_chars)
                    if merged:
                        result.append({
                            "type": "narration",
                            "role": "旁白",
                            "text": merged,
                            "content_grade": "B",
                            "condensed": True,
                            "merged_from": len(b_buffer),
                            "beat_type": "transition",
                        })
                    b_buffer = []
                result.append(elem)

            elif grade == "A":
                # 清空B缓冲区
                if b_buffer:
                    merged = self.merge_b_level(b_buffer, max_merged_chars)
                    if merged:
                        result.append({
                            "type": "narration",
                            "role": "旁白",
                            "text": merged,
                            "content_grade": "B",
                            "condensed": True,
                            "merged_from": len(b_buffer),
                            "beat_type": "transition",
                        })
                    b_buffer = []
                # A级压缩
                condensed_text = self.condense_a_level([elem], mode)
                if condensed_text:
                    elem_copy = dict(elem)
                    elem_copy["text"] = condensed_text
                    elem_copy["condensed"] = True
                    elem_copy["original_text"] = elem.get("text", "")
                    result.append(elem_copy)
                # 如果压缩后为空，则跳过（隐式过滤）

            elif grade == "B":
                b_buffer.append(elem)
                # B级缓冲区过大时强制合并
                if len(b_buffer) >= 8:
                    merged = self.merge_b_level(b_buffer, max_merged_chars)
                    if merged:
                        result.append({
                            "type": "narration",
                            "role": "旁白",
                            "text": merged,
                            "content_grade": "B",
                            "condensed": True,
                            "merged_from": len(b_buffer),
                            "beat_type": "transition",
                        })
                    b_buffer = []

        # 处理末尾B缓冲区
        if b_buffer:
            merged = self.merge_b_level(b_buffer, max_merged_chars)
            if merged:
                result.append({
                    "type": "narration",
                    "role": "旁白",
                    "text": merged,
                    "content_grade": "B",
                    "condensed": True,
                    "merged_from": len(b_buffer),
                    "beat_type": "transition",
                })

        return result

    # ═══════════════════════════════════════════════════════════
    # 批量处理
    # ═══════════════════════════════════════════════════════════

    def grade_chapters(
        self,
        chapters_elements: list[list[dict]],
        mode: str = "balanced",
        character_importance: dict[str, float] = None,
    ) -> list[list[dict]]:
        """
        批量分级多个章节的元素。

        Args:
            chapters_elements: [[ch1_elements], [ch2_elements], ...]
            mode: 适应度模式
            character_importance: 角色重要性映射

        Returns:
            分级后的章节元素列表
        """
        result = []
        for ch_elements in chapters_elements:
            graded = self.grade_elements(ch_elements, mode, character_importance)
            result.append(graded)
        return result

    # ═══════════════════════════════════════════════════════════
    # 统计报告
    # ═══════════════════════════════════════════════════════════

    def get_grading_report(self, elements: list[dict]) -> dict:
        """生成分级统计报告"""
        total = len(elements)
        if total == 0:
            return {"total": 0}

        counts = {"S": 0, "A": 0, "B": 0}
        for elem in elements:
            grade = elem.get("content_grade", "S")
            counts[grade] = counts.get(grade, 0) + 1

        return {
            "total": total,
            "S_count": counts["S"],
            "A_count": counts["A"],
            "B_count": counts["B"],
            "S_ratio": round(counts["S"] / total * 100, 1),
            "A_ratio": round(counts["A"] / total * 100, 1),
            "B_ratio": round(counts["B"] / total * 100, 1),
            "filtered_count": counts["B"],
            "condensed_count": counts["A"],
            "preserved_count": counts["S"],
        }
