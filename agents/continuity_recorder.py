"""
连续性记录 Agent — Phase 4: 跨集一致性检查

职责:
  - 跨集一致性检查：人物称呼、道具状态、时间线、地点
  - 更新项目级记忆（.agent-state.json 中的 continuity_records）
  - 产出 review/continuity-ep{N:02d}.md

使用:
  agent = ContinuityRecorder(config)
  result = agent.execute(episode=1, script_elements=...)
"""

import os
from datetime import datetime

from .base_agent import BaseAgent


class ContinuityRecorder(BaseAgent):
    """连续性记录 Agent — 跨集一致性的守护者"""

    agent_name = "continuity-recorder"
    agent_display_name = "连续性记录员"
    agent_description = "检查跨集一致性，更新项目记忆，确保前后不矛盾"
    phase = "review"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from skills.review_skills import ContinuityRecordSkill
        self.skill = ContinuityRecordSkill()

    def execute(
        self,
        episode: int = 1,
        script_elements: list = None,
        script_path: str = None,
        state_manager=None,
        **kwargs,
    ) -> dict:
        """
        执行连续性检查并更新记录。

        Args:
            episode: 当前集数
            script_elements: 剧本元素
            script_path: 剧本路径
            state_manager: AgentStateManager

        Returns:
            {status, issues, updates, report_path}
        """
        self.state_manager = state_manager or self.state_manager

        # 加载
        if script_elements is None and script_path:
            script_elements = self._load_elements(script_path)
        script_elements = script_elements or []

        self.log(f"连续性检查第{episode}集: {len(script_elements)} 个元素")

        # 获取之前的连续性记录
        previous_records = (
            self.state_manager.state.get("continuity_records", {})
            if self.state_manager else {}
        )

        # 执行检查
        result = self.skill.check_continuity(
            current_elements=script_elements,
            previous_records=previous_records,
            current_episode=episode,
        )

        # 更新记录
        if self.state_manager:
            updated_records = self.skill.update_records(
                records=previous_records,
                current_elements=script_elements,
                episode=episode,
                updates=result.get("updates", {}),
            )
            self.state_manager.state["continuity_records"] = updated_records
            self.state_manager._save()

            # 同时更新 StateManager 的内置记录
            for role in result.get("current_roles", []):
                snapshot = {
                    "status": "active",
                    "location": "",
                    "emotion": "",
                }
                for e in script_elements:
                    if e.get("role") == role:
                        snapshot["emotion"] = e.get("emotion", "")
                        break
                self.state_manager.update_character_state(role, episode, snapshot)

            # 添加时间线事件
            for tm in result.get("time_mentions", []):
                self.state_manager.add_timeline_event(
                    episode, tm.get("text", ""), tm.get("keyword", "")
                )

        # 生成报告
        report = self._generate_report(episode=episode, result=result)

        # 保存报告
        output_dir = self.get_config("output.output_dir", "./output")
        project_name = self.state_manager.project_name if self.state_manager else "untitled"
        full_output_dir = os.path.join(output_dir, project_name)
        os.makedirs(os.path.join(full_output_dir, "review"), exist_ok=True)
        report_path = os.path.join(
            full_output_dir, "review", f"continuity-ep{episode:02d}.md"
        )

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        self.log(
            f"连续性检查完成: {len(result.get('issues', []))} 个问题, "
            f"{len(result.get('current_roles', []))} 个角色, "
            f"{len(result.get('current_props', []))} 个道具"
        )

        return {
            "status": "completed",
            "episode": episode,
            "issues": result.get("issues", []),
            "issue_count": len(result.get("issues", [])),
            "updates": result.get("updates", {}),
            "current_roles": result.get("current_roles", []),
            "current_props": result.get("current_props", []),
            "report_path": report_path,
            "message": result.get("summary", "连续性检查完成"),
        }

    def _load_elements(self, path: str) -> list:
        try:
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                script = yaml.safe_load(f)
            elements = []
            for ch in script.get("script", {}).get("chapters", []):
                for scene in ch.get("scenes", []):
                    elements.extend(scene.get("elements", []))
            return elements
        except Exception:
            return []

    def init_new_project(self):
        """为新项目初始化连续性记录"""
        if self.state_manager:
            self.state_manager.state["continuity_records"] = {
                "character_states": {},
                "props_inventory": {},
                "timeline": [],
                "unresolved_hooks": [],
                "location_states": {},
            }
            self.state_manager._save()
            self.log("已初始化全新连续性记录")

    def get_full_records(self) -> dict:
        """获取完整连续性记录"""
        if self.state_manager:
            return self.state_manager.state.get("continuity_records", {})
        return {}

    def print_continuity_summary(self):
        """打印连续性摘要"""
        records = self.get_full_records()
        chars = records.get("character_states", {})
        props = records.get("props_inventory", {})
        timeline = records.get("timeline", [])
        hooks = records.get("unresolved_hooks", [])

        print(f"\n{'='*40}")
        print(f"📋 连续性记录摘要")
        print(f"{'='*40}")
        print(f"  角色: {len(chars)} 个")
        print(f"  道具: {len(props)} 个")
        print(f"  时间线事件: {len(timeline)}")
        print(f"  未解悬念: {sum(1 for h in hooks if not h.get('resolved', False))}")
        print(f"{'='*40}\n")

    def _generate_report(
        self, episode: int, result: dict
    ) -> str:
        """生成连续性报告"""
        report = []
        report.append(f"# 连续性检查报告 — 第{episode}集\n")
        report.append(f"**检查时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append(f"**出场角色**: {len(result.get('current_roles', []))} 个")
        report.append(f"**涉及道具**: {len(result.get('current_props', []))} 个\n")

        issues = result.get("issues", [])
        if issues:
            report.append(f"## ⚠️ 发现 {len(issues)} 个一致性问题\n")
            for i, issue in enumerate(issues, 1):
                severity = issue.get("severity", "?")
                icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")
                report.append(f"{i}. {icon} **[{issue.get('type', '?')}]** "
                             f"{issue.get('description', '')}")
        else:
            report.append("## ✅ 未发现一致性问题\n")

        # 更新摘要
        updates = result.get("updates", {})
        if updates.get("new_characters"):
            report.append(f"\n### 新角色首次出场\n")
            for name in updates["new_characters"]:
                report.append(f"- {name}")
            report.append("")

        # 角色状态
        report.append(f"\n### 角色状态快照\n")
        for role in result.get("current_roles", [])[:20]:
            report.append(f"- {role}")

        report.append(f"\n### 道具清单\n")
        for prop in sorted(result.get("current_props", []))[:30]:
            report.append(f"- {prop}")

        return "\n".join(report)


def create_continuity_recorder(config: dict = None, **kwargs) -> ContinuityRecorder:
    return ContinuityRecorder(config=config, **kwargs)
