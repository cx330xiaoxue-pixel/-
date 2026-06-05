"""
AI 辅助剧本创作工具 - 主入口
小说文本 → 结构化 YAML 剧本 的一站式转换工具

用法:
    python main.py --input ./sample_novel/ --output ./output/
    python main.py --input ./sample_novel/ --output ./output/ --config config.yaml
    python main.py --input ./sample_novel/ --title "我的剧本" --author "原作者"
"""

import argparse
import os
import sys
from pathlib import Path

# Windows 控制台 UTF-8 支持
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import yaml

from extractor import NovelExtractor
from script_builder import ScriptBuilder


def load_config(config_path: str) -> dict:
    """加载配置文件"""
    if not os.path.exists(config_path):
        print(f"⚠️  配置文件 {config_path} 不存在，使用默认配置")
        return {
            "llm": {
                "provider": "deepseek",
                "api_key": "sk-YOUR-API-KEY",
                "base_url": "https://api.deepseek.com/v1",
                "model": "deepseek-chat",
                "temperature": 0.7,
                "max_tokens": 4096,
            },
            "processing": {
                "window_size": 40,
                "overlap_rate": 0.5,
                "max_workers": 4,
                "retry_times": 3,
            },
            "output": {
                "format": "yaml",
                "output_dir": "./output",
                "include_emotion": True,
                "include_action": True,
                "language": "zh-CN",
            },
        }

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_chapter_files(input_dir: str) -> list[dict]:
    """读取输入目录下的所有章节文件"""
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"❌ 输入目录不存在: {input_dir}")
        sys.exit(1)

    chapters = []
    # 支持 .txt 文件，按文件名排序（假设文件名包含数字编号）
    txt_files = sorted(
        input_path.glob("*.txt"),
        key=lambda p: (
            int("".join(c for c in p.stem if c.isdigit()) or "0"),
            p.name,
        ),
    )

    if not txt_files:
        print(f"❌ 在 {input_dir} 中未找到 .txt 文件")
        sys.exit(1)

    for idx, filepath in enumerate(txt_files, start=1):
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        # 从文件名推断章节标题
        title = filepath.stem.replace("_", " ").replace("-", " ")

        chapters.append(
            {
                "chapter_id": idx,
                "title": title,
                "text": text,
                "filename": filepath.name,
            }
        )
        print(f"  📖 读取章节 {idx}: {filepath.name} ({len(text)} 字符)")

    return chapters


def validate_api_key(config: dict) -> bool:
    """验证 API Key 是否已配置"""
    api_key = config.get("llm", {}).get("api_key", "")
    if not api_key or api_key == "sk-YOUR-API-KEY":
        print("=" * 60)
        print("⚠️  未配置 API Key！")
        print()
        print("请通过以下方式之一配置 API Key:")
        print("  1. 编辑 config.yaml，将 api_key 替换为你的密钥")
        print("  2. 设置环境变量: export DEEPSEEK_API_KEY=sk-xxx")
        print("  3. 使用命令行参数: --api-key sk-xxx")
        print()
        print("支持 DeepSeek API (https://platform.deepseek.com)")
        print("也支持任何 OpenAI 兼容接口")
        print("=" * 60)
        return False
    return True


def print_script_summary(script: dict):
    """打印剧本摘要"""
    meta = script["script"]["metadata"]
    chars = script["script"]["characters"]
    chapters = script["script"]["chapters"]

    print()
    print("=" * 60)
    print(f"📜 剧本:《{meta['script_title']}》")
    print(f"   原著: {meta['original_work']}")
    print(f"   作者: {meta['original_author']}")
    print(f"   生成日期: {meta['created_date']}")
    print(f"   改编章节: {meta['total_chapters_adapted']} 章")
    print()
    print(f"👥 角色数量: {len(chars)}")
    for char in chars[:10]:  # 只显示前 10 个
        print(
            f"   [{char['role_type']}] {char['name']}"
            f" (出场 {char['total_appearances']} 次)"
        )
    if len(chars) > 10:
        print(f"   ... 还有 {len(chars) - 10} 个角色")

    print()
    print(f"📖 章节数: {len(chapters)}")
    for ch in chapters:
        print(
            f"   第 {ch['chapter_id']} 章: {ch['scene_count']} 个场景,"
            f" {ch['element_count']} 个元素"
        )

    stats = meta["statistics"]
    print()
    print(f"📊 统计: 总计 {stats['total_elements']} 个元素,"
          f" 对白 {stats['dialogue_count']} 个,"
          f" 旁白 {stats['narration_count']} 个")


