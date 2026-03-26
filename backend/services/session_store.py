import json
import time
import uuid
from pathlib import Path
from typing import Optional

from config import TEMP_DIR


def _session_dir(session_id: str) -> Path:
    return TEMP_DIR / session_id


def _meta_path(session_dir: Path) -> Path:
    return session_dir / "meta.json"


def load_meta(session_dir: Path) -> Optional[dict]:
    p = _meta_path(session_dir)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _save_meta(session_dir: Path, meta: dict):
    _meta_path(session_dir).write_text(json.dumps(meta, default=str))


def get_or_create(session_id: str) -> dict:
    sdir = _session_dir(session_id)
    meta = load_meta(sdir) if sdir.exists() else None
    if meta is None:
        sdir.mkdir(parents=True, exist_ok=True)
        (sdir / "originals").mkdir(exist_ok=True)
        (sdir / "converted").mkdir(exist_ok=True)
        (sdir / "thumbnails").mkdir(exist_ok=True)
        (sdir / "output").mkdir(exist_ok=True)
        meta = {"id": session_id, "created_at": time.time(), "files": [], "jobs": {}}
        _save_meta(sdir, meta)
    return meta


def get(session_id: str) -> Optional[dict]:
    sdir = _session_dir(session_id)
    return load_meta(sdir)


def add_file(session_id: str, file_record: dict):
    sdir = _session_dir(session_id)
    meta = load_meta(sdir)
    meta["files"].append(file_record)
    _save_meta(sdir, meta)


def add_job(session_id: str, job_id: str, job_record: dict):
    sdir = _session_dir(session_id)
    meta = load_meta(sdir)
    meta["jobs"][job_id] = job_record
    _save_meta(sdir, meta)


def get_job(session_id: str, job_id: str) -> Optional[dict]:
    meta = get(session_id)
    if meta is None:
        return None
    return meta.get("jobs", {}).get(job_id)


def session_dir(session_id: str) -> Path:
    return _session_dir(session_id)
