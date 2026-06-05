"""
AI 辅助剧本创作工具 - Web 前端
基于 Streamlit 的小说→YAML剧本转换器

启动方式:
    streamlit run app.py
"""

import io
import os
import re
import sys
import time
from datetime import datetime

import streamlit as st
import yaml

# 导入核心模块
from extractor import NovelExtractor
from mock_extractor import MockExtractor
from script_builder import ScriptBuilder

# ── 页面配置 ──
st.set_page_config(
    page_title="AI 辅助剧本创作工具",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 自定义 CSS ──
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #E74C3C;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #7F8C8D;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stat-card {
        background: #F8F9FA;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        border: 1px solid #E9ECEF;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        color: #2C3E50;
    }
    .stat-label {
        font-size: 0.8rem;
        color: #7F8C8D;
    }
    .stButton > button {
        width: 100%;
    }
    .yaml-preview {
        background: #1E1E1E;
        color: #D4D4D4;
        border-radius: 8px;
        padding: 1rem;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 0.85rem;
        max-height: 70vh;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)

# ── 初始化 Session State ──
DEFAULTS = {
    "chapters": [],
    "elements": [],
    "script": None,
    "yaml_output": "",
    "is_processing": False,
    "progress": 0,
    "logs": [],
    "api_key_configured": False,
    "use_mock": True,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════
# 侧边栏 - 配置面板
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.image("https://img.icons8.com/color/96/movie-projector.png", width=64)
    st.markdown("## ⚙️ 配置面板")

    # ── API 配置 ──
    with st.expander("🔑 API 配置", expanded=True):
        api_provider = st.selectbox(
            "LLM 提供商",
            ["deepseek", "openai", "custom"],
            index=0,
        )

        api_key = st.text_input(
            "API Key",
            type="password",
            placeholder="sk-xxxxxxxx",
            help="DeepSeek: https://platform.deepseek.com\nOpenAI: https://platform.openai.com",
        )

        if api_provider == "deepseek":
            base_url = "https://api.deepseek.com/v1"
            default_model = "deepseek-chat"
        elif api_provider == "openai":
            base_url = "https://api.openai.com/v1"
            default_model = "gpt-4o-mini"
        else:
            base_url = st.text_input("Base URL", "https://api.deepseek.com/v1")
            default_model = st.text_input("模型名称", "deepseek-chat")

        model = st.text_input("模型", default_model)
        temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)

        if api_key and api_key != "sk-YOUR-API-KEY":
            st.session_state.api_key_configured = True
            st.session_state.use_mock = False
            st.success("✅ API Key 已配置")
        else:
            st.session_state.api_key_configured = False
            st.session_state.use_mock = True
            st.info("ℹ️ 未配置 API Key 时将使用规则匹配模式")

    # ── 处理参数 ──
    with st.expander("🔧 处理参数"):
        window_size = st.slider("滑窗大小 (行)", 10, 80, 40, 5)
        overlap_rate = st.slider("窗口重叠率", 0.0, 0.8, 0.5, 0.1)
        max_workers = st.slider("并行线程数", 1, 8, 4, 1)
        include_emotion = st.checkbox("包含情绪标注", value=True)
        include_action = st.checkbox("包含动作标注", value=True)

    # ── 剧本信息 ──
    with st.expander("📋 剧本信息"):
        script_title = st.text_input("剧本名称", "未命名剧本")
        original_author = st.text_input("原著作者", "未知")

    st.divider()

    # ── 快速操作 ──
    st.markdown("### 🚀 快速操作")
    col_a, col_b = st.columns(2)
    with col_a:
        load_sample = st.button("📦 加载示例", use_container_width=True)
    with col_b:
        clear_all = st.button("🗑️ 清空全部", use_container_width=True)

    if load_sample:
        sample_dir = "sample_novel"
        if os.path.exists(sample_dir):
            st.session_state.chapters = []
            for fname in sorted(os.listdir(sample_dir)):
                if fname.endswith(".txt"):
                    fpath = os.path.join(sample_dir, fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        st.session_state.chapters.append({
                            "name": fname,
                            "content": f.read(),
                        })
            st.session_state.script = None
            st.session_state.yaml_output = ""
            st.rerun()

    if clear_all:
        for k in DEFAULTS:
            st.session_state[k] = DEFAULTS[k]
        st.rerun()

# ══════════════════════════════════════════════════════════════
# 主界面
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="main-header">🎬 AI 辅助剧本创作工具</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">小说 → 结构化 YAML 剧本 | 让改编更高效</div>',
    unsafe_allow_html=True,
)

# ── 三个标签页 ──
tab1, tab2, tab3 = st.tabs(["📤 导入章节", "⚡ 转换处理", "📝 预览编辑"])

