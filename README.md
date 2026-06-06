# Novel-to-Script Pro

> 🎬 小说 → 剧本 → 分镜 → 生图，AI 驱动的全流程智能改编系统

**Novel-to-Script Pro** 是一款 AI 辅助剧本创作工具。上传小说 TXT 章节，自动生成结构化 YAML 剧本、审核报告、分镜序列板和 AI 图片。

---

## ✨ 核心特性

- **📖 LLM 智能抽取** — 滑窗并行 + DeepSeek LLM 深度抽取，精准识别对话、动作、描写、情绪
- **🔗 7 阶段管线** — 导入 → 分析 → 规划 → 写剧本 → 审核 → 分镜 → 生图，全流程自动化
- **🤖 9 Agent 协作** — 专职 Agent 角色（剧本分析、分集规划、情绪曲线、多维度审核、分镜设计）
- **🔄 审核闭环** — 业务评分（情节/人物/对白/节奏/视觉/情感/悬念）+ 合规检查 + AI 评审意见
- **🎥 分镜序列板** — 从剧本自动解析场景 → 镜头 → 节拍，生成 Camera Map + Motion Prompts
- **🖼️ AI 生图** — 集成 Doubao Seedream 5.0，从分镜数据自动生成分镜图
- **🖥️ Web UI** — Next.js 前端 + FastAPI 后端，可视化操作全流程 + 实时进度
- **🔌 多 Provider** — LLM（DeepSeek）、图片生成（Doubao/OpenAI 兼容）可配置切换

---

## 🏗️ 管线流程

```
Phase 0: 导入        →  扫描 TXT 章节，建立源材料索引
Phase 1: 分析        →  LLM 分析叙事结构、角色网络、改编潜力（含综合评分）
Phase 2: 规划        →  章节→集映射、情绪曲线设计、悬念钩子
Phase 3: 写剧本      →  LLM 滑窗抽取 → 结构化 YAML 剧本（对白/动作/情绪/潜台词）
Phase 4: 审核        →  LLM 多维度审核（业务 7 维度评分 + 合规检查 + AI 评审意见）
Phase 5: 分镜        →  剧本解析 → 场景/镜头/节拍 → Sequence Board + Motion Prompts
Phase 6: 生图        →  分镜数据 → 图片提示词 → AI 生成分镜图（可选）
Phase 7: 完成检查    →  乱码检测、一致性校验、完整性验证
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
python server.py
# API 运行在 http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### 4. 启动前端

```bash
cd web
npm install
npm run build
npm run start
# 前端运行在 http://localhost:3000
```

### 5. 使用

1. 打开 `http://localhost:3000`
2. 「导入」标签页上传 `.txt` 章节文件
3. 点「运行管线」
4. 查看「剧本」「审核」「分镜」「图片」各阶段产出

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
├── agents/              # 9 个专职 Agent（基类 + 各角色实现）
├── skills/              # 可复用技能模块（审核、写作、分镜、图片生成）
├── extractors/          # 文本抽取层（LLM 抽取、规则抽取）
├── builders/            # 剧本构建层（YAML 构建器）
├── knowledge/           # 知识层（参考库、提示词模板）
├── references/          # 方法论参考
├── schema/              # YAML Schema 定义
├── web/                 # Next.js 前端
├── sample_novel/        # 示例小说（3 章）
├── output/              # 输出目录
│   └── {项目名}/
│       ├── scripts/         # YAML 剧本
│       ├── analysis/        # 分析报告
│       ├── planning/        # 分集规划 + 情绪曲线
│       ├── review/          # 审核报告
│       ├── storyboard/      # 分镜序列板 + 运动提示
│       └── images/          # AI 生成图片 + 提示词
├── config.yaml          # 全局配置
├── server.py            # FastAPI 入口
└── requirements.txt     # Python 依赖
```

---

## ⚙️ 配置说明

| 配置项 | 说明 |
|--------|------|
| `llm.provider` | LLM 提供商：`deepseek` / `openai` / `custom` |
| `llm.model` | 模型名称 |
| `image_gen.provider` | 图片生成器：`ark` (Doubao) / `openai` (DALL-E) / `custom` |
| `image_gen.model` | 图片模型名称 |
| `processing.window_size` | 滑窗行数（默认 40） |
| `pipeline.review_passes` | 审核通过最少 PASS 数 |
| `pipeline.max_rewrite_rounds` | 单集最多回改轮次 |
| `compliance.target_platform` | 合规平台：`generic` / `youku` / `iqiyi` / `tencent` |

---

## 📄 许可证

MIT License
