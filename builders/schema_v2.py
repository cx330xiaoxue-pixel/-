"""
Schema v2.0 定义与校验模块

定义小说→剧本改编的增强 YAML Schema（v2.0），
兼容 v1.0 并新增 subtext、beat_type、visual_hint、
relationships、arc_summary、emotion_curve 等字段。

提供 validate() 方法对生成的剧本进行完整性校验。
"""

from typing import Optional


# ═══════════════════════════════════════════════════════════════
# Schema 版本信息
# ═══════════════════════════════════════════════════════════════

SCHEMA_VERSION = "2.0"
SCHEMA_DATE = "2026-06-06"

# 字段枚举
ELEMENT_TYPES = ["dialogue", "narration", "action", "description"]
ROLE_TYPES = ["protagonist", "antagonist", "supporting", "minor", "cameo"]
BEAT_TYPES = ["setup", "confrontation", "payoff", "transition", "revelation"]
TARGET_MEDIUMS = ["film", "tv_series", "stage", "animation", "web_series"]
ATMOSPHERE_VALUES = ["欢快", "忧伤", "紧张", "平静", "温馨", "悬疑", "阴暗",
                     "中性", "激昂", "忧郁", "压抑", "冷峻"]
TIME_VALUES = ["清晨", "早晨", "上午", "中午", "下午", "傍晚", "黄昏",
               "夜晚", "深夜", "黎明", "未指定"]

# ═══════════════════════════════════════════════════════════════
# v2.1 新增：内容分级 & 智能分集
# ═══════════════════════════════════════════════════════════════

CONTENT_GRADES = ["S", "A", "B"]  # 内容分级
EPISODE_FORMATS = ["short_drama", "long_drama"]  # 剧集格式
HOOK_TYPES = ["opening_hook", "mid_conflict", "cliffhanger", "foreshadowing"]  # 钩子类型
CONFLICT_NODE_TYPES = ["major_twist", "scene_shift", "emotional_peak",
                       "cliffhanger", "resolution_point"]  # 冲突节点类型
ADAPTATION_MODES = ["strict", "balanced", "loose"]  # 适应度模式

# 必填字段定义
REQUIRED_METADATA_FIELDS = [
    "script_title", "original_work", "original_author",
    "created_date", "version", "total_chapters_adapted",
    "adapted_chapter_ids", "statistics",
]
REQUIRED_CHARACTER_FIELDS = [
    "character_id", "name", "role_type",
]
REQUIRED_CHAPTER_FIELDS = [
    "chapter_id", "chapter_title", "summary",
    "scene_count", "element_count", "scenes",
]
REQUIRED_SCENE_FIELDS = [
    "scene_id", "scene_number", "location", "element_count", "elements",
]
REQUIRED_ELEMENT_FIELDS = [
    "element_id", "type", "role", "text",
]
# v2.1 新增可选元素字段
OPTIONAL_ELEMENT_FIELDS_V21 = [
    "content_grade",      # "S" | "A" | "B"
    "grade_confidence",   # 0.0-1.0
    "condensed",          # bool (A级压缩标记)
    "merged_from",        # int (B级合并来源数量)
    "original_text",      # str (压缩前原文)
]


# ═══════════════════════════════════════════════════════════════
# 校验函数
# ═══════════════════════════════════════════════════════════════

