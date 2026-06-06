"""
规则抽取器 — 使用正则/规则匹配从小说中提取结构化信息
用于在不调用 API 的情况下测试完整流程（离线模式）

重构自 novel-to-script-yaml/mock_extractor.py
增强:
  - 更多角色识别模式（对话前缀、动作主语、称呼系统）
  - 场景切换检测（地点变化、时间变化、视角切换）
  - 更细粒度的情绪/动作分类
  - 角色别名自动关联
"""

import re
from typing import Optional


class RuleExtractor:
    """基于规则的小说文本结构化提取器（无需 API Key）"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.window_size = self.config.get("processing", {}).get("window_size", 40)
        self.overlap_rate = self.config.get("processing", {}).get("overlap_rate", 0.5)

    # ═══════════════════════════════════════════════════════════
    # 主入口
    # ═══════════════════════════════════════════════════════════

    def extract_from_text(
        self, text: str, chapter_context: str = "", window_idx: int = 0
    ) -> list:
        """从单段文本中提取结构化信息（规则匹配）"""
        elements = []
        idx = 0

        lines = text.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测对话
            dialogue_matches = self._find_dialogues(line)
            if dialogue_matches:
                role = self._find_speaker(line)
                for d_text in dialogue_matches:
                    if d_text.strip():
                        idx += 1
                        elements.append({
                            "id": idx,
                            "type": "dialogue",
                            "role": role,
                            "text": d_text.strip(),
                            "emotion": self._detect_emotion(line + d_text),
                            "action": self._detect_action(line),
                            "subtext": self._infer_subtext(d_text, role),
                            "beat_type": self._infer_beat_type(line, d_text),
                            "visual_hint": self._suggest_visual(line, role),
                            "window_idx": window_idx,
                        })

            # 检测动作描写
            elif self._is_action_line(line):
                idx += 1
                actor = self._find_actor(line) or "角色"
                elements.append({
                    "id": idx,
                    "type": "action",
                    "role": actor,
                    "text": line,
                    "emotion": self._detect_emotion(line),
                    "action": self._detect_action(line),
                    "subtext": "",
                    "beat_type": self._infer_beat_type(line, ""),
                    "visual_hint": self._suggest_visual(line, actor),
                    "window_idx": window_idx,
                })

            # 其余为旁白/叙述
            else:
                idx += 1
                elements.append({
                    "id": idx,
                    "type": "narration",
                    "role": "旁白",
                    "text": line,
                    "emotion": self._detect_emotion(line),
                    "action": self._detect_action(line),
                    "subtext": "",
                    "beat_type": self._infer_beat_type(line, ""),
                    "visual_hint": self._suggest_visual(line, "旁白"),
                    "window_idx": window_idx,
                })

        return elements

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

        print(f"  章节 {chapter_id} 分 {len(windows)} 个滑窗处理（规则模式）")

        all_elements = []
        for w_idx, w_text in windows:
            elements = self.extract_from_text(w_text, chapter_context, w_idx)
            all_elements.extend(elements)

        all_elements = self._deduplicate_and_sort(all_elements)

        for elem in all_elements:
            elem["chapter_id"] = chapter_id
            elem["chapter_title"] = chapter_title

        return all_elements

    def detect_scene_boundaries(self, elements: list) -> list:
        """检测场景边界（地点/时间变化）"""
        boundaries = []
        for i in range(1, len(elements)):
            prev = elements[i - 1]
            curr = elements[i]

            # 地点变化检测
            prev_loc = self._infer_location_from_text(prev.get("text", ""))
            curr_loc = self._infer_location_from_text(curr.get("text", ""))
            if prev_loc and curr_loc and prev_loc != curr_loc:
                boundaries.append({"index": i, "reason": f"地点变化: {prev_loc} → {curr_loc}"})

            # 时间变化检测
            prev_time = self._infer_time_from_text(prev.get("text", ""))
            curr_time = self._infer_time_from_text(curr.get("text", ""))
            if prev_time and curr_time and prev_time != curr_time:
                boundaries.append({"index": i, "reason": f"时间变化: {prev_time} → {curr_time}"})

        return boundaries

    # ═══════════════════════════════════════════════════════════
    # 对话检测
    # ═══════════════════════════════════════════════════════════

    def _find_dialogues(self, line: str) -> list:
        """检测中文对话（引号包裹内容）"""
        # 匹配中文引号
        matches = re.findall(r'[“]([^“”]+)[”]', line)
        if matches:
            return matches
        # 匹配英文引号作为中文对话
        matches = re.findall(r'"([^"]+)"', line)
        if matches:
            return matches
        # 匹配单引号
        matches = re.findall(r"'([^']+)'", line)
        return matches

    def _find_speaker(self, line: str) -> str:
        """从行首找到说话者的角色名"""
        # 取引号前的内容
        prefix = ""
        for quote in ['"', '"', '"', "'"]:
            if quote in line:
                prefix = line.split(quote)[0]
                break

        prefix = prefix.strip()

        # 模式1: "XXX 说/道/问/答/喊/叫/..."
        patterns = [
            r"^(.+?)(?:说|说道|道|问|答|答道|问道|回答|喊道|叫道|笑道|
                       怒道|叹道|冷声道|轻声道|大声道|低声道|喝道|哼道|
                       开口|插嘴|嘀咕|嘟囔|喃喃|厉声|沉声|朗声|
                       苦笑|冷笑|微微一笑|点了点头|摇了摇头|摆了摆手)$",
            r"^(.+?)(?:走|来|去|站|坐|跑|跳|看|望|转|回|抬|低|伸|挥|
                       抓|握|拿|放|推|拉|拍|踢|指|叹|想|暗|悄|忙)$",
            r"^(.{1,4})$",  # 短名字（中文2-4字）
        ]

        for pattern in patterns:
            m = re.match(pattern, prefix, re.VERBOSE)
            if m:
                name = m.group(1).strip()
                # 过滤非人名词
                if name and len(name) <= 5 and not re.search(r"[，。！？、；：…—\d]", name):
                    return name

        # 如果前缀是2-3个中文字符，大概率是角色名
        if len(prefix) >= 2 and re.match(r"^[一-鿿]{2,3}$", prefix):
            return prefix

        return "角色"

    # ═══════════════════════════════════════════════════════════
    # 情绪检测（增强版）
    # ═══════════════════════════════════════════════════════════

    def _detect_emotion(self, text: str) -> str:
        """检测文本中的情绪（增强版，更多关键词）"""
        emotion_map = {
            # 喜悦系
            "笑": "喜悦", "哈哈": "喜悦", "欣喜": "喜悦", "高兴": "喜悦",
            "愉快": "喜悦", "欢": "喜悦", "乐": "喜悦",
            # 愤怒系
            "怒": "愤怒", "咬牙切齿": "愤怒", "气愤": "愤怒", "恼": "愤怒",
            "恨": "愤怒", "勃然大怒": "愤怒", "咆哮": "愤怒",
            # 悲伤系
            "泪": "悲伤", "哭": "悲伤", "悲伤": "悲伤", "难过": "悲伤",
            "伤心": "悲伤", "哀": "悲伤", "泣": "悲伤", "哽咽": "悲伤",
            # 惊讶系
            "惊": "惊讶", "诧异": "惊讶", "愕然": "惊讶", "目瞪口呆": "惊讶",
            "大吃一惊": "惊讶", "愣": "惊讶",
            # 恐惧系
            "害怕": "恐惧", "恐惧": "恐惧", "畏": "恐惧", "颤": "恐惧",
            "抖": "恐惧", "毛骨悚然": "恐惧",
            # 紧张系
            "紧张": "紧张", "焦虑": "焦虑", "不安": "焦虑", "烦躁": "焦虑",
            "忐忑": "紧张", "如坐针毡": "焦虑",
            # 温柔系
            "温柔": "温柔", "轻轻": "温柔", "柔和": "温柔", "温": "温柔",
            "宠溺": "温柔", "柔声": "温柔",
            # 平静系
            "平静": "平静", "淡淡": "平静", "冷静": "平静", "镇定": "平静",
            "从容": "平静", "淡然": "平静",
            # 严肃系
            "严肃": "严肃", "郑重": "严肃", "正色": "严肃", "凛然": "严肃",
            # 坚定系
            "坚定": "坚定", "坚决": "坚定", "毅然": "坚定", "断然": "坚定",
            # 轻蔑系
            "轻蔑": "轻蔑", "不屑": "轻蔑", "鄙": "轻蔑", "嗤笑": "轻蔑",
            "嘲": "轻蔑", "讽刺": "轻蔑",
            # 愧疚系
            "愧疚": "愧疚", "惭愧": "愧疚", "抱歉": "愧疚", "内疚": "愧疚",
            # 嫉妒系
            "嫉妒": "嫉妒", "妒": "嫉妒", "眼红": "嫉妒", "羡": "嫉妒",
        }

        for keyword, emotion in emotion_map.items():
            if keyword in text:
                return emotion
        return ""

    # ═══════════════════════════════════════════════════════════
    # 动作检测（增强版）
    # ═══════════════════════════════════════════════════════════

    def _detect_action(self, text: str) -> str:
        """检测文本中的动作"""
        action_patterns = [
            # 移动
            (r"(转身|回头|走向|走进|走出|跑向|奔向|步|迈步|踱|跨|跃|跳|飞|闪|退|进)", "移动"),
            # 手势
            (r"(挥手|抬手|伸手|挥手|摆|指|点|按|握|抓|拿|放|拍|敲|推|拉|扯|拽|扔)", "手势"),
            # 头部
            (r"(点头|摇头|低头|抬头|回头|歪头|扭头|垂首|昂首)", "头部动作"),
            # 武器
            (r"(拔剑|拔刀|出鞘|挥剑|挥刀|舞|刺|劈|砍|斩|射|掷)", "武器动作"),
            # 礼仪
            (r"(跪下|躬身|鞠躬|行礼|抱拳|作揖|拱手|叩首|磕头)", "礼仪动作"),
            # 表情
            (r"(微笑|笑|苦笑|冷笑|怒笑|皱眉|眯眼|瞪眼|瞥|瞅|凝视|注视|闭眼|睁眼)", "表情"),
            # 呼吸
            (r"(叹气|叹息|深吸|呼气|屏息|喘|呼吸)", "呼吸"),
            # 体态
            (r"(坐|站|蹲|躺|靠|倚|趴|跪|立)", "体态"),
        ]

        for pattern, action_type in action_patterns:
            if re.search(pattern, text):
                return action_type
        return ""

    # ═══════════════════════════════════════════════════════════
    # 节拍类型推断
    # ═══════════════════════════════════════════════════════════

    def _infer_beat_type(self, line: str, dialogue: str = "") -> str:
        """根据文本内容推断节拍类型"""
        combined = line + dialogue

        confrontation_keywords = ["怒", "恨", "吵", "争", "打", "杀", "战", "斗", "反驳", "质问",
                                  "威胁", "警告", "不许", "你敢", "住手", "放肆"]
        revelation_keywords = ["原来", "竟然", "难道", "真相", "秘密", "揭", "暴露", "发现",
                               "原来如此", "难怪", "居然是", "怎么会"]
        payoff_keywords = ["终于", "成功", "完成", "到达", "击败", "胜利", "突破", "领悟",
                           "得手", "到手", "总算"]
        transition_keywords = ["过了", "之后", "等", "随后", "接着", "不久", "第二天",
                               "次日", "翌日", "转眼", "时光", "数月后", "数日后", "深夜"]

        if any(kw in combined for kw in confrontation_keywords):
            return "confrontation"
        if any(kw in combined for kw in revelation_keywords):
            return "revelation"
        if any(kw in combined for kw in payoff_keywords):
            return "payoff"
        if any(kw in combined for kw in transition_keywords):
            return "transition"
        return "setup"

    # ═══════════════════════════════════════════════════════════
    # 视觉化提示
    # ═══════════════════════════════════════════════════════════

    def _suggest_visual(self, text: str, role: str) -> str:
        """为文本生成简单的视觉化呈现建议"""
        hints = []

        if "剑" in text or "刀" in text or "武器" in text:
            hints.append("特写武器细节")
        if "泪" in text or "哭" in text:
            hints.append("面部特写，强调情感")
        if "走" in text or "跑" in text or "追" in text:
            hints.append("动态跟拍或斯坦尼康运镜")
        if "看" in text or "望" in text or "凝视" in text:
            hints.append("POV主观视角镜头")
        if "说" in text or "道" in text:
            hints.append(f"中景双人镜头，焦点在{role}")
        if "风" in text or "雨" in text or "雪" in text:
            hints.append("环境全景，强调天气氛围")
        if "夜" in text or "月" in text:
            hints.append("低照度夜景布光")
        if "晨" in text or "朝阳" in text or "日出" in text:
            hints.append("暖色调晨光，逆光拍摄")

        return "；".join(hints) if hints else ""

    # ═══════════════════════════════════════════════════════════
    # 潜台词推断
    # ═══════════════════════════════════════════════════════════

    def _infer_subtext(self, dialogue: str, role: str) -> str:
        """基于规则推断对白的潜台词"""
        subtext_map = {
            "没事": "其实有事，但不想让对方担心",
            "不用了": "想要但不好意思接受",
            "随便": "其实有想法但不愿表态",
            "你走吧": "希望你留下",
            "我恨你": "我其实很在乎你",
            "没关系": "有关系但选择原谅",
            "凭什么": "感到委屈和不公",
            "我知道了": "可能并不完全理解",
            "你确定": "对对方的决定表示怀疑",
            "太好了": "真诚的喜悦和期待",
            "对不起": "内心充满愧疚，寻求原谅",
            "谢谢你": "真诚感激，可能欠了人情",
            "别管我": "需要帮助但不想示弱",
            "滚开": "愤怒掩盖下的受伤感",
            "为什么": "对命运或他人的质问和不解",
            "保重": "依依不舍，可能不会再见面",
        }
        for keyword, subtext in subtext_map.items():
            if keyword in dialogue:
                return subtext
        return ""

    # ═══════════════════════════════════════════════════════════
    # 角色识别
    # ═══════════════════════════════════════════════════════════

    def _find_actor(self, line: str) -> Optional[str]:
        """找到动作的执行者"""
        # 取行首的中文词
        m = re.match(r"^([一-鿿]{2,4})", line)
        if m:
            name = m.group(1)
            # 排除常见的非人名词
            non_person = {
                "清晨", "黄昏", "月光", "天色", "山风", "竹叶", "树叶",
                "云雾", "天空", "大地", "江湖", "客栈", "房间", "街道",
                "阳光", "微风", "细雨", "雪花", "夜幕", "灯火", "爆竹",
            }
            if name not in non_person:
                return name
        return None

    def _is_action_line(self, line: str) -> bool:
        """判断是否是动作描写行"""
        action_keywords = [
            "挥", "击", "踢", "踹", "跃", "跳", "跑", "冲", "闪", "躲",
            "拔", "抽出", "握", "抓", "拍", "飞", "舞", "转", "转身",
            "回头", "走出", "走进", "奔向", "冲向", "袭来", "攻",
        ]
        # 对白行不是动作行
        if self._find_dialogues(line):
            return False
        return any(kw in line for kw in action_keywords)

    # ═══════════════════════════════════════════════════════════
    # 地点/时间检测
    # ═══════════════════════════════════════════════════════════

    def _infer_location_from_text(self, text: str) -> str:
        """从文本中推断场景地点"""
        location_keywords = {
            "房间": "室内-房间", "客厅": "室内-客厅", "厨房": "室内-厨房",
            "院": "室外-庭院", "街": "室外-街道", "山": "室外-山野",
            "林": "室外-森林", "殿": "室内-殿堂", "城": "室外-城镇",
            "楼": "室内-楼阁", "河": "室外-河边", "海": "室外-海边",
            "路": "室外-道路", "店": "室内-店铺", "堂": "室内-厅堂",
            "府": "室内-府邸", "庙": "室内-庙宇", "洞": "室外-洞穴",
            "谷": "室外-山谷", "湖": "室外-湖畔", "亭": "室外-亭台",
            "桥": "室外-桥头", "门": "室外-门前", "阁": "室内-阁楼",
            "市": "室外-集市", "村": "室外-村落", "墓": "室外-墓地",
            "塔": "室内-塔楼", "船": "室外-船上", "车": "室外-车中",
        }
        for keyword, location in location_keywords.items():
            if keyword in text:
                return location
        return ""

    def _infer_time_from_text(self, text: str) -> str:
        """从文本中推断时间"""
        time_keywords = {
            "清晨": "清晨", "早晨": "早晨", "早上": "早晨", "上午": "上午",
            "中午": "中午", "下午": "下午", "傍晚": "傍晚", "黄昏": "黄昏",
            "晚上": "夜晚", "深夜": "深夜", "夜": "夜晚", "午时": "中午",
            "黎明": "黎明", "夕阳": "傍晚", "月色": "夜晚", "月光": "夜晚",
            "日出": "清晨", "日落": "傍晚", "子时": "深夜", "辰时": "早晨",
            "午后": "下午", "暮色": "傍晚", "三更": "深夜", "五更": "黎明",
        }
        for keyword, time_desc in time_keywords.items():
            if keyword in text:
                return time_desc
        return ""

    # ═══════════════════════════════════════════════════════════
    # 去重与摘要
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
