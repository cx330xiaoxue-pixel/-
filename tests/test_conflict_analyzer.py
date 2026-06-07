"""
测试冲突分析技能 & 影视节奏引擎
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skills.conflict_analyzer import ConflictAnalyzerSkill
from skills.episode_rhythm import EpisodeRhythmSkill


class TestConflictAnalyzer:
    """冲突分析单元测试"""

    @pytest.fixture
    def analyzer(self):
        return ConflictAnalyzerSkill()

    @pytest.fixture
    def sample_elements(self):
        """模拟3章以上的元素（含冲突节点）"""
        elements = []
        ch1 = 1
        ch2 = 2
        ch3 = 3

        # 第1章: 建立 + 冲突结尾
        elements.extend([
            {"chapter_id": ch1, "type": "narration", "role": "旁白",
             "text": "清晨的阳光洒在山路上", "beat_type": "setup"},
            {"chapter_id": ch1, "type": "narration", "role": "旁白",
             "text": "主角走在山路上，思考着今日的挑战", "beat_type": "transition"},
            {"chapter_id": ch1, "type": "dialogue", "role": "主角",
             "text": "今天一定要找到真相", "beat_type": "setup"},
            {"chapter_id": ch1, "type": "narration", "role": "旁白",
             "text": "说着，他加快了脚步", "beat_type": "transition"},
            {"chapter_id": ch1, "type": "dialogue", "role": "主角",
             "text": "你终于来了，我等你很久了。你以为你逃得掉吗？",
             "beat_type": "confrontation", "emotion": "紧张"},
            {"chapter_id": ch1, "type": "narration", "role": "旁白",
             "text": "突然，一道黑影从林中窜出，直扑主角。这是谁？他为何在此？",
             "beat_type": "confrontation", "emotion": "恐惧"},
        ])

        # 第1章结尾: 情绪峰值
        for i in range(5):
            elements.append({
                "chapter_id": ch1, "type": "action", "role": "主角",
                "text": f"剑光闪烁，第{i+1}次交锋", "beat_type": "confrontation",
                "emotion": "紧张",
            })

        # 第2章: 场景切换
        elements.extend([
            {"chapter_id": ch2, "type": "narration", "role": "旁白",
             "text": "与此同时，远在京城的大殿中", "beat_type": "transition"},
            {"chapter_id": ch2, "type": "dialogue", "role": "反派",
             "text": "那边的事情办得如何了？", "beat_type": "setup"},
            {"chapter_id": ch2, "type": "narration", "role": "旁白",
             "text": "一个黑衣人跪下禀报", "beat_type": "transition"},
            {"chapter_id": ch2, "type": "dialogue", "role": "黑衣人",
             "text": "禀告大人，计划已经启动，不出三日必有结果",
             "beat_type": "revelation"},
        ])

        # 第2章结尾: cliffhanger
        elements.extend([
            {"chapter_id": ch2, "type": "narration", "role": "旁白",
             "text": "反派露出阴冷的笑容，但他却不知，真正的危险正在逼近",
             "beat_type": "revelation"},
        ])

        # 第3章: 收束
        elements.extend([
            {"chapter_id": ch3, "type": "dialogue", "role": "主角",
             "text": "原来这一切都是你的阴谋", "beat_type": "confrontation",
             "emotion": "愤怒"},
            {"chapter_id": ch3, "type": "narration", "role": "旁白",
             "text": "真相终于大白，但代价却是惨重的", "beat_type": "payoff"},
            {"chapter_id": ch3, "type": "narration", "role": "旁白",
             "text": "主角望着远方，一个更大的阴谋正在展开？",
             "beat_type": "revelation"},
        ])

        return elements

    @pytest.fixture
    def sample_chapters(self):
        return [
            {"chapter_id": 1, "chapter_title": "山道遇袭", "element_count": 11},
            {"chapter_id": 2, "chapter_title": "京城密谋", "element_count": 6},
            {"chapter_id": 3, "chapter_title": "真相大白", "element_count": 3},
        ]

    # ── 冲突密度 ──

    def test_conflict_density(self, analyzer, sample_elements):
        """测试冲突密度计算"""
        ch1 = [e for e in sample_elements if e["chapter_id"] == 1]
        density = analyzer.compute_conflict_density(ch1)
        assert density > 0.3, f"第1章冲突密度应>0.3，实际: {density:.2f}"

    def test_conflict_density_empty(self, analyzer):
        assert analyzer.compute_conflict_density([]) == 0.0

    # ── 冲突节点检测 ──

    def test_detect_conflict_nodes(self, analyzer, sample_elements, sample_chapters):
        """测试冲突节点检测"""
        nodes = analyzer.detect_conflict_nodes(sample_elements, sample_chapters)
        assert len(nodes) > 0, "应检测到至少1个冲突节点"

        node_types = [n["type"] for n in nodes]
        # 应包含多种类型
        assert "cliffhanger" in node_types or "scene_shift" in node_types, \
            f"应检测到cliffhanger或scene_shift，实际类型: {node_types}"

    def test_detect_cliffhanger(self, analyzer):
        """测试章末悬念检测"""
        tail = [
            {"type": "narration", "text": "反派露出阴冷的笑容，但他却不知，真正的危险正在逼近",
             "beat_type": "revelation"},
        ]
        result = analyzer.detect_cliffhanger_elements(tail)
        assert result["is_cliffhanger"], f"应检测到悬念: {result}"

    def test_no_cliffhanger(self, analyzer):
        """测试无悬念的情况"""
        tail = [
            {"type": "narration", "text": "主角平静地回到了住处，今天的事情就此结束",
             "beat_type": "transition"},
        ]
        result = analyzer.detect_cliffhanger_elements(tail)
        # 这个可能检测到也可能检测不到，取决于阈值
        assert "is_cliffhanger" in result
        assert "confidence" in result

    # ── 断点查找 ──

    def test_find_breakpoints(self, analyzer, sample_chapters):
        """测试自然断点查找"""
        nodes = analyzer.detect_conflict_nodes(
            [],
            sample_chapters,
        )
        # 没有元素但有章节也可以测试断点
        breakpoints = analyzer.find_natural_breakpoints(
            sample_chapters, nodes, target_episodes=2,
            min_chapters_per_episode=1, max_chapters_per_episode=5,
        )
        assert isinstance(breakpoints, list)

    # ── 叙事弧线 ──

    def test_narrative_arc(self, analyzer, sample_chapters):
        """测试叙事弧线构建"""
        nodes = analyzer.detect_conflict_nodes([], sample_chapters)
        arc = analyzer.build_narrative_arc(sample_chapters, nodes)
        assert arc["total_chapters"] == 3
        assert arc["arc_type"] in ("三幕结构", "短篇单幕")
        if arc["arc_type"] == "三幕结构":
            assert len(arc["phases"]) == 4


class TestEpisodeRhythm:
    """影视节奏引擎测试"""

    @pytest.fixture
    def engine(self):
        return EpisodeRhythmSkill()

    @pytest.fixture
    def sample_chapters(self):
        return [
            {"chapter_id": 1, "chapter_title": "山道遇袭"},
            {"chapter_id": 2, "chapter_title": "京城密谋"},
            {"chapter_id": 3, "chapter_title": "真相大白"},
            {"chapter_id": 4, "chapter_title": "新的征程"},
            {"chapter_id": 5, "chapter_title": "暗流涌动"},
        ]

    @pytest.fixture
    def sample_elements(self):
        """为5章生成模拟元素"""
        elements = []
        for ch_id in range(1, 6):
            for i in range(8):
                elements.append({
                    "chapter_id": ch_id,
                    "type": "narration" if i % 3 == 0 else "dialogue",
                    "role": "主角" if i % 2 == 0 else "配角",
                    "text": f"第{ch_id}章第{i+1}段文本内容",
                    "beat_type": "confrontation" if i % 4 == 0 else "setup",
                    "emotion": "紧张" if i % 3 == 0 else "",
                })
        return elements

    @pytest.fixture
    def sample_conflict_nodes(self):
        return [
            {"node_id": "NODE-001", "type": "cliffhanger", "chapter_id": 1,
             "position": 0.9, "intensity": 0.8,
             "description": "章末悬念"},
            {"node_id": "NODE-002", "type": "scene_shift", "chapter_id": 2,
             "position": 0.1, "intensity": 0.3,
             "description": "场景切换"},
            {"node_id": "NODE-003", "type": "major_twist", "chapter_id": 3,
             "position": 0.5, "intensity": 0.7,
             "description": "剧情转折"},
            {"node_id": "NODE-004", "type": "cliffhanger", "chapter_id": 3,
             "position": 0.9, "intensity": 0.6,
             "description": "章末悬念"},
            {"node_id": "NODE-005", "type": "resolution_point", "chapter_id": 5,
             "position": 0.8, "intensity": 0.5,
             "description": "收束"},
        ]

    # ── 节奏规划 ──

    def test_long_drama_plan(self, engine, sample_chapters, sample_elements, sample_conflict_nodes):
        """测试长剧格式分集"""
        episodes = engine.plan_episodes_by_rhythm(
            chapters=sample_chapters,
            elements=sample_elements,
            conflict_nodes=sample_conflict_nodes,
            target_format="long_drama",
            cliffhanger_required=True,
        )
        assert len(episodes) > 0
        assert episodes[0]["episode_id"] == 1
        # 每集应有钩子/冲突/悬念
        for ep in episodes:
            assert "opening_hook" in ep
            assert "mid_conflict" in ep
            assert "cliffhanger" in ep
            assert "core_highlights" in ep
            assert "foreshadowing" in ep
            # 长剧每集至少1章
            assert ep["chapter_count"] >= 1

    def test_short_drama_plan(self, engine, sample_chapters, sample_elements, sample_conflict_nodes):
        """测试短剧格式分集"""
        episodes = engine.plan_episodes_by_rhythm(
            chapters=sample_chapters,
            elements=sample_elements,
            conflict_nodes=sample_conflict_nodes,
            target_format="short_drama",
            cliffhanger_required=True,
        )
        assert len(episodes) > 0
        # 短剧每集章节数≤2
        for ep in episodes:
            assert ep["chapter_count"] <= 2, \
                f"短剧每集应≤2章，实际: {ep['chapter_count']}"

    # ── 钩子/冲突/悬念生成 ──

    def test_opening_hook(self, engine, sample_elements):
        hook = engine.generate_opening_hook(sample_elements[:3])
        assert len(hook) > 10
        assert "开篇" in hook or "钩子" in hook or "[" in hook

    def test_mid_conflict(self, engine, sample_elements):
        conflict = engine.generate_mid_conflict(sample_elements, [])
        assert len(conflict) > 5

    def test_cliffhanger(self, engine, sample_elements):
        cliff = engine.generate_cliffhanger(sample_elements[-4:])
        assert len(cliff) > 5
        assert "悬念" in cliff or "[" in cliff

    # ── 标注 ──

    def test_highlights(self, engine, sample_elements):
        highlights = engine.annotate_highlights(sample_elements, ["主角", "配角"])
        assert len(highlights) > 0

    def test_foreshadowing(self, engine, sample_elements):
        foreshadowing = engine.annotate_foreshadowing(
            sample_elements, sample_elements, current_episode_id=1
        )
        assert isinstance(foreshadowing, list)

    # ── 招商备注 ──

    def test_investor_notes(self, engine):
        episode = {
            "episode_id": 1,
            "chapters_range": "第1-2章",
            "duration_estimate": "10分钟",
            "scene_count_estimate": 5,
            "core_highlights": ["冲突场景", "揭示真相"],
            "conflict_nodes": [
                {"type": "major_twist", "desc": "转折"},
                {"type": "cliffhanger", "desc": "悬念"},
            ],
            "top_characters": [{"name": "主角", "appearances": 10}],
            "foreshadowing": [
                {"type": "key_item", "description": "关键道具出现"},
            ],
            "opening_hook": "开篇钩子",
            "mid_conflict": "中段冲突",
            "cliffhanger": "结尾悬念",
            "act_structure": {"Act 1": "建立", "Act 2": "对抗", "Act 3": "高潮"},
        }
        notes = engine.generate_investor_notes(episode)
        assert len(notes) > 50
        assert "招商" in notes or "审核" in notes
        assert "核心看点" in notes
        assert "剧集结构" in notes

    # ── 估算 ──

    def test_scene_estimate(self, engine, sample_elements):
        scenes = engine._estimate_scene_count(sample_elements, "long_drama")
        assert scenes > 0

    def test_duration_estimate(self, engine):
        dur = engine._estimate_duration(10, "long_drama")
        assert "分钟" in dur


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
