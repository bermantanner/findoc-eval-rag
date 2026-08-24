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


def judge_answer(client: OpenAI, question: str, expected: str, actual: str) -> dict:
    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        temperature=0,
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


def run_pass(
    document_id: str,
    api_url: str,
    questions: list[dict],
    openai_client: OpenAI,
    label: str,
) -> list[dict]:
    """Run the full question set once and return per-question results."""
    results = []

    for i, item in enumerate(questions):
        print(f"{label} [{i + 1}/{len(questions)}] {item['question'][:58]}...")

        start = time.time()
        try:
            response = httpx.post(
                f"{api_url}/api/v1/query",
                headers={"X-API-Key": API_KEY},
                json={"query": item["question"], "document_id": document_id},
                timeout=30.0,
            )
            latency = time.time() - start

            if response.status_code != 200:
                raise RuntimeError(f"HTTP {response.status_code}: {response.text[:120]}")

            payload = response.json()
            actual_answer = payload["answer"]
            retrieved = payload["chunks"]
            top_similarity = retrieved[0]["similarity"] if retrieved else 0.0
            retrieved_pages = [c["page"] for c in retrieved]

        except Exception as exc:
            latency = time.time() - start
            results.append({
                "id": item["id"],
                "question": item["question"],
                "expected": item["expected_answer"],
                "tags": item.get("tags", []),
                "actual": str(exc),
                "correct": False,
                "reason": f"Request failed: {exc}",
                "top_similarity": 0.0,
                "retrieved_pages": [],
                "latency": latency,
                "transport_error": True,
            })
            print(f"       TRANSPORT ERROR — {exc}")
            continue

        verdict = judge_answer(
            openai_client, item["question"], item["expected_answer"], actual_answer
        )

        results.append({
            "id": item["id"],
            "question": item["question"],
            "expected": item["expected_answer"],
            "tags": item.get("tags", []),
            "actual": actual_answer,
            "correct": verdict["correct"],
            "reason": verdict["reason"],
            "top_similarity": top_similarity,
            "retrieved_pages": retrieved_pages,
            "latency": latency,
            "transport_error": False,
        })

        status = "PASS" if verdict["correct"] else "FAIL"
        retrieval = "HIT " if top_similarity >= RETRIEVAL_HIT_THRESHOLD else "MISS"
        print(f"       {status} | retrieval={retrieval} ({top_similarity:.2f}) | {latency:.1f}s")

    return results


def run_eval(document_id: str, api_url: str, runs: int) -> None:
    dataset_path = Path(__file__).parent / "golden_dataset.json"
    with open(dataset_path) as f:
        data = json.load(f)
    questions = data["questions"]

    openai_client = OpenAI()

    print(f"\nFinDoc-Eval Harness")
    print(f"Document ID : {document_id}")
    print(f"API         : {api_url}")
    print(f"Questions   : {len(questions)}")
    print(f"Runs        : {runs}")
    print(f"Judge       : {JUDGE_MODEL} (temperature=0)")
    print("-" * 66)

    all_runs = []
    for r in range(runs):
        label = f"run {r + 1}/{runs}" if runs > 1 else "     "
        all_runs.append(run_pass(document_id, api_url, questions, openai_client, label))
        if runs > 1:
            score = sum(1 for x in all_runs[-1] if x["correct"])
            print(f"  → run {r + 1} scored {score}/{len(questions)}")
            print("-" * 66)

    write_benchmarks(all_runs, document_id)

    scores = [sum(1 for x in run if x["correct"]) for run in all_runs]
    n = len(questions)
    print(f"\nScores per run : {scores} (out of {n})")
    print(f"Reported       : {summarize_score(scores, n)}")
    print(f"\nResults written to BENCHMARKS.md")


def summarize_score(scores: list[int], n: int) -> str:
    """Format scores as a mean with a spread, e.g. '65% ± 5pp over 2 runs'."""
    pcts = [s / n * 100 for s in scores]
    mean = sum(pcts) / len(pcts)
    if len(pcts) == 1:
        return f"{mean:.0f}% (single run — no error bar)"
    spread = (max(pcts) - min(pcts)) / 2
    return f"{mean:.0f}% ± {spread:.0f}pp over {len(pcts)} runs"


