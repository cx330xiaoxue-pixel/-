"""
分镜导演 Agent — Phase 5: 分镜可视化 (~storyboard-film/~storyboard-seedance N)

职责:
  - 读取剧本，识别关键视觉时刻
  - 选择分镜策略（Film 或 Seedance）
  - 审核所有分镜产物
  - 协调 storyboard_artist、art_designer、image_generator

使用:
  agent = StoryboardDirector(config)
  result = agent.execute(episode=1, mode="film", script_elements=...)
"""

import os
from datetime import datetime

from .base_agent import BaseAgent


class StoryboardDirector(BaseAgent):
    """分镜导演 Agent — 分镜策略选择与产物审核"""

    agent_name = "storyboard-director"
    agent_display_name = "分镜导演"
    agent_description = "选择分镜策略，识别关键视觉时刻，审核所有分镜产物"
    phase = "storyboard"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from skills.storyboard_skills import FilmStoryboardSkill, SeedanceStoryboardSkill
        self.film_skill = FilmStoryboardSkill()
        self.seedance_skill = SeedanceStoryboardSkill()

    def execute(
        self,
        episode: int = 1,
        mode: str = "film",
        script_elements: list = None,
        script_path: str = None,
        episode_plan: dict = None,
        characters: list = None,
        state_manager=None,
        image_generator=None,
        output_dir: str = None,
        use_llm: bool = True,
        **kwargs,
    ) -> dict:
        """
        执行分镜流程。

        Args:
            episode: 集数
            mode: 分镜模式 (film | seedance)
            script_elements: 剧本元素
            script_path: 剧本路径
            episode_plan: 分集规划
            characters: 角色信息
            state_manager: AgentStateManager
            image_generator: ImageGenerationSkill 或 Agent
            output_dir: 输出目录
            use_llm: LLM 增强

        Returns:
            {status, storyboard_dir, beat_board, sequences, prompts, ...}
        """
        self.state_manager = state_manager or self.state_manager

        # 加载剧本
        if script_elements is None and script_path:
            script_elements = self._load_elements(script_path)
        script_elements = script_elements or []

        self.log(f"分镜导演: 第{episode}集, 模式={mode}, {len(script_elements)} 元素")

        # 确定输出目录
        output_dir = output_dir or self.get_config("output.output_dir", "./output")
        project_name = self.state_manager.project_name if self.state_manager else "untitled"
        storyboard_dir = os.path.join(
            output_dir, project_name, "storyboard", f"ep{episode:02d}"
        )
        os.makedirs(storyboard_dir, exist_ok=True)

        # Step 1: Step 节拍分析
        self.log("节拍分析 (Beat Analysis)...")
        beats = self.film_skill.analyze_beats(script_elements)
        self.log(f"识别到 {len(beats)} 个节拍")

        # Step 2: Beat Board
        self.log("生成 Beat Board...")
        beat_board = self.film_skill.generate_beat_board(beats, episode)

        # Step 3: 按模式生成
        if mode == "film":
            result = self._execute_film_mode(
                beat_board, episode, storyboard_dir, use_llm
            )
        else:
            result = self._execute_seedance_mode(
                beat_board, script_elements, characters,
                episode, storyboard_dir, use_llm
            )

        # Step 4: 导演审核
        self.log("导演审核...")
        review = self._director_review(result, mode)

        # Step 5: 保存产物索引
        self._save_storyboard_manifest(
            episode=episode,
            mode=mode,
            beat_board=beat_board,
            result=result,
            review=review,
            output_dir=storyboard_dir,
        )

        self.save_state(f"last_storyboard_ep{episode}", {
            "timestamp": datetime.now().isoformat(),
            "episode": episode,
            "mode": mode,
            "beats_analyzed": len(beats),
            "shots_generated": len(result.get("sequences", result.get("prompts", []))),
        })

        self.log(f"分镜完成: {mode}模式, {len(beats)}节拍")

        return {
            "status": "completed",
            "episode": episode,
            "mode": mode,
            "storyboard_dir": storyboard_dir,
            "beat_count": len(beats),
            "beat_board": beat_board,
            "sequences": result.get("sequences", []),
            "prompts": result.get("prompts", []),
            "director_review": review,
            "message": (
                f"第{episode}集分镜完成 ({mode}): "
                f"{len(beats)}个节拍, "
                f"导演审核{'通过' if review.get('approved') else '需修改'}"
            ),
        }

    def _execute_film_mode(
        self, beat_board: dict, episode: int, output_dir: str, use_llm: bool
    ) -> dict:
        """执行标准电影分镜流程"""
        # Sequence Board
        self.log("生成 Sequence Board...")
        sequences = self.film_skill.generate_sequence_board(beat_board)

        # Motion Prompts
        self.log("生成 Motion Prompts...")
        motion_prompts = self.film_skill.generate_motion_prompts(sequences)

        # 保存
        import json
        seq_path = os.path.join(output_dir, f"sequence_board_ep{episode:02d}.json")
        with open(seq_path, "w", encoding="utf-8") as f:
            json.dump(sequences, f, ensure_ascii=False, indent=2)

        prompt_path = os.path.join(output_dir, f"motion_prompts_ep{episode:02d}.json")
        with open(prompt_path, "w", encoding="utf-8") as f:
            json.dump(motion_prompts, f, ensure_ascii=False, indent=2)

        return {
            "sequences": sequences,
            "prompts": motion_prompts,
            "sequence_path": seq_path,
            "prompt_path": prompt_path,
        }

    def _execute_seedance_mode(
        self, beat_board: dict, elements: list, characters: list,
        episode: int, output_dir: str, use_llm: bool
    ) -> dict:
        """执行 Seedance AI 分镜流程"""
        # Director Vision
        self.log("导演视角分析...")
        director_vision = self.seedance_skill.analyze_director_vision(elements)

        # Art Design Spec
        self.log("美术设计...")
        art_spec = self.seedance_skill.generate_art_design_spec(
            director_vision, characters
        )

        # Seedance Prompts
        self.log("生成 Seedance 提示词...")
        seedance_prompts = self.seedance_skill.generate_seedance_prompts(
            director_vision=director_vision,
            art_spec=art_spec,
            beat_board=beat_board,
            shot_count=12,
        )

        # 保存
        import json
        vision_path = os.path.join(output_dir, f"director_vision_ep{episode:02d}.json")
        with open(vision_path, "w", encoding="utf-8") as f:
            json.dump(director_vision, f, ensure_ascii=False, indent=2)

        art_path = os.path.join(output_dir, f"art_spec_ep{episode:02d}.json")
        with open(art_path, "w", encoding="utf-8") as f:
            json.dump(art_spec, f, ensure_ascii=False, indent=2)

        prompt_path = os.path.join(output_dir, f"seedance_prompts_ep{episode:02d}.json")
        with open(prompt_path, "w", encoding="utf-8") as f:
            json.dump(seedance_prompts, f, ensure_ascii=False, indent=2)

        return {
            "director_vision": director_vision,
            "art_spec": art_spec,
            "prompts": seedance_prompts,
            "vision_path": vision_path,
            "art_path": art_path,
            "prompt_path": prompt_path,
        }

    def _director_review(self, result: dict, mode: str) -> dict:
        """导演审核分镜产物"""
        issues = []
        total_shots = 0

        if mode == "film":
            total_shots = len(result.get("sequences", []))
            if total_shots < 5:
                issues.append("镜头数过少（<5），无法形成有效叙事")
            shot_types = set(
                s.get("shot_type", "") for s in result.get("sequences", [])
            )
            if len(shot_types) < 3:
                issues.append("镜头类型单一，建议增加特写/主观/POV等变化")
        else:
            total_shots = len(result.get("prompts", []))
            if total_shots < 6:
                issues.append("Seedance 帧数不足（<6）")

        return {
            "approved": len(issues) == 0,
            "total_shots": total_shots,
            "issues": issues,
            "suggestions": (
                [] if not issues
                else ["增加镜头变化", "检查关键节拍是否全部覆盖"]
            ),
        }

    def _save_storyboard_manifest(
        self, episode: int, mode: str, beat_board: dict,
        result: dict, review: dict, output_dir: str
    ):
        """保存分镜产物清单"""
        import json
        manifest = {
            "episode": episode,
            "mode": mode,
            "generated_at": datetime.now().isoformat(),
            "beat_board": {
                "total_beats": beat_board.get("total_beats_analyzed", 0),
                "key_beats": beat_board.get("key_beats_selected", 0),
            },
            "director_review": review,
            "files": {},
        }

        for key in ["sequence_path", "prompt_path", "vision_path", "art_path"]:
            if key in result:
                manifest["files"][key] = result[key]

        manifest_path = os.path.join(output_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    def _load_elements(self, path: str) -> list:
        try:
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                script = yaml.safe_load(f)
            elements = []
            for ch in script.get("script", {}).get("chapters", []):
                for scene in ch.get("scenes", []):
                    elements.extend(scene.get("elements", []))
            return elements
        except Exception:
            return []


def create_storyboard_director(config: dict = None, **kwargs) -> StoryboardDirector:
    return StoryboardDirector(config=config, **kwargs)
