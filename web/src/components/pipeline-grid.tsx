"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Play,
  Pause,
  CheckCircle,
  Circle,
  ArrowClockwise,
  Spinner,
} from "@phosphor-icons/react";
import { motion, AnimatePresence } from "framer-motion";
import { easeOutExpo } from "@/lib/motion";
import {
  getProjectStatus,
  runAuto,
  getTaskStatus,
  listProjects,
  type ProjectStatus,
} from "@/lib/api";

type PhaseStatus = "done" | "active" | "idle" | "running";

interface PhaseData {
  id: string;
  label: string;
  description: string;
  status: PhaseStatus;
  episode?: number;
  stats?: { label: string; value: string }[];
}

const PHASE_META: Omit<PhaseData, "status" | "stats">[] = [
  { id: "ingest", label: "导入", description: "扫描源材料，提取术语和世界观规则" },
  { id: "analyze", label: "分析", description: "LLM分析叙事结构、角色网络和主题洞察" },
  { id: "plan", label: "规划", description: "章节到集数的映射，情绪曲线设计" },
  { id: "write", label: "编写", description: "LLM逐集生成完整剧本，滑窗并行抽取" },
  { id: "review", label: "审核", description: "LLM多维度审核：业务逻辑、合规、AI评审" },
  { id: "storyboard", label: "分镜", description: "从剧本解析场景 → 镜头 → 节拍，生成序列板" },
];

function derivePhases(status: ProjectStatus | null, running: boolean): PhaseData[] {
  if (!status) {
    return PHASE_META.map((p) => ({ ...p, status: "idle" as PhaseStatus }));
  }

  const done = new Set(status.phases_completed || []);
  const current = status.current_phase;

  return PHASE_META.map((p) => {
    let phaseStatus: PhaseStatus = "idle";
    if (done.has(p.id)) phaseStatus = "done";
    else if (p.id === current && running) phaseStatus = "running";

    const stats: { label: string; value: string }[] = [];
    if (p.id === "write") {
      stats.push({ label: "已编写", value: `${status.episodes_written || 0}` });
    }
    if (p.id === "review") {
      stats.push({ label: "已审核", value: `${status.episodes_reviewed || 0}` });
    }
    if (p.id === "storyboard") {
      stats.push({ label: "已分镜", value: `${status.episodes_storyboarded || 0}` });
    }

    return {
      ...p,
      status: phaseStatus,
      episode: current === p.id ? (status.current_episode ?? undefined) : undefined,
      stats: stats.length > 0 ? stats : undefined,
    };
  });
}

