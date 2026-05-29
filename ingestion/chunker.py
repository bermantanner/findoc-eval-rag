from dataclasses import dataclass
import tiktoken
from ingestion.parser import ParsedBlock

CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
ENCODING = "cl100k_base"  # matches text-embedding-3-small


@dataclass
class Chunk:
    text: str
    metadata: dict


def chunk_blocks(blocks: list[ParsedBlock], company: str, fiscal_year: str) -> list[Chunk]:
    enc = tiktoken.get_encoding(ENCODING)
    chunks = []
    for block in blocks:
        if block.block_type == "table":
            chunks.extend(_chunk_table(block, company, fiscal_year, enc))
        else:
            chunks.extend(_chunk_text(block, company, fiscal_year, enc))
    return chunks


def _chunk_text(block: ParsedBlock, company: str, fiscal_year: str, enc) -> list[Chunk]:
    tokens = enc.encode(block.text)
    chunks = []
    start = 0

    while start < len(tokens):
        end = min(start + CHUNK_SIZE, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(Chunk(
            text=enc.decode(chunk_tokens),
            metadata={
                "page_number": block.page_number,
                "source_table_name": None,
                "token_count": len(chunk_tokens),
                "company": company,
                "fiscal_year": fiscal_year,
                "block_type": "text",
            },
        ))
        if end == len(tokens):
            break
        start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


def _chunk_table(block: ParsedBlock, company: str, fiscal_year: str, enc) -> list[Chunk]:
    tokens = enc.encode(block.text)

    if len(tokens) <= CHUNK_SIZE:
        return [Chunk(
            text=block.text,
            metadata={
                "page_number": block.page_number,
                "source_table_name": block.source_table_name,
                "token_count": len(tokens),
                "company": company,
                "fiscal_year": fiscal_year,
                "block_type": "table",
            },
        )]

    # Table exceeds chunk size — split by row, repeating header in each chunk
    lines = block.text.split("\n")
    if len(lines) < 3:
        return _chunk_text(block, company, fiscal_year, enc)

    header = lines[0]
    separator = lines[1]
    data_rows = lines[2:]
    header_tokens = len(enc.encode(header + "\n" + separator + "\n"))

    chunks = []
    current_rows: list[str] = []
    current_tokens = header_tokens

    for row in data_rows:
        row_tokens = len(enc.encode(row + "\n"))
        if current_tokens + row_tokens > CHUNK_SIZE and current_rows:
            table_text = "\n".join([header, separator] + current_rows)
            chunks.append(Chunk(
                text=table_text,
                metadata={
                    "page_number": block.page_number,
                    "source_table_name": block.source_table_name,
                    "token_count": current_tokens,
                    "company": company,
                    "fiscal_year": fiscal_year,
                    "block_type": "table",
                },
            ))
            current_rows = []
            current_tokens = header_tokens

        current_rows.append(row)
        current_tokens += row_tokens

    if current_rows:
        table_text = "\n".join([header, separator] + current_rows)
        chunks.append(Chunk(
            text=table_text,
            metadata={
                "page_number": block.page_number,
                "source_table_name": block.source_table_name,
                "token_count": current_tokens,
                "company": company,
                "fiscal_year": fiscal_year,
                "block_type": "table",
            },
        ))

    return chunks
