"""
Novel-to-Script Pro - FastAPI Server
====================================
REST API wrapping the 6-phase Pipeline engine.
Serves the Next.js frontend at web/.
"""

import os
import sys
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional

import yaml
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.pipeline import Pipeline, create_pipeline

# ── App ──
app = FastAPI(
    title="Novel-to-Script Pro API",
    version="2.0",
    description="REST API for the 6-phase novel-to-script adaptation pipeline",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config ──
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
config = {}
if CONFIG_PATH.exists():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

OUTPUT_DIR = config.get("output", {}).get("output_dir", "./output")

# ── Pipeline cache (one per project) ──
_pipelines: dict[str, Pipeline] = {}
_lock = threading.Lock()

# ── Background task store ──
_tasks: dict[str, dict] = {}
_task_counter = 0


def _get_pipeline(project_name: str) -> Pipeline:
    """Get or create a pipeline for a project."""
    with _lock:
        if project_name not in _pipelines:
            _pipelines[project_name] = create_pipeline(
                project_name=project_name,
                output_dir=OUTPUT_DIR,
                config_path=str(CONFIG_PATH),
            )
        return _pipelines[project_name]


def _run_phase_task(task_id: str, project_name: str, phase: str, **kwargs):
    """Background: run a pipeline phase and store result."""
    try:
        pipeline = _get_pipeline(project_name)
        result = pipeline._run_phase(phase, **kwargs)
        _tasks[task_id] = {"status": "completed", "result": result}
    except Exception as e:
        _tasks[task_id] = {"status": "failed", "error": str(e)}


def _run_auto_task(task_id: str, project_name: str, **kwargs):
    """Background: run full auto pipeline."""
    try:
        pipeline = _get_pipeline(project_name)
        result = pipeline.auto(**kwargs)
        _tasks[task_id] = {"status": "completed", "result": result}
    except Exception as e:
        _tasks[task_id] = {"status": "failed", "error": str(e)}


# ── Pydantic models ──
class ProjectCreate(BaseModel):
    name: str

class IngestRequest(BaseModel):
    source_dir: str

class AnalyzeRequest(BaseModel):
    title: str = ""
    author: str = ""

class PlanRequest(BaseModel):
    episodes: int = 3

class StoryboardRequest(BaseModel):
    mode: str = "film"

class AutoRequest(BaseModel):
    source_dir: str = ""
    title: str = ""
    author: str = ""
    episodes: int = 3


# ═══════════════════════════════════════════════════
# Projects
# ═══════════════════════════════════════════════════

@app.get("/api/projects")
def list_projects():
    """List existing projects from output directory."""
    output = Path(OUTPUT_DIR)
    if not output.exists():
        return {"projects": []}
    projects = []
    for d in sorted(output.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            state_file = d / ".agent-state.json"
            status = "idle"
            phases_done = []
            if state_file.exists():
                try:
                    with open(state_file, "r", encoding="utf-8") as f:
                        state = json.load(f)
                    status = state.get("current_phase", "idle")
                    phases_done = state.get("phases_completed", [])
                except Exception:
                    pass
            projects.append({
                "name": d.name,
                "status": status,
                "phases_completed": phases_done,
            })
    return {"projects": projects}


@app.post("/api/projects")
def create_project(body: ProjectCreate):
    """Initialize a new project."""
    pipeline = _get_pipeline(body.name)
    return {
        "name": body.name,
        "status": "created",
        "output_dir": str(PROJECT_ROOT / OUTPUT_DIR / body.name),
    }


@app.get("/api/projects/{project_name}/status")
def get_project_status(project_name: str):
    """Get full progress report for a project."""
    pipeline = _get_pipeline(project_name)
    return pipeline.get_status()


@app.get("/api/projects/{project_name}/phase/{phase}")
def get_phase_detail(project_name: str, phase: str):
    """Get detail for a specific pipeline phase."""
    pipeline = _get_pipeline(project_name)
    detail = pipeline.get_phase_detail(phase)
    return {"phase": phase, **detail}


# ═══════════════════════════════════════════════════
# Pipeline phases
# ═══════════════════════════════════════════════════

@app.post("/api/projects/{project_name}/ingest")
def run_ingest(project_name: str, body: IngestRequest, bg: BackgroundTasks):
    """Phase 0: Scan source materials."""
    task_id = f"{project_name}-ingest-{datetime.now().timestamp()}"
    _tasks[task_id] = {"status": "running"}
    bg.add_task(_run_phase_task, task_id, project_name, "ingest", source_dir=body.source_dir)
    return {"task_id": task_id, "status": "started"}


@app.post("/api/projects/{project_name}/analyze")
def run_analyze(project_name: str, body: AnalyzeRequest, bg: BackgroundTasks):
    """Phase 1: Adaptation analysis."""
    task_id = f"{project_name}-analyze-{datetime.now().timestamp()}"
    _tasks[task_id] = {"status": "running"}
    bg.add_task(_run_phase_task, task_id, project_name, "analyze", title=body.title, author=body.author)
    return {"task_id": task_id, "status": "started"}


@app.post("/api/projects/{project_name}/plan")
def run_plan(project_name: str, body: PlanRequest, bg: BackgroundTasks):
    """Phase 2: Episode planning."""
    task_id = f"{project_name}-plan-{datetime.now().timestamp()}"
    _tasks[task_id] = {"status": "running"}
    bg.add_task(_run_phase_task, task_id, project_name, "plan", episodes=body.episodes)
    return {"task_id": task_id, "status": "started"}


@app.post("/api/projects/{project_name}/write/{episode}")
def run_write(project_name: str, episode: int, bg: BackgroundTasks):
    """Phase 3: Write episode script."""
    task_id = f"{project_name}-write-{episode}-{datetime.now().timestamp()}"
    _tasks[task_id] = {"status": "running"}
    bg.add_task(_run_phase_task, task_id, project_name, "write", episode=episode)
    return {"task_id": task_id, "status": "started"}


@app.post("/api/projects/{project_name}/review/{episode}")
def run_review(project_name: str, episode: int, bg: BackgroundTasks):
    """Phase 4: Review episode."""
    task_id = f"{project_name}-review-{episode}-{datetime.now().timestamp()}"
    _tasks[task_id] = {"status": "running"}
    bg.add_task(_run_phase_task, task_id, project_name, "review", episode=episode)
    return {"task_id": task_id, "status": "started"}


@app.post("/api/projects/{project_name}/storyboard/{episode}")
def run_storyboard(project_name: str, episode: int, body: StoryboardRequest, bg: BackgroundTasks):
    """Phase 5: Storyboard episode."""
    task_id = f"{project_name}-storyboard-{episode}-{datetime.now().timestamp()}"
    _tasks[task_id] = {"status": "running"}
    bg.add_task(_run_phase_task, task_id, project_name, "storyboard", episode=episode, mode=body.mode)
    return {"task_id": task_id, "status": "started"}


@app.post("/api/projects/{project_name}/final-check")
def run_final_check(project_name: str, bg: BackgroundTasks):
    """Phase 6: Final validation."""
    task_id = f"{project_name}-final-check-{datetime.now().timestamp()}"
    _tasks[task_id] = {"status": "running"}
    bg.add_task(_run_phase_task, task_id, project_name, "final_check")
    return {"task_id": task_id, "status": "started"}


@app.post("/api/projects/{project_name}/auto")
def run_auto(project_name: str, body: AutoRequest, bg: BackgroundTasks):
    """Run full pipeline automatically."""
    task_id = f"{project_name}-auto-{datetime.now().timestamp()}"
    _tasks[task_id] = {"status": "running"}
    bg.add_task(
        _run_auto_task,
        task_id,
        project_name,
        source_dir=body.source_dir or None,
        title=body.title,
        author=body.author,
        episodes=body.episodes,
    )
    return {"task_id": task_id, "status": "started"}


# ═══════════════════════════════════════════════════
# Task polling
# ═══════════════════════════════════════════════════

@app.get("/api/tasks/{task_id}")
def get_task_status(task_id: str):
    """Poll background task status."""
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ═══════════════════════════════════════════════════
# Output files
# ═══════════════════════════════════════════════════

@app.get("/api/projects/{project_name}/scripts/{episode}")
def get_script(project_name: str, episode: int):
    """Read a generated script YAML file."""
    script_path = PROJECT_ROOT / OUTPUT_DIR / project_name / "scripts" / f"ep{episode:02d}_script.yaml"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail=f"Script for episode {episode} not found")
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"episode": episode, "content": content, "path": str(script_path)}


