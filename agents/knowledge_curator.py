"""
知识管理者 Agent — Phase 0: 知识收编 (~ingest)

职责:
  - 扫描 sources/ 目录中的原始材料
  - 提取关键术语、世界观设定、人物关系
  - 通过 LLM 增强知识提取质量
  - 更新 knowledge/source_registry.md
  - 产出术语表、世界观摘要

使用:
  agent = KnowledgeCurator(config)
  result = agent.execute(source_dir="./sample_novel/")
"""

import os
from datetime import datetime
from typing import Any

from .base_agent import BaseAgent


class KnowledgeCurator(BaseAgent):
    """知识管理者 Agent — 负责源材料的收编与知识结构化"""

    agent_name = "knowledge-curator"
    agent_display_name = "知识管理者"
    agent_description = "负责扫描源材料，提取专有术语、世界观规则、人物关系，并维护知识注册表"
    phase = "ingest"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # 延迟导入避免循环依赖
        from skills.knowledge_curation import KnowledgeCurationSkill
        self.skill = KnowledgeCurationSkill(
            sources_dir=self.get_config("knowledge.sources_dir", "./sources"),
            output_dir=self.get_config("knowledge.output_dir", "./knowledge"),
        )

    def execute(
        self,
        source_dir: str = None,
        state_manager=None,
        use_llm: bool = True,
        **kwargs,
    ) -> dict:
        """
        执行知识收编流程。

        Args:
            source_dir: 源材料目录（覆盖默认值）
            state_manager: AgentStateManager 实例
            use_llm: 是否使用 LLM 增强（术语分类、规则归纳）

        Returns:
            {status, terms_count, rules_count, registry_path, summary, ...}
        """
        self.state_manager = state_manager or self.state_manager
        source_dir = source_dir or self.skill.sources_dir

        self.log(f"开始扫描源目录: {source_dir}")

        if not os.path.isdir(source_dir):
            return {
                "status": "failed",
                "error": f"源目录不存在: {source_dir}",
            }

        # Step 1: 规则扫描（离线，快）
        self.log("Step 1/4: 规则扫描源文件...")
        scan_result = self.skill.scan_source_directory(source_dir)

        if scan_result["file_count"] == 0:
            return {
                "status": "failed",
                "error": f"源目录中没有 .txt/.md 文件: {source_dir}",
            }

        self.log(
            f"扫描完成: {scan_result['file_count']} 文件, "
            f"{len(scan_result['terms'])} 术语, "
            f"{len(scan_result['rules'])} 规则"
        )

        # Step 2: LLM 增强分类（可选）
        if use_llm and scan_result["terms"]:
            self.log("Step 2/4: LLM 增强术语分类...")
            scan_result = self._llm_enhance_terms(scan_result)

        # Step 3: LLM 提取世界观摘要
        world_summary = ""
        if use_llm and scan_result["rules"]:
            self.log("Step 3/4: LLM 生成世界观摘要...")
            world_summary = self._llm_generate_world_summary(scan_result)

        # Step 4: 更新注册表
        self.log("Step 4/4: 更新知识注册表...")
        registry_path = self.skill.update_registry(
            terms=scan_result["terms"],
            rules=scan_result["rules"],
            graph=scan_result["graph"],
            source_name=os.path.basename(source_dir),
        )

        # 生成摘要
        summary = self.skill.generate_summary(scan_result)

        # 保存到 état
        self.save_state("last_scan", {
            "source_dir": source_dir,
            "timestamp": datetime.now().isoformat(),
            "terms_count": len(scan_result["terms"]),
            "rules_count": len(scan_result["rules"]),
            "file_count": scan_result["file_count"],
        })

        self.log(
            f"知识收编完成: {len(scan_result['terms'])} 术语, "
            f"{len(scan_result['rules'])} 规则, "
            f"注册表: {registry_path}"
        )

        return {
            "status": "completed",
            "source_dir": source_dir,
            "terms_count": len(scan_result["terms"]),
            "rules_count": len(scan_result["rules"]),
            "file_count": scan_result["file_count"],
            "total_chars": scan_result["total_chars"],
            "registry_path": registry_path,
            "summary": summary,
            "world_summary": world_summary,
            "graph_nodes": len(scan_result["graph"]["nodes"]),
            "graph_edges": len(scan_result["graph"]["edges"]),
            "message": (
                f"知识收编完成：扫描 {scan_result['file_count']} 个文件，"
                f"提取 {len(scan_result['terms'])} 个术语，"
                f"{len(scan_result['rules'])} 条世界观规则"
            ),
        }

    # ═══════════════════════════════════════════════════════════
    # LLM 增强方法
    # ═══════════════════════════════════════════════════════════

    def _llm_enhance_terms(self, scan_result: dict) -> dict:
        """使用 LLM 对术语进行重新分类和补充描述"""
        # 取前 50 个高频术语让 LLM 分类
        sorted_terms = sorted(
            scan_result["terms"].items(),
            key=lambda x: -x[1]["frequency"],
        )[:50]

        term_list = "\n".join(
            f"- {term} (规则分类: {info['category']}, 出现 {info['frequency']} 次)"
            for term, info in sorted_terms
        )

        prompt = f"""请分析以下小说中的专有术语，进行更精细的分类。

每个术语请输出:
- 精确分类: character(角色)/location(地点)/organization(组织)/technique(功法/技能)/item(道具/物品)/concept(概念/规则)/realm(境界/等级)/event(事件)/title(称号)
- 简要说明 (20字以内)
- 重要性评分 (1-5)

术语列表:
{term_list}

请输出 JSON 数组:
[{{"term": "术语名", "refined_category": "精确分类", "description": "简要说明", "importance": 1-5}}]"""

        try:
            enhanced = self.call_llm(prompt, use_light=True, expect_json=True)
            if isinstance(enhanced, list):
                for item in enhanced:
                    term = item.get("term", "")
                    if term in scan_result["terms"]:
                        scan_result["terms"][term]["refined_category"] = item.get(
                            "refined_category", ""
                        )
                        scan_result["terms"][term]["description"] = item.get(
                            "description", ""
                        )
                        scan_result["terms"][term]["importance"] = item.get(
                            "importance", 3
                        )
        except Exception as e:
            self.log(f"LLM 术语增强失败（使用规则分类）: {e}", level="warning")

        return scan_result

    def _llm_generate_world_summary(self, scan_result: dict) -> str:
        """使用 LLM 生成世界观摘要"""
        # 整理规则
        rules_text = "\n".join(
            f"- [{r['category']}] {r['rule'][:200]}"
            for r in scan_result["rules"][:30]
        )
        # 整理术语
        terms_text = "\n".join(
            f"- {term} [{info.get('refined_category', info['category'])}]: "
            f"{info.get('description', '')}"
            for term, info in sorted(
                scan_result["terms"].items(),
                key=lambda x: -x[1]["frequency"],
            )[:30]
        )

        prompt = f"""请基于以下提取的术语和规则，撰写一段 300-500 字的世界观摘要。

要求：
1. 概括这个世界的核心特征（武侠/仙侠/科幻/都市/历史等）
2. 描述力量体系或核心规则
3. 说明主要势力或组织分布
4. 指出最独特的设定亮点

术语:
{terms_text}

规则:
{rules_text}"""

        try:
            summary = self.ask_llm(prompt)
            return summary if summary else ""
        except Exception as e:
            self.log(f"LLM 世界观摘要生成失败: {e}", level="warning")
            return ""


# ═══════════════════════════════════════════════════════════════
# 便捷工厂
# ═══════════════════════════════════════════════════════════════

def create_knowledge_curator(config: dict = None, **kwargs) -> KnowledgeCurator:
    """创建知识管理者 Agent 实例"""
    return KnowledgeCurator(config=config, **kwargs)
