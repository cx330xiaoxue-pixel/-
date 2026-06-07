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
import json
import time
from datetime import datetime
from typing import Any, Callable, Optional

from .state_manager import AgentStateManager, create_state_manager
from .task_queue import TaskQueue, Task, TaskStatus, TaskPriority

# ── Fallback: 接入 novel-to-script-yaml 的可运行代码 ──
_NTS_YAML_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "novel-to-script-yaml")
if _NTS_YAML_DIR not in sys.path:
    sys.path.insert(0, _NTS_YAML_DIR)

# Lazy imports for fallback extractor / builder
_mock_extractor = None
_script_builder = None

def _get_mock_extractor():
    global _mock_extractor
    if _mock_extractor is None:
        from mock_extractor import MockExtractor
        _mock_extractor = MockExtractor()
    return _mock_extractor

def _get_script_builder(title: str = "", original_work: str = "", author: str = ""):
    from script_builder import ScriptBuilder
    return ScriptBuilder(title=title, original_work=original_work, author=author)


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
        "generate_images",
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
        "generate_images": "图片生成 — 从分镜数据生成图片提示词与AI图片",
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

    def plan(self, episodes: int = 40, target_format: str = "long_drama", **kwargs) -> dict:
        """
        Phase 2: 分集规划 — 章节→集映射（支持智能节奏分集）。

        Args:
            episodes: 目标集数
            target_format: 剧集格式 short_drama | long_drama

        Returns:
            阶段结果 {status, episode_plan, ...}
        """
        return self._run_phase("plan", episodes=episodes, target_format=target_format, **kwargs)

    def write(self, episode: int, adaptation_mode: str = None, **kwargs) -> dict:
        """
        Phase 3: 剧本生成 — 生成单集完整剧本（支持内容分级）。

        Args:
            episode: 集数
            adaptation_mode: v2.1 适应度模式 strict | balanced | loose

        Returns:
            阶段结果 {status, script_yaml, script_path, grading_stats, ...}
        """
        return self._run_phase("write", episode=episode, adaptation_mode=adaptation_mode, **kwargs)

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
        adaptation_mode: str = "balanced",
        target_format: str = "long_drama",
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
            adaptation_mode: v2.1 适应度模式 strict | balanced | loose
            target_format: v2.1 剧集格式 short_drama | long_drama

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
                    r = self.plan(episodes=episodes, target_format=target_format)

                elif phase == "write":
                    # Pass plan & analysis context to write phase
                    plan_data = results.get("plan", {})
                    analyze_data = results.get("analyze", {})
                    for ep in range(1, episodes + 1):
                        r = self.write(
                            episode=ep,
                            episode_plan=plan_data.get("episode_plan", []),
                            analysis_result=analyze_data,
                            adaptation_mode=adaptation_mode,
                        )
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
                        # 分镜后自动生成图片提示词
                        img_r = self.generate_image_prompts(episode=ep)
                        results[f"image_prompts_ep{ep}"] = img_r

                elif phase == "generate_images":
                    for ep in range(1, episodes + 1):
                        r = self.generate_image_prompts(episode=ep)
                        results[f"image_prompts_ep{ep}"] = r

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
        if phase not in self.PHASES and phase != "generate_images":
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
            # 尝试 fallback: uploads 目录 → sample_novel
            alt = os.path.join("uploads", self.project_name)
            if os.path.isdir(alt) and os.listdir(alt):
                source_dir = alt
            elif os.path.isdir("./sample_novel"):
                source_dir = "./sample_novel"
            else:
                return {"status": "failed", "error": f"源目录不存在: {source_dir}，请先上传小说文件"}

        agent = self.agents.get("knowledge-curator")
        if agent:
            result = agent.execute(source_dir=source_dir, state_manager=self.state)
            return result

        # Fallback: 扫描并复制源文件到项目输出目录
        files = []
        for root, _, filenames in os.walk(source_dir):
            for fn in filenames:
                if fn.endswith((".txt", ".md")):
                    files.append(os.path.join(root, fn))

        # 把源文件列表和内容存到项目输出目录供后续阶段使用
        project_dir = os.path.join(self.output_dir, self.project_name)
        sources_dir = os.path.join(project_dir, "sources")
        os.makedirs(sources_dir, exist_ok=True)

        chapters = []
        for fpath in sorted(files):
            fname = os.path.basename(fpath)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            chapters.append({"name": fname, "content": content, "path": fpath})

        # 保存章节索引供 write 阶段使用
        index_path = os.path.join(sources_dir, "chapters_index.json")
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(chapters, f, ensure_ascii=False, indent=2)

        return {
            "status": "completed",
            "source_dir": source_dir,
            "files_found": len(files),
            "chapters_loaded": len(chapters),
            "index_path": index_path,
            "message": f"扫描完成，加载 {len(chapters)} 个章节",
        }

    def _handle_analyze(self, title: str = "", author: str = "", **kwargs) -> dict:
        """处理 Phase 1: 改编分析"""
        # Determine source_dir from ingest phase output or fallback to sample_novel
        project_dir = os.path.join(self.output_dir, self.project_name)
        sources_dir = os.path.join(project_dir, "sources")
        index_path = os.path.join(sources_dir, "chapters_index.json")
        default_source = "./sample_novel" if os.path.isdir("./sample_novel") else None

        source_dir = default_source
        if os.path.exists(index_path):
            source_dir = sources_dir  # Use ingested chapters

        agent = self.agents.get("novel-analyzer")
        if agent:
            result = agent.execute(
                title=title, author=author, state_manager=self.state,
                llm_extractor=self.llm_extractor,
                rule_extractor=self.rule_extractor,
                character_tracker=self.character_tracker,
                source_dir=source_dir,
            )
            if result.get("status") == "completed":
                return result
            # If agent failed, fall through to fallback
            print(f"  ⚠️  Agent 分析失败: {result.get('error')}，使用 Fallback")

        # Fallback: 基于已加载章节做基础分析
        chapters = []
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                chapters = json.load(f)

        total_chars = sum(len(ch["content"]) for ch in chapters)
        analysis_dir = os.path.join(project_dir, "analysis")
        os.makedirs(analysis_dir, exist_ok=True)

        # 生成简单分析报告
        report_lines = [
            f"# 改编分析报告 — {title or self.project_name}",
            f"\n**作者**: {author or '未知'}",
            f"**总章节数**: {len(chapters)}",
            f"**总字符数**: {total_chars:,}",
            f"**改编难度**: 中等",
            f"**推荐媒介**: 电视剧",
            f"\n## 章节概况",
        ]
        for i, ch in enumerate(chapters, 1):
            report_lines.append(f"- 第{i}章: {ch['name']} ({len(ch['content']):,} 字符)")

        report_path = os.path.join(analysis_dir, "analysis-report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        return {
            "status": "completed",
            "title": title or self.project_name,
            "author": author,
            "total_chapters": len(chapters),
            "total_characters": total_chars,
            "report_path": report_path,
            "message": f"分析完成：{len(chapters)}章，{total_chars:,}字",
        }

    def _handle_plan(self, episodes: int = 40, **kwargs) -> dict:
        """处理 Phase 2: 分集规划 — 支持智能节奏分集"""
        project_dir = os.path.join(self.output_dir, self.project_name)
        sources_dir = os.path.join(project_dir, "sources")
        index_path = os.path.join(sources_dir, "chapters_index.json")

        chapters = []
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                chapters = json.load(f)

        # 尝试加载已提取的元素（从 analyze 阶段产出）
        all_elements = self._load_analyzed_elements()

        # ── 检查是否启用智能分集 ──
        rhythm_cfg = self.config.get("episode_rhythm", {})
        use_smart_planning = rhythm_cfg.get("enabled", True) and len(chapters) >= 3

        if use_smart_planning:
            target_format = rhythm_cfg.get("target_format", "long_drama")
            director = self.agents.get("episode-director")
            if director and all_elements:
                print(f"  🎬 使用智能分集引擎 (格式: {target_format})")
                result = director.execute(
                    chapters=chapters,
                    elements=all_elements,
                    target_format=target_format,
                    target_episodes=episodes,
                    state_manager=self.state,
                    use_llm=True,
                )
                if result.get("status") == "completed":
                    return result
                print(f"  ⚠️  智能分集失败: {result.get('error')}，回退到传统分集")

        # 回退: 使用传统 episode-architect 或简单映射
        agent = self.agents.get("episode-architect")
        if agent and all_elements:
            result = agent.execute(
                episodes=episodes, state_manager=self.state,
                all_elements=all_elements,
            )
            if result.get("status") == "completed":
                return result

        # Fallback: 简单比例映射
        planning_dir = os.path.join(project_dir, "planning")
        os.makedirs(planning_dir, exist_ok=True)

        plan_lines = [
            f"# 分集规划 — {self.project_name}",
            f"\n**目标集数**: {episodes}",
            f"**可用章节**: {len(chapters)}",
            f"\n## 章节→剧集映射",
        ]
        for i, ch in enumerate(chapters, 1):
            plan_lines.append(f"- 第{i}集 ← 第{i}章: {ch['name']}")

        plan_path = os.path.join(planning_dir, "episode-plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("\n".join(plan_lines))

        return {
            "status": "completed",
            "target_episodes": episodes,
            "chapters_available": len(chapters),
            "plan_path": plan_path,
            "message": f"分集规划完成：{len(chapters)}章 → {min(episodes, len(chapters))}集",
        }

    def _handle_write(self, episode: int, revision_round: int = 0, **kwargs) -> dict:
        """
        处理 Phase 3: 剧本生成 — 使用 LLM 抽取器 + ScriptBuilder。
        不走 Agent（Agent 需要跨阶段数据，不稳定），直接调用 extractor。
        """
        # ── 找到源章节 ──
        project_dir = os.path.join(self.output_dir, self.project_name)
        sources_dir = os.path.join(project_dir, "sources")
        index_path = os.path.join(sources_dir, "chapters_index.json")

        chapters = []
        # 1) 优先从 ingest 阶段的索引加载
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                chapters = json.load(f)
        # 2) 从 upload 目录加载
        if not chapters:
            upload_dir = os.path.join("uploads", self.project_name)
            if os.path.isdir(upload_dir):
                for fn in sorted(os.listdir(upload_dir)):
                    if fn.endswith(".txt"):
                        fpath = os.path.join(upload_dir, fn)
                        with open(fpath, "r", encoding="utf-8") as f:
                            chapters.append({"name": fn, "content": f.read()})
        # 3) 最后才用 sample_novel
        if not chapters:
            sample_dir = "./sample_novel"
            if os.path.isdir(sample_dir):
                for fn in sorted(os.listdir(sample_dir)):
                    if fn.endswith(".txt"):
                        fpath = os.path.join(sample_dir, fn)
                        with open(fpath, "r", encoding="utf-8") as f:
                            chapters.append({"name": fn, "content": f.read()})

        if not chapters:
            return {"status": "failed", "error": "没有找到源章节。请先上传小说文件（导入标签页）"}

        chapter_idx = (episode - 1) % len(chapters)
        chapter = chapters[chapter_idx]
        print(f"  📝 生成第{episode}集剧本 ← 第{chapter_idx + 1}章: {chapter['name']}")

        # ── LLM 抽取结构化元素 ──
        if self.llm_extractor is None:
            return {
                "status": "failed",
                "error": "LLM 抽取器未初始化，请先配置 API Key",
            }

        try:
            # extract_from_chapter 支持滑窗处理长章节
            elements = self.llm_extractor.extract_from_chapter(
                chapter_text=chapter["content"],
                chapter_id=episode,
                chapter_title=chapter["name"],
                chapter_context=f"第{chapter_idx + 1}章",
            )
        except Exception as e:
            return {
                "status": "failed",
                "error": f"LLM 抽取失败: {e}",
            }

        if not elements:
            return {
                "status": "failed",
                "error": f"LLM 未从章节 '{chapter['name']}' 中抽取到任何元素",
            }

        print(f"     ✅ LLM 抽取 {len(elements)} 个结构化元素")

        # ── 内容分级（v2.1 新增）──
        grading_cfg = self.config.get("content_grading", {})
        grading_stats = None
        original_element_count = len(elements)

        if grading_cfg.get("enabled", True) and len(elements) > 10:
            adaptation_mode = kwargs.get("adaptation_mode") or grading_cfg.get("mode", "balanced")
            print(f"  📊 内容分级中 (模式: {adaptation_mode})...")

            grader = self.agents.get("content-grader")
            if grader:
                try:
                    # 尝试加载角色网络用于重要性判断
                    char_network = self._load_character_network()
                    grade_result = grader.execute(
                        elements=elements,
                        mode=adaptation_mode,
                        character_network=char_network,
                        use_llm=grading_cfg.get("llm_borderline_review", True),
                        state_manager=self.state,
                    )
                    if grade_result.get("status") == "completed":
                        # 使用分级处理后的元素
                        elements = grade_result.get("processed_elements", elements)
                        grading_stats = grade_result.get("stats", {})
                        grading_stats["filtered_count"] = grade_result.get("filtered_count", 0)
                        print(f"     📊 分级完成: S={grading_stats.get('S_count',0)}, "
                              f"A={grading_stats.get('A_count',0)}, "
                              f"B={grading_stats.get('B_count',0)}, "
                              f"过滤 {grading_stats['filtered_count']} 个元素")
                except Exception as e:
                    print(f"  ⚠️  内容分级失败: {e}，使用原始元素继续")
            else:
                # Fallback: 使用 skill 直接分级
                try:
                    from skills.content_grading import ContentGradingSkill
                    skill = ContentGradingSkill()
                    graded = skill.grade_elements(elements, mode=adaptation_mode)
                    max_chars = grading_cfg.get("max_merged_narration_chars", 50)
                    elements = skill.apply_grading_to_elements(graded, mode=adaptation_mode, max_merged_chars=max_chars)
                    grading_stats = skill.get_grading_report(graded)
                    grading_stats["filtered_count"] = original_element_count - len(elements)
                    print(f"     📊 规则分级完成: 过滤 {grading_stats['filtered_count']} 个元素")
                except Exception as e:
                    print(f"  ⚠️  规则分级失败: {e}")

        # ── 构建 YAML 剧本 ──
        builder = _get_script_builder(
            title=self.project_name,
            original_work=self.project_name,
            author="AI 辅助改编",
        )

        script = builder.build_with_grading(
            all_elements=elements,
            include_emotion=True,
            include_action=True,
            grading_stats=grading_stats,
        )

        scripts_dir = os.path.join(project_dir, "scripts")
        os.makedirs(scripts_dir, exist_ok=True)
        script_path = os.path.join(scripts_dir, f"ep{episode:02d}_script.yaml")

        yaml_content = builder.to_yaml(script)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        stats = script.get("script", {}).get("metadata", {}).get("statistics", {})
        char_count = len(script.get("script", {}).get("characters", []))

        return {
            "status": "completed",
            "episode": episode,
            "source_chapter": chapter["name"],
            "elements_count": len(elements),
            "original_element_count": original_element_count,
            "characters_count": char_count,
            "dialogue_count": stats.get("dialogue_count", 0),
            "grading_stats": grading_stats,
            "script_path": script_path,
            "message": f"第{episode}集剧本已生成: {script_path}",
        }

    def _handle_review(self, episode: int, **kwargs) -> dict:
        """处理 Phase 4: 多维度审核 — 使用 ReviewDirector Agent"""
        project_dir = os.path.join(self.output_dir, self.project_name)
        script_path = os.path.join(project_dir, "scripts", f"ep{episode:02d}_script.yaml")

        if not os.path.exists(script_path):
            return {"status": "failed", "error": f"剧本文件不存在: {script_path}"}

        agent = self.agents.get("review-director")
        if agent:
            review_dir = os.path.join(project_dir, "review")
            os.makedirs(review_dir, exist_ok=True)
            result = agent.execute(
                episode=episode,
                script_path=script_path,
                state_manager=self.state,
                use_llm=True,
            )
            if result.get("status") == "completed":
                return result

        # 无 Agent 时做基础审核
        review_dir = os.path.join(project_dir, "review")
        os.makedirs(review_dir, exist_ok=True)
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()
        lines = content.count("\n")

        review_text = (
            f"# 审核报告 — 第{episode}集\n\n"
            f"✅ 剧本文件存在 ({lines} 行)\n"
            f"⚠️  未启用审核 Agent，此为自动通过"
        )
        review_path = os.path.join(review_dir, f"review-ep{episode:02d}.md")
        with open(review_path, "w", encoding="utf-8") as f:
            f.write(review_text)

        return {
            "status": "completed",
            "episode": episode,
            "passed": True,
            "review_path": review_path,
            "message": f"第{episode}集审核通过",
        }

    def _handle_storyboard(self, episode: int, mode: str = "film", **kwargs) -> dict:
        """处理 Phase 5: 分镜可视化 — 从剧本 YAML 解析元素直接生成分镜"""
        project_dir = os.path.join(self.output_dir, self.project_name)
        script_path = os.path.join(project_dir, "scripts", f"ep{episode:02d}_script.yaml")

        if not os.path.exists(script_path):
            return {"status": "failed", "error": f"剧本文件不存在: {script_path}"}

        sb_dir = os.path.join(project_dir, "storyboard", f"ep{episode:02d}")
        os.makedirs(sb_dir, exist_ok=True)

        # ── 解析剧本 YAML ──
        import yaml as _yaml
        try:
            with open(script_path, "r", encoding="utf-8") as _f:
                _script_data = _yaml.safe_load(_f)
        except Exception as _e:
            return {"status": "failed", "error": f"剧本 YAML 解析失败: {_e}"}

        _script = (_script_data or {}).get("script", {})
        _chapters = _script.get("chapters", [])
        _characters = _script.get("characters", [])

        # 收集所有元素，并基于 type 字段推断 beat_type
        all_elements = []
        for _ch in _chapters:
            for _sc in _ch.get("scenes", []):
                for _el in _sc.get("elements", []):
                    all_elements.append(_el)

        # beat_type 推断规则
        def _infer_beat(el):
            t = el.get("type", "")
            if t in ("dialogue",): return "confrontation"
            if t in ("action",): return "action"
            if t in ("description",): return "setup"
            if t in ("narration",): return "transition"
            return "neutral"

        # ── 场景 → 序列板 (Sequence Board) ──
        sequences = []
        for _ch in _chapters:
            for _sc in _ch.get("scenes", []):
                shots = []
                for _el in _sc.get("elements", []):
                    bt = _infer_beat(_el)
                    shots.append({
                        "shot_id": _el.get("element_id", ""),
                        "type": _el.get("type", ""),
                        "role": _el.get("role", "旁白"),
                        "text": (_el.get("text", "") or "")[:120],
                        "beat_type": bt,
                        "emotion": _el.get("emotion", ""),
                        "action_hint": _el.get("action", ""),
                        "camera": (
                            "CU" if _el.get("type") == "dialogue" else
                            "WS" if _el.get("type") == "description" else
                            "MS"
                        ),
                    })

                sequences.append({
                    "scene_id": _sc.get("scene_id", _sc.get("scene_number", "?")),
                    "scene_number": _sc.get("scene_number", 1),
                    "location": _sc.get("location", "未指定"),
                    "time": _sc.get("time", "未指定"),
                    "atmosphere": _sc.get("atmosphere", ""),
                    "characters_present": _sc.get("characters_present", []),
                    "shot_count": len(shots),
                    "beats": list(set(s.get("beat_type") for s in shots)),
                    "shots": shots,
                })

        beat_count = sum(len(seq["beats"]) for seq in sequences)
        total_shots = sum(seq["shot_count"] for seq in sequences)

        # ── 保存产物 ──
        # Sequence Board
        sb_json = {
            "episode": episode,
            "mode": mode,
            "generated_at": datetime.now().isoformat(),
            "scene_count": len(sequences),
            "total_beats": beat_count,
            "total_shots": total_shots,
            "characters": [{"name": c.get("name", ""), "role": c.get("role_type", "")} for c in _characters[:10]],
            "sequences": sequences,
        }
        with open(os.path.join(sb_dir, "sequence_board.json"), "w", encoding="utf-8") as _f:
            json.dump(sb_json, _f, ensure_ascii=False, indent=2)

        # Motion Prompts (镜头运动提示)
        motion_prompts = []
        for seq in sequences:
            for shot in seq["shots"]:
                motion_prompts.append({
                    "shot_id": shot["shot_id"],
                    "scene": seq["scene_number"],
                    "camera": shot["camera"],
                    "subject": shot["role"],
                    "action": shot["action_hint"],
                    "text_snippet": shot["text"][:80],
                })
        with open(os.path.join(sb_dir, "motion_prompts.json"), "w", encoding="utf-8") as _f:
            json.dump(motion_prompts, _f, ensure_ascii=False, indent=2)

        # Manifest
        manifest = {
            "episode": episode,
            "mode": mode,
            "scene_count": len(sequences),
            "beat_count": beat_count,
            "total_shots": total_shots,
            "files": ["sequence_board.json", "motion_prompts.json"],
        }
        with open(os.path.join(sb_dir, "manifest.json"), "w", encoding="utf-8") as _f:
            json.dump(manifest, _f, ensure_ascii=False, indent=2)

        return {
            "status": "completed",
            "episode": episode,
            "mode": mode,
            "scene_count": len(sequences),
            "beat_count": beat_count,
            "total_shots": total_shots,
            "storyboard_dir": str(sb_dir),
            "message": f"第{episode}集分镜完成: {len(sequences)}场景, {total_shots}镜头, {beat_count}节拍类型",
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
    # 数据加载辅助方法（v2.1 新增）
    # ═══════════════════════════════════════════════════════════

    def _load_analyzed_elements(self) -> list:
        """加载分析阶段产生的结构化元素（供 plan/write 阶段复用）"""
        project_dir = os.path.join(self.output_dir, self.project_name)
        analysis_dir = os.path.join(project_dir, "analysis")
        elements_path = os.path.join(analysis_dir, "all_elements.json")
        if os.path.exists(elements_path):
            try:
                with open(elements_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _load_character_network(self) -> dict:
        """加载角色网络分析结果（供 grading 使用）"""
        project_dir = os.path.join(self.output_dir, self.project_name)
        analysis_dir = os.path.join(project_dir, "analysis")
        network_path = os.path.join(analysis_dir, "character_network.json")
        if os.path.exists(network_path):
            try:
                with open(network_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

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

    def _handle_generate_images(self, episode: int, mode: str = "film", **kwargs) -> dict:
        """Phase: 从分镜生成图片提示词"""
        return self.generate_image_prompts(episode, mode)

    def generate_image_prompts(self, episode: int, mode: str = "film") -> dict:
        """从分镜数据生成图片提示词。Storyboard → Image Prompts"""
        project_dir = os.path.join(self.output_dir, self.project_name)
        sb_dir = os.path.join(project_dir, "storyboard", f"ep{episode:02d}")
        seq_path = os.path.join(sb_dir, "sequence_board.json")

        if not os.path.exists(seq_path):
            return {"status": "skipped", "error": "sequence_board.json 不存在，请先运行分镜"}

        with open(seq_path, "r", encoding="utf-8") as f:
            seq_data = json.load(f)

        prompts = []
        for seq in seq_data.get("sequences", []):
            for shot in seq.get("shots", []):
                camera_map = {"CU": "close-up shot", "WS": "wide shot", "MS": "medium shot"}
                camera_desc = camera_map.get(shot.get("camera", "MS"), "medium shot")

                img_prompt = (
                    f"{camera_desc}, {seq.get('location', 'scene')}, "
                    f"{seq.get('atmosphere', '')}, {shot.get('beat_type', '')}, "
                    f"{shot.get('role', '')} - {shot.get('text', '')[:100]}"
                )
                prompts.append({
                    "shot_id": shot.get("shot_id", ""),
                    "scene": seq.get("scene_number", 1),
                    "camera": shot.get("camera", "MS"),
                    "prompt": img_prompt,
                    "negative_prompt": "blurry, low quality, distorted face, watermark, text",
                })

        images_dir = os.path.join(project_dir, "images", f"ep{episode:02d}")
        os.makedirs(images_dir, exist_ok=True)

        prompts_path = os.path.join(images_dir, "image_prompts.json")
        with open(prompts_path, "w", encoding="utf-8") as f:
            json.dump({"episode": episode, "total_prompts": len(prompts), "prompts": prompts}, f, ensure_ascii=False, indent=2)

        # 如果配了图生 API key，尝试生成
        generated = []
        img_cfg = self.config.get("image_gen", {})
        if img_cfg.get("api_key", ""):
            try:
                from skills.image_skills import ImageGenerationSkill
                skill = ImageGenerationSkill(self.config)
                for p in prompts[:3]:  # 限3张
                    result = skill.generate(
                        prompt=p["prompt"],
                        negative_prompt=p.get("negative_prompt", ""),
                        output_path=os.path.join(images_dir, f"{p['shot_id']}.png"),
                    )
                    generated.append(result)
            except Exception as e:
                print(f"  ⚠️  图片生成失败: {e}")

        return {
            "status": "completed",
            "episode": episode,
            "prompts_generated": len(prompts),
            "images_generated": len([g for g in generated if g.get("success")]),
            "prompts_path": prompts_path,
            "message": f"第{episode}集: {len(prompts)} 个图片提示词, {len([g for g in generated if g.get('success')])} 张图片已生成",
        }

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
    if isinstance(config_path, dict):
        config = config_path  # 直接传入 config dict
    elif config_path and os.path.exists(str(config_path)):
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

    # ── 创建抽取器（供 Agent 使用）──
    llm_extractor = None
    rule_extractor = None
    api_key = config.get("llm", {}).get("api_key", "")
    if api_key and api_key != "sk-YOUR-API-KEY" and len(api_key) > 10:
        try:
            from extractor import NovelExtractor
            # 将 config dict 写入临时文件供 NovelExtractor 使用
            import tempfile
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8")
            yaml.dump(config, tmp)
            tmp.close()
            llm_extractor = NovelExtractor(tmp.name)
            os.unlink(tmp.name)
        except Exception as e:
            print(f"⚠️  LLM 抽取器初始化失败: {e}")

    # 始终创建规则抽取器作为 fallback
    try:
        from mock_extractor import MockExtractor
        rule_extractor = MockExtractor()
    except Exception:
        pass

    return Pipeline(
        project_name=project_name,
        output_dir=output_dir,
        config=config,
        agents=agents,
        llm_extractor=llm_extractor,
        rule_extractor=rule_extractor,
    )
