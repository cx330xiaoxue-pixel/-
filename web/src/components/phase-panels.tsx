"use client";

import { useState, useEffect, useCallback, useRef } from "react";
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
  Star,
  Lightning,
  Target,
  FlagBanner,
  WarningCircle,
  PencilSimple,
  Spinner,
  Globe,
} from "@phosphor-icons/react";
import { motion, AnimatePresence } from "framer-motion";
import { easeOutExpo } from "@/lib/motion";
import {
  getScript,
  getReport,
  listOutputFiles,
  getGradingStats,
  getConflictMap,
  getEpisodeAnnotations,
  reviseScript,
  getTaskStatus,
  type ScriptData,
  type GradingStats,
  type ConflictNode,
  type EpisodeAnnotations,
} from "@/lib/api";

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

const panelVariants = {
  initial: { opacity: 0, y: 20, filter: "blur(2px)" },
  animate: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: {
      duration: 0.45,
      ease: easeOutExpo,
    },
  },
  exit: {
    opacity: 0,
    y: -16,
    filter: "blur(2px)",
    transition: { duration: 0.25, ease: "easeIn" as const },
  },
};

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
  const highlighted = content
    .split("\n")
    .map((line) => {
      const indent = line.match(/^(\s*)/)?.[1].length ?? 0;
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#"))
        return `<span style="padding-left:${indent * 2}ch"><span class="yaml-comment">${trimmed || " "}</span></span>`;
      const colonIdx = trimmed.indexOf(":");
      if (colonIdx === -1)
        return `<span style="padding-left:${indent * 2}ch">${trimmed}</span>`;
      const key = trimmed.slice(0, colonIdx);
      const value = trimmed.slice(colonIdx + 1).trim();
      let cls = "yaml-val";
      if (value === "true" || value === "false") cls = "yaml-bool";
      else if (/^\d+(\.\d+)?$/.test(value)) cls = "yaml-num";
      return `<span style="padding-left:${indent * 2}ch"><span class="yaml-key">${key}</span>: <span class="${cls}">${value}</span></span>`;
    })
    .join("\n");

  return (
    <pre
      className="code-surface p-5 overflow-x-auto text-[13px] leading-[1.7]"
      dangerouslySetInnerHTML={{ __html: highlighted }}
    />
  );
}

