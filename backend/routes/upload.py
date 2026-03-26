import uuid
import zipfile
from pathlib import Path
from typing import List

from fastapi import APIRouter, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from config import ALLOWED_EXTS, IMAGE_EXTS
from services import session_store
from services.converter import convert_to_pdf
from services.thumbnailer import generate_thumbnail

router = APIRouter()


@router.post("/upload")
async def upload_files(
    files: List[UploadFile],
    x_session_id: str = Header(...),
):
    if not x_session_id:
        raise HTTPException(status_code=400, detail="X-Session-ID header required")

    meta = session_store.get_or_create(x_session_id)
    sdir = session_store.session_dir(x_session_id)

    results = []

    for upload in files:
        ext = Path(upload.filename).suffix.lower()
        if ext not in ALLOWED_EXTS:
            raise HTTPException(status_code=415, detail=f"Unsupported file type: {ext}")

        # Save original
        file_id = uuid.uuid4().hex
        orig_path = sdir / "originals" / f"{file_id}{ext}"
        content = await upload.read()
        orig_path.write_bytes(content)

        if ext == ".zip":
            zip_results = await _process_zip(orig_path, sdir, x_session_id)
            results.extend(zip_results)
        else:
            record = await _process_single_file(orig_path, file_id, upload.filename, sdir, x_session_id)
            if record:
                results.append(record)

    return JSONResponse(content=results)


async def _process_single_file(
    orig_path: Path,
    file_id: str,
    original_name: str,
    sdir: Path,
    session_id: str,
) -> dict:
    ext = orig_path.suffix.lower()
    try:
        converted_pdf = await convert_to_pdf(orig_path, sdir / "converted")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed for {original_name}: {str(e)}")

    thumb_path = sdir / "thumbnails" / f"{file_id}.png"
    try:
        generate_thumbnail(converted_pdf, thumb_path)
    except Exception:
        thumb_path = None

    record = {
        "id": file_id,
        "filename": original_name,
        "type": _file_type_label(ext),
        "thumbnail_url": f"/thumbnail/{session_id}/{file_id}",
        "converted_pdf": str(converted_pdf),
    }

    session_store.add_file(session_id, record)
    return {k: v for k, v in record.items() if k != "converted_pdf"}


async def _process_zip(zip_path: Path, sdir: Path, session_id: str) -> list:
    results = []
    extract_dir = sdir / "originals" / f"zip_{zip_path.stem}"
    extract_dir.mkdir(exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            # Security: prevent path traversal
            safe_name = Path(name).name
            if not safe_name:
                continue
            ext = Path(safe_name).suffix.lower()
            if ext not in ALLOWED_EXTS or ext == ".zip":
                continue

            file_id = uuid.uuid4().hex
            dest = extract_dir / f"{file_id}{ext}"
            with zf.open(name) as src, open(dest, "wb") as dst:
                dst.write(src.read())

            record = await _process_single_file(dest, file_id, safe_name, sdir, session_id)
            if record:
                results.append(record)

    return results


def _file_type_label(ext: str) -> str:
    if ext in IMAGE_EXTS:
        return ext.lstrip(".").upper()
    return ext.lstrip(".").upper()
