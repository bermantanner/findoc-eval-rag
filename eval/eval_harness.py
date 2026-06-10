#!/usr/bin/env python3
"""
Standalone eval harness for FinDoc-Eval RAG pipeline.

Usage:
    python3 eval/eval_harness.py --document-id <uuid> [--api-url http://localhost:8000]

Prerequisites:
    - API must be running (docker compose up --build)
    - NVIDIA 10-K must be uploaded and its document_id passed via --document-id
    - OPENAI_API_KEY must be set in the environment
"""

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

JUDGE_MODEL = "gpt-4o-mini"
RETRIEVAL_HIT_THRESHOLD = 0.60
API_KEY = "dev-secret-key"

JUDGE_SYSTEM_PROMPT = """You are grading a financial RAG system. Given a question, an expected answer, \
and the system's actual answer, determine if the actual answer is correct.

Rules:
- Numbers must match within normal rounding (e.g. $130.5B ≈ $130,497M ≈ approximately $130 billion)
- Paraphrasing is fine — exact wording is not required
- The actual answer may include extra context; that's OK as long as the core fact is right
- If the actual answer says "Insufficient data" but a correct answer exists, that is INCORRECT
- If the actual answer is vague where the expected is specific (e.g., "revenue increased" vs "$130.5B"), \
that is INCORRECT
- For qualitative questions, the actual answer must convey the same key concept as the expected answer

Respond with JSON only: {"correct": true/false, "reason": "<one sentence explanation>"}"""


def parse_plain_response(text: str) -> tuple[str, float]:
    sep = "=" * 60
    parts = text.split(sep)
    answer = parts[2].strip() if len(parts) > 2 else text.strip()
    similarities = re.findall(r"similarity: (\d+\.\d+)", text)
    top_similarity = float(similarities[0]) if similarities else 0.0
    return answer, top_similarity


def judge_answer(client: OpenAI, question: str, expected: str, actual: str) -> dict:
    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"Expected answer: {expected}\n\n"
                    f"Actual answer: {actual}"
                ),
            },
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def run_eval(document_id: str, api_url: str) -> None:
    dataset_path = Path(__file__).parent / "golden_dataset.json"
    with open(dataset_path) as f:
        data = json.load(f)
    questions = data["questions"]

    openai_client = OpenAI()
    results = []

    print(f"\nFinDoc-Eval Harness")
    print(f"Document ID : {document_id}")
    print(f"API         : {api_url}")
    print(f"Questions   : {len(questions)}")
    print(f"Judge       : {JUDGE_MODEL}")
    print("-" * 60)

    for i, item in enumerate(questions):
        print(f"[{i + 1}/{len(questions)}] {item['question'][:65]}...")

        start = time.time()
        try:
            response = httpx.post(
                f"{api_url}/api/v1/query",
                headers={"X-API-Key": API_KEY},
                json={"query": item["question"], "document_id": document_id},
                params={"format": "plain"},
                timeout=30.0,
            )
            latency = time.time() - start

            if response.status_code != 200:
                raise RuntimeError(f"HTTP {response.status_code}: {response.text[:120]}")

            actual_answer, top_similarity = parse_plain_response(response.text)

        except Exception as exc:
            latency = time.time() - start
            results.append({
                "id": item["id"],
                "question": item["question"],
                "expected": item["expected_answer"],
                "actual": str(exc),
                "correct": False,
                "reason": f"Request failed: {exc}",
                "top_similarity": 0.0,
                "latency": latency,
            })
            print(f"       ✖️ ERROR — {exc}")
            continue

        verdict = judge_answer(
            openai_client, item["question"], item["expected_answer"], actual_answer
        )

        results.append({
            "id": item["id"],
            "question": item["question"],
            "expected": item["expected_answer"],
            "actual": actual_answer,
            "correct": verdict["correct"],
            "reason": verdict["reason"],
            "top_similarity": top_similarity,
            "latency": latency,
        })

        status = "✔️" if verdict["correct"] else "✖️"
        retrieval = "HIT " if top_similarity >= RETRIEVAL_HIT_THRESHOLD else "MISS"
        print(f"       {status} | retrieval={retrieval} ({top_similarity:.2f}) | {latency:.1f}s")
        print(f"          judge: {verdict['reason']}")

    print("-" * 60)
    write_benchmarks(results, document_id)
    print(f"\nResults written to BENCHMARKS.md")


def write_benchmarks(results: list[dict], document_id: str) -> None:
    n = len(results)
    n_correct = sum(1 for r in results if r["correct"])
    n_retrieval_hits = sum(
        1 for r in results if r["top_similarity"] >= RETRIEVAL_HIT_THRESHOLD
    )
    latencies = [r["latency"] for r in results]
    avg_latency = sum(latencies) / len(latencies)
    p95_latency = sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)]

    run_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# Eval Benchmarks — NVIDIA FY2025 10-K",
        "",
        f"**Run:** {run_time}  ",
        f"**Document ID:** `{document_id}`  ",
        f"**Judge model:** {JUDGE_MODEL}  ",
        f"**Retrieval hit threshold:** similarity ≥ {RETRIEVAL_HIT_THRESHOLD}",
        "",
        "## Summary",
        "",
        "| Metric | Result |",
        "|---|---|",
        f"| Answer Correctness | {n_correct}/{n} ({n_correct / n * 100:.0f}%) |",
        f"| Retrieval Hit Rate | {n_retrieval_hits}/{n} ({n_retrieval_hits / n * 100:.0f}%) |",
        f"| Avg Latency | {avg_latency:.1f}s |",
        f"| P95 Latency | {p95_latency:.1f}s |",
        "",
        "## Per-Question Results",
        "",
        "| # | Question | Correct? | Top Sim | Latency | Judge Reason |",
        "|---|---|---|---|---|---|",
    ]

    for i, r in enumerate(results):
        status = "✔️" if r["correct"] else "✖️"
        q = r["question"][:55] + ("..." if len(r["question"]) > 55 else "")
        retrieval_flag = "" if r["top_similarity"] >= RETRIEVAL_HIT_THRESHOLD else " [!]"
        lines.append(
            f"| {i + 1} | {q} | {status} | "
            f"{r['top_similarity']:.2f}{retrieval_flag} | "
            f"{r['latency']:.1f}s | {r['reason']} |"
        )

    failed = [r for r in results if not r["correct"]]
    if failed:
        lines += ["", "## Failed Cases", ""]
        for r in failed:
            actual_truncated = r["actual"][:600] + ("..." if len(r["actual"]) > 600 else "")
            lines += [
                f"### {r['id']}",
                "",
                f"**Question:** {r['question']}",
                "",
                f"**Expected:** {r['expected']}",
                "",
                f"**Actual:** {actual_truncated}",
                "",
                f"**Judge:** {r['reason']}",
                "",
            ]

    Path("BENCHMARKS.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RAG eval harness against live API")
    parser.add_argument(
        "--document-id",
        required=True,
        help="UUID of the uploaded NVIDIA 10-K document (from upload response)",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)",
    )
    args = parser.parse_args()
    run_eval(args.document_id, args.api_url)
