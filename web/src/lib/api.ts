/**
 * Novel-to-Script Pro - Frontend API Client
 * Typed fetch wrappers for the FastAPI backend.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${res.status}: ${err}`);
  }
  return res.json();
}

// ── Types ──

export interface Project {
  name: string;
  status: string;
  phases_completed: string[];
}

export interface ProjectStatus {
  project_name: string;
  current_phase: string;
  current_episode: number | null;
  progress: string;
  phases_completed: string[];
  episodes_written: number;
  episodes_reviewed: number;
  episodes_storyboarded: number;
  total_agent_calls: number;
  success_rate: string;
  failed_calls: number;
  total_agent_duration_seconds: number;
  error_count: number;
  continuity_hooks_open: number;
  last_updated: string;
}

export interface PhaseDetail {
  phase: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  episodes_completed?: number[];
  episodes_in_progress?: Record<string, unknown>;
}

export interface TaskStatus {
  status: "running" | "completed" | "failed";
  result?: Record<string, unknown>;
  error?: string;
}

export interface ScriptData {
  episode: number;
  content: string;
  path: string;
}

export interface ReportData {
  type: string;
  content: string;
  path: string;
}

export interface OutputFile {
  name: string;
  path: string;
  size: number;
}

// ── Projects ──

export function listProjects() {
  return fetchJSON<{ projects: Project[] }>("/api/projects");
}

export function createProject(name: string) {
  return fetchJSON<{ name: string; status: string }>("/api/projects", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function getProjectStatus(name: string) {
  return fetchJSON<ProjectStatus>(`/api/projects/${encodeURIComponent(name)}/status`);
}

export function getPhaseDetail(name: string, phase: string) {
  return fetchJSON<PhaseDetail>(
    `/api/projects/${encodeURIComponent(name)}/phase/${phase}`
  );
}

// ── Pipeline phases (return task_id for polling) ──

export function runIngest(name: string, sourceDir: string) {
  return fetchJSON<{ task_id: string; status: string }>(
    `/api/projects/${encodeURIComponent(name)}/ingest`,
    { method: "POST", body: JSON.stringify({ source_dir: sourceDir }) }
  );
}

export function runAnalyze(name: string, title: string, author?: string) {
  return fetchJSON<{ task_id: string; status: string }>(
    `/api/projects/${encodeURIComponent(name)}/analyze`,
    { method: "POST", body: JSON.stringify({ title, author: author || "" }) }
  );
}

export function runPlan(name: string, episodes: number) {
  return fetchJSON<{ task_id: string; status: string }>(
    `/api/projects/${encodeURIComponent(name)}/plan`,
    { method: "POST", body: JSON.stringify({ episodes }) }
  );
}

export function runWrite(name: string, episode: number) {
  return fetchJSON<{ task_id: string; status: string }>(
    `/api/projects/${encodeURIComponent(name)}/write/${episode}`,
    { method: "POST" }
  );
}

export function runReview(name: string, episode: number) {
  return fetchJSON<{ task_id: string; status: string }>(
    `/api/projects/${encodeURIComponent(name)}/review/${episode}`,
    { method: "POST" }
  );
}

export function runStoryboard(name: string, episode: number, mode: string = "film") {
  return fetchJSON<{ task_id: string; status: string }>(
    `/api/projects/${encodeURIComponent(name)}/storyboard/${episode}`,
    { method: "POST", body: JSON.stringify({ mode }) }
  );
}

export function runFinalCheck(name: string) {
  return fetchJSON<{ task_id: string; status: string }>(
    `/api/projects/${encodeURIComponent(name)}/final-check`,
    { method: "POST" }
  );
}

export function runAuto(
  name: string,
  opts: { source_dir?: string; title?: string; author?: string; episodes?: number }
) {
  return fetchJSON<{ task_id: string; status: string }>(
    `/api/projects/${encodeURIComponent(name)}/auto`,
    { method: "POST", body: JSON.stringify(opts) }
  );
}

// ── Task polling ──

export function getTaskStatus(taskId: string) {
  return fetchJSON<TaskStatus>(`/api/tasks/${encodeURIComponent(taskId)}`);
}

// ── Output files ──

export function getScript(name: string, episode: number) {
  return fetchJSON<ScriptData>(
    `/api/projects/${encodeURIComponent(name)}/scripts/${episode}`
  );
}

export function getReport(name: string, type: string) {
  return fetchJSON<ReportData>(
    `/api/projects/${encodeURIComponent(name)}/reports/${type}`
  );
}

export function listOutputFiles(name: string) {
  return fetchJSON<{ files: OutputFile[] }>(
    `/api/projects/${encodeURIComponent(name)}/files`
  );
}
