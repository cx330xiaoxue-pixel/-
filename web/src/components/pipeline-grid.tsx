"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Play,
  Pause,
  CheckCircle,
  Circle,
  ArrowClockwise,
} from "@phosphor-icons/react";
import {
  getProjectStatus,
  runAuto,
  getTaskStatus,
  listProjects,
  type ProjectStatus,
} from "@/lib/api";

type PhaseStatus = "done" | "active" | "idle";

interface PhaseData {
  id: string;
  label: string;
  description: string;
  status: PhaseStatus;
  episode?: number;
  stats?: { label: string; value: string }[];
}

const PHASE_META: Omit<PhaseData, "status" | "stats">[] = [
  { id: "ingest", label: "Ingest", description: "Scan source materials, extract terminology and world-building rules" },
  { id: "analyze", label: "Analyze", description: "Analyze narrative structure, character networks, theme insights" },
  { id: "plan", label: "Plan", description: "Chapter-to-episode mapping, emotion curve design" },
  { id: "write", label: "Write", description: "Generate complete scripts per episode with hit-reference retrieval" },
  { id: "review", label: "Review", description: "Multi-dimension review: business logic, compliance, comparison" },
  { id: "storyboard", label: "Storyboard", description: "Cinematic shot planning, dual-track: Film and Seedance AI" },
];

function derivePhases(status: ProjectStatus | null): PhaseData[] {
  if (!status) {
    return PHASE_META.map((p, i) => ({ ...p, status: "idle" as PhaseStatus, index: i }));
  }

  const done = new Set(status.phases_completed || []);
  const current = status.current_phase;

  return PHASE_META.map((p, i) => {
    let phaseStatus: PhaseStatus = "idle";
    if (done.has(p.id)) phaseStatus = "done";
    else if (p.id === current) phaseStatus = "active";

    const stats: { label: string; value: string }[] = [];
    if (p.id === "write") {
      stats.push({ label: "Written", value: `${status.episodes_written || 0}` });
      stats.push({ label: "Agent Calls", value: `${status.total_agent_calls || 0}` });
    }
    if (p.id === "review") {
      stats.push({ label: "Reviewed", value: `${status.episodes_reviewed || 0}` });
    }
    if (p.id === "storyboard") {
      stats.push({ label: "Storyboarded", value: `${status.episodes_storyboarded || 0}` });
    }

    return {
      ...p,
      status: phaseStatus,
      episode: current === p.id ? (status.current_episode ?? undefined) : undefined,
      stats: stats.length > 0 ? stats : undefined,
    };
  });
}

