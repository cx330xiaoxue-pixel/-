"""
分集规划 Skill — 章节→集映射、情绪节奏模板、悬念钩子设计

可被 episode-architect 和 emotion-architect Agent 复用。
"""

from collections import defaultdict
from typing import Optional


class EpisodePlanningSkill:
    """分集规划核心技能"""

    def __init__(self):
        # 标准电视剧集结构模板
        self.episode_templates = {
            "cold_open": "冷开场 — 5分钟悬念/动作场面，抓住观众注意力",
            "teaser": "引子 — 铺垫本集核心冲突",
            "act1": "第一幕 — 建立情境，引入问题 (15-20分钟)",
            "act2": "第二幕 — 冲突升级，角色应对 (15-20分钟)",
            "act3": "第三幕 — 高潮/转折，为下集埋钩 (10-15分钟)",
            "cliffhanger": "悬念钩子 — 让观众迫不及待想看下一集",
        }

        # 情绪节奏模板
        self.emotion_rhythm_templates = {
            "standard": {
                "description": "标准起伏型 — 每集有明确的情绪上升和释放",
                "pattern": [3, 5, 7, 6, 8, 7, 9, 5],  # 情感强度 1-10
            },
            "roller_coaster": {
                "description": "过山车型 — 高频率情感切换，适合动作/悬疑",
                "pattern": [5, 8, 4, 9, 3, 8, 5, 9],
            },
            "slow_burn": {
                "description": "慢热型 — 情感递进缓慢但持久，适合文艺/伦理",
                "pattern": [2, 3, 4, 5, 5, 6, 7, 8],
            },
            "tension_release": {
                "description": "紧张释放型 — 积压→爆发→喘息→再积压",
                "pattern": [3, 4, 6, 8, 9, 4, 7, 9],
            },
        }

    # ═══════════════════════════════════════════════════════════
    # 章节→集 映射
    # ═══════════════════════════════════════════════════════════

    def map_chapters_to_episodes(
        self,
        chapter_count: int,
        target_episodes: int,
        chapter_elements: dict = None,
        chapter_emotions: dict = None,
    ) -> list[dict]:
        """
        将小说章节映射为电视剧集。

        Args:
            chapter_count: 总章节数
            target_episodes: 目标集数
            chapter_elements: {chapter_id: element_count} 每章元素数
            chapter_emotions: {chapter_id: [emotions]} 每章情绪列表

        Returns:
            [{episode_id, chapters_range, element_count, hook_suggestion, ...}]
        """
        if chapter_count <= 0 or target_episodes <= 0:
            return []

        # 基础映射比例
        chapters_per_ep = max(1, chapter_count / target_episodes)

        episodes = []
        current_chapter = 1

        for ep_id in range(1, target_episodes + 1):
            # 动态调整每集章节数（基于剩余章数和集数）
            remaining_chapters = chapter_count - current_chapter + 1
            remaining_eps = target_episodes - ep_id + 1
            ch_count = max(1, round(remaining_chapters / remaining_eps))

            start_ch = current_chapter
            end_ch = min(chapter_count, current_chapter + ch_count - 1)

            # 计算元素数
            elem_count = 0
            if chapter_elements:
                for ch in range(start_ch, end_ch + 1):
                    elem_count += chapter_elements.get(ch, 0)

            # 确定情绪峰值章节
            peak_chapter = start_ch
            if chapter_emotions:
                max_intensity = 0
                for ch in range(start_ch, end_ch + 1):
                    emotions = chapter_emotions.get(ch, [])
                    # 情绪强度简化为数量
                    intensity = len(emotions)
                    if intensity > max_intensity:
                        max_intensity = intensity
                        peak_chapter = ch

            # 悬念钩子建议
            hook = None
            if ep_id < target_episodes:
                hook = f"第{end_ch}章结尾的悬念可作为第{ep_id}集的Cliffhanger"

            episodes.append({
                "episode_id": ep_id,
                "chapters_range": f"第{start_ch}-{end_ch}章",
                "chapter_ids": list(range(start_ch, end_ch + 1)),
                "start_chapter": start_ch,
                "end_chapter": end_ch,
                "chapter_count": end_ch - start_ch + 1,
                "estimated_elements": elem_count,
                "peak_chapter": peak_chapter,
                "episode_title_hint": f"第{ep_id}集",
                "hook_suggestion": hook,
                "act_structure": (
                    f"Act1: 第{start_ch}章 | "
                    f"Act2: 第{start_ch+1}-{end_ch-1}章 | "
                    f"Act3: 第{end_ch}章"
                ) if end_ch - start_ch >= 2 else "单章/双章结构",
            })

            current_chapter = end_ch + 1
            if current_chapter > chapter_count:
                break

        return episodes

    # ═══════════════════════════════════════════════════════════
    # 情绪曲线设计
    # ═══════════════════════════════════════════════════════════

    def design_emotion_curve(
        self,
        episodes: list[dict],
        style: str = "standard",
        chapter_emotions: dict = None,
    ) -> list[dict]:
        """
        为各集设计情绪曲线。

        Args:
            episodes: 分集映射结果
            style: 情绪风格 (standard | roller_coaster | slow_burn | tension_release)
            chapter_emotions: 各章的情绪数据

        Returns:
            [{episode_id, emotion_sequence, peak, valley, pattern}]
        """
        template = self.emotion_rhythm_templates.get(
            style, self.emotion_rhythm_templates["standard"]
        )

        curves = []
        for ep in episodes:
            # 基于模板生成情绪序列
            ch_count = ep["chapter_count"]
            pattern = self._interpolate_pattern(template["pattern"], ch_count * 2)

            # 如果有实际情绪数据，融合
            if chapter_emotions:
                for ch_id in ep["chapter_ids"]:
                    emotions = chapter_emotions.get(ch_id, [])
                    if emotions:
                        # 取主导情绪对应的强度
                        from collections import Counter
                        dominant = Counter(emotions).most_common(1)[0][0]
                        # 简单映射：情绪 → 强度
                        intensity = self._emotion_to_intensity(dominant)
                        idx = (ch_id - ep["start_chapter"]) * 2
                        if idx < len(pattern):
                            pattern[idx] = (pattern[idx] + intensity) // 2

            curves.append({
                "episode_id": ep["episode_id"],
                "emotion_sequence": pattern,
                "peak_value": max(pattern),
                "valley_value": min(pattern),
                "peak_position": pattern.index(max(pattern)) + 1,
                "style": style,
                "rhythm_description": template["description"],
            })

        return curves

    def _interpolate_pattern(self, template: list, target_length: int) -> list:
        """将模板插值到目标长度"""
        if len(template) >= target_length:
            return template[:target_length]
        result = []
        for i in range(target_length):
            idx = int(i * len(template) / target_length)
            result.append(template[min(idx, len(template) - 1)])
        return result

    def _emotion_to_intensity(self, emotion: str) -> int:
        """将情绪标签映射为强度值 1-10"""
        mapping = {
            "喜悦": 8, "快乐": 7, "愤怒": 9, "恐惧": 8, "紧张": 7,
            "悲伤": 3, "温柔": 4, "惊讶": 7, "厌恶": 6, "坚定": 6,
            "轻蔑": 5, "愧疚": 3, "嫉妒": 6, "平静": 2, "焦虑": 6,
        }
        return mapping.get(emotion, 5)

    # ═══════════════════════════════════════════════════════════
    # 悬念钩子设计
    # ═══════════════════════════════════════════════════════════

    def generate_hooks(
        self,
        episodes: list[dict],
        all_elements: list = None,
        strategy: str = "cliffhanger",
    ) -> dict[int, str]:
        """
        为每集设计悬念钩子。

        Args:
            episodes: 分集规划
            all_elements: 所有结构化元素（用于检测现有悬念）
            strategy: 钩子策略 (cliffhanger | mystery | emotional | mixed)

        Returns:
            {episode_id: hook_text}
        """
        hooks = {}

        # 如果提供了元素，检测章末的悬念内容
        chapter_hooks = {}
        if all_elements:
            chapter_groups = defaultdict(list)
            for e in all_elements:
                chapter_groups[e.get("chapter_id", 0)].append(e)

            for ch_id, elements in chapter_groups.items():
                tail = elements[-15:]  # 最后15个元素
                for e in reversed(tail):
                    text = e.get("text", "")
                    # 检测悬念关键词
                    suspense_kw = ["突然", "忽然", "却", "然而", "但", "不料",
                                   "谁知", "没想到", "竟然", "难道"]
                    for kw in suspense_kw:
                        if kw in text:
                            chapter_hooks[ch_id] = text[:150]
                            break
                    if ch_id in chapter_hooks:
                        break

        # 为每集分配钩子
        for ep in episodes:
            ep_id = ep["episode_id"]
            end_ch = ep["end_chapter"]

            # 优先使用检测到的章末悬念
            if end_ch in chapter_hooks:
                hooks[ep_id] = chapter_hooks[end_ch]

            elif ep_id < len(episodes):
                # 根据策略生成钩子
                if strategy == "cliffhanger":
                    hooks[ep_id] = (
                        f"[悬念钩子] 第{ep_id}集结尾应留悬念："
                        f"角色面临关键抉择 / 新威胁出现 / 真相部分揭露"
                    )
                elif strategy == "mystery":
                    hooks[ep_id] = (
                        f"[谜题钩子] 第{ep_id}集结尾应揭示一个谜题线索，"
                        f"但同时引出更大的谜团"
                    )
                elif strategy == "emotional":
                    hooks[ep_id] = (
                        f"[情感钩子] 第{ep_id}集结尾应聚焦角色情感转折，"
                        f"让观众对角色命运产生共情"
                    )
                else:  # mixed
                    hooks[ep_id] = (
                        f"[混合钩子] 第{ep_id}集结尾需同时包含悬念和情感共鸣，"
                        f"保持观众的兴趣和情感投入"
                    )

        return hooks

    # ═══════════════════════════════════════════════════════════
    # 全剧结构设计
    # ═══════════════════════════════════════════════════════════

    def design_series_structure(
        self,
        episodes: list[dict],
        total_episodes: int,
    ) -> dict:
        """
        设计全剧的宏观结构。

        Returns:
            {season_arc, act_breakdown, key_turning_points}
        """
        # 全剧幕结构
        if total_episodes <= 10:
            season_structure = "迷你剧 — 单季完整故事"
        elif total_episodes <= 24:
            season_structure = "标准季 — 24集以内，适合黄金档"
        elif total_episodes <= 40:
            season_structure = "长剧 — 40集以内，可分上下半季"
        else:
            season_structure = "超长剧 — 建议分多季"

        # 关键转折点
        turning_points = []
        if total_episodes >= 3:
            turning_points.append({
                "episode": 1,
                "type": "inciting_incident",
                "description": "激励事件 — 打破主角日常，推动故事开始",
            })
        if total_episodes >= 5:
            turning_points.append({
                "episode": max(2, total_episodes // 4),
                "type": "first_act_break",
                "description": "第一幕转折 — 主角做出不可逆的选择",
            })
        if total_episodes >= 8:
            turning_points.append({
                "episode": total_episodes // 2,
                "type": "midpoint",
                "description": "中点转折 — 局势发生质变，假胜利或假失败",
            })
        if total_episodes >= 12:
            turning_points.append({
                "episode": total_episodes * 3 // 4,
                "type": "all_is_lost",
                "description": "至暗时刻 — 主角看似已无希望",
            })
        if total_episodes >= 3:
            turning_points.append({
                "episode": total_episodes,
                "type": "climax",
                "description": "最终高潮 — 核心冲突的最终对决与解决",
            })

        return {
            "season_structure": season_structure,
            "total_episodes": total_episodes,
            "key_turning_points": turning_points,
            "recommended_cliffhanger_episodes": self._recommend_cliffhangers(
                total_episodes
            ),
        }

    def _recommend_cliffhangers(self, total: int) -> list[int]:
        """推荐应在结尾留悬念的集数"""
        if total <= 3:
            return list(range(1, total))  # 除最后一集外全部
        elif total <= 12:
            return [3, 6, 9] + ([total - 1] if total > 3 else [])
        else:
            # 每4-5集一个强悬念
            return list(range(4, total, 4)) + [total - 1]

    # ═══════════════════════════════════════════════════════════
    # 分集报告
    # ═══════════════════════════════════════════════════════════

    def generate_episode_plan_report(
        self,
        title: str,
        episodes: list[dict],
        series_structure: dict,
        hooks: dict,
        emotion_curves: list = None,
    ) -> str:
        """生成分集规划报告 (Markdown)"""
        report = []
        report.append(f"# 分集规划报告 — 《{title}》\n")
        report.append(f"**总集数**: {len(episodes)}")
        report.append(f"**全剧结构**: {series_structure.get('season_structure', '未知')}\n")
        report.append("---\n")

        # 全剧关键转折点
        report.append("## 全剧关键转折点\n")
        for tp in series_structure.get("key_turning_points", []):
            report.append(f"- **第{tp['episode']}集** [{tp['type']}]: {tp['description']}")

        cliffhangers = series_structure.get("recommended_cliffhanger_episodes", [])
        if cliffhangers:
            report.append(f"\n### 推荐悬念集数")
            report.append(f"建议在以下集数结尾设置强力悬念钩子: "
                         f"{', '.join(f'第{ep}集' for ep in cliffhangers)}")

        report.append("\n---\n")

        # 逐集规划
        report.append("## 逐集规划详情\n")
        for ep in episodes:
            ep_id = ep["episode_id"]
            report.append(f"### 第{ep_id}集 — {ep.get('episode_title_hint', '')}")
            report.append(f"- **覆盖章节**: {ep['chapters_range']} ({ep['chapter_count']}章)")
            report.append(f"- **预估元素数**: {ep.get('estimated_elements', '?')}")
            report.append(f"- **幕结构**: {ep.get('act_structure', '?')}")
            report.append(f"- **情绪峰值章节**: 第{ep.get('peak_chapter', '?')}章")

            if ep_id in hooks:
                report.append(f"- **悬念钩子**: {hooks[ep_id][:200]}")

            # 情绪曲线
            if emotion_curves:
                matching = [c for c in emotion_curves if c["episode_id"] == ep_id]
                if matching:
                    curve = matching[0]
                    bar = self._emotion_bar(curve["emotion_sequence"])
                    report.append(f"- **情绪曲线**: {bar}")
                    report.append(f"  峰值: {curve['peak_value']} (位置{curve['peak_position']}) | "
                                 f"谷值: {curve['valley_value']}")

            report.append("")

        return "\n".join(report)

    def _emotion_bar(self, sequence: list, max_chars: int = 40) -> str:
        """将情绪序列可视化为单行文本"""
        chars = "▁▂▃▄▅▆▇█"
        bar = ""
        for v in sequence:
            idx = min(len(chars) - 1, max(0, int(v / 10 * (len(chars) - 1))))
            bar += chars[idx]
        return bar[:max_chars]
