"""
图片技能合集 — AI 图片生成 + 图片反推

包含:
  - ImageGenerationSkill: 多 Provider 图片生成（Nano Banana / SkyReels / OpenAI）
  - ImageToPromptSkill: 从图片反推描述提示词
"""

import base64
import json
import os
import time
from datetime import datetime
from typing import Optional


# ═══════════════════════════════════════════════════════════════
# 1. ImageGenerationSkill — AI 图片生成
# ═══════════════════════════════════════════════════════════════

class ImageGenerationSkill:
    """AI 图片生成技能 — 支持多 Provider 切换"""

    PROVIDERS = ["openai", "nano_banana", "skyreels", "custom"]

    def __init__(self, config: dict = None):
        """
        Args:
            config: 全局配置字典（含 image_gen 段）
        """
        self.config = config or {}
        img_cfg = self.config.get("image_gen", {})
        self.provider = img_cfg.get("provider", "openai")
        self.api_key = img_cfg.get("api_key", "")
        self.base_url = img_cfg.get("base_url", "")
        self.model = img_cfg.get("model", "")
        self.default_size = img_cfg.get("default_size", "1024x1024")
        self.default_quality = img_cfg.get("default_quality", "high")

    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        size: str = None,
        style: str = "cinematic",
        output_path: str = None,
    ) -> dict:
        """
        生成单张图片。

        Args:
            prompt: 正向提示词
            negative_prompt: 负向提示词
            size: 图片尺寸
            style: 风格标签
            output_path: 保存路径

        Returns:
            {success, image_path, prompt_used, provider, metadata}
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "未配置图片生成 API Key",
                "prompt_used": prompt,
            }

        full_prompt = self._build_full_prompt(prompt, style)

        try:
            if self.provider == "openai":
                result = self._generate_openai(full_prompt, size)
            elif self.provider == "nano_banana":
                result = self._generate_nano_banana(full_prompt, negative_prompt, size)
            elif self.provider == "skyreels":
                result = self._generate_skyreels(full_prompt, negative_prompt, size)
            else:
                result = self._generate_custom(full_prompt, negative_prompt, size)

            if result.get("success") and output_path:
                self._save_image(result["image_data"], output_path)
                result["image_path"] = output_path

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "prompt_used": full_prompt,
            }

    def generate_batch(
        self,
        prompts: list[dict],
        output_dir: str = "./output/images",
        parallel: bool = False,
    ) -> list[dict]:
        """
        批量生成图片。

        Args:
            prompts: [{prompt, negative_prompt, filename, ...}]
            output_dir: 输出目录
            parallel: 是否并行（需 ThreadPoolExecutor）

        Returns:
            [{success, image_path, ...}]
        """
        os.makedirs(output_dir, exist_ok=True)
        results = []

        for i, p in enumerate(prompts):
            filename = p.get("filename", f"frame_{i+1:04d}.png")
            output_path = os.path.join(output_dir, filename)

            result = self.generate(
                prompt=p.get("prompt", ""),
                negative_prompt=p.get("negative_prompt", ""),
                size=p.get("size"),
                output_path=output_path,
            )
            result["index"] = i + 1
            results.append(result)

            # 限流等待
            if i < len(prompts) - 1:
                time.sleep(0.5)

        return results

    def _build_full_prompt(self, prompt: str, style: str) -> str:
        """构建完整提示词（加风格前缀和质量后缀）"""
        style_prefixes = {
            "cinematic": "cinematic lighting, film still, ",
            "anime": "anime style, studio ghibli, makoto shinkai, ",
            "realistic": "photorealistic, 8K, ultra detailed, ",
            "concept_art": "concept art, artstation, trending, ",
            "oil_painting": "oil painting, classical, masterpiece, ",
        }
        quality_suffix = (
            ", high quality, sharp focus, professional color grading, "
            "no watermark, no text"
        )

        prefix = style_prefixes.get(style, style_prefixes["cinematic"])
        return prefix + prompt + quality_suffix

    def _generate_openai(self, prompt: str, size: str) -> dict:
        """OpenAI DALL-E / 兼容 API"""
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key, base_url=self.base_url or None)
        resp = client.images.generate(
            model=self.model or "dall-e-3",
            prompt=prompt,
            size=size or self.default_size,
            quality=self.default_quality,
            n=1,
        )
        return {
            "success": True,
            "provider": "openai",
            "image_url": resp.data[0].url if resp.data else "",
            "prompt_used": prompt,
        }

    def _generate_nano_banana(self, prompt: str, negative: str, size: str) -> dict:
        """Nano Banana API（OpenAI-compatible 图片生成）"""
        return self._generate_openai(prompt, size)

    def _generate_skyreels(self, prompt: str, negative: str, size: str) -> dict:
        """SkyReels API"""
        # SkyReels 需要先提交任务再轮询
        import httpx
        submit_url = self.config.get("video_gen", {}).get("submit_url", self.base_url)
        task_url = self.config.get("video_gen", {}).get("task_url", "")

        try:
            resp = httpx.post(
                submit_url,
                json={"prompt": prompt, "negative_prompt": negative},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                task_id = data.get("task_id", "")
                # 轮询结果（简化：最多等30秒）
                for _ in range(15):
                    time.sleep(2)
                    task_resp = httpx.get(
                        f"{task_url}/{task_id}",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        timeout=10,
                    )
                    if task_resp.status_code == 200:
                        task_data = task_resp.json()
                        if task_data.get("status") == "completed":
                            return {
                                "success": True,
                                "provider": "skyreels",
                                "image_url": task_data.get("url", ""),
                                "prompt_used": prompt,
                            }

            return {"success": False, "error": f"SkyReels API 失败: {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_custom(self, prompt: str, negative: str, size: str) -> dict:
        """自定义 Provider"""
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        resp = client.images.generate(
            model=self.model,
            prompt=prompt,
            size=size or self.default_size,
            n=1,
        )
        return {
            "success": True,
            "provider": "custom",
            "image_url": resp.data[0].url if resp.data else "",
            "prompt_used": prompt,
        }

    def _save_image(self, image_data, path: str):
        """保存图片到文件"""
        if isinstance(image_data, bytes):
            with open(path, "wb") as f:
                f.write(image_data)
        elif isinstance(image_data, str) and image_data.startswith("http"):
            # URL 类型 — 下载
            try:
                import httpx
                resp = httpx.get(image_data, timeout=30)
                with open(path, "wb") as f:
                    f.write(resp.content)
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════
# 2. ImageToPromptSkill — 图片反推提示词
# ═══════════════════════════════════════════════════════════════

class ImageToPromptSkill:
    """图片反推技能 — 从图片 URL/文件 反推风格化提示词"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        rev_cfg = self.config.get("image_reverse", {})
        self.provider = rev_cfg.get("provider", "openai")
        self.api_key = rev_cfg.get("api_key", "")
        self.base_url = rev_cfg.get("base_url", "")
        self.model = rev_cfg.get("model", "gpt-4o")

    def reverse(
        self,
        image_source: str,
        target_style: str = "cinematic",
        output_detail: str = "detailed",
    ) -> dict:
        """
        从图片反推提示词。

        Args:
            image_source: 图片 URL 或本地文件路径
            target_style: 目标风格转译（cinematic/anime/realistic）
            output_detail: 输出详细程度

        Returns:
            {success, original_prompt, styled_prompt, style, metadata}
        """
        # 构建多模态 prompt
        analysis_prompt = (
            "Please describe this image in detail, focusing on: "
            "1) composition and framing, "
            "2) lighting and color palette, "
            "3) mood and atmosphere, "
            "4) key visual elements. "
            "Output as a structured JSON."
        )

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.base_url or None)

            # 处理图片来源
            if image_source.startswith("http"):
                image_content = {"type": "image_url", "image_url": {"url": image_source}}
            elif os.path.exists(image_source):
                with open(image_source, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                image_content = {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                }
            else:
                return {"success": False, "error": f"无法访问图片: {image_source}"}

            resp = client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": analysis_prompt},
                        image_content,
                    ],
                }],
                max_tokens=1024,
            )
            raw = resp.choices[0].message.content

            # 解析 JSON
            try:
                analysis = json.loads(raw)
            except json.JSONDecodeError:
                import re
                m = re.search(r'\{[\s\S]*\}', raw)
                analysis = json.loads(m.group(0)) if m else {"description": raw}

            # 转译为指定风格
            styled_prompt = self._stylize(analysis, target_style)

            return {
                "success": True,
                "original_analysis": analysis,
                "styled_prompt": styled_prompt,
                "style": target_style,
                "metadata": {
                    "model": self.model,
                    "provider": self.provider,
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _stylize(self, analysis: dict, style: str) -> str:
        """将分析结果转译为指定风格的提示词"""
        desc = analysis.get("description", str(analysis))

        style_modifiers = {
            "cinematic": "cinematic lighting, film grain, 8K, professional color grading",
            "anime": "anime style, cel shaded, vibrant colors, clean lines",
            "realistic": "photorealistic, hyper-detailed, natural lighting, 8K RAW",
            "concept_art": "concept art, artstation trending, digital painting, dramatic lighting",
        }

        modifier = style_modifiers.get(style, style_modifiers["cinematic"])
        return f"{desc}, {modifier}"


# ═══════════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════════

def create_image_generator(config: dict) -> ImageGenerationSkill:
    """从配置创建图片生成器"""
    return ImageGenerationSkill(config)


def quick_generate(
    prompt: str, output_path: str, config: dict = None
) -> dict:
    """快速生成一张图片"""
    skill = ImageGenerationSkill(config)
    return skill.generate(prompt=prompt, output_path=output_path)
