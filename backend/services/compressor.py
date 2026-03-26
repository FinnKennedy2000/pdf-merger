import os
import shutil
from pathlib import Path
from typing import List

import fitz  # pymupdf

from config import MAX_OUTPUT_BYTES


def compress_to_target(input_path: Path, max_bytes: int = MAX_OUTPUT_BYTES) -> dict:
    current = input_path
    passes_applied: List[str] = []

    # Pass 1: Lossless garbage collection + deflate compression
    p1_out = input_path.with_name("compressed_p1.pdf")
    _pass1_lossless(current, p1_out)
    if os.path.getsize(p1_out) < os.path.getsize(current):
        current = p1_out
        passes_applied.append("lossless_deflate")
    else:
        p1_out.unlink(missing_ok=True)

    if os.path.getsize(current) <= max_bytes:
        return _result(current, input_path, passes_applied, True)

    # Pass 2a: Reduce image DPI to 150
    p2a_out = input_path.with_name("compressed_p2a.pdf")
    _pass2_resample_images(current, p2a_out, target_dpi=150)
    current = p2a_out
    passes_applied.append("image_dpi_150")

    if os.path.getsize(current) <= max_bytes:
        return _result(current, input_path, passes_applied, True)

    # Pass 2b: Reduce image DPI to 96
    p2b_out = input_path.with_name("compressed_p2b.pdf")
    _pass2_resample_images(current, p2b_out, target_dpi=96)
    current = p2b_out
    passes_applied.append("image_dpi_96")

    if os.path.getsize(current) <= max_bytes:
        return _result(current, input_path, passes_applied, True)

    # Pass 2c: Reduce image DPI to 72
    p2c_out = input_path.with_name("compressed_p2c.pdf")
    _pass2_resample_images(current, p2c_out, target_dpi=72)
    current = p2c_out
    passes_applied.append("image_dpi_72")

    if os.path.getsize(current) <= max_bytes:
        return _result(current, input_path, passes_applied, True)

    # Pass 3: Convert to grayscale
    p3_out = input_path.with_name("compressed_p3.pdf")
    _pass3_grayscale(current, p3_out)
    current = p3_out
    passes_applied.append("grayscale")

    reached_target = os.path.getsize(current) <= max_bytes
    return _result(current, input_path, passes_applied, reached_target)


def _result(current: Path, input_path: Path, passes: List[str], reached: bool) -> dict:
    # Move final file to output path
    final_path = input_path.with_name("merged_final.pdf")
    shutil.move(str(current), str(final_path))
    # Clean up intermediate files
    for name in ["compressed_p1.pdf", "compressed_p2a.pdf", "compressed_p2b.pdf",
                 "compressed_p2c.pdf", "compressed_p3.pdf"]:
        p = input_path.with_name(name)
        p.unlink(missing_ok=True)
    return {
        "path": final_path,
        "size_bytes": os.path.getsize(final_path),
        "passes_applied": passes,
        "compressed_to_target": reached,
    }


def _pass1_lossless(src: Path, dst: Path):
    doc = fitz.open(str(src))
    doc.save(
        str(dst),
        garbage=4,
        deflate=True,
        deflate_images=True,
        deflate_fonts=True,
    )
    doc.close()


def _pass2_resample_images(src: Path, dst: Path, target_dpi: int):
    doc = fitz.open(str(src))

    for page in doc:
        image_list = page.get_images(full=True)
        for img_info in image_list:
            xref = img_info[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n > 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)

                # Estimate current DPI from page dimensions vs image resolution
                # Scale down to target DPI by resizing pixmap
                rect = page.rect
                page_width_pt = rect.width
                page_height_pt = rect.height

                current_w = pix.width
                current_h = pix.height

                # Points to inches: 72 pts = 1 inch
                expected_w_at_target = int((page_width_pt / 72) * target_dpi)
                expected_h_at_target = int((page_height_pt / 72) * target_dpi)

                if current_w > expected_w_at_target or current_h > expected_h_at_target:
                    scale = min(
                        expected_w_at_target / current_w,
                        expected_h_at_target / current_h,
                    )
                    new_w = max(1, int(current_w * scale))
                    new_h = max(1, int(current_h * scale))
                    pix = pix.scale_to(new_w, new_h)

                doc.update_stream(xref, pix.tobytes("jpg", jpg_quality=75))
                pix = None
            except Exception:
                continue

    doc.save(str(dst), garbage=4, deflate=True)
    doc.close()


def _pass3_grayscale(src: Path, dst: Path):
    doc = fitz.open(str(src))

    for page in doc:
        image_list = page.get_images(full=True)
        for img_info in image_list:
            xref = img_info[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n > 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                # Convert to grayscale
                gray = fitz.Pixmap(fitz.csGRAY, pix)
                doc.update_stream(xref, gray.tobytes("jpg", jpg_quality=70))
                gray = None
                pix = None
            except Exception:
                continue

    doc.save(str(dst), garbage=4, deflate=True)
    doc.close()
