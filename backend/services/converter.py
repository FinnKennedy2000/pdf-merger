import asyncio
import shutil
import uuid
from pathlib import Path

import img2pdf
from PIL import Image, ImageOps

from config import IMAGE_EXTS


async def convert_to_pdf(source: Path, dest_dir: Path) -> Path:
    ext = source.suffix.lower()
    out_path = dest_dir / (source.stem + ".pdf")

    if ext in IMAGE_EXTS:
        return _image_to_pdf(source, out_path)
    elif ext == ".docx":
        return await _docx_to_pdf(source, dest_dir)
    elif ext == ".pdf":
        shutil.copy2(source, out_path)
        return out_path
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _image_to_pdf(source: Path, out_path: Path) -> Path:
    ext = source.suffix.lower()

    with Image.open(source) as img:
        # Fix EXIF rotation
        img = ImageOps.exif_transpose(img)

        if ext in (".gif", ".tif", ".tiff"):
            # Use first frame only
            img.seek(0)
            img = img.convert("RGBA")

        # img2pdf needs JPEG or PNG; convert to PNG for safety
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            normalized_path = out_path.with_suffix(".png")
            img.save(normalized_path, "PNG")
        else:
            img = img.convert("RGB")
            normalized_path = out_path.with_suffix(".jpg")
            img.save(normalized_path, "JPEG", quality=90)

    with open(out_path, "wb") as f:
        f.write(img2pdf.convert(str(normalized_path)))

    # Clean up temp normalized file if different from source
    if normalized_path != source:
        normalized_path.unlink(missing_ok=True)

    return out_path


async def _docx_to_pdf(source: Path, dest_dir: Path) -> Path:
    # Use a unique LibreOffice user installation to allow concurrent conversions
    lo_profile = f"/tmp/lo-{uuid.uuid4().hex}"

    proc = await asyncio.create_subprocess_exec(
        "soffice",
        "--headless",
        f"-env:UserInstallation=file://{lo_profile}",
        "--convert-to", "pdf",
        "--outdir", str(dest_dir),
        str(source),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError(f"LibreOffice conversion timed out for {source.name}")

    if proc.returncode != 0:
        raise RuntimeError(
            f"LibreOffice failed for {source.name}: stdout={stdout.decode()!r} stderr={stderr.decode()!r}"
        )

    out_path = dest_dir / (source.stem + ".pdf")
    if not out_path.exists():
        raise RuntimeError(f"LibreOffice did not produce output for {source.name}")

    return out_path
