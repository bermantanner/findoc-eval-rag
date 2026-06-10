from dataclasses import dataclass
from typing import Optional
import pdfplumber


@dataclass
class ParsedBlock:
    text: str
    page_number: int
    block_type: str  # "text" or "table"
    source_table_name: Optional[str] = None


def parse_pdf(pdf_path: str) -> list[ParsedBlock]:
    """
    Extract text and tables from a native-text-layer PDF.
    Raises ValueError for scanned PDFs with no text layer.
    """
    blocks = []

    with pdfplumber.open(pdf_path) as pdf:
        sample = "".join(p.extract_text() or "" for p in pdf.pages[:5])
        if len(sample.strip()) < 100:
            raise ValueError("No readable text layer — scanned PDFs are not supported.")

        for page in pdf.pages:
            page_num = page.page_number  # 1-indexed

            for i, table_obj in enumerate(page.find_tables()):
                md = _table_to_markdown(table_obj.extract())
                if md:
                    blocks.append(ParsedBlock(
                        text=md,
                        page_number=page_num,
                        block_type="table",
                        source_table_name=f"table_p{page_num}_{i + 1}",
                    ))

            text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
            if text.strip():
                blocks.append(ParsedBlock(
                    text=text.strip(),
                    page_number=page_num,
                    block_type="text",
                ))

    return blocks


def _table_to_markdown(table: list[list]) -> str:
    if not table:
        return ""

    cleaned = []
    for row in table:
        cells = [str(c).strip() if c is not None else "" for c in row]
        merged = _merge_row(cells)
        if merged:
            cleaned.append(merged)

    if not cleaned:
        return ""

    lines = []
    for i, row in enumerate(cleaned):
        lines.append("| " + " | ".join(row) + " |")
        if i == 0:
            lines.append("|" + "|".join(["---"] * len(row)) + "|")

    return "\n".join(lines)


def _merge_row(cells: list[str]) -> list[str]:
    """Merge currency symbols with adjacent values and drop empty cells."""
    merged = []
    skip = False
    for i, cell in enumerate(cells):
        if skip:
            skip = False
            continue
        if cell in ("$", "€", "£", "¥") and i + 1 < len(cells) and cells[i + 1]:
            merged.append(f"{cell}{cells[i + 1]}")
            skip = True
        elif cell:
            merged.append(cell)
    return merged
