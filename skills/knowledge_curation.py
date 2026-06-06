"""
知识管理 Skill — 术语提取、世界观规则归纳、关系图谱构建、知识注册表管理

可被 knowledge-curator Agent 和其他 Agent 复用的核心技能。
"""

import json
import os
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional


class KnowledgeCurationSkill:
    """知识管理核心技能——纯逻辑层，不依赖 LLM"""

    def __init__(self, sources_dir: str = "./sources", output_dir: str = "./knowledge"):
        self.sources_dir = sources_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    # ═══════════════════════════════════════════════════════════
    # 术语提取（规则 + 统计）
    # ═══════════════════════════════════════════════════════════

    def extract_terms(self, text: str, min_frequency: int = 2) -> dict:
        """
        从文本中提取专有术语。

        识别：
        - 书名号包裹的专有名词《》
        - 引号强调的术语
        - 首字母大写的复合词（英文）
        - 高频出现的 2-4 字中文短语
        - 数字 + 量词组合（功法等级、境界）

        Args:
            text: 原始文本
            min_frequency: 最低出现频次

        Returns:
            {term: {category, frequency, contexts, first_appearance}}
        """
        terms = {}

        # 规则1: 《》书名号（功法、秘籍、书名）
        for m in re.finditer(r'《([^》]+)》', text):
            term = m.group(1)
            self._add_term(terms, term, "technique_or_book",
                          text[max(0, m.start()-20):m.end()+20])

        # 规则2: "" 或 '' 强调短语（3-8字）
        for m in re.finditer(r'["“]([^"”]{3,10})["”]', text):
            term = m.group(1)
            if not re.search(r'[，。！？、；：]', term):
                self._add_term(terms, term, "emphasized_term",
                              text[max(0, m.start()-20):m.end()+20])

        # 规则3: 境界/等级模式（X品/阶/级/重/层/星 + 名词）
        realm_patterns = [
            r'(?:踏入|突破|达到|晋升|已是)\s*(\S{1,6}(?:品|阶|级|重|层|星|段))',
            r'(\S{1,4}(?:境|界|期))(?:\s|，|。)',
        ]
        for pattern in realm_patterns:
            for m in re.finditer(pattern, text):
                term = m.group(1).strip()
                self._add_term(terms, term, "realm_or_level",
                              text[max(0, m.start()-20):m.end()+20])

        # 规则4: 地名模式（X山/城/谷/派/门/宫/阁/殿/府/岛/域/国）
        place_pattern = r'(\S{1,4}(?:山|城|谷|派|门|宫|阁|殿|府|岛|域|国|堂|庄|堡|楼|塔|湖|海|林|峰|渊|崖|洞|寺|庙|观|院|坊|街|镇|村|寨|岭))'
        for m in re.finditer(place_pattern, text):
            term = m.group(1)
            if len(term) >= 2 and term not in ["一座山", "这座城", "那座塔"]:
                self._add_term(terms, term, "location",
                              text[max(0, m.start()-20):m.end()+20])

        # 规则5: 人名模式（2-4字中文名 + 称谓后缀）
        name_suffixes = r'(?:道长|大师|前辈|少侠|大侠|掌门|长老|护法|堂主|帮主|教主|宗师|散人|真人|上人|尊者|仙子|圣女|魔头|老魔|妖王|鬼王)'
        for m in re.finditer(r'(\S{1,4})' + name_suffixes, text):
            name = m.group(1)
            if len(name) <= 4 and not re.search(r'[的地得了着过]', name):
                self._add_term(terms, name, "character_title",
                              text[max(0, m.start()-20):m.end()+20])

        # 规则6: 道具/法器模式
        item_patterns = [
            (r'(?:祭出|拿出|掏出|拔出|挥动|握紧|举起|掷出)\s*(\S{2,8}(?:剑|刀|枪|棍|鞭|戟|斧|钩|叉|锤|扇|针|镜|印|符|鼎|炉|幡|旗|环|珠|玉|石|环|索|绫|伞|琴|箫|笛|鼓|钟))', "weapon_or_artifact"),
        ]
        for pattern, category in item_patterns:
            for m in re.finditer(pattern, text):
                term = m.group(1).strip()
                self._add_term(terms, term, category,
                              text[max(0, m.start()-20):m.end()+20])

        # 过滤低频
        terms = {k: v for k, v in terms.items()
                 if v["frequency"] >= min_frequency and len(k) >= 2}
        return terms

    def _add_term(self, terms: dict, term: str, category: str, context: str):
        """向术语字典中添加或更新术语"""
        if term not in terms:
            terms[term] = {
                "category": category,
                "frequency": 0,
                "contexts": [],
                "first_appearance": context[:200],
            }
        terms[term]["frequency"] += 1
        if len(terms[term]["contexts"]) < 3:
            terms[term]["contexts"].append(context[:200])

    # ═══════════════════════════════════════════════════════════
    # 世界观规则归纳
    # ═══════════════════════════════════════════════════════════

    def extract_world_rules(self, text: str) -> list[dict]:
        """
        从文本中提取世界观规则。

        识别模式：
        - "在X世界中，Y是Z"
        - "X的规则是Y"
        - 因果陈述（因为…所以 / 一旦…就会）
        - 条件假设（如果…则 / 若…则）
        - 等级体系描述

        Returns:
            [{rule, category, confidence, evidence}]
        """
        rules = []

        # 显式规则陈述
        explicit_patterns = [
            (r'(?:在|于)(?:这|那)?(?:个|片)?[一-鿿]{2,20}(?:中|里|之中|之内)\s*[一-鿿，；]+(?:。|；)', "world_rule"),
            (r'(?:因为|由于)[^。]{5,50}(?:所以|因此|于是)[^。]{5,50}', "causality"),
            (r'(?:如果|若是|倘若|假如|一旦)[^。]{5,50}(?:那么|就|便会|则会|定会)[^。]{5,50}', "conditional"),
            (r'(?:每|每隔|每当)[^。]{5,50}(?:就会|便会|都会|必须)[^。]{5,50}', "recurring_rule"),
        ]

        for pattern, category in explicit_patterns:
            for m in re.finditer(pattern, text):
                rule_text = m.group(0).strip()
                rules.append({
                    "rule": rule_text[:300],
                    "category": category,
                    "confidence": 0.7,
                    "evidence": rule_text[:200],
                })

        # 等级体系描述
        level_patterns = [
            r'(?:分为|共分|划分)\s*(\S{2,4}(?:\s*[、，,]\s*\S{2,4}){2,})',
            r'(?:从低到高|从下到上|依次为)[：:]?\s*(\S{2,4}(?:\s*[、，,]\s*\S{2,4}){2,})',
        ]
        for pattern in level_patterns:
            for m in re.finditer(pattern, text):
                rule_text = m.group(0).strip()
                levels = re.split(r'[、，,]', m.group(1)) if m.lastindex else []
                rules.append({
                    "rule": rule_text[:300],
                    "category": "hierarchy",
                    "confidence": 0.85,
                    "evidence": rule_text[:200],
                })

        return rules

    # ═══════════════════════════════════════════════════════════
    # 关系图谱
    # ═══════════════════════════════════════════════════════════

    def build_relationship_graph(self, terms: dict, character_names: list[str]) -> dict:
        """
        从术语和角色列表中构建初步关系图谱。

        Args:
            terms: extract_terms() 的输出
            character_names: 已知角色名列表

        Returns:
            {nodes: [...], edges: [...]}
        """
        nodes = []
        edges = []

        # 角色节点
        for name in character_names:
            nodes.append({
                "id": name,
                "type": "character",
                "label": name,
            })

        # 术语节点（地点、组织）
        for term, info in terms.items():
            if info["category"] in ("location", "technique_or_book", "realm_or_level"):
                nodes.append({
                    "id": term,
                    "type": info["category"],
                    "label": term,
                    "frequency": info["frequency"],
                })

        # 共现边：角色与地点/组织在同一上下文中出现
        for term, info in terms.items():
            if info["category"] in ("location", "character_title"):
                for ctx in info.get("contexts", []):
                    for name in character_names:
                        if name in ctx and name != term:
                            edges.append({
                                "source": name,
                                "target": term,
                                "relation": "associated_with",
                                "context": ctx[:100],
                            })

        return {"nodes": nodes, "edges": edges}

    # ═══════════════════════════════════════════════════════════
    # 知识注册表
    # ═══════════════════════════════════════════════════════════

    def update_registry(
        self,
        terms: dict,
        rules: list[dict],
        graph: dict,
        source_name: str = "",
        registry_path: str = None,
    ) -> str:
        """
        更新知识注册表（Markdown 格式）。

        Args:
            terms: 术语字典
            rules: 世界观规则
            graph: 关系图谱
            source_name: 来源名称
            registry_path: 注册表文件路径

        Returns:
            注册表文件路径
        """
        if registry_path is None:
            registry_path = os.path.join(self.output_dir, "source_registry.md")

        # 读取已有内容
        existing = ""
        if os.path.exists(registry_path):
            with open(registry_path, "r", encoding="utf-8") as f:
                existing = f.read()

        # 生成新内容
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        content = []

        # 如果注册表为空，先生成头部
        if not existing.strip():
            content.append("# 知识注册表 — Novel-to-Script Pro\n")
            content.append(f"> 自动生成于 {now}")
            content.append(f"> 来源材料: {source_name}\n")
        else:
            content.append(f"\n---\n\n## 更新: {source_name} ({now})\n")

        # 术语表
        content.append(f"### 术语表 ({len(terms)} 项)\n")
        content.append("| 术语 | 类别 | 频次 | 首次出现 |")
        content.append("|------|------|------|---------|")
        for term, info in sorted(terms.items(), key=lambda x: -x[1]["frequency"]):
            first = info.get("first_appearance", "")[:60].replace("|", "\\|")
            content.append(f"| {term} | {info['category']} | {info['frequency']} | {first} |")

        # 世界观规则
        if rules:
            content.append(f"\n### 世界观规则 ({len(rules)} 条)\n")
            for i, rule in enumerate(rules, 1):
                content.append(f"{i}. **[{rule['category']}]** {rule['rule'][:200]}")
                if rule.get("evidence"):
                    content.append(f"   > 原文: {rule['evidence'][:150]}")

        # 关系图谱摘要
        if graph["nodes"]:
            content.append(f"\n### 关系图谱摘要\n")
            content.append(f"- 节点: {len(graph['nodes'])} 个")
            content.append(f"- 边: {len(graph['edges'])} 条")
            content.append(f"- 角色节点: {sum(1 for n in graph['nodes'] if n['type'] == 'character')}")
            content.append(f"- 地点节点: {sum(1 for n in graph['nodes'] if n['type'] == 'location')}")

        full_content = existing + "\n" + "\n".join(content)

        with open(registry_path, "w", encoding="utf-8") as f:
            f.write(full_content)

        return registry_path

    # ═══════════════════════════════════════════════════════════
    # 批量扫描
    # ═══════════════════════════════════════════════════════════

    def scan_source_directory(self, source_dir: str = None) -> dict:
        """
        扫描整个源目录，聚合所有文件的提取结果。

        Args:
            source_dir: 源目录路径（默认使用实例的 sources_dir）

        Returns:
            {terms, rules, graph, file_count, total_chars}
        """
        source_dir = source_dir or self.sources_dir
        if not os.path.isdir(source_dir):
            return {"terms": {}, "rules": [], "graph": {"nodes": [], "edges": []},
                    "file_count": 0, "total_chars": 0}

        all_terms = defaultdict(lambda: {"category": "", "frequency": 0,
                                          "contexts": [], "first_appearance": ""})
        all_rules = []
        all_characters = set()
        total_chars = 0
        file_count = 0

        for root, _, files in os.walk(source_dir):
            for fn in sorted(files):
                if fn.endswith((".txt", ".md")):
                    file_count += 1
                    fpath = os.path.join(root, fn)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            text = f.read()
                    except UnicodeDecodeError:
                        print(f"  ⚠️  跳过非 UTF-8 文件: {fpath}")
                        continue

                    total_chars += len(text)

                    # 提取术语
                    terms = self.extract_terms(text)
                    for term, info in terms.items():
                        if not all_terms[term]["first_appearance"]:
                            all_terms[term]["first_appearance"] = info.get("first_appearance", "")
                        all_terms[term]["frequency"] += info["frequency"]
                        if info["category"] not in all_terms[term]["category"]:
                            all_terms[term]["category"] = info["category"]
                        for ctx in info["contexts"]:
                            if len(all_terms[term]["contexts"]) < 5:
                                all_terms[term]["contexts"].append(ctx)

                    # 提取规则
                    rules = self.extract_world_rules(text)
                    all_rules.extend(rules)

                    # 收集角色名（从术语中筛选）
                    for term, info in terms.items():
                        if info["category"] == "character_title":
                            all_characters.add(term)

                    print(f"  📄 {fn}: {len(terms)} 术语, {len(rules)} 规则")

        # 构建关系图谱
        graph = self.build_relationship_graph(dict(all_terms), list(all_characters))

        return {
            "terms": dict(all_terms),
            "rules": all_rules,
            "graph": graph,
            "file_count": file_count,
            "total_chars": total_chars,
        }

    # ═══════════════════════════════════════════════════════════
    # 知识摘要生成（规则版，无需 LLM）
    # ═══════════════════════════════════════════════════════════

    def generate_summary(self, scan_result: dict) -> str:
        """基于扫描结果生成知识摘要"""
        terms = scan_result.get("terms", {})
        rules = scan_result.get("rules", [])
        file_count = scan_result.get("file_count", 0)

        summary = []
        summary.append(f"## 源材料知识摘要\n")
        summary.append(f"- 扫描文件: {file_count} 个")
        summary.append(f"- 总字符数: {scan_result.get('total_chars', 0):,}")
        summary.append(f"- 提取术语: {len(terms)} 个")
        summary.append(f"- 世界观规则: {len(rules)} 条")

        # 按类别统计术语
        by_category = defaultdict(int)
        for info in terms.values():
            by_category[info["category"]] += 1

        summary.append(f"\n### 术语类别分布")
        for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
            summary.append(f"- {cat}: {count}")

        # Top 术语
        top_terms = sorted(terms.items(), key=lambda x: -x[1]["frequency"])[:20]
        summary.append(f"\n### 高频术语 Top 20")
        for term, info in top_terms:
            summary.append(f"- **{term}** [{info['category']}] — 出现 {info['frequency']} 次")

        # 规则摘要
        rule_categories = defaultdict(int)
        for r in rules:
            rule_categories[r["category"]] += 1
        summary.append(f"\n### 规则类别分布")
        for cat, count in sorted(rule_categories.items(), key=lambda x: -x[1]):
            summary.append(f"- {cat}: {count}")

        return "\n".join(summary)


# ═══════════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════════

def quick_scan(source_dir: str, output_dir: str = "./knowledge") -> dict:
    """快速扫描源目录并更新注册表"""
    skill = KnowledgeCurationSkill(sources_dir=source_dir, output_dir=output_dir)
    result = skill.scan_source_directory(source_dir)
    if result["file_count"] > 0:
        skill.update_registry(
            terms=result["terms"],
            rules=result["rules"],
            graph=result["graph"],
            source_name=os.path.basename(source_dir),
        )
        summary = skill.generate_summary(result)
        print(summary)
    return result
