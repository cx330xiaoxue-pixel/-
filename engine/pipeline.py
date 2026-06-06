"""
管线调度器 — Novel-to-Script Pro 核心编排引擎

功能:
  - 6阶段管线调度: ingest → analyze → plan → write → review → storyboard → final_check
  - 阶段间状态传递
  - 支持单阶段执行和全自动流程
  - 审核闭环: 生成→审核→回改→复审
  - 与 AgentStateManager 集成，支持中断续跑

命令:
  python main.py ingest --source ./my_novel/
  python main.py analyze --title "剑影江湖"
  python main.py plan --episodes 40
  python main.py write --episode 1

imports below
"""
import sys
# Windows 终端默认 GBK 不支持 emoji，强制 UTF-8 输出
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import os
import time
from datetime import datetime
from typing import Any, Callable, Optional

from .state_manager import AgentStateManager, create_state_manager
from .task_queue import TaskQueue, Task, TaskStatus, TaskPriority


class Pipeline:
    """
    Novel-to-Script Pro 管线调度器。

    编排 6 个阶段的执行顺序和状态传递。
    每个阶段委托给对应的 Agent 执行，
    阶段间通过文件系统和 AgentStateManager 传递产物。
    """

    # 阶段定义
    PHASES = [
        "ingest",
        "analyze",
        "plan",
        "write",
        "review",
        "storyboard",
        "final_check",
    ]

    PHASE_DESCRIPTIONS = {
        "ingest": "知识收编 — 扫描源材料，提取术语与世界观",
        "analyze": "改编分析 — 分析叙事结构、人物网络、主题洞察",
        "plan": "分集规划 — 章节→集映射，情绪曲线设计",
        "write": "剧本生成 — 逐集生成完整剧本",
        "review": "多维度审核 — 业务审核、合规审核、对比审核",
        "storyboard": "分镜可视化 — 标准分镜 / Seedance AI 分镜",
        "final_check": "完成检查 — 乱码扫描、一致性验证、完整性检查",
    }

    def __init__(
        self,
        project_name: str = "untitled",
        output_dir: str = "./output",
        config: dict = None,
        llm_extractor=None,
        rule_extractor=None,
        character_tracker=None,
        script_builder=None,
        schema_validator=None,
        agents: dict = None,
        state_manager: AgentStateManager = None,
    ):
        """
        初始化管线调度器。

        Args:
            project_name: 项目名称（剧本名）
            output_dir: 输出根目录
            config: 全局配置字典（config.yaml 内容）
            llm_extractor: LLMExtractor 实例
            rule_extractor: RuleExtractor 实例
            character_tracker: CharacterTracker 实例
            script_builder: ScriptBuilder 实例
            schema_validator: SchemaValidator 实例
            agents: Agent 实例字典 {agent_name: agent_instance}
            state_manager: AgentStateManager 实例（可选，自动创建）
        """
        self.project_name = project_name
        self.output_dir = output_dir
        self.config = config or {}

        # 核心组件
        self.llm_extractor = llm_extractor
        self.rule_extractor = rule_extractor
        self.character_tracker = character_tracker
        self.script_builder = script_builder
        self.schema_validator = schema_validator
        self.agents = agents or {}

        # 状态管理器
        self.state = state_manager or create_state_manager(
            project_name, output_dir
        )

        # 管线配置
        pipeline_cfg = self.config.get("pipeline", {})
        self.review_passes = pipeline_cfg.get("review_passes", 2)
        self.max_rewrite_rounds = pipeline_cfg.get("max_rewrite_rounds", 3)
        self.auto_continue = pipeline_cfg.get("auto_continue", False)
        self.default_storyboard_mode = pipeline_cfg.get("storyboard_mode", "film")

        # 任务队列
        self.task_queue = TaskQueue(
            max_workers=self.config.get("processing", {}).get("max_workers", 4),
            state_manager=self.state,
        )

        # 钩子（阶段前后回调）
        self.hooks: dict[str, list[Callable]] = {
            "before_phase": [],
            "after_phase": [],
            "on_error": [],
        }

    # ═══════════════════════════════════════════════════════════
    # 管线命令（公开 API）
    # ═══════════════════════════════════════════════════════════

    def ingest(self, source_dir: str, **kwargs) -> dict:
        """
        Phase 0: 知识收编 — 扫描源材料，提取术语与世界观。

        Args:
            source_dir: 原始材料目录路径

        Returns:
            阶段结果 {status, terms_count, registry_path, ...}
        """
        return self._run_phase("ingest", source_dir=source_dir, **kwargs)

    def analyze(self, title: str = "", author: str = "", **kwargs) -> dict:
        """
        Phase 1: 改编分析 — 分析叙事结构、人物网络、主题洞察。

        Args:
            title: 作品标题
            author: 原作者

        Returns:
            阶段结果 {status, analysis_report, insight_report, ...}
        """
        return self._run_phase("analyze", title=title, author=author, **kwargs)

    def plan(self, episodes: int = 40, **kwargs) -> dict:
        """
        Phase 2: 分集规划 — 章节→集映射，情绪曲线设计。

        Args:
            episodes: 目标集数

        Returns:
            阶段结果 {status, episode_plan, emotion_curve, ...}
        """
        return self._run_phase("plan", episodes=episodes, **kwargs)

    def write(self, episode: int, **kwargs) -> dict:
        """
        Phase 3: 剧本生成 — 生成单集完整剧本。

        Args:
            episode: 集数

        Returns:
            阶段结果 {status, script_yaml, script_path, ...}
        """
        return self._run_phase("write", episode=episode, **kwargs)

    def review(self, episode: int, **kwargs) -> dict:
        """
        Phase 4: 多维度审核 — 业务审核、合规审核、对比审核。

        Args:
            episode: 集数

        Returns:
            阶段结果 {status, review_report, passed, suggestions, ...}
        """
        return self._run_phase("review", episode=episode, **kwargs)

    def storyboard(self, episode: int, mode: str = None, **kwargs) -> dict:
        """
        Phase 5: 分镜可视化 — 标准分镜 / Seedance AI 分镜。

        Args:
            episode: 集数
            mode: 分镜模式 (film | seedance)

        Returns:
            阶段结果 {status, storyboard_path, frames, ...}
        """
        mode = mode or self.default_storyboard_mode
        return self._run_phase("storyboard", episode=episode, mode=mode, **kwargs)

    def final_check(self, **kwargs) -> dict:
        """
        Phase 6: 完成检查 — 乱码扫描、一致性验证、完整性检查。

        Returns:
            阶段结果 {status, report, issues, ...}
        """
        return self._run_phase("final_check", **kwargs)

    def auto(
        self,
        source_dir: str = None,
        title: str = "",
        author: str = "",
        episodes: int = 3,
        start_phase: str = None,
        stop_phase: str = None,
        **kwargs,
    ) -> dict:
        """
        一键全流程：从知识收编到完成检查。

        Args:
            source_dir: 原始材料目录
            title: 作品标题
            author: 原作者
            episodes: 目标集数
            start_phase: 起始阶段（默认从第一个未完成阶段开始）
            stop_phase: 终止阶段（默认执行到最后）

        Returns:
            完整流程报告
        """
        results = {}

        # 确定起始阶段
        if start_phase is None:
            start_phase = self.state.get_next_pending_phase() or "ingest"

        phase_order = self.PHASES[self.PHASES.index(start_phase):]
        if stop_phase:
            stop_idx = self.PHASES.index(stop_phase) + 1
            phase_order = phase_order[:stop_idx]

        print(f"\n{'='*60}")
        print(f"🚀 启动全自动管线: {self.project_name}")
        print(f"   阶段: {' → '.join(phase_order)}")
        print(f"   目标集数: {episodes}")
        print(f"{'='*60}\n")

        for phase in phase_order:
            try:
                if phase == "ingest":
                    if source_dir:
                        r = self.ingest(source_dir)
                    else:
                        print("⏭️  跳过 ingest（未提供 source_dir）")
                        continue

                elif phase == "analyze":
                    r = self.analyze(title=title, author=author)

                elif phase == "plan":
                    r = self.plan(episodes=episodes)

                elif phase == "write":
                    for ep in range(1, episodes + 1):
                        r = self.write(episode=ep)
                        # 审核闭环
                        if self.auto_continue:
                            review_r = self.review(episode=ep)
                            rewrite_rounds = 0
                            while not review_r.get("passed") and rewrite_rounds < self.max_rewrite_rounds:
                                print(f"🔄 第{ep}集审核未通过，回改第{rewrite_rounds + 1}轮...")
                                r = self.write(episode=ep, revision_round=rewrite_rounds + 1)
                                review_r = self.review(episode=ep)
                                rewrite_rounds += 1
                        results[f"write_ep{ep}"] = r

                elif phase == "review":
                    for ep in range(1, episodes + 1):
                        r = self.review(episode=ep)
                        results[f"review_ep{ep}"] = r

                elif phase == "storyboard":
                    for ep in range(1, episodes + 1):
                        r = self.storyboard(episode=ep)
                        results[f"storyboard_ep{ep}"] = r

                elif phase == "final_check":
                    r = self.final_check()

                if phase != "write" and phase != "review" and phase != "storyboard":
                    results[phase] = r
                    if r.get("status") == "failed":
                        print(f"❌ 阶段 '{phase}' 失败，停止管线")
                        break

            except Exception as e:
                print(f"❌ 阶段 '{phase}' 执行异常: {e}")
                self.state.log_error(phase, "pipeline", str(e))
                results[phase] = {"status": "failed", "error": str(e)}
                if not self.auto_continue:
                    break

        # 打印最终报告
        self.state.print_progress()
        return results

    # ═══════════════════════════════════════════════════════════
    # 阶段执行核心
    # ═══════════════════════════════════════════════════════════

    def _run_phase(self, phase: str, **kwargs) -> dict:
        """
        执行单个管线阶段。

        Args:
            phase: 阶段名称
            **kwargs: 阶段特定参数

        Returns:
            阶段执行结果
        """
        if phase not in self.PHASES:
            raise ValueError(f"未知阶段: {phase}。有效值: {self.PHASES}")

        print(f"\n{'─'*50}")
        print(f"📌 Phase: {phase} — {self.PHASE_DESCRIPTIONS.get(phase, '')}")
        print(f"{'─'*50}")

        # 前置钩子
        self._run_hooks("before_phase", phase, kwargs)

        # 开始阶段
        episode = kwargs.get("episode")
        self.state.start_phase(phase, episode)

        start_time = time.time()
        result = {"status": "completed", "phase": phase}

        try:
            # 分派到具体处理方法
            handler = getattr(self, f"_handle_{phase}", None)
            if handler:
                phase_result = handler(**kwargs)
                result.update(phase_result)
            else:
                result["status"] = "skipped"
                result["message"] = f"阶段 '{phase}' 处理器未实现"

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            self.state.log_error(phase, "pipeline", str(e))
            self._run_hooks("on_error", phase, {"error": str(e)})
            print(f"❌ 阶段 '{phase}' 失败: {e}")

        duration = time.time() - start_time
        result["duration_seconds"] = round(duration, 1)

        # 完成阶段
        if result.get("status") == "completed":
            self.state.complete_phase(phase, episode)
            print(f"✅ 阶段 '{phase}' 完成 ({duration:.1f}s)")
        else:
            print(f"⚠️  阶段 '{phase}' 未完全成功: {result.get('status')}")

        # 后置钩子
        self._run_hooks("after_phase", phase, result)

        return result

    # ═══════════════════════════════════════════════════════════
    # 阶段处理器（委托给 Agent）
    # ═══════════════════════════════════════════════════════════

    def _handle_ingest(self, source_dir: str, **kwargs) -> dict:
        """处理 Phase 0: 知识收编"""
        if not source_dir or not os.path.isdir(source_dir):
            return {"status": "failed", "error": f"源目录不存在: {source_dir}"}

        agent = self.agents.get("knowledge-curator")
        if agent:
            result = agent.execute(source_dir=source_dir, state_manager=self.state)
            return result

        # Fallback: 基本扫描
        files = []
        for root, _, filenames in os.walk(source_dir):
            for fn in filenames:
                if fn.endswith((".txt", ".md")):
                    files.append(os.path.join(root, fn))

        return {
            "status": "completed",
            "source_dir": source_dir,
            "files_found": len(files),
            "file_list": files[:50],
            "message": f"扫描完成，发现 {len(files)} 个文本文件（未启用 Agent，仅扫描）",
        }

    def _handle_analyze(self, title: str = "", author: str = "", **kwargs) -> dict:
        """处理 Phase 1: 改编分析"""
        agent = self.agents.get("novel-analyzer")
        if agent:
            result = agent.execute(
                title=title, author=author, state_manager=self.state,
                llm_extractor=self.llm_extractor,
                rule_extractor=self.rule_extractor,
                character_tracker=self.character_tracker,
            )
            return result

        return {
            "status": "completed",
            "message": "改编分析阶段（未启用 Agent，请实现 novel-analyzer Agent）",
            "title": title,
            "author": author,
        }

    def _handle_plan(self, episodes: int = 40, **kwargs) -> dict:
        """处理 Phase 2: 分集规划"""
        agent = self.agents.get("episode-architect")
        if agent:
            result = agent.execute(
                episodes=episodes, state_manager=self.state,
            )
            return result

        return {
            "status": "completed",
            "message": "分集规划阶段（未启用 Agent，请实现 episode-architect Agent）",
            "target_episodes": episodes,
        }

    def _handle_write(self, episode: int, revision_round: int = 0, **kwargs) -> dict:
        """
        处理 Phase 3: 剧本生成。

        Args:
            episode: 集数
            revision_round: 回改轮次（0 = 初稿）
        """
        agent = self.agents.get("script-writer")
        if agent:
            result = agent.execute(
                episode=episode,
                revision_round=revision_round,
                state_manager=self.state,
                llm_extractor=self.llm_extractor,
                character_tracker=self.character_tracker,
                script_builder=self.script_builder,
            )
            return result

        return {
            "status": "completed",
            "message": f"第{episode}集剧本生成（未启用 Agent）",
            "episode": episode,
            "revision_round": revision_round,
        }

    def _handle_review(self, episode: int, **kwargs) -> dict:
        """处理 Phase 4: 多维度审核"""
        agent = self.agents.get("review-director")
        if agent:
            result = agent.execute(
                episode=episode, state_manager=self.state,
                schema_validator=self.schema_validator,
            )
            return result

        return {
            "status": "completed",
            "message": f"第{episode}集审核（未启用 Agent）",
            "episode": episode,
            "passed": True,
        }

    def _handle_storyboard(self, episode: int, mode: str = "film", **kwargs) -> dict:
        """处理 Phase 5: 分镜可视化"""
        agent = self.agents.get("storyboard-director")
        if agent:
            result = agent.execute(
                episode=episode, mode=mode, state_manager=self.state,
            )
            return result

        return {
            "status": "completed",
            "message": f"第{episode}集分镜（未启用 Agent，模式: {mode}）",
            "episode": episode,
            "mode": mode,
        }

    def _handle_final_check(self, **kwargs) -> dict:
        """处理 Phase 6: 完成检查"""
        issues = []

        # 1. 检查输出目录完整性
        project_dir = os.path.join(self.output_dir, self.project_name)
        expected_dirs = ["analysis", "planning", "scripts", "review", "storyboard"]
        for d in expected_dirs:
            d_path = os.path.join(project_dir, d)
            if not os.path.exists(d_path):
                issues.append(f"缺少目录: {d}")

        # 2. 检查 UTF-8 乱码
        # (简化版：检查是否有替换字符)
        for root, _, files in os.walk(project_dir):
            for fn in files:
                if fn.endswith((".yaml", ".md", ".json", ".txt")):
                    fpath = os.path.join(root, fn)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            content = f.read()
                        if "�" in content:
                            issues.append(f"可能存在乱码: {fpath}")
                    except UnicodeDecodeError:
                        issues.append(f"UTF-8 解码失败: {fpath}")

        # 3. 状态一致性检查
        write_eps = self.state.state["phases"]["write"].get("episodes_completed", [])
        review_eps = self.state.state["phases"]["review"].get("episodes_completed", [])
        if set(write_eps) != set(review_eps):
            missing_review = set(write_eps) - set(review_eps)
            if missing_review:
                issues.append(f"以下集数已生成但未审核: {sorted(missing_review)}")

        report_path = os.path.join(project_dir, "final-check-report.md")
        report_content = self._generate_final_report(issues)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        return {
            "status": "completed",
            "total_issues": len(issues),
            "issues": issues,
            "report_path": report_path,
            "passed": len(issues) == 0,
        }

    def _generate_final_report(self, issues: list) -> str:
        """生成最终检查报告（Markdown 格式）"""
        report = []
        report.append(f"# 完成检查报告 — {self.project_name}")
        report.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"管线版本: 2.0")
        report.append(f"\n---\n")

        # 进度摘要
        progress = self.state.get_progress_report()
        report.append("## 项目进度")
        report.append(f"- 阶段进度: {progress['progress']}")
        report.append(f"- 已写集数: {progress['episodes_written']}")
        report.append(f"- 已审核集数: {progress['episodes_reviewed']}")
        report.append(f"- 已分镜集数: {progress['episodes_storyboarded']}")
        report.append(f"- Agent 调用: {progress['total_agent_calls']} 次")
        report.append(f"- 成功率: {progress['success_rate']}")

        # 问题列表
        report.append(f"\n## 发现的问题 ({len(issues)} 个)")
        if issues:
            for i, issue in enumerate(issues, 1):
                report.append(f"{i}. {issue}")
        else:
            report.append("✅ 未发现问题")

        # 连续性记录
        report.append(f"\n## 连续性记录")
        ctx = self.state.get_continuity_context()
        if ctx.strip():
            report.append(ctx)
        else:
            report.append("（无记录）")

        return "\n".join(report)

    # ═══════════════════════════════════════════════════════════
    # 钩子管理
    # ═══════════════════════════════════════════════════════════

    def add_hook(self, event: str, callback: Callable):
        """
        添加管线钩子。

        Args:
            event: 'before_phase' | 'after_phase' | 'on_error'
            callback: (phase: str, context: dict) -> None
        """
        if event in self.hooks:
            self.hooks[event].append(callback)

    def _run_hooks(self, event: str, phase: str, context: dict):
        """执行钩子"""
        for callback in self.hooks.get(event, []):
            try:
                callback(phase, context)
            except Exception as e:
                print(f"⚠️  钩子执行失败 ({event}): {e}")

    # ═══════════════════════════════════════════════════════════
    # 审核闭环
    # ═══════════════════════════════════════════════════════════

    def review_and_rewrite_loop(
        self, episode: int, max_rounds: int = None
    ) -> dict:
        """
        对单集执行 生成→审核→回改→复审 闭环。

        Args:
            episode: 集数
            max_rounds: 最大回改轮次（默认使用管线配置）

        Returns:
            {final_script, review_history, rounds, passed}
        """
        max_rounds = max_rounds or self.max_rewrite_rounds
        history = []

        for round_num in range(max_rounds + 1):
            print(f"\n{'~'*40}")
            print(f"📝 第{episode}集 — 第{round_num}轮"
                  f"{'（初稿）' if round_num == 0 else '（回改）'}")
            print(f"{'~'*40}")

            # 写剧本
            write_result = self.write(episode=episode, revision_round=round_num)
            if write_result.get("status") != "completed":
                return {
                    "final_script": None,
                    "review_history": history,
                    "rounds": round_num,
                    "passed": False,
                    "error": write_result.get("error", "写剧本失败"),
                }

            # 审核
            review_result = self.review(episode=episode)
            history.append({
                "round": round_num,
                "write": write_result,
                "review": review_result,
            })

            if review_result.get("passed"):
                print(f"✅ 第{episode}集审核通过！(第{round_num}轮)")
                return {
                    "final_script": write_result,
                    "review_history": history,
                    "rounds": round_num,
                    "passed": True,
                }
            else:
                suggestions = review_result.get("suggestions", "无具体建议")
                print(f"🔄 第{episode}集审核未通过，回改建议: {suggestions}")

        print(f"⚠️  第{episode}集达到最大回改轮次({max_rounds})，审核仍未通过")
        return {
            "final_script": write_result if 'write_result' in dir() else None,
            "review_history": history,
            "rounds": max_rounds,
            "passed": False,
        }

    # ═══════════════════════════════════════════════════════════
    # 状态查询
    # ═══════════════════════════════════════════════════════════

    def get_status(self) -> dict:
        """获取管线当前状态"""
        return self.state.get_progress_report()

    def get_phase_detail(self, phase: str) -> dict:
        """获取某阶段的详细信息"""
        return self.state.get_phase_status(phase)

    def print_pipeline_diagram(self):
        """打印管线流程图"""
        phase_status = {}
        for p in self.PHASES:
            info = self.state.get_phase_status(p)
            icon = {
                "completed": "✅",
                "in_progress": "🔄",
                "pending": "⬜",
            }.get(info.get("status", "pending"), "❓")
            phase_status[p] = icon

        print(f"""
管线流程图 — {self.project_name}
{'='*60}

  {phase_status['ingest']} ingest ──→ {phase_status['analyze']} analyze ──→ {phase_status['plan']} plan
                                      │
                                      ▼
  {phase_status['final_check']} final_check ←── {phase_status['storyboard']} storyboard ←── {phase_status['review']} review ←── {phase_status['write']} write
                                      │                                            │
                                      └── 分集循环 ─────────────────────────────────┘

图例: ✅ 已完成  🔄 进行中  ⬜ 待执行
{'='*60}
""")


# ═══════════════════════════════════════════════════════════════
# 便捷工厂函数
# ═══════════════════════════════════════════════════════════════

def create_pipeline(
    project_name: str = "untitled",
    output_dir: str = "./output",
    config_path: str = "config.yaml",
    agents: dict = None,
) -> Pipeline:
    """
    便捷工厂：从配置文件创建完整的 Pipeline 实例。

    Args:
        project_name: 项目名称
        output_dir: 输出目录
        config_path: 全局配置 YAML 文件路径
        agents: Agent 实例字典

    Returns:
        Pipeline 实例
    """
    import yaml

    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

    return Pipeline(
        project_name=project_name,
        output_dir=output_dir,
        config=config,
        agents=agents,
    )
