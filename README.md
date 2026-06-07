# Novel-to-Script Pro v2.3

> 🎬 小说 → 剧本 → 分镜 → 生图，AI 驱动的全流程智能改编系统

**Novel-to-Script Pro** 是一款 AI 辅助剧本创作工具。上传小说 TXT 章节或**在线爬取**，自动生成结构化 YAML/TXT 剧本、审核报告、分镜序列板和 AI 图片。

v2.1 独创**剧情权重分级算法**与**影视节奏智能拆分**，v2.2 新增**在线小说爬取**、**剧本微调**和**动态前端动效**，v2.3 全新**影院级封面页**与**TXT 剧本面板**，打破市面工具"无脑全文直译"的弊端，实现真正专业的影视改编。

![Novel-to-Script Pro 封面](docs/screenshot.png)

---

## ✨ 核心特性

### 🆕 v2.3 新增：封面页 & TXT 剧本面板

- **🎞️ 影院级封面页** — 暗色影院风格全屏封面，浮动粒子 + 海报光扫 + 鼠标视差，Enter/点击进入工作台，AnimatePresence 平滑转场
- **📝 TXT 剧本视图** — YAML / TXT / 预览三视图切换，TXT 以可读剧本格式渲染（角色对话、动作描述、场景标题）
- **📋 一键复制剧本** — TXT 视图内置「复制剧本」按钮，Clipboard API 一键复制全剧本纯文本
- **🗺️ 场景导航侧栏** — TXT 视图左侧场景列表，点击跳转到对应场景
- **🖨️ 打印友好** — 内建 `@media print` 样式，白色背景 + A4 排版，直接打印/导出 PDF
- **♿ 无障碍增强** — aria-label 全覆蓋、prefers-reduced-motion 适配、键盘导航支持
- **📜 浏览器历史集成** — 进入/退出工作台支持浏览器前进后退

### 🆕 v2.2 新增：在线爬虫 & 剧本微调 & 动态前端

- **🕷️ 在线小说爬取** — 输入小说类型/关键词，自动搜索公开小说源并下载全文。内置 18 部热门小说目录，支持多选批量下载
- **✏️ 剧本微调** — 对已生成剧本提交自定义修改意见（如"增加动作描写""减少旁白"），系统自动重新生成新版本，支持版本化管理
- **✨ 动态前端动效** — 基于 Framer Motion 的全站动画升级：交错文本揭示、鼠标视差环境光、滚动触发卡片揭示、选项卡切换过渡、悬停物理反馈、滚动进度条
- **📦 版本化剧本** — 每次微调生成 `ep01_script_v{N}.yaml` 新版本，API 默认返回最新版，可通过 `?version=N` 查看历史版本

### 🎯 v2.1：内容分级 & 智能分集

- **📊 S/A/B 三级权重分拣** — 独创剧情权重分级算法，智能识别核心剧情(S级)、辅助内容(A级)、冗余灌水(B级)，自动过滤压缩
- **🎚️ 三种改编模式** — `忠于原著`(strict) / `均衡改编`(balanced) / `影视节奏`(loose)，满足不同创作需求
- **🔀 冲突节点检测** — 自动识别剧情转折、场景切换、情绪峰值、章末悬念、情节收束五大节点类型
- **🎬 影视节奏拆分** — 打破"逐章机械转换"，按冲突节点智能合并/拆分章节，适配短剧(3-5min)和长剧(45min)
- **🪝 剧集结构标注** — 每集自动生成开篇钩子、中段冲突、结尾悬念 + 核心看点、剧情伏笔、招商审核备注

### 🏗️ 基础能力

- **📖 LLM 智能抽取** — 滑窗并行 + DeepSeek LLM 深度抽取，精准识别对话、动作、描写、情绪、潜台词
- **🔗 8 阶段管线** — 导入 → 分析 → 规划(智能分集) → 写剧本(分级过滤) → 审核 → 分镜 → 生图 → 完成检查
- **🤖 11 Agent 协作** — 专职 Agent 角色（内容分级师、影视导演、剧本分析、分集规划、情绪曲线、多维度审核、分镜设计等）
- **🔄 审核闭环** — 业务评分（情节/人物/对白/节奏/视觉/情感/悬念）+ 合规检查 + AI 评审意见
- **🎥 分镜序列板** — 从剧本自动解析场景 → 镜头 → 节拍，生成 Camera Map + Motion Prompts
- **🖼️ AI 生图** — 集成 Doubao Seedream 5.0，从分镜数据自动生成分镜图
- **🖥️ Web UI** — Next.js 16 + FastAPI，影院级封面页 + 可视化操作全流程 + 实时进度 + TXT/YAML 双格式
- **🔌 多 Provider** — LLM（DeepSeek/OpenAI）、图片生成（Doubao/OpenAI 兼容）可配置切换

---

## 🏗️ 管线流程

```
Phase 0: 导入        →  扫描 TXT 章节，建立源材料索引
Phase 1: 分析        →  LLM 分析叙事结构、角色网络、改编潜力 + 冲突节点检测
Phase 2: 规划        →  冲突节点驱动智能分集、情绪曲线、每集钩子/冲突/悬念标注
Phase 3: 写剧本      →  S/A/B 内容分级 → 过滤冗余/压缩辅助 → 结构化 YAML 剧本
Phase 4: 审核        →  LLM 多维度审核（业务 7 维度评分 + 合规检查 + AI 评审意见）
Phase 5: 分镜        →  剧本解析 → 场景/镜头/节拍 → Sequence Board + Motion Prompts
Phase 6: 生图        →  分镜数据 → 图片提示词 → AI 生成分镜图（可选）
Phase 7: 完成检查    →  乱码检测、一致性校验、完整性验证
```

