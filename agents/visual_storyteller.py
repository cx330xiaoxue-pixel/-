"""
视觉叙事 Agent — Phase 3: Show Don't Tell 审查

职责:
  - 审查剧本中的"告诉"式表达
  - 将内心独白/抽象描述转换为可拍的动作/表情/对白
  - 提供具体的视觉化重写建议
  - 增强剧本的影视感和可拍性

使用:
  agent = VisualStoryteller(config)
  result = agent.execute(script_elements=..., episode=1)
"""

from collections import Counter

from .base_agent import BaseAgent


class VisualStoryteller(BaseAgent):
    """视觉叙事 Agent — Show Don't Tell 审查与转换"""

    agent_name = "visual-storyteller"
    agent_display_name = "视觉叙事师"
    agent_description = "审查剧本的 Show Don't Tell 问题，将抽象描述转化为可拍的视觉语言"
    phase = "write"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from skills.script_writing import ScriptWritingSkill
        self.skill = ScriptWritingSkill()

    def execute(
        self,
        script_elements: list = None,
        script_path: str = None,
        episode: int = 1,
        state_manager=None,
        use_llm: bool = True,
        auto_fix: bool = False,
        **kwargs,
    ) -> dict:
        """
        执行 Show Don't Tell 审查。

        Args:
            script_elements: 剧本元素列表
            script_path: 剧本 YAML 文件路径（如果未提供 elements）
            episode: 集数
            state_manager: AgentStateManager 实例
            use_llm: 是否使用 LLM 增强
            auto_fix: 是否自动修复发现的问题

        Returns:
            {status, issues, fixes_applied, visual_score, suggestions}
        """
        self.state_manager = state_manager or self.state_manager

        # 加载剧本
        if script_elements is None and script_path:
            script_elements = self._load_elements_from_yaml(script_path)
        script_elements = script_elements or []

        self.log(f"审查第{episode}集: {len(script_elements)} 个元素")

        # Step 1: 规则审查
        self.log("规则审查...")
        rule_issues = self._rule_based_review(script_elements)

        # Step 2: LLM 增强审查
        llm_issues = []
        if use_llm:
            self.log("LLM 增强审查...")
            llm_issues = self._llm_enhanced_review(script_elements)

        # Step 3: 合并问题
        all_issues = self._deduplicate_issues(rule_issues + llm_issues)

        # Step 4: 计算视觉化评分
        visual_score = self._calculate_visual_score(
            script_elements, all_issues
        )

        # Step 5: 自动修复（如果启用）
        fixes_applied = 0
        if auto_fix and all_issues:
            self.log(f"自动修复 {len(all_issues)} 个问题...")
            script_elements, fixes_applied = self._auto_fix(
                script_elements, all_issues
            )

        # Step 6: 生成建议
        suggestions = self._generate_suggestions(all_issues, visual_score)

        # 总结报告
        severity_counts = Counter(i.get("severity", "low") for i in all_issues)
        self.log(
            f"审查完成: 视觉化评分 {visual_score}/10, "
            f"{len(all_issues)} 个问题 "
            f"(高{severity_counts.get('high', 0)} "
            f"中{severity_counts.get('medium', 0)} "
            f"低{severity_counts.get('low', 0)})"
        )

        return {
            "status": "completed",
            "episode": episode,
            "total_elements": len(script_elements),
            "issues_found": len(all_issues),
            "issues": all_issues,
            "fixes_applied": fixes_applied,
            "visual_score": visual_score,
            "suggestions": suggestions,
            "severity_breakdown": dict(severity_counts),
            "message": (
                f"视觉叙事审查完成: 视觉化评分 {visual_score}/10, "
                f"发现 {len(all_issues)} 个问题, "
                f"自动修复 {fixes_applied} 处"
            ),
        }

    # ═══════════════════════════════════════════════════════════
    # 规则审查
    # ═══════════════════════════════════════════════════════════

    def _rule_based_review(self, elements: list) -> list[dict]:
        """基于规则检测 Show Don't Tell 问题"""
        issues = []

        # 检测模式
        patterns = [
            # (正则, 严重度, 类别, 修复建议)
            (r'(\S+)感到很?(\S{1,3})', "medium", "直接陈述情感",
             "用角色的外部动作/表情替代，如「他握紧了拳头」"),
            (r'(\S+)的心中(?:暗想|想到|暗道|思索)', "high", "心理活动外露",
             "将内心活动转化为对白、画外音或象征性画面"),
            (r'(\S+)的(?:内心|心底|脑海)中?', "medium", "内心描写",
             "删去「内心/心底」等词，用具体画面呈现"),
            (r'(?:只见|但见|却见)\s*(\S)', "low", "网文视觉引导",
             "删去「只见」，直接描述画面内容"),
            (r'浑身上下|全身上下|周身上下', "low", "冗余身体描写",
             "简化为具体部位，如「他的手」「他的肩膀」"),
            (r'眼中闪过(?:一抹|一丝|一道)', "medium", "套话式眼神",
             "用更具体的眼神描写替代，如「他的眼睛亮了起来」"),
            (r'嘴角(?:扬起|浮现|掠过)(?:一抹|一丝)', "medium", "套话式微笑",
             "用更具体的面部表情替代"),
            (r'不由得|不禁|忍不住|情不自禁', "low", "冗余心理修饰",
             "直接描述动作，去掉心理修饰词"),
            (r'(?:显然是|明显是|分明是|无疑是)', "medium", "作者判断句",
             "删去判断词，通过画面本身让观众自己得出结论"),
            (r'(?:似乎|仿佛|好像|宛若)(?!.*\n)', "low", "模糊修辞",
             "在剧本中避免模糊修辞，给出明确的视觉指示"),
        ]

        for i, elem in enumerate(elements):
            text = elem.get("text", "")
            etype = elem.get("type", "")
            role = elem.get("role", "")

            for pattern, severity, category, fix_hint in patterns:
                for m in __import__('re').finditer(pattern, text):
                    issues.append({
                        "element_index": i,
                        "element_id": elem.get("element_id", str(i)),
                        "type": etype,
                        "role": role,
                        "text_preview": text[:100],
                        "match": m.group(0),
                        "category": category,
                        "severity": severity,
                        "fix_hint": fix_hint,
                        "source": "rule",
                    })

        return issues

    # ═══════════════════════════════════════════════════════════
    # LLM 增强审查
    # ═══════════════════════════════════════════════════════════

    def _llm_enhanced_review(self, elements: list) -> list[dict]:
        """使用 LLM 进行更深层的 Show Don't Tell 审查"""
        if not elements:
            return []

        # 选取样本（避免 token 过大）
        sample_size = min(30, len(elements))
        sample = elements[:sample_size]
        sample_text = "\n".join(
            f"[{e.get('type', '?')}] {e.get('role', '?')}: {e.get('text', '')[:120]}"
            for e in sample
        )

        prompt = f"""你是一位影视剧本编辑专家。请审查以下剧本片段中的 Show Don't Tell 问题。

剧本片段:
{sample_text}

请找出所有：
1. 直接陈述情感而非展示的（如"他很生气"→ 应该展示他做了什么事表现出愤怒）
2. 心理活动没有外化的（如"他心里想"→ 应该变成对白或动作）
3. 抽象描述无法拍摄的（如"气氛很紧张"→ 应该用具体的画面元素展示）
4. 网文套话和陈词滥调

输出 JSON 数组:
[
  {{
    "text_preview": "原文片段 (前50字)",
    "issue": "问题描述",
    "severity": "high|medium|low",
    "category": "情感陈述|心理外化|抽象描述|套话|其他",
    "rewrite_suggestion": "具体的重写建议（影视语言）"
  }}
]"""

        try:
            result = self.call_llm(prompt, use_light=False, expect_json=True)
            if isinstance(result, list):
                return [
                    {
                        "text_preview": item.get("text_preview", ""),
                        "category": item.get("category", ""),
                        "severity": item.get("severity", "low"),
                        "fix_hint": item.get("rewrite_suggestion", ""),
                        "source": "llm",
                    }
                    for item in result
                ]
        except Exception as e:
            self.log(f"LLM 审查失败: {e}", level="warning")

        return []

    # ═══════════════════════════════════════════════════════════

    def _deduplicate_issues(self, issues: list) -> list:
        """去重问题列表"""
        seen = set()
        unique = []
        for issue in issues:
            key = (issue.get("element_index", 0), issue.get("match", ""),
                   issue.get("category", ""))
            if key not in seen:
                seen.add(key)
                unique.append(issue)
        return unique

    def _calculate_visual_score(
        self, elements: list, issues: list
    ) -> float:
        """计算视觉化评分 (0-10)"""
        if not elements:
            return 0.0

        # 基础分
        base_score = 7.0

        # 问题扣分
        high_issues = sum(1 for i in issues if i.get("severity") == "high")
        med_issues = sum(1 for i in issues if i.get("severity") == "medium")
        low_issues = sum(1 for i in issues if i.get("severity") == "low")

        penalty = (
            high_issues * 0.5 +
            med_issues * 0.2 +
            low_issues * 0.05
        )
        # 按比例缩放
        penalty = penalty / max(len(elements), 1) * 10

        # 视觉标记加分
        visual_count = sum(
            1 for e in elements
            if e.get("visual_hint") or
            any(kw in e.get("text", "") for kw in
                ["镜头", "特写", "远景", "中景", "切至", "叠化", "POV"])
        )
        bonus = min(2.0, visual_count / max(len(elements), 1) * 10)

        return round(max(0, min(10, base_score + bonus - penalty)), 1)

    def _auto_fix(self, elements: list, issues: list) -> tuple:
        """自动修复检测到的问题"""
        fixes = 0

        for issue in issues:
            idx = issue.get("element_index", -1)
            if idx < 0 or idx >= len(elements):
                continue

            text = elements[idx].get("text", "")
            match = issue.get("match", "")
            fix_hint = issue.get("fix_hint", "")

            if match and match in text:
                # 简单替换策略
                converted = self.skill.convert_show_dont_tell(text)
                if converted["has_changes"]:
                    elements[idx]["text"] = converted["converted"]
                    elements[idx]["original_text"] = converted["original"]
                    elements[idx]["visual_reviewed"] = True
                    fixes += 1

        return elements, fixes

    def _generate_suggestions(
        self, issues: list, visual_score: float
    ) -> list[str]:
        """生成改进建议"""
        suggestions = []

        if visual_score < 5:
            suggestions.append("⚠️ 视觉化评分偏低，剧本可能过于依赖文字叙述，建议大幅增加可拍摄的视觉元素")
        elif visual_score < 7:
            suggestions.append("视觉化评分中等，仍有一些抽象描述需要转化为具体画面")

        # 分类统计
        categories = Counter(i.get("category", "") for i in issues)
        if categories.get("心理活动外露", 0) > 3:
            suggestions.append("存在较多未外化的心理活动，建议全部转化为对白或象征性画面")
        if categories.get("套话式眼神", 0) + categories.get("套话式微笑", 0) > 5:
            suggestions.append("面部表情描写有套话倾向，建议用更具体、独特的动作替代")
        if categories.get("直接陈述情感", 0) > 5:
            suggestions.append("直接陈述情感过多，请记住：观众看不到'愤怒'，只能看到愤怒的表现")

        if not suggestions:
            suggestions.append("剧本视觉化程度良好")

        return suggestions

    # ═══════════════════════════════════════════════════════════

    def _load_elements_from_yaml(self, path: str) -> list:
        """从 YAML 文件加载剧本元素"""
        try:
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                script = yaml.safe_load(f)

            elements = []
            for ch in script.get("script", {}).get("chapters", []):
                for scene in ch.get("scenes", []):
                    elements.extend(scene.get("elements", []))
            return elements
        except Exception as e:
            self.log(f"加载 YAML 失败: {e}", level="error")
            return []


def create_visual_storyteller(config: dict = None, **kwargs) -> VisualStoryteller:
    """创建视觉叙事 Agent 实例"""
    return VisualStoryteller(config=config, **kwargs)
