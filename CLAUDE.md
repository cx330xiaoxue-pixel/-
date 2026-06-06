# Novel-to-Script Pro — Claude 项目上下文

> 小说→剧本→分镜 全流程智能改编系统  
> 融合 `novel-to-script-yaml`（可运行代码）+ `novel-to-script-team`（多Agent多Skill架构）

---

## 项目定位

本仓库是对两个项目的深度融合与升级：

| 来源 | 核心资产 | 局限 |
|------|---------|------|
| **novel-to-script-yaml** (本地demo) | 可运行的Python代码、Streamlit Web UI、LLM抽取器、YAML Schema | 单次直通管线，无审查回改，无分镜 |
| **novel-to-script-team** (GitHub/Supreme-Ultimate) | 多Agent多Skill工作流、6阶段管线、双轨分镜(Film/Seedance)、审核闭环 | 无独立可运行代码，依赖Claude Code Agent调度 |

**本项目的目标**：把 team 的架构智慧和 demo 的可运行代码融合，做一个**真正能独立运行**的、有完整多阶段管线和 Web UI 的高级改编工具。

---

## 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                   Novel-to-Script Pro                       │
├─────────────────────────────────────────────────────────────┤
│  📂 Web UI (Streamlit)           — 全流程可视化操作界面      │
│  📂 Engine (Pipeline)             — 6阶段管线引擎            │
│  📂 Agents (Agent层)              — 专职Agent角色            │
│  📂 Skills (Skill层)              — 可复用技能模块           │
│  📂 Knowledge (知识层)            — 参考库/方法论/记忆        │
│  📂 Schema (数据层)               — 增强YAML Schema v2.0     │
│  📂 Scripts (工具层)              — 检索/图片生成/批处理     │
└─────────────────────────────────────────────────────────────┘
```

### 6阶段管线（继承自 team，工程化为独立Python模块）

```
Phase 0: ~ingest     → 知识收编与原文导入
Phase 1: ~analyze    → 改编分析（主题洞察、人物弧光、世界规则）
Phase 2: ~plan       → 分集规划（章节→集映射、情绪曲线、悬念设计）
Phase 3: ~write N    → 逐集写剧本（含爆款参考检索、Show Don't Tell）
Phase 4: ~review N   → 多维度审核（业务+合规+对比+风格）
Phase 5: ~storyboard → 分镜可视化（双轨：Film Storyboard + Seedance）
Phase 6: ~final-check→ 完成检查（乱码、一致性、完整性）
```

### Agent 角色（13个核心Agent）

| Agent | 职责 | 对应来源 |
|-------|------|---------|
| `knowledge-curator` | 原文知识管理、术语注册 | team |
| `novel-analyzer` | 小说深度分析（人物、结构、类型） | team + demo (extractor) |
| `insight-architect` | "开天眼"式主题洞察 | team |
| `episode-architect` | 分集规划与结构设计 | team |
| `emotion-architect` | 情绪曲线设计、观众心理管理 | team |
| `script-writer` | 单集剧本生成（检索+参考+风格） | team + demo (script_builder) |
| `visual-storyteller` | Show Don't Tell 审核 | team |
| `script-comparator` | 与参考剧本逐一对比 | team |
| `review-director` | 业务审核+合规审核 | team |
| `continuity-recorder` | 跨集一致性记录 | team |
| `storyboard-director` | 分镜指导与审核 | team |
| `storyboard-artist` | 分镜图/Seedance提示词生成 | team |
| `art-designer` | 人物/场景服化道设计 | team |
| `image-generator` | 文生图/图生视频API调用 | team |

---

## 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| Web UI | Streamlit | 全流程可视化 |
| LLM调用 | OpenAI SDK | 兼容 DeepSeek/OpenAI/任何 OpenAI-compatible |
| 数据格式 | YAML 1.2 | Schema v2.0（增强版，参考 scripts-yaml-schema.md） |
| 配置管理 | YAML + .env | 多Provider切换 |
| 并行处理 | ThreadPoolExecutor / asyncio | 滑窗并行 + 多Agent并行 |
| 检索 | 自建检索(similarity search) | 爆款剧本检索、参考知识检索 |
| 图片生成 | HTTP API (nano banana / SkyReels / etc.) | 可配置Provider |
| 状态持久化 | JSON (.agent-state.json) | Agent上下文恢复 |

---

## 目录结构设计

```
novel-to-script-pro/
├── CLAUDE.md                        # 本文件
├── 步骤.md                          # 实施步骤规划
├── README.md                        # 项目说明
├── requirements.txt                 # Python依赖
├── config.yaml                      # 默认配置
├── .env.example                     # 环境变量模板
│
├── app.py                           # Streamlit Web UI 入口
├── main.py                          # CLI 入口
│
├── engine/                          # 管线引擎
│   ├── pipeline.py                  # Pipeline调度器（阶段路由）
│   ├── state_manager.py             # Agent状态管理（resumable subagents）
│   └── task_queue.py                # 任务队列
│
├── agents/                          # Agent定义（每个Agent是一个模块）
│   ├── base_agent.py                # Agent基类
│   ├── knowledge_curator.py
│   ├── novel_analyzer.py
│   ├── insight_architect.py
│   ├── episode_architect.py
│   ├── emotion_architect.py
│   ├── script_writer.py
│   ├── visual_storyteller.py
│   ├── script_comparator.py
│   ├── review_director.py
│   ├── continuity_recorder.py
│   ├── storyboard_director.py
│   ├── storyboard_artist.py
│   ├── art_designer.py
│   └── image_generator.py
│
├── skills/                          # 技能模块（可被多个Agent复用）
│   ├── adaptation_analysis.py       # 改编分析技能
│   ├── episode_planning.py          # 分集规划技能
│   ├── script_writing.py            # 写剧本技能
│   ├── script_review.py             # 剧本审核技能
│   ├── compliance_review.py         # 合规审核技能
│   ├── style_analysis.py            # 风格分析技能
│   ├── comparative_review.py        # 对比审核技能
│   ├── one_by_one_comparison.py     # 逐一对比技能
│   ├── show_dont_tell.py            # 视觉化审核技能
│   ├── continuity_record.py         # 连续性记录技能
│   ├── hit_script_retrieval.py      # 爆款剧本检索技能
│   ├── film_storyboard.py           # 标准分镜技能
│   ├── seedance_storyboard.py       # Seedance分镜技能
│   ├── image_generation.py          # 图片生成技能
│   ├── image_to_prompt.py           # 图片反推技能
│   └── knowledge_curation.py        # 知识管理技能
│
├── extractors/                      # 文本抽取层（继承自demo重构）
│   ├── llm_extractor.py             # LLM抽取器（重构自extractor.py）
│   ├── rule_extractor.py            # 规则抽取器（重构自mock_extractor.py）
│   └── character_tracker.py         # 角色追踪器（新增）
│
├── builders/                        # 剧本构建层（继承自demo重构）
│   ├── script_builder.py            # YAML剧本构建器
│   └── schema_v2.py                 # Schema v2.0定义
│
├── knowledge/                       # 知识层
│   ├── source_registry.md           # 源材料注册表
│   ├── absorption_map.md            # 知识吸收映射
│   ├── hit_scripts/                 # 爆款剧本参考库索引
│   └── templates/                   # 提示词模板
│
├── references/                      # 参考知识库（继承自team）
│   ├── 00-core-principles.md
│   ├── 01-adaptation-systems.md
│   ├── 08-storyboard-methodology.md
│   ├── 09-visual-design.md
│   ├── 13-show-dont-tell.md
│   ├── 14-story-psychology.md
│   ├── 18-theme-selection.md
│   └── 21-agent-logging-standard.md
│
├── scripts/                         # 工具脚本
│   ├── quick_search.py              # 快速检索
│   ├── generate_image.py            # 文生图
│   ├── reverse_prompt.py            # 图反推提示词
│   └── batch_skyreels.py            # SkyReels批处理
│
├── schema/                          # Schema定义
│   └── scripts-yaml-schema-v2.md    # 增强版YAML Schema
│
├── output/                          # 产出目录
│   └── {剧本名}/
│       ├── .agent-state.json        # Agent状态
│       ├── analysis/                # 分析报告
│       ├── planning/                # 分集规划
│       ├── scripts/                 # 各集剧本(YAML)
│       ├── review/                  # 审核报告
│       ├── storyboard/              # 分镜产物
│       │   └── ep{NN}/
│       ├── assets/                  # 资产提示词
│       ├── images/                  # 生成图片
│       │   ├── characters/
│       │   ├── scenes/
│       │   └── frames/
│       └── final-check-report.md    # 完成检查报告
│
├── ui/                              # Streamlit 页面组件
│   ├── components/                  # UI组件
│   ├── pages/                       # 各页面
│   └── utils.py                     # UI工具
│
└── tests/                           # 测试
    ├── test_extractors.py
    ├── test_builders.py
    └── test_pipeline.py