def write_benchmarks(all_runs: list[list[dict]], document_id: str) -> None:
    runs = len(all_runs)
    n = len(all_runs[0])
    ids = [r["id"] for r in all_runs[0]]

    scores = [sum(1 for x in run if x["correct"]) for run in all_runs]
    correct_counts = {
        qid: sum(1 for run in all_runs for x in run if x["id"] == qid and x["correct"])
        for qid in ids
    }
    unstable = [qid for qid, c in correct_counts.items() if 0 < c < runs]

    hit_counts = {
        qid: sum(
            1 for run in all_runs for x in run
            if x["id"] == qid and x["top_similarity"] >= RETRIEVAL_HIT_THRESHOLD
        )
        for qid in ids
    }
    mean_hits = sum(hit_counts.values()) / runs

    latencies = [x["latency"] for run in all_runs for x in run]
    avg_latency = sum(latencies) / len(latencies)
    p95_latency = sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)]

    transport_errors = sum(1 for run in all_runs for x in run if x["transport_error"])

    lines = [
        "# Eval Benchmarks — NVIDIA FY2025 10-K",
        "",
        f"**Run:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"**Document ID:** `{document_id}`  ",
        f"**Judge model:** {JUDGE_MODEL} (`temperature=0`)  ",
        f"**Passes:** {runs}",
        "",
        "## Summary",
        "",
        "| Metric | Result |",
        "|---|---|",
        f"| **Answer Correctness** | **{summarize_score(scores, n)}** |",
        f"| Scores per pass | {', '.join(f'{s}/{n}' for s in scores)} |",
        f"| Unstable questions | {len(unstable)}/{n}"
        + (f" ({', '.join(unstable)})" if unstable else "")
        + " |",
        f"| Retrieval confidence ≥ {RETRIEVAL_HIT_THRESHOLD} | {mean_hits:.1f}/{n} — *proxy, not a retrieval metric* |",
        f"| Avg latency | {avg_latency:.1f}s |",
        f"| P95 latency | {p95_latency:.1f}s |",
        f"| Transport errors | {transport_errors} |",
        "",
    ]

    if runs > 1:
        lines += [
            "> The error bar is the headline number. LLM output is sampled, so a benchmark",
            "> without a spread cannot distinguish a real improvement from a re-roll.",
            "",
        ]

    lines += [
        "## Per-Question Results",
        "",
        f"| # | Question | Correct | Stable | Top Sim | Judge Reason (last pass) |",
        "|---|---|---|---|---|---|",
    ]

    last = all_runs[-1]
    for i, r in enumerate(last):
        qid = r["id"]
        c = correct_counts[qid]
        verdict = "PASS" if c == runs else ("FAIL" if c == 0 else "MIXED")
        stable = "—" if runs == 1 else ("yes" if c in (0, runs) else "**no**")
        q = r["question"][:52] + ("..." if len(r["question"]) > 52 else "")
        flag = "" if r["top_similarity"] >= RETRIEVAL_HIT_THRESHOLD else " [!]"
        lines.append(
            f"| {i + 1} | {q} | {verdict} ({c}/{runs}) | {stable} | "
            f"{r['top_similarity']:.2f}{flag} | {r['reason']} |"
        )

    by_tag: dict[str, list[int]] = {}
    for r in last:
        for tag in r["tags"]:
            by_tag.setdefault(tag, []).append(correct_counts[r["id"]])
    if by_tag:
        lines += ["", "## By Tag", "", "| Tag | Correct | Questions |", "|---|---|---|"]
        for tag in sorted(by_tag, key=lambda t: (sum(by_tag[t]) / (len(by_tag[t]) * runs))):
            vals = by_tag[tag]
            lines.append(
                f"| {tag} | {sum(vals)}/{len(vals) * runs} | {len(vals)} |"
            )

    failed = [r for r in last if correct_counts[r["id"]] < runs]
    if failed:
        lines += ["", "## Failed and Unstable Cases", ""]
        for r in failed:
            qid = r["id"]
            actual = r["actual"][:600] + ("..." if len(r["actual"]) > 600 else "")
            lines += [
                f"### {qid} — {correct_counts[qid]}/{runs} passes correct",
                "",
                f"**Question:** {r['question']}",
                "",
                f"**Expected:** {r['expected']}",
                "",
                f"**Actual (last pass):** {actual}",
                "",
                f"**Judge:** {r['reason']}",
                "",
                f"**Pages retrieved:** {r['retrieved_pages']}",
                "",
            ]

    Path("BENCHMARKS.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RAG eval harness against live API")
    parser.add_argument(
        "--document-id",
        required=True,
        help="UUID of the uploaded document (from the upload response)",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of full passes. >1 reports a mean and spread (default: 1)",
    )
    args = parser.parse_args()
    run_eval(args.document_id, args.api_url, args.runs)
