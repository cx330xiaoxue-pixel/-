"""
模拟抽取器 - 使用规则匹配从小说中提取结构化信息
用于在不调用 API 的情况下测试完整流程
"""

import re


class MockExtractor:
    """基于规则的小说文本结构化提取器（不需要 API Key）"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.window_size = 40
        self.overlap_rate = 0.5
        self.max_workers = 1
        self.retry_times = 1

    def extract_from_text(
        self, text: str, chapter_context: str = "", window_idx: int = 0
    ) -> list:
        """从单段文本中提取结构化信息（规则匹配）"""
        elements = []
        idx = 0

        # 分行处理
        lines = text.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 1. 检测对话：中文引号包裹的内容
            dialogue_matches = re.findall(
                r'[“"]([^"”“]+)[”"]',
                line
            )

            if dialogue_matches:
                # 提取对话前的角色信息
                role = self._find_speaker(line)
                for d_text in dialogue_matches:
                    if d_text.strip():
                        idx += 1
                        elements.append(
                            {
                                "id": idx,
                                "type": "dialogue",
                                "role": role,
                                "text": d_text.strip(),
                                "emotion": self._detect_emotion(d_text),
                                "action": self._detect_action(line),
                                "window_idx": window_idx,
                            }
                        )

            # 2. 检测动作描写
            elif self._is_action_line(line):
                idx += 1
                elements.append(
                    {
                        "id": idx,
                        "type": "action",
                        "role": self._find_actor(line) or "旁白",
                        "text": line,
                        "emotion": self._detect_emotion(line),
                        "action": self._detect_action(line),
                        "window_idx": window_idx,
                    }
                )

            # 3. 其余为旁白/叙述
            else:
                idx += 1
                elements.append(
                    {
                        "id": idx,
                        "type": "narration",
                        "role": "旁白",
                        "text": line,
                        "emotion": self._detect_emotion(line),
                        "action": self._detect_action(line),
                        "window_idx": window_idx,
                    }
                )

        return elements

    def _find_speaker(self, line: str) -> str:
        """从行首找到说话者"""
        # 模式: "XXX 说", "XXX说道", "XXX笑道", "XXX问"等
        prefix = line.split("“")[0] if "“" in line else line.split('"')[0] if '"' in line else ""
        prefix = prefix.strip()

        # 提取角色名（常见模式）
        patterns = [
            r"^(.+?)(?:说|说道|道|问|答|喊道|叫道|笑道|怒道|叹道|冷声道|轻声道|大声道|低声道|问道|答道|开口道)",
            r"^(.+?)(?:微微一笑|冷笑|苦笑|笑了笑|怒喝|哼了一声|点了点头|摇了摇头)",
            r"^(.+?)(?:走|来|去|站|坐|跑|跳|看|望|转|回|抬|低|伸|挥|抓|握|拿|放|推|拉|拍|踢|指)",
            r"^(.{1,4})$",
        ]
        for pattern in patterns:
            m = re.match(pattern, prefix)
            if m:
                name = m.group(1).strip()
                # 过滤非人名词
                if name and len(name) <= 4 and not re.search(r"[，。！？、；：]", name):
                    return name

        # 默认使用前两个字符为名字（如果是常见人名模式）
        if len(prefix) >= 2 and re.match(r"^[一-鿿]{2,3}$", prefix[:2]):
            return prefix[:2]

        return "角色"

    def _find_actor(self, line: str) -> str:
        """找到动作的执行者"""
        # 简单: 取前两个字或词
        m = re.match(r"^([一-鿿]{2,4})", line)
        if m:
            name = m.group(1)
            # 排除一些常见的非人名词
            non_person = {"清晨", "黄昏", "月光", "天色", "山风", "竹叶", "树叶", "云雾", "天空", "大地", "江湖", "客栈", "房间", "街道"}
            if name not in non_person:
                return name
        return None

    def _is_action_line(self, line: str) -> bool:
        """判断是否是动作描写行"""
        action_keywords = ["挥", "击", "踢", "踹", "跃", "跳", "跑", "冲", "闪", "躲", "拔", "抽出", "握", "抓", "拍", "飞", "舞", "转", "转身", "回头", "走出", "走进"]
        return any(kw in line for kw in action_keywords)

    def _detect_emotion(self, text: str) -> str:
        """检测文本中的情绪"""
        emotion_map = {
            "笑": "喜悦",
            "怒": "愤怒",
            "咬牙切齿": "愤怒",
            "泪": "悲伤",
            "哭": "悲伤",
            "惊": "惊讶",
            "害怕": "恐惧",
            "恐惧": "恐惧",
            "紧张": "紧张",
            "颤抖": "紧张",
            "温柔": "温柔",
            "轻轻": "温柔",
            "平静": "平静",
            "淡淡": "平静",
            "严肃": "严肃",
            "郑重": "严肃",
        }
        for keyword, emotion in emotion_map.items():
            if keyword in text:
                return emotion
        return ""

    def _detect_action(self, text: str) -> str:
        """检测文本中的动作"""
        action_patterns = [
            (r"(转身|回头|走向|走进|走出|跑向|奔向)", "移动"),
            (r"(挥手|抬手|伸手|挥拳|出掌)", "手势"),
            (r"(点头|摇头|低头|抬头|回头)", "头部动作"),
            (r"(拔剑|拔刀|出鞘|挥舞)", "武器动作"),
            (r"(跪下|躬身|鞠躬|行礼)", "礼仪动作"),
            (r"(微笑|笑|苦笑|冷笑|怒笑)", "表情"),
            (r"(叹气|叹息|深吸|呼气)", "呼吸"),
        ]
        for pattern, action_type in action_patterns:
            if re.search(pattern, text):
                return action_type
        return ""

    def extract_from_chapter(
        self,
        chapter_text: str,
        chapter_id: int,
        chapter_title: str = "",
        chapter_context: str = "",
    ) -> list:
        """从单个章节中提取结构化信息"""
        lines = chapter_text.split("\n")
        lines = [l for l in lines if l.strip()]

        if not lines:
            print(f"  章节 {chapter_id} 为空，跳过")
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
        for w_idx, w_text in windows:
            elements = self.extract_from_text(w_text, chapter_context, w_idx)
            all_elements.extend(elements)

        # 去重 + 排序
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

        for idx, elem in enumerate(unique, start=1):
            elem["global_id"] = idx

        return unique

    def generate_chapter_summary(self, elements: list, max_length: int = 200) -> str:
        """根据提取结果生成章节摘要"""
        if not elements:
            return ""

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