@app.get("/api/projects/{project_name}/reports/{report_type}")
def get_report(project_name: str, report_type: str):
    """Read an analysis/planning/review report."""
    report_dir = PROJECT_ROOT / OUTPUT_DIR / project_name
    type_to_path = {
        "analysis": report_dir / "analysis" / "analysis-report.md",
        "insight": report_dir / "analysis" / "insight-report.md",
        "plan": report_dir / "planning" / "episode-plan.md",
        "emotion": report_dir / "planning" / "emotion-curve.md",
        "final": report_dir / "final-check-report.md",
    }
    if report_type.startswith("review-"):
        ep = report_type.split("-")[1]
        type_to_path[report_type] = report_dir / "review" / f"review-ep{ep}.md"

    path = type_to_path.get(report_type)
    if not path:
        available = list(type_to_path.keys())
        raise HTTPException(status_code=400, detail=f"Unknown report type. Available: {available}")
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Report '{report_type}' not found at {path}")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"type": report_type, "content": content, "path": str(path)}


@app.get("/api/projects/{project_name}/files")
def list_output_files(project_name: str):
    """List all output files for a project."""
    project_dir = PROJECT_ROOT / OUTPUT_DIR / project_name
    if not project_dir.exists():
        return {"files": []}

    files = []
    for root, _, filenames in os.walk(project_dir):
        for fn in filenames:
            if fn.startswith("."):
                continue
            full = Path(root) / fn
            files.append({
                "name": fn,
                "path": str(full.relative_to(project_dir)),
                "size": full.stat().st_size,
            })
    return {"files": sorted(files, key=lambda f: f["path"])}


# ═══════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════

@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ── Entry ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
