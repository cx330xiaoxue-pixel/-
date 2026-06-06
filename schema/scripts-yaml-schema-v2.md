# Novel-to-Script Pro — YAML Schema v2.0

> 小说→剧本改编的结构化数据格式规范  
> 兼容 v1.0，新增 subtext、beat_type、visual_hint、emotion_curve 等字段  
> 版本: 2.0 | 日期: 2026-06-06

---

## 目录

1. [顶层结构](#1-顶层结构)
2. [metadata — 元数据](#2-metadata--元数据)
3. [characters — 角色列表](#3-characters--角色列表)
4. [chapters — 章节列表](#4-chapters--章节列表)
5. [scenes — 场景](#5-scenes--场景)
6. [elements — 元素](#6-elements--元素)
7. [emotion_curve — 情绪曲线](#7-emotion_curve--情绪曲线)
8. [枚举值参考](#8-枚举值参考)
9. [完整示例](#9-完整示例)
10. [校验规则](#10-校验规则)

---

## 1. 顶层结构

```yaml
script:
  metadata:    # 剧本元数据
  characters:  # 角色列表
  chapters:    # 章节列表
  emotion_curve: # 情绪曲线（v2.0 新增）
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `script` | object | ✅ | 根节点 |
| `script.metadata` | object | ✅ | 剧本元数据 |
| `script.characters` | array | ✅ | 角色列表 |
| `script.chapters` | array | ✅ | 章节列表 |
| `script.emotion_curve` | array | | 全剧情绪曲线（v2.0 新增） |

---

## 2. metadata — 元数据

```yaml
metadata:
  script_title: "剑影江湖"           # 剧本标题
  original_work: "剑影江湖"          # 原著名称
  original_author: "佚名"            # 原著作者
  adapter: "Novel-to-Script Pro v2.0" # 改编工具
  created_date: "2026-06-06"         # 生成日期
  version: "2.0-draft"               # 版本号
  schema_version: "2.0"              # Schema 版本
  genre:                             # 🆕 v2.0 剧本类型标签
    - "武侠"
    - "冒险"
  target_medium: "tv_series"         # 🆕 v2.0 目标媒介
  language: "zh-CN"                  # 语言
  total_chapters_adapted: 3          # 已改编章节数
  adapted_chapter_ids: [1, 2, 3]     # 已改编章节ID列表
  pipeline_version: "2.0"            # 🆕 v2.0 管线版本
  statistics:                        # 统计信息
    total_elements: 245
    dialogue_count: 98
    narration_count: 112
    action_count: 35
    estimated_scenes: 24
```

| 字段 | 类型 | 必填 | v2.0 新增 | 说明 |
|------|------|------|-----------|------|
| `script_title` | string | ✅ | | 剧本标题 |
| `original_work` | string | ✅ | | 原著名称 |
| `original_author` | string | ✅ | | 原著作者 |
| `adapter` | string | | | 改编工具名称 |
| `created_date` | string | | | 生成日期 (YYYY-MM-DD) |
| `version` | string | ✅ | | 版本号，建议格式 `X.Y-draft` |
| `schema_version` | string | | | Schema 版本号 |
| `genre` | array[string] | | ✅ | 剧本类型标签 |
| `target_medium` | string | | ✅ | 目标媒介，见[枚举值](#target_medium) |
| `language` | string | | | 输出语言 |
| `total_chapters_adapted` | int | ✅ | | 已改编章节总数 |
| `adapted_chapter_ids` | array[int] | ✅ | | 已改编章节ID |
| `pipeline_version` | string | | ✅ | 使用的管线版本 |
| `statistics` | object | ✅ | | 统计信息 |
| `statistics.total_elements` | int | | | 总元素数 |
| `statistics.dialogue_count` | int | | | 对白元素数 |
| `statistics.narration_count` | int | | | 旁白/叙述元素数 |
| `statistics.action_count` | int | | | 动作元素数 |
| `statistics.estimated_scenes` | int | | | 预估场景数 |

---

## 3. characters — 角色列表

```yaml
characters:
  - character_id: "CHAR-001"         # 角色唯一ID
    name: "林风"                     # 角色名称
    aliases: ["风儿", "小林"]        # 别名列表
    role_type: "protagonist"         # 角色类型
    description: "少年剑客，初入江湖"  # 角色描述
    traits: ["勇敢", "正直", "冲动"]  # 性格特征
    relationships:                   # 🆕 v2.0 角色关系
      - target: "苏婉儿"
        relation: "恋人"
      - target: "赵铁柱"
        relation: "挚友"
    arc_summary: "从懵懂少年成长为一代大侠"  # 🆕 v2.0 弧线概述
    visual_design: "白衣青衫，腰间佩剑..."   # 🆕 v2.0 视觉设计
    first_appearance: "第1章"        # 首次出场
    last_appearance: "第3章"         # 最后出场
    total_appearances: 45            # 总出场次数
    primary_emotion: "坚定"          # 主导情绪
    arc_stage: "development"         # 弧线阶段
```

| 字段 | 类型 | 必填 | v2.0 新增 | 说明 |
|------|------|------|-----------|------|
| `character_id` | string | ✅ | | 唯一标识，格式 `CHAR-NNN` |
| `name` | string | ✅ | | 角色名称 |
| `aliases` | array[string] | | | 别名/绰号/敬称 |
| `role_type` | string | ✅ | | 角色类型，见[枚举值](#role_type) |
| `description` | string | | | 形象/身份/性格简要描述 |
| `traits` | array[string] | | | 性格特征标签 |
| `relationships` | array[object] | | ✅ | 角色关系列表 |
| `relationships[].target` | string | | | 关系目标角色名 |
| `relationships[].relation` | string | | | 关系描述（师徒/恋人/仇敌…） |
| `arc_summary` | string | | ✅ | 角色弧线概述 |
| `visual_design` | string | | ✅ | 服化道设计提示词 |
| `first_appearance` | string | | | 首次出场描述 |
| `last_appearance` | string | | | 最后出场描述 |
| `total_appearances` | int | | | 总出场次数 |
| `primary_emotion` | string | | | 主导情绪 |
| `arc_stage` | string | | | 弧线阶段 |

---

## 4. chapters — 章节列表

```yaml
chapters:
  - chapter_id: 1
    chapter_title: "第一章 初入江湖"
    source_chapter: 1
    summary: "少年林风离开师门，踏上江湖之路..."
    scene_count: 3
    element_count: 85
    emotion_peak:                     # 本章情绪峰值
      emotion: "紧张"
      frequency: 12
      intensity: 7.5
    suspense_hook: "神秘黑衣人突然现身..."  # 章末悬念钩子
    scenes:
      - # 见 scenes 定义
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `chapter_id` | int | ✅ | 章节序号 |
| `chapter_title` | string | ✅ | 章节标题 |
| `source_chapter` | int | | 对应的原著章节 |
| `summary` | string | ✅ | 章节摘要 |
| `scene_count` | int | ✅ | 场景数量 |
| `element_count` | int | ✅ | 元素总数 |
| `emotion_peak` | object | | 情绪峰值 |
| `emotion_peak.emotion` | string | | 峰值情绪类型 |
| `emotion_peak.frequency` | int | | 出现频率 |
| `emotion_peak.intensity` | float | | 强度 (0-10) |
| `suspense_hook` | string | | 章末悬念钩子 |
| `scenes` | array | ✅ | 场景列表 |

---

## 5. scenes — 场景

```yaml
scenes:
  - scene_id: "1.1"
    scene_number: 1
    location: "室外-山野"            # 场景地点
    time: "清晨"                     # 时间
    atmosphere: "紧张"               # 氛围
    characters_present:              # 🆕 v2.0 出场角色
      - "林风"
      - "神秘人"
    props_needed:                    # 🆕 v2.0 所需道具
      - "剑"
      - "斗笠"
    element_count: 28
    elements:
      - # 见 elements 定义
```

| 字段 | 类型 | 必填 | v2.0 新增 | 说明 |
|------|------|------|-----------|------|
| `scene_id` | string | ✅ | | 场景唯一ID，格式 `{chapter}.{scene}` |
| `scene_number` | int | ✅ | | 本章内场景序号 |
| `location` | string | ✅ | | 场景地点，格式 `{室内/室外}-{具体}` |
| `time` | string | | | 时间，见[枚举值](#time) |
| `atmosphere` | string | | | 氛围，见[枚举值](#atmosphere) |
| `characters_present` | array[string] | | ✅ | 本场出场角色列表 |
| `props_needed` | array[string] | | ✅ | 所需道具清单 |
| `element_count` | int | ✅ | | 元素数量 |
| `elements` | array | ✅ | | 元素列表 |

---

## 6. elements — 元素

元素是剧本的最小单位，每条元素对应一句对白、一段叙述或一个动作。

```yaml
elements:
  - element_id: "1.1.1"
    type: "dialogue"                 # 元素类型
    role: "林风"                     # 说话者/执行者
    text: "师父，我准备好了。"        # 原文
    emotion: "坚定"                  # 情绪标签
    action: "手势"                   # 动作类型
    subtext: "内心充满忐忑但不愿表露"  # 🆕 v2.0 潜台词
    beat_type: "setup"               # 🆕 v2.0 节拍类型
    visual_hint: "中景双人镜头，焦点在林风握剑的手"  # 🆕 v2.0 视觉提示
    parenthetical: ""                # 括号提示（表演指导）
```

| 字段 | 类型 | 必填 | v2.0 新增 | 说明 |
|------|------|------|-----------|------|
| `element_id` | string | ✅ | | 唯一ID，格式 `{chapter}.{scene}.{seq}` |
| `type` | string | ✅ | | 元素类型，见[枚举值](#element_type) |
| `role` | string | ✅ | | 说话者/执行者角色名，旁白为 `"旁白"` |
| `text` | string | ✅ | | 原文内容（不润色不改写） |
| `emotion` | string | | | 情绪标签 |
| `action` | string | | | 动作类型（手势/移动/表情等） |
| `subtext` | string | | ✅ | 潜台词，仅 `dialogue` 类型填写 |
| `beat_type` | string | | ✅ | 节拍类型，见[枚举值](#beat_type) |
| `visual_hint` | string | | ✅ | 影视画面呈现建议（镜头语言） |
| `parenthetical` | string | | | 括号提示（表演指导，如"低声""激动"） |

### subtext 潜台词说明

潜台词揭露角色说某句话时的**真实意图或内心想法**，而不是字面意思。

| 对白 | 潜台词示例 |
|------|-----------|
| "没事。" | 其实有事，但不想让对方担心 |
| "你走吧。" | 希望你留下 |
| "我恨你。" | 我其实很在乎你 |
| "不用了。" | 想要但不好意思接受 |

### visual_hint 视觉提示说明

视觉提示用镜头语言描述该段内容在影视中的呈现方式。应具体、可操作：

- ✅ "特写角色手指慢慢握紧剑柄，关节发白"
- ✅ "中景双人镜头，背景虚化的竹林在风中摇曳"
- ✅ "POV 主观视角缓缓推进，穿过门缝看到屋内"
- ❌ "拍好看一点"（太模糊）
- ❌ "此处应有画面"（无信息量）

---

## 7. emotion_curve — 情绪曲线

🆕 v2.0 新增。情绪曲线描述全剧的情绪起伏变化，每个章节对应一个情绪数据点。

```yaml
emotion_curve:
  - chapter_id: 1
    chapter_title: "第一章 初入江湖"
    emotion_peak:
      emotion: "喜悦"
      frequency: 8
      intensity: 6.5
    suspense_hook: "黑衣人暗中跟踪..."
    scenes:
      - scene_id: "1.1"
        atmosphere: "平静"
        dominant_emotion: "坚定"
      - scene_id: "1.2"
        atmosphere: "紧张"
        dominant_emotion: "恐惧"
      - scene_id: "1.3"
        atmosphere: "温馨"
        dominant_emotion: "温柔"
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `chapter_id` | int | ✅ | 章节ID |
| `chapter_title` | string | | 章节标题 |
根节点 | `emotion_peak` | object | | 本章情绪峰值 |
| `emotion_peak.emotion` | string | | 峰值情绪 |
| `emotion_peak.frequency` | int | | 出现频次 |
| `emotion_peak.intensity` | float | | 强度 (0-10) |
| `suspense_hook` | string | | 悬念念钩子 |
| `scenes` | array | | 各场景情绪 |
| `scenes[].scene_id` | string | | 场景ID |
| `scenes[].atmosphere` | string | | 场景氛围 |
| `scenes[].dominant_emotion` | string | | 主导演情绪 |

---

## 8. 枚举值参考

### element_type

元素类型，描述该片段在剧本中的叙事功能。

| 值 | 说明 |
|----|------|
| `dialogue` | 角色对白（有引号包裹的台词） |
| `narration` | 旁白/叙述（第三人称叙述） |
| `action` | 动作描写（角色肢体动作） |
| `description` | 场景/环境描写（静态描述） |

### role_type

角色类型，描述角色在故事中的功能定位。

| 值 | 说明 |
|----|------|
| `protagonist` | 主角 |
| `antagonist` | 反派/对手 |
| `supporting` | 重要配角 |
| `minor` | 次要角色 |
| `cameo` | 客串角色 |

### beat_type

节拍类型，描述该元素在叙事节拍中的位置。

| 值 | 说明 | 特征关键词 |
|----|------|-----------|
| `setup` | 铺垫 | 介绍、建立、暗示 |
| `confrontation` | 冲突 | 争执、对抗、战斗、反驳 |
| `payoff` | 收尾 | 完成、揭示、解决、胜利 |
| `transition` | 过渡 | 时间跳跃、地点切换、转场 |
| `revelation` | 揭示 | 真相暴露、秘密揭露、反转 |

### target_medium

目标媒介类型。

| 值 | 说明 |
|----|------|
| `film` | 电影（90-180分钟） |
| `tv_series` | 电视剧（多集连续） |
| `stage` | 舞台剧 |
| `animation` | 动画 |
| `web_series` | 网络短剧/微短剧 |

### atmosphere

场景氛围。

| 值 | 适用场景 |
|----|---------|
| `欢快` | 喜剧、轻松对话、庆祝 |
| `忧伤` | 离别、失落、回忆 |
| `紧张` | 对峙、追逐、危险 |
| `平静` | 日常、过渡、内心独白 |
| `温馨` | 亲情、友情、爱情温馨时刻 |
| `悬疑` | 谜团、未知、伏笔揭示前 |
| `阴暗` | 阴谋、背叛、黑暗场景 |
| `中性` | 无明确情感倾向 |
| `激昂` | 决战、高潮、觉醒 |
| `忧郁` | 压抑、迷茫、内心挣扎 |
| `压抑` | 控制、压迫、隐忍 |
| `冷峻` | 冷静、克制、权谋 |

### time

场景时间。

| 值 |
|----|
| `清晨` `早晨` `上午` `中午` `下午` `傍晚` `黄昏` `夜晚` `深夜` `黎明` `未指定` |

---

## 9. 完整示例

```yaml
script:
  metadata:
    script_title: "剑影江湖"
    original_work: "剑影江湖"
    original_author: "江湖客"
    adapter: "Novel-to-Script Pro v2.0"
    created_date: "2026-06-06"
    version: "2.0-draft"
    schema_version: "2.0"
    genre:
      - "武侠"
      - "成长"
    target_medium: "tv_series"
    language: "zh-CN"
    total_chapters_adapted: 3
    adapted_chapter_ids: [1, 2, 3]
    pipeline_version: "2.0"
    statistics:
      total_elements: 245
      dialogue_count: 98
      narration_count: 112
      action_count: 35
      estimated_scenes: 24

  characters:
    - character_id: "CHAR-001"
      name: "林风"
      aliases: ["风儿", "小林"]
      role_type: "protagonist"
      description: "十七岁少年剑客，师从青云门，性格正直勇敢但经验不足"
      traits: ["勇敢", "正直", "冲动", "重情义"]
      relationships:
        - target: "苏婉儿"
          relation: "青梅竹马"
        - target: "赵铁柱"
          relation: "挚友"
        - target: "青云道长"
          relation: "恩师"
      arc_summary: "从懵懂莽撞的少年成长为肩负江湖大义的一代剑侠"
      visual_design: "白衣青衫，腰间斜挎一柄古朴长剑，剑鞘刻有流云纹"
      first_appearance: "第1章"
      last_appearance: "第40章"
      total_appearances: 420
      primary_emotion: "坚定"
      arc_stage: "development"

    - character_id: "CHAR-002"
      name: "苏婉儿"
      aliases: ["婉儿"]
      role_type: "supporting"
      description: "青云门掌门之女，聪慧温柔，医术高超"
      traits: ["聪慧", "温柔", "坚韧", "善良"]
      relationships:
        - target: "林风"
          relation: "青梅竹马"
      arc_summary: "从被保护的掌门千金蜕变为独立坚强的女性"
      visual_design: "淡绿长裙，头戴银簪，腰间悬一枚玉佩"
      first_appearance: "第1章"
      last_appearance: "第40章"
      total_appearances: 310
      primary_emotion: "温柔"
      arc_stage: "development"

  chapters:
    - chapter_id: 1
      chapter_title: "第一章 初入江湖"
      source_chapter: 1
      summary: "少年林风在师父的嘱托下离开青云门，踏上江湖之路。途中遇到神秘黑衣人的袭击，被路过的苏婉儿所救。"
      scene_count: 3
      element_count: 85
      emotion_peak:
        emotion: "紧张"
        frequency: 12
        intensity: 7.5
      suspense_hook: "黑衣人临走前留下一句话：'你父亲的事，还没完。'"
      scenes:
        - scene_id: "1.1"
          scene_number: 1
          location: "室外-山野"
          time: "清晨"
          atmosphere: "平静"
          characters_present:
            - "林风"
            - "青云道长"
          props_needed:
            - "剑"
            - "包袱"
          element_count: 25
          elements:
            - element_id: "1.1.1"
              type: "dialogue"
              role: "青云道长"
              text: "风儿，江湖险恶，为师能教你的，都已经教了。"
              emotion: "平静"
              action: ""
              subtext: "对你的成长既欣慰又担忧"
              beat_type: "setup"
              visual_hint: "中景双人镜头，晨光逆光，青云道长背对朝阳"

            - element_id: "1.1.2"
              type: "dialogue"
              role: "林风"
              text: "师父，我不会让您失望的。"
              emotion: "坚定"
              action: "手势"
              subtext: "虽然内心忐忑，但不愿让师父担心"
              beat_type: "setup"
              visual_hint: "特写林风握剑的手，指节因用力而发白"

            - element_id: "1.1.3"
              type: "narration"
              role: "旁白"
              text: "晨雾渐散，远山如黛。林风踏上了这条不归路。"
              emotion: "平静"
              action: ""
              subtext: ""
              beat_type: "transition"
              visual_hint: "大远景，林风小小的身影消失在山道尽头，晨雾缓缓散去"

  emotion_curve:
    - chapter_id: 1
      chapter_title: "第一章 初入江湖"
      emotion_peak:
        emotion: "紧张"
        frequency: 12
        intensity: 7.5
      suspense_hook: "黑衣人临走前留下一句话：'你父亲的事，还没完。'"
      scenes:
        - scene_id: "1.1"
          atmosphere: "平静"
          dominant_emotion: "坚定"
        - scene_id: "1.2"
          atmosphere: "紧张"
          dominant_emotion: "恐惧"
        - scene_id: "1.3"
          atmosphere: "温馨"
          dominant_emotion: "温柔"
```

---

## 10. 校验规则

使用 `builders/schema_v2.py` 中的 `SchemaValidator` 进行校验。

### 结构完整性检查

- [x] 根节点 `script` 必须存在
- [x] `metadata`、`characters`、`chapters` 必须存在
- [x] 每个章节至少包含 1 个场景
- [x] 每个场景至少包含 1 个元素
- [x] `character_id` 唯一，格式 `CHAR-NNN`
- [x] `chapter_id` 和 `scene_id` 唯一

### 数据一致性检查

- [x] `element_count` 与实际元素数量一致
- [x] `scene_count` 与实际场景数量一致
- [x] `dialogue_count + narration_count + action_count <= total_elements`
- [x] `emotion_curve` 长度与 `chapters` 长度一致

### 字段值域检查

- [x] `type` 在 `dialogue | narration | action | description` 中
- [x] `role_type` 在 `protagonist | antagonist | supporting | minor | cameo` 中
- [x] `beat_type` 在 `setup | confrontation | payoff | transition | revelation` 中
- [x] `target_medium` 在 `film | tv_series | stage | animation | web_series` 中
- [x] `subtext` 仅对 `type=dialogue` 的元素有值

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2025 | 初始版本：三层结构 (Chapter → Scene → Element)，基础字段 |
| 2.0 | 2026-06-06 | 新增：genre, target_medium, pipeline_version, relationships, arc_summary, visual_design, characters_present, props_needed, subtext, beat_type, visual_hint, emotion_curve |

---

> 本 Schema 是 Novel-to-Script Pro 所有组件的数据交换标准。  
> 所有 Agent 产出、Builder 输出、Validator 校验均以此为基础。
