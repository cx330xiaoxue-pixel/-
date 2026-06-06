"""
任务队列 — 管线任务调度与并行执行

功能:
  - 支持并发任务执行（ThreadPoolExecutor）
  - 任务依赖管理（阻塞/非阻塞）
  - 任务优先级排序
  - 进度追踪与失败重试
  - 与 AgentStateManager 集成记录执行日志
"""

import sys
import threading
import time
import traceback
from collections import defaultdict

# Windows 终端默认 GBK 不支持 emoji，强制 UTF-8 输出
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    HIGH = 0
    NORMAL = 1
    LOW = 2


@dataclass
class Task:
    """单个任务的定义"""

    name: str                          # 任务名称（唯一标识）
    func: Callable                     # 要执行的函数
    args: tuple = ()                   # 位置参数
    kwargs: dict = field(default_factory=dict)  # 关键字参数
    priority: TaskPriority = TaskPriority.NORMAL
    description: str = ""              # 任务描述
    phase: str = ""                    # 所属管线阶段
    episode: int = None                # 关联集数
    agent_name: str = ""               # 关联 Agent 名称
    timeout: float = 600.0             # 超时时间（秒）
    max_retries: int = 0               # 失败后最大重试次数
    retry_delay: float = 2.0           # 重试间隔（秒）
    depends_on: list = field(default_factory=list)  # 依赖的任务名称列表

    # 运行时状态（由 TaskQueue 管理）
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    retry_count: int = 0
    future: Optional[Future] = None

    @property
    def duration(self) -> float:
        """执行耗时"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return 0.0

    @property
    def is_done(self) -> bool:
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.SKIPPED,
            TaskStatus.CANCELLED,
        )


class TaskQueue:
    """
    任务队列调度器。

    支持:
      - 并发执行（可配置最大并发数）
      - 依赖管理（depends_on 列表中的任务完成后才执行）
      - 优先级排序（HIGH > NORMAL > LOW）
      - 失败重试
      - 进度回调
    """

    def __init__(
        self,
        max_workers: int = 4,
        state_manager=None,
        progress_callback: Callable = None,
    ):
        """
        初始化任务队列。

        Args:
            max_workers: 最大并行线程数
            state_manager: AgentStateManager 实例（用于记录日志）
            progress_callback: 进度回调 (task_name, status) -> None
        """
        self.max_workers = max_workers
        self.state_manager = state_manager
        self.progress_callback = progress_callback

        self.tasks: dict[str, Task] = {}      # 所有任务
        self._lock = threading.Lock()
        self._executor: Optional[ThreadPoolExecutor] = None

    # ═══════════════════════════════════════════════════════════
    # 任务管理
    # ═══════════════════════════════════════════════════════════

    def add_task(
        self,
        name: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        description: str = "",
        phase: str = "",
        episode: int = None,
        agent_name: str = "",
        timeout: float = 600.0,
        max_retries: int = 0,
        retry_delay: float = 2.0,
        depends_on: list = None,
    ) -> Task:
        """
        向队列添加一个任务。

        Args:
            name: 任务名称（唯一）
            func: 执行函数
            args: 位置参数
            kwargs: 关键字参数
            priority: 优先级
            description: 描述
            phase: 管线阶段
            episode: 集数
            agent_name: Agent 名称
            timeout: 超时（秒）
            max_retries: 最大重试次数
            retry_delay: 重试间隔
            depends_on: 依赖任务名列表

        Returns:
            Task 对象

        Raises:
            ValueError: 任务名重复
        """
        if name in self.tasks:
            raise ValueError(f"任务名重复: {name}")

        task = Task(
            name=name,
            func=func,
            args=args,
            kwargs=kwargs or {},
            priority=priority,
            description=description,
            phase=phase,
            episode=episode,
            agent_name=agent_name,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
            depends_on=depends_on or [],
        )
        self.tasks[name] = task
        return task

    def add_tasks_batch(self, task_specs: list[dict]) -> list[Task]:
        """
        批量添加任务。

        Args:
            task_specs: 任务规格列表，每项为 add_task 的参数字典

        Returns:
            Task 对象列表
        """
        tasks = []
        for spec in task_specs:
            task = self.add_task(**spec)
            tasks.append(task)
        return tasks

    def get_task(self, name: str) -> Optional[Task]:
        """获取任务对象"""
        return self.tasks.get(name)

    def cancel_task(self, name: str):
        """取消一个待执行的任务"""
        task = self.tasks.get(name)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            self._notify_progress(name, TaskStatus.CANCELLED)

    # ═══════════════════════════════════════════════════════════
    # 执行引擎
    # ═══════════════════════════════════════════════════════════

    def run_all(self) -> dict[str, Any]:
        """
        执行所有任务（按优先级和依赖关系）。

        Returns:
            {task_name: result} 字典
        """
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)

        try:
            results = self._execute_with_dependencies()
            return results
        finally:
            self._executor.shutdown(wait=False)
            self._executor = None

    def run_phase(self, phase: str) -> dict[str, Any]:
        """
        只执行指定阶段的任务。

        Args:
            phase: 阶段名称

        Returns:
            {task_name: result}
        """
        phase_tasks = {
            name: task
            for name, task in self.tasks.items()
            if task.phase == phase
        }
        if not phase_tasks:
            print(f"⚠️  阶段 '{phase}' 没有待执行的任务")
            return {}

        # 临时替换任务表
        original_tasks = self.tasks
        self.tasks = phase_tasks
        try:
            return self.run_all()
        finally:
            self.tasks = original_tasks

    def run_episode(self, episode: int) -> dict[str, Any]:
        """
        只执行指定集数的任务。

        Args:
            episode: 集数

        Returns:
            {task_name: result}
        """
        ep_tasks = {
            name: task
            for name, task in self.tasks.items()
            if task.episode == episode
        }
        if not ep_tasks:
            print(f"⚠️  第{episode}集没有待执行的任务")
            return {}

        original_tasks = self.tasks
        self.tasks = ep_tasks
        try:
            return self.run_all()
        finally:
            self.tasks = original_tasks

    # ═══════════════════════════════════════════════════════════
    # 内部：依赖感知执行
    # ═══════════════════════════════════════════════════════════

    def _execute_with_dependencies(self) -> dict[str, Any]:
        """按依赖关系分层执行所有任务"""
        results = {}

        # 按优先级排序
        pending = sorted(
            [t for t in self.tasks.values() if t.status == TaskStatus.PENDING],
            key=lambda t: (t.priority.value, t.name),
        )

        # 构建依赖图
        completed_names: set = set()
        failed_names: set = set()

        while pending:
            # 找出所有依赖已满足的任务
            ready = []
            still_waiting = []
            for task in pending:
                deps = set(task.depends_on)
                if deps.issubset(completed_names):
                    ready.append(task)
                elif deps & failed_names:
                    # 依赖失败 → 跳过此任务
                    task.status = TaskStatus.SKIPPED
                    task.error = f"依赖任务失败: {deps & failed_names}"
                    results[task.name] = None
                    self._notify_progress(task.name, TaskStatus.SKIPPED)
                else:
                    still_waiting.append(task)

            if not ready and still_waiting:
                # 有循环依赖或依赖不存在
                stuck_names = [t.name for t in still_waiting]
                missing_deps = set()
                for t in still_waiting:
                    missing_deps.update(
                        d for d in t.depends_on if d not in self.tasks
                    )
                error_msg = (
                    f"任务卡住: {stuck_names}，"
                    f"缺失依赖: {missing_deps}"
                )
                print(f"❌ {error_msg}")
                for t in still_waiting:
                    t.status = TaskStatus.FAILED
                    t.error = error_msg
                break

            # 并行执行当前层
            if ready:
                futures_map: dict[Future, Task] = {}
                for task in ready:
                    future = self._executor.submit(self._run_single_task, task)
                    futures_map[future] = task
                    task.status = TaskStatus.RUNNING
                    task.started_at = time.time()

                for future in as_completed(futures_map):
                    task = futures_map[future]
                    try:
                        result = future.result(timeout=task.timeout)
                        task.result = result
                        task.status = TaskStatus.COMPLETED
                        completed_names.add(task.name)
                    except Exception as e:
                        task.error = str(e)[:500]
                        # 重试
                        if task.retry_count < task.max_retries:
                            task.retry_count += 1
                            task.status = TaskStatus.PENDING
                            print(f"🔄 任务 '{task.name}' 失败，重试 {task.retry_count}/{task.max_retries}: {e}")
                            time.sleep(task.retry_delay)
                            # 重新提交
                            future = self._executor.submit(self._run_single_task, task)
                            futures_map[future] = task
                            task.status = TaskStatus.RUNNING
                            continue
                        else:
                            task.status = TaskStatus.FAILED
                            failed_names.add(task.name)
                            results[task.name] = None

                    task.completed_at = time.time()
                    results[task.name] = task.result

                    # 记录到 state_manager
                    self._log_to_state_manager(task)

                    # 进度回调
                    self._notify_progress(task.name, task.status)

                # 更新 pending 列表
                pending = [
                    t for t in still_waiting
                    if t.status == TaskStatus.PENDING
                ]

        return results

    def _run_single_task(self, task: Task) -> Any:
        """在独立线程中执行单个任务"""
        return task.func(*task.args, **task.kwargs)

    # ═══════════════════════════════════════════════════════════
    # 同步执行（单任务，阻塞）
    # ═══════════════════════════════════════════════════════════

    def run_sync(self, task_name: str) -> Any:
        """
        同步执行单个任务（阻塞，不考虑依赖）。

        Args:
            task_name: 任务名称

        Returns:
            任务返回值
        """
        task = self.tasks.get(task_name)
        if not task:
            raise ValueError(f"任务不存在: {task_name}")

        task.status = TaskStatus.RUNNING
        task.started_at = time.time()

        try:
            result = task.func(*task.args, **task.kwargs)
            task.result = result
            task.status = TaskStatus.COMPLETED
            return result
        except Exception as e:
            task.error = str(e)[:500]
            task.status = TaskStatus.FAILED
            raise
        finally:
            task.completed_at = time.time()
            self._log_to_state_manager(task)
            self._notify_progress(task.name, task.status)

    # ═══════════════════════════════════════════════════════════
    # 查询与统计
    # ═══════════════════════════════════════════════════════════

    def get_status_summary(self) -> dict:
        """获取所有任务的状态汇总"""
        counts = defaultdict(int)
        for task in self.tasks.values():
            counts[task.status.value] += 1

        return {
            "total": len(self.tasks),
            "by_status": dict(counts),
            "completed": counts["completed"],
            "failed": counts["failed"],
            "pending": counts["pending"],
            "running": counts["running"],
            "skipped": counts["skipped"],
        }

    def get_failed_tasks(self) -> list[Task]:
        """获取所有失败的任务"""
        return [t for t in self.tasks.values() if t.status == TaskStatus.FAILED]

    def get_phase_summary(self) -> dict:
        """按阶段汇总任务状态"""
        by_phase = defaultdict(lambda: defaultdict(int))
        for task in self.tasks.values():
            phase = task.phase or "unknown"
            by_phase[phase][task.status.value] += 1
        return dict(by_phase)

    def print_summary(self):
        """打印任务执行摘要"""
        summary = self.get_status_summary()
        print(f"\n{'='*50}")
        print(f"📋 任务队列摘要")
        print(f"{'='*50}")
        print(f"  总任务数: {summary['total']}")
        print(f"  已完成:   {summary['completed']}")
        print(f"  失败:     {summary['failed']}")
        print(f"  待执行:   {summary['pending']}")
        print(f"  已跳过:   {summary['skipped']}")

        failed = self.get_failed_tasks()
        if failed:
            print(f"\n❌ 失败任务 ({len(failed)}):")
            for task in failed:
                print(f"  - {task.name}: {task.error[:120]}")

        print(f"{'='*50}\n")

    # ═══════════════════════════════════════════════════════════
    # 内部辅助
    # ═══════════════════════════════════════════════════════════

    def _notify_progress(self, task_name: str, status: TaskStatus):
        """调用进度回调"""
        if self.progress_callback:
            try:
                self.progress_callback(task_name, status)
            except Exception:
                pass  # 回调失败不影响任务执行

    def _log_to_state_manager(self, task: Task):
        """将任务执行结果记录到 AgentStateManager"""
        if self.state_manager and task.agent_name:
            try:
                self.state_manager.log_agent_execution(
                    agent_name=task.agent_name,
                    phase=task.phase,
                    episode=task.episode,
                    input_summary=task.description,
                    output_summary=(
                        str(task.result)[:500] if task.result else ""
                    ),
                    duration_seconds=task.duration,
                    status=(
                        "success" if task.status == TaskStatus.COMPLETED
                        else "failed" if task.status == TaskStatus.FAILED
                        else "skipped"
                    ),
                    error_message=task.error,
                )
            except Exception:
                pass  # 日志记录失败不影响任务

    def clear(self):
        """清空所有任务"""
        self.tasks.clear()


# ═══════════════════════════════════════════════════════════════
# 预定义管线任务模板
# ═══════════════════════════════════════════════════════════════

PIPELINE_TASK_TEMPLATES = {
    "ingest": [
        {
            "name": "scan_sources",
            "description": "扫描 sources/ 目录中的原始材料",
            "agent_name": "knowledge-curator",
            "max_retries": 1,
        },
        {
            "name": "extract_terms",
            "description": "提取关键术语与世界观设定",
            "agent_name": "knowledge-curator",
            "depends_on": ["scan_sources"],
        },
        {
            "name": "build_registry",
            "description": "更新知识注册表",
            "agent_name": "knowledge-curator",
            "depends_on": ["extract_terms"],
        },
    ],
    "analyze": [
        {
            "name": "extract_structure",
            "description": "抽取小说结构信息",
            "agent_name": "novel-analyzer",
            "max_retries": 2,
        },
        {
            "name": "analyze_characters",
            "description": "分析人物网络与关系",
            "agent_name": "novel-analyzer",
            "depends_on": ["extract_structure"],
        },
        {
            "name": "insight_analysis",
            "description": "深度主题洞察分析",
            "agent_name": "insight-architect",
            "depends_on": ["analyze_characters"],
        },
    ],
    "plan": [
        {
            "name": "episode_mapping",
            "description": "章节→集映射规划",
            "agent_name": "episode-architect",
            "max_retries": 2,
        },
        {
            "name": "emotion_curve_design",
            "description": "全剧情绪曲线设计",
            "agent_name": "emotion-architect",
            "depends_on": ["episode_mapping"],
        },
    ],
}


def create_pipeline_tasks(
    phase: str, task_queue: TaskQueue, custom_funcs: dict[str, Callable] = None
) -> list[Task]:
    """
    根据模板创建管线阶段的标准任务。

    Args:
        phase: 阶段名称
        task_queue: TaskQueue 实例
        custom_funcs: {task_name: callable} 自定义执行函数映射

    Returns:
        创建的 Task 列表
    """
    templates = PIPELINE_TASK_TEMPLATES.get(phase, [])
    if not templates:
        print(f"⚠️  阶段 '{phase}' 没有预定义任务模板")
        return []

    funcs = custom_funcs or {}
    tasks = []

    for tmpl in templates:
        name = tmpl["name"]
        if name not in funcs:
            print(f"⚠️  任务 '{name}' 缺少执行函数，将作为占位符")
            funcs[name] = lambda: None

        task = task_queue.add_task(
            name=name,
            func=funcs[name],
            description=tmpl.get("description", ""),
            phase=phase,
            agent_name=tmpl.get("agent_name", ""),
            max_retries=tmpl.get("max_retries", 0),
            depends_on=tmpl.get("depends_on", []),
        )
        tasks.append(task)

    return tasks
