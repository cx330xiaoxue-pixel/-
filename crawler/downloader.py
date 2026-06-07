"""
小说下载器 — 全文爬取并保存为 TXT
"""

import os
import re
import time
import random
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


class NovelDownloader:
    """下载指定小说的全部章节"""

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

    def download(
        self,
        source_url: str,
        output_dir: str,
        max_chapters: int = 200,
        title: str = "",
    ) -> dict:
        """
        下载小说全文。

        Args:
            source_url: 小说目录页 URL
            output_dir: 输出目录
            max_chapters: 最多下载章节数
            title: 小说标题（如果为空则从页面提取）

        Returns:
            {status, file_path, chapter_count, total_chars, title, message}
        """
        os.makedirs(output_dir, exist_ok=True)

        # Step 1: 获取目录页，提取所有章节链接
        print(f"  Getting catalog: {source_url}")
        resp = self.client.get(source_url)
        html = resp.content.decode("utf-8", errors="replace")

        soup = BeautifulSoup(html, "lxml")

        # 提取标题
        if not title:
            title_el = soup.find("h1") or soup.find("h2")
            title = title_el.get_text(strip=True) if title_el else "未命名小说"
        # 清理标题（去掉"正文"等后缀）
        title = re.sub(r"\s*正文\s*$", "", title)

        # 提取章节链接
        chapters = self._extract_chapter_links(soup, source_url)
        if not chapters:
            return {
                "status": "failed",
                "error": f"未能从目录页提取章节链接",
                "title": title,
            }

        if len(chapters) > max_chapters:
            print(f"  [WARN] Too many chapters ({len(chapters)}), limiting to {max_chapters}")
            chapters = chapters[:max_chapters]

        print(f"  Downloading {len(chapters)} chapters...")

        # Step 2: 逐章下载
        all_text = []
        success_count = 0

        for i, ch in enumerate(chapters):
            try:
                ch_text = self._download_chapter(ch["url"], ch["title"])
                if ch_text:
                    all_text.append(ch_text)
                    success_count += 1

                # 进度输出
                if (i + 1) % 20 == 0 or i == len(chapters) - 1:
                    print(f"    Downloaded {i + 1}/{len(chapters)} chapters")

                # 随机延迟，避免被反爬
                time.sleep(random.uniform(0.1, 0.3))
            except Exception as e:
                print(f"    [WARN] Chapter {i+1} download failed: {e}")
                continue

        if not all_text:
            return {
                "status": "failed",
                "error": "所有章节下载均失败",
                "title": title,
            }

        # Step 3: 保存为 TXT
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        safe_title = safe_title.replace(" ", "_")[:50]
        file_path = os.path.join(output_dir, f"{safe_title}.txt")

        full_text = f"《{title}》\n{'=' * 60}\n\n" + "\n\n".join(all_text)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(full_text)

        total_chars = len(full_text)
        print(f"  [OK] Download complete: {file_path} ({success_count}/{len(chapters)} chapters, {total_chars:,} chars)")

        return {
            "status": "completed",
            "title": title,
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "chapter_count": success_count,
            "total_chapters": len(chapters),
            "total_chars": total_chars,
            "message": f"下载完成: {title} ({success_count}章, {total_chars:,}字)",
        }

    def _extract_chapter_links(self, soup: BeautifulSoup, base_url: str) -> list[dict]:
        """从目录页提取章节列表"""
        chapters = []

        # 检测站点类型
        is_biquwu = "biquwu.cc" in base_url

        if is_biquwu:
            # biquwu.cc: 章节链接格式 /biquge/X_Y/c{数字}.html
            links = soup.select("a[href*='/c']")
            if len(links) < 3:
                links = soup.find_all("a", href=re.compile(r"/c\d+\.html"))
        else:
            # 尝试多种常见的章节列表选择器
            for selector in [
                ".listmain dd a",    # bqg70.com
                "#list dd a",         # 通用笔趣阁
                ".chapterlist dd a",
                "#chapterlist dd a",
                ".mulu li a",
                ".catalog a",
                "dl dd a",
            ]:
                links = soup.select(selector)
                if len(links) >= 3:
                    break

        # 如果都没找到，尝试找所有指向章节的链接
        if len(links) < 3:
            links = soup.select("a[href*='html']")

        seen_urls = set()
        for a in links:
            href = a.get("href", "")
            ch_title = a.get_text(strip=True)

            if not href or not ch_title:
                continue
            if len(ch_title) < 1:
                continue

            # 确保完整 URL
            if not href.startswith("http"):
                if href.startswith("/"):
                    # 绝对路径 — 从域名根拼接
                    from urllib.parse import urlparse
                    parsed = urlparse(base_url)
                    href = f"{parsed.scheme}://{parsed.netloc}{href}"
                else:
                    href = base_url.rstrip("/") + "/" + href

            # 去重
            if href in seen_urls:
                continue
            seen_urls.add(href)

            chapters.append({"title": ch_title, "url": href})

        return chapters

    def _download_chapter(self, url: str, title: str) -> Optional[str]:
        """下载单个章节内容"""
        resp = self.client.get(url)
        # 手动解码避免 httpx encoding 锁定问题
        html = resp.content.decode("utf-8", errors="replace")

        soup = BeautifulSoup(html, "lxml")

        # 检测站点类型
        is_biquwu = "biquwu.cc" in url

        # 尝试提取正文内容
        content_el = None

        if is_biquwu:
            # biquwu.cc: 内容在 div.box.single 中
            content_el = soup.select_one("div.box.single") or soup.select_one("div.container")

        if not content_el:
            for selector in [
                "#content",
                ".content",
                "#contents",
                ".showtxt",
                "#chaptercontent",
                ".reader-main .content",
                "article",
            ]:
                content_el = soup.select_one(selector)
                if content_el:
                    break

        if not content_el:
            body = soup.find("body")
            if body:
                content_el = body

        if not content_el:
            return None

        # 清理内容
        text = content_el.get_text(separator="\n")

        # 去除常见广告/脚本内容
        for pattern in [
            r"请记住本书首发域名.*",
            r"一秒记住.*",
            r"天才一秒记住.*",
            r"手机用户请浏览.*",
            r"笔趣阁.*",
            r"www\..*",
            r"function\s*\(.*\)",
            r"var\s+\w+\s*=.*",
            r"document\..*",
        ]:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # 清理多余空行
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        text = "\n".join(lines)

        if len(text) < 50:
            return None

        return f"\n\n{title}\n{'-' * 30}\n\n{text}"

    def _detect_encoding(self, resp: httpx.Response) -> str:
        """尝试检测页面编码（使用 resp.content 避免锁定 encoding）"""
        # 先尝试从 Content-Type 获取
        content_type = resp.headers.get("content-type", "")
        match = re.search(r"charset=([\w-]+)", content_type)
        if match:
            return match.group(1)

        # 从 HTML meta 标签获取（用 content 而非 text）
        html_head = resp.content[:2000].decode("utf-8", errors="ignore")
        match = re.search(
            r'<meta[^>]+charset=["\']?([\w-]+)',
            html_head,
            re.IGNORECASE,
        )
        if match:
            return match.group(1)

        return "utf-8"


def download_novel(source_url: str, output_dir: str, title: str = "", max_chapters: int = 200) -> dict:
    """便捷函数：下载小说全文"""
    downloader = NovelDownloader()
    return downloader.download(source_url, output_dir, title=title, max_chapters=max_chapters)
