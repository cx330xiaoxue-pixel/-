"""
图片生成 Agent — Phase 5: AI 图片/视频生成

职责:
  - 支持多 Provider（Nano Banana / SkyReels / OpenAI-compatible）
  - 批量生成角色立绘、场景概念图、分镜帧
  - 图片反推提示词
  - 生成历史记录与状态追踪

使用:
  agent = ImageGeneratorAgent(config)
  result = agent.execute(prompts=[...], output_dir="...")
"""

import os
import json
from datetime import datetime

from .base_agent import BaseAgent


class ImageGeneratorAgent(BaseAgent):
    """图片生成 Agent — 多 Provider 图片/视频生成"""

    agent_name = "image-generator"
    agent_display_name = "图片生成器"
    agent_description = "批量生成角色立绘、场景概念图、分镜帧，支持多Provider"
    phase = "storyboard"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from skills.image_skills import ImageGenerationSkill, ImageToPromptSkill
        self.image_skill = ImageGenerationSkill(self.config)
        self.reverse_skill = ImageToPromptSkill(self.config)

    def execute(
        self,
        prompts: list = None,
        category: str = "frames",
        episode: int = 1,
        state_manager=None,
        output_dir: str = None,
        **kwargs,
    ) -> dict:
        """
        批量生成图片。

        Args:
            prompts: 提示词列表 [{prompt, negative_prompt, filename}] 或按模式自动生成
            category: 类别 (characters | scenes | frames)
            episode: 集数
            state_manager: AgentStateManager
            output_dir: 输出目录

        Returns:
            {status, generated, failed, images: [...]}
        """
        self.state_manager = state_manager or self.state_manager
        prompts = prompts or []

        # 输出目录
        output_dir = output_dir or self.get_config("output.output_dir", "./output")
        project_name = self.state_manager.project_name if self.state_manager else "untitled"
        img_dir = os.path.join(output_dir, project_name, "images", category)
        os.makedirs(img_dir, exist_ok=True)

        self.log(f"图片生成: {category}, {len(prompts)} 张, 目标: {img_dir}")

        if not prompts:
            return {
                "status": "completed",
                "message": "未提供生成提示词",
                "generated": 0,
                "images": [],
            }

        # 检查 API Key
        if not self.image_skill.api_key:
            self.log("未配置图片生成 API Key，跳过实际生成", level="warning")
            return {
                "status": "skipped",
                "message": "未配置图片生成 API Key，已保存提示词供手动使用",
                "generated": 0,
                "prompts_saved": len(prompts),
                "images": [],
            }

        # 批量生成
        results = self.image_skill.generate_batch(
            prompts=prompts,
            output_dir=img_dir,
        )

        generated = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]

        # 保存生成记录
        history_path = os.path.join(img_dir, "generation_history.json")
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "category": category,
                "episode": episode,
                "total": len(prompts),
                "generated": len(generated),
                "failed": len(failed),
                "results": results,
            }, f, ensure_ascii=False, indent=2)

        self.save_state(f"last_generation_{category}", {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "generated": len(generated),
            "failed": len(failed),
        })

        self.log(f"图片生成完成: {len(generated)}/{len(prompts)} 成功")

        return {
            "status": "completed",
            "category": category,
            "generated": len(generated),
            "failed": len(failed),
            "images": results,
            "output_dir": img_dir,
            "history_path": history_path,
            "message": f"图片生成: {len(generated)}/{len(prompts)} 成功" +
                       (f", {len(failed)} 失败" if failed else ""),
        }

    def generate_character_sheet(
        self, character_designs: list, episode: int = 1, output_dir: str = None
    ) -> dict:
        """生成角色立绘/设定图"""
        prompts = []
        for char in character_designs:
            name = char.get("name", "unknown")
            img_prompt = char.get("image_prompt", char.get("visual_design", ""))
            prompts.append({
                "prompt": img_prompt,
                "negative_prompt": "bad anatomy, extra limbs, ugly, deformed",
                "filename": f"char_{name}_ep{episode:02d}.png",
            })

        return self.execute(
            prompts=prompts,
            category="characters",
            episode=episode,
            output_dir=output_dir,
        )

    def generate_frames(
        self, frame_prompts: list, episode: int = 1, output_dir: str = None
    ) -> dict:
        """生成分镜帧图"""
        prompts = []
        for i, fp in enumerate(frame_prompts):
            prompts.append({
                "prompt": fp.get("prompt", fp.get("cinematic_description", "")),
                "negative_prompt": fp.get("negative_prompt", ""),
                "filename": f"frame_{fp.get('frame_id', i+1):04d}.png",
            })

        return self.execute(
            prompts=prompts,
            category="frames",
            episode=episode,
            output_dir=output_dir,
        )

    def reverse_image_to_prompt(
        self, image_source: str, target_style: str = "cinematic"
    ) -> dict:
        """从图片反推提示词"""
        self.log(f"图片反推: {target_style} 风格")
        return self.reverse_skill.reverse(
            image_source=image_source,
            target_style=target_style,
        )


def create_image_generator(config: dict = None, **kwargs) -> ImageGeneratorAgent:
    return ImageGeneratorAgent(config=config, **kwargs)
