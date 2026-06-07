"""
剧本构建模块 — 将结构化提取结果转换为增强 YAML 剧本（Schema v2.0）

重构自 novel-to-script-yaml/script_builder.py
增强:
  - Schema v2.0 支持（subtext, beat_type, visual_hint, relationships, arc_summary）
  - 角色信息来源于 CharacterTracker（跨章节累积）
  - 场景边界检测优化（支持 LLM 辅助推断）
  - 多格式输出（YAML / JSON / Markdown / 纯文本）
  - 情绪曲线数据生成
"""

import re
from datetime import datetime
from typing import Any, Optional

import yaml


class ScriptBuilder:
    """剧本构建器：将提取的结构化数据组装为符合 Schema v2.0 的 YAML 剧本"""

    def __init__(
        self,
        title: str = "",
        original_work: str = "",
        author: str = "",
        adapter: str = "Novel-to-Script Pro v2.0",
        target_medium: str = "tv_series",
        genre: list = None,
    ):
        self.title = title
        self.original_work = original_work or title
        self.author = author
        self.adapter = adapter
        self.target_medium = target_medium
        self.genre = genre or []
        self.created_date = datetime.now().strftime("%Y-%m-%d")

        # 地点/时间/氛围的关键词库
        self._init_keyword_libraries()

    def _init_keyword_libraries(self):
        """初始化推断关键词库"""
        self.location_keywords = {
            "房间": "室内-房间", "客厅": "室内-客厅", "厨房": "室内-厨房",
            "院": "室外-庭院", "街": "室外-街道", "山": "室外-山野",
            "林": "室外-森林", "殿": "室内-殿堂", "城": "室外-城镇",
            "楼": "室内-楼阁", "河": "室外-河边", "海": "室外-海边",
            "路": "室外-道路", "店": "室内-店铺", "堂": "室内-厅堂",
            "府": "室内-府邸", "庙": "室内-庙宇", "洞": "室外-洞穴",
            "谷": "室外-山谷", "湖": "室外-湖畔", "亭": "室外-亭台",
            "桥": "室外-桥头", "门": "室外-门前", "阁": "室内-阁楼",
            "市": "室外-集市", "村": "室外-村落", "塔": "室内-塔楼",
            "船": "室外-船上", "车": "室外-车中", "舟": "室外-舟中",
        }
        self.time_keywords = {
            "清晨": "清晨", "早晨": "早晨", "上午": "上午",
            "中午": "中午", "下午": "下午", "傍晚": "傍晚", "黄昏": "黄昏",
            "晚上": "夜晚", "深夜": "深夜", "夜": "夜晚", "午时": "中午",
            "黎明": "黎明", "夕阳": "傍晚", "月色": "夜晚", "月光": "夜晚",
            "日出": "清晨", "日落": "傍晚", "子时": "深夜", "辰时": "早晨",
            "暮色": "傍晚", "三更": "深夜", "五更": "黎明",
        }
        self.atmosphere_map = {
            "喜悦": "欢快", "快乐": "欢快", "高兴": "欢快",
            "悲伤": "忧伤", "难过": "忧伤", "愤怒": "紧张", "恐惧": "紧张",
            "紧张": "紧张", "焦虑": "压抑", "平静": "平静", "温柔": "温馨",
            "惊讶": "悬疑", "厌恶": "阴暗", "坚定": "激昂", "愧疚": "忧郁",
            "轻蔑": "冷峻", "嫉妒": "阴暗",
        }

    # ═══════════════════════════════════════════════════════════
    # 主构建方法
    # ═══════════════════════════════════════════════════════════

    def build(
        self,
        all_elements: list,
        character_tracker=None,
        include_emotion: bool = True,
        include_action: bool = True,
        include_subtext: bool = True,
        include_visual_hint: bool = True,
    ) -> dict:
        """将提取结果构建为完整的 YAML 剧本结构"""
        return self.build_with_grading(
            all_elements=all_elements,
            character_tracker=character_tracker,
            include_emotion=include_emotion,
            include_action=include_action,
            include_subtext=include_subtext,
            include_visual_hint=include_visual_hint,
            grading_stats=None,
        )

    def build_with_grading(
        self,
        all_elements: list,
        character_tracker=None,
        include_emotion: bool = True,
        include_action: bool = True,
        include_subtext: bool = True,
        include_visual_hint: bool = True,
        grading_stats: dict = None,
    ) -> dict:
        """
        分级感知的构建入口。

        Args:
            all_elements: 提取的结构化元素（可含 content_grade 字段）
            character_tracker: 角色追踪器
            include_emotion: 是否包含情绪标注
            include_action: 是否包含动作标注
            include_subtext: 是否包含潜台词
            include_visual_hint: 是否包含视觉化提示
            grading_stats: 分级统计 {S_count, A_count, B_count, filtered_count, ...}
        """
        script = self.build(
            all_elements=all_elements,
            character_tracker=character_tracker,
            include_emotion=include_emotion,
            include_action=include_action,
            include_subtext=include_subtext,
            include_visual_hint=include_visual_hint,
        )

        # 如果提供了分级统计，注入元数据
        if grading_stats:
            meta = script["script"]["metadata"]
            meta["content_grading"] = {
                "enabled": True,
                "S_count": grading_stats.get("S_count", 0),
                "A_count": grading_stats.get("A_count", 0),
                "B_count": grading_stats.get("B_count", 0),
                "filtered_count": grading_stats.get("filtered_count", 0),
                "condensed_count": grading_stats.get("condensed_count", 0),
                "preserved_count": grading_stats.get("preserved_count", 0),
            }
            stats = meta.get("statistics", {})
            stats["graded_elements"] = len(all_elements)

        return script

    # ═══════════════════════════════════════════════════════════
    # 元数据
    # ═══════════════════════════════════════════════════════════

    def _build_metadata(self, all_elements: list) -> dict:
        """构建剧本元数据（Schema v2.0）"""
        chapter_ids = sorted(
            set(e.get("chapter_id", 0) for e in all_elements)
        )
        total_elements = len(all_elements)
        dialogue_count = sum(1 for e in all_elements if e.get("type") == "dialogue")
        narration_count = sum(
            1 for e in all_elements if e.get("type") in ("narration", "description")
        )
        action_count = sum(1 for e in all_elements if e.get("type") == "action")

        estimated_scenes = max(1, total_elements // 10)

        return {
            "script_title": self.title or "未命名剧本",
            "original_work": self.original_work,
            "original_author": self.author or "未知",
            "adapter": self.adapter,
            "created_date": self.created_date,
            "version": "2.0-draft",
            "schema_version": "2.0",
            "genre": self.genre,
            "target_medium": self.target_medium,
            "language": "zh-CN",
            "total_chapters_adapted": len(chapter_ids),
            "adapted_chapter_ids": chapter_ids,
            "pipeline_version": "2.0",
            "statistics": {
                "total_elements": total_elements,
                "dialogue_count": dialogue_count,
                "narration_count": narration_count,
                "action_count": action_count,
                "estimated_scenes": estimated_scenes,
            },
        }

    # ═══════════════════════════════════════════════════════════
    # 角色构建（增强：支持 CharacterTracker）
    # ═══════════════════════════════════════════════════════════

    def _build_characters(
        self,
        all_elements: list,
        character_tracker=None,
    ) -> list:
        """构建角色列表"""

        # 优先使用 CharacterTracker 数据
        if character_tracker is not None:
            chars = character_tracker.get_all_characters()
            # 确保 character_id 格式正确
            for i, char in enumerate(chars):
                if "character_id" not in char:
                    char["character_id"] = f"CHAR-{i + 1:03d}"
            return chars

        # Fallback：从 elements 中统计
        return self._build_characters_from_elements(all_elements)

    def _build_characters_from_elements(self, all_elements: list) -> list:
        """从元素中统计角色信息（fallback）"""
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
            role_stats[role]["first_chapter"] = min(role_stats[role]["first_chapter"], ch)
            role_stats[role]["last_chapter"] = max(role_stats[role]["last_chapter"], ch)

        characters = []
        for idx, (name, stats) in enumerate(
            sorted(role_stats.items(), key=lambda x: -x[1]["appearances"]), start=1
        ):
            role_type = self._infer_role_type(stats, len(all_elements))
            primary_emotion = (
                max(set(stats["emotions"]), key=stats["emotions"].count)
                if stats["emotions"] else ""
            )

            characters.append({
                "character_id": f"CHAR-{idx:03d}",
                "name": name,
                "aliases": [],
                "role_type": role_type,
                "description": "",
                "traits": [],
                "relationships": [],
                "arc_summary": "",
                "visual_design": "",
                "first_appearance": f"第{stats['first_chapter']}章",
                "last_appearance": f"第{stats['last_chapter']}章",
                "total_appearances": stats["appearances"],
                "primary_emotion": primary_emotion,
            })

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

    # ═══════════════════════════════════════════════════════════
    # 章节构建
    # ═══════════════════════════════════════════════════════════

    def _build_chapters(
        self,
        all_elements: list,
        include_emotion: bool = True,
        include_action: bool = True,
        include_subtext: bool = True,
        include_visual_hint: bool = True,
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

            # 分场景
            scenes = self._split_into_scenes(elements, ch_id)

            chapter_entry = {
                "chapter_id": ch_id,
                "chapter_title": chapter_title,
                "source_chapter": ch_id,
                "summary": self._generate_chapter_summary(elements),
                "scene_count": len(scenes),
                "element_count": len(elements),
                "emotion_peak": self._detect_emotion_peak(elements),
                "suspense_hook": self._detect_suspense_hook(elements),
                "scenes": scenes,
            }
            chapters.append(chapter_entry)

        return chapters

    # ═══════════════════════════════════════════════════════════
    # 场景拆分
    # ═══════════════════════════════════════════════════════════

    def _split_into_scenes(self, elements: list, chapter_id: int) -> list:
        """将章节内的元素按自然断点分为场景"""
        if not elements:
            return []

        scenes = []
        current_scene_elements = []
        scene_counter = 0

        for elem in elements:
            current_scene_elements.append(elem)

            # 场景断点：长旁白 + 有一定积累
            etype = elem.get("type", "")
            text = elem.get("text", "")
            if etype in ("narration", "description") and len(text) > 100:
                if len(current_scene_elements) >= 3:
                    scene_counter += 1
                    scenes.append(
                        self._build_scene(current_scene_elements, chapter_id, scene_counter)
                    )
                    current_scene_elements = []
            elif len(current_scene_elements) >= 15:
                scene_counter += 1
                scenes.append(
                    self._build_scene(current_scene_elements, chapter_id, scene_counter)
                )
                current_scene_elements = []

        # 剩余元素
        if current_scene_elements:
            scene_counter += 1
            scenes.append(
                self._build_scene(current_scene_elements, chapter_id, scene_counter)
            )

        return scenes

    def _build_scene(
        self, elements: list, chapter_id: int, scene_number: int
    ) -> dict:
        """构建单个场景（Schema v2.0）"""
        location = self._infer_location(elements)
        time_of_day = self._infer_time(elements)
        atmosphere = self._infer_atmosphere(elements)

        # 出场角色
        characters_present = []
        seen = set()
        for elem in elements:
            role = elem.get("role", "").strip()
            if role and role != "旁白" and role not in seen:
                seen.add(role)
                characters_present.append(role)

        # 道具推断
        props_needed = self._infer_props(elements)

        # 构建元素
        scene_elements = []
        for elem in elements:
            scene_elem = {
                "element_id": (
                    f"{chapter_id}.{scene_number}."
                    f"{elem.get('global_id', elem.get('id', 0))}"
                ),
                "type": elem.get("type", "narration"),
                "role": elem.get("role", "旁白"),
                "text": elem.get("text", ""),
            }

            # 可选字段（按 Schema v2.0）
            if elem.get("emotion"):
                scene_elem["emotion"] = elem["emotion"]
            if elem.get("action"):
                scene_elem["action"] = elem["action"]
            if elem.get("subtext"):
                scene_elem["subtext"] = elem["subtext"]
            if elem.get("beat_type"):
                scene_elem["beat_type"] = elem["beat_type"]
            if elem.get("visual_hint"):
                scene_elem["visual_hint"] = elem["visual_hint"]
            if elem.get("parenthetical"):
                scene_elem["parenthetical"] = elem["parenthetical"]
            # v2.1: 内容分级字段
            if elem.get("content_grade"):
                scene_elem["content_grade"] = elem["content_grade"]
                scene_elem["grade_confidence"] = elem.get("grade_confidence", 0)
            if elem.get("condensed"):
                scene_elem["condensed"] = True
                scene_elem["original_text"] = elem.get("original_text", "")
            if elem.get("merged_from"):
                scene_elem["merged_from"] = elem["merged_from"]

            scene_elements.append(scene_elem)

        return {
            "scene_id": f"{chapter_id}.{scene_number}",
            "scene_number": scene_number,
            "location": location,
            "time": time_of_day,
            "atmosphere": atmosphere,
            "characters_present": characters_present,
            "props_needed": props_needed,
            "element_count": len(scene_elements),
            "elements": scene_elements,
        }

    # ═══════════════════════════════════════════════════════════
    # 推断方法
    # ═══════════════════════════════════════════════════════════

    def _infer_location(self, elements: list) -> str:
        for elem in elements:
            text = elem.get("text", "")
            for keyword, location in self.location_keywords.items():
                if keyword in text:
                    return location
        return "未指定"

    def _infer_time(self, elements: list) -> str:
        for elem in elements:
            text = elem.get("text", "")
            for keyword, time_desc in self.time_keywords.items():
                if keyword in text:
                    return time_desc
        return "未指定"

    def _infer_atmosphere(self, elements: list) -> str:
        emotions = [e.get("emotion", "") for e in elements if e.get("emotion")]
        if not emotions:
            return "中性"
        most_common = max(set(emotions), key=emotions.count)
        return self.atmosphere_map.get(most_common, "中性")

    def _infer_props(self, elements: list) -> list:
        """推断场景所需道具"""
        prop_keywords = {
            "剑": "剑", "刀": "刀", "枪": "枪", "棍": "棍",
            "茶": "茶具", "酒": "酒具", "书": "书籍/文书", "信": "信件",
            "药": "药品", "钱": "银两/钱币", "杯": "杯具", "碗": "碗筷",
            "灯": "灯具", "烛": "蜡烛", "桌": "桌椅", "椅": "桌椅",
            "床": "床榻", "镜": "镜子", "扇": "扇子", "伞": "雨伞",
            "琴": "琴", "棋": "棋具", "画": "画卷", "笔": "笔墨",
            "香": "香炉", "囊": "香囊/锦囊", "玉佩": "玉佩", "簪": "发簪",
        }
        props = set()
        for elem in elements:
            text = elem.get("text", "")
            for keyword, prop_name in prop_keywords.items():
                if keyword in text:
                    props.add(prop_name)
        return sorted(props)

    def _detect_emotion_peak(self, elements: list) -> dict:
        """检测本章情绪峰值"""
        emotions = [e.get("emotion", "") for e in elements if e.get("emotion")]
        if not emotions:
            return {"emotion": "", "intensity": 0}

        from collections import Counter
        counter = Counter(emotions)
        top_emotion = counter.most_common(1)[0]
        intensity = min(10, len(emotions) / max(len(elements), 1) * 20)

        return {
            "emotion": top_emotion[0],
            "frequency": top_emotion[1],
            "intensity": round(intensity, 1),
        }

    def _detect_suspense_hook(self, elements: list) -> str:
        """检测章末悬念钩子"""
        # 取最后 20 个元素分析
        tail = elements[-20:] if len(elements) > 20 else elements
        # 检查是否有未解决冲突或悬念
        suspense_keywords = ["突然", "忽然", "却", "然而", "但", "不料",
                              "谁知", "没想到", "竟然", "难道", "难道说"]
        for elem in reversed(tail):
            text = elem.get("text", "")
            for kw in suspense_keywords:
                if kw in text:
                    return text[:150]
        # 返回最后一段 narration
        for elem in reversed(tail):
            if elem.get("type") in ("narration", "description"):
                return elem.get("text", "")[:150]
        return ""

    # ═══════════════════════════════════════════════════════════
    # 情绪曲线
    # ═══════════════════════════════════════════════════════════

    def _build_emotion_curve(self, chapters: list) -> list:
        """生成全剧情绪曲线数据"""
        curve = []
        for ch in chapters:
            scenes_data = []
            for scene in ch.get("scenes", []):
                emotions_in_scene = []
                for elem in scene.get("elements", []):
                    if elem.get("emotion"):
                        emotions_in_scene.append(elem["emotion"])
                scenes_data.append({
                    "scene_id": scene["scene_id"],
                    "atmosphere": scene.get("atmosphere", "中性"),
                    "dominant_emotion": (
                        max(set(emotions_in_scene), key=emotions_in_scene.count)
                        if emotions_in_scene else ""
                    ),
                })

            curve.append({
                "chapter_id": ch["chapter_id"],
                "chapter_title": ch["chapter_title"],
                "emotion_peak": ch.get("emotion_peak", {}),
                "suspense_hook": ch.get("suspense_hook", ""),
                "scenes": scenes_data,
            })

        return curve

    def _generate_chapter_summary(self, elements: list) -> str:
        """生成章节摘要"""
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

    # ═══════════════════════════════════════════════════════════
    # 输出方法
    # ═══════════════════════════════════════════════════════════

    def to_yaml(self, script: dict) -> str:
        """将剧本字典转换为 YAML 字符串（美化格式）"""

        class ScriptDumper(yaml.Dumper):
            pass

        def str_representer(dumper, data):
            """多行字符串使用 literal block scalar"""
            if "\n" in data and len(data) > 80:
                return dumper.represent_scalar(
                    "tag:yaml.org,2002:str", data, style="|"
                )
            if len(data) > 120:
                return dumper.represent_scalar(
                    "tag:yaml.org,2002:str", data, style=">"
                )
            return dumper.represent_scalar("tag:yaml.org,2002:str", data)

        ScriptDumper.add_representer(str, str_representer)

        return yaml.dump(
            script,
            Dumper=ScriptDumper,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            width=120,
        )

    def to_json(self, script: dict) -> str:
        """将剧本导出为 JSON 格式"""
        import json
        return json.dumps(script, ensure_ascii=False, indent=2)

    def to_plain_text(self, script: dict) -> str:
        """将剧本导出为纯文本格式"""
        lines = []
        meta = script["script"]["metadata"]
        lines.append(f"{'='*50}")
        lines.append(f"剧名：《{meta['script_title']}》")
        lines.append(f"原著：《{meta['original_work']}》 作者：{meta['original_author']}")
        lines.append(f"改编工具：{meta['adapter']}")
        lines.append(f"生成日期：{meta['created_date']}")
        lines.append(f"{'='*50}")

        # 角色
        lines.append(f"\n👥 角色列表 ({len(script['script']['characters'])}人)")
        lines.append("-" * 30)
        for char in script["script"]["characters"]:
            lines.append(
                f"  [{char['role_type']}] {char['name']}"
                f"（出场 {char['total_appearances']} 次）"
            )
            if char.get("description"):
                lines.append(f"    描述: {char['description']}")
            if char.get("traits"):
                lines.append(f"    特征: {', '.join(char['traits'])}")

        # 章节
        for ch in script["script"]["chapters"]:
            lines.append(f"\n{'='*50}")
            lines.append(f"第{ch['chapter_id']}章 {ch['chapter_title']}")
            lines.append(f"{'='*50}")

            for scene in ch.get("scenes", []):
                lines.append(
                    f"\n【场景{scene['scene_number']}】"
                    f" {scene.get('location', '')} — {scene.get('time', '')}"
                    f" | 氛围: {scene.get('atmosphere', '')}"
                )
                lines.append("")

                for elem in scene.get("elements", []):
                    text = elem.get("text", "")
                    role = elem.get("role", "")
                    etype = elem.get("type", "")

                    if etype == "dialogue" and role != "旁白":
                        prefix = f"  {role}："
                    elif etype in ("narration", "description"):
                        prefix = "  [旁白] "
                    elif etype == "action":
                        prefix = f"  [{role} 动作] "
                    else:
                        prefix = "  "

                    lines.append(prefix + text)

                    # 附加信息
                    extras = []
                    if elem.get("emotion"):
                        extras.append(f"情绪: {elem['emotion']}")
                    if elem.get("subtext"):
                        extras.append(f"潜台词: {elem['subtext']}")
                    if extras:
                        lines.append(f"    （{'；'.join(extras)}）")

                lines.append("")

        return "\n".join(lines)

    def save(self, script: dict, output_path: str) -> str:
        """保存剧本到 YAML 文件"""
        yaml_content = self.to_yaml(script)

        header = (
            f"# ============================================================\n"
            f"# Novel-to-Script Pro v2.0 生成\n"
            f"# 剧本名称: {script['script']['metadata']['script_title']}\n"
            f"# 原著: {script['script']['metadata']['original_work']}\n"
            f"# 生成日期: {script['script']['metadata']['created_date']}\n"
            f"# Schema 版本: 2.0\n"
            f"# 本文件遵循 schema/scripts-yaml-schema-v2.md\n"
            f"# ============================================================\n\n"
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header + yaml_content)

        print(f"✅ 剧本已保存到: {output_path}")
        return output_path
