#!/usr/bin/env python3
"""Interactive CLI for querying an ingested document.

Usage: python3 ask.py <document_id>

Consumes the structured JSON response from POST /api/v1/query and renders it
for a human. Presentation lives here, at the edge — the API returns data.
"""
import json
import sys
import urllib.error
import urllib.request

API_URL = "http://localhost:8000/api/v1/query"
API_KEY = "dev-secret-key"
SEP = "=" * 60


def format_response(data: dict) -> str:
    lines = [SEP, "ANSWER", SEP, data["answer"].strip(), "", SEP, "SOURCES", SEP]

    if not data["chunks"]:
        lines.append("    (no chunks met the similarity threshold)")
        return "\n".join(lines)

    for i, c in enumerate(data["chunks"]):
        snippet = c["text"].replace("\n", " ").strip()[:200]
        lines += [
            f"[{i + 1}] {c['company']} {c['fiscal_year']} — "
            f"Page {c['page']} (similarity: {c['similarity']:.2f})",
            f"    ...{snippet}...",
            "",
        ]
    return "\n".join(lines)


def main() -> None:
    doc_id = sys.argv[1] if len(sys.argv) > 1 else input("Document ID: ").strip()

    while True:
        try:
            question = input("\nAsk a question (or 'quit' to exit): ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if question.lower() in ("quit", "exit", "q"):
            break
        if not question:
            continue

        payload = json.dumps({"query": question, "document_id": doc_id}).encode()
        req = urllib.request.Request(
            API_URL,
            data=payload,
            headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
            print("\n" + format_response(data))
        except urllib.error.HTTPError as e:
            print(f"Error {e.code}: {e.read().decode()}")


if __name__ == "__main__":
    main()
