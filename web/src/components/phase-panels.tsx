"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Upload,
  ChartBar,
  TreeStructure,
  Article,
  CheckSquare,
  FilmStrip,
  Download,
  FileText,
  Eye,
  Code,
  Image as ImageIcon,
} from "@phosphor-icons/react";
import { getScript, getReport, listOutputFiles, type ScriptData } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TABS = [
  { id: "ingest", label: "导入", icon: Upload },
  { id: "analyze", label: "分析", icon: ChartBar },
  { id: "plan", label: "规划", icon: TreeStructure },
  { id: "write", label: "剧本", icon: Article },
  { id: "review", label: "审核", icon: CheckSquare },
  { id: "storyboard", label: "分镜", icon: FilmStrip },
  { id: "images", label: "图片", icon: ImageIcon },
  { id: "export", label: "导出", icon: Download },
];

function downloadFile(content: string, filename: string, mime = "text/yaml") {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/* ── YAML Viewer ── */
function YamlViewer({ content }: { content: string }) {
  const highlighted = content.split("\n").map((line) => {
    const indent = line.match(/^(\s*)/)?.[1].length ?? 0;
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#"))
      return `<span style="padding-left:${indent * 2}ch"><span class="yaml-comment">${trimmed || " "}</span></span>`;
    const colonIdx = trimmed.indexOf(":");
    if (colonIdx === -1) return `<span style="padding-left:${indent * 2}ch">${trimmed}</span>`;
    const key = trimmed.slice(0, colonIdx);
    const value = trimmed.slice(colonIdx + 1).trim();
    let cls = "yaml-val";
    if (value === "true" || value === "false") cls = "yaml-bool";
    else if (/^\d+(\.\d+)?$/.test(value)) cls = "yaml-num";
    return `<span style="padding-left:${indent * 2}ch"><span class="yaml-key">${key}</span>: <span class="${cls}">${value}</span></span>`;
  }).join("\n");
  return <pre className="code-surface p-5 overflow-x-auto text-[13px] leading-[1.7]" dangerouslySetInnerHTML={{ __html: highlighted }} />;
}

/* ── Empty state ── */
function EmptyState({ icon: Icon, title, desc }: { icon: React.ElementType; title: string; desc: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-16 h-16 rounded-2xl bg-[#18181b] border border-[#27272a] flex items-center justify-center mb-5">
        <Icon size={28} className="text-[#71717a]" />
      </div>
      <h3 className="text-lg font-semibold text-[#f4f4f5] mb-2">{title}</h3>
      <p className="text-sm text-[#a1a1aa] max-w-[400px]">{desc}</p>
    </div>
  );
}

/* ── Ingest Panel ── */
function IngestPanel({ projectName }: { projectName: string }) {
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setUploading(true); setMessage("");
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) formData.append("files", files[i]);
    try {
      const res = await fetch(`${API_URL}/api/projects/${encodeURIComponent(projectName)}/upload`, { method: "POST", body: formData });
      const data = await res.json();
      setMessage(res.ok ? `✅ 已上传 ${data.files_saved} 个文件` : `❌ ${data.detail || JSON.stringify(data)}`);
    } catch (err) { setMessage(`❌ 上传失败: ${String(err)}`); }
    setUploading(false);
  };
  return (
    <div className="card-surface p-6 flex flex-col gap-4">
      <div className="flex items-center gap-2.5"><Upload size={18} className="text-[#d4a853]" /><h3 className="text-sm font-semibold text-[#f4f4f5]">上传小说章节</h3></div>
      <p className="text-[13px] text-[#a1a1aa]">上传 .txt 小说章节文件。文件名请包含数字编号，如 01_初入江湖.txt</p>
      <label className="flex flex-col items-center justify-center gap-3 p-8 border-2 border-dashed border-[#27272a] rounded-xl hover:border-[#d4a853]/50 cursor-pointer transition-colors">
        <Upload size={32} className="text-[#71717a]" />
        <span className="text-sm text-[#71717a]">{uploading ? "上传中..." : "点击选择 .txt 文件（可多选）"}</span>
        <input type="file" multiple accept=".txt" onChange={handleUpload} disabled={uploading} className="hidden" />
      </label>
      {message && <p className={`text-[13px] ${message.startsWith("✅") ? "text-[#22c55e]" : "text-[#ef4444]"}`}>{message}</p>}
    </div>
  );
}