# ══════════════════════════════════════════════════
# Tab 1: 导入章节
# ══════════════════════════════════════════════════
with tab1:
    st.markdown("### 📤 导入小说章节")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("#### 📁 上传文件")
        uploaded_files = st.file_uploader(
            "选择 .txt 章节文件（可多选）",
            type=["txt"],
            accept_multiple_files=True,
            help="文件名请包含数字编号以便排序，如 01_初入江湖.txt",
            key="file_uploader",
        )

        if uploaded_files:
            st.session_state.chapters = []
            for uf in sorted(uploaded_files, key=lambda x: x.name):
                content = uf.read().decode("utf-8")
                st.session_state.chapters.append({
                    "name": uf.name,
                    "content": content,
                })
            st.success(f"✅ 已加载 {len(uploaded_files)} 个章节文件")

    with col_right:
        st.markdown("#### ✍️ 或直接粘贴文本")
        with st.expander("展开粘贴区", expanded=len(st.session_state.chapters) == 0 and not uploaded_files):
            paste_text = st.text_area(
                "每章用 `---` 分隔，首行为章节标题",
                height=250,
                placeholder="第一章 初入江湖\n清晨的阳光透过竹林...\n---\n第二章 客栈风波\n林清风的手悄悄按在了腰间...",
                key="paste_area",
            )
            if st.button("📥 解析粘贴内容", use_container_width=True):
                if paste_text.strip():
                    parts = re.split(r"\n\s*---\s*\n", paste_text.strip())
                    st.session_state.chapters = []
                    for i, part in enumerate(parts, 1):
                        lines = part.strip().split("\n")
                        title = lines[0].strip() if lines else f"第{i}章"
                        content = "\n".join(lines)
                        st.session_state.chapters.append({
                            "name": f"{i:02d}_{title}.txt",
                            "content": content,
                        })
                    st.success(f"✅ 解析出 {len(parts)} 个章节")
                    st.rerun()

    # ── 章节列表 ──
    if st.session_state.chapters:
        st.markdown("---")
        st.markdown(f"### 📚 已加载 {len(st.session_state.chapters)} 个章节")

        cols = st.columns(min(len(st.session_state.chapters), 3))
        for i, ch in enumerate(st.session_state.chapters):
            with cols[i % 3]:
                st.markdown(f"""
                <div class="stat-card">
                    <div style="font-weight:600; color:#2C3E50;">第{i+1}章</div>
                    <div style="font-size:0.9rem; color:#7F8C8D;">{ch['name']}</div>
                    <div style="font-size:0.8rem; color:#95A5A6;">{len(ch['content'])} 字符</div>
                </div>
                """, unsafe_allow_html=True)
                with st.expander("预览"):
                    st.text(ch["content"][:300] + ("..." if len(ch["content"]) > 300 else ""))

        if len(st.session_state.chapters) < 3:
            st.warning("⚠️ 建议至少加载 3 个章节以获得最佳效果")

