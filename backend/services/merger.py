from pathlib import Path
from typing import List

import fitz


def merge_pdfs(ordered_paths: List[Path], output_path: Path) -> Path:
    merged = fitz.open()

    for pdf_path in ordered_paths:
        with fitz.open(str(pdf_path)) as doc:
            merged.insert_pdf(doc)

    merged.save(str(output_path))
    merged.close()

    return output_path
