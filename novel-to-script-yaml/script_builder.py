"""
剧本构建模块 - 将结构化提取结果转换为 YAML 剧本
遵循 scripts-yaml-schema.md 定义的 Schema
"""

from datetime import datetime
from typing import Any, Optional

import yaml


class ScriptBuilder:
    """剧本构建器：将提取的结构化数据组装为符合 Schema 的 YAML 剧本"""

    def __init__(self, title: str = "", original_work: str = "", author: str = ""):
        self.title = title
        self.original_work = original_work or title
        self.author = author
        self.adapter = "AI 辅助剧本创作工具 v1.0"
        self.created_date = datetime.now().strftime("%Y-%m-%d")

    def build(
        self,
        all_elements: list,
        character_info: Optional[dict] = None,
        include_emotion: bool = True,
        include_action: bool = True,
    ) -> dict:
        """将提取结果构建为完整的 YAML 剧本结构"""

        # 1. 构建元数据
        metadata = self._build_metadata(all_elements)

        # 2. 构建角色列表
        characters = self._build_characters(all_elements, character_info)

        # 3. 构建章节-场景结构
        chapters = self._build_chapters(
            all_elements, include_emotion, include_action
        )

        # 4. 组装完整剧本
        script = {
            "script": {
                "metadata": metadata,
                "characters": characters,
                "chapters": chapters,
            }
        }

        return script

    def _build_metadata(self, all_elements: list) -> dict:
        """构建剧本元数据"""
        chapter_ids = sorted(
            set(e.get("chapter_id", 0) for e in all_elements)
        )
        total_elements = len(all_elements)
        dialogue_count = sum(
            1 for e in all_elements if e.get("type") == "dialogue"
        )
        narration_count = sum(
            1 for e in all_elements if e.get("type") in ("narration", "description")
        )

        # 估算总场景数（每10个左右元素构成一个场景）
        estimated_scenes = max(1, total_elements // 10)

        return {
            "script_title": self.title or "未命名剧本",
            "original_work": self.original_work,
            "original_author": self.author or "未知",
            "adapter": self.adapter,
            "created_date": self.created_date,
            "version": "1.0-draft",
            "total_chapters_adapted": len(chapter_ids),
            "adapted_chapter_ids": chapter_ids,
            "statistics": {
                "total_elements": total_elements,
                "dialogue_count": dialogue_count,
                "narration_count": narration_count,
                "estimated_scenes": estimated_scenes,
            },
        }

    def _build_characters(
        self,
        all_elements: list,
        character_info: Optional[dict] = None,
    ) -> list:
        """构建角色列表"""
        # 统计角色出现频率
        role_stats: dict = {}
        for elem in all_elements:
            role = elem.get("role", "").strip()
            if not role or role == "旁白":
                continue
            if role not in role_stats:
                role_stats[role] = {
                    "name": role,
                    "appearances": 0,
                    "emotions": [],
                    "first_chapter": float("inf"),
                    "last_chapter": 0,
                }
            role_stats[role]["appearances"] += 1
            if elem.get("emotion"):
                role_stats[role]["emotions"].append(elem["emotion"])
            ch = elem.get("chapter_id", 0)
            role_stats[role]["first_chapter"] = min(
                role_stats[role]["first_chapter"], ch
            )
            role_stats[role]["last_chapter"] = max(
                role_stats[role]["last_chapter"], ch
            )

        characters = []
        for idx, (name, stats) in enumerate(
            sorted(role_stats.items(), key=lambda x: -x[1]["appearances"]),
            start=1,
        ):
            # 推断角色类型
            role_type = self._infer_role_type(stats, len(all_elements))

            # 推断主要情绪
            primary_emotion = (
                max(set(stats["emotions"]), key=stats["emotions"].count)
                if stats["emotions"]
                else ""
            )

            char_entry = {
                "character_id": f"CHAR-{idx:03d}",
                "name": name,
                "aliases": [] if character_info is None
                else character_info.get(name, {}).get("aliases", []),
                "role_type": role_type,
                "description": "",
                "traits": [],
                "first_appearance": f"第{stats['first_chapter']}章",
                "last_appearance": f"第{stats['last_chapter']}章",
                "total_appearances": stats["appearances"],
                "primary_emotion": primary_emotion,
            }

            # 合并外部提供的角色信息
            if character_info and name in character_info:
                info = character_info[name]
                char_entry["description"] = info.get("description", "")
                char_entry["traits"] = info.get("traits", [])
                char_entry["role_type"] = info.get("role_type", role_type)
                char_entry["aliases"] = info.get("aliases", [])

            characters.append(char_entry)

        return characters

    def _infer_role_type(self, stats: dict, total_elements: int) -> str:
        """根据出场频率推断角色类型"""
        ratio = stats["appearances"] / max(total_elements, 1)
        if ratio > 0.15:
            return "protagonist"
        elif ratio > 0.05:
            return "supporting"
        else:
            return "minor"

    def _build_chapters(
        self,
        all_elements: list,
        include_emotion: bool = True,
        include_action: bool = True,
    ) -> list:
        """构建章节-场景-元素层级结构"""
        # 按章节分组
        chapter_groups: dict = {}
        for elem in all_elements:
            ch_id = elem.get("chapter_id", 0)
            if ch_id not in chapter_groups:
                chapter_groups[ch_id] = []
            chapter_groups[ch_id].append(elem)

        chapters = []
        for ch_id in sorted(chapter_groups.keys()):
            elements = chapter_groups[ch_id]
            chapter_title = elements[0].get("chapter_title", f"第{ch_id}章")

            # 将章节内的元素分为场景（按自然段落间隔划分）
            scenes = self._split_into_scenes(elements, ch_id)

            chapter_entry = {
                "chapter_id": ch_id,
                "chapter_title": chapter_title,
                "source_chapter": ch_id,
                "summary": self._generate_scene_summary(elements),
                "scene_count": len(scenes),
                "element_count": len(elements),
                "scenes": scenes,
            }
            chapters.append(chapter_entry)

        return chapters

    def _split_into_scenes(
        self, elements: list, chapter_id: int
    ) -> list:
        """将章节内的元素按自然断点分为场景"""
        if not elements:
            return []

        scenes = []
        current_scene_elements = []
        scene_counter = 0

        for elem in elements:
            current_scene_elements.append(elem)

            # 场景断点判断：遇到长段旁白描述或连续对话结束后
            if elem.get("type") in ("narration", "description") and len(
                elem.get("text", "")
            ) > 100:
                if len(current_scene_elements) >= 3:
                    scene_counter += 1
                    scenes.append(
                        self._build_scene(
                            current_scene_elements, chapter_id, scene_counter
                        )
                    )
                    current_scene_elements = []
            elif len(current_scene_elements) >= 15:
                scene_counter += 1
                scenes.append(
                    self._build_scene(
                        current_scene_elements, chapter_id, scene_counter
                    )
                )
                current_scene_elements = []

        # 剩余元素组成尾场
        if current_scene_elements:
            scene_counter += 1
            scenes.append(
                self._build_scene(
                    current_scene_elements, chapter_id, scene_counter
                )
            )

        return scenes

    def _build_scene(
        self, elements: list, chapter_id: int, scene_number: int
    ) -> dict:
        """构建单个场景"""
        # 推断场景地点和时间
        location = self._infer_location(elements)
        time_of_day = self._infer_time(elements)
        atmosphere = self._infer_atmosphere(elements)

        # 构建场景元素
        scene_elements = []
        for elem in elements:
            scene_elem = {
                "element_id": f"{chapter_id}.{scene_number}.{elem.get('global_id', elem.get('id', 0))}",
                "type": elem.get("type", "narration"),
                "role": elem.get("role", "旁白"),
                "text": elem.get("text", ""),
            }

            if elem.get("emotion"):
                scene_elem["emotion"] = elem["emotion"]
            if elem.get("action"):
                scene_elem["action"] = elem["action"]
            if elem.get("parenthetical"):
                scene_elem["parenthetical"] = elem["parenthetical"]

            scene_elements.append(scene_elem)

        return {
            "scene_id": f"{chapter_id}.{scene_number}",
            "scene_number": scene_number,
            "location": location,
            "time": time_of_day,
            "atmosphere": atmosphere,
            "element_count": len(scene_elements),
            "elements": scene_elements,
        }

    def _infer_location(self, elements: list) -> str:
        """从文本中推断场景地点"""
        # 简单关键词匹配
        location_keywords = {
            "房间": "室内-房间",
            "客厅": "室内-客厅",
            "厨房": "室内-厨房",
            "院": "室外-庭院",
            "街": "室外-街道",
            "山": "室外-山野",
            "林": "室外-森林",
            "殿": "室内-殿堂",
            "城": "室外-城镇",
            "楼": "室内-楼阁",
            "河": "室外-河边",
            "海": "室外-海边",
            "路": "室外-道路",
            "店": "室内-店铺",
            "堂": "室内-厅堂",
            "府": "室内-府邸",
        }

        for elem in elements:
            text = elem.get("text", "")
            for keyword, location in location_keywords.items():
                if keyword in text:
                    return location

        return "未指定"

    def _infer_time(self, elements: list) -> str:
        """从文本中推断时间"""
        time_keywords = {
            "清晨": "清晨",
            "早晨": "早晨",
            "早上": "早晨",
            "上午": "上午",
            "中午": "中午",
            "下午": "下午",
            "傍晚": "傍晚",
            "黄昏": "黄昏",
            "晚上": "夜晚",
            "深夜": "深夜",
            "夜": "夜晚",
            "午时": "中午",
            "黎明": "黎明",
            "夕阳": "傍晚",
            "月色": "夜晚",
            "月光": "夜晚",
            "日出": "清晨",
            "日落": "傍晚",
        }

        for elem in elements:
            text = elem.get("text", "")
            for keyword, time_desc in time_keywords.items():
                if keyword in text:
                    return time_desc

        return "未指定"

    def _infer_atmosphere(self, elements: list) -> str:
        """从情绪标签推断场景氛围"""
        emotions = [
            e.get("emotion", "")
            for e in elements
            if e.get("emotion")
        ]
        if not emotions:
            return "中性"

        # 统计情绪频率
        emotion_map = {
            "喜悦": "欢快",
            "快乐": "欢快",
            "高兴": "欢快",
            "悲伤": "忧伤",
            "难过": "忧伤",
            "愤怒": "紧张",
            "恐惧": "紧张",
            "紧张": "紧张",
            "焦虑": "压抑",
            "平静": "平静",
            "温柔": "温馨",
            "惊讶": "悬疑",
            "厌恶": "阴暗",
        }

        # 取最常见的情绪
        most_common = max(set(emotions), key=emotions.count)
        return emotion_map.get(most_common, "中性")

    def _generate_scene_summary(self, elements: list) -> str:
        """生成场景摘要"""
        characters = set()
        for elem in elements:
            role = elem.get("role", "")
            if role and role != "旁白":
                characters.add(role)

        first_text = ""
        for elem in elements:
            if elem.get("type") == "narration":
                first_text = elem.get("text", "")[:100]
                break

        summary = f"涉及角色：{'、'.join(sorted(characters)) if characters else '无'}。"
        if first_text:
            summary += f" 开场：{first_text}..."
        return summary

    def to_yaml(self, script: dict) -> str:
        """将剧本字典转换为 YAML 字符串"""

        class _ScriptDumper(yaml.Dumper):
            pass

        def _str_representer(dumper, data):
            """多行字符串使用 literal block scalar"""
            if "\n" in data and len(data) > 80:
                return dumper.represent_scalar(
                    "tag:yaml.org,2002:str", data, style="|"
                )
            return dumper.represent_scalar(
                "tag:yaml.org,2002:str", data
            )

        _ScriptDumper.add_representer(str, _str_representer)

        return yaml.dump(
            script,
            Dumper=_ScriptDumper,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            width=120,
        )

    def save(self, script: dict, output_path: str) -> str:
        """保存剧本到 YAML 文件"""
        yaml_content = self.to_yaml(script)

        # 添加 Schema 引用注释
        header = (
            f"# ============================================================\n"
            f"# AI 辅助剧本创作工具 生成\n"
            f"# 剧本名称: {script['script']['metadata']['script_title']}\n"
            f"# 原著: {script['script']['metadata']['original_work']}\n"
            f"# 生成日期: {script['script']['metadata']['created_date']}\n"
            f"# Schema 版本: 1.0\n"
            f"# 本文件遵循 scripts-yaml-schema.md 定义的 Schema\n"
            f"# ============================================================\n\n"
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header + yaml_content)

        print(f"✅ 剧本已保存到: {output_path}")
        return output_path