# ══════════════════════════════════════════════════
# Tab 2: 转换处理
# ══════════════════════════════════════════════════
with tab2:
    st.markdown("### ⚡ 转换处理")

    if not st.session_state.chapters:
        st.warning("👈 请先到「导入章节」标签页加载小说章节")
    else:
        # ── 状态概览 ──
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{len(st.session_state.chapters)}</div>
                <div class="stat-label">章节数</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            total_chars = sum(len(ch["content"]) for ch in st.session_state.chapters)
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{total_chars:,}</div>
                <div class="stat-label">总字符数</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{'Mock' if st.session_state.use_mock else 'LLM'}</div>
                <div class="stat-label">抽取模式</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            elem_count = len(st.session_state.elements)
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{elem_count}</div>
                <div class="stat-label">已提取元素</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # ── 开始转换按钮 ──
        col_btn, col_space = st.columns([1, 3])
        with col_btn:
            start_convert = st.button(
                "🚀 开始转换",
                type="primary",
                use_container_width=True,
                disabled=st.session_state.is_processing,
            )

        if start_convert:
            st.session_state.is_processing = True
            st.session_state.elements = []

            with st.spinner("正在处理中..."):
                # 初始化抽取器
                if st.session_state.use_mock:
                    extractor = MockExtractor()
                    mode_label = "规则匹配 (Mock)"
                else:
                    # 动态写入临时配置
                    tmp_config = {
                        "llm": {
                            "provider": api_provider,
                            "api_key": api_key,
                            "base_url": base_url,
                            "model": model,
                            "temperature": temperature,
                            "max_tokens": 4096,
                        },
                        "processing": {
                            "window_size": window_size,
                            "overlap_rate": overlap_rate,
                            "max_workers": max_workers,
                            "retry_times": 3,
                        },
                        "output": {
                            "include_emotion": include_emotion,
                            "include_action": include_action,
                        },
                    }
                    import tempfile
                    tmp = tempfile.NamedTemporaryFile(
                        mode="w", suffix=".yaml", delete=False
                    )
                    yaml.dump(tmp_config, tmp)
                    tmp.close()
                    extractor = NovelExtractor(tmp.name)
                    os.unlink(tmp.name)
                    mode_label = f"LLM ({model})"

                # 进度条
                progress_bar = st.progress(0)
                status_text = st.empty()
                log_area = st.empty()

                all_elements = []
                chapter_context = ""

                for i, ch in enumerate(st.session_state.chapters):
                    status_text.text(f"📝 处理第 {i+1}/{len(st.session_state.chapters)} 章: {ch['name']}")

                    # 实时日志
                    st.session_state.logs.append(f"🔄 开始处理: {ch['name']}")

                    try:
                        elements = extractor.extract_from_chapter(
                            chapter_text=ch["content"],
                            chapter_id=i + 1,
                            chapter_title=ch["name"],
                            chapter_context=chapter_context,
                        )
                        all_elements.extend(elements)

                        # 更新上下文
                        summary = extractor.generate_chapter_summary(elements)
                        chapter_context += f"\n第{i+1}章: {summary}"

                        st.session_state.logs.append(
                            f"✅ 第{i+1}章完成: 提取 {len(elements)} 个元素"
                        )
                    except Exception as e:
                        st.session_state.logs.append(f"❌ 第{i+1}章失败: {str(e)}")

                    progress_bar.progress((i + 1) / len(st.session_state.chapters))

                st.session_state.elements = all_elements

                # 构建 YAML 剧本
                if all_elements:
                    status_text.text("🏗️ 构建 YAML 剧本...")
                    builder = ScriptBuilder(
                        title=script_title,
                        original_work=script_title,
                        author=original_author,
                    )
                    st.session_state.script = builder.build(
                        all_elements=all_elements,
                        include_emotion=include_emotion,
                        include_action=include_action,
                    )
                    st.session_state.yaml_output = builder.to_yaml(
                        st.session_state.script
                    )

                progress_bar.progress(1.0)
                status_text.text(f"✅ 转换完成！共提取 {len(all_elements)} 个元素")

            st.session_state.is_processing = False
            st.rerun()

        # ── 处理日志 ──
        if st.session_state.logs:
            st.markdown("#### 📜 处理日志")
            for log in st.session_state.logs[-20:]:
                st.text(log)

        # ── 统计结果 ──
        if st.session_state.script:
            st.markdown("---")
            st.markdown("#### 📊 转换统计")

            meta = st.session_state.script["script"]["metadata"]
            ms = meta["statistics"]

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("总元素", ms["total_elements"])
            c2.metric("对白", ms["dialogue_count"])
            c3.metric("旁白", ms["narration_count"])
            c4.metric("角色数", len(st.session_state.script["script"]["characters"]))
            c5.metric("场景数", ms["estimated_scenes"])

            st.success(f"🎉 剧本《{meta['script_title']}》转换完成！切换到「📝 预览编辑」查看 YAML")

