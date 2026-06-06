"""
角色追踪器 — 跨章节角色信息追踪与管理

功能:
  - 角色信息跨章节累积与合并
  - 别名自动关联与消歧
  - 角色关系图谱构建
  - 角色弧线进度追踪
  - 角色出场统计与可视化数据
"""

from collections import defaultdict
from typing import Optional


class CharacterTracker:
    """跨章节角色信息追踪器"""

    def __init__(self):
        # 角色主表: {角色名: 角色信息字典}
        self.characters: dict = {}
        # 别名索引: {别名: 规范名}
        self.alias_index: dict = {}
        # 关系图: {(角色A, 角色B): 关系描述}
        self.relationships: dict = {}
        # 章节级出场记录: {chapter_id: [角色名列表]}
        self.appearance_log: dict = {}
        # 角色弧线历史: {角色名: [{chapter_id, emotion, summary}]}
        self.arc_history: dict = defaultdict(list)

    # ═══════════════════════════════════════════════════════════
    # 角色注册与更新
    # ═══════════════════════════════════════════════════════════

    def register_character(
        self,
        name: str,
        aliases: list = None,
        role_type: str = "minor",
        description: str = "",
        traits: list = None,
        chapter_id: int = 1,
        first_scene: str = "",
    ) -> str:
        """
        注册或更新一个角色。

        Args:
            name: 角色名称（规范名）
            aliases: 别名列表
            role_type: 角色类型
            description: 角色描述
            traits: 性格特征
            chapter_id: 首次出现的章节
            first_scene: 首次出现的场景描述

        Returns:
            角色的规范名称
        """
        canonical = self._resolve_canonical_name(name)

        if canonical not in self.characters:
            # 新建角色
            self.characters[canonical] = {
                "name": canonical,
                "aliases": [],
                "role_type": role_type,
                "description": description,
                "traits": traits or [],
                "first_appearance_chapter": chapter_id,
                "first_appearance_scene": first_scene,
                "last_appearance_chapter": chapter_id,
                "total_appearances": 1,
                "chapter_appearances": [chapter_id],
                "emotion_history": [],
                "arc_stage": "introduction",
            }
        else:
            # 更新已有角色
            char = self.characters[canonical]
            char["last_appearance_chapter"] = max(
                char["last_appearance_chapter"], chapter_id
            )
            char["total_appearances"] += 1
            if chapter_id not in char["chapter_appearances"]:
                char["chapter_appearances"].append(chapter_id)

            # 合并新信息
            if description and not char["description"]:
                char["description"] = description
            if traits:
                char["traits"] = list(set(char["traits"] + traits))
            if role_type != "minor" and char["role_type"] == "minor":
                char["role_type"] = role_type

        # 注册别名
        if aliases:
            for alias in aliases:
                if alias and alias != canonical:
                    self.alias_index[alias] = canonical
                    if alias not in self.characters[canonical]["aliases"]:
                        self.characters[canonical]["aliases"].append(alias)

        # 更新关系
        if canonical != name and name not in self.alias_index:
            self.alias_index[name] = canonical

        return canonical

    def update_from_elements(
        self, elements: list, chapter_id: int
    ) -> dict:
        """
        从提取的元素中批量更新角色信息。

        Args:
            elements: LLM/规则提取的元素列表
            chapter_id: 当前章节ID

        Returns:
            本章新发现的角色统计
        """
        roles_seen = set()
        for elem in elements:
            role = elem.get("role", "").strip()
            if not role or role == "旁白":
                continue

            canonical = self.register_character(
                name=role,
                chapter_id=chapter_id,
            )
            roles_seen.add(canonical)

            # 记录情绪历史
            emotion = elem.get("emotion", "")
            if emotion:
                self.characters[canonical]["emotion_history"].append({
                    "chapter_id": chapter_id,
                    "emotion": emotion,
                })
                self.arc_history[canonical].append({
                    "chapter_id": chapter_id,
                    "emotion": emotion,
                    "text_preview": elem.get("text", "")[:50],
                })

        # 记录本章出场
        self.appearance_log[chapter_id] = list(roles_seen)

        # 更新弧线阶段
        for name in roles_seen:
            self._update_arc_stage(name)

        return {
            "new_characters": len(roles_seen - set(self.characters.keys())),
            "total_characters": len(self.characters),
            "chapter_roles": list(roles_seen),
        }

    def merge_extracted_characters(
        self, extracted_chars: list, chapter_id: int
    ) -> dict:
        """
        合并 LLM extract_characters() 的结果。

        Args:
            extracted_chars: LLM 角色提取结果
            chapter_id: 当前章节

        Returns:
            合并统计
        """
        new_count = 0
        updated_count = 0

        for char_info in extracted_chars:
            name = char_info.get("name", "")
            if not name:
                continue

            aliases = char_info.get("aliases", [])
            role_type = char_info.get("role_type", "minor")
            description = char_info.get("description", "")
            traits = char_info.get("traits", [])
            relationships = char_info.get("relationships", [])

            canonical = self.register_character(
                name=name,
                aliases=aliases,
                role_type=role_type,
                description=description,
                traits=traits,
                chapter_id=chapter_id,
            )

            if canonical not in self.characters:
                new_count += 1
            else:
                updated_count += 1

            # 记录角色关系
            for rel in relationships:
                target = rel.get("target", "")
                relation = rel.get("relation", "")
                if target and relation:
                    self.add_relationship(canonical, target, relation)

        return {
            "new": new_count,
            "updated": updated_count,
            "total": len(self.characters),
        }

    # ═══════════════════════════════════════════════════════════
    # 关系管理
    # ═══════════════════════════════════════════════════════════

    def add_relationship(self, char_a: str, char_b: str, relation: str):
        """添加或更新角色关系"""
        canonical_a = self._resolve_canonical_name(char_a)
        canonical_b = self._resolve_canonical_name(char_b)

        # 确保两个角色都已注册
        if canonical_a not in self.characters:
            self.register_character(canonical_a)
        if canonical_b not in self.characters:
            self.register_character(canonical_b)

        # 双向记录（排序保证唯一性）
        key = tuple(sorted([canonical_a, canonical_b]))
        if key not in self.relationships:
            self.relationships[key] = []
        if relation not in self.relationships[key]:
            self.relationships[key].append(relation)

    def get_relationships_for(self, name: str) -> list:
        """获取某个角色的所有关系"""
        canonical = self._resolve_canonical_name(name)
        result = []
        for (a, b), relations in self.relationships.items():
            if a == canonical:
                result.append({"target": b, "relations": relations})
            elif b == canonical:
                result.append({"target": a, "relations": relations})
        return result

    # ═══════════════════════════════════════════════════════════
    # 查询方法
    # ═══════════════════════════════════════════════════════════

    def get_character(self, name: str) -> Optional[dict]:
        """通过名称（含别名）获取角色信息"""
        canonical = self._resolve_canonical_name(name)
        return self.characters.get(canonical)

    def get_all_characters(self) -> list:
        """获取所有角色的完整信息列表"""
        result = []
        for idx, (name, info) in enumerate(
            sorted(self.characters.items(),
                   key=lambda x: -x[1]["total_appearances"])
        ):
            char = dict(info)
            char["character_id"] = f"CHAR-{idx + 1:03d}"
            char["relationships"] = self.get_relationships_for(name)
            char["aliases"] = list(set(char.get("aliases", [])))  # 去重
            # 推断主导情绪
            emotions = [e["emotion"] for e in char.get("emotion_history", [])
                        if e.get("emotion")]
            char["primary_emotion"] = (
                max(set(emotions), key=emotions.count) if emotions else ""
            )
            result.append(char)
        return result

    def get_chapter_roles(self, chapter_id: int) -> list:
        """获取某章出场的角色列表"""
        return self.appearance_log.get(chapter_id, [])

    def get_arc_summary(self, name: str) -> dict:
        """获取角色的弧线摘要"""
        canonical = self._resolve_canonical_name(name)
        char = self.characters.get(canonical, {})
        history = self.arc_history.get(canonical, [])

        # 情感变化
        emotions = [h["emotion"] for h in history if h.get("emotion")]
        emotion_sequence = []
        prev = None
        for e in emotions:
            if e != prev:
                emotion_sequence.append(e)
                prev = e

        return {
            "name": canonical,
            "role_type": char.get("role_type", "unknown"),
            "first_appearance": char.get("first_appearance_chapter"),
            "last_appearance": char.get("last_appearance_chapter"),
            "total_appearances": char.get("total_appearances", 0),
            "arc_stage": char.get("arc_stage", "unknown"),
            "emotion_sequence": emotion_sequence,
        }

    def get_statistics(self) -> dict:
        """获取全局统计"""
        role_types = defaultdict(int)
        for char in self.characters.values():
            role_types[char.get("role_type", "minor")] += 1

        return {
            "total_characters": len(self.characters),
            "by_role_type": dict(role_types),
            "total_relationships": len(self.relationships),
            "chapters_covered": len(self.appearance_log),
        }

    # ═══════════════════════════════════════════════════════════
    # 内部方法
    # ═══════════════════════════════════════════════════════════

    def _resolve_canonical_name(self, name: str) -> str:
        """将名称解析为规范角色名（通过别名索引）"""
        if name in self.characters:
            return name
        if name in self.alias_index:
            return self.alias_index[name]
        return name  # 新名称，直接返回

    def _update_arc_stage(self, name: str):
        """根据出场次数更新角色弧线阶段"""
        char = self.characters.get(name)
        if not char:
            return

        appearances = char["total_appearances"]
        if appearances <= 2:
            char["arc_stage"] = "introduction"
        elif appearances <= 5:
            char["arc_stage"] = "development"
        elif appearances <= 10:
            char["arc_stage"] = "crisis_or_transformation"
        else:
            char["arc_stage"] = "resolution_or_legacy"

    def to_dict(self) -> dict:
        """序列化所有跟踪数据为字典"""
        return {
            "characters": self.characters,
            "alias_index": self.alias_index,
            "relationships": {
                f"{a}|{b}": rels
                for (a, b), rels in self.relationships.items()
            },
            "appearance_log": self.appearance_log,
            "arc_history": dict(self.arc_history),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterTracker":
        """从字典恢复跟踪器状态"""
        tracker = cls()
        tracker.characters = data.get("characters", {})
        tracker.alias_index = data.get("alias_index", {})
        tracker.relationships = {
            tuple(key.split("|")): rels
            for key, rels in data.get("relationships", {}).items()
        }
        tracker.appearance_log = {
            int(k): v for k, v in data.get("appearance_log", {}).items()
        }
        tracker.arc_history = defaultdict(
            list, {k: v for k, v in data.get("arc_history", {}).items()}
        )
        return tracker
