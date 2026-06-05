"""
小说文本抽取模块 - 基于 LLM 的小说文本结构化提取
从小说文本中提取角色、对白、旁白、情绪、动作等信息
"""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import yaml
from openai import OpenAI
from tqdm import tqdm


class NovelExtractor:
    """小说文本结构化抽取器"""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        llm_cfg = self.config["llm"]
        proc_cfg = self.config["processing"]

        self.client = OpenAI(
            api_key=llm_cfg["api_key"],
            base_url=llm_cfg["base_url"],
        )
        self.model = llm_cfg["model"]
        self.temperature = llm_cfg["temperature"]
        self.max_tokens = llm_cfg["max_tokens"]
        self.window_size = proc_cfg["window_size"]
        self.overlap_rate = proc_cfg["overlap_rate"]
        self.max_workers = proc_cfg["max_workers"]
        self.retry_times = proc_cfg["retry_times"]

    def _build_extraction_prompt(self, text: str, chapter_context: str = "") -> str:
        """构建文本提取的 Prompt"""
        context_section = ""
        if chapter_context:
            context_section = f"\n\n前文章节摘要（供参考）：\n{chapter_context}"

        return f"""你是一位资深的剧本分析师。请从以下小说文本中提取所有与剧本创作相关的结构化信息。

要求：
1. 识别每个片段的类型：narration（旁白/叙述）、dialogue（对白）、action（动作描写）、description（场景/环境描写）
2. 对于对白，准确识别说话角色名称
3. 对于旁白/叙述，role 设置为 "旁白"
4. 提取情绪标签（如：愤怒、喜悦、悲伤、紧张、平静、焦虑、温柔、惊讶、恐惧、厌恶等）
5. 提取动作描述（角色正在做什么）
6. 保持原文内容不变，不要润色或改写

请严格输出 JSON 数组，用 ```json ``` 包裹，格式如下：
```json
[
  {{
    "id": 1,
    "type": "dialogue",
    "role": "角色名",
    "text": "对白内容",
    "emotion": "情绪标签",
    "action": "动作描述"
  }},
  {{
    "id": 2,
    "type": "narration",
    "role": "旁白",
    "text": "叙述内容",
    "emotion": "",
    "action": ""
  }}
]
```

注意：
- 不要遗漏任何角色对白
- 不要合并不同角色的台词
- 保持文本的原始顺序
- 如果无法确定情绪或动作，留空字符串即可{context_section}

小说文本：
{text}"""

    def _call_llm(self, prompt: str) -> list:
        """调用 LLM API，带重试机制"""
        for attempt in range(self.retry_times):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一位专业的剧本分析师，擅长从小说文本中提取结构化信息。请严格输出 JSON 格式。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stream=False,
                )
                raw = resp.choices[0].message.content

                # 提取 JSON
                m = re.search(r"```json\s*(\[[\s\S]*?\])\s*```", raw)
                if m:
                    return json.loads(m.group(1))
                # 尝试直接解析
                json_str = raw.strip()
                if json_str.startswith("["):
                    return json.loads(json_str)
                # 最后尝试：提取任何 JSON 数组
                m2 = re.search(r"\[[\s\S]*\]", raw)
                if m2:
                    return json.loads(m2.group(0))

                print(f"⚠️  无法解析 JSON 响应 (attempt {attempt + 1}): {raw[:200]}...")
                if attempt < self.retry_times - 1:
                    time.sleep(2**attempt)  # 指数退避

            except Exception as e:
                print(f"❌ API 调用失败 (attempt {attempt + 1}): {e}")
                if attempt < self.retry_times - 1:
                    time.sleep(2**attempt)

        return []

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

    def extract_from_chapter(
        self,
        chapter_text: str,
        chapter_id: int,
        chapter_title: str = "",
        chapter_context: str = "",
    ) -> list:
        """从单个章节中提取结构化信息（使用滑窗法处理长文本）"""
        lines = chapter_text.split("\n")
        # 过滤空行
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

        # 去重 + 重新排序
        all_elements = self._deduplicate_and_sort(all_elements)

        # 标注章节信息
        for elem in all_elements:
            elem["chapter_id"] = chapter_id
            elem["chapter_title"] = chapter_title

        return all_elements

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

    def generate_chapter_summary(self, elements: list, max_length: int = 200) -> str:
        """根据提取结果生成章节摘要（用于跨章节上下文）"""
        if not elements:
            return ""

        # 收集关键信息
        characters = set()
        dialogue_count = 0
        narration_count = 0
        key_events = []

        for elem in elements:
            if elem.get("role") and elem["role"] != "旁白":
                characters.add(elem["role"])
            if elem.get("type") == "dialogue":
                dialogue_count += 1
            elif elem.get("type") == "narration":
                narration_count += 1
            # 收集前几个元素作为关键事件
            if elem.get("type") == "narration" and len(key_events) < 3:
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
