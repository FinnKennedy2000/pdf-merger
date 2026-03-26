from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from services import session_store

router = APIRouter()


@router.get("/thumbnail/{session_id}/{file_id}")
def get_thumbnail(session_id: str, file_id: str):
    sdir = session_store.session_dir(session_id)
    thumb = sdir / "thumbnails" / f"{file_id}.png"

    if not thumb.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    return FileResponse(str(thumb), media_type="image/png")
