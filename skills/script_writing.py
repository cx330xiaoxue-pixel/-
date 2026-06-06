"""
剧本写作 Skill — 剧本生成模板、爆款参考检索、风格分析、Show Don't Tell 转换

可被 script-writer 和 visual-storyteller Agent 复用。
"""

import os
import re
from collections import Counter, defaultdict
from typing import Optional


class ScriptWritingSkill:
    """剧本写作核心技能"""

    # ═══════════════════════════════════════════════════════════
    # 剧本生成模板
    # ═══════════════════════════════════════════════════════════

    SCENE_OPENING_TEMPLATES = {
        "action": [
            "画面骤亮。{location}，{time}。{action_description}",
            "镜头从{visual_detail}缓缓拉开，露出{location}的全貌。",
            "急促的{action_sound}打破了{atmosphere}的宁静。",
        ],
        "dialogue": [
            "{character}的声音先于画面响起：「{line}」",
            "画面未至，{character}的话已传入耳中。",
        ],
        "atmosphere": [
            "{weather}。{location}笼罩在一片{atmosphere}之中。",
            "空镜。{location}。{visual_detail}暗示着即将到来的{event_hint}。",
        ],
    }

    TRANSITION_TEMPLATES = [
        "切至：",
        "叠化至：",
        "跳切：",
        "平行剪辑 ——",
        "渐黑。\n淡入：",
    ]

    # ═══════════════════════════════════════════════════════════
    # 爆款参考检索
    # ═══════════════════════════════════════════════════════════

    def __init__(self, hit_scripts_dir: str = "./knowledge/hit_scripts"):
        self.hit_scripts_dir = hit_scripts_dir
        self._reference_index = None  # 延迟构建

    def retrieve_references(
        self,
        query: str,
        genre: str = "",
        element_type: str = "",
        top_k: int = 5,
    ) -> list[dict]:
        """
        检索爆款剧本参考片段。

        支持：
        - 关键词匹配
        - TF-IDF 语义相似度（需 scikit-learn）
        - 类型过滤

        Args:
            query: 检索查询（场景描述、情绪、节拍类型等）
            genre: 类型过滤
            element_type: 元素类型过滤 (dialogue/action/opening/cliffhanger)
            top_k: 返回数量

        Returns:
            [{title, scene_type, content, similarity, source}]
        """
        # 构建索引
        if self._reference_index is None:
            self._reference_index = self._build_reference_index()

        results = []

        # 关键词匹配
        query_terms = set(self._tokenize(query))
        for ref in self._reference_index:
            score = 0
            ref_terms = set(ref.get("keywords", []))

            # 关键词重合度
            overlap = query_terms & ref_terms
            score += len(overlap) * 2

            # 类型匹配加分
            if genre and genre == ref.get("genre", ""):
                score += 3
            if element_type and element_type == ref.get("element_type", ""):
                score += 3

            if score > 0:
                results.append({
                    "title": ref.get("title", "未知"),
                    "scene_type": ref.get("scene_type", ""),
                    "content": ref.get("content", ""),
                    "similarity": min(score / 10, 1.0),
                    "source": ref.get("source", ""),
                    "genre": ref.get("genre", ""),
                    "notes": ref.get("notes", ""),
                })

        # 按相似度排序
        results.sort(key=lambda x: -x["similarity"])
        return results[:top_k]

    def _build_reference_index(self) -> list[dict]:
        """构建爆款剧本参考索引"""
        index = []

        # 内置参考库（用户可扩展）
        builtin_references = [
            {
                "title": "《琅琊榜》",
                "genre": "古装",
                "scene_type": "opening",
                "element_type": "action",
                "content": "梅长苏立于江边，披风猎猎作响。远处，金陵城的轮廓在暮色中若隐若现。他缓缓摘下面具，露出那张苍白却坚毅的脸。",
                "keywords": ["开场", "远景", "人物出场", "氛围营造", "古装", "权谋"],
                "notes": "经典人物出场：景→人→细节，层层推进",
            },
            {
                "title": "《隐秘的角落》",
                "genre": "悬疑",
                "scene_type": "opening",
                "element_type": "action",
                "content": "张东升将岳父母推下山崖的瞬间，镜头切至他面无表情的脸。没有配乐，只有风声。",
                "keywords": ["冷开场", "震惊", "无声", "面部特写", "悬疑"],
                "notes": "冷开场典范：用最冷静的手法拍最震撼的内容",
            },
            {
                "title": "《甄嬛传》",
                "genre": "古装",
                "scene_type": "confrontation",
                "element_type": "dialogue",
                "content": "甄嬛：「臣妾做不到啊！」—— 华妃冷眼相视，殿内针落可闻。",
                "keywords": ["对峙", "情感爆发", "台词", "宫斗", "戏剧张力"],
                "notes": "情绪爆发点：一句台词+一个眼神，胜过千言万语",
            },
            {
                "title": "《庆余年》",
                "genre": "古装",
                "scene_type": "revelation",
                "element_type": "dialogue",
                "content": "范闲在朝堂之上，当众背诵杜甫《登高》。满朝文武，鸦雀无声。",
                "keywords": ["揭示", "高光时刻", "文戏", "智斗", "爽点"],
                "notes": "智力高光：用文化碾压制造爽感",
            },
            {
                "title": "《狂飙》",
                "genre": "犯罪",
                "scene_type": "confrontation",
                "element_type": "dialogue",
                "content": "高启强：「我想吃鱼了。」—— 一句话，一个眼神，杀机四伏。",
                "keywords": ["潜台词", "威胁", "冷峻", "黑帮", "经典台词"],
                "notes": "潜台词教科书：表面说吃鱼，实际下杀令",
            },
            {
                "title": "《漫长的季节》",
                "genre": "悬疑",
                "scene_type": "emotional",
                "element_type": "action",
                "content": "王响独自坐在空荡荡的客厅里。电视机开着，雪花屏。他手里握着一只旧手套，指节泛白。",
                "keywords": ["情感", "细节", "道具", "留白", "悲伤"],
                "notes": "情感留白：不说一句话，用道具和动作传递全部情绪",
            },
            {
                "title": "《三体》",
                "genre": "科幻",
                "scene_type": "revelation",
                "element_type": "narration",
                "content": "\"不要回答！不要回答！不要回答！\" —— 叶文洁的手指悬在发射键上方，窗外是燃烧的兴安岭。",
                "keywords": ["科幻", "揭示", "历史交叠", "抉择", "宏大"],
                "notes": "宏大揭示：个人抉择与文明命运的对照",
            },
            {
                "title": "《武林外传》",
                "genre": "喜剧",
                "scene_type": "dialogue",
                "element_type": "dialogue",
                "content": "佟湘玉：「额滴神啊！」白展堂：「这事儿不赖我！」—— 同福客栈日常。",
                "keywords": ["喜剧", "口头禅", "群像", "日常", "节奏"],
                "notes": "喜剧节奏：口头禅+反差+群像互动",
            },
            {
                "title": "《觉醒年代》",
                "genre": "历史",
                "scene_type": "emotional",
                "element_type": "dialogue",
                "content": "陈独秀在狱中写下：「我们这些人的坚持，不是为了自己能看到天亮，而是为了让后人活在光明里。」",
                "keywords": ["历史", "信仰", "牺牲", "台词", "燃向"],
                "notes": "信仰高光：个人苦难与历史使命的交织",
            },
            {
                "title": "《山河令》",
                "genre": "武侠",
                "scene_type": "action",
                "element_type": "action",
                "content": "温客行折扇轻摇，笑里藏刀。周子舒长剑出鞘，寒光照亮半张脸。两人之间，竹叶纷飞。",
                "keywords": ["武侠", "打斗", "意境", "双雄", "美感"],
                "notes": "武侠美学：打斗不是目的，意境和人物关系才是",
            },
        ]

        # 也尝试从文件加载用户自定义参考
        index.extend(builtin_references)

        if os.path.isdir(self.hit_scripts_dir):
            for fn in os.listdir(self.hit_scripts_dir):
                if fn.endswith((".md", ".txt", ".json")):
                    # 简化处理：文件名作为关键词
                    keywords = self._tokenize(os.path.splitext(fn)[0])
                    fpath = os.path.join(self.hit_scripts_dir, fn)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            content = f.read()[:1000]
                        index.append({
                            "title": fn,
                            "genre": "",
                            "scene_type": "",
                            "element_type": "",
                            "content": content,
                            "keywords": keywords,
                            "source": fpath,
                            "notes": "",
                        })
                    except Exception:
                        pass

        return index

    def _tokenize(self, text: str) -> list[str]:
        """简易中文分词"""
        # 去除标点后按 2-4 字切分
        cleaned = re.sub(r'[^一-鿿\w]', ' ', text)
        tokens = []
        # 英文词
        tokens.extend(re.findall(r'[a-zA-Z]+', cleaned))
        # 中文 2-gram
        chinese = re.findall(r'[一-鿿]+', cleaned)
        for segment in chinese:
            for i in range(len(segment) - 1):
                tokens.append(segment[i:i+2])
        return tokens

    # ═══════════════════════════════════════════════════════════
    # 风格分析
    # ═══════════════════════════════════════════════════════════

    def analyze_style(self, elements: list, script_text: str = "") -> dict:
        """
        分析剧本的语言风格。

        Returns:
            {avg_sentence_length, dialogue_ratio, visual_marker_density,
             web_novel_keywords, style_category, suggestions}
        """
        if not elements:
            return {"style_category": "unknown"}

        # 句长分析
        text_lengths = [len(e.get("text", "")) for e in elements]
        avg_len = sum(text_lengths) / max(len(text_lengths), 1)

        # 对白密度
        dialogue_count = sum(1 for e in elements if e.get("type") == "dialogue")
        dialogue_ratio = dialogue_count / max(len(elements), 1)

        # 视觉标记密度（镜头相关词汇）
        visual_keywords = [
            "镜头", "特写", "远景", "中景", "近景", "全景",
            "切至", "叠化", "淡入", "淡出", "推", "拉", "摇", "移", "跟",
            "画面", "屏幕", "背景", "前景", "俯拍", "仰拍", "POV",
        ]
        visual_count = 0
        for e in elements:
            text = e.get("text", "")
            for kw in visual_keywords:
                if kw in text:
                    visual_count += 1
                    break
        visual_density = visual_count / max(len(elements), 1)

        # 网文感关键词
        web_novel_kw = [
            "只见", "话说", "且说", "却说", "原来如此", "不由得",
            "心中暗道", "暗自想到", "内心深处", "浑身上下", "全身上下",
            "眼中闪过", "嘴角扬起", "微微", "顿时", "不由得", "赫然",
        ]
        web_novel_count = 0
        web_novel_hits = []
        for e in elements:
            text = e.get("text", "")
            for kw in web_novel_kw:
                if kw in text:
                    web_novel_count += 1
                    web_novel_hits.append({"keyword": kw, "text": text[:80]})
                    break

        # 风格分类
        if dialogue_ratio > 0.45:
            style_category = "对白驱动型 — 适合情景剧/喜剧/都市"
        elif visual_density > 0.15:
            style_category = "视觉叙事型 — 已有较强分镜意识"
        elif avg_len > 120:
            style_category = "文学描写型 — 需要大量精炼和视觉化转换"
        elif web_novel_count / max(len(elements), 1) > 0.1:
            style_category = "网文风格 — 需去除套话，增强影视感"
        else:
            style_category = "均衡型"

        return {
            "avg_sentence_length": round(avg_len, 1),
            "dialogue_ratio": round(dialogue_ratio * 100, 1),
            "visual_marker_density": round(visual_density * 100, 1),
            "web_novel_keyword_count": web_novel_count,
            "web_novel_hits": web_novel_hits[:10],
            "style_category": style_category,
            "suggestions": self._generate_style_suggestions(
                avg_len, dialogue_ratio, visual_density, web_novel_count, len(elements)
            ),
        }

    def _generate_style_suggestions(
        self,
        avg_len: float,
        dialogue_ratio: float,
        visual_density: float,
        web_novel_count: int,
        total: int,
    ) -> list[str]:
        """生成风格改进建议"""
        suggestions = []
        if avg_len > 100:
            suggestions.append("句子偏长（均{:.0f}字），剧本应以短句为主，建议拆分长句".format(avg_len))
        if dialogue_ratio < 0.15:
            suggestions.append("对白密度偏低，影视剧需要更多可说的台词")
        if visual_density < 0.05:
            suggestions.append("缺少视觉标记，建议增加镜头方向和画面描述")
        if web_novel_count > total * 0.1:
            suggestions.append("网文套话较多，建议用具体的动作/表情替代")
        return suggestions

    # ═══════════════════════════════════════════════════════════
    # Show Don't Tell 转换规则
    # ═══════════════════════════════════════════════════════════

    SHOW_DONT_TELL_RULES = {
        # 情绪 → 外部表现
        "他很生气": "他握紧拳头，指节因用力而发白",
        "她很伤心": "她低头看着地板，眼泪一滴一滴落在手背上",
        "他非常害怕": "他靠在墙上，双腿微微发抖，呼吸急促",
        "她很高兴": "她笑得眼睛弯成月牙，忍不住原地蹦了两下",
        "他紧张极了": "他反复摩挲着衣角，额头上渗出细密的汗珠",
        "她犹豫不决": "她伸出的手在空中停住，又慢慢收回",
        "他内心挣扎": "他盯着两个方向，眼神来回游移，嘴唇抿成一线",
        # 心理活动 → 动作
        "他心里想": "他的目光落在远处，眉头微蹙",
        "他暗自决定": "他深吸一口气，眼神变得坚定",
        "他忽然意识到": "他猛地停住脚步，瞳孔微微放大",
        # 抽象概念 → 具体画面
        "气氛很紧张": "房间里没人说话。墙上的钟，滴答声格外刺耳",
        "场面很混乱": "人影绰绰，喊声此起彼伏。一只茶碗被撞翻，在地上转了两圈",
        # 网文套话 → 影视语言
        "眼中闪过一抹精光": "他的眼睛在那一刻亮了起来",
        "浑身上下散发着一股杀气": "他站在那里，周围的人不自觉地退了一步",
        "嘴角扬起一抹冷笑": "他扯了扯嘴角，眼底没有半分笑意",
    }

    def convert_show_dont_tell(self, text: str) -> dict:
        """
        将"告诉"风格转换为"展示"风格。

        Returns:
            {original, converted, changed, suggestions}
        """
        converted = text
        changes = []

        # 规则替换
        for tell, show in self.SHOW_DONT_TELL_RULES.items():
            if tell in converted:
                converted = converted.replace(tell, show)
                changes.append({"tell": tell, "show": show})

        # 检测更多"告诉"模式
        suggestions = []
        tell_patterns = [
            (r'(\S+)感到很?(\S{1,3})', '直接陈述情感"{}感到{}"，建议用动作/表情替代'),
            (r'(\S+)的心中(?:暗想|想到|暗道)', '"{}"的心理活动，建议转化为外在表现'),
            (r'(?:只见|但见|却见)\s*(\S+)', '网文视觉引导"只见{}"，可删去直接描述画面'),
            (r'浑身上下|全身上下|周身上下', '冗余的身体描写"{}"，删去更简洁'),
            (r'眼中闪过一抹|眼中闪过一丝|眼底闪过一抹', '套话"{}"，用简洁的视觉描写替代'),
        ]
        for pattern, msg_template in tell_patterns:
            for m in re.finditer(pattern, converted):
                match_text = m.group(0)
                suggestions.append(msg_template.format(match_text))

        return {
            "original": text,
            "converted": converted,
            "changes": changes,
            "suggestions": suggestions[:5],
            "has_changes": len(changes) > 0 or len(suggestions) > 0,
        }

    # ═══════════════════════════════════════════════════════════
    # 对白优化
    # ═══════════════════════════════════════════════════════════

    def optimize_dialogue(self, dialogue: str, character_name: str = "") -> dict:
        """
        优化对白质量。

        检查：
        - 信息密度（是否太啰嗦）
        - 角色辨识度（是否换个角色说也一样）
        - 潜台词空间（是否太直白）
        """
        issues = []
        optimized = dialogue

        # 太长的对白
        if len(dialogue) > 80:
            issues.append("对白过长（{}字），建议拆分为交互式对话".format(len(dialogue)))

        # 信息倾泻（多个句号 = 在说教）
        sentence_count = dialogue.count("。") + dialogue.count("！") + dialogue.count("？")
        if sentence_count > 3:
            issues.append("信息密度过高（{}句），观众难以消化".format(sentence_count))

        # 缺乏潜台词（太直白）
        direct_patterns = [
            "我爱你", "我恨你", "我害怕", "我很高兴",
            "因为你是我的", "你要相信我", "你必须",
        ]
        for pattern in direct_patterns:
            if pattern in dialogue:
                issues.append(f"直白表达'{pattern}'，建议用间接方式传递")
                break

        # 角色辨识度检查（通用对白）
        generic_lines = [
            "你好", "再见", "好的", "知道了", "嗯",
            "是吗", "真的吗", "为什么", "怎么办",
        ]
        if dialogue.strip() in generic_lines:
            issues.append("对白过于通用，缺乏角色辨识度")

        return {
            "original": dialogue,
            "issues": issues,
            "suggestion": (
                "对白应当：1) 推进情节 2) 揭示角色 3) 包含潜台词。"
                "如果一句话三个功能都不满足，考虑删掉或重写。"
            ) if issues else "对白质量良好",
        }

    # ═══════════════════════════════════════════════════════════
    # 场景格式转换
    # ═══════════════════════════════════════════════════════════

    def elements_to_screenplay_format(
        self,
        elements: list,
        scene_location: str = "",
        scene_time: str = "",
    ) -> str:
        """
        将结构化元素转换为标准剧本格式文本。

        Returns:
            标准剧本格式的字符串
        """
        lines = []

        # 场景头
        if scene_location or scene_time:
            loc = scene_location or "未知地点"
            tim = scene_time or "未知时间"
            lines.append(f"[{loc} — {tim}]")
            lines.append("")

        for elem in elements:
            etype = elem.get("type", "")
            role = elem.get("role", "")
            text = elem.get("text", "")
            parenthetical = elem.get("parenthetical", "")
            visual_hint = elem.get("visual_hint", "")

            if etype == "dialogue" and role != "旁白":
                # 角色名居中
                lines.append(f"                        {role}")
                if parenthetical:
                    lines.append(f"                    ({parenthetical})")
                lines.append(f"    {text}")
                lines.append("")

            elif etype == "action":
                lines.append(f"{text}")
                lines.append("")

            elif etype in ("narration", "description"):
                if visual_hint:
                    lines.append(f"[{visual_hint}]")
                lines.append(f"{text}")
                lines.append("")

        return "\n".join(lines)

    def elements_to_scene_script(
        self,
        elements: list,
        scene_id: str = "1.1",
        location: str = "",
        time: str = "",
        atmosphere: str = "",
        characters_present: list = None,
    ) -> dict:
        """
        将元素列表组装为 Schema v2.0 场景格式，供 ScriptBuilder 使用。

        Returns:
            {scene_id, scene_number, location, time, atmosphere,
             characters_present, element_count, elements}
        """
        scene_elements = []
        for elem in elements:
            scene_elem = {
                "element_id": f"{scene_id}.{elem.get('id', elem.get('global_id', 1))}",
                "type": elem.get("type", "narration"),
                "role": elem.get("role", "旁白"),
                "text": elem.get("text", ""),
            }
            for key in ["emotion", "action", "subtext", "beat_type",
                         "visual_hint", "parenthetical"]:
                if elem.get(key):
                    scene_elem[key] = elem[key]
            scene_elements.append(scene_elem)

        return {
            "scene_id": scene_id,
            "scene_number": int(scene_id.split(".")[-1]) if "." in scene_id else 1,
            "location": location or "未指定",
            "time": time or "未指定",
            "atmosphere": atmosphere or "中性",
            "characters_present": characters_present or [],
            "element_count": len(scene_elements),
            "elements": scene_elements,
        }