function PhaseCard({ phase }: { phase: PhaseData }) {
  return (
    <div className="card-surface p-5 flex flex-col gap-3 opacity-0 animate-[fadeIn_0.5s_ease-out_forwards]">
      <div className="flex items-center gap-2.5">
        {phase.status === "done" && (
          <CheckCircle size={18} weight="fill" className="text-[#22c55e]" />
        )}
        {phase.status === "active" && <div className="phase-dot phase-dot-active" />}
        {phase.status === "idle" && (
          <Circle size={18} weight="bold" className="text-[#3f3f46]" />
        )}
        <span className="text-sm font-semibold text-[#f4f4f5]">{phase.label}</span>
        {phase.status === "active" && (
          <span className="ml-auto text-[11px] font-mono px-2 py-0.5 rounded-full bg-[#d4a853]/10 text-[#d4a853] border border-[#d4a853]/20">
            RUNNING
          </span>
        )}
        {phase.status === "done" && (
          <span className="ml-auto text-[11px] font-mono text-[#22c55e]">DONE</span>
        )}
        {phase.status === "idle" && (
          <span className="ml-auto text-[11px] font-mono text-[#71717a]">PENDING</span>
        )}
      </div>
      <p className="text-[13px] text-[#a1a1aa] leading-relaxed">{phase.description}</p>
      {phase.episode && (
        <div className="flex items-center gap-2 text-[13px]">
          <span className="text-[#71717a]">Current:</span>
          <span className="font-mono text-[#d4a853]">Episode {phase.episode}</span>
        </div>
      )}
      {phase.stats && (
        <div className="flex gap-4 mt-1">
          {phase.stats.map((s) => (
            <div key={s.label} className="flex items-baseline gap-1.5">
              <span className="text-lg font-mono font-semibold text-[#f4f4f5]">{s.value}</span>
              <span className="text-[11px] text-[#71717a]">{s.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function PipelineGrid() {
  const [projectName, setProjectName] = useState("青云之路");
  const [status, setStatus] = useState<ProjectStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [projects, setProjects] = useState<string[]>([]);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await getProjectStatus(projectName);
      setStatus(data);
    } catch {
      // Project doesn't exist yet
      setStatus(null);
    }
  }, [projectName]);

  // Load project list and status
  useEffect(() => {
    listProjects().then((res) => {
      setProjects(res.projects.map((p) => p.name));
    }).catch(() => {});
    fetchStatus();
  }, [fetchStatus]);

  // Poll task status
  useEffect(() => {
    if (!taskId) return;
    const interval = setInterval(async () => {
      try {
        const task = await getTaskStatus(taskId);
        if (task.status === "completed" || task.status === "failed") {
          setTaskId(null);
          setLoading(false);
          if (task.status === "failed") setError(task.error || "Task failed");
          fetchStatus(); // Refresh after task completes
        }
      } catch {
        setTaskId(null);
        setLoading(false);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [taskId, fetchStatus]);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await runAuto(projectName, {
        title: projectName,
        episodes: 3,
        source_dir: "./sample_novel",
      });
      if (res.task_id) setTaskId(res.task_id);
    } catch (e) {
      setError(String(e));
      setLoading(false);
    }
  };

  const handleStop = () => {
    setTaskId(null);
    setLoading(false);
  };

  const phases = derivePhases(status);

  return (
    <section id="pipeline" className="py-24 px-6">
      <div className="max-w-[1400px] mx-auto">
        <div className="mb-12">
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-[#f4f4f5]">
            Pipeline Status
          </h2>
          <p className="mt-3 text-[#a1a1aa] text-sm max-w-[65ch]">
            Six-phase pipeline from source ingestion to cinematic storyboard.
            Each phase delegates to a specialized AI agent.
          </p>

          {/* Project selector + controls */}
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <select
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              className="px-3 py-2 text-[13px] rounded-lg bg-[#141416] border border-[#27272a] text-[#f4f4f5] focus:border-[#d4a853] focus:outline-none"
            >
              {projects.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
              {projects.length === 0 && (
                <option value={projectName}>{projectName}</option>
              )}
            </select>

            <button
              onClick={loading ? handleStop : handleRun}
              disabled={!projectName}
              className={`inline-flex items-center gap-2 px-4 py-2 text-[13px] font-medium rounded-lg transition-all duration-200 active:scale-[0.98] ${
                loading
                  ? "bg-[#ef4444]/10 text-[#ef4444] border border-[#ef4444]/30"
                  : "bg-[#d4a853] text-[#09090b] hover:bg-[#d4a853]/90"
              }`}
            >
              {loading ? (
                <><Pause size={16} weight="bold" /> Stop</>
              ) : (
                <><Play size={16} weight="bold" /> Run Pipeline</>
              )}
            </button>

            <button
              onClick={fetchStatus}
              className="inline-flex items-center gap-2 px-4 py-2 text-[13px] font-medium rounded-lg border border-[#27272a] text-[#a1a1aa] hover:text-[#f4f4f5] hover:border-[#3f3f46] transition-all duration-200 active:scale-[0.98]"
            >
              <ArrowClockwise size={16} weight="bold" /> Refresh
            </button>

            {status && (
              <span className="text-[11px] font-mono text-[#71717a]">
                Phase: {status.current_phase} | Agents: {status.total_agent_calls} calls | {status.success_rate}
              </span>
            )}
          </div>

          {error && (
            <div className="mt-3 p-3 rounded-lg bg-[#ef4444]/10 border border-[#ef4444]/30 text-[13px] text-[#ef4444]">
              {error}
            </div>
          )}
        </div>

        {/* Bento grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="md:col-span-2 lg:col-span-3">
            <PhaseCard phase={phases[0]} />
          </div>
          <PhaseCard phase={phases[1]} />
          <div className="lg:col-span-2">
            <PhaseCard phase={phases[2]} />
          </div>
          <div className="md:col-span-2 lg:col-span-2">
            <PhaseCard phase={phases[3]} />
          </div>
          <PhaseCard phase={phases[4]} />
          <div className="md:col-span-2 lg:col-span-3">
            <PhaseCard phase={phases[5]} />
          </div>
        </div>
      </div>
    </section>
  );
}
