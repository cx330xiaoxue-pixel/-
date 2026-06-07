"""
小说搜索器 — 多源聚合搜索
"""

import re
import time
import random
from typing import Optional
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup


# 小说类型关键词映射
GENRE_KEYWORDS = {
    "玄幻": ["玄幻", "异界", "魔法", "斗气"],
    "武侠": ["武侠", "江湖", "剑客", "武林"],
    "都市": ["都市", "现代", "总裁", "职场"],
    "言情": ["言情", "爱情", "婚恋", "甜宠"],
    "仙侠": ["仙侠", "修真", "修仙", "飞升"],
    "科幻": ["科幻", "星际", "机甲", "末世"],
    "历史": ["历史", "穿越", "古代", "王朝"],
    "悬疑": ["悬疑", "推理", "侦探", "灵异"],
    "游戏": ["游戏", "电竞", "网游", "虚拟"],
    "军事": ["军事", "战争", "特种兵", "谍战"],
}


class NovelSearcher:
    """聚合搜索多个公开小说源"""

    # 源站配置
    SOURCES = [
        {
            "name": "biquge_info",
            "base_url": "https://www.biquge.info",
            "search_url": "https://www.biquge.info/search.html",
            "search_param": "searchkey",
            "chapter_list_selector": "#list dd a",
            "encoding": "utf-8",
            "timeout": 15,
        },
        {
            "name": "xbiquge",
            "base_url": "https://www.xbiquge.la",
            "search_url": "https://www.xbiquge.la/modules/article/search.php",
            "search_param": "searchkey",
            "chapter_list_selector": "#list dd a",
            "encoding": "utf-8",
            "timeout": 15,
        },
        {
            "name": "du1du",
            "base_url": "https://www.du1du.org",
            "search_url": "https://www.du1du.org/search.html",
            "search_param": "searchkey",
            "chapter_list_selector": "#list dd a",
            "encoding": "utf-8",
            "timeout": 15,
        },
    ]

    def __init__(self, user_agent: str = None):
        self.client = httpx.Client(
            headers={
                "User-Agent": user_agent or (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )

    def search(
        self,
        keyword: str = "",
        genre: str = "",
        limit: int = 20,
    ) -> list[dict]:
        """
        搜索小说。

        Args:
            keyword: 搜索关键词（书名或作者）
            genre: 类型（玄幻/武侠/都市 等），为空时不过滤
            limit: 最多返回条数

        Returns:
            [{title, author, summary, genre, chapter_count, source_url, source_name}]
        """
        # 如果指定了类型，用类型关键词增强搜索
        search_terms = [keyword.strip()] if keyword.strip() else []
        if genre and genre in GENRE_KEYWORDS:
            search_terms.extend(GENRE_KEYWORDS[genre][:2])

        query = " ".join(search_terms) if search_terms else genre or "热门"

        # Step 1: 先在本地目录搜索（稳定可靠）
        from .catalog import search_catalog
        catalog_results = search_catalog(keyword=keyword, genre=genre, limit=limit)
        catalog_urls = {r["source_url"] for r in catalog_results}

        # Step 2: 在线搜索补充（只对未覆盖的结果）
        remaining = limit - len(catalog_results)
        if remaining > 0:
            live_results = []
            for source in self.SOURCES:
                try:
                    results = self._search_source(source, query, remaining)
                    # 去重
                    for r in results:
                        if r["source_url"] not in catalog_urls:
                            live_results.append(r)
                            catalog_urls.add(r["source_url"])
                            if len(live_results) >= remaining:
                                break
                    if len(live_results) >= remaining:
                        break
                    time.sleep(random.uniform(0.5, 1.5))
                except Exception as e:
                    print(f"  [WARN] Source {source['name']} search failed: {e}")
                    continue
            catalog_results.extend(live_results[:remaining])

        return catalog_results[:limit]

    def _search_source(self, source: dict, query: str, limit: int) -> list[dict]:
        """在单个源站搜索"""
        url = f"{source['search_url']}?{source['search_param']}={quote(query)}"

        resp = self.client.get(url)
        resp.encoding = source.get("encoding", "utf-8")
        soup = BeautifulSoup(resp.text, "lxml")

        results = []

        # 尝试多种常见的搜索结果选择器
        for selector in [
            ".result-list .result-item",
            ".novelslist2 li",
            "#main .list li",
            ".grid .book",
            ".item",
            "#sitembox dl",
        ]:
            items = soup.select(selector)
            if len(items) >= 1:
                break

        # 如果选择器都没命中，尝试提取所有带链接的块
        if not items:
            items = soup.select("li a[href*='book'], a[href*='novel'], a[href*='info']")[:limit]
            if not items:
                items = soup.select("dd a, dt a")[:limit]

        for item in items[:limit]:
            try:
                link = item if item.name == "a" else item.find("a")
                if not link:
                    continue
                href = link.get("href", "")
                title = link.get("title", "") or link.get_text(strip=True)

                if not title or len(title) < 2:
                    continue

                # 确保 URL 完整
                if href and not href.startswith("http"):
                    href = source["base_url"].rstrip("/") + "/" + href.lstrip("/")

                # 尝试提取更多信息
                author_el = item.find("span", class_=re.compile("author")) or item.find("em")
                author = author_el.get_text(strip=True) if author_el else ""
                if not author:
                    # 尝试从附近文本提取
                    text = item.get_text()
                    author_match = re.search(r"作者[：:]\s*(\S+)", text)
                    author = author_match.group(1) if author_match else "未知"

                summary_el = item.find("p", class_=re.compile("desc|intro|summary"))
                summary = summary_el.get_text(strip=True)[:200] if summary_el else ""

                results.append({
                    "title": title,
                    "author": author or "未知",
                    "summary": summary,
                    "source_url": href,
                    "source_name": source["name"],
                    "genre": _guess_genre(title),
                })
            except Exception:
                continue

        return results


def _guess_genre(title: str) -> str:
    """根据标题猜测小说类型"""
    for genre, keywords in GENRE_KEYWORDS.items():
        for kw in keywords[:2]:
            if kw in title:
                return genre
    return "未知"


def search_novels(keyword: str = "", genre: str = "", limit: int = 20) -> list[dict]:
    """便捷函数：搜索小说"""
    searcher = NovelSearcher()
    return searcher.search(keyword=keyword, genre=genre, limit=limit)