### 分级数据流

```
小说文本 → LLM提取元素 → S/A/B 分拣:
  ├─ S级 (核心剧情): 冲突/对话/关键动作/转折 → 100% 保留
  ├─ A级 (辅助剧情): 环境铺垫/人物神态 → 压缩为镜头描述
  └─ B级 (冗余内容): 重复碎碎念/心理OS/灌水 → 过滤或合并极简旁白
```

---

## 📦 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- LLM API Key（DeepSeek 或 OpenAI 兼容）
- （可选）图片生成 API Key（Doubao Seedream / OpenAI DALL-E）

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 LLM API Key
```

或通过 API 运行时配置：
```bash
curl -X POST http://localhost:8000/api/config \
  -H "Content-Type: application/json" \
  -d '{"api_key":"sk-你的key","base_url":"https://api.deepseek.com/v1","model":"deepseek-chat"}'
```

### 3. 启动后端

```bash
py -3.11 -m uvicorn server:app --host 0.0.0.0 --port 8000
# API 运行在 http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### 4. 启动前端

```bash
cd web
npm install
npm run build
npm run start -- --port 3333
# 前端运行在 http://localhost:3333
```

### 5. 使用

1. 打开 `http://localhost:3333`
2. 📸 封面页 → 点击「开始体验」或按 Enter 进入工作台
3. 选择**改编模式**（忠于原著 / 均衡改编 / 影视节奏）和**剧集格式**（长剧45min / 短剧3-5min）
4. 「导入」标签页上传 `.txt` 章节文件（或在线爬取小说）
5. 点「运行管线」
6. 查看「剧本」(YAML/TXT/预览三视图 + S/A/B分级统计 + **微调**)、「规划」(冲突节点+剧集标注)、「审核」「分镜」「图片」

> 💡 **不用上传 TXT？** 切换「导入」标签页 → "在线获取小说" → 选择类型 → 搜索 → 勾选 → 下载 → 自动导入管线

---

## 🖼️ 图片生成配置

编辑 `config.yaml`：
```yaml
image_gen:
  provider: "ark"        # ark (Doubao) / openai (DALL-E) / custom
  api_key: "你的图片API Key"
  base_url: "https://ark.cn-beijing.volces.com/api/v3"
  model: "doubao-seedream-5-0-260128"
  default_size: "2K"
```

---

## 📁 项目结构

```
novel-to-script-pro/
├── engine/              # 管线引擎（Pipeline 调度、状态管理、任务队列）
├── agents/              # 11 个专职 Agent（v2.1 新增: ContentGrader, EpisodeDirector）
├── skills/              # 可复用技能模块（v2.1 新增: content_grading, conflict_analyzer, episode_rhythm）
├── crawler/             # 🆕 v2.2 爬虫模块（目录搜索 + 在线多源聚合 + 全文下载）
├── extractors/          # 文本抽取层（LLM 抽取、规则抽取）
├── builders/            # 剧本构建层（YAML 构建器 v2.1）
├── knowledge/           # 知识层（参考库、提示词模板）
├── references/          # 方法论参考
├── schema/              # YAML Schema 定义 (v2.0)
├── web/                 # Next.js 16 前端（v2.3: 封面页 + TXT 面板 + 打印样式）
├── docs/                # 🆕 文档资源（截图等）
├── tests/               # 单元测试（31 用例）
├── sample_novel/        # 示例小说（3 章）
├── output/              # 输出目录
│   └── {项目名}/
│       ├── scripts/         # YAML 剧本（含 content_grade 标记）
│       ├── analysis/        # 分析报告 + 冲突节点数据
│       ├── planning/        # 智能分集规划 + 情绪曲线 + 剧集标注
│       ├── review/          # 审核报告
│       ├── storyboard/      # 分镜序列板 + 运动提示
│       └── images/          # AI 生成图片 + 提示词
├── config.yaml          # 全局配置（v2.1 新增 content_grading + episode_rhythm）
├── server.py            # FastAPI 入口（v2.3: CORS 多端口支持）
└── requirements.txt     # Python 依赖
```

---

## ⚙️ 配置说明

| 配置项 | 说明 |
|--------|------|
| `llm.provider` | LLM 提供商：`deepseek` / `openai` / `custom` |
| `llm.model` | 模型名称 |
| `content_grading.enabled` | 是否启用内容分级（v2.1） |
| `content_grading.mode` | 分级模式：`strict`(忠于原著) / `balanced`(均衡) / `loose`(影视节奏) |
| `content_grading.s_level_threshold` | S级置信度阈值 (0-1) |
| `content_grading.max_merged_narration_chars` | B级合并旁白最大字数 |
| `episode_rhythm.enabled` | 是否启用智能分集（v2.1） |
| `episode_rhythm.target_format` | 剧集格式：`short_drama`(3-5min) / `long_drama`(45min) |
| `episode_rhythm.cliffhanger_required` | 每集是否必须有悬念结尾 |
| `image_gen.provider` | 图片生成器：`ark` (Doubao) / `openai` (DALL-E) / `custom` |
| `processing.window_size` | 滑窗行数（默认 40） |
| `pipeline.review_passes` | 审核通过最少 PASS 数 |
| `pipeline.max_rewrite_rounds` | 单集最多回改轮次 |
| `crawler.max_chapters` | 爬虫单次下载最大章节数（默认 50） |

---

## 📄 许可证

MIT License
