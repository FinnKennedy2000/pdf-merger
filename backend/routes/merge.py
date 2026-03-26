import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from services import session_store
from services.merger import merge_pdfs
from services.compressor import compress_to_target

router = APIRouter()


class MergeRequest(BaseModel):
    session_id: str
    order: List[str]  # list of file IDs in desired order


@router.post("/merge")
async def merge(req: MergeRequest):
    meta = session_store.get(req.session_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Session not found")

    # Build a lookup of file_id -> converted_pdf path
    file_map = {f["id"]: f for f in meta["files"]}

    missing = [fid for fid in req.order if fid not in file_map]
    if missing:
        raise HTTPException(status_code=422, detail=f"Unknown file IDs: {missing}")

    ordered_paths = []
    for fid in req.order:
        pdf_path = Path(file_map[fid]["converted_pdf"])
        if not pdf_path.exists():
            raise HTTPException(status_code=422, detail=f"Converted PDF missing for file {fid}")
        ordered_paths.append(pdf_path)

    sdir = session_store.session_dir(req.session_id)
    raw_merged = sdir / "output" / "merged_raw.pdf"

    # Merge
    try:
        merge_pdfs(ordered_paths, raw_merged)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Merge failed: {str(e)}")

    # Compress
    try:
        result = compress_to_target(raw_merged)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compression failed: {str(e)}")

    job_id = uuid.uuid4().hex
    job_record = {
        "path": str(result["path"]),
        "size_bytes": result["size_bytes"],
        "passes_applied": result["passes_applied"],
        "compressed_to_target": result["compressed_to_target"],
        "pages": len(ordered_paths),
    }
    session_store.add_job(req.session_id, job_id, job_record)

    return {
        "job_id": job_id,
        "size_bytes": result["size_bytes"],
        "size_mb": round(result["size_bytes"] / 1024 / 1024, 2),
        "pages": len(ordered_paths),
        "compressed_to_target": result["compressed_to_target"],
        "passes_applied": result["passes_applied"],
    }


@router.get("/download/{session_id}/{job_id}")
def download(session_id: str, job_id: str, background_tasks: BackgroundTasks):
    job = session_store.get_job(session_id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    pdf_path = Path(job["path"])
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Output file not found")

    return FileResponse(
        str(pdf_path),
        media_type="application/pdf",
        filename="merged.pdf",
        headers={"Content-Disposition": 'attachment; filename="merged.pdf"'},
    )
