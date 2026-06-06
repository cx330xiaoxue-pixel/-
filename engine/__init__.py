"""
Novel-to-Script Pro — 管线引擎模块

提供:
  - Pipeline: 6阶段管线调度器
  - AgentStateManager: Agent 状态管理与持久化
  - TaskQueue: 依赖感知的并行任务队列
"""

from .pipeline import Pipeline, create_pipeline
from .state_manager import AgentStateManager, create_state_manager
from .task_queue import (
    TaskQueue,
    Task,
    TaskStatus,
    TaskPriority,
    create_pipeline_tasks,
    PIPELINE_TASK_TEMPLATES,
)

__all__ = [
    "Pipeline",
    "create_pipeline",
    "AgentStateManager",
    "create_state_manager",
    "TaskQueue",
    "Task",
    "TaskStatus",
    "TaskPriority",
    "create_pipeline_tasks",
    "PIPELINE_TASK_TEMPLATES",
]
