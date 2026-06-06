"""
Agent 状态管理器 — 管线执行状态持久化与恢复

功能:
  - 读写 outputs/{剧本名}/.agent-state.json
  - 支持 Resume（恢复上下文）和 Reset（重置上下文）
  - 记录每个 Agent 的执行日志（时间戳、输入/输出摘要、耗时）
  - 跨集连续性记录（continuity_records）
  - 管线阶段进度追踪
"""

import json
import os
import sys
import time
from datetime import datetime

# Windows 终端默认 GBK 不支持 emoji，强制 UTF-8 输出
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
from typing import Any, Optional


class AgentStateManager:
    """Agent 状态管理器：持久化管线执行状态，支持中断续跑"""

    def __init__(self, project_name: str, output_dir: str = "./output"):
        """
        初始化状态管理器。

        Args:
            project_name: 剧本项目名称（用于子目录命名）
            output_dir: 输出根目录
        """
        self.project_name = project_name
        self.output_dir = output_dir
        self.project_dir = os.path.join(output_dir, project_name)
        self.state_file = os.path.join(self.project_dir, ".agent-state.json")

        # 内存中的状态缓存
        self.state: dict = {}

        # 确保目录存在
        os.makedirs(self.project_dir, exist_ok=True)

        # 加载或初始化
        if os.path.exists(self.state_file):
            self._load()
        else:
            self._init_fresh()

    # ═══════════════════════════════════════════════════════════
    # 初始化与持久化
    # ═══════════════════════════════════════════════════════════

    def _init_fresh(self):
        """初始化全新的状态结构"""
        self.state = {
            "project_name": self.project_name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "pipeline_version": "2.0",
            "current_phase": "idle",  # idle | ingest | analyze | plan | write | review | storyboard | final_check | done
            "current_episode": None,   # 当前正在处理的集数
            "phases_completed": [],    # 已完成的阶段列表
            "phases": {
                "ingest": {"status": "pending", "started_at": None, "completed_at": None},
                "analyze": {"status": "pending", "started_at": None, "completed_at": None},
                "plan": {"status": "pending", "started_at": None, "completed_at": None},
                "write": {"status": "pending", "started_at": None, "completed_at": None,
                          "episodes_completed": [], "episodes_in_progress": {}},
                "review": {"status": "pending", "started_at": None, "completed_at": None,
                           "episodes_completed": [], "episodes_in_progress": {}},
                "storyboard": {"status": "pending", "started_at": None, "completed_at": None,
                               "episodes_completed": [], "episodes_in_progress": {}},
                "final_check": {"status": "pending", "started_at": None, "completed_at": None},
            },
            "agent_logs": [],           # Agent 执行日志
            "continuity_records": {     # 跨集连续性记录
                "character_states": {},  # 角色状态快照
                "timeline": [],          # 时间线事件
                "unresolved_hooks": [],  # 未解决的悬念钩子
                "props_inventory": {},   # 道具清单
                "location_states": {},   # 地点状态
            },
            "errors": [],               # 错误记录
        }
        self._save()

    def _load(self):
        """从磁盘加载状态"""
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                self.state = json.load(f)
            print(f"📂 已加载项目状态: {self.state_file}")
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  状态文件损坏，重新初始化: {e}")
            self._init_fresh()

    def _save(self):
        """将当前状态写入磁盘"""
        self.state["updated_at"] = datetime.now().isoformat()
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
        print(f"💾 状态已保存: {self.state_file}")

    # ═══════════════════════════════════════════════════════════
    # 阶段管理
    # ═══════════════════════════════════════════════════════════

    def start_phase(self, phase: str, episode: int = None):
        """
        开始一个管线阶段。

        Args:
            phase: 阶段名称 (ingest/analyze/plan/write/review/storyboard/final_check)
            episode: 集数（write/review/storyboard 阶段需要）
        """
        if phase not in self.state["phases"]:
            raise ValueError(f"未知阶段: {phase}。有效值: {list(self.state['phases'].keys())}")

        self.state["current_phase"] = phase
        if episode is not None:
            self.state["current_episode"] = episode

        phase_info = self.state["phases"][phase]
        phase_info["status"] = "in_progress"
        if phase_info["started_at"] is None:
            phase_info["started_at"] = datetime.now().isoformat()

        if episode is not None:
            phase_info["episodes_in_progress"][str(episode)] = {
                "started_at": datetime.now().isoformat(),
                "round": 0,
            }

        self._save()

    def complete_phase(self, phase: str, episode: int = None):
        """
        完成一个管线阶段。

        Args:
            phase: 阶段名称
            episode: 集数（分集阶段需要）
        """
        if phase not in self.state["phases"]:
            raise ValueError(f"未知阶段: {phase}")

        phase_info = self.state["phases"][phase]
        phase_info["status"] = "completed"
        phase_info["completed_at"] = datetime.now().isoformat()

        if episode is not None:
            episodes_key = "episodes_completed"
            if episodes_key in phase_info:
                if episode not in phase_info[episodes_key]:
                    phase_info[episodes_key].append(episode)
            # 从 in_progress 中移除
            in_prog = phase_info.get("episodes_in_progress", {})
            in_prog.pop(str(episode), None)

        if phase not in self.state["phases_completed"]:
            self.state["phases_completed"].append(phase)

        self.state["current_phase"] = "idle"
        self.state["current_episode"] = None
        self._save()

    def get_phase_status(self, phase: str) -> dict:
        """获取指定阶段的状态"""
        return self.state["phases"].get(phase, {})

    def get_next_pending_phase(self) -> Optional[str]:
        """获取下一个未完成的阶段"""
        phase_order = ["ingest", "analyze", "plan", "write", "review", "storyboard", "final_check"]
        for phase in phase_order:
            status = self.state["phases"][phase]["status"]
            if status == "pending":
                return phase
            elif status == "in_progress":
                return phase  # 返回进行中的阶段以便继续
        return None

    def is_phase_completed(self, phase: str) -> bool:
        """检查阶段是否已完成"""
        return self.state["phases"].get(phase, {}).get("status") == "completed"

    # ═══════════════════════════════════════════════════════════
    # Agent 执行日志
    # ═══════════════════════════════════════════════════════════

    def log_agent_execution(
        self,
        agent_name: str,
        phase: str,
        episode: int = None,
        input_summary: str = "",
        output_summary: str = "",
        duration_seconds: float = 0.0,
        status: str = "success",  # success | failed | skipped
        error_message: str = "",
        token_usage: dict = None,
    ):
        """
        记录一次 Agent 执行。

        Args:
            agent_name: Agent 名称（如 'novel-analyzer'）
            phase: 所属管线阶段
            episode: 集数（可选）
            input_summary: 输入摘要
            output_summary: 输出摘要
            duration_seconds: 执行耗时
            status: 执行状态
            error_message: 错误信息（如果失败）
            token_usage: LLM token 消耗统计
        """
        log_entry = {
            "id": len(self.state["agent_logs"]) + 1,
            "agent_name": agent_name,
            "phase": phase,
            "episode": episode,
            "timestamp": datetime.now().isoformat(),
            "input_summary": input_summary[:500],
            "output_summary": output_summary[:500],
            "duration_seconds": round(duration_seconds, 2),
            "status": status,
            "error_message": error_message[:500],
            "token_usage": token_usage or {},
        }
        self.state["agent_logs"].append(log_entry)
        self._save()

    def get_agent_logs(
        self, agent_name: str = None, phase: str = None, status: str = None
    ) -> list:
        """
        查询 Agent 执行日志（支持过滤）。

        Args:
            agent_name: 按 Agent 名称过滤
            phase: 按阶段过滤
            status: 按状态过滤

        Returns:
            匹配的日志条目列表
        """
        logs = self.state["agent_logs"]
        if agent_name:
            logs = [l for l in logs if l["agent_name"] == agent_name]
        if phase:
            logs = [l for l in logs if l["phase"] == phase]
        if status:
            logs = [l for l in logs if l["status"] == status]
        return logs

    def get_last_agent_log(self, agent_name: str) -> Optional[dict]:
        """获取指定 Agent 最后一次执行的日志"""
        for log in reversed(self.state["agent_logs"]):
            if log["agent_name"] == agent_name:
                return log
        return None

    # ═══════════════════════════════════════════════════════════
    # 连续性记录
    # ═══════════════════════════════════════════════════════════

    def update_character_state(self, name: str, chapter_id: int, snapshot: dict):
        """
        更新角色跨集状态快照。

        Args:
            name: 角色名
            chapter_id: 章节ID
            snapshot: 状态快照 {status, location, emotion, hp_metaphor, ...}
        """
        if name not in self.state["continuity_records"]["character_states"]:
            self.state["continuity_records"]["character_states"][name] = []
        self.state["continuity_records"]["character_states"][name].append({
            "chapter_id": chapter_id,
            "timestamp": datetime.now().isoformat(),
            "snapshot": snapshot,
        })

    def add_timeline_event(self, chapter_id: int, event: str, timestamp_desc: str = ""):
        """添加时间线事件"""
        self.state["continuity_records"]["timeline"].append({
            "chapter_id": chapter_id,
            "event": event,
            "timestamp_desc": timestamp_desc,
        })

    def add_suspense_hook(self, chapter_id: int, hook: str, resolved: bool = False):
        """添加未解决的悬念钩子"""
        self.state["continuity_records"]["unresolved_hooks"].append({
            "chapter_id": chapter_id,
            "hook": hook[:300],
            "resolved": resolved,
        })

    def resolve_hook(self, hook_index: int):
        """标记一个悬念钩子已解决"""
        hooks = self.state["continuity_records"]["unresolved_hooks"]
        if 0 <= hook_index < len(hooks):
            hooks[hook_index]["resolved"] = True

    def update_props_inventory(self, prop_name: str, chapter_id: int, status: str):
        """更新道具清单"""
        self.state["continuity_records"]["props_inventory"][prop_name] = {
            "last_seen_chapter": chapter_id,
            "status": status,  # possessed / lost / destroyed / transferred
            "updated_at": datetime.now().isoformat(),
        }

    def get_continuity_context(self, max_hooks: int = 5) -> str:
        """
        生成连续性上下文摘要（供 Agent 的 system prompt 使用）。

        Returns:
            格式化的连续性上下文文本
        """
        records = self.state["continuity_records"]
        parts = []

        # 角色状态
        if records["character_states"]:
            parts.append("## 角色跨集状态")
            for name, snapshots in records["character_states"].items():
                if snapshots:
                    last = snapshots[-1]["snapshot"]
                    parts.append(f"- {name}: {json.dumps(last, ensure_ascii=False)}")

        # 未解决的钩子
        unresolved = [h for h in records["unresolved_hooks"] if not h["resolved"]]
        if unresolved:
            parts.append("\n## 未解决的悬念钩子")
            for i, h in enumerate(unresolved[-max_hooks:]):
                parts.append(f"- [{i}] 第{h['chapter_id']}章: {h['hook'][:200]}")

        return "\n".join(parts)

    # ═══════════════════════════════════════════════════════════
    # 事件时间线记录
    # ═══════════════════════════════════════════════════════════

    def get_timeline(self) -> list:
        """获取完整时间线"""
        return sorted(
            self.state["continuity_records"]["timeline"],
            key=lambda e: e["chapter_id"],
        )

    # ═══════════════════════════════════════════════════════════
    # 错误记录
    # ═══════════════════════════════════════════════════════════

    def log_error(self, phase: str, agent_name: str, error: str, context: dict = None):
        """记录管线执行中的错误"""
        self.state["errors"].append({
            "timestamp": datetime.now().isoformat(),
            "phase": phase,
            "agent_name": agent_name,
            "error": error[:1000],
            "context": context or {},
        })
        self._save()

    def get_errors(self, phase: str = None, limit: int = 20) -> list:
        """获取错误记录"""
        errors = self.state["errors"]
        if phase:
            errors = [e for e in errors if e["phase"] == phase]
        return errors[-limit:]

    # ═══════════════════════════════════════════════════════════
    # Resume / Reset
    # ═══════════════════════════════════════════════════════════

    def can_resume(self) -> bool:
        """检查是否可以从中断处恢复"""
        return self.state["current_phase"] != "idle" or len(self.state["phases_completed"]) > 0

    def get_resume_context(self) -> dict:
        """
        获取恢复执行所需的上下文。

        Returns:
            {current_phase, current_episode, last_agent_log, phases_completed, ...}
        """
        return {
            "current_phase": self.state["current_phase"],
            "current_episode": self.state["current_episode"],
            "phases_completed": self.state["phases_completed"],
            "last_agent_log": (
                self.state["agent_logs"][-1] if self.state["agent_logs"] else None
            ),
            "pending_episodes": {
                phase: info.get("episodes_in_progress", {})
                for phase, info in self.state["phases"].items()
            },
        }

    def reset(self, confirm: bool = False):
        """
        重置所有状态（危险操作）。

        Args:
            confirm: 必须显式确认为 True
        """
        if not confirm:
            raise ValueError("重置状态需要 confirm=True 显式确认")
        self._init_fresh()
        print("🔄 项目状态已重置")

    def reset_phase(self, phase: str):
        """重置单个阶段的进度（保留已完成阶段的数据）"""
        if phase in self.state["phases"]:
            self.state["phases"][phase] = {
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "episodes_completed": [],
                "episodes_in_progress": {},
            }
            if phase in self.state["phases_completed"]:
                self.state["phases_completed"].remove(phase)
            self._save()
            print(f"🔄 阶段 '{phase}' 已重置")

    # ═══════════════════════════════════════════════════════════
    # 统计与报告
    # ═══════════════════════════════════════════════════════════

    def get_progress_report(self) -> dict:
        """生成进度报告"""
        total_phases = len(self.state["phases"])
        completed = len(self.state["phases_completed"])
        in_progress = sum(
            1 for p in self.state["phases"].values() if p["status"] == "in_progress"
        )

        # 各集进度
        write_eps = self.state["phases"]["write"].get("episodes_completed", [])
        review_eps = self.state["phases"]["review"].get("episodes_completed", [])
        storyboard_eps = self.state["phases"]["storyboard"].get("episodes_completed", [])

        # 执行统计
        success_logs = [l for l in self.state["agent_logs"] if l["status"] == "success"]
        failed_logs = [l for l in self.state["agent_logs"] if l["status"] == "failed"]
        total_duration = sum(l["duration_seconds"] for l in self.state["agent_logs"])

        return {
            "project_name": self.project_name,
            "current_phase": self.state["current_phase"],
            "current_episode": self.state["current_episode"],
            "progress": f"{completed}/{total_phases} 阶段完成 ({in_progress} 进行中)",
            "phases_completed": self.state["phases_completed"],
            "episodes_written": len(write_eps),
            "episodes_reviewed": len(review_eps),
            "episodes_storyboarded": len(storyboard_eps),
            "total_agent_calls": len(self.state["agent_logs"]),
            "success_rate": (
                f"{len(success_logs) / max(len(self.state['agent_logs']), 1) * 100:.1f}%"
            ),
            "failed_calls": len(failed_logs),
            "total_agent_duration_seconds": round(total_duration, 1),
            "error_count": len(self.state["errors"]),
            "continuity_hooks_open": sum(
                1 for h in self.state["continuity_records"]["unresolved_hooks"]
                if not h["resolved"]
            ),
            "last_updated": self.state["updated_at"],
        }

    def print_progress(self):
        """打印可读的进度报告"""
        report = self.get_progress_report()
        print(f"\n{'='*50}")
        print(f"📊 项目进度: {report['project_name']}")
        print(f"{'='*50}")
        print(f"  阶段进度:    {report['progress']}")
        print(f"  当前阶段:    {report['current_phase']}")
        if report['current_episode']:
            print(f"  当前集数:    第{report['current_episode']}集")
        print(f"  已完成阶段:  {', '.join(report['phases_completed']) or '无'}")
        print(f"  已写集数:    {report['episodes_written']}")
        print(f"  已审核集数:  {report['episodes_reviewed']}")
        print(f"  已分镜集数:  {report['episodes_storyboarded']}")
        print(f"  Agent 调用:  {report['total_agent_calls']} 次 (成功率 {report['success_rate']})")
        print(f"  累计耗时:    {report['total_agent_duration_seconds']:.1f}s")
        print(f"  待解决钩子:  {report['continuity_hooks_open']}")
        print(f"  最后更新:    {report['last_updated']}")
        print(f"{'='*50}\n")


# ═══════════════════════════════════════════════════════════════
# 便捷工厂函数
# ═══════════════════════════════════════════════════════════════

def create_state_manager(
    project_name: str, output_dir: str = "./output", auto_resume: bool = True
) -> AgentStateManager:
    """
    创建或加载状态管理器。

    Args:
        project_name: 项目名称
        output_dir: 输出目录
        auto_resume: 是否自动恢复（如果有存档）

    Returns:
        AgentStateManager 实例
    """
    sm = AgentStateManager(project_name, output_dir)
    if auto_resume and sm.can_resume():
        ctx = sm.get_resume_context()
        print(f"🔄 检测到未完成的项目，当前阶段: {ctx['current_phase']}")
    return sm
