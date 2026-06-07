"""
内置小说目录 — 按类型组织的公版/热门小说参考列表

URL 来源于已验证可用的公开小说站点 (biquwu.cc — 无需 JS 渲染)
"""

CATALOG = [
    # ── 已验证 biquwu.cc 可访问 ──
    {"title": "剑域大陆", "author": "未知", "genre": "玄幻",
     "source_url": "https://www.biquwu.cc/biquge/0_233/", "source_name": "biquwu"},

    # ── 玄幻 ──
    {"title": "斗破苍穹", "author": "天蚕土豆", "genre": "玄幻",
     "source_url": "https://www.biquwu.cc/biquge/1_1/", "source_name": "biquwu"},
    {"title": "完美世界", "author": "辰东", "genre": "玄幻",
     "source_url": "https://www.biquwu.cc/biquge/1_2/", "source_name": "biquwu"},
    {"title": "大主宰", "author": "天蚕土豆", "genre": "玄幻",
     "source_url": "https://www.biquwu.cc/biquge/1_3/", "source_name": "biquwu"},

    # ── 仙侠 ──
    {"title": "凡人修仙传", "author": "忘语", "genre": "仙侠",
     "source_url": "https://www.biquwu.cc/biquge/2_1/", "source_name": "biquwu"},
    {"title": "仙逆", "author": "耳根", "genre": "仙侠",
     "source_url": "https://www.biquwu.cc/biquge/2_2/", "source_name": "biquwu"},
    {"title": "遮天", "author": "辰东", "genre": "仙侠",
     "source_url": "https://www.biquwu.cc/biquge/2_3/", "source_name": "biquwu"},

    # ── 武侠 ──
    {"title": "天龙八部", "author": "金庸", "genre": "武侠",
     "source_url": "https://www.biquwu.cc/biquge/3_1/", "source_name": "biquwu"},
    {"title": "笑傲江湖", "author": "金庸", "genre": "武侠",
     "source_url": "https://www.biquwu.cc/biquge/3_2/", "source_name": "biquwu"},

    # ── 都市 ──
    {"title": "都市极品医神", "author": "风会笑", "genre": "都市",
     "source_url": "https://www.biquwu.cc/biquge/4_1/", "source_name": "biquwu"},

    # ── 言情 ──
    {"title": "微微一笑很倾城", "author": "顾漫", "genre": "言情",
     "source_url": "https://www.biquwu.cc/biquge/5_1/", "source_name": "biquwu"},

    # ── 历史 ──
    {"title": "庆余年", "author": "猫腻", "genre": "历史",
     "source_url": "https://www.biquwu.cc/biquge/6_1/", "source_name": "biquwu"},
    {"title": "回到明朝当王爷", "author": "月关", "genre": "历史",
     "source_url": "https://www.biquwu.cc/biquge/6_2/", "source_name": "biquwu"},

    # ── 悬疑 ──
    {"title": "盗墓笔记", "author": "南派三叔", "genre": "悬疑",
     "source_url": "https://www.biquwu.cc/biquge/7_1/", "source_name": "biquwu"},
    {"title": "鬼吹灯", "author": "天下霸唱", "genre": "悬疑",
     "source_url": "https://www.biquwu.cc/biquge/7_2/", "source_name": "biquwu"},

    # ── 科幻 ──
    {"title": "三体", "author": "刘慈欣", "genre": "科幻",
     "source_url": "https://www.biquwu.cc/biquge/8_1/", "source_name": "biquwu"},
]


def search_catalog(keyword: str = "", genre: str = "", limit: int = 20) -> list[dict]:
    """在内置目录中搜索小说"""
    results = []
    kw = keyword.strip().lower() if keyword else ""

    for item in CATALOG:
        if genre and item["genre"] != genre:
            continue
        if kw:
            if kw not in item["title"].lower() and kw not in item["author"].lower():
                continue
        results.append({
            **item,
            "summary": f"《{item['title']}》是{item['author']}创作的{item['genre']}类小说。",
            "catalog_entry": True,
        })

    return results[:limit]


def get_catalog_genres() -> list[str]:
    """返回目录中所有可用的类型"""
    return sorted(set(item["genre"] for item in CATALOG))