/* ── Script Panel ── */
function ScriptPanel({ projectName }: { projectName: string }) {
  const [episode, setEpisode] = useState(1);
  const [view, setView] = useState<"yaml" | "preview">("yaml");
  const [script, setScript] = useState<ScriptData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchScript = useCallback(async (ep: number) => {
    setLoading(true); setError(null);
    try { const data = await getScript(projectName, ep); setScript(data); } catch (e) { setError(String(e)); setScript(null); }
    setLoading(false);
  }, []);
  useEffect(() => { fetchScript(episode); }, [episode, fetchScript]);

  const sceneCount = script?.content ? (script.content.match(/scene_id/g) || []).length : 0;
  const elemCount = script?.content ? (script.content.match(/element_id/g) || []).length : 0;

  // YAML → 纯文本剧本
  const handleDownloadTxt = () => {
    if (!script?.content) return;
    const lines: string[] = [];
    const content = script.content;

    // 用正则从 YAML 中提取章节和场景信息
    const chapterMatch = content.match(/chapters:/);
    if (!chapterMatch) { downloadFile(content, `ep${episode.toString().padStart(2, "0")}_script.txt`, "text/plain"); return; }

    // 提取标题
    const titleMatch = content.match(/script_title:\s*(.+)/);
    const title = titleMatch ? titleMatch[1] : `第${episode}集`;

    lines.push(title);
    lines.push("=".repeat(50));
    lines.push("");

    // 按场景分割
    const sceneBlocks = content.split(/(?=  - scene_id:)/);
    for (const block of sceneBlocks) {
      if (!block.includes("scene_id:")) continue;

      const locMatch = block.match(/location:\s*(.+)/);
      const timeMatch = block.match(/time:\s*(.+)/);
      const atmMatch = block.match(/atmosphere:\s*(.+)/);
      const sceneNum = block.match(/scene_number:\s*(\d+)/);

      const location = locMatch ? locMatch[1].trim() : "未知";
      const time = timeMatch ? timeMatch[1].trim() : "";
      const atmosphere = atmMatch ? atmMatch[1].trim() : "";

      lines.push(`【场景${sceneNum ? sceneNum[1] : "?"}】${location}${time ? " · " + time : ""}${atmosphere ? " · " + atmosphere : ""}`);
      lines.push("");

      // 提取元素
      const elemBlocks = block.split(/(?=  - element_id:)/);
      for (const eb of elemBlocks) {
        if (!eb.includes("element_id:")) continue;
        const typeMatch = eb.match(/type:\s*(.+)/);
        const roleMatch = eb.match(/role:\s*(.+)/);
        const textMatch = eb.match(/text:\s*(.+)/);
        const emotionMatch = eb.match(/emotion:\s*(.+)/);
        const actionMatch = eb.match(/action:\s*(.+)/);
        const subtextMatch = eb.match(/subtext:\s*(.+)/);

        const type = typeMatch ? typeMatch[1].trim() : "";
        const role = roleMatch ? roleMatch[1].trim() : "";
        const text = textMatch ? textMatch[1].trim() : "";
        const emotion = emotionMatch ? emotionMatch[1].trim() : "";
        const action = actionMatch ? actionMatch[1].trim() : "";
        const subtext = subtextMatch ? subtextMatch[1].trim() : "";

        if (type === "dialogue" && role !== "旁白") {
          const emot = emotion ? `（${emotion}）` : "";
          lines.push(`  ${role}${emot}：${text}`);
        } else if (type === "action") {
          const actText = action || text;
          lines.push(`  [${actText}]`);
        } else if (type === "narration" || type === "description") {
          lines.push(`  ${text}`);
        } else if (text) {
          lines.push(`  ${text}`);
        }
      }
      lines.push("");
    }

    downloadFile(lines.join("\n"), `ep${episode.toString().padStart(2, "0")}_剧本.txt`, "text/plain;charset=utf-8");
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-sm text-[#71717a]">集数:</span>
        {[1, 2, 3].map((ep) => (
          <button key={ep} onClick={() => setEpisode(ep)} className={`px-3 py-1.5 text-[13px] font-mono rounded-md transition-all ${
            episode === ep ? "bg-[#d4a853]/10 text-[#d4a853] border border-[#d4a853]/30" : "text-[#a1a1aa] border border-[#27272a] hover:border-[#3f3f46]"}`}>
            第{ep.toString().padStart(2, "0")}集
          </button>
        ))}
        <div className="ml-auto flex gap-2">
          <button onClick={handleDownloadTxt} disabled={!script?.content}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[13px] font-medium rounded-lg bg-[#d4a853] text-[#09090b] hover:bg-[#d4a853]/90 transition-all disabled:opacity-30 disabled:cursor-not-allowed">
            <FileText size={14} /> 下载 TXT</button>
          <button onClick={() => script?.content && downloadFile(script.content, `ep${episode.toString().padStart(2, "0")}_script.yaml`)} disabled={!script?.content}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[13px] font-medium rounded-lg border border-[#27272a] text-[#a1a1aa] hover:text-[#f4f4f5] transition-all disabled:opacity-30 disabled:cursor-not-allowed">
            <Download size={14} /> 下载 YAML</button>
        </div>
      </div>
      <div className="flex items-center gap-1 p-1 bg-[#18181b] border border-[#27272a] rounded-lg w-fit">
        <button onClick={() => setView("yaml")} className={`flex items-center gap-1.5 px-3 py-1.5 text-[13px] rounded-md transition-all ${view === "yaml" ? "bg-[#09090b] text-[#d4a853]" : "text-[#71717a] hover:text-[#a1a1aa]"}`}><Code size={14} /> YAML</button>
        <button onClick={() => setView("preview")} className={`flex items-center gap-1.5 px-3 py-1.5 text-[13px] rounded-md transition-all ${view === "preview" ? "bg-[#09090b] text-[#d4a853]" : "text-[#71717a] hover:text-[#a1a1aa]"}`}><Eye size={14} /> 预览</button>
      </div>
      {loading ? <div className="card-surface p-12 flex items-center justify-center"><p className="text-sm text-[#71717a]">加载中...</p></div>
      : error ? <EmptyState icon={Article} title="暂无剧本" desc="运行管线以生成剧本。" />
      : view === "yaml" ? <YamlViewer content={script?.content || "# 暂无数据"} />
      : <div className="card-surface p-8"><div className="max-w-[65ch] mx-auto space-y-4 text-sm">
        <h3 className="text-xl font-semibold text-[#f4f4f5]">第{episode}集</h3>
        <div className="flex gap-4 text-[11px] font-mono text-[#71717a]"><span>场景: {sceneCount}</span><span>元素: {elemCount}</span></div>
        <p className="text-[#a1a1aa]">切换 YAML 视图查看完整剧本，或点下载按钮保存。</p>
      </div></div>}
    </div>
  );
}

/* ── Review Panel ── */
function ReviewPanel({ projectName }: { projectName: string }) {
  const [episode, setEpisode] = useState(1);
  const [report, setReport] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchReport = useCallback(async (ep: number) => {
    setLoading(true);
    try { const r = await getReport(projectName, `review-${ep}`); setReport(r.content); } catch { setReport(null); }
    setLoading(false);
  }, []);
  useEffect(() => { fetchReport(episode); }, [episode, fetchReport]);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-3">
        <span className="text-sm text-[#71717a]">集数:</span>
        {[1, 2, 3].map((ep) => (
          <button key={ep} onClick={() => setEpisode(ep)} className={`px-3 py-1.5 text-[13px] font-mono rounded-md transition-all ${
            episode === ep ? "bg-[#d4a853]/10 text-[#d4a853] border border-[#d4a853]/30" : "text-[#a1a1aa] border border-[#27272a] hover:border-[#3f3f46]"}`}>
            第{ep.toString().padStart(2, "0")}集
          </button>
        ))}
      </div>
      {loading ? <div className="card-surface p-12 text-center text-sm text-[#71717a]">加载审核报告...</div>
      : report ? <div className="card-surface p-6"><pre className="text-[13px] text-[#a1a1aa] leading-relaxed whitespace-pre-wrap font-mono">{report}</pre></div>
      : <EmptyState icon={CheckSquare} title="暂无审核报告" desc="运行管线后查看审核结果。" />}
    </div>
  );
}

/* ── Storyboard Panel ── */
function StoryboardPanel({ projectName }: { projectName: string }) {
  const [episode, setEpisode] = useState(1);
  const [sbJson, setSbJson] = useState<{ scene_count: number; total_beats: number; total_shots: number; sequences: any[] } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/api/projects/${encodeURIComponent(projectName)}/download/storyboard/ep${episode.toString().padStart(2, "0")}/sequence_board.json`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { setSbJson(d); setLoading(false); })
      .catch(() => { setSbJson(null); setLoading(false); });
  }, [episode]);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-3">
        <span className="text-sm text-[#71717a]">集数:</span>
        {[1, 2, 3].map((ep) => (
          <button key={ep} onClick={() => setEpisode(ep)} className={`px-3 py-1.5 text-[13px] font-mono rounded-md transition-all ${
            episode === ep ? "bg-[#d4a853]/10 text-[#d4a853] border border-[#d4a853]/30" : "text-[#a1a1aa] border border-[#27272a] hover:border-[#3f3f46]"}`}>
            第{ep.toString().padStart(2, "0")}集
          </button>
        ))}
        {sbJson && <span className="ml-auto text-[11px] font-mono text-[#71717a]">{sbJson.scene_count}场景 · {sbJson.total_shots}镜头 · {sbJson.total_beats}节拍</span>}
      </div>
      {loading ? <div className="card-surface p-12 text-center text-sm text-[#71717a]">加载中...</div>
      : !sbJson ? <EmptyState icon={FilmStrip} title="暂无分镜" desc="运行管线后生成分镜数据。" />
      : <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {sbJson.sequences.map((seq: any, i: number) => (
          <div key={i} className="card-surface p-4 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-[#f4f4f5]">场景 {seq.scene_number}</span>
              <span className="text-[11px] font-mono text-[#71717a]">{seq.shot_count} 镜头</span>
            </div>
            <div className="text-[12px] text-[#a1a1aa]">
              📍 {seq.location} · 🕐 {seq.time} · 🎭 {seq.atmosphere || "—"}
            </div>
            <div className="text-[11px] text-[#71717a]">节拍: {seq.beats.join(" · ")}</div>
            <div className="mt-2 space-y-1 max-h-[300px] overflow-y-auto">
              {seq.shots.slice(0, 10).map((shot: any) => (
                <div key={shot.shot_id} className="flex items-start gap-2 text-[11px] py-1 border-b border-[#1f1f23] last:border-0">
                  <span className="font-mono text-[#d4a853] shrink-0 w-[24px]">{shot.camera}</span>
                  <span className="text-[#71717a] font-mono shrink-0 w-[60px] truncate">{shot.role}</span>
                  <span className="text-[#a1a1aa] truncate">{shot.text}</span>
                </div>
              ))}
              {seq.shot_count > 10 && <div className="text-[10px] text-[#71717a] text-center">... 还有 {seq.shot_count - 10} 个镜头</div>}
            </div>
          </div>
        ))}
      </div>}
    </div>
  );
}

/* ── Plan Panel ── */
function PlanPanel({ projectName }: { projectName: string }) {
  const [plan, setPlan] = useState<string | null>(null);
  const [emotion, setEmotion] = useState<any[] | null>(null);
  useEffect(() => {
    getReport(projectName, "plan").then(r => setPlan(r.content)).catch(() => setPlan(null));
    getReport(projectName, "emotion").then(r => {
      try { setEmotion(JSON.parse(r.content)); } catch { setEmotion(null); }
    }).catch(() => setEmotion(null));
  }, [projectName]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div className="card-surface p-6 flex flex-col gap-4">
        <div className="flex items-center gap-2.5">
          <TreeStructure size={18} className="text-[#d4a853]" />
          <h3 className="text-sm font-semibold text-[#f4f4f5]">分集规划</h3>
        </div>
        {plan ? <pre className="text-[13px] text-[#a1a1aa] leading-relaxed whitespace-pre-wrap font-mono">{plan}</pre>
        : <p className="text-sm text-[#71717a]">暂无规划数据，运行管线后生成。</p>}
      </div>
      <div className="card-surface p-6 flex flex-col gap-4">
        <div className="flex items-center gap-2.5">
          <ChartBar size={18} className="text-[#d4a853]" />
          <h3 className="text-sm font-semibold text-[#f4f4f5]">情绪曲线</h3>
        </div>
        {emotion && emotion.length > 0 ? (
          <div className="space-y-4">
            {emotion.map((ep: any) => (
              <div key={ep.episode_id} className="p-4 rounded-lg bg-[#141416] border border-[#1f1f23]">
                <div className="flex justify-between text-[13px] mb-2">
                  <span className="text-[#f4f4f5] font-medium">第{ep.episode_id}集</span>
                  <span className="text-[#71717a] font-mono">{ep.style} · 峰值{ep.peak_value}/谷值{ep.valley_value}</span>
                </div>
                <div className="flex items-end gap-1 h-16 mb-2">
                  {(ep.emotion_sequence || []).map((v: number, i: number) => (
                    <div key={i} className="flex-1 rounded-t-sm" style={{
                      height: `${(v / 10) * 100}%`,
                      backgroundColor: v >= 7 ? '#22c55e' : v >= 4 ? '#d4a853' : '#ef4444',
                      opacity: 0.8,
                    }} />
                  ))}
                </div>
                <p className="text-[12px] text-[#a1a1aa]">{ep.rhythm_description}</p>
              </div>
            ))}
          </div>
        ) : <p className="text-sm text-[#71717a]">暂无情绪曲线数据。</p>}
      </div>
    </div>
  );
}

/* ── Analysis Panel ── */
function AnalysisPanel({ projectName }: { projectName: string }) {
  const [report, setReport] = useState<string | null>(null);
  useEffect(() => { getReport(projectName, "analysis").then(r => setReport(r.content)).catch(() => setReport(null)); }, []);
  return report ? <div className="card-surface p-6"><pre className="text-[13px] text-[#a1a1aa] leading-relaxed whitespace-pre-wrap font-mono">{report}</pre></div> : <EmptyState icon={ChartBar} title="暂无分析报告" desc="运行管线后生成。" />;
}

/* ── Export Panel ── */
function ExportPanel({ projectName }: { projectName: string }) {
  const [files, setFiles] = useState<{ name: string; path: string; size: number }[]>([]);
  useEffect(() => { listOutputFiles(projectName).then(r => setFiles(r.files)).catch(() => {}); }, []);
  const downloadAll = async () => { for (let ep = 1; ep <= 3; ep++) { try { const d = await getScript(projectName, ep); if (d?.content) downloadFile(d.content, `ep${ep.toString().padStart(2, "0")}_script.yaml`); } catch {} } };
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 card-surface p-6 flex flex-col md:flex-row gap-6 items-start">
          <div className="w-12 h-12 rounded-xl bg-[#d4a853]/10 border border-[#d4a853]/20 flex items-center justify-center shrink-0"><Download size={22} className="text-[#d4a853]" /></div>
          <div className="flex-1"><h4 className="text-sm font-semibold text-[#f4f4f5]">全部剧本 (YAML)</h4><p className="text-[13px] text-[#a1a1aa] mt-1">下载全部已生成集数的 YAML 剧本。</p><p className="text-[11px] font-mono text-[#71717a] mt-2">{files.filter(f => f.path.endsWith(".yaml")).length} 个 YAML 文件</p></div>
          <button onClick={downloadAll} className="px-5 py-2 text-[13px] font-medium rounded-lg bg-[#d4a853] text-[#09090b] hover:bg-[#d4a853]/90 transition-all active:scale-[0.98] shrink-0">下载全部</button>
        </div>
        <div className="card-surface p-5 flex flex-col gap-3">
          <div className="w-10 h-10 rounded-lg bg-[#d4a853]/10 border border-[#d4a853]/20 flex items-center justify-center"><FileText size={18} className="text-[#d4a853]" /></div>
          <h4 className="text-sm font-semibold text-[#f4f4f5]">项目文件</h4>
          <div className="flex-1 max-h-[250px] overflow-y-auto mt-2 space-y-0.5">
            {files.length === 0 ? <p className="text-[11px] text-[#71717a]">暂无文件</p>
            : files.map(f => <div key={f.path} className="flex justify-between text-[11px] py-1 border-b border-[#1f1f23] last:border-0"><span className="text-[#a1a1aa] font-mono truncate max-w-[200px]">{f.path}</span><span className="text-[#71717a]">{Math.round(f.size/1024)} KB</span></div>)}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Images Panel ── */
function ImagesPanel({ projectName }: { projectName: string }) {
  const [episode, setEpisode] = useState(1);
  const [data, setData] = useState<{ images: { name: string; url: string; size: number }[]; prompts: any[] } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/api/projects/${encodeURIComponent(projectName)}/images/${episode}`)
      .then(r => r.json()).then(d => { setData(d); setLoading(false); })
      .catch(() => { setData(null); setLoading(false); });
  }, [episode]);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-3">
        <span className="text-sm text-[#71717a]">集数:</span>
        {[1, 2, 3].map((ep) => (
          <button key={ep} onClick={() => setEpisode(ep)} className={`px-3 py-1.5 text-[13px] font-mono rounded-md transition-all ${
            episode === ep ? "bg-[#d4a853]/10 text-[#d4a853] border border-[#d4a853]/30" : "text-[#a1a1aa] border border-[#27272a] hover:border-[#3f3f46]"}`}>
            第{ep.toString().padStart(2, "0")}集
          </button>
        ))}
        {data && <span className="ml-auto text-[11px] font-mono text-[#71717a]">{data.images.length} 张图片</span>}
      </div>
      {loading ? <div className="card-surface p-12 text-center text-sm text-[#71717a]">加载中...</div>
      : !data || data.images.length === 0 ? <EmptyState icon={ImageIcon} title="暂无图片" desc="运行管线生成图片。需要配置图片 API key。" />
      : <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.images.map((img: any) => (
          <div key={img.name} className="card-surface overflow-hidden">
            <img src={`${API_URL}${img.url}`} alt={img.name} className="w-full h-48 object-cover" loading="lazy" />
            <div className="p-2 flex justify-between text-[11px]">
              <span className="text-[#a1a1aa] font-mono">{img.name}</span>
              <span className="text-[#71717a]">{Math.round(img.size/1024)} KB</span>
            </div>
          </div>
        ))}
      </div>}
    </div>
  );
}