```

---

## 关键设计决策

### 决策1：Agent以Python模块实现（非纯Markdown）
- **原因**：team项目使用纯Markdown定义Agent，依赖Claude Code执行。本项目需要独立运行，每个Agent必须是可调用的Python类。
- **做法**：`BaseAgent` 提供 LLM 调用、日志、状态持久化能力；每个Agent继承并实现 `execute()` 方法。

### 决策2：保留 demo 的抽取器架构，增强为多阶段
- **原因**：demo的 `extractor.py` 已经实现了滑窗、并行、LLM调用的良好基础。
- **做法**：将单一抽取扩展为 Phase 1→2→3→4 的多阶段管线，每个阶段用专门的Agent进行。

### 决策3：双轨分镜系统
- **原因**：team项目有两条分镜路径——传统Film Storyboard（Beat Board → Sequence Board → Motion）和Seedance AI视频流。
- **做法**：在 Phase 5 中实现两个子流程，用户可选择。

### 决策4：保留 YAML 作为核心数据格式
- **原因**：demo的 YAML Schema 设计精良，人机共读。
- **做法**：升级为 Schema v2.0，增加：角色关系图、情绪曲线数据、分镜关联、版本对比字段。

### 决策5：Provider 可替换
- **原因**：team项目支持 Nano Banana、SkyReels 等多种外部服务。
- **做法**：所有外部服务通过 Provider 抽象层接入，.env 配置。

---

## 编码规范

- **语言**：Python 3.10+，中文注释，英文变量名
- **LLM调用**：统一通过 `BaseAgent.call_llm()` 方法
- **日志**：所有Agent通过 `engine/state_manager.py` 记录执行日志
- **状态持久化**：JSON格式，写入 `outputs/{剧本名}/.agent-state.json`
- **Schema**：遵循 `schema/scripts-yaml-schema-v2.md`
- **文件命名**：Python模块小写_下划线，Agent类名 PascalCase
- **测试**：pytest，覆盖核心抽取和构建逻辑
