"""
分镜技能合集 — 标准分镜(Film) + Seedance AI 分镜

包含:
  - FilmStoryboardSkill: Beat Board → Sequence Board → Motion Prompt
  - SeedanceStoryboardSkill: Director Analysis → Art Design → Seedance Prompts
"""

import os
from datetime import datetime
from typing import Optional


# ═══════════════════════════════════════════════════════════════
# 1. FilmStoryboardSkill — 标准电影分镜
# ═══════════════════════════════════════════════════════════════

class FilmStoryboardSkill:
    """标准电影分镜技能 — Beat Board → Sequence Board → Motion Prompt"""

    # 镜头类型参考
    SHOT_TYPES = {
        "establishing": {"name": "定场镜头", "description": "建立场景空间关系的大远景/全景"},
        "wide": {"name": "全景", "description": "展示角色全身及环境关系"},
        "medium": {"name": "中景", "description": "角色膝盖以上，强调肢体语言"},
        "close_up": {"name": "特写", "description": "面部或物体细节，强调情感"},
        "extreme_close_up": {"name": "大特写", "description": "眼睛/手指等极限细节"},
        "over_shoulder": {"name": "过肩镜头", "description": "从角色背后拍摄，建立对话空间"},
        "pov": {"name": "主观镜头", "description": "角色视角，观众所见即角色所见"},
        "dutch": {"name": "倾斜镜头", "description": "画面倾斜，表示失衡/不安"},
        "tracking": {"name": "跟拍", "description": "摄影机跟随角色移动"},
        "crane": {"name": "升降镜头", "description": "从高处下降或从低处升起"},
    }

    # 节拍 → 推荐镜头 映射
    BEAT_SHOT_MAP = {
        "setup": ["establishing", "wide", "medium"],
        "confrontation": ["close_up", "over_shoulder", "dutch", "tracking"],
        "payoff": ["close_up", "extreme_close_up", "crane"],
        "transition": ["wide", "establishing", "tracking"],
        "revelation": ["extreme_close_up", "close_up", "pov", "dutch"],
    }

    # 情绪 → 调色板
    EMOTION_PALETTE = {
        "喜悦": "暖金色调，高饱和度，柔光",
        "愤怒": "高对比度，冷蓝阴影，手持晃动",
        "悲伤": "低饱和度，蓝色调，柔焦",
        "恐惧": "暗调，绿色调，高对比，快速切换",
        "紧张": "中灰调，稳定构图，渐增的镜头切换频率",
        "温柔": "柔光，暖色调，浅景深，慢速运镜",
        "平静": "自然光，中饱和度，固定机位/慢摇",
        "惊讶": "强对比，快速变焦，白闪过渡",
    }

    def analyze_beats(self, elements: list) -> list[dict]:
        """
        从剧本元素中识别关键节拍 (Beat Analysis)。

        Returns:
            [{beat_id, beat_type, elements, emotion, shot_suggestion, visual_moment}]
        """
        beats = []
        current_beat = None

        for elem in elements:
            beat_type = elem.get("beat_type", "")
            emotion = elem.get("emotion", "")

            # 新的节拍开始
            if beat_type and (not current_beat or beat_type != current_beat.get("beat_type")):
                if current_beat:
                    beats.append(current_beat)
                current_beat = {
                    "beat_id": len(beats) + 1,
                    "beat_type": beat_type,
                    "elements": [],
                    "emotion": emotion,
                    "shot_suggestions": self.BEAT_SHOT_MAP.get(beat_type, ["medium"]),
                    "visual_moment": elem.get("visual_hint", ""),
                }
            if current_beat:
                current_beat["elements"].append(elem)
                if emotion and not current_beat["emotion"]:
                    current_beat["emotion"] = emotion

        if current_beat:
            beats.append(current_beat)

        return beats

    def generate_beat_board(self, beats: list[dict], episode: int) -> dict:
        """
        生成 Beat Board（九宫格式节拍板）。

        选9个关键节拍，每个配缩略图描述和镜头建议。

        Returns:
            {episode, grid: [...], total_beats}
        """
        # 选最重要/最具视觉性的 9 个节拍
        key_beats = self._select_key_beats(beats, max_count=9)

        grid = []
        for i, beat in enumerate(key_beats):
            # 生成缩略图描述
            thumbnail = self._generate_beat_thumbnail(beat)
            grid.append({
                "position": i + 1,
                "beat_type": beat["beat_type"],
                "emotion": beat["emotion"],
                "shot_type": beat["shot_suggestions"][0] if beat["shot_suggestions"] else "medium",
                "thumbnail_description": thumbnail,
                "element_count": len(beat["elements"]),
            })

        return {
            "episode": episode,
            "grid": grid,
            "total_beats_analyzed": len(beats),
            "key_beats_selected": len(key_beats),
        }

    def _select_key_beats(self, beats: list, max_count: int = 9) -> list:
        """选择关键节拍（优先 confrontation/revelation/payoff）"""
        priority_order = ["revelation", "payoff", "confrontation", "setup", "transition"]
        selected = []
        seen_types = set()

        # 先按优先级选
        for priority in priority_order:
            for beat in beats:
                if beat["beat_type"] == priority and len(selected) < max_count:
                    if beat["beat_type"] not in seen_types or len(selected) < max_count - 3:
                        selected.append(beat)
                        seen_types.add(beat["beat_type"])

        # 如果不够，补充
        for beat in beats:
            if beat not in selected and len(selected) < max_count:
                selected.append(beat)

        return sorted(selected, key=lambda b: b["beat_id"])[:max_count]

    def _generate_beat_thumbnail(self, beat: dict) -> str:
        """生成节拍的缩略图描述"""
        elements = beat["elements"]
        if not elements:
            return "空场景"

        # 取第一个有实质内容的元素
        for e in elements:
            text = e.get("text", "")
            if len(text) > 10:
                preview = text[:80]
                shot = self.SHOT_TYPES.get(
                    beat["shot_suggestions"][0] if beat["shot_suggestions"] else "medium",
                    {"name": "中景"},
                )
                return f"[{shot['name']}] {preview}"

        return f"[{beat['beat_type']}] — {beat['emotion']}"

    def generate_sequence_board(
        self, beat_board: dict, scenes: list = None
    ) -> list[dict]:
        """
        生成 Sequence Board — 将 Beat Board 展开为具体镜头序列。

        Returns:
            [{shot_id, shot_type, duration, description, camera_movement, transition}]
        """
        sequences = []
        shot_id = 0

        for beat in beat_board.get("grid", []):
            # 每个关键节拍生成 2-4 个镜头
            shot_count = {
                "setup": 2,
                "confrontation": 4,
                "payoff": 3,
                "transition": 2,
                "revelation": 3,
            }.get(beat["beat_type"], 2)

            for s in range(shot_count):
                shot_id += 1
                shot_type = beat["shot_type"]
                if s == 0:
                    camera = "静态 / 缓慢推近"
                elif s == shot_count - 1:
                    camera = "加速 / 急推"
                else:
                    camera = "跟拍 / 环绕"

                sequences.append({
                    "shot_id": shot_id,
                    "shot_type": shot_type,
                    "duration_seconds": self._estimate_shot_duration(beat["beat_type"], s),
                    "description": beat["thumbnail_description"],
                    "camera_movement": camera,
                    "transition": "切" if s < shot_count - 1 else "叠化",
                    "emotion": beat["emotion"],
                })

        return sequences

    def _estimate_shot_duration(self, beat_type: str, index: int) -> float:
        """估算镜头时长（秒）"""
        base = {
            "setup": 4.0,
            "confrontation": 2.5,
            "payoff": 3.5,
            "transition": 3.0,
            "revelation": 4.0,
        }.get(beat_type, 3.0)
        return round(base + index * 0.5, 1)

    def generate_motion_prompts(
        self, sequences: list[dict]
    ) -> list[dict]:
        """为镜头序列生成 Motion Prompt（AI 视频生成用）"""
        prompts = []
        for shot in sequences:
            prompt = (
                f"{shot['description'][:120]}, "
                f"{shot['camera_movement']}, "
                f"{shot['shot_type']} shot, "
                f"duration {shot['duration_seconds']}s"
            )
            prompts.append({
                "shot_id": shot["shot_id"],
                "prompt": prompt,
                "negative_prompt": "blur, distortion, ugly, low quality, watermark",
                "duration": shot["duration_seconds"],
            })
        return prompts


