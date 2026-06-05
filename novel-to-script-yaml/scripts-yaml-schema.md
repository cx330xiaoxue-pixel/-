# 剧本 YAML Schema 定义文档

> 版本: 1.0  
> 适用工具: AI 辅助剧本创作工具  
> 格式: YAML 1.2

---

## 目录

1. [设计理念](#设计理念)
2. [Schema 总览](#schema-总览)
3. [字段详细定义](#字段详细定义)
4. [完整示例](#完整示例)
5. [设计决策说明](#设计决策说明)
6. [扩展性考虑](#扩展性考虑)

---

## 设计理念

本 Schema 专为 **小说→剧本改编** 的半自动化流程设计，核心目标：

1. **可读性优先**: YAML 格式天然兼容人类阅读和机器解析，作者可以直接用文本编辑器修改
2. **层级映射**: 剧本本身的层级结构（作品→章→场→元素）在 Schema 中得到自然映射
3. **双向可追溯**: 每个元素都能追溯到原文位置，方便作者对比原著修改
4. **AI 友好**: 结构化的字段设计让 LLM 能够准确理解和填充内容
5. **渐进增强**: 必填字段最小化，大量可选字段支持从初稿到终稿的渐进完善

---

## Schema 总览

```
script                           # 根节点
├── metadata                     # 剧本元信息
├── characters[]                 # 角色列表
└── chapters[]                   # 章节列表
    └── scenes[]                 # 场景列表
        └── elements[]           # 剧本元素列表（最小单位）
```

### 核心设计原则: 三层结构

| 层级 | 对应概念 | 关键字段 |
|------|---------|---------|
| **Chapter（章）** | 原著章节 / 改编后的幕 | summary, scene_count |
| **Scene（场）** | 同一时间地点发生的连续剧情 | location, time, atmosphere |
| **Element（元素）** | 单句对白 / 一段旁白 / 一个动作 | type, role, text |

---

## 字段详细定义

### 1. `metadata` — 剧本元信息

```yaml
metadata:
  script_title: string           # 必填。剧本名称
  original_work: string          # 必填。原著作品名
  original_author: string        # 必填。原著作者
  adapter: string                # 可选。改编者/工具
  created_date: string           # 必填。生成日期 (YYYY-MM-DD)
  version: string                # 必填。版本号，初稿建议 "1.0-draft"
  total_chapters_adapted: int    # 必填。改编章节总数
  adapted_chapter_ids: [int]     # 必填。改编的章节编号列表
  statistics:                    # 必填。统计信息
    total_elements: int          # 元素总数
    dialogue_count: int          # 对白元素数
    narration_count: int         # 旁白元素数
    estimated_scenes: int        # 估算场景数
```

**设计原因**: 元数据区块独立于内容，方便剧本管理、版本控制和出处追溯。在影视工业中，改编权溯源和版本管理是刚性需求。

---

### 2. `characters[]` — 角色列表

```yaml
characters:
  - character_id: string         # 必填。唯一标识，格式: "CHAR-NNN" (如 CHAR-001)
    name: string                 # 必填。角色名称
    aliases: [string]            # 可选。别名/称呼列表
    role_type: string            # 必填。角色类型
                                #   枚举: protagonist | antagonist | supporting | minor | cameo
    description: string          # 可选。角色描述
    traits: [string]             # 可选。性格特征标签
    first_appearance: string     # 可选。首次出场 (如 "第1章")
    last_appearance: string      # 可选。最后出场
    total_appearances: int       # 可选。出场总次数
    primary_emotion: string      # 可选。主导情绪
```

**设计原因**:

- **character_id 使用前缀编码 (CHAR-001)** 而非数字，方便与其他系统（如剧组管理软件）对接
- **role_type 借鉴影视工业分类** (protagonist/antagonist/supporting/minor/cameo)，让编剧能快速评估角色配置
- **aliases 字段**解决小说中同一角色有多个称呼的问题（如"林清风"也称为"清风哥"、"林小子"）
- **统计字段 (appearances)** 帮助作者量化角色分量，做出合理的戏份分配决策

---

### 3. `chapters[]` — 章节列表

```yaml
chapters:
  - chapter_id: int              # 必填。章节编号
    chapter_title: string        # 必填。章节标题
    source_chapter: int          # 可选。对应原著章节号 (默认为 chapter_id)
    summary: string              # 必填。本章摘要
    scene_count: int             # 必填。本章场景数
    element_count: int           # 必填。本章元素数
    scenes: [scene]              # 必填。场景列表 (见下)
```

**设计原因**:

- **source_chapter** 允许与原著章节号不同，支持"将多章合并为一章"或"一章拆为多章"的改编场景
- **summary** 是 AI 自动生成的关键字段 — 一方面作为跨章节上下文传递给 LLM 保持连贯性，另一方面方便作者快速浏览全局
- **scene_count / element_count** 是低成本的结构概览，帮助作者判断章节密度是否合适

---

### 4. `scenes[]` — 场景列表

```yaml
scenes:
  - scene_id: string             # 必填。场景唯一标识，格式: "chapter_id.scene_number" (如 "1.2")
    scene_number: int            # 必填。章内场景序号
    location: string             # 必填。场景地点 (AI 推断，作者可修改)
    time: string                 # 可选。时间 (清晨/上午/中午/下午/傍晚/夜晚/深夜)
    atmosphere: string           # 可选。氛围 (欢快/忧伤/紧张/平静/温馨/悬疑/阴暗/中性)
    element_count: int           # 必填。本场景元素数
    elements: [element]          # 必填。元素列表 (见下)
```

**设计原因**:

- **scene_id 采用层级编号 (1.2)** 而非 UUID，人眼可读且能直接体现所属章节
- **location 和 time** 由 AI 从文本中自动推断 — 不完全准确但为作者提供了高价值的起点
- **atmosphere** 通过情绪标签聚合得出，帮助导演/编剧把握每个场景的基调
- 所有 AI 推断字段均可被作者手动修改 — Schema 是 **脚手架而非牢笼**

---

### 5. `elements[]` — 剧本元素（最小单位）

```yaml
elements:
  - element_id: string           # 必填。唯一标识，格式: "chapter.scene.seq" (如 "1.2.5")
    type: string                 # 必填。元素类型
                                #   枚举: dialogue | narration | action | description
    role: string                 # 必填。角色名 或 "旁白"
    text: string                 # 必填。原始文本内容
    emotion: string              # 可选。情绪标签
    action: string               # 可选。动作描述
    parenthetical: string        # 可选。括号内的表演指导
```

**元素类型说明**:

| type | 含义 | role 示例 |
|------|------|----------|
| `dialogue` | 角色对白 | "林清风" |
| `narration` | 旁白/叙述（剧本画外音） | "旁白" |
| `action` | 动作描写 | 角色名 |
| `description` | 场景/环境描写 | "旁白" |

**设计原因**:

- **element_id 采用三段式编号 (章.场.序号)** — 既是唯一标识也是位置信息，方便定位
- **type 枚举仅限于 4 种** — 覆盖剧本创作的所有基本单元，同时不过度细分导致分类边界模糊
- **emotion 和 action 为可选字段** — 不是所有片段都有明确的情绪/动作，强制填充会导致 AI 编造
- **parenthetical（表演指导）**保留了好莱坞标准剧本格式中的括号标注惯例，如 "(激动地)"、"(低声)"

---

## 完整示例

以下是一个最小的完整剧本 YAML 示例：

```yaml
script:
  metadata:
    script_title: "剑影江湖"
    original_work: "剑影江湖"
    original_author: "示例作者"
    adapter: "AI 辅助剧本创作工具 v1.0"
    created_date: "2026-06-05"
    version: "1.0-draft"
    total_chapters_adapted: 1
    adapted_chapter_ids: [1]
    statistics:
      total_elements: 5
      dialogue_count: 2
      narration_count: 3
      estimated_scenes: 1

  characters:
    - character_id: "CHAR-001"
      name: "林清风"
      aliases: ["清风", "清风哥"]
      role_type: "protagonist"
      description: "十八岁的少年修行者，心性纯良"
      traits: ["勇敢", "善良", "坚韧"]
      first_appearance: "第1章"
      total_appearances: 2
      primary_emotion: "平静"

    - character_id: "CHAR-002"
      name: "苏婉儿"
      role_type: "supporting"
      description: "邻家少女，暗恋林清风"
      traits: ["温柔", "细腻"]
      first_appearance: "第1章"
      total_appearances: 1
      primary_emotion: "悲伤"

  chapters:
    - chapter_id: 1
      chapter_title: "初入江湖"
      source_chapter: 1
      summary: "少年林清风告别家乡，踏上修行之路"
      scene_count: 1
      element_count: 5
      scenes:
        - scene_id: "1.1"
          scene_number: 1
          location: "室外-村口"
          time: "清晨"
          atmosphere: "忧伤"
          element_count: 5
          elements:
            - element_id: "1.1.1"
              type: "narration"
              role: "旁白"
              text: "清晨的阳光透过竹林洒在地上，林清风背着行囊站在村口的老槐树下。"
              
            - element_id: "1.1.2"
              type: "dialogue"
              role: "苏婉儿"
              text: "清风哥，你真的要走吗？"
              emotion: "悲伤"
              action: "咬着嘴唇"
              
            - element_id: "1.1.3"
              type: "dialogue"
              role: "林清风"
              text: "婉儿，我必须走。修行之路不进则退。"
              emotion: "坚定"
              action: "微微一笑"
              
            - element_id: "1.1.4"
              type: "action"
              role: "苏婉儿"
              text: "她从袖中取出一个绣着兰花的香囊，塞进林清风的手中。"
              emotion: "悲伤"
              action: "递出香囊"
              
            - element_id: "1.1.5"
              type: "narration"
              role: "旁白"
              text: "林清风转过身，迈开步子踏上了通向山外的蜿蜒小路。他没有再回头。"
              emotion: "平静"
```

---

## 设计决策说明

### 决策 1: 为什么选择 YAML 而非 JSON 或 XML？

| 维度 | YAML | JSON | XML |
|------|------|------|-----|
| 人类可读性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| 多行文本支持 | ⭐⭐⭐⭐⭐ (literal block) | ⭐⭐ (需转义) | ⭐⭐⭐ |
| 注释支持 | ✅ | ❌ | ✅ |
| 版本控制友好 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 生态工具 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

**结论**: YAML 是剧本格式的最佳选择。剧本天然包含大量多行对白和叙述文本，YAML 的 literal block scalar (`|`) 可以原生支持多行文本而无需转义换行符。同时，注释功能允许作者在剧本中留下创作笔记。

### 决策 2: 为什么采用三层结构（Chapter → Scene → Element）？

这是影视工业标准剧本格式的数字化映射：

- **Chapter（章/幕）**: 对应剧本的宏观结构单元。在好莱坞体系中称为 Act（幕），在中国剧本中通常按原著章节推进
- **Scene（场）**: 标准剧本的基本单位，定义为同一时间地点发生的连续剧情
- **Element（元素）**: 场内的最小可操作单元，每个元素对应剧本中的一个对白行、一段旁白或一个动作描述

这种三层结构让作者可以在不同粒度上操作：
- **按章**: 调整故事整体结构和节奏
- **按场**: 增删场景，调整场景顺序
- **按元素**: 逐句修改对白，调整角色互动

### 决策 3: 为什么 emotion 和 action 是可选字段？

1. **AI 提取不保证完整性**: 不是每句话都有明确的情绪标签或动作描述。强制填充会导致 AI 编造不存在的内容
2. **作者工作量考虑**: 让 AI 标记它能确定的，作者补充它不确定的
3. **格式兼容性**: 空字段比填充错误数据更好处理

### 决策 4: 为什么 element_id 使用层级编号而非 UUID？

```
element_id: "3.2.15"
# 阅读: 第3章 → 第2场 → 第15个元素
```

层级编号的优势：
- **位置自描述**: 一眼可知元素在剧本中的位置
- **排序友好**: 字符串排序即逻辑排序
- **范围查询**: 正则 `^3\.` 即可筛选第3章所有元素
- **人机共读**: 编导可以口头交流 "修改第3章第2场第15句对白"

UUID 更适合分布式系统，但剧本创作是线性流程，层级编号更合适。

### 决策 5: 为什么保留 role_type 的英文枚举值？

```yaml
role_type: "protagonist"  # 而非 "主角"
```

- **工具链兼容**: 主流剧本软件（Final Draft, Celtx）使用英文标签
- **编程友好**: 英文枚举值可直接用作代码中的变量名和数据库键
- **国际化**: 显示层可以翻译为任何语言，但数据层保持稳定

### 决策 6: 为什么 characters 独立于 chapters？

角色信息被提升到与章节同级的顶层，因为：
1. **角色跨章节存在**: 同一个角色出现在多个章节中
2. **全局角色视图**: 作者可以在一处查看和管理所有角色
3. **统计分析**: 计算全剧角色出场频次、情绪分布等
4. **一致性**: 避免同一角色在不同章节中出现描述不一致

---

## 扩展性考虑

### 短期扩展 (v1.1)

```yaml
# 新增字段示例
metadata:
  genre: [string]              # 剧本类型: 玄幻 | 言情 | 武侠 | 都市 | ...
  target_medium: string        # 目标媒介: film | tv_series | stage | animation
  estimated_runtime: string    # 预估时长: "120min" | "45min x 12ep"

characters:
  - character_id: string
    # 新增
    relationships:             # 角色关系
      - target: "CHAR-002"
        relation: "恋人"
    arc_summary: string        # 角色弧线概述

scenes:
  - scene_id: string
    # 新增
    characters_present: [string]  # 本场出场角色
    props_needed: [string]        # 所需道具
    estimated_duration: string    # 预估拍摄时长
```

### 长期扩展 (v2.0)

- **多版本对比**: 支持同一场景的多个改编版本并存
- **拍摄备注**: 为导演/摄影/灯光添加技术备注字段
- **分镜脚本映射**: 关联分镜画面到具体的 elements
- **成本估算**: 基于场景复杂度自动估算拍摄预算
- **多语言支持**: 双语剧本格式（如中英对照）

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| 1.0 | 2026-06-05 | 初始版本，定义核心 Schema |

---

## 参考文献

- *The Screenwriter's Bible* — David Trottier
- *The Hollywood Standard* — Christopher Riley
- Final Draft XML Schema
- Fountain Screenplay Markup Language
