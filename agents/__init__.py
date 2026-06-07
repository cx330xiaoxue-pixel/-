"""
Novel-to-Script Pro — Agent 层 (13个Agent)

Phase 0 (ingest):     KnowledgeCurator
Phase 1 (analyze):    NovelAnalyzer, InsightArchitect
Phase 2 (plan):       EpisodeArchitect, EmotionArchitect
Phase 3 (write):      ScriptWriter, VisualStoryteller
Phase 4 (review):     ReviewDirector, ScriptComparator, ContinuityRecorder
Phase 5 (storyboard): StoryboardDirector, StoryboardArtist, ArtDesigner, ImageGeneratorAgent
"""

from .base_agent import BaseAgent
from .knowledge_curator import KnowledgeCurator, create_knowledge_curator
from .novel_analyzer import NovelAnalyzer, create_novel_analyzer
from .insight_architect import InsightArchitect, create_insight_architect
from .episode_architect import EpisodeArchitect, create_episode_architect
from .emotion_architect import EmotionArchitect, create_emotion_architect
from .script_writer import ScriptWriter, create_script_writer
from .visual_storyteller import VisualStoryteller, create_visual_storyteller
from .review_director import ReviewDirector, create_review_director
from .script_comparator import ScriptComparator, create_script_comparator
from .continuity_recorder import ContinuityRecorder, create_continuity_recorder
from .storyboard_director import StoryboardDirector, create_storyboard_director
from .storyboard_artist import StoryboardArtist, create_storyboard_artist
from .art_designer import ArtDesigner, create_art_designer
from .image_generator import ImageGeneratorAgent, create_image_generator
# v2.1 新增: 内容分级 & 智能分集
from .content_grader import ContentGrader, create_content_grader
from .episode_director import EpisodeDirector, create_episode_director

__all__ = [
    "BaseAgent",
    "KnowledgeCurator", "create_knowledge_curator",
    "NovelAnalyzer", "create_novel_analyzer",
    "InsightArchitect", "create_insight_architect",
    "EpisodeArchitect", "create_episode_architect",
    "EmotionArchitect", "create_emotion_architect",
    "ScriptWriter", "create_script_writer",
    "VisualStoryteller", "create_visual_storyteller",
    "ReviewDirector", "create_review_director",
    "ScriptComparator", "create_script_comparator",
    "ContinuityRecorder", "create_continuity_recorder",
    "StoryboardDirector", "create_storyboard_director",
    "StoryboardArtist", "create_storyboard_artist",
    "ArtDesigner", "create_art_designer",
    "ImageGeneratorAgent", "create_image_generator",
    # v2.1
    "ContentGrader", "create_content_grader",
    "EpisodeDirector", "create_episode_director",
]