# ═══════════════════════════════════════════════════════════════
# 2. SeedanceStoryboardSkill — Seedance AI 分镜
# ═══════════════════════════════════════════════════════════════

class SeedanceStoryboardSkill:
    """Seedance AI 视频分镜技能 — 专门面向 AI 视频生成的提示词工程"""

    def analyze_director_vision(
        self, elements: list, episode_plan: dict = None
    ) -> dict:
        """
        导演视角分析 — 提炼本集的核心视觉概念。

        Returns:
            {visual_theme, color_palette, lighting_style, camera_style, key_visuals}
        """
        # 情绪统计
        emotions = [e.get("emotion", "") for e in elements if e.get("emotion")]
        from collections import Counter
        dominant_emotion = Counter(emotions).most_common(1)
        dom = dominant_emotion[0][0] if dominant_emotion else "中性"

        # 视觉主题推断
        beat_types = Counter(e.get("beat_type", "") for e in elements if e.get("beat_type"))
        is_action_heavy = beat_types.get("confrontation", 0) > len(elements) * 0.15

        if is_action_heavy:
            visual_theme = "动作驱动 — 高速运镜、碎片化剪辑、强视觉冲击"
            camera_style = "手持/斯坦尼康/无人机跟拍"
        else:
            visual_theme = "情感驱动 — 细腻构图、缓慢运镜、氛围营造"
            camera_style = "固定机位/滑轨/摇臂"

        # 色调
        from skills.storyboard_skills import FilmStoryboardSkill
        emotion_palette = FilmStoryboardSkill.EMOTION_PALETTE
        color_palette = emotion_palette.get(dom, "自然色调，中饱和度")

        # 光源
        time_mentions = [e.get("text", "") for e in elements
                        if any(kw in e.get("text", "") for kw in ["夜", "月", "烛", "灯", "晨", "暮"])]
        if any("夜" in t or "月" in t for t in time_mentions):
            lighting = "低照度夜景 — 月光/烛光/灯笼作为主光源"
        elif any("晨" in t for t in time_mentions):
            lighting = "晨光 — 暖色调逆光，薄雾散射"
        else:
            lighting = "自然光 — 柔光箱模拟，适度阴影"

        # 关键视觉时刻
        key_visuals = []
        for e in elements:
            if e.get("visual_hint"):
                key_visuals.append({
                    "moment": e.get("visual_hint", ""),
                    "beat_type": e.get("beat_type", ""),
                    "emotion": e.get("emotion", ""),
                })
            if len(key_visuals) >= 5:
                break

        return {
            "visual_theme": visual_theme,
            "color_palette": color_palette,
            "lighting_style": lighting,
            "camera_style": camera_style,
            "dominant_emotion": dom,
            "key_visuals": key_visuals,
        }

    def generate_art_design_spec(
        self, director_vision: dict, characters: list = None
    ) -> dict:
        """
        生成美术设计规格书。

        Returns:
            {characters, environments, props, overall_style}
        """
        characters = characters or []
        spec = {
            "characters": [],
            "environments": [],
            "props": [],
            "overall_style": {
                "visual_theme": director_vision.get("visual_theme", ""),
                "color_palette": director_vision.get("color_palette", ""),
                "lighting": director_vision.get("lighting_style", ""),
                "camera": director_vision.get("camera_style", ""),
            },
        }

        for char in characters[:8]:
            spec["characters"].append({
                "name": char.get("name", "未知"),
                "role_type": char.get("role_type", "minor"),
                "visual_design": char.get("visual_design", ""),
                "design_notes": (
                    f"角色定位: {char.get('role_type', '')}. "
                    f"情绪基调: {char.get('primary_emotion', '')}"
                ),
            })

        return spec

    def generate_seedance_prompts(
        self,
        director_vision: dict,
        art_spec: dict,
        beat_board: dict,
        shot_count: int = 12,
    ) -> list[dict]:
        """
        生成 Seedance AI 视频提示词。

        每一条 prompt 都针对 AI 视频生成优化，包含：
        - 画面描述
        - 运镜指令
        - 光影/色调
        - 负面提示词

        Returns:
            [{frame_id, prompt, negative_prompt, duration, camera}]
        """
        prompts = []
        grid = beat_board.get("grid", [])

        frames_per_beat = max(1, shot_count // max(len(grid), 1))

        frame_id = 0
        for beat in grid:
            for f in range(frames_per_beat):
                if frame_id >= shot_count:
                    break
                frame_id += 1

                # 根据节拍类型决定画面类型
                beat_type = beat.get("beat_type", "")
                if f == 0:
                    shot = "wide establishing shot"
                elif f == frames_per_beat - 1:
                    shot = "extreme close-up detail shot"
                else:
                    shot = "medium shot"

                prompt = (
                    f"cinematic {shot}, "
                    f"{director_vision.get('visual_theme', '')[:80]}, "
                    f"{director_vision.get('color_palette', '')}, "
                    f"{director_vision.get('lighting_style', '')}, "
                    f"8K, film grain, professional color grading"
                )

                prompts.append({
                    "frame_id": frame_id,
                    "beat_type": beat_type,
                    "prompt": prompt,
                    "negative_prompt": (
                        "blur, haze, distorted face, extra limbs, bad anatomy, "
                        "watermark, text, logo, low resolution, oversaturated"
                    ),
                    "duration_seconds": 3.0,
                    "camera": shot,
                })

        return prompts
