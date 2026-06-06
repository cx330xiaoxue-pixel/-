"""
情绪架构师 Agent — Phase 2: 情绪曲线设计 (~plan)

职责:
  - 设计全剧情绪曲线
  - 单集情绪节奏（紧张→释放→悬念）
  - 观众心理预期管理
  - 产出 planning/emotion-curve.md

使用:
  agent = EmotionArchitect(config)
  result = agent.execute(episode_plan=..., emotion_curves=...)
"""

import os
from datetime import datetime

from .base_agent import BaseAgent


class EmotionArchitect(BaseAgent):
    """情绪架构师 Agent — 全剧情绪曲线设计与观众心理管理"""

    agent_name = "emotion-architect"
    agent_display_name = "情绪架构师"
    agent_description = "设计全剧情绪曲线、单集情绪节奏，管理观众心理预期"
    phase = "plan"

    def execute(
        self,
        episode_plan: list[dict] = None,
        emotion_curves: list[dict] = None,
        all_elements: list = None,
        hooks: dict = None,
        series_structure: dict = None,
        state_manager=None,
        use_llm: bool = True,
        **kwargs,
    ) -> dict:
        """
        设计全剧情绪曲线。

        Args:
            episode_plan: 分集规划（来自 episode_architect）
            emotion_curves: 初步情绪曲线（来自 EpisodePlanningSkill）
            all_elements: 所有结构化元素
            hooks: 悬念钩子
            series_structure: 全剧结构
            state_manager: AgentStateManager 实例
            use_llm: 是否使用 LLM

        Returns:
            {status, emotion_report_path, series_emotion, per_episode_rhythm, ...}
        """
        self.state_manager = state_manager or self.state_manager
        episode_plan = episode_plan or []
        emotion_curves = emotion_curves or []

        self.log(f"设计全剧情绪曲线: {len(episode_plan)} 集")

        # Step 1: 全剧情绪走向分析
        self.log("分析全剧情绪走向...")
        series_emotion = self._analyze_series_emotion(emotion_curves, series_structure)

        # Step 2: 单集情绪节奏细化
        self.log("细化单集情绪节奏...")
        per_episode_rhythm = self._design_per_episode_rhythm(
            episode_plan, emotion_curves, all_elements
        )

        # Step 3: 观众心理旅程设计
        self.log("设计观众心理旅程...")
        audience_journey = self._design_audience_journey(
            episode_plan, emotion_curves, use_llm=use_llm
        )

        # Step 4: 情绪冲突设计
        self.log("设计情绪冲突对位...")
        emotional_counterpoint = self._design_emotional_counterpoint(
            episode_plan, emotion_curves
        )

        # Step 5: 生成报告
        title = self.state_manager.project_name if self.state_manager else "未命名"
        report = self._generate_report(
            title=title,
            series_emotion=series_emotion,
            per_episode_rhythm=per_episode_rhythm,
            audience_journey=audience_journey,
            emotional_counterpoint=emotional_counterpoint,
        )

        # 保存
        output_dir = self.get_config("output.output_dir", "./output")
        full_output_dir = os.path.join(
            output_dir,
            self.state_manager.project_name if self.state_manager else title,
        )
        os.makedirs(os.path.join(full_output_dir, "planning"), exist_ok=True)
        report_path = os.path.join(full_output_dir, "planning", "emotion-curve.md")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        self.save_state("last_emotion_design", {
            "timestamp": datetime.now().isoformat(),
            "episode_count": len(episode_plan),
            "overall_tone": series_emotion.get("overall_tone", ""),
        })

        self.log(f"情绪曲线设计完成: 主调 {series_emotion.get('overall_tone', '未知')}")

        return {
            "status": "completed",
            "emotion_report_path": report_path,
            "series_emotion": series_emotion,
            "per_episode_rhythm": per_episode_rhythm,
            "audience_journey": audience_journey,
            "message": (
                f"情绪曲线设计完成: {len(episode_plan)} 集, "
                f"全剧主调: {series_emotion.get('overall_tone', '未知')}"
            ),
        }

    # ═══════════════════════════════════════════════════════════

    def _analyze_series_emotion(
        self, emotion_curves: list[dict], series_structure: dict = None
    ) -> dict:
        """分析全剧情绪走向"""
        if not emotion_curves:
            return {"overall_tone": "未确定", "arc_type": "未知"}

        # 计算全剧平均情绪
        all_peaks = [c.get("peak_value", 5) for c in emotion_curves]
        all_valleys = [c.get("valley_value", 3) for c in emotion_curves]

        avg_peak = sum(all_peaks) / len(all_peaks)
        avg_valley = sum(all_valleys) / len(all_valleys)
        dynamic_range = avg_peak - avg_valley

        # 推断弧线类型
        first_half_peaks = all_peaks[:len(all_peaks)//2]
        second_half_peaks = all_peaks[len(all_peaks)//2:]
        first_avg = sum(first_half_peaks) / max(len(first_half_peaks), 1)
        second_avg = sum(second_half_peaks) / max(len(second_half_peaks), 1)

        if second_avg > first_avg + 1:
            arc_type = "上升型 — 高潮在结尾，情绪累积上扬"
        elif first_avg > second_avg + 1:
            arc_type = "下降型 — 开场即高潮，情绪逐渐沉入深层"
        elif dynamic_range > 4:
            arc_type = "振荡型 — 情绪大幅度起伏，高潮与低谷交替"
        else:
            arc_type = "平稳型 — 情绪保持在较窄的波动范围内"

        # 主调
        if avg_peak > 7:
            overall_tone = "激昂热血"
        elif avg_valley < 4:
            overall_tone = "深沉压抑"
        elif 4 <= avg_peak <= 7:
            overall_tone = "温暖治愈"
        else:
            overall_tone = "均衡中性"

        return {
            "overall_tone": overall_tone,
            "arc_type": arc_type,
            "avg_peak": round(avg_peak, 1),
            "avg_valley": round(avg_valley, 1),
            "dynamic_range": round(dynamic_range, 1),
            "peak_episode": all_peaks.index(max(all_peaks)) + 1,
            "valley_episode": all_valleys.index(min(all_valleys)) + 1,
        }

    def _design_per_episode_rhythm(
        self,
        episode_plan: list[dict],
        emotion_curves: list[dict],
        all_elements: list = None,
    ) -> list[dict]:
        """为每集设计详细情绪节奏"""
        rhythms = []

        # 构建曲线查找表
        curve_map = {c["episode_id"]: c for c in emotion_curves}

        for ep in episode_plan:
            ep_id = ep["episode_id"]
            curve = curve_map.get(ep_id, {})

            # 将情绪序列分段映射到荧幕
            seq = curve.get("emotion_sequence", [])
            if len(seq) >= 4:
                beats = {
                    "opening": seq[:len(seq)//4],        # 开场
                    "act1": seq[len(seq)//4:len(seq)//2],  # 第一幕
                    "act2": seq[len(seq)//2:3*len(seq)//4], # 第二幕
                    "climax": seq[3*len(seq)//4:],         # 高潮/结尾
                }
            else:
                beats = {"opening": seq, "act1": [], "act2": [], "climax": []}

            avg_per_beat = {
                beat: round(sum(vals) / max(len(vals), 1), 1)
                for beat, vals in beats.items()
                if vals
            }

            rhythms.append({
                "episode_id": ep_id,
                "beats": beats,
                "avg_intensity": avg_per_beat,
                "peak": curve.get("peak_value", 5),
                "valley": curve.get("valley_value", 3),
                "rhythm_description": self._describe_rhythm(avg_per_beat),
            })

        return rhythms

    def _describe_rhythm(self, beats: dict) -> str:
        """描述情绪节奏模式"""
        if not beats:
            return "未知"
        opening = beats.get("opening", 5)
        climax = beats.get("climax", 5)
        if climax > opening + 1.5:
            return "渐进上升 — 从平静开场逐步推至高潮"
        elif opening > climax + 1.5:
            return "高开低走 — 开场震撼，逐步收敛至情感落点"
        elif beats.get("act2", 5) > max(opening, climax):
            return "中间爆发 — 第二幕为情绪核心，首尾较为平稳"
        else:
            return "均匀分布 — 情绪在各幕之间均匀展开"

    def _design_audience_journey(
        self,
        episode_plan: list[dict],
        emotion_curves: list[dict],
        use_llm: bool = True,
    ) -> dict:
        """设计观众心理旅程"""
        journey = {
            "opening_hook_strategy": "前三集必须建立世界观并抛出核心悬念",
            "episode3_checkpoint": "第3集结尾留第一个强力悬念，确保观众继续追看",
            "mid_season_slump": "中段可能出现审美疲劳，需要新鲜刺激",
            "finale_build_up": "最后三集逐步收线，每集解决一个次要冲突",
        }

        if use_llm and len(episode_plan) >= 3:
            total = len(episode_plan)
            prompt = f"""你是一位观众心理学专家。为一部 {total} 集的电视剧设计观众心理管理策略。

请考虑:
- 前3集如何钩住观众
- 第3-8集如何深化投入
- 中段如何防止流失
- 最后阶段如何推向高潮

输出 JSON:
{{
  "hook_phase": "0-3集: 策略描述",
  "investment_phase": "4-8集: 策略描述",
  "mid_season_strategy": "中段: 策略描述",
  "finale_strategy": "最后阶段: 策略描述",
  "retention_mechanisms": ["机制1", "机制2", ...],
  "emotional_payoff_design": "情感回报设计",
  "rewatch_incentive": "二刷激励点"
}}"""

            try:
                result = self.call_llm(prompt, use_light=False, expect_json=True)
                if isinstance(result, dict):
                    journey.update(result)
            except Exception as e:
                self.log(f"LLM 观众旅程设计失败: {e}", level="warning")

        return journey

    def _design_emotional_counterpoint(
        self,
        episode_plan: list[dict],
        emotion_curves: list[dict],
    ) -> list[dict]:
        """
        设计情绪对位 —— 在紧张场景中安排舒缓时刻，反之亦然。
        这是专业剧本的标志性技巧。
        """
        counterpoints = []

        for ep in episode_plan:
            ep_id = ep["episode_id"]
            curve = next(
                (c for c in emotion_curves if c["episode_id"] == ep_id), {}
            )
            seq = curve.get("emotion_sequence", [])

            counterpoint_moments = []
            for i in range(1, len(seq)):
                # 检测情绪突变（相邻值差距 > 3）
                if abs(seq[i] - seq[i-1]) > 3:
                    moment_type = (
                        "紧张中的喘息" if seq[i] < seq[i-1]
                        else "平静中的爆发"
                    )
                    counterpoint_moments.append({
                        "position": i + 1,
                        "type": moment_type,
                        "from_intensity": seq[i-1],
                        "to_intensity": seq[i],
                    })

            counterpoints.append({
                "episode_id": ep_id,
                "counterpoint_moments": counterpoint_moments,
                "count": len(counterpoint_moments),
                "quality": (
                    "丰富" if len(counterpoint_moments) >= 3
                    else "适中" if len(counterpoint_moments) >= 1
                    else "缺乏 — 建议增加情绪对比"
                ),
            })

        return counterpoints

    # ═══════════════════════════════════════════════════════════

    def _generate_report(
        self,
        title: str,
        series_emotion: dict,
        per_episode_rhythm: list,
        audience_journey: dict,
        emotional_counterpoint: list,
    ) -> str:
        """生成情绪曲线报告 (Markdown)"""
        report = []
        report.append(f"# 情绪曲线设计报告 — 《{title}》\n")
        report.append(f"**分析工具**: Novel-to-Script Pro v2.0 — Emotion Architect")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        report.append("---\n")

        # 全剧情绪总览
        report.append("## 1. 全剧情绪总览\n")
        report.append(f"- **情绪主调**: {series_emotion.get('overall_tone', '未知')}")
        report.append(f"- **弧线类型**: {series_emotion.get('arc_type', '未知')}")
        report.append(f"- **平均峰值**: {series_emotion.get('avg_peak', '?')}/10")
        report.append(f"- **平均谷值**: {series_emotion.get('avg_valley', '?')}/10")
        report.append(f"- **动态范围**: {series_emotion.get('dynamic_range', '?')}")
        report.append(f"- **情绪峰值集**: 第{series_emotion.get('peak_episode', '?')}集")
        report.append(f"- **情绪低谷集**: 第{series_emotion.get('valley_episode', '?')}集")

        report.append("\n---\n")

        # 单集情绪节奏
        report.append("## 2. 逐集情绪节奏\n")
        for rhythm in per_episode_rhythm[:20]:  # 最多显示20集
            ep_id = rhythm["episode_id"]
            report.append(f"### 第{ep_id}集")
            report.append(f"- **节奏模式**: {rhythm.get('rhythm_description', '未知')}")
            report.append(f"- **峰值强度**: {rhythm.get('peak', '?')}")
            report.append(f"- **谷值强度**: {rhythm.get('valley', '?')}")
            avg = rhythm.get("avg_intensity", {})
            report.append(f"- **各幕平均**: "
                         f"开场 {avg.get('opening', '?')} | "
                         f"Act1 {avg.get('act1', '?')} | "
                         f"Act2 {avg.get('act2', '?')} | "
                         f"高潮 {avg.get('climax', '?')}")
            report.append("")

        report.append("---\n")

        # 情绪对位
        report.append("## 3. 情绪对位分析\n")
        for cp in emotional_counterpoint[:15]:
            ep_id = cp["episode_id"]
            quality = cp.get("quality", "")
            moments = cp.get("counterpoint_moments", [])
            report.append(f"### 第{ep_id}集 — 情绪对位: {quality}")
            for m in moments:
                report.append(f"- 位置{m['position']}: {m['type']} "
                             f"({m['from_intensity']}→{m['to_intensity']})")
            report.append("")

        report.append("---\n")

        # 观众心理旅程
        report.append("## 4. 观众心理旅程设计\n")
        for key, value in audience_journey.items():
            if isinstance(value, list):
                report.append(f"### {key}")
                for item in value:
                    report.append(f"- {item}")
            else:
                report.append(f"- **{key}**: {value}")
            report.append("")

        return "\n".join(report)


def create_emotion_architect(config: dict = None, **kwargs) -> EmotionArchitect:
    """创建情绪架构师 Agent 实例"""
    return EmotionArchitect(config=config, **kwargs)
