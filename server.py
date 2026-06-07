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
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.pipeline import Pipeline, create_pipeline
from crawler import NovelSearcher, NovelDownloader

# ── Load env vars ──
try:
    from dotenv import load_dotenv
    _env_file = PROJECT_ROOT / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
    else:
        load_dotenv()  # try default
except ImportError:
    pass

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

# Override config with env vars
for _key, _env_var in [
    ("llm.api_key", "LLM_API_KEY"),
    ("llm.base_url", "LLM_BASE_URL"),
    ("llm.model", "LLM_MODEL"),
    ("llm_light.api_key", "LLM_LIGHT_API_KEY"),
    ("llm_light.base_url", "LLM_LIGHT_BASE_URL"),
    ("llm_light.model", "LLM_LIGHT_MODEL"),
]:
    _val = os.getenv(_env_var, "")
    if _val and _val != "sk-YOUR-API-KEY":
        _section, _k = _key.split(".")
        config.setdefault(_section, {})[_k] = _val

OUTPUT_DIR = config.get("output", {}).get("output_dir", "./output")

# ── Pipeline cache (one per project) ──
_pipelines: dict[str, Pipeline] = {}
_lock = threading.Lock()

# ── Background task store ──
_tasks: dict[str, dict] = {}
_task_counter = 0

# ── Agent factory (lazy, created once) ──
_agents_cache: Optional[dict] = None

def _has_valid_api_key() -> bool:
    """Check if a valid API key is configured."""
    key = config.get("llm", {}).get("api_key", "")
    return bool(key) and key != "sk-YOUR-API-KEY" and len(key) > 10

def _create_agents() -> dict:
    """Create all pipeline agent instances."""
    global _agents_cache
    if _agents_cache is not None:
        return _agents_cache

    from agents import (
        create_knowledge_curator,
        create_novel_analyzer,
        create_insight_architect,
        create_episode_architect,
        create_emotion_architect,
        create_script_writer,
        create_review_director,
        create_continuity_recorder,
        create_storyboard_director,
        # v2.1
        create_content_grader,
        create_episode_director,
    )

    _agents_cache = {
        "knowledge-curator": create_knowledge_curator(config=config),
        "novel-analyzer": create_novel_analyzer(config=config),
        "insight-architect": create_insight_architect(config=config),
        "episode-architect": create_episode_architect(config=config),
        "episode-director": create_episode_director(config=config),
        "emotion-architect": create_emotion_architect(config=config),
        "script-writer": create_script_writer(config=config),
        "review-director": create_review_director(config=config),
        "continuity-recorder": create_continuity_recorder(config=config),
        "storyboard-director": create_storyboard_director(config=config),
        # v2.1
        "content-grader": create_content_grader(config=config),
    }
    return _agents_cache


def _get_pipeline(project_name: str) -> Pipeline:
    """Get or create a pipeline for a project."""
    with _lock:
        if project_name not in _pipelines:
            # Always create agents — they fall back to rule-based mode
            # when no LLM API key is configured.
            agents = _create_agents()
            _pipelines[project_name] = create_pipeline(
                project_name=project_name,
                output_dir=OUTPUT_DIR,
                config_path=config,  # 传 dict（含内存中的 API key）
                agents=agents,
            )
        return _pipelines[project_name]


def _run_phase_task(task_id: str, project_name: str, phase: str, **kwargs):
    """Background: run a pipeline phase and store result."""
    try:
        pipeline = _get_pipeline(project_name)
        if phase == "generate_images":
            result = pipeline.generate_image_prompts(**kwargs)
        else:
            result = pipeline._run_phase(phase, **kwargs)
        _tasks[task_id] = {"status": "completed", "result": result}
    except Exception as e:
        _tasks[task_id] = {"status": "failed", "error": str(e)}


def _run_auto_task(task_id: str, project_name: str, adaptation_mode: str = "balanced", target_format: str = "long_drama", **kwargs):
    """Background: run full auto pipeline."""
    try:
        pipeline = _get_pipeline(project_name)
        # v2.1: 传递适应度模式和剧集格式
        result = pipeline.auto(
            adaptation_mode=adaptation_mode,
            target_format=target_format,
            **kwargs,
        )
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
    adaptation_mode: str = "balanced"   # v2.1: strict | balanced | loose
    target_format: str = "long_drama"   # v2.1: short_drama | long_drama