class SchemaValidator:
    """Schema v2.0 校验器"""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate(self, script: dict) -> tuple:
        """
        校验剧本是否符合 Schema v2.0。

        Args:
            script: 剧本字典

        Returns:
            (is_valid: bool, errors: list, warnings: list)
        """
        self.errors = []
        self.warnings = []

        if "script" not in script:
            self.errors.append("缺少根节点 'script'")
            return False, self.errors, self.warnings

        s = script["script"]

        # 校验三个顶级区块
        self._validate_metadata(s.get("metadata", {}))
        self._validate_characters(s.get("characters", []))
        self._validate_chapters(s.get("chapters", []))

        # 校验情绪曲线（v2.0 新增，可选）
        if "emotion_curve" in s:
            self._validate_emotion_curve(s["emotion_curve"], s.get("chapters", []))

        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings

    def _validate_metadata(self, meta: dict):
        """校验元数据"""
        for field in REQUIRED_METADATA_FIELDS:
            if field not in meta:
                self.errors.append(f"metadata 缺少必填字段: {field}")

        # 校验 target_medium（如果存在）
        if "target_medium" in meta:
            if meta["target_medium"] not in TARGET_MEDIUMS:
                self.warnings.append(
                    f"metadata.target_medium 值 '{meta['target_medium']}' "
                    f"不在推荐值中: {TARGET_MEDIUMS}"
                )

        # 校验 version 格式
        version = meta.get("version", "")
        if version and not version.endswith("-draft") and "-" not in version:
            self.warnings.append(
                f"metadata.version '{version}' 建议使用语义化版本，"
                f"如 '2.0-draft'"
            )

        # 校验 statistics
        stats = meta.get("statistics", {})
        if stats:
            total = stats.get("total_elements", 0)
            dialogue = stats.get("dialogue_count", 0)
            narration = stats.get("narration_count", 0)
            if dialogue + narration > total:
                self.errors.append(
                    f"statistics 中 dialogue_count({dialogue}) + "
                    f"narration_count({narration}) > total_elements({total})"
                )

    def _validate_characters(self, characters: list):
        """校验角色列表"""
        if not characters:
            self.warnings.append("角色列表为空")

        char_ids = set()
        char_names = set()

        for char in characters:
            # 必填字段
            for field in REQUIRED_CHARACTER_FIELDS:
                if field not in char:
                    self.errors.append(
                        f"角色 {char.get('name', '?')} 缺少必填字段: {field}"
                    )

            # character_id 唯一性
            cid = char.get("character_id", "")
            if cid:
                if cid in char_ids:
                    self.errors.append(f"角色 ID 重复: {cid}")
                char_ids.add(cid)
                # 格式校验
                if not cid.startswith("CHAR-"):
                    self.warnings.append(
                        f"角色 ID '{cid}' 建议使用 CHAR-NNN 格式"
                    )

            # 名称唯一性
            name = char.get("name", "")
            if name:
                if name in char_names:
                    self.warnings.append(f"角色名重复: {name}")
                char_names.add(name)

            # role_type 校验
            role_type = char.get("role_type", "")
            if role_type and role_type not in ROLE_TYPES:
                self.warnings.append(
                    f"角色 '{name}' 的 role_type '{role_type}' "
                    f"不在推荐值中: {ROLE_TYPES}"
                )

            # 检查 v2.0 新增字段（提醒但不报错）
            if "arc_summary" not in char:
                self.warnings.append(f"角色 '{name}' 缺少 v2.0 字段: arc_summary")
            if "visual_design" not in char:
                self.warnings.append(f"角色 '{name}' 缺少 v2.0 字段: visual_design")

    def _validate_chapters(self, chapters: list):
        """校验章节列表"""
        if not chapters:
            self.errors.append("章节列表为空")

        for ch in chapters:
            # 必填字段
            for field in REQUIRED_CHAPTER_FIELDS:
                if field not in ch:
                    self.errors.append(
                        f"第{ch.get('chapter_id', '?')}章 缺少必填字段: {field}"
                    )

            # element_count 一致性
            scenes = ch.get("scenes", [])
            actual_element_count = sum(
                scene.get("element_count", 0) for scene in scenes
            )
            declared_count = ch.get("element_count", 0)
            if actual_element_count != declared_count:
                self.warnings.append(
                    f"第{ch.get('chapter_id')}章 element_count 不匹配: "
                    f"声明的 {declared_count} ≠ 实际场景元素总和 {actual_element_count}"
                )

            # scene_count 一致性
            if len(scenes) != ch.get("scene_count", 0):
                self.warnings.append(
                    f"第{ch.get('chapter_id')}章 scene_count 不匹配: "
                    f"声明的 {ch.get('scene_count')} ≠ 实际 {len(scenes)}"
                )

            # 校验每个场景
            for scene in scenes:
                self._validate_scene(scene, ch.get("chapter_id", 0))

    def _validate_scene(self, scene: dict, chapter_id: int):
        """校验单个场景"""
        for field in REQUIRED_SCENE_FIELDS:
            if field not in scene:
                self.errors.append(
                    f"第{chapter_id}章 场景{scene.get('scene_number', '?')} "
                    f"缺少必填字段: {field}"
                )

        # 校验场景元素
        elements = scene.get("elements", [])
        actual_element_count = len(elements)
        declared_count = scene.get("element_count", 0)
        if actual_element_count != declared_count:
            self.warnings.append(
                f"场景 {scene.get('scene_id')} element_count 不匹配: "
                f"声明的 {declared_count} ≠ 实际 {actual_element_count}"
            )

        for elem in elements:
            self._validate_element(elem, scene.get("scene_id", "?"))

        # atmosphere 校验
        atmosphere = scene.get("atmosphere", "")
        if atmosphere and atmosphere not in ATMOSPHERE_VALUES:
            self.warnings.append(
                f"场景 {scene.get('scene_id')} atmosphere '{atmosphere}' "
                f"不在推荐值中"
            )

        # v2.0 新增字段提醒
        if "characters_present" not in scene:
            self.warnings.append(
                f"场景 {scene.get('scene_id')} 缺少 v2.0 字段: characters_present"
            )

    def _validate_element(self, elem: dict, scene_id):
        """校验单个元素"""
        for field in REQUIRED_ELEMENT_FIELDS:
            if field not in elem:
                self.errors.append(
                    f"元素 {elem.get('element_id', '?')} "
                    f"(场景 {scene_id}) 缺少必填字段: {field}"
                )

        # type 枚举校验
        etype = elem.get("type", "")
        if etype and etype not in ELEMENT_TYPES:
            self.errors.append(
                f"元素 {elem.get('element_id')} type '{etype}' "
                f"不在枚举值中: {ELEMENT_TYPES}"
            )

        # subtext 只应用于 dialogue
        if elem.get("subtext") and elem.get("type") != "dialogue":
            self.warnings.append(
                f"元素 {elem.get('element_id')} 类型为 {elem.get('type')}，"
                f"但填写了 subtext（subtext 仅适用于 dialogue）"
            )

        # beat_type 校验
        beat_type = elem.get("beat_type", "")
        if beat_type and beat_type not in BEAT_TYPES:
            self.warnings.append(
                f"元素 {elem.get('element_id')} beat_type '{beat_type}' "
                f"不在推荐值中: {BEAT_TYPES}"
            )

    def _validate_emotion_curve(self, curve: list, chapters: list):
        """校验情绪曲线与章节的一致性"""
        if len(curve) != len(chapters):
            self.warnings.append(
                f"emotion_curve 长度({len(curve)}) 与 chapters 长度"
                f"({len(chapters)}) 不一致"
            )

        for point in curve:
            ch_id = point.get("chapter_id")
            # 检查对应章节存在
            if not any(ch.get("chapter_id") == ch_id for ch in chapters):
                self.warnings.append(
                    f"emotion_curve 中 chapter_id={ch_id} 在 chapters 中不存在"
                )


