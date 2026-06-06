"""
Novel-to-Script Pro — Skill 层 (7个Skill模块)

提供:
  - KnowledgeCurationSkill: 术语提取、世界观规则、知识注册表
  - AdaptationAnalysisSkill: 叙事结构、人物网络、改编潜力评估
  - EpisodePlanningSkill: 章节映射、情绪曲线、悬念钩子
  - ScriptWritingSkill: 爆款参考检索、风格分析、Show Don't Tell
  - ReviewSkills (4合1): 业务审核、合规检查、对比审核、连续性记录
  - StoryboardSkills (2合1): 标准分镜(Film) + Seedance AI分镜
  - ImageSkills (2合1): 图片生成 + 图片反推
"""

from .knowledge_curation import KnowledgeCurationSkill, quick_scan
from .adaptation_analysis import AdaptationAnalysisSkill
from .episode_planning import EpisodePlanningSkill
from .script_writing import ScriptWritingSkill
from .review_skills import (
    ScriptReviewSkill,
    ComplianceReviewSkill,
    ComparativeReviewSkill,
    ContinuityRecordSkill,
)
from .storyboard_skills import FilmStoryboardSkill, SeedanceStoryboardSkill
from .image_skills import ImageGenerationSkill, ImageToPromptSkill

__all__ = [
    "KnowledgeCurationSkill", "quick_scan",
    "AdaptationAnalysisSkill",
    "EpisodePlanningSkill",
    "ScriptWritingSkill",
    "ScriptReviewSkill", "ComplianceReviewSkill",
    "ComparativeReviewSkill", "ContinuityRecordSkill",
    "FilmStoryboardSkill", "SeedanceStoryboardSkill",
    "ImageGenerationSkill", "ImageToPromptSkill",
]
