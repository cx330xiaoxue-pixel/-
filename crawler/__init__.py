"""
小说爬虫模块 — Novel-to-Script Pro

功能:
  - 搜索: 从多个公开小说源聚合搜索小说
  - 下载: 爬取指定小说的全部章节并保存为 TXT

支持的源站: 笔趣阁系列 (biquge, xbiquge)
"""

from .searcher import NovelSearcher, search_novels
from .downloader import NovelDownloader, download_novel

__all__ = ["NovelSearcher", "search_novels", "NovelDownloader", "download_novel"]
