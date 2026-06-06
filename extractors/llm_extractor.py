"""
小说文本LLM抽取器 — 基于 LLM 的小说文本结构化提取
从小说文本中提取角色、对白、旁白、情绪、动作、潜台词、节拍类型等信息

重构自 novel-to-script-yaml/extractor.py
增强:
  - 多 Provider 支持（DeepSeek / OpenAI / Custom）
  - 角色专项抽取（extract_characters）
  - 新增 subtext（潜台词）和 beat_type（节拍类型）字段
  - 更强的 JSON 解析容错
  - 支持 dict 配置（不限于 YAML 文件）
"""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import yaml
from openai import OpenAI
from tqdm import tqdm


class LLMExtractor:
    """小说文本结构化抽取器（LLM 驱动）"""

    def __init__(self, config=None, config_path: str = None):
        """
        初始化抽取器。

        Args:
            config: 配置字典（优先于 config_path）
            config_path: YAML 配置文件路径
        """
        if config is not None:
            self.config = config
        elif config_path:
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
        else:
            raise ValueError("必须提供 config 字典或 config_path 路径")

        llm_cfg = self.config.get("llm", {})
        proc_cfg = self.config.get("processing", {})
        output_cfg = self.config.get("output", {})

        # 多 Provider 支持
        provider = llm_cfg.get("provider", "deepseek")
        api_key = llm_cfg.get("api_key", "")
        base_url = llm_cfg.get("base_url", "")

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = llm_cfg.get("model", "deepseek-chat")
        self.temperature = llm_cfg.get("temperature", 0.7)
        self.max_tokens = llm_cfg.get("max_tokens", 8192)
        self.window_size = proc_cfg.get("window_size", 40)
        self.overlap_rate = proc_cfg.get("overlap_rate", 0.5)
        self.max_workers = proc_cfg.get("max_workers", 4)
        self.retry_times = proc_cfg.get("retry_times", 3)
        self.include_subtext = output_cfg.get("include_subtext", True)
        self.include_visual_hint = output_cfg.get("include_visual_hint", True)

        # 轻量 LLM（用于摘要等简单任务）
        light_cfg = self.config.get("llm_light", llm_cfg)
        self.light_client = OpenAI(
            api_key=light_cfg.get("api_key", api_key),
            base_url=light_cfg.get("base_url", base_url),
        )
        self.light_model = light_cfg.get("model", self.model)

    # ═══════════════════════════════════════════════════════════
    # Prompt 构建
    # ═══════════════════════════════════════════════════════════

    def _build_extraction_prompt(self, text: str, chapter_context: str = "") -> str:
        """构建文本提取的 Prompt（增强版：含 subtext + beat_type + visual_hint）"""
        context_section = ""
        if chapter_context:
            context_section = f"""
前文章节摘要（供参考，保持角色和情节连贯性）：
{chapter_context}
"""

        subtext_requirement = ""
        if self.include_subtext:
            subtext_requirement = """
7. 对于对白（dialogue），推断潜台词（subtext）：角色说这句话的真实意图或内心想法
8. 标注节拍类型（beat_type）：setup（铺垫）/ confrontation（冲突）/ payoff（收尾）/ transition（过渡）/ revelation（揭示）"""

        visual_requirement = ""
        if self.include_visual_hint:
            visual_requirement = """
9. 为每个元素提供视觉化提示（visual_hint）：这段内容在影视中应如何用画面呈现"""

        return f"""你是一位资深的剧本分析师和影视编剧。请从以下小说文本中提取所有与剧本创作相关的结构化信息。

要求：
1. 识别每个片段的类型：dialogue（对白）、narration（旁白/叙述）、action（动作描写）、description（场景/环境描写）
2. 对于对白，准确识别说话角色名称（注意别名和称呼变化）
3. 对于旁白/叙述，role 设置为 "旁白"
4. 提取情绪标签（如：愤怒、喜悦、悲伤、紧张、平静、焦虑、温柔、惊讶、恐惧、厌恶、坚定、犹豫、轻蔑、嫉妒、愧疚）
5. 提取动作描述——角色正在做什么
6. 保持原文内容不变，不要润色或改写
{subtext_requirement}
{visual_requirement}

请严格输出 JSON 数组，用 ```json ``` 包裹，格式如下：
```json
[
  {{
    "id": 1,
    "type": "dialogue",
    "role": "角色名",
    "text": "对白内容",
    "emotion": "情绪标签",
    "action": "动作描述",
    "subtext": "潜台词（仅dialogue类型填写）",
    "beat_type": "setup|confrontation|payoff|transition|revelation",
    "visual_hint": "影视画面呈现建议"
  }},
  {{
    "id": 2,
    "type": "narration",
    "role": "旁白",
    "text": "叙述内容",
    "emotion": "",
    "action": "",
    "subtext": "",
    "beat_type": "transition",
    "visual_hint": "画面呈现建议"
  }}
]
```

注意：
- 不要遗漏任何角色对白
- 不要合并不同角色的台词
- 保持文本的原始顺序
- 如果无法确定情绪或动作，留空字符串即可
- 对白的 role 必须是角色名（不是"角色"），旁白/叙述的 role 必须是"旁白"
- 潜台词（subtext）仅对 type=dialogue 的元素填写，揭示角色说这句话的真实意图
- 视觉化提示（visual_hint）要具体，用镜头语言描述，如"特写角色手指握紧剑柄"
{context_section}

小说文本：
{text}"""

    def _build_character_extraction_prompt(self, text: str) -> str:
        """构建角色专项抽取的 Prompt"""
        return f"""你是一位专业的剧本角色分析师。请从以下小说文本中提取所有角色信息。

请严格输出 JSON 数组，用 ```json ``` 包裹，格式如下：
```json
[
  {{
    "name": "角色名",
    "aliases": ["别名1", "别名2"],
    "role_type": "protagonist|antagonist|supporting|minor|cameo",
    "description": "角色外貌、身份、性格的简要描述",
    "traits": ["性格特征1", "性格特征2"],
    "relationships": [
      {{"target": "另一个角色名", "relation": "关系描述（师徒/恋人/仇敌/朋友/家人/同门等）"}}
    ],
    "first_appearance_hint": "首次出现的场景描述"
  }}
]
```

注意：
- 识别所有有名字或有对白的角色
- 别名包括：绰号、敬称、小名、道号等
- 关系要尽可能完整
- 如果信息不足，字段可以为空字符串或空数组

小说文本：
{text}"""

    def _build_chapter_summary_prompt(self, elements: list, characters: list) -> str:
        """构建章节摘要 Prompt"""
        char_names = ", ".join([c.get("name", "?") for c in characters[:10]])
        elements_brief = []
        for elem in elements[:15]:
            role = elem.get("role", "?")
            etype = elem.get("type", "?")
            text_preview = elem.get("text", "")[:60]
            elements_brief.append(f"[{etype}] {role}: {text_preview}")

        elements_text = "\n".join(elements_brief)

        return f"""请基于以下信息，写一段 150-200 字的章节摘要。包括：主要事件、角色动态、情节推进。

出场角色：{char_names}

关键片段：
{elements_text}

请直接输出摘要文本，不需要 JSON 或其他格式。"""

    # ═══════════════════════════════════════════════════════════
    # LLM 调用
    # ═══════════════════════════════════════════════════════════

    def _call_llm(self, prompt: str, system_prompt: str = None,
                  use_light: bool = False, expect_json: bool = True) -> list:
        """调用 LLM API，带重试机制和多层 JSON 解析容错"""
        if system_prompt is None:
            system_prompt = "你是一位专业的剧本分析师，擅长从小说文本中提取结构化信息。请严格输出 JSON 格式。"

        client = self.light_client if use_light else self.client
        model = self.light_model if use_light else self.model
        max_tokens = 2048 if use_light else self.max_tokens
        temperature = 0.3 if use_light else self.temperature

        for attempt in range(self.retry_times):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                )
                raw = resp.choices[0].message.content

                if not expect_json:
                    return raw.strip()

                # ── 多层 JSON 解析 ──
                parsed = self._parse_json_response(raw)
                if parsed is not None:
                    return parsed

                print(f"⚠️  无法解析 JSON (attempt {attempt + 1}): {raw[:200]}...")
                if attempt < self.retry_times - 1:
                    time.sleep(2 ** attempt)  # 指数退避

            except Exception as e:
                print(f"❌ API 调用失败 (attempt {attempt + 1}): {e}")
                if attempt < self.retry_times - 1:
                    time.sleep(2 ** attempt)

        return []

    def _parse_json_response(self, raw: str) -> Optional[list]:
        """多层 JSON 解析策略，提高容错率"""
        # 策略1: ```json ``` 代码块
        m = re.search(r"```json\s*(\[[\s\S]*?\])\s*```", raw)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        # 策略2: 直接 JSON 数组
        json_str = raw.strip()
        if json_str.startswith("["):
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # 策略3: 正则提取 JSON 数组（最宽松）
        m2 = re.search(r"\[[\s\S]*\]", raw)
        if m2:
            try:
                return json.loads(m2.group(0))
            except json.JSONDecodeError:
                pass

        # 策略4: 尝试修复常见错误（尾逗号、单引号等）
        m3 = re.search(r"\[[\s\S]*\]", raw)
        if m3:
            try:
                fixed = m3.group(0)
                # 移除尾随逗号
                fixed = re.sub(r",\s*]", "]", fixed)
                fixed = re.sub(r",\s*}", "}", fixed)
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

        return None

    # ═══════════════════════════════════════════════════════════
    # 主要抽取方法
    # ═══════════════════════════════════════════════════════════

    def extract_from_text(
        self, text: str, chapter_context: str = "", window_idx: int = 0
    ) -> list:
        """从单段文本中提取结构化信息"""
        prompt = self._build_extraction_prompt(text, chapter_context)
        elements = self._call_llm(prompt)

        # 标注窗口索引
        for elem in elements:
            elem["window_idx"] = window_idx

        return elements

    def extract_characters(self, text: str) -> list:
        """从文本中专项提取角色信息"""
        prompt = self._build_character_extraction_prompt(text)
        return self._call_llm(prompt, expect_json=True)

    def extract_from_chapter(
        self,
        chapter_text: str,
        chapter_id: int,
        chapter_title: str = "",
        chapter_context: str = "",
    ) -> list:
        """从单个章节中提取结构化信息（使用滑窗法处理长文本）"""
        lines = chapter_text.split("\n")
        # 过滤全空行
        lines = [l for l in lines if l.strip()]

        if not lines:
            print(f"⚠️  章节 {chapter_id} 为空，跳过")
            return []

        stride = max(1, int(self.window_size * (1 - self.overlap_rate)))
        windows = []
        for start in range(0, len(lines), stride):
            window_lines = lines[start : start + self.window_size]
            if not window_lines:
                break
            window_text = "\n".join(window_lines)
            window_idx = start // stride + 1
            windows.append((window_idx, window_text))

        print(f"  章节 {chapter_id} 分 {len(windows)} 个滑窗处理")

        all_elements = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self.extract_from_text, w_text, chapter_context, w_idx
                ): w_idx
                for w_idx, w_text in windows
            }

            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc=f"  处理章节 {chapter_id}",
            ):
                try:
                    elements = future.result()
                    all_elements.extend(elements)
                except Exception as e:
                    print(f"  ❌ 滑窗处理失败: {e}")

        # 去重 + 排序
        all_elements = self._deduplicate_and_sort(all_elements)

        # 标注章节信息
        for elem in all_elements:
            elem["chapter_id"] = chapter_id
            elem["chapter_title"] = chapter_title

        return all_elements

    def extract_characters_from_chapter(
        self, chapter_text: str, chapter_id: int
    ) -> list:
        """从单个章节中提取角色信息"""
        # 取前 3000 字符做角色提取（足够识别主要角色）
        text_sample = chapter_text[:3000]
        characters = self.extract_characters(text_sample)
        for char in characters:
            char["first_seen_chapter"] = chapter_id
        return characters

    def generate_chapter_summary(
        self, elements: list, characters: list = None, use_llm: bool = False
    ) -> str:
        """根据提取结果生成章节摘要"""
        if not elements:
            return ""

        if use_llm and characters is not None:
            prompt = self._build_chapter_summary_prompt(elements, characters)
            result = self._call_llm(prompt, use_light=True, expect_json=False)
            if result:
                return result[:250]

        # 规则生成摘要（fallback）
        return self._rule_based_summary(elements)

    # ═══════════════════════════════════════════════════════════
    # 去重与排序
    # ═══════════════════════════════════════════════════════════

    def _deduplicate_and_sort(self, elements: list) -> list:
        """去重并按窗口索引和 ID 排序"""
        seen_texts = set()
        unique = []
        for elem in sorted(
            elements, key=lambda e: (e.get("window_idx", 0), e.get("id", 0))
        ):
            text = elem.get("text", "").strip()
            if text and text not in seen_texts:
                seen_texts.add(text)
                unique.append(elem)

        # 重新编号
        for idx, elem in enumerate(unique, start=1):
            elem["global_id"] = idx

        return unique

    def _rule_based_summary(self, elements: list, max_length: int = 200) -> str:
        """基于规则生成章节摘要（不调用LLM）"""
        characters = set()
        dialogue_count = 0
        narration_count = 0
        key_events = []

        for elem in elements:
            role = elem.get("role", "")
            if role and role != "旁白":
                characters.add(role)
            etype = elem.get("type", "")
            if etype == "dialogue":
                dialogue_count += 1
            elif etype in ("narration", "description"):
                narration_count += 1
                if len(key_events) < 3:
                    text = elem.get("text", "")
                    if len(text) > 80:
                        key_events.append(text[:80] + "...")
                    else:
                        key_events.append(text)

        summary = f"出场角色：{'、'.join(sorted(characters)) if characters else '无'}。"
        summary += f"对话片段 {dialogue_count} 个，叙述片段 {narration_count} 个。"
        if key_events:
            summary += f"关键场景：{'；'.join(key_events)}"

        return summary[:max_length]