def main():
    parser = argparse.ArgumentParser(
        description="AI 辅助剧本创作工具 - 将小说文本转换为结构化 YAML 剧本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py -i ./sample_novel/ -o ./output/
  python main.py -i ./sample_novel/ -t "剑来" -a "烽火戏诸侯"
  python main.py -i ./sample_novel/ --api-key sk-xxx --model deepseek-chat
        """,
    )

    parser.add_argument(
        "-i", "--input", required=True, help="输入目录（包含 .txt 章节文件）"
    )
    parser.add_argument(
        "-o", "--output", default="./output", help="输出目录（默认: ./output）"
    )
    parser.add_argument(
        "-c", "--config", default="config.yaml", help="配置文件路径"
    )
    parser.add_argument("-t", "--title", default="", help="剧本名称")
    parser.add_argument(
        "-a", "--author", default="", help="原著作者"
    )
    parser.add_argument("--api-key", default="", help="API Key（覆盖配置文件）")
    parser.add_argument("--base-url", default="", help="API Base URL")
    parser.add_argument("--model", default="", help="模型名称")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅读取和分析，不调用 API",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="使用规则匹配模拟抽取（无需 API Key，用于测试流程）",
    )
    parser.add_argument(
        "--min-chapters",
        type=int,
        default=3,
        help="最少需要的章节数（默认: 3）",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🎬 AI 辅助剧本创作工具 v1.0")
    print("   小说 → 结构化 YAML 剧本")
    print("=" * 60)
    print()

    # 加载配置
    config = load_config(args.config)

    # 命令行参数覆盖配置
    if args.api_key:
        config["llm"]["api_key"] = args.api_key
    if args.base_url:
        config["llm"]["base_url"] = args.base_url
    if args.model:
        config["llm"]["model"] = args.model

    # 读取章节文件
    print("📂 读取章节文件...")
    chapters = read_chapter_files(args.input)

    if len(chapters) < args.min_chapters:
        print(
            f"❌ 章节数量不足！需要至少 {args.min_chapters} 章，"
            f"当前只有 {len(chapters)} 章"
        )
        sys.exit(1)

    print(f"✅ 成功读取 {len(chapters)} 个章节\n")

    if args.dry_run:
        print("🔍 Dry-run 模式: 仅分析不转换")
        for ch in chapters:
            print(
                f"  第 {ch['chapter_id']} 章: {ch['title']}"
                f" ({len(ch['text'])} 字符)"
            )
        print()
        print("✅ 分析完成，使用以下命令进行实际转换:")
        print(f"   python main.py -i {args.input} -o {args.output}")
        return

    # 初始化抽取器
    if args.mock:
        print("🧪 使用 Mock 抽取器（规则匹配模式）...")
        from mock_extractor import MockExtractor
        extractor = MockExtractor()
        mock_mode = True
    else:
        # 验证 API Key
        if not validate_api_key(config):
            sys.exit(1)
        print("🤖 初始化 LLM 抽取器...")
        extractor = NovelExtractor(args.config)
        mock_mode = False
        print(f"   模型: {extractor.model}")
        print(f"   滑窗大小: {extractor.window_size} 行")
    print()

    # 逐章提取结构化信息
    all_elements = []
    chapter_context = ""  # 累积的章节上下文

    for ch in chapters:
        print(f"📝 处理第 {ch['chapter_id']} 章: {ch['title']}")
        elements = extractor.extract_from_chapter(
            chapter_text=ch["text"],
            chapter_id=ch["chapter_id"],
            chapter_title=ch["title"],
            chapter_context=chapter_context,
        )
        print(f"   ✅ 提取 {len(elements)} 个元素\n")
        all_elements.extend(elements)

        # 更新上下文
        summary = extractor.generate_chapter_summary(elements)
        chapter_context += f"\n第{ch['chapter_id']}章摘要: {summary}"

    print(f"🎯 总计提取 {len(all_elements)} 个结构化元素\n")

    # 构建 YAML 剧本
    print("🏗️  构建 YAML 剧本...")
    builder = ScriptBuilder(
        title=args.title or chapters[0]["title"],
        original_work=args.title or chapters[0]["title"],
        author=args.author or "未知",
    )

    script = builder.build(
        all_elements=all_elements,
        include_emotion=config["output"]["include_emotion"],
        include_action=config["output"]["include_action"],
    )

    # 保存
    os.makedirs(args.output, exist_ok=True)
    safe_title = (
        args.title or chapters[0]["title"]
    ).replace(" ", "_")[:20]
    output_path = os.path.join(args.output, f"{safe_title}_剧本.yaml")
    builder.save(script, output_path)

    # 打印摘要
    print_script_summary(script)

    print()
    print("=" * 60)
    print("✨ 转换完成！")
    print(f"   YAML 剧本: {output_path}")
    print(f"   可直接用文本编辑器打开编辑")
    print(f"   也可导入到支持 YAML 的剧本工具中进一步打磨")
    print("=" * 60)


if __name__ == "__main__":
    main()
