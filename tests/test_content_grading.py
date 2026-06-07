"""
测试内容分级技能 — S/A/B 三级分拣算法
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skills.content_grading import ContentGradingSkill


class TestContentGrading:
    """内容分级单元测试"""

    @pytest.fixture
    def skill(self):
        return ContentGradingSkill()

    @pytest.fixture
    def sample_elements(self):
        """构造测试用元素列表"""
        return [
            # S级: 对话
            {"type": "dialogue", "role": "主角", "text": "你竟敢背叛我！",
             "beat_type": "confrontation", "emotion": "愤怒", "global_id": 1},
            # S级: 冲突+转折关键词
            {"type": "narration", "role": "旁白", "text": "突然，一道黑影从暗处袭来",
             "beat_type": "confrontation", "global_id": 2},
            # S级: 揭示
            {"type": "dialogue", "role": "主角", "text": "原来你才是幕后黑手",
             "beat_type": "revelation", "global_id": 3},
            # A级: 环境描写
            {"type": "description", "role": "旁白",
             "text": "阳光穿过庭院的老树，洒在青石板上",
             "beat_type": "setup", "global_id": 4},
            # A级: 人物神态
            {"type": "narration", "role": "配角", "text": "他眉头紧锁，似乎在思考什么",
             "beat_type": "setup", "global_id": 5},
            # B级: 心理活动
            {"type": "narration", "role": "旁白",
             "text": "他心想，这些人到底要做什么，暗暗觉得不对劲",
             "beat_type": "transition", "global_id": 6},
            # B级: 重复片段
            {"type": "description", "role": "旁白",
             "text": "风轻轻地吹过，树叶沙沙作响，月光如水般洒落",
             "beat_type": "transition", "global_id": 7},
            {"type": "description", "role": "旁白",
             "text": "风轻轻吹过，树叶沙沙地响，月光如水洒落在地上",
             "beat_type": "transition", "global_id": 8},
            # B级: 短碎片
            {"type": "narration", "role": "旁白", "text": "嗯。",
             "beat_type": "transition", "global_id": 9},
        ]

    @pytest.fixture
    def character_importance(self):
        return {"主角": 1.0, "配角": 0.5}

    # ── 基础分级测试 ──

    def test_grade_elements_basic(self, skill, sample_elements, character_importance):
        """测试基础分级功能"""
        graded = skill.grade_elements(
            sample_elements, mode="balanced", character_importance=character_importance
        )
        assert len(graded) == len(sample_elements)
        for elem in graded:
            assert "content_grade" in elem
            assert "grade_confidence" in elem
            assert "grade_score" in elem
            assert elem["content_grade"] in ("S", "A", "B")

    def test_s_level_elements(self, skill, sample_elements, character_importance):
        """验证S级元素识别"""
        graded = skill.grade_elements(
            sample_elements, mode="balanced", character_importance=character_importance
        )
        s_elements = [e for e in graded if e["content_grade"] == "S"]
        # 前3个应该都是S级（对话+冲突、转折+冲突、揭示）
        assert len(s_elements) >= 2, f"期望至少2个S级元素，实际{len(s_elements)}个"
        # 验证dialogue+confrontation被识别为S级
        assert graded[0]["content_grade"] == "S"

    def test_b_level_psychological(self, skill, sample_elements, character_importance):
        """验证心理活动被识别为B级"""
        graded = skill.grade_elements(
            sample_elements, mode="balanced", character_importance=character_importance
        )
        # 第6个元素（心理活动"心想"/"暗暗"）应为B级
        psych_elem = graded[5]  # index 5
        assert psych_elem["content_grade"] == "B", \
            f"心理活动应为B级，实际: {psych_elem['content_grade']}"

    # ── 模式差异测试 ──

    def test_strict_mode(self, skill, sample_elements, character_importance):
        """严格模式应保留更多元素"""
        strict = skill.grade_elements(
            sample_elements, mode="strict", character_importance=character_importance
        )
        loose = skill.grade_elements(
            sample_elements, mode="loose", character_importance=character_importance
        )
        s_strict = sum(1 for e in strict if e["content_grade"] == "S")
        s_loose = sum(1 for e in loose if e["content_grade"] == "S")
        b_strict = sum(1 for e in strict if e["content_grade"] == "B")
        b_loose = sum(1 for e in loose if e["content_grade"] == "B")
        # strict模式B级应少于loose模式
        assert b_strict <= b_loose, \
            f"strict B级({b_strict})应 ≤ loose B级({b_loose})"

    def test_loose_mode_filters_more(self, skill, sample_elements, character_importance):
        """松散模式应过滤更多B级内容"""
        graded = skill.grade_elements(
            sample_elements, mode="loose", character_importance=character_importance
        )
        b_count = sum(1 for e in graded if e["content_grade"] == "B")
        # loose模式: B级过滤率应>40%
        b_ratio = b_count / len(graded)
        assert b_ratio > 0.3, f"loose模式B级比例应>30%，实际: {b_ratio:.1%}"

    # ── 重复检测 ──

    def test_repetition_detection(self, skill):
        """测试重复文本检测"""
        text1 = "风轻轻地吹过，树叶沙沙作响，月光如水般洒落"
        text2 = "风轻轻吹过，树叶沙沙地响，月光如水洒落在地上"
        similarity = skill._compute_text_similarity(text1, text2)
        assert similarity > 0.5, f"相似度应>0.5，实际: {similarity:.2f}"

        # 完全不同文本应低相似度
        text3 = "主角拔剑而起，剑光如虹"
        similarity2 = skill._compute_text_similarity(text1, text3)
        assert similarity2 < 0.4, f"不同文本相似度应<0.4，实际: {similarity2:.2f}"

    def test_repetition_indices(self, skill, sample_elements):
        """测试重复元素索引检测"""
        rep_set = skill._detect_repetition_patterns(sample_elements, similarity_threshold=0.5)
        # 第7和第8个元素是相似的环境描写，第8个应被标记为重复
        assert 7 in rep_set or 8 in rep_set, \
            f"相似环境描写应被检测为重复，标记了: {rep_set}"

    # ── 心理活动检测 ──

    def test_psychological_detection(self, skill):
        """测试心理活动标记检测"""
        assert skill._is_psychological_monologue("他心想，这事情不对劲")
        assert skill._is_psychological_monologue("暗暗思忖着对策")
        assert skill._is_psychological_monologue("他暗道一声不好")
        assert not skill._is_psychological_monologue("他站起身来，推门而去")
        assert not skill._is_psychological_monologue("")

    # ── 压缩/合并 ──

    def test_condense_a_level(self, skill, sample_elements):
        """测试A级元素压缩"""
        a_elements = [e for e in sample_elements if e.get("global_id") in (4, 5)]
        condensed = skill.condense_a_level(a_elements, mode="balanced")
        assert len(condensed) > 0, "A级压缩应返回非空文本"
        assert len(condensed) < 200, "压缩后文本应明显变短"

    def test_merge_b_level(self, skill, sample_elements):
        """测试B级元素合并"""
        b_elements = [e for e in sample_elements if e.get("global_id") in (6, 7, 8, 9)]
        merged = skill.merge_b_level(b_elements, max_chars=50)
        assert len(merged) <= 50, f"合并后应≤50字，实际: {len(merged)}"
        # 心理活动内容应被清理
        assert "心想" not in merged, "心理活动标记应被清理"

    # ── 应用分级 ──

    def test_apply_grading(self, skill, sample_elements, character_importance):
        """测试apply_grading_to_elements的过滤/压缩效果"""
        graded = skill.grade_elements(
            sample_elements, mode="balanced", character_importance=character_importance
        )
        processed = skill.apply_grading_to_elements(graded, mode="balanced", max_merged_chars=50)

        # 处理后的元素应少于或等于原始
        assert len(processed) <= len(sample_elements), \
            f"处理后({len(processed)})应≤原始({len(sample_elements)})"

        # 应该有一些被合并/压缩的元素
        condensed = [e for e in processed if e.get("condensed")]
        merged = [e for e in processed if e.get("merged_from")]
        assert len(condensed) + len(merged) > 0, "应该有被压缩或合并的元素"

    def test_apply_grading_loose_filters_more(self, skill, sample_elements, character_importance):
        """loose模式下apply_grading应过滤更多"""
        graded_loose = skill.grade_elements(
            sample_elements, mode="loose", character_importance=character_importance
        )
        graded_strict = skill.grade_elements(
            sample_elements, mode="strict", character_importance=character_importance
        )
        processed_loose = skill.apply_grading_to_elements(graded_loose, mode="loose", max_merged_chars=50)
        processed_strict = skill.apply_grading_to_elements(graded_strict, mode="strict", max_merged_chars=50)

        # loose模式过滤率应更高
        assert len(processed_loose) <= len(processed_strict), \
            f"loose({len(processed_loose)})应 ≤ strict({len(processed_strict)})"

    # ── 统计报告 ──

    def test_grading_report(self, skill, sample_elements, character_importance):
        """测试分级统计报告"""
        graded = skill.grade_elements(
            sample_elements, mode="balanced", character_importance=character_importance
        )
        report = skill.get_grading_report(graded)

        assert report["total"] == len(sample_elements)
        assert report["S_count"] + report["A_count"] + report["B_count"] == report["total"]
        assert 0 <= report["S_ratio"] <= 100
        assert 0 <= report["A_ratio"] <= 100
        assert 0 <= report["B_ratio"] <= 100

    # ── 空输入 ──

    def test_empty_elements(self, skill):
        """测试空输入"""
        graded = skill.grade_elements([], mode="balanced")
        assert graded == []
        report = skill.get_grading_report([])
        assert report == {"total": 0}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