/* ── Main ── */
export default function PhasePanels({ projectName }: { projectName: string }) {
  const [activeTab, setActiveTab] = useState("write");
  const render = () => {
    switch (activeTab) {
      case "ingest": return <IngestPanel projectName={projectName} />;
      case "analyze": return <AnalysisPanel projectName={projectName} />;
      case "plan": return <PlanPanel projectName={projectName} />;
      case "write": return <ScriptPanel projectName={projectName} />;
      case "review": return <ReviewPanel projectName={projectName} />;
      case "storyboard": return <StoryboardPanel projectName={projectName} />;
      case "images": return <ImagesPanel projectName={projectName} />;
      case "export": return <ExportPanel projectName={projectName} />;
      default: return null;
    }
  };
  return (
    <section id="dashboard" className="py-24 px-6">
      <div className="max-w-[1400px] mx-auto">
        <div className="mb-10"><h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-[#f4f4f5]">阶段详情</h2><p className="mt-3 text-sm text-[#a1a1aa] max-w-[65ch]">深入每个管线阶段。编辑剧本、查看审核、管理分镜。</p></div>
        <div className="flex items-center gap-0.5 mb-8 overflow-x-auto pb-2 border-b border-[#27272a]">
          {TABS.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`flex items-center gap-2 px-4 py-2.5 text-[13px] font-medium whitespace-nowrap rounded-t-lg transition-all ${activeTab === tab.id ? "text-[#d4a853] bg-[#d4a853]/5 border-b-2 border-[#d4a853]" : "text-[#71717a] hover:text-[#a1a1aa] border-b-2 border-transparent"}`}>
              <tab.icon size={15} weight={activeTab === tab.id ? "fill" : "regular"} />{tab.label}
            </button>
          ))}
        </div>
        <div key={activeTab}>{render()}</div>
      </div>
    </section>
  );
}
