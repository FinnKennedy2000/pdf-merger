from pathlib import Path
from typing import List

import fitz

# A4 in points (72 pts/inch)
A4_WIDTH = 595
A4_HEIGHT = 842


def merge_pdfs(ordered_paths: List[Path], output_path: Path) -> Path:
    merged = fitz.open()

    for pdf_path in ordered_paths:
        with fitz.open(str(pdf_path)) as doc:
            for src_page in doc:
                src_rect = src_page.rect
                # Determine target dimensions preserving orientation
                if src_rect.width > src_rect.height:
                    target_w, target_h = A4_HEIGHT, A4_WIDTH  # landscape
                else:
                    target_w, target_h = A4_WIDTH, A4_HEIGHT  # portrait

                new_page = merged.new_page(width=target_w, height=target_h)
                new_page.show_pdf_page(new_page.rect, doc, src_page.number)

    merged.save(str(output_path))
    merged.close()

    return output_path
