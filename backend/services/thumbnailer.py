from pathlib import Path

import fitz  # pymupdf
from PIL import Image


def generate_thumbnail(pdf_path: Path, out_path: Path, dpi: int = 150, max_px: int = 400) -> Path:
    doc = fitz.open(str(pdf_path))
    page = doc[0]

    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    doc.close()

    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # Cap to max_px on longest side
    if max(img.width, img.height) > max_px:
        img.thumbnail((max_px, max_px), Image.LANCZOS)

    img.save(str(out_path), "PNG")
    return out_path
