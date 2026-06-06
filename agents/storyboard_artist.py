"""
分镜艺术家 Agent — Phase 5: 分镜帧生成

职责:
  - 将 Beat Board 细化为具体镜头
  - 生成分镜图提示词
  - 色彩脚本(Color Script)设计
  - 支持 Film Storyboard 和 Seedance 双模式

使用:
  agent = StoryboardArtist(config)
  result = agent.execute(beat_board=..., mode="film", episode=1)
"""

import os
import json
from datetime import datetime

from .base_agent import BaseAgent


class StoryboardArtist(BaseAgent):
    """分镜艺术家 Agent — 镜头细化与色彩脚本"""

    agent_name = "storyboard-artist"
    agent_display_name = "分镜艺术家"
    agent_description = "将Beat Board细化为具体镜头，设计色彩脚本"
    phase = "storyboard"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from skills.storyboard_skills import FilmStoryboardSkill
        self.film_skill = FilmStoryboardSkill()

    def execute(
        self,
        beat_board: dict = None,
        director_vision: dict = None,
        mode: str = "film",
        episode: int = 1,
        state_manager=None,
        output_dir: str = None,
        use_llm: bool = True,
        **kwargs,
    ) -> dict:
        """
        细化分镜。

        Args:
            beat_board: Beat Board 数据
            director_vision: 导演视角（Seedance模式）
            mode: film | seedance
            episode: 集数
            state_manager: AgentStateManager
            output_dir: 输出目录
            use_llm: LLM 增强

        Returns:
            {status, frames, color_script, ...}
        """
        self.state_manager = state_manager or self.state_manager
        beat_board = beat_board or {}

        self.log(f"分镜艺术家: 第{episode}集, {mode}模式")

        # 确定输出目录
        output_dir = output_dir or self.get_config("output.output_dir", "./output")
        project_name = self.state_manager.project_name if self.state_manager else "untitled"
        frames_dir = os.path.join(
            output_dir, project_name, "storyboard", f"ep{episode:02d}", "frames"
        )
        os.makedirs(frames_dir, exist_ok=True)

        # Step 1: 生成详细镜头描述
        self.log("生成详细镜头...")
        frames = self._generate_frames(beat_board, mode, director_vision)

        # Step 2: 色彩脚本
        self.log("设计色彩脚本...")
        color_script = self._design_color_script(beat_board, frames)

        # Step 3: LLM 增强镜头描述
        if use_llm:
            self.log("LLM 增强镜头描述...")
            frames = self._llm_enhance_frames(frames, mode)

        # 保存
        frames_path = os.path.join(frames_dir, "frames.json")
        with open(frames_path, "w", encoding="utf-8") as f:
            json.dump(frames, f, ensure_ascii=False, indent=2)

        color_path = os.path.join(frames_dir, "color_script.json")
        with open(color_path, "w", encoding="utf-8") as f:
            json.dump(color_script, f, ensure_ascii=False, indent=2)

        self.log(f"生成 {len(frames)} 个镜头帧")

        return {
            "status": "completed",
            "episode": episode,
            "mode": mode,
            "frame_count": len(frames),
            "frames": frames,
            "color_script": color_script,
            "frames_path": frames_path,
            "color_script_path": color_path,
            "message": f"分镜细化完成: {len(frames)} 个镜头帧",
        }

    def _generate_frames(
        self, beat_board: dict, mode: str, director_vision: dict = None
    ) -> list[dict]:
        """生成镜头帧描述"""
        frames = []
        grid = beat_board.get("grid", [])

        frame_id = 0
        for beat in grid:
            # 每个节拍 2-4 帧
            beat_type = beat.get("beat_type", "")
            frame_count = 4 if beat_type in ("confrontation", "revelation") else 2

            for f in range(frame_count):
                frame_id += 1
                shot_type = self._pick_shot_for_position(beat_type, f, frame_count)

                frame = {
                    "frame_id": frame_id,
                    "beat_type": beat_type,
                    "position_in_beat": f + 1,
                    "shot_type": shot_type,
                    "description": beat.get("thumbnail_description", ""),
                    "emotion": beat.get("emotion", ""),
                    "camera_instruction": self._get_camera_instruction(shot_type),
                    "lighting_note": self._get_lighting_note(beat.get("emotion", "")),
                    "duration_seconds": self.film_skill._estimate_shot_duration(beat_type, f),
                }
                frames.append(frame)

        return frames

    def _pick_shot_for_position(
        self, beat_type: str, position: int, total: int
    ) -> str:
        """根据节拍位置选择镜头类型"""
        if total == 2:
            return "wide" if position == 0 else "close_up"
        elif total == 4:
            return ["wide", "medium", "close_up", "extreme_close_up"][position]
        return "medium"

    def _get_camera_instruction(self, shot_type: str) -> str:
        """获取镜头运镜指导"""
        instructions = {
            "establishing": "缓慢摇摄，从左至右展示环境",
            "wide": "固定机位，角色从远处走入画面",
            "medium": "轻微推近，聚焦角色上半身",
            "close_up": "手持微晃，贴近角色面部",
            "extreme_close_up": "极慢速推近，焦点在细节",
            "over_shoulder": "过肩固定，前景虚化",
            "pov": "第一人称视角，模拟角色视线移动",
        }
        return instructions.get(shot_type, "固定机位")

    def _get_lighting_note(self, emotion: str) -> str:
        """获取灯光指导"""
        notes = {
            "喜悦": "高调光，暖色温，逆光光晕",
            "愤怒": "底光，硬光，高对比",
            "悲伤": "柔光，蓝色温，暗角",
            "恐惧": "闪烁光源，长阴影，绿色调",
            "紧张": "顶光，硬阴影，渐暗",
            "温柔": "窗光，柔焦，暖色温",
            "平静": "自然光/天光，均匀照明",
        }
        return notes.get(emotion, "三点式标准布光")

    def _design_color_script(
        self, beat_board: dict, frames: list
    ) -> list[dict]:
        """设计色彩脚本——每帧的调色板"""
        color_script = []

        # 基础调色板
        base_palettes = {
            "喜悦": ["#FFD700", "#FFA500", "#FFF8DC"],
            "愤怒": ["#8B0000", "#FF4500", "#2F0000"],
            "悲伤": ["#4682B4", "#708090", "#191970"],
            "恐惧": ["#006400", "#228B22", "#000000"],
            "紧张": ["#696969", "#808080", "#2F4F4F"],
            "温柔": ["#FFB6C1", "#FFC0CB", "#FFF0F5"],
            "平静": ["#87CEEB", "#F5F5DC", "#E0E0E0"],
        }

        for frame in frames:
            emotion = frame.get("emotion", "")
            palette = base_palettes.get(emotion, ["#808080", "#C0C0C0", "#FFFFFF"])
            color_script.append({
                "frame_id": frame["frame_id"],
                "emotion": emotion,
                "palette": palette,
                "saturation": "高" if emotion in ("喜悦", "愤怒") else "低",
                "contrast": "高" if emotion in ("愤怒", "恐惧", "紧张") else "中",
                "color_temp": "暖" if emotion in ("喜悦", "温柔") else "冷",
            })

        return color_script

    def _llm_enhance_frames(
        self, frames: list, mode: str
    ) -> list[dict]:
        """LLM 增强镜头描述"""
        if not frames:
            return frames

        sample = frames[:5]
        sample_text = "\n".join(
            f"Frame {f['frame_id']}: [{f['shot_type']}] {f['description'][:100]}"
            for f in sample
        )

        prompt = f"""你是电影分镜师。以下是 {len(frames)} 个镜头的初稿：

{sample_text}
(共 {len(frames)} 个镜头)

请为前5个镜头增强描述，使其更具电影感和视觉冲击力。
每个镜头输出:
- cinematic_description: 增强后的电影级画面描述（50-100字）
- visual_reference: 可参考的电影/导演风格

输出 JSON 数组: [{{"frame_id": 1, "cinematic_description": "...", "visual_reference": "..."}}]"""

        try:
            enhanced = self.call_llm(prompt, use_light=False, expect_json=True)
            if isinstance(enhanced, list):
                enhance_map = {item["frame_id"]: item for item in enhanced}
                for frame in frames:
                    enh = enhance_map.get(frame["frame_id"], {})
                    if enh.get("cinematic_description"):
                        frame["cinematic_description"] = enh["cinematic_description"]
                    if enh.get("visual_reference"):
                        frame["visual_reference"] = enh["visual_reference"]
        except Exception as e:
            self.log(f"LLM 增强失败: {e}", level="warning")

        return frames


def create_storyboard_artist(config: dict = None, **kwargs) -> StoryboardArtist:
    return StoryboardArtist(config=config, **kwargs)
