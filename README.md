# Novel-to-Script Pro

> 🎬 小说 → 剧本 → 分镜，AI 驱动的全流程智能改编系统

**Novel-to-Script Pro** 是一款面向小说作者的 AI 辅助剧本创作工具。输入 3 章以上的小说文本，自动生成结构化的 YAML 剧本初稿 —— 可编辑、可打磨、可直接进入拍摄筹备。

---

## ✨ 核心特性

- **📖 智能抽取** — 滑窗并行 + LLM 深度抽取，精准识别对话、动作、描写、潜台词、节拍类型
- **🔗 6 阶段管线** — 知识收编 → 改编分析 → 分集规划 → 逐集写剧本 → 多维度审核 → 分镜可视化，全流程自动化
- **🤖 多 Agent 协作** — 14 个专职 Agent 角色，各司其职（剧本分析、情绪曲线、分镜设计、合规审核…）
- **🎨 双轨分镜** — 同时支持传统 Film Storyboard 和 Seedance AI 视频流分镜
- **🔄 审核闭环** — 业务审核 + 合规检查 + 风格对比 + Show Don't Tell 视觉化验证，自动回改
- **📐 YAML Schema v2** — 结构化剧本格式，人机共读，支持角色关系图、情绪曲线、版本对比
- **🖥️ Web UI** — Next.js 前端 + FastAPI 后端，可视化操作全流程
- **🔌 多 Provider 可替换** — LLM（DeepSeek/OpenAI/任意兼容）、图片生成、视频生成均可配置切换

---

## 🏗️ 6 阶段管线

```
Phase 0: 知识收编    →  导入原文，术语注册，建立知识索引
Phase 1: 改编分析    →  主题洞察、人物弧光、世界规则分析
Phase 2: 分集规划    →  章节→集映射、情绪曲线、悬念设计
Phase 3: 逐集写剧本  →  AI 生成 YAML 剧本（含爆款参考、Show Don't Tell）
Phase 4: 多维度审核  →  业务 + 合规 + 对比 + 风格，不通过则自动回改
Phase 5: 分镜可视化  →  双轨分镜（Film Storyboard + Seedance）
Phase 6: 完成检查    →  乱码检测、一致性校验、完整性验证
```

---

## 🎭 Agent 角色

| Agent | 职责 |
|-------|------|
| `knowledge-curator` | 原文知识管理、术语注册 |
| `novel-analyzer` | 小说深度分析（人物、结构、类型） |
| `insight-architect` | 主题洞察与改编策略 |
| `episode-architect` | 分集规划与结构设计 |
| `emotion-architect` | 情绪曲线设计与观众心理管理 |
| `script-writer` | 单集剧本生成（检索 + 参考 + 风格控制） |
| `visual-storyteller` | Show Don't Tell 视觉化审核 |
| `script-comparator` | 与参考剧本逐一对比 |
| `review-director` | 业务审核 + 合规审核 |
| `continuity-recorder` | 跨集一致性记录 |
| `storyboard-director` | 分镜指导与审核 |
| `storyboard-artist` | 分镜图 / Seedance 提示词生成 |
| `art-designer` | 人物 / 场景服化道设计 |
| `image-generator` | 文生图 / 图生视频 API 调用 |

---

## 🛠️ 技术栈

| 层 | 技术 |
|----|------|
| **后端** | Python 3.10+, FastAPI |
| **前端** | Next.js, TypeScript, Tailwind CSS |
| **LLM** | OpenAI SDK（兼容 DeepSeek / OpenAI / 任意 OpenAI-compatible API） |
| **数据格式** | YAML 1.2（Schema v2.0） |
| **配置** | YAML + .env |
| **并发** | ThreadPoolExecutor / asyncio |
| **图片生成** | 可配置 Provider（Nano Banana / SkyReels / OpenAI） |

---

## 📦 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- LLM API Key（DeepSeek 或 OpenAI 兼容）

### 1. 克隆仓库

```bash
git clone https://github.com/cx330xiaoxue-pixel/-.git
cd novel-to-script-pro
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key
```

编辑 `config.yaml`，选择 LLM Provider 和模型。

### 4. 启动后端 API

```bash
python server.py
# API 运行在 http://localhost:8000
```

### 5. 启动前端（可选）

```bash
cd web
npm install
npm run dev
# 前端运行在 http://localhost:3000
```

### 6. 使用 CLI（无 UI）

```bash
# 将 sample_novel 目录下的示例小说转换为剧本
python -m engine.pipeline --source ./sample_novel --output ./output/my_script
```

---

## 📁 项目结构

```
novel-to-script-pro/
├── engine/              # 管线引擎（Pipeline 调度、状态管理、任务队列）
├── agents/              # 14 个专职 Agent（基类 + 各角色实现）
├── skills/              # 可复用技能模块（审核、写作、分镜、检索…）
├── extractors/          # 文本抽取层（LLM 抽取、规则抽取、角色追踪）
├── builders/            # 剧本构建层（YAML 构建器、Schema v2.0）
├── knowledge/           # 知识层（爆款剧本参考库、提示词模板）
├── references/          # 方法论参考（改编系统、分镜方法、故事心理学…）
├── schema/              # YAML Schema v2.0 定义文档
├── scripts/             # 工具脚本（检索、文生图、图反推、批处理）
├── web/                 # Next.js 前端
├── ui/                  # Streamlit UI 组件（旧版）
├── tests/               # 单元测试
├── sample_novel/        # 示例小说（3 章）
├── output/              # 输出目录，按剧本名组织
├── config.yaml          # 全局配置
├── server.py            # FastAPI 入口
└── requirements.txt     # Python 依赖
```

---

## ⚙️ 配置说明

`config.yaml` 中的关键配置项：

| 配置项 | 说明 |
|--------|------|
| `llm.provider` | LLM 提供商：`deepseek` / `openai` / `custom` |
| `llm.model` | 模型名称 |
| `processing.window_size` | 滑窗行数（默认 40） |
| `pipeline.review_passes` | 审核通过最少 PASS 数（默认 2） |
| `pipeline.max_rewrite_rounds` | 单集最多回改轮次（默认 3） |
| `pipeline.storyboard_mode` | 分镜模式：`film` / `seedance` |
| `compliance.target_platform` | 目标平台合规：`generic` / `youku` / `iqiyi` / `tencent` |

---

## 📄 许可证

MIT License

---

## 🙏 致谢

本项目融合了两个来源的核心思想：
- **novel-to-script-yaml** — 可运行的 Python 抽取 + YAML 构建管线
- **novel-to-script-team** — 多 Agent 多 Skill 协作架构与 6 阶段流程设计