/* ── Status Icon ── */
function StatusIcon({ status }: { status: PhaseStatus }) {
  switch (status) {
    case "done":
      return (
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
        >
          <CheckCircle size={18} weight="fill" className="text-[#22c55e]" />
        </motion.span>
      );
    case "running":
      return (
        <motion.span
          animate={{ rotate: 360 }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
        >
          <Spinner size={18} weight="bold" className="text-[#d4a853]" />
        </motion.span>
      );
    case "idle":
    default:
      return <Circle size={18} weight="bold" className="text-[#3f3f46]" />;
  }
}

function PhaseCard({ phase, index }: { phase: PhaseData; index: number }) {
  const isRunning = phase.status === "running";

  return (
    <motion.div
      initial={{ y: 40, opacity: 0, scale: 0.96 }}
      whileInView={{ y: 0, opacity: 1, scale: 1 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{
        delay: index * 0.08,
        duration: 0.6,
        ease: easeOutExpo,
      }}
      whileHover={{
        scale: 1.02,
        borderColor: "rgba(212, 168, 83, 0.35)",
        boxShadow: "0 4px 30px rgba(212, 168, 83, 0.06)",
      }}
      className={`card-surface p-5 flex flex-col gap-3 transition-colors duration-300 ${
        isRunning ? "border-[#d4a853]/40 shadow-[0_0_20px_rgba(212,168,83,0.08)]" : ""
      }`}
    >
      <div className="flex items-center gap-2.5">
        <StatusIcon status={phase.status} />
        <span className="text-sm font-semibold text-[#f4f4f5]">{phase.label}</span>
        {isRunning && (
          <motion.span
            className="ml-auto text-[11px] font-mono px-2 py-0.5 rounded-full bg-[#d4a853]/10 text-[#d4a853] border border-[#d4a853]/20"
            animate={{ opacity: [1, 0.6, 1] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
          >
            执行中...
          </motion.span>
        )}
        {phase.status === "done" && (
          <span className="ml-auto text-[11px] font-mono text-[#22c55e]">已完成</span>
        )}
        {phase.status === "idle" && (
          <span className="ml-auto text-[11px] font-mono text-[#71717a]">等待中</span>
        )}
      </div>

      <p className="text-[13px] text-[#a1a1aa] leading-relaxed">{phase.description}</p>

      {phase.episode && (
        <motion.div
          className="flex items-center gap-2 text-[13px]"
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <span className="text-[#71717a]">当前:</span>
          <motion.span
            className="font-mono text-[#d4a853]"
            animate={{ opacity: [1, 0.5, 1] }}
            transition={{ duration: 1, repeat: Infinity }}
          >
            第{phase.episode}集
          </motion.span>
        </motion.div>
      )}

      {phase.stats && (
        <motion.div
          className="flex gap-4 mt-1"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          {phase.stats.map((s) => (
            <div key={s.label} className="flex items-baseline gap-1.5">
              <span className="text-lg font-mono font-semibold text-[#f4f4f5]">{s.value}</span>
              <span className="text-[11px] text-[#71717a]">{s.label}</span>
            </div>
          ))}
        </motion.div>
      )}
    </motion.div>
  );
}

export default function PipelineGrid({
  projectName,
  onProjectChange,
}: {
  projectName: string;
  onProjectChange: (name: string) => void;
}) {
  const [status, setStatus] = useState<ProjectStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [projects, setProjects] = useState<string[]>([]);
  const [progressText, setProgressText] = useState("");
  const [adaptationMode, setAdaptationMode] = useState("balanced");
  const [targetFormat, setTargetFormat] = useState("long_drama");

  const fetchStatus = useCallback(async () => {
    try {
      const data = await getProjectStatus(projectName);
      setStatus(data);
    } catch {
      setStatus(null);
    }
  }, [projectName]);

  useEffect(() => {
    listProjects()
      .then((res) => {
        setProjects(res.projects.map((p) => p.name));
      })
      .catch(() => {});
    fetchStatus();
  }, [fetchStatus]);

  useEffect(() => {
    if (!taskId) return;
    let count = 0;
    setProgressText("管线启动中...");
    const interval = setInterval(async () => {
      count++;
      try {
        const task = await getTaskStatus(taskId);
        if (task.status === "completed") {
          setTaskId(null);
          setLoading(false);
          setProgressText("✅ 管线完成！");
          fetchStatus();
          setTimeout(() => setProgressText(""), 3000);
        } else if (task.status === "failed") {
          setTaskId(null);
          setLoading(false);
          setProgressText("");
          setError(task.error || "任务执行失败");
        } else {
          const mins = Math.floor((count * 2) / 60);
          const secs = (count * 2) % 60;
          setProgressText(
            `⏳ 运行中... ${mins}分${secs.toString().padStart(2, "0")}秒`,
          );
        }
      } catch {
        setTaskId(null);
        setLoading(false);
        setProgressText("");
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [taskId, fetchStatus]);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    setProgressText("正在启动管线...");
    try {
      const res = await runAuto(projectName, {
        title: projectName,
        episodes: 3,
        source_dir: `./uploads/${projectName}`,
        adaptation_mode: adaptationMode,
        target_format: targetFormat,
      });
      if (res.task_id) {
        setTaskId(res.task_id);
      } else {
        setLoading(false);
        setError("未能获取任务ID");
      }
    } catch (e) {
      setError(String(e));
      setLoading(false);
      setProgressText("");
    }
  };

  const handleStop = () => {
    setTaskId(null);
    setLoading(false);
    setProgressText("");
  };

  const phases = derivePhases(status, loading);

  return (
    <section id="pipeline" className="py-24 px-6">
      <div className="max-w-[1400px] mx-auto">
        {/* Section header */}
        <motion.div
          className="mb-12"
          initial={{ y: 30, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.7, ease: easeOutExpo }}
        >
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-[#f4f4f5]">
            管线状态
          </h2>
          <p className="mt-3 text-[#a1a1aa] text-sm max-w-[65ch]">
            六阶段管线，全部由 LLM Agent 驱动。每个阶段调用 DeepSeek API 进行真实分析。
          </p>

          {/* Project selector + controls */}
          <motion.div
            className="mt-6 flex flex-wrap items-center gap-3"
            initial={{ y: 12, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2, duration: 0.5 }}
          >
            <select
              value={projectName}
              onChange={(e) => onProjectChange(e.target.value)}
              className="px-3 py-2 text-[13px] rounded-lg bg-[#141416] border border-[#27272a] text-[#f4f4f5] focus:border-[#d4a853] focus:outline-none transition-colors"
            >
              {projects.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
              {projects.length === 0 && (
                <option value={projectName}>{projectName}</option>
              )}
            </select>

            {/* Adaptation mode selector */}
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] text-[#71717a]">模式:</span>
              <select
                value={adaptationMode}
                onChange={(e) => setAdaptationMode(e.target.value)}
                className="px-2.5 py-2 text-[12px] rounded-lg bg-[#141416] border border-[#27272a] text-[#a1a1aa] focus:border-[#d4a853] focus:outline-none transition-colors"
              >
                <option value="strict">忠于原著</option>
                <option value="balanced">均衡改编</option>
                <option value="loose">影视节奏</option>
              </select>
            </div>

            {/* Target format selector */}
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] text-[#71717a]">格式:</span>
              <select
                value={targetFormat}
                onChange={(e) => setTargetFormat(e.target.value)}
                className="px-2.5 py-2 text-[12px] rounded-lg bg-[#141416] border border-[#27272a] text-[#a1a1aa] focus:border-[#d4a853] focus:outline-none transition-colors"
              >
                <option value="long_drama">长剧 (45min)</option>
                <option value="short_drama">短剧 (3-5min)</option>
              </select>
            </div>

            {/* Run / Stop button */}
            <motion.button
              onClick={loading ? handleStop : handleRun}
              disabled={!projectName}
              whileHover={!loading ? { scale: 1.05, boxShadow: "0 0 24px rgba(212, 168, 83, 0.35)" } : {}}
              whileTap={{ scale: 0.95 }}
              className={`inline-flex items-center gap-2 px-4 py-2 text-[13px] font-medium rounded-lg transition-all duration-200 ${
                loading
                  ? "bg-[#ef4444]/10 text-[#ef4444] border border-[#ef4444]/30 hover:bg-[#ef4444]/20"
                  : "bg-[#d4a853] text-[#09090b] hover:bg-[#d4a853]/90"
              }`}
            >
              {loading ? (
                <>
                  <motion.span
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  >
                    <Spinner size={16} weight="bold" />
                  </motion.span>{" "}
                  停止
                </>
              ) : (
                <>
                  <Play size={16} weight="bold" /> 运行管线
                </>
              )}
            </motion.button>

            {/* Refresh button */}
            <motion.button
              onClick={fetchStatus}
              whileHover={{ scale: 1.05, borderColor: "#3f3f46", color: "#f4f4f5" }}
              whileTap={{ scale: 0.95 }}
              className="inline-flex items-center gap-2 px-4 py-2 text-[13px] font-medium rounded-lg border border-[#27272a] text-[#a1a1aa] transition-all duration-200"
            >
              <ArrowClockwise size={16} weight="bold" /> 刷新
            </motion.button>

            {status && (
              <motion.span
                className="text-[11px] font-mono text-[#71717a]"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
              >
                阶段: {status.current_phase} | 成功率: {status.success_rate}
              </motion.span>
            )}
          </motion.div>

          {/* Progress indicator */}
          <AnimatePresence mode="wait">
            {progressText && (
              <motion.div
                key={progressText}
                initial={{ height: 0, opacity: 0, y: -8 }}
                animate={{ height: "auto", opacity: 1, y: 0 }}
                exit={{ height: 0, opacity: 0, y: -8 }}
                transition={{ duration: 0.3 }}
                className={`mt-3 p-3 rounded-lg text-[13px] flex items-center gap-2 overflow-hidden ${
                  progressText.startsWith("✅")
                    ? "bg-[#22c55e]/10 border border-[#22c55e]/30 text-[#22c55e]"
                    : progressText.startsWith("⏳")
                      ? "bg-[#d4a853]/10 border border-[#d4a853]/30 text-[#d4a853]"
                      : "bg-[#3b82f6]/10 border border-[#3b82f6]/30 text-[#3b82f6]"
                }`}
              >
                {progressText.startsWith("⏳") && (
                  <motion.span
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  >
                    <Spinner size={14} />
                  </motion.span>
                )}
                {progressText}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Error banner */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="mt-3 p-3 rounded-lg bg-[#ef4444]/10 border border-[#ef4444]/30 text-[13px] text-[#ef4444] overflow-hidden"
              >
                ❌ {error}
                <button onClick={() => setError(null)} className="ml-4 underline">
                  关闭
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Bento grid — dense, gap-less */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 grid-flow-dense">
          {/* Row 1: ingest — full width */}
          <div className="md:col-span-2 lg:col-span-3">
            <PhaseCard phase={phases[0]} index={0} />
          </div>
          {/* Row 2: analyze (1col) + plan (2col) */}
          <PhaseCard phase={phases[1]} index={1} />
          <div className="lg:col-span-2">
            <PhaseCard phase={phases[2]} index={2} />
          </div>
          {/* Row 3: write (2col) + review (1col) */}
          <div className="md:col-span-2 lg:col-span-2">
            <PhaseCard phase={phases[3]} index={3} />
          </div>
          <PhaseCard phase={phases[4]} index={4} />
          {/* Row 4: storyboard — full width */}
          <div className="md:col-span-2 lg:col-span-3">
            <PhaseCard phase={phases[5]} index={5} />
          </div>
        </div>
      </div>
    </section>
  );
}