class ReviseRequest(BaseModel):
    modification_notes: str             # 用户修改意见
    adaptation_mode: str = "balanced"   # v2.1: strict | balanced | loose

class CrawlSearchRequest(BaseModel):
    keyword: str = ""
    genre: str = ""                     # 玄幻/武侠/都市/言情...
    limit: int = 20

class CrawlDownloadRequest(BaseModel):
    source_url: str
    source_name: str = ""
    title: str = ""
    max_chapters: int = 50


# ═══════════════════════════════════════════════════
# Crawler
# ═══════════════════════════════════════════════════

@app.post("/api/crawl/search")
def crawl_search(body: CrawlSearchRequest):
    """Search novels from public sources by keyword and genre."""
    try:
        searcher = NovelSearcher()
        results = searcher.search(keyword=body.keyword, genre=body.genre, limit=body.limit)
        return {"status": "ok", "results": results, "total": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@app.post("/api/projects/{project_name}/crawl/download")
def crawl_download(project_name: str, body: CrawlDownloadRequest):
    """Download a novel from a public source and save to project uploads dir."""
    upload_dir = PROJECT_ROOT / "uploads" / project_name
    upload_dir.mkdir(parents=True, exist_ok=True)
    try:
        downloader = NovelDownloader()
        result = downloader.download(
            source_url=body.source_url,
            output_dir=str(upload_dir),
            title=body.title,
            max_chapters=body.max_chapters,
        )
        if result.get("status") == "failed":
            raise HTTPException(status_code=500, detail=result.get("error", "下载失败"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


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


@app.post("/api/projects/{project_name}/upload")
async def upload_files(project_name: str, files: list[UploadFile] = File(...)):
    """Upload .txt novel chapter files for a project."""
    upload_dir = PROJECT_ROOT / "uploads" / project_name
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved = 0
    for f in files:
        if f.filename and f.filename.endswith(".txt"):
            content = await f.read()
            filepath = upload_dir / f.filename
            with open(filepath, "wb") as out:
                out.write(content)
            saved += 1

    return {"status": "ok", "files_saved": saved, "upload_dir": str(upload_dir)}


@app.get("/api/projects/{project_name}/download/{file_path:path}")
def download_file(project_name: str, file_path: str):
    """Download a generated output file."""
    full_path = PROJECT_ROOT / OUTPUT_DIR / project_name / file_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(full_path))


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


@app.post("/api/projects/{project_name}/revise/{episode}")
def run_revise(project_name: str, episode: int, body: ReviseRequest, bg: BackgroundTasks):
    """Accept user modification notes and re-generate the script."""
    task_id = f"{project_name}-revise-{episode}-{datetime.now().timestamp()}"
    _tasks[task_id] = {"status": "running"}
    # Re-run write phase with revision notes — pipeline handles versioned output
    bg.add_task(
        _run_phase_task, task_id, project_name, "write",
        episode=episode,
        revision_notes=body.modification_notes,
        adaptation_mode=body.adaptation_mode,
    )
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


@app.post("/api/projects/{project_name}/generate-images/{episode}")
def run_generate_images(project_name: str, episode: int, bg: BackgroundTasks):
    """Generate image prompts (& actual images if API key configured) from storyboard."""
    task_id = f"{project_name}-images-{episode}-{datetime.now().timestamp()}"
    _tasks[task_id] = {"status": "running"}
    bg.add_task(_run_phase_task, task_id, project_name, "generate_images", episode=episode)
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

    # v2.1: 应用适应度模式和剧集格式到配置
    if body.adaptation_mode:
        config.setdefault("content_grading", {})["mode"] = body.adaptation_mode
    if body.target_format:
        config.setdefault("episode_rhythm", {})["target_format"] = body.target_format

    bg.add_task(
        _run_auto_task,
        task_id,
        project_name,
        source_dir=body.source_dir or None,
        title=body.title,
        author=body.author,
        episodes=body.episodes,
        adaptation_mode=body.adaptation_mode,
        target_format=body.target_format,
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
def get_script(project_name: str, episode: int, version: int = 0):
    """Read a generated script YAML file. version=0 returns latest, version=N returns vN."""
    scripts_dir = PROJECT_ROOT / OUTPUT_DIR / project_name / "scripts"
    base = f"ep{episode:02d}_script"

    if version > 0:
        script_path = scripts_dir / f"{base}_v{version}.yaml"
    else:
        # Find latest version
        candidates = sorted(scripts_dir.glob(f"{base}*.yaml"))
        if not candidates:
            raise HTTPException(status_code=404, detail=f"Script for episode {episode} not found")
        script_path = candidates[-1]  # last = latest version

    if not script_path.exists():
        raise HTTPException(status_code=404, detail=f"Script for episode {episode} v{version} not found")
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract version from filename
    fname = script_path.stem  # ep01_script or ep01_script_v2
    if "_v" in fname:
        file_version = int(fname.split("_v")[-1])
    else:
        file_version = 1

    return {
        "episode": episode,
        "version": file_version,
        "content": content,
        "path": str(script_path),
    }


@app.get("/api/projects/{project_name}/reports/{report_type}")
def get_report(project_name: str, report_type: str):
    """Read an analysis/planning/review report."""
    report_dir = PROJECT_ROOT / OUTPUT_DIR / project_name
    type_to_path = {
        "analysis": report_dir / "analysis" / "analysis-report.md",
        "insight": report_dir / "analysis" / "insight-report.md",
        "plan": report_dir / "planning" / "episode-plan.md",
        "emotion": report_dir / "planning" / "emotion-curve.json",
        "final": report_dir / "final-check-report.md",
    }
    if report_type.startswith("review-"):
        ep = report_type.split("-")[1]
        type_to_path[report_type] = report_dir / "review" / f"review-ep{int(ep):02d}.md"

    path = type_to_path.get(report_type)
    if not path:
        available = list(type_to_path.keys())
        raise HTTPException(status_code=400, detail=f"Unknown report type. Available: {available}")
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Report '{report_type}' not found at {path}")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"type": report_type, "content": content, "path": str(path)}


@app.get("/api/projects/{project_name}/images/{episode}")
def list_images(project_name: str, episode: int):
    """List generated images for an episode."""
    img_dir = PROJECT_ROOT / OUTPUT_DIR / project_name / "images" / f"ep{episode:02d}"
    if not img_dir.exists():
        return {"images": [], "prompts": []}

    images = []
    prompts = []
    for f in sorted(img_dir.iterdir()):
        if f.suffix in (".png", ".jpg", ".jpeg", ".webp"):
            images.append({
                "name": f.name,
                "url": f"/api/projects/{project_name}/images/{episode}/{f.name}",
                "size": f.stat().st_size,
            })
        elif f.name == "image_prompts.json":
            try:
                with open(f, "r", encoding="utf-8") as pf:
                    prompts = json.load(pf).get("prompts", [])[:5]
            except Exception:
                pass
    return {"images": images, "prompts": prompts}


@app.get("/api/projects/{project_name}/images/{episode}/{filename}")
def serve_image(project_name: str, episode: int, filename: str):
    """Serve a generated image file."""
    img_path = PROJECT_ROOT / OUTPUT_DIR / project_name / "images" / f"ep{episode:02d}" / filename
    if not img_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(img_path))


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
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "api_key_configured": _has_valid_api_key(),
        "agents_loaded": _agents_cache is not None,
        "llm_provider": config.get("llm", {}).get("provider", "unknown"),
        "llm_model": config.get("llm", {}).get("model", "unknown"),
    }


class ConfigUpdate(BaseModel):
    api_key: str = ""
    base_url: str = ""
    model: str = ""


# ═══════════════════════════════════════════════════
# v2.1 新增: 内容分级 & 智能分集 API
# ═══════════════════════════════════════════════════

@app.get("/api/projects/{project_name}/grading-stats")
def get_grading_stats(project_name: str):
    """获取内容分级统计（S/A/B比例）"""
    pipeline = _get_pipeline(project_name)
    project_dir = PROJECT_ROOT / OUTPUT_DIR / project_name
    scripts_dir = project_dir / "scripts"
    if not scripts_dir.exists():
        return {"stats": None, "message": "尚未生成剧本"}

    # 汇总所有已生成剧本的分级统计
    total_stats = {"S": 0, "A": 0, "B": 0, "total": 0}
    for script_file in sorted(scripts_dir.glob("ep*_script.yaml")):
        try:
            with open(script_file, "r", encoding="utf-8") as f:
                content = f.read()
            # 统计 content_grade 标记
            for grade in ["S", "A", "B"]:
                count = content.count(f"content_grade: {grade}")
                total_stats[grade] += count
                total_stats["total"] += count
        except Exception:
            pass

    if total_stats["total"] > 0:
        total_stats["S_ratio"] = round(total_stats["S"] / total_stats["total"] * 100, 1)
        total_stats["A_ratio"] = round(total_stats["A"] / total_stats["total"] * 100, 1)
        total_stats["B_ratio"] = round(total_stats["B"] / total_stats["total"] * 100, 1)

    return {"stats": total_stats}


@app.get("/api/projects/{project_name}/conflict-map")
def get_conflict_map(project_name: str):
    """获取冲突节点分布图数据"""
    project_dir = PROJECT_ROOT / OUTPUT_DIR / project_name
    conflict_path = project_dir / "analysis" / "conflict-nodes.json"
    if not conflict_path.exists():
        return {"nodes": [], "message": "冲突节点数据不存在，请先运行分析阶段"}

    try:
        with open(conflict_path, "r", encoding="utf-8") as f:
            nodes = json.load(f)
        return {"nodes": nodes, "total": len(nodes)}
    except Exception as e:
        return {"nodes": [], "error": str(e)}


@app.get("/api/projects/{project_name}/episodes/{episode}/annotations")
def get_episode_annotations(project_name: str, episode: int):
    """获取单集标注（看点/伏笔/招商备注）"""
    project_dir = PROJECT_ROOT / OUTPUT_DIR / project_name
    annotations_path = project_dir / "planning" / "episode-annotations.json"
    if not annotations_path.exists():
        return {"annotations": None, "message": "剧集标注数据不存在"}

    try:
        with open(annotations_path, "r", encoding="utf-8") as f:
            all_annotations = json.load(f)
        for ann in all_annotations:
            if ann.get("episode_id") == episode:
                return {"annotations": ann}
        return {"annotations": None, "message": f"未找到第{episode}集的标注"}
    except Exception as e:
        return {"annotations": None, "error": str(e)}


class RhythmConfigUpdate(BaseModel):
    adaptation_mode: str = "balanced"    # strict | balanced | loose
    target_format: str = "long_drama"    # short_drama | long_drama


@app.put("/api/projects/{project_name}/rhythm-config")
def update_rhythm_config(project_name: str, body: RhythmConfigUpdate):
    """更新项目的适应度模式和剧集格式"""
    if body.adaptation_mode not in ("strict", "balanced", "loose"):
        raise HTTPException(400, "adaptation_mode 必须是 strict/balanced/loose")
    if body.target_format not in ("short_drama", "long_drama"):
        raise HTTPException(400, "target_format 必须是 short_drama/long_drama")

    # 更新内存中的 config
    config.setdefault("content_grading", {})["mode"] = body.adaptation_mode
    config.setdefault("episode_rhythm", {})["target_format"] = body.target_format

    return {
        "status": "ok",
        "adaptation_mode": body.adaptation_mode,
        "target_format": body.target_format,
    }


@app.post("/api/config")
def update_config(body: ConfigUpdate):
    """Update LLM config at runtime (api_key, base_url, model)."""
    global _agents_cache, _pipelines
    if body.api_key and body.api_key != "sk-YOUR-API-KEY":
        config.setdefault("llm", {})["api_key"] = body.api_key
    if body.base_url:
        config.setdefault("llm", {})["base_url"] = body.base_url
    if body.model:
        config.setdefault("llm", {})["model"] = body.model
    # Invalidate agent cache so they get recreated with new config
    _agents_cache = None
    _pipelines.clear()
    return {"status": "ok", "api_key_configured": _has_valid_api_key()}


# ── Entry ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