# ═══════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════

def create_skeleton_script(
    title: str = "未命名剧本",
    author: str = "未知",
    genre: list = None,
    target_medium: str = "tv_series",
) -> dict:
    """生成 Schema v2.0 骨架剧本（用于初始化新项目）"""
    from datetime import datetime

    return {
        "script": {
            "metadata": {
                "script_title": title,
                "original_work": title,
                "original_author": author,
                "adapter": "Novel-to-Script Pro v2.0",
                "created_date": datetime.now().strftime("%Y-%m-%d"),
                "version": "2.0-draft",
                "schema_version": "2.0",
                "genre": genre or [],
                "target_medium": target_medium,
                "language": "zh-CN",
                "total_chapters_adapted": 0,
                "adapted_chapter_ids": [],
                "pipeline_version": "2.0",
                "statistics": {
                    "total_elements": 0,
                    "dialogue_count": 0,
                    "narration_count": 0,
                    "action_count": 0,
                    "estimated_scenes": 0,
                },
            },
            "characters": [],
            "chapters": [],
            "emotion_curve": [],
        }
    }


def quick_validate(script: dict) -> bool:
    """快速校验（只检查最基本的结构完整性）"""
    if "script" not in script:
        return False
    s = script["script"]
    if "metadata" not in s:
        return False
    if "characters" not in s:
        return False
    if "chapters" not in s:
        return False
    return True
