from pathlib import Path
from typing import List

from pypdf import PdfReader, PdfWriter


def merge_pdfs(ordered_paths: List[Path], output_path: Path) -> Path:
    writer = PdfWriter()

    for pdf_path in ordered_paths:
        reader = PdfReader(str(pdf_path))
        for page in reader.pages:
            writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path