/* ── Empty state ── */
function EmptyState({
  icon: Icon,
  title,
  desc,
}: {
  icon: React.ElementType;
  title: string;
  desc: string;
}) {
  return (
    <motion.div
      className="flex flex-col items-center justify-center py-20 text-center"
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      <motion.div
        className="w-16 h-16 rounded-2xl bg-[#18181b] border border-[#27272a] flex items-center justify-center mb-5"
        animate={{ y: [0, -4, 0] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
      >
        <Icon size={28} className="text-[#71717a]" />
      </motion.div>
      <h3 className="text-lg font-semibold text-[#f4f4f5] mb-2">{title}</h3>
      <p className="text-sm text-[#a1a1aa] max-w-[400px]">{desc}</p>
    </motion.div>
  );
}

/* ── Ingest Panel ── */
const CRAWL_GENRES = ["", "玄幻", "武侠", "都市", "言情", "仙侠", "科幻", "历史", "悬疑", "游戏", "军事"];

function IngestPanel({ projectName }: { projectName: string }) {
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");

  // ── Crawler state ──
  const [crawlKeyword, setCrawlKeyword] = useState("");
  const [crawlGenre, setCrawlGenre] = useState("");
  const [crawlResults, setCrawlResults] = useState<import("@/lib/api").CrawlResult[]>([]);
  const [crawlSearching, setCrawlSearching] = useState(false);
  const [crawlError, setCrawlError] = useState<string | null>(null);
  const [selectedNovels, setSelectedNovels] = useState<Set<number>>(new Set());
  const [crawlDownloading, setCrawlDownloading] = useState<Record<number, string>>({});
  const [crawlDone, setCrawlDone] = useState<Set<number>>(new Set());

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setUploading(true);
    setMessage("");
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) formData.append("files", files[i]);
    try {
      const res = await fetch(
        `${API_URL}/api/projects/${encodeURIComponent(projectName)}/upload`,
        { method: "POST", body: formData },
      );
      const data = await res.json();
      setMessage(
        res.ok
          ? `✅ 已上传 ${data.files_saved} 个文件`
          : `❌ ${data.detail || JSON.stringify(data)}`,
      );
    } catch (err) {
      setMessage(`❌ 上传失败: ${String(err)}`);
    }
    setUploading(false);
  };

  const handleCrawlSearch = async () => {
    setCrawlSearching(true);
    setCrawlError(null);
    setSelectedNovels(new Set());
    setCrawlDone(new Set());
    try {
      const { crawlSearch } = await import("@/lib/api");
      const res = await crawlSearch(crawlKeyword, crawlGenre, 20);
      setCrawlResults(res.results || []);
    } catch (e) {
      setCrawlError(String(e));
      setCrawlResults([]);
    }
    setCrawlSearching(false);
  };

  const toggleNovel = (idx: number) => {
    const next = new Set(selectedNovels);
    if (next.has(idx)) next.delete(idx); else next.add(idx);
    setSelectedNovels(next);
  };

  const handleCrawlDownload = async () => {
    const { crawlDownload } = await import("@/lib/api");
    // Download selected novels sequentially
    for (const idx of selectedNovels) {
      if (crawlDone.has(idx)) continue;
      setCrawlDownloading((prev) => ({ ...prev, [idx]: "下载中..." }));
      try {
        const novel = crawlResults[idx];
        await crawlDownload(projectName, novel.source_url, novel.source_name, novel.title);
        setCrawlDone((prev) => new Set(prev).add(idx));
        setCrawlDownloading((prev) => ({ ...prev, [idx]: "✅ 已导入" }));
      } catch (e) {
        setCrawlDownloading((prev) => ({ ...prev, [idx]: `❌ ${String(e).slice(0, 40)}` }));
      }
    }
    if (selectedNovels.size > 0) {
      setMessage("✅ 爬取完成，文件已导入到上传目录");
    }
  };

  return (
    <motion.div
      className="flex flex-col gap-5"
      variants={panelVariants}
      initial="initial"
      animate="animate"
    >
      {/* ── Upload card ── */}
      <div className="card-surface p-6 flex flex-col gap-4">
        <div className="flex items-center gap-2.5">
          <Upload size={18} className="text-[#d4a853]" />
          <h3 className="text-sm font-semibold text-[#f4f4f5]">上传小说章节</h3>
        </div>
        <p className="text-[13px] text-[#a1a1aa]">
          上传 .txt 小说章节文件。文件名请包含数字编号，如 01_初入江湖.txt
        </p>
        <motion.label
          whileHover={{ borderColor: "rgba(212, 168, 83, 0.5)", scale: 1.01 }}
          className="flex flex-col items-center justify-center gap-3 p-8 border-2 border-dashed border-[#27272a] rounded-xl cursor-pointer transition-colors"
        >
          <motion.span
            animate={{ y: [0, -3, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          >
            <Upload size={32} className="text-[#71717a]" />
          </motion.span>
          <span className="text-sm text-[#71717a]">
            {uploading ? "上传中..." : "点击选择 .txt 文件（可多选）"}
          </span>
          <input
            type="file"
            multiple
            accept=".txt"
            onChange={handleUpload}
            disabled={uploading}
            className="hidden"
          />
        </motion.label>
        <AnimatePresence>
          {message && (
            <motion.p
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className={`text-[13px] overflow-hidden ${message.startsWith("✅") ? "text-[#22c55e]" : "text-[#ef4444]"}`}
            >
              {message}
            </motion.p>
          )}
        </AnimatePresence>
      </div>

      {/* ── Online crawl card ── */}
      <div className="card-surface p-6 flex flex-col gap-4">
        <div className="flex items-center gap-2.5">
          <Globe size={18} className="text-[#d4a853]" />
          <h3 className="text-sm font-semibold text-[#f4f4f5]">在线获取小说</h3>
        </div>
        <p className="text-[13px] text-[#a1a1aa]">
          按类型或关键词搜索公开小说源，选择后自动下载到项目。
        </p>

        {/* Search bar */}
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={crawlGenre}
            onChange={(e) => setCrawlGenre(e.target.value)}
            className="px-2.5 py-2 text-[12px] rounded-lg bg-[#141416] border border-[#27272a] text-[#a1a1aa] focus:border-[#d4a853] focus:outline-none"
          >
            <option value="">全部类型</option>
            {CRAWL_GENRES.filter(Boolean).map((g) => (
              <option key={g} value={g}>{g}</option>
            ))}
          </select>
          <input
            type="text"
            value={crawlKeyword}
            onChange={(e) => setCrawlKeyword(e.target.value)}
            placeholder="关键词（可选）"
            onKeyDown={(e) => e.key === "Enter" && handleCrawlSearch()}
            className="flex-1 min-w-[140px] px-3 py-2 text-[13px] rounded-lg bg-[#141416] border border-[#27272a] text-[#f4f4f5] placeholder:text-[#52525b] focus:border-[#d4a853] focus:outline-none"
          />
          <motion.button
            onClick={handleCrawlSearch}
            disabled={crawlSearching}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.96 }}
            className="px-4 py-2 text-[13px] font-medium rounded-lg bg-[#d4a853] text-[#09090b] hover:bg-[#d4a853]/90 transition-all disabled:opacity-50 shrink-0"
          >
            {crawlSearching ? "搜索中..." : "搜索"}
          </motion.button>
        </div>

        {/* Error */}
        <AnimatePresence>
          {crawlError && (
            <motion.p
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="text-[12px] text-[#ef4444] overflow-hidden"
            >
              ❌ {crawlError}
            </motion.p>
          )}
        </AnimatePresence>

        {/* Results */}
        <AnimatePresence>
          {crawlResults.length > 0 && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              className="overflow-hidden"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-[12px] text-[#71717a]">
                  搜索结果 ({crawlResults.length} 部)
                </span>
                {selectedNovels.size > 0 && (
                  <motion.button
                    onClick={handleCrawlDownload}
                    whileHover={{ scale: 1.04 }}
                    whileTap={{ scale: 0.96 }}
                    className="px-3 py-1.5 text-[12px] font-medium rounded-lg bg-[#d4a853] text-[#09090b] hover:bg-[#d4a853]/90 transition-all"
                  >
                    下载选中 ({selectedNovels.size}部)
                  </motion.button>
                )}
              </div>
              <div className="space-y-1.5 max-h-[360px] overflow-y-auto">
                {crawlResults.map((novel, idx) => {
                  const isSelected = selectedNovels.has(idx);
                  const isDone = crawlDone.has(idx);
                  const dlStatus = crawlDownloading[idx];
                  return (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.03 }}
                      onClick={() => !isDone && toggleNovel(idx)}
                      className={`flex items-start gap-3 p-3 rounded-lg border transition-all cursor-pointer ${
                        isDone
                          ? "border-[#22c55e]/30 bg-[#22c55e]/5"
                          : isSelected
                            ? "border-[#d4a853]/40 bg-[#d4a853]/5"
                            : "border-[#1f1f23] bg-[#141416] hover:border-[#3f3f46]"
                      }`}
                    >
                      {/* Checkbox */}
                      <span
                        className={`mt-0.5 w-4 h-4 rounded border flex items-center justify-center shrink-0 text-[10px] transition-all ${
                          isDone
                            ? "bg-[#22c55e] border-[#22c55e] text-white"
                            : isSelected
                              ? "bg-[#d4a853] border-[#d4a853] text-[#09090b]"
                              : "border-[#3f3f46] text-transparent"
                        }`}
                      >
                        {isDone ? "✓" : isSelected ? "✓" : ""}
                      </span>
                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-[13px] font-medium text-[#f4f4f5] truncate">
                            《{novel.title}》
                          </span>
                          {novel.genre && novel.genre !== "未知" && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#d4a853]/10 text-[#d4a853] font-mono shrink-0">
                              {novel.genre}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-[11px] text-[#71717a] mt-0.5">
                          <span>{novel.author}</span>
                          <span>来源: {novel.source_name}</span>
                        </div>
                        {novel.summary && (
                          <p className="text-[11px] text-[#52525b] mt-1 line-clamp-2">
                            {novel.summary}
                          </p>
                        )}
                      </div>
                      {/* Download status */}
                      {dlStatus && (
                        <span
                          className={`text-[11px] shrink-0 ${
                            dlStatus.startsWith("✅")
                              ? "text-[#22c55e]"
                              : dlStatus.startsWith("❌")
                                ? "text-[#ef4444]"
                                : "text-[#d4a853]"
                          }`}
                        >
                          {dlStatus}
                        </span>
                      )}
                    </motion.div>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

/* ── Script Panel ── */
function ScriptPanel({ projectName }: { projectName: string }) {
  const [episode, setEpisode] = useState(1);
  const [view, setView] = useState<"yaml" | "preview">("yaml");
  const [script, setScript] = useState<ScriptData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Revision / micro-tune state ──
  const revisionRef = useRef<HTMLTextAreaElement>(null);
  const [revisionNotesDirty, setRevisionNotesDirty] = useState(false);
  const [revisionTaskId, setRevisionTaskId] = useState<string | null>(null);
  const [revisionStatus, setRevisionStatus] = useState<
    "idle" | "submitting" | "running" | "done" | "failed"
  >("idle");
  const [revisionError, setRevisionError] = useState<string | null>(null);

  const fetchScript = useCallback(async (ep: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getScript(projectName, ep);
      setScript(data);
    } catch (e) {
      setError(String(e));
      setScript(null);
    }
    setLoading(false);
  }, [projectName]);

  // Poll revision task
  useEffect(() => {
    if (!revisionTaskId) return;
    let count = 0;
    setRevisionStatus("running");
    const interval = setInterval(async () => {
      count++;
      try {
        const task = await getTaskStatus(revisionTaskId);
        if (task.status === "completed") {
          setRevisionTaskId(null);
          setRevisionStatus("done");
          fetchScript(episode);
          setTimeout(() => setRevisionStatus("idle"), 4000);
        } else if (task.status === "failed") {
          setRevisionTaskId(null);
          setRevisionStatus("failed");
          setRevisionError(task.error || "微调失败");
          setTimeout(() => setRevisionStatus("idle"), 5000);
        }
      } catch {
        setRevisionTaskId(null);
        setRevisionStatus("failed");
        setRevisionError("无法获取任务状态");
        setTimeout(() => setRevisionStatus("idle"), 5000);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [revisionTaskId, episode, fetchScript]);

  const handleRevise = async () => {
    const notes = revisionRef.current?.value?.trim();
    if (!notes) return;
    setRevisionStatus("submitting");
    setRevisionError(null);
    try {
      const res = await reviseScript(projectName, episode, notes);
      if (res.task_id) {
        setRevisionTaskId(res.task_id);
      } else {
        setRevisionStatus("failed");
        setRevisionError("未能获取任务ID");
      }
    } catch (e) {
      setRevisionStatus("failed");
      setRevisionError(String(e));
    }
  };

  useEffect(() => {
    fetchScript(episode);
  }, [episode, fetchScript]);

  const sceneCount = script?.content
    ? (script.content.match(/scene_id/g) || []).length
    : 0;
  const elemCount = script?.content
    ? (script.content.match(/element_id/g) || []).length
    : 0;

  const [gradingStats, setGradingStats] = useState<GradingStats | null>(null);
  useEffect(() => {
    getGradingStats(projectName)
      .then((r) => {
        if (r.stats && r.stats.total > 0) setGradingStats(r.stats);
      })
      .catch(() => {});
  }, [projectName, script]);

  const handleDownloadTxt = () => {
    if (!script?.content) return;
    const lines: string[] = [];
    const content = script.content;

    const chapterMatch = content.match(/chapters:/);
    if (!chapterMatch) {
      downloadFile(
        content,
        `ep${episode.toString().padStart(2, "0")}_script.txt`,
        "text/plain",
      );
      return;
    }

    const titleMatch = content.match(/script_title:\s*(.+)/);
    const title = titleMatch ? titleMatch[1] : `第${episode}集`;

    lines.push(title);
    lines.push("=".repeat(50));
    lines.push("");

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

      lines.push(
        `【场景${sceneNum ? sceneNum[1] : "?"}】${location}${time ? " · " + time : ""}${atmosphere ? " · " + atmosphere : ""}`,
      );
      lines.push("");

      const elemBlocks = block.split(/(?=  - element_id:)/);
      for (const eb of elemBlocks) {
        if (!eb.includes("element_id:")) continue;
        const typeMatch = eb.match(/type:\s*(.+)/);
        const roleMatch = eb.match(/role:\s*(.+)/);
        const textMatch = eb.match(/text:\s*(.+)/);
        const emotionMatch = eb.match(/emotion:\s*(.+)/);
        const actionMatch = eb.match(/action:\s*(.+)/);

        const type = typeMatch ? typeMatch[1].trim() : "";
        const role = roleMatch ? roleMatch[1].trim() : "";
        const text = textMatch ? textMatch[1].trim() : "";
        const emotion = emotionMatch ? emotionMatch[1].trim() : "";
        const action = actionMatch ? actionMatch[1].trim() : "";

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

    downloadFile(
      lines.join("\n"),
      `ep${episode.toString().padStart(2, "0")}_剧本.txt`,
      "text/plain;charset=utf-8",
    );
  };

  return (
    <motion.div
      className="flex flex-col gap-5"
      variants={panelVariants}
      initial="initial"
      animate="animate"
    >
      {/* Episode selector + actions */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-sm text-[#71717a]">集数:</span>
        {[1, 2, 3].map((ep) => (
          <motion.button
            key={ep}
            onClick={() => setEpisode(ep)}
            whileHover={{ scale: 1.06 }}
            whileTap={{ scale: 0.94 }}
            className={`px-3 py-1.5 text-[13px] font-mono rounded-md transition-all ${
              episode === ep
                ? "bg-[#d4a853]/10 text-[#d4a853] border border-[#d4a853]/30"
                : "text-[#a1a1aa] border border-[#27272a] hover:border-[#3f3f46]"
            }`}
          >
            第{ep.toString().padStart(2, "0")}集
          </motion.button>
        ))}
        <div className="ml-auto flex gap-2">
          <motion.button
            onClick={handleDownloadTxt}
            disabled={!script?.content}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.96 }}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[13px] font-medium rounded-lg bg-[#d4a853] text-[#09090b] hover:bg-[#d4a853]/90 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <FileText size={14} /> 下载 TXT
          </motion.button>
          <motion.button
            onClick={() =>
              script?.content &&
              downloadFile(
                script.content,
                `ep${episode.toString().padStart(2, "0")}_script.yaml`,
              )
            }
            disabled={!script?.content}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.96 }}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[13px] font-medium rounded-lg border border-[#27272a] text-[#a1a1aa] hover:text-[#f4f4f5] transition-all disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <Download size={14} /> 下载 YAML
          </motion.button>
        </div>
      </div>

      {/* View toggle */}
      <div className="flex items-center gap-1 p-1 bg-[#18181b] border border-[#27272a] rounded-lg w-fit">
        {(["yaml", "preview"] as const).map((v) => (
          <motion.button
            key={v}
            onClick={() => setView(v)}
            whileHover={view !== v ? { scale: 1.04 } : {}}
            whileTap={{ scale: 0.96 }}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-[13px] rounded-md transition-all ${
              view === v
                ? "bg-[#09090b] text-[#d4a853]"
                : "text-[#71717a] hover:text-[#a1a1aa]"
            }`}
          >
            {v === "yaml" ? <Code size={14} /> : <Eye size={14} />}
            {v === "yaml" ? "YAML" : "预览"}
          </motion.button>
        ))}
      </div>

      {/* Grading stats bar */}
      <AnimatePresence>
        {gradingStats && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="card-surface p-4 flex items-center gap-6 flex-wrap overflow-hidden"
          >
            <div className="flex items-center gap-2">
              <Star size={16} weight="fill" className="text-[#22c55e]" />
              <span className="text-[13px] text-[#f4f4f5] font-medium">
                S级核心
              </span>
              <span className="text-lg font-mono font-semibold text-[#22c55e]">
                {gradingStats.S_count}
              </span>
              <span className="text-[11px] text-[#71717a]">
                ({gradingStats.S_ratio}%)
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Lightning size={16} weight="fill" className="text-[#d4a853]" />
              <span className="text-[13px] text-[#f4f4f5] font-medium">
                A级辅助
              </span>
              <span className="text-lg font-mono font-semibold text-[#d4a853]">
                {gradingStats.A_count}
              </span>
              <span className="text-[11px] text-[#71717a]">
                ({gradingStats.A_ratio}%)
              </span>
            </div>
            <div className="flex items-center gap-2">
              <WarningCircle
                size={16}
                weight="fill"
                className="text-[#ef4444]"
              />
              <span className="text-[13px] text-[#f4f4f5] font-medium">
                B级冗余
              </span>
              <span className="text-lg font-mono font-semibold text-[#ef4444]">
                {gradingStats.B_count}
              </span>
              <span className="text-[11px] text-[#71717a]">
                ({gradingStats.B_ratio}% · 已过滤)
              </span>
            </div>
            <div className="flex-1 h-2 bg-[#18181b] rounded-full overflow-hidden min-w-[120px]">
              <div className="flex h-full">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${gradingStats.S_ratio}%` }}
                  transition={{ duration: 0.8, ease: "easeOut" }}
                  className="bg-[#22c55e]"
                />
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${gradingStats.A_ratio}%` }}
                  transition={{ duration: 0.8, delay: 0.15, ease: "easeOut" }}
                  className="bg-[#d4a853]"
                />
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${gradingStats.B_ratio}%` }}
                  transition={{ duration: 0.8, delay: 0.3, ease: "easeOut" }}
                  className="bg-[#ef4444]/30"
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Content area */}
      <AnimatePresence mode="wait">
        {loading ? (
          <motion.div
            key="loading"
            className="card-surface p-12 flex items-center justify-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.p
              className="text-sm text-[#71717a]"
              animate={{ opacity: [0.4, 1, 0.4] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              加载中...
            </motion.p>
          </motion.div>
        ) : error ? (
          <EmptyState
            icon={Article}
            title="暂无剧本"
            desc="运行管线以生成剧本。"
          />
        ) : view === "yaml" ? (
          <motion.div
            key={`yaml-${episode}`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
          >
            <YamlViewer
              content={script?.content || "# 暂无数据"}
            />
          </motion.div>
        ) : (
          <motion.div
            key={`preview-${episode}`}
            className="card-surface p-8"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
          >
            <div className="max-w-[65ch] mx-auto space-y-4 text-sm">
              <h3 className="text-xl font-semibold text-[#f4f4f5]">
                第{episode}集
              </h3>
              <div className="flex gap-4 text-[11px] font-mono text-[#71717a]">
                <span>场景: {sceneCount}</span>
                <span>元素: {elemCount}</span>
              </div>
              <p className="text-[#a1a1aa]">
                切换 YAML 视图查看完整剧本，或点下载按钮保存。
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Micro-tune card ── */}
      <AnimatePresence>
        {!loading && !error && script && (
          <motion.div
            className="card-surface p-5 flex flex-col gap-3"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.35, ease: easeOutExpo }}
          >
            <div className="flex items-center gap-2">
              <PencilSimple size={16} className="text-[#d4a853]" />
              <span className="text-sm font-semibold text-[#f4f4f5]">
                微调剧本
              </span>
              {script.version !== undefined && (
                <span className="ml-auto text-[11px] font-mono text-[#71717a]">
                  v{script.version}
                </span>
              )}
            </div>
            <p className="text-[12px] text-[#71717a]">
              输入修改意见，系统将根据你的反馈重新生成剧本。支持多次微调，每次生成新版本。
            </p>
            <textarea
              ref={revisionRef}
              onChange={(e) => setRevisionNotesDirty(!!e.target.value.trim())}
              placeholder="例如：增加更多动作描写、减少旁白、让对白更口语化、加强角色A的情绪冲突..."
              rows={3}
              disabled={revisionStatus === "running" || revisionStatus === "submitting"}
              className="w-full px-3 py-2.5 text-[13px] rounded-lg bg-[#141416] border border-[#27272a] text-[#f4f4f5] placeholder:text-[#52525b] focus:border-[#d4a853] focus:outline-none resize-y transition-colors disabled:opacity-50"
            />
            <div className="flex items-center gap-3">
              <motion.button
                onClick={handleRevise}
                disabled={
                  revisionStatus === "running" ||
                  revisionStatus === "submitting"
                }
                whileHover={
                  revisionNotesDirty && revisionStatus === "idle"
                    ? { scale: 1.03, boxShadow: "0 0 16px rgba(212,168,83,0.25)" }
                    : {}
                }
                whileTap={{ scale: 0.97 }}
                className={`inline-flex items-center gap-1.5 px-4 py-2 text-[13px] font-medium rounded-lg transition-all ${
                  revisionNotesDirty && revisionStatus === "idle"
                    ? "bg-[#d4a853] text-[#09090b] hover:bg-[#d4a853]/90"
                    : revisionStatus === "running" || revisionStatus === "submitting"
                      ? "bg-[#3b82f6]/10 text-[#3b82f6] border border-[#3b82f6]/30"
                      : revisionStatus === "done"
                        ? "bg-[#22c55e]/10 text-[#22c55e] border border-[#22c55e]/30"
                        : "bg-[#18181b] text-[#52525b] border border-[#27272a] cursor-not-allowed"
                }`}
              >
                {revisionStatus === "running" || revisionStatus === "submitting" ? (
                  <>
                    <motion.span
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                    >
                      <Spinner size={14} />
                    </motion.span>
                    微调中...
                  </>
                ) : revisionStatus === "done" ? (
                  <>✅ 微调完成</>
                ) : (
                  <>
                    <PencilSimple size={14} /> 提交微调
                  </>
                )}
              </motion.button>
              {revisionNotesDirty && revisionStatus === "idle" && (
                <button
                  onClick={() => {
                    if (revisionRef.current) {
                      revisionRef.current.value = "";
                      setRevisionNotesDirty(false);
                    }
                  }}
                  className="text-[12px] text-[#71717a] hover:text-[#a1a1aa] transition-colors"
                >
                  清空
                </button>
              )}
            </div>

            {/* Status feedback */}
            <AnimatePresence>
              {revisionStatus === "done" && (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="text-[12px] text-[#22c55e]"
                >
                  剧本已更新，当前显示最新版本。
                </motion.p>
              )}
              {revisionError && revisionStatus === "failed" && (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="text-[12px] text-[#ef4444]"
                >
                  ❌ {revisionError}
                  <button
                    onClick={() => {
                      setRevisionError(null);
                      setRevisionStatus("idle");
                    }}
                    className="ml-3 underline"
                  >
                    关闭
                  </button>
                </motion.p>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/* ── Review Panel ── */
function ReviewPanel({ projectName }: { projectName: string }) {
  const [episode, setEpisode] = useState(1);
  const [report, setReport] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchReport = useCallback(async (ep: number) => {
    setLoading(true);
    try {
      const r = await getReport(projectName, `review-${ep}`);
      setReport(r.content);
    } catch {
      setReport(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchReport(episode);
  }, [episode, fetchReport]);

  return (
    <motion.div
      className="flex flex-col gap-5"
      variants={panelVariants}
      initial="initial"
      animate="animate"
    >
      <div className="flex items-center gap-3">
        <span className="text-sm text-[#71717a]">集数:</span>
        {[1, 2, 3].map((ep) => (
          <motion.button
            key={ep}
            onClick={() => setEpisode(ep)}
            whileHover={{ scale: 1.06 }}
            whileTap={{ scale: 0.94 }}
            className={`px-3 py-1.5 text-[13px] font-mono rounded-md transition-all ${
              episode === ep
                ? "bg-[#d4a853]/10 text-[#d4a853] border border-[#d4a853]/30"
                : "text-[#a1a1aa] border border-[#27272a] hover:border-[#3f3f46]"
            }`}
          >
            第{ep.toString().padStart(2, "0")}集
          </motion.button>
        ))}
      </div>
      <AnimatePresence mode="wait">
        {loading ? (
          <motion.div
            key="loading"
            className="card-surface p-12 text-center text-sm text-[#71717a]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.span
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              加载审核报告...
            </motion.span>
          </motion.div>
        ) : report ? (
          <motion.div
            key={`report-${episode}`}
            className="card-surface p-6"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <pre className="text-[13px] text-[#a1a1aa] leading-relaxed whitespace-pre-wrap font-mono">
              {report}
            </pre>
          </motion.div>
        ) : (
          <EmptyState
            icon={CheckSquare}
            title="暂无审核报告"
            desc="运行管线后查看审核结果。"
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/* ── Storyboard Panel ── */
function StoryboardPanel({ projectName }: { projectName: string }) {
  const [episode, setEpisode] = useState(1);
  const [sbJson, setSbJson] = useState<{
    scene_count: number;
    total_beats: number;
    total_shots: number;
    sequences: any[];
  } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(
      `${API_URL}/api/projects/${encodeURIComponent(projectName)}/download/storyboard/ep${episode.toString().padStart(2, "0")}/sequence_board.json`,
    )
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        setSbJson(d);
        setLoading(false);
      })
      .catch(() => {
        setSbJson(null);
        setLoading(false);
      });
  }, [episode, projectName]);

  return (
    <motion.div
      className="flex flex-col gap-5"
      variants={panelVariants}
      initial="initial"
      animate="animate"
    >
      <div className="flex items-center gap-3">
        <span className="text-sm text-[#71717a]">集数:</span>
        {[1, 2, 3].map((ep) => (
          <motion.button
            key={ep}
            onClick={() => setEpisode(ep)}
            whileHover={{ scale: 1.06 }}
            whileTap={{ scale: 0.94 }}
            className={`px-3 py-1.5 text-[13px] font-mono rounded-md transition-all ${
              episode === ep
                ? "bg-[#d4a853]/10 text-[#d4a853] border border-[#d4a853]/30"
                : "text-[#a1a1aa] border border-[#27272a] hover:border-[#3f3f46]"
            }`}
          >
            第{ep.toString().padStart(2, "0")}集
          </motion.button>
        ))}
        {sbJson && (
          <motion.span
            className="ml-auto text-[11px] font-mono text-[#71717a]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            {sbJson.scene_count}场景 · {sbJson.total_shots}镜头 ·{" "}
            {sbJson.total_beats}节拍
          </motion.span>
        )}
      </div>
      <AnimatePresence mode="wait">
        {loading ? (
          <motion.div
            key="loading"
            className="card-surface p-12 text-center text-sm text-[#71717a]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.span
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              加载中...
            </motion.span>
          </motion.div>
        ) : !sbJson ? (
          <EmptyState
            icon={FilmStrip}
            title="暂无分镜"
            desc="运行管线后生成分镜数据。"
          />
        ) : (
          <motion.div
            key={`sb-${episode}`}
            className="grid grid-cols-1 lg:grid-cols-2 gap-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            {sbJson.sequences.map((seq: any, i: number) => (
              <motion.div
                key={i}
                className="card-surface p-4 flex flex-col gap-2"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06, duration: 0.4 }}
                whileHover={{
                  scale: 1.02,
                  borderColor: "rgba(212, 168, 83, 0.25)",
                }}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-[#f4f4f5]">
                    场景 {seq.scene_number}
                  </span>
                  <span className="text-[11px] font-mono text-[#71717a]">
                    {seq.shot_count} 镜头
                  </span>
                </div>
                <div className="text-[12px] text-[#a1a1aa]">
                  📍 {seq.location} · 🕐 {seq.time} · 🎭{" "}
                  {seq.atmosphere || "—"}
                </div>
                <div className="text-[11px] text-[#71717a]">
                  节拍: {seq.beats.join(" · ")}
                </div>
                <div className="mt-2 space-y-1 max-h-[300px] overflow-y-auto">
                  {seq.shots.slice(0, 10).map((shot: any) => (
                    <div
                      key={shot.shot_id}
                      className="flex items-start gap-2 text-[11px] py-1 border-b border-[#1f1f23] last:border-0"
                    >
                      <span className="font-mono text-[#d4a853] shrink-0 w-[24px]">
                        {shot.camera}
                      </span>
                      <span className="text-[#71717a] font-mono shrink-0 w-[60px] truncate">
                        {shot.role}
                      </span>
                      <span className="text-[#a1a1aa] truncate">
                        {shot.text}
                      </span>
                    </div>
                  ))}
                  {seq.shot_count > 10 && (
                    <div className="text-[10px] text-[#71717a] text-center">
                      ... 还有 {seq.shot_count - 10} 个镜头
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/* ── Plan Panel (v2.1 enhanced) ── */
function PlanPanel({ projectName }: { projectName: string }) {
  const [plan, setPlan] = useState<string | null>(null);
  const [emotion, setEmotion] = useState<any[] | null>(null);
  const [conflictNodes, setConflictNodes] = useState<ConflictNode[]>([]);
  const [selectedEp, setSelectedEp] = useState(1);
  const [annotations, setAnnotations] = useState<EpisodeAnnotations | null>(
    null,
  );

  useEffect(() => {
    getReport(projectName, "plan")
      .then((r) => setPlan(r.content))
      .catch(() => setPlan(null));
    getReport(projectName, "emotion")
      .then((r) => {
        try {
          setEmotion(JSON.parse(r.content));
        } catch {
          setEmotion(null);
        }
      })
      .catch(() => setEmotion(null));
    getConflictMap(projectName)
      .then((r) => {
        if (r.nodes) setConflictNodes(r.nodes);
      })
      .catch(() => {});
  }, [projectName]);

  useEffect(() => {
    getEpisodeAnnotations(projectName, selectedEp)
      .then((r) => {
        if (r.annotations) setAnnotations(r.annotations);
        else setAnnotations(null);
      })
      .catch(() => setAnnotations(null));
  }, [projectName, selectedEp]);

  const nodeTypes: Record<string, { icon: string; color: string }> = {
    major_twist: { icon: "🔀", color: "#ef4444" },
    scene_shift: { icon: "🎬", color: "#3b82f6" },
    emotional_peak: { icon: "📈", color: "#22c55e" },
    cliffhanger: { icon: "🪝", color: "#d4a853" },
    resolution_point: { icon: "✅", color: "#8b5cf6" },
  };

  return (
    <motion.div
      className="grid grid-cols-1 lg:grid-cols-2 gap-5"
      variants={panelVariants}
      initial="initial"
      animate="animate"
    >
      {/* Episode plan */}
      <motion.div
        className="card-surface p-6 flex flex-col gap-4"
        whileHover={{ borderColor: "rgba(212, 168, 83, 0.2)" }}
      >
        <div className="flex items-center gap-2.5">
          <TreeStructure size={18} className="text-[#d4a853]" />
          <h3 className="text-sm font-semibold text-[#f4f4f5]">分集规划</h3>
          {conflictNodes.length > 0 && (
            <motion.span
              className="ml-auto text-[11px] font-mono text-[#71717a]"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              {conflictNodes.length} 冲突节点
            </motion.span>
          )}
        </div>

        {/* Conflict nodes */}
        <AnimatePresence>
          {conflictNodes.length > 0 && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              className="p-3 rounded-lg bg-[#141416] border border-[#1f1f23] overflow-hidden"
            >
              <div className="text-[11px] text-[#71717a] mb-2 font-medium">
                冲突节点分布
              </div>
              <div className="flex flex-wrap gap-1.5 max-h-[120px] overflow-y-auto">
                {conflictNodes.map((n, i) => {
                  const nt = nodeTypes[n.type] || {
                    icon: "•",
                    color: "#71717a",
                  };
                  return (
                    <motion.span
                      key={n.node_id}
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: i * 0.04 }}
                      whileHover={{ scale: 1.08, borderColor: nt.color }}
                      className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded-full bg-[#18181b] border border-[#27272a] cursor-default"
                      title={n.description}
                    >
                      <span>{nt.icon}</span>
                      <span className="text-[#a1a1aa]">
                        第{n.chapter_id}章
                      </span>
                      <span
                        style={{ color: nt.color }}
                        className="font-mono"
                      >
                        {n.type}
                      </span>
                    </motion.span>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {plan ? (
          <pre className="text-[13px] text-[#a1a1aa] leading-relaxed whitespace-pre-wrap font-mono max-h-[500px] overflow-y-auto">
            {plan}
          </pre>
        ) : (
          <p className="text-sm text-[#71717a]">
            暂无规划数据，运行管线后生成。
          </p>
        )}
      </motion.div>

      {/* Right column: emotion + annotations */}
      <div className="flex flex-col gap-5">
        {/* Emotion curve */}
        <motion.div
          className="card-surface p-6 flex flex-col gap-4"
          whileHover={{ borderColor: "rgba(212, 168, 83, 0.2)" }}
        >
          <div className="flex items-center gap-2.5">
            <ChartBar size={18} className="text-[#d4a853]" />
            <h3 className="text-sm font-semibold text-[#f4f4f5]">
              情绪曲线
            </h3>
          </div>
          {emotion && emotion.length > 0 ? (
            <div className="space-y-3 max-h-[260px] overflow-y-auto">
              {emotion.map((ep: any, i: number) => (
                <motion.div
                  key={ep.episode_id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.08 }}
                  className="p-3 rounded-lg bg-[#141416] border border-[#1f1f23]"
                >
                  <div className="flex justify-between text-[13px] mb-1.5">
                    <span className="text-[#f4f4f5] font-medium">
                      第{ep.episode_id}集
                    </span>
                    <span className="text-[#71717a] font-mono text-[11px]">
                      峰值{ep.peak_value}/谷值{ep.valley_value}
                    </span>
                  </div>
                  <div className="flex items-end gap-0.5 h-12 mb-1.5">
                    {(ep.emotion_sequence || []).map(
                      (v: number, j: number) => (
                        <motion.div
                          key={j}
                          className="flex-1 rounded-t-sm"
                          initial={{ height: 0 }}
                          animate={{
                            height: `${Math.max(4, (v / 10) * 100)}%`,
                          }}
                          transition={{
                            delay: i * 0.08 + j * 0.03,
                            duration: 0.35,
                            ease: "easeOut",
                          }}
                          style={{
                            backgroundColor:
                              v >= 7
                                ? "#22c55e"
                                : v >= 4
                                  ? "#d4a853"
                                  : "#ef4444",
                            opacity: 0.75,
                          }}
                        />
                      ),
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[#71717a]">暂无情绪曲线数据。</p>
          )}
        </motion.div>

        {/* Episode annotations */}
        <motion.div
          className="card-surface p-6 flex flex-col gap-4 flex-1"
          whileHover={{ borderColor: "rgba(212, 168, 83, 0.2)" }}
        >
          <div className="flex items-center gap-2.5">
            <FlagBanner size={18} className="text-[#d4a853]" />
            <h3 className="text-sm font-semibold text-[#f4f4f5]">
              剧集标注
            </h3>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] text-[#71717a]">集数:</span>
            {[1, 2, 3].map((ep) => (
              <motion.button
                key={ep}
                onClick={() => setSelectedEp(ep)}
                whileHover={{ scale: 1.06 }}
                whileTap={{ scale: 0.94 }}
                className={`px-2.5 py-1 text-[12px] font-mono rounded-md transition-all ${
                  selectedEp === ep
                    ? "bg-[#d4a853]/10 text-[#d4a853] border border-[#d4a853]/30"
                    : "text-[#a1a1aa] border border-[#27272a] hover:border-[#3f3f46]"
                }`}
              >
                第{ep.toString().padStart(2, "0")}集
              </motion.button>
            ))}
          </div>

          <AnimatePresence mode="wait">
            {annotations ? (
              <motion.div
                key={`annot-${selectedEp}`}
                className="space-y-3 max-h-[350px] overflow-y-auto"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <div className="p-3 rounded-lg bg-[#141416] border border-[#1f1f23]">
                  <div className="flex items-center gap-1.5 text-[11px] text-[#d4a853] font-medium mb-1">
                    <Target size={12} weight="fill" /> 开篇钩子
                  </div>
                  <p className="text-[12px] text-[#a1a1aa]">
                    {annotations.opening_hook}
                  </p>
                </div>

                <div className="p-3 rounded-lg bg-[#141416] border border-[#1f1f23]">
                  <div className="flex items-center gap-1.5 text-[11px] text-[#ef4444] font-medium mb-1">
                    <Lightning size={12} weight="fill" /> 中段冲突
                  </div>
                  <p className="text-[12px] text-[#a1a1aa]">
                    {annotations.mid_conflict}
                  </p>
                </div>

                <div className="p-3 rounded-lg bg-[#141416] border border-[#1f1f23]">
                  <div className="flex items-center gap-1.5 text-[11px] text-[#3b82f6] font-medium mb-1">
                    <Star size={12} weight="fill" /> 结尾悬念
                  </div>
                  <p className="text-[12px] text-[#a1a1aa]">
                    {annotations.cliffhanger}
                  </p>
                </div>

                {annotations.highlights &&
                  annotations.highlights.length > 0 && (
                    <div className="p-3 rounded-lg bg-[#141416] border border-[#1f1f23]">
                      <div className="text-[11px] text-[#22c55e] font-medium mb-1.5">
                        核心看点
                      </div>
                      <div className="space-y-1">
                        {annotations.highlights.map((h, i) => (
                          <div
                            key={i}
                            className="text-[12px] text-[#a1a1aa]"
                          >
                            {h}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                {annotations.foreshadowing &&
                  annotations.foreshadowing.length > 0 && (
                    <div className="p-3 rounded-lg bg-[#141416] border border-[#1f1f23]">
                      <div className="text-[11px] text-[#8b5cf6] font-medium mb-1.5">
                        剧情伏笔
                      </div>
                      <div className="space-y-1.5">
                        {annotations.foreshadowing.map((f, i) => (
                          <div
                            key={i}
                            className="text-[12px] text-[#a1a1aa] flex items-start gap-1.5"
                          >
                            <span className="text-[10px] text-[#8b5cf6] mt-0.5">
                              ◆
                            </span>
                            <span>{f.description}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                {annotations.investor_notes && (
                  <details className="p-3 rounded-lg bg-[#141416] border border-[#1f1f23]">
                    <summary className="text-[11px] text-[#71717a] font-medium cursor-pointer hover:text-[#a1a1aa]">
                      招商/审核参考
                    </summary>
                    <pre className="mt-2 text-[11px] text-[#71717a] whitespace-pre-wrap font-mono leading-relaxed max-h-[150px] overflow-y-auto">
                      {annotations.investor_notes}
                    </pre>
                  </details>
                )}
              </motion.div>
            ) : (
              <motion.p
                key="no-annot"
                className="text-sm text-[#71717a]"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
              >
                运行管线后查看剧集标注（看点/伏笔/招商备注）。
              </motion.p>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    </motion.div>
  );
}

/* ── Analysis Panel ── */
function AnalysisPanel({ projectName }: { projectName: string }) {
  const [report, setReport] = useState<string | null>(null);
  useEffect(() => {
    getReport(projectName, "analysis")
      .then((r) => setReport(r.content))
      .catch(() => setReport(null));
  }, [projectName]);

  return report ? (
    <motion.div
      className="card-surface p-6"
      variants={panelVariants}
      initial="initial"
      animate="animate"
    >
      <pre className="text-[13px] text-[#a1a1aa] leading-relaxed whitespace-pre-wrap font-mono">
        {report}
      </pre>
    </motion.div>
  ) : (
    <EmptyState
      icon={ChartBar}
      title="暂无分析报告"
      desc="运行管线后生成。"
    />
  );
}

/* ── Export Panel ── */
function ExportPanel({ projectName }: { projectName: string }) {
  const [files, setFiles] = useState<
    { name: string; path: string; size: number }[]
  >([]);

  useEffect(() => {
    listOutputFiles(projectName)
      .then((r) => setFiles(r.files))
      .catch(() => {});
  }, [projectName]);

  const downloadAll = async () => {
    for (let ep = 1; ep <= 3; ep++) {
      try {
        const d = await getScript(projectName, ep);
        if (d?.content)
          downloadFile(
            d.content,
            `ep${ep.toString().padStart(2, "0")}_script.yaml`,
          );
      } catch {}
    }
  };

  return (
    <motion.div
      className="space-y-4"
      variants={panelVariants}
      initial="initial"
      animate="animate"
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <motion.div
          className="lg:col-span-2 card-surface p-6 flex flex-col md:flex-row gap-6 items-start"
          whileHover={{ borderColor: "rgba(212, 168, 83, 0.2)" }}
        >
          <motion.div
            className="w-12 h-12 rounded-xl bg-[#d4a853]/10 border border-[#d4a853]/20 flex items-center justify-center shrink-0"
            whileHover={{ scale: 1.1, borderColor: "rgba(212, 168, 83, 0.4)" }}
          >
            <Download size={22} className="text-[#d4a853]" />
          </motion.div>
          <div className="flex-1">
            <h4 className="text-sm font-semibold text-[#f4f4f5]">
              全部剧本 (YAML)
            </h4>
            <p className="text-[13px] text-[#a1a1aa] mt-1">
              下载全部已生成集数的 YAML 剧本。
            </p>
            <p className="text-[11px] font-mono text-[#71717a] mt-2">
              {files.filter((f) => f.path.endsWith(".yaml")).length} 个 YAML
              文件
            </p>
          </div>
          <motion.button
            onClick={downloadAll}
            whileHover={{ scale: 1.05, boxShadow: "0 0 20px rgba(212,168,83,0.3)" }}
            whileTap={{ scale: 0.95 }}
            className="px-5 py-2 text-[13px] font-medium rounded-lg bg-[#d4a853] text-[#09090b] hover:bg-[#d4a853]/90 transition-all shrink-0"
          >
            下载全部
          </motion.button>
        </motion.div>

        <motion.div
          className="card-surface p-5 flex flex-col gap-3"
          whileHover={{ borderColor: "rgba(212, 168, 83, 0.2)" }}
        >
          <motion.div
            className="w-10 h-10 rounded-lg bg-[#d4a853]/10 border border-[#d4a853]/20 flex items-center justify-center"
            whileHover={{ scale: 1.1 }}
          >
            <FileText size={18} className="text-[#d4a853]" />
          </motion.div>
          <h4 className="text-sm font-semibold text-[#f4f4f5]">项目文件</h4>
          <div className="flex-1 max-h-[250px] overflow-y-auto mt-2 space-y-0.5">
            {files.length === 0 ? (
              <p className="text-[11px] text-[#71717a]">暂无文件</p>
            ) : (
              files.map((f) => (
                <div
                  key={f.path}
                  className="flex justify-between text-[11px] py-1 border-b border-[#1f1f23] last:border-0"
                >
                  <span className="text-[#a1a1aa] font-mono truncate max-w-[200px]">
                    {f.path}
                  </span>
                  <span className="text-[#71717a]">
                    {Math.round(f.size / 1024)} KB
                  </span>
                </div>
              ))
            )}
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}

/* ── Images Panel ── */
function ImagesPanel({ projectName }: { projectName: string }) {
  const [episode, setEpisode] = useState(1);
  const [data, setData] = useState<{
    images: { name: string; url: string; size: number }[];
    prompts: any[];
  } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(
      `${API_URL}/api/projects/${encodeURIComponent(projectName)}/images/${episode}`,
    )
      .then((r) => r.json())
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch(() => {
        setData(null);
        setLoading(false);
      });
  }, [episode, projectName]);

  return (
    <motion.div
      className="flex flex-col gap-5"
      variants={panelVariants}
      initial="initial"
      animate="animate"
    >
      <div className="flex items-center gap-3">
        <span className="text-sm text-[#71717a]">集数:</span>
        {[1, 2, 3].map((ep) => (
          <motion.button
            key={ep}
            onClick={() => setEpisode(ep)}
            whileHover={{ scale: 1.06 }}
            whileTap={{ scale: 0.94 }}
            className={`px-3 py-1.5 text-[13px] font-mono rounded-md transition-all ${
              episode === ep
                ? "bg-[#d4a853]/10 text-[#d4a853] border border-[#d4a853]/30"
                : "text-[#a1a1aa] border border-[#27272a] hover:border-[#3f3f46]"
            }`}
          >
            第{ep.toString().padStart(2, "0")}集
          </motion.button>
        ))}
        {data && (
          <motion.span
            className="ml-auto text-[11px] font-mono text-[#71717a]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            {data.images.length} 张图片
          </motion.span>
        )}
      </div>
      <AnimatePresence mode="wait">
        {loading ? (
          <motion.div
            key="loading"
            className="card-surface p-12 text-center text-sm text-[#71717a]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.span
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              加载中...
            </motion.span>
          </motion.div>
        ) : !data || data.images.length === 0 ? (
          <EmptyState
            icon={ImageIcon}
            title="暂无图片"
            desc="运行管线生成图片。需要配置图片 API key。"
          />
        ) : (
          <motion.div
            key={`img-${episode}`}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            {data.images.map((img: any, i: number) => (
              <motion.div
                key={img.name}
                className="card-surface overflow-hidden"
                initial={{ opacity: 0, scale: 0.92 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.08, duration: 0.4 }}
                whileHover={{
                  scale: 1.03,
                  borderColor: "rgba(212, 168, 83, 0.4)",
                  boxShadow: "0 8px 30px rgba(0,0,0,0.4)",
                }}
              >
                <img
                  src={`${API_URL}${img.url}`}
                  alt={img.name}
                  className="w-full h-48 object-cover"
                  loading="lazy"
                />
                <div className="p-2 flex justify-between text-[11px]">
                  <span className="text-[#a1a1aa] font-mono">{img.name}</span>
                  <span className="text-[#71717a]">
                    {Math.round(img.size / 1024)} KB
                  </span>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/* ── Main ── */
export default function PhasePanels({
  projectName,
}: {
  projectName: string;
}) {
  const [activeTab, setActiveTab] = useState("write");

  const render = () => {
    switch (activeTab) {
      case "ingest":
        return <IngestPanel projectName={projectName} />;
      case "analyze":
        return <AnalysisPanel projectName={projectName} />;
      case "plan":
        return <PlanPanel projectName={projectName} />;
      case "write":
        return <ScriptPanel projectName={projectName} />;
      case "review":
        return <ReviewPanel projectName={projectName} />;
      case "storyboard":
        return <StoryboardPanel projectName={projectName} />;
      case "images":
        return <ImagesPanel projectName={projectName} />;
      case "export":
        return <ExportPanel projectName={projectName} />;
      default:
        return null;
    }
  };

  return (
    <section id="dashboard" className="py-24 px-6">
      <div className="max-w-[1400px] mx-auto">
        <motion.div
          className="mb-10"
          initial={{ y: 30, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.7, ease: easeOutExpo }}
        >
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-[#f4f4f5]">
            阶段详情
          </h2>
          <p className="mt-3 text-sm text-[#a1a1aa] max-w-[65ch]">
            深入每个管线阶段。编辑剧本、查看审核、管理分镜。
          </p>
        </motion.div>

        {/* Tab bar */}
        <div className="flex items-center gap-0.5 mb-8 overflow-x-auto pb-2 border-b border-[#27272a]">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <motion.button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                whileHover={{ scale: 1.05, color: isActive ? "#d4a853" : "#a1a1aa" }}
                whileTap={{ scale: 0.95 }}
                className={`relative flex items-center gap-2 px-4 py-2.5 text-[13px] font-medium whitespace-nowrap rounded-t-lg transition-colors ${
                  isActive
                    ? "text-[#d4a853]"
                    : "text-[#71717a] hover:text-[#a1a1aa]"
                }`}
              >
                <tab.icon
                  size={15}
                  weight={isActive ? "fill" : "regular"}
                />
                {tab.label}
                {isActive && (
                  <motion.span
                    layoutId="tab-underline"
                    className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#d4a853] rounded-full"
                    transition={{ type: "spring", stiffness: 500, damping: 35 }}
                  />
                )}
              </motion.button>
            );
          })}
        </div>

        {/* Panel content with AnimatePresence */}
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            variants={panelVariants}
            initial="initial"
            animate="animate"
            exit="exit"
          >
            {render()}
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}
