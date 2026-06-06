"""
美术设计 Agent — Phase 5: 角色/场景服化道设计

职责:
  - 角色视觉设计（服化道、外貌、气质）
  - 场景概念设计（建筑风格、时代背景、环境氛围）
  - 道具设计（重要物品的外观描述）
  - 产出 assets/ 目录下的设计文档

使用:
  agent = ArtDesigner(config)
  result = agent.execute(characters=..., episode=1)
"""

import os
import json
from datetime import datetime

from .base_agent import BaseAgent


class ArtDesigner(BaseAgent):
    """美术设计 Agent — 角色/场景/道具视觉设计"""

    agent_name = "art-designer"
    agent_display_name = "美术设计师"
    agent_description = "设计角色服化道、场景概念、道具外观"
    phase = "storyboard"

    # 设计风格参考
    STYLE_REFERENCES = {
        "古装": {
            "architecture": "唐宋风格，木质结构，飞檐斗拱",
            "costume": "交领右衽，宽袖长袍，丝绸/棉麻",
            "color_scheme": "低饱和度传统色谱：赭石、靛青、月白、绛紫",
        },
        "武侠": {
            "architecture": "山水意境，竹林木屋，悬崖古刹",
            "costume": "束袖劲装，皮革护腕，斗笠披风",
            "color_scheme": "水墨风：墨黑、素白、青灰、暗红",
        },
        "都市": {
            "architecture": "现代玻璃幕墙，工业风loft，霓虹街道",
            "costume": "当代时装，层次叠穿，质感面料",
            "color_scheme": "都市中性色+点缀亮色：灰、蓝、白、橙",
        },
        "科幻": {
            "architecture": "赛博朋克/极简未来，全息投影，金属质感",
            "costume": "功能性面料，几何剪裁，LED线光",
            "color_scheme": "冷金属+霓虹：银灰、深蓝、紫色、荧光绿",
        },
    }

    def execute(
        self,
        characters: list = None,
        genre: str = "武侠",
        episode: int = 1,
        state_manager=None,
        output_dir: str = None,
        use_llm: bool = True,
        **kwargs,
    ) -> dict:
        """
        执行美术设计。

        Args:
            characters: 角色信息列表
            genre: 类型（古装/武侠/都市/科幻）
            episode: 集数
            state_manager: AgentStateManager
            output_dir: 输出目录
            use_llm: LLM 增强

        Returns:
            {status, character_designs, style_guide, assets_path}
        """
        self.state_manager = state_manager or self.state_manager
        characters = characters or []

        self.log(f"美术设计: 第{episode}集, {genre}风格, {len(characters)} 个角色")

        # 输出目录
        output_dir = output_dir or self.get_config("output.output_dir", "./output")
        project_name = self.state_manager.project_name if self.state_manager else "untitled"
        assets_dir = os.path.join(output_dir, project_name, "assets")
        os.makedirs(assets_dir, exist_ok=True)

        # Step 1: 风格指南
        style_guide = self._build_style_guide(genre)

        # Step 2: 角色设计
        character_designs = self._design_characters(characters, style_guide)

        # Step 3: LLM 增强
        if use_llm:
            self.log("LLM 增强美术设计...")
            character_designs = self._llm_enhance_designs(
                character_designs, style_guide
            )

        # 保存
        design_doc = {
            "episode": episode,
            "genre": genre,
            "generated_at": datetime.now().isoformat(),
            "style_guide": style_guide,
            "characters": character_designs,
        }

        design_path = os.path.join(assets_dir, f"art_design_ep{episode:02d}.json")
        with open(design_path, "w", encoding="utf-8") as f:
            json.dump(design_doc, f, ensure_ascii=False, indent=2)

        self.log(f"美术设计完成: {len(character_designs)} 个角色")

        return {
            "status": "completed",
            "episode": episode,
            "genre": genre,
            "character_count": len(character_designs),
            "character_designs": character_designs,
            "style_guide": style_guide,
            "design_path": design_path,
            "message": f"美术设计完成: {len(character_designs)} 个角色, {genre}风格",
        }

    def _build_style_guide(self, genre: str) -> dict:
        """构建风格指南"""
        ref = self.STYLE_REFERENCES.get(genre, self.STYLE_REFERENCES["武侠"])
        return {
            "genre": genre,
            "architecture_style": ref["architecture"],
            "costume_style": ref["costume"],
            "color_scheme": ref["color_scheme"],
            "lighting_preference": "自然光为主，关键场景用戏剧光",
            "overall_mood": self._get_genre_mood(genre),
        }

    def _get_genre_mood(self, genre: str) -> str:
        moods = {
            "古装": "典雅庄重，东方美学，留白意蕴",
            "武侠": "江湖浪漫，快意恩仇，山水意境",
            "都市": "现代冷感，疏离与温暖并存",
            "科幻": "未来感，宏大与孤独，技术与人性的张力",
        }
        return moods.get(genre, "中性")

    def _design_characters(
        self, characters: list, style_guide: dict
    ) -> list[dict]:
        """为每个角色生成美术设计方案"""
        designs = []

        for char in characters:
            name = char.get("name", "未知")
            role_type = char.get("role_type", "minor")
            existing_visual = char.get("visual_design", "")

            # 基于角色类型推断设计方向
            if role_type == "protagonist":
                color_accent = "主色调鲜明，与配角形成对比"
                silhouette = "轮廓简洁有力，辨识度高"
            elif role_type == "antagonist":
                color_accent = "深色调为主，暗藏锋芒"
                silhouette = "轮廓带有压迫感，不对称设计"
            else:
                color_accent = "辅助角色色调，不夺主角风头"
                silhouette = "轮廓清晰但不抢眼"

            design = {
                "name": name,
                "role_type": role_type,
                "existing_visual": existing_visual,
                "costume_design": {
                    "style": style_guide.get("costume_style", ""),
                    "color_accent": color_accent,
                    "silhouette": silhouette,
                    "key_pieces": self._suggest_costume_pieces(role_type),
                    "fabric_texture": "丝绸/棉麻/皮革" if role_type != "minor" else "棉麻",
                },
                "makeup_hair": {
                    "hair_style": self._suggest_hairstyle(role_type, char.get("traits", [])),
                    "makeup_focus": "自然裸妆" if role_type == "protagonist" else "强调轮廓",
                },
                "prop_design": {
                    "signature_prop": self._suggest_prop(role_type, char.get("traits", [])),
                },
                "image_prompt": self._build_character_image_prompt(
                    name, role_type, existing_visual, style_guide
                ),
            }
            designs.append(design)

        return designs

    def _suggest_costume_pieces(self, role_type: str) -> str:
        pieces = {
            "protagonist": "标志性外套 + 内搭 + 腰带 + 靴子",
            "antagonist": "长袍/披风 + 暗色内搭 + 金属配件",
            "supporting": "与主角风格协调的功能性服装",
            "minor": "时代背景下的普通装束",
        }
        return pieces.get(role_type, "基础装束")

    def _suggest_hairstyle(self, role_type: str, traits: list) -> str:
        if "高冷" in traits or "冷漠" in traits:
            return "束发整齐，一丝不苟"
        elif "活泼" in traits or "开朗" in traits:
            return "半束半散，灵动自然"
        elif "温柔" in traits:
            return "柔顺披肩/温婉发髻"
        return {"protagonist": "标志性发型", "antagonist": "凌厉束发"}.get(
            role_type, "时代标准发型"
        )

    def _suggest_prop(self, role_type: str, traits: list) -> str:
        props = {
            "protagonist": "剑/刀/杖 — 与角色成长故事关联",
            "antagonist": "异形武器/暗器/法器 — 体现压迫感",
            "supporting": "特色道具（琴/扇/酒壶）— 辅助性格塑造",
            "minor": "日常用品",
        }
        return props.get(role_type, "无特殊道具")

    def _build_character_image_prompt(
        self, name: str, role_type: str, visual: str, style_guide: dict
    ) -> str:
        """生成角色立绘的图片生成提示词"""
        base = f"{style_guide.get('costume_style', '')}, {visual}"
        return (
            f"full body character design sheet, {name}, "
            f"{base}, "
            f"{style_guide.get('color_scheme', '')}, "
            f"concept art, character reference, front view, "
            f"detailed costume, professional illustration"
        )

    def _llm_enhance_designs(
        self, designs: list, style_guide: dict
    ) -> list[dict]:
        """LLM 增强角色设计"""
        if not designs:
            return designs

        names = [d["name"] for d in designs[:5]]
        prompt = f"""你是影视美术指导。为以下角色增强视觉设计：

角色: {', '.join(names)}
风格: {style_guide.get('genre', '')} — {style_guide.get('costume_style', '')}

为每个角色输出:
- visual_concept: 一句话概括视觉核心概念
- color_palette: 3个推荐颜色(HEX)
- design_detail: 一个独特的视觉记忆点

输出 JSON 数组: [{{"name": "角色名", "visual_concept": "...", "color_palette": ["#XXX"], "design_detail": "..."}}]"""

        try:
            enhanced = self.call_llm(prompt, use_light=False, expect_json=True)
            if isinstance(enhanced, list):
                enhance_map = {item["name"]: item for item in enhanced}
                for design in designs:
                    enh = enhance_map.get(design["name"], {})
                    if enh:
                        design["visual_concept"] = enh.get("visual_concept", "")
                        design["color_palette"] = enh.get("color_palette", [])
                        design["design_detail"] = enh.get("design_detail", "")
        except Exception as e:
            self.log(f"LLM 增强失败: {e}", level="warning")

        return designs


def create_art_designer(config: dict = None, **kwargs) -> ArtDesigner:
    return ArtDesigner(config=config, **kwargs)