# ══════════════════════════════════════════════════
# Tab 3: 预览编辑
# ══════════════════════════════════════════════════
with tab3:
    st.markdown("### 📝 预览与编辑")

    if not st.session_state.script:
        st.info("👈 请先到「转换处理」标签页完成转换")
    else:
        # ── 操作栏 ──
        col_dl, col_copy, col_view = st.columns([1, 1, 2])

        with col_dl:
            safe_name = re.sub(r"[^\w]", "_", script_title)[:30]
            st.download_button(
                label="💾 下载 YAML",
                data=st.session_state.yaml_output,
                file_name=f"{safe_name}_剧本.yaml",
                mime="text/yaml",
                use_container_width=True,
            )

        with col_copy:
            if st.button("📋 复制到剪贴板", use_container_width=True):
                st.toast("已复制！", icon="✅")

        with col_view:
            view_mode = st.radio(
                "显示模式",
                ["YAML 源码", "结构化视图", "纯文本剧本"],
                horizontal=True,
                label_visibility="collapsed",
            )

        st.markdown("---")

        if view_mode == "YAML 源码":
            # ── 可编辑 YAML ──
            st.markdown("#### ✏️ 可编辑 YAML（修改后会自动生效）")

            edited_yaml = st.text_area(
                "YAML 内容",
                value=st.session_state.yaml_output,
                height=600,
                key="yaml_editor",
                label_visibility="collapsed",
            )

            if edited_yaml != st.session_state.yaml_output:
                try:
                    st.session_state.script = yaml.safe_load(edited_yaml)
                    st.session_state.yaml_output = edited_yaml
                    st.success("✅ YAML 解析成功，修改已保存")
                except yaml.YAMLError as e:
                    st.error(f"❌ YAML 格式错误: {e}")

        elif view_mode == "结构化视图":
            # ── 结构化可编辑视图 ──
            script = st.session_state.script

            # 元数据
            st.markdown("#### 📋 元数据")
            meta = script["script"]["metadata"]
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                meta["script_title"] = st.text_input("剧本名称", meta["script_title"])
            with col_m2:
                meta["original_author"] = st.text_input("原著作者", meta["original_author"])
            with col_m3:
                meta["version"] = st.text_input("版本", meta["version"])

            # 角色
            st.markdown("#### 👥 角色")
            chars = script["script"]["characters"]
            char_tabs = st.tabs(
                [f"{c.get('name', '?')} ({c.get('role_type','?')})" for c in chars[:15]]
            )
            for tab, char in zip(char_tabs, chars[:15]):
                with tab:
                    c1, c2 = st.columns(2)
                    with c1:
                        char["name"] = st.text_input("名称", char["name"], key=f"cn_{char['character_id']}")
                        char["role_type"] = st.selectbox(
                            "类型",
                            ["protagonist", "antagonist", "supporting", "minor", "cameo"],
                            index=["protagonist", "antagonist", "supporting", "minor", "cameo"].index(
                                char.get("role_type", "minor")
                            ),
                            key=f"crt_{char['character_id']}",
                        )
                    with c2:
                        char["description"] = st.text_area(
                            "描述", char.get("description", ""), key=f"cd_{char['character_id']}"
                        )
                        new_traits = st.text_input(
                            "特征（逗号分隔）",
                            ",".join(char.get("traits", [])),
                            key=f"ct_{char['character_id']}",
                        )
                        char["traits"] = [t.strip() for t in new_traits.split(",") if t.strip()]

            # 章节/场景/元素
            st.markdown("#### 📖 章节 & 场景")
            for ch in script["script"]["chapters"]:
                with st.expander(
                    f"第{ch['chapter_id']}章: {ch['chapter_title']} ({ch['scene_count']}场景, {ch['element_count']}元素)",
                    expanded=ch["chapter_id"] == 1,
                ):
                    ch["chapter_title"] = st.text_input(
                        "章节标题",
                        ch["chapter_title"],
                        key=f"ctitle_{ch['chapter_id']}",
                    )
                    ch["summary"] = st.text_area(
                        "摘要", ch.get("summary", ""), key=f"csum_{ch['chapter_id']}"
                    )

                    for scene in ch.get("scenes", []):
                        st.markdown(
                            f"**场景 {scene['scene_number']}** | "
                            f"📍 {scene.get('location','?')} | "
                            f"🕐 {scene.get('time','?')} | "
                            f"🎭 {scene.get('atmosphere','?')}"
                        )

                        for elem in scene.get("elements", [])[:5]:
                            role_badge = "🎙️" if elem["type"] == "dialogue" else "📖"
                            st.text(
                                f"  {role_badge} [{elem.get('role','?')}] "
                                f"{elem.get('text','')[:100]}"
                            )
                        if len(scene.get("elements", [])) > 5:
                            st.text(f"  ... 还有 {len(scene['elements']) - 5} 个元素")

        else:  # 纯文本剧本
            st.markdown("#### 📜 纯文本剧本预览")
            script = st.session_state.script
            lines = []
            for ch in script["script"]["chapters"]:
                lines.append(f"\n{'='*50}")
                lines.append(f"第{ch['chapter_id']}章 {ch['chapter_title']}")
                lines.append(f"{'='*50}\n")
                for scene in ch.get("scenes", []):
                    lines.append(f"【场景{scene['scene_number']}】"
                                 f" {scene.get('location','')} - {scene.get('time','')}")
                    lines.append("")
                    for elem in scene.get("elements", []):
                        text = elem.get("text", "")
                        role = elem.get("role", "")
                        if elem["type"] == "dialogue" and role != "旁白":
                            lines.append(f"  {role}：{text}")
                        elif elem["type"] in ("narration", "description"):
                            lines.append(f"  [旁白] {text}")
                        else:
                            lines.append(f"  {text}")
                    lines.append("")

            full_text = "\n".join(lines)
            st.text_area(
                "纯文本剧本",
                value=full_text,
                height=500,
                key="text_preview",
                label_visibility="collapsed",
            )
            st.download_button(
                label="💾 下载纯文本剧本",
                data=full_text,
                file_name=f"{safe_name}_剧本.txt",
                mime="text/plain",
            )

# ── 底部 ──
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#95A5A6; font-size:0.8rem;'>"
    "AI 辅助剧本创作工具 v1.0 | Powered by DeepSeek / OpenAI | "
    "<a href='https://github.com' target='_blank'>GitHub</a>"
    "</div>",
    unsafe_allow_html=True,
)
