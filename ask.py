#!/usr/bin/env python3
import json
import sys
import urllib.request

API_URL = "http://localhost:8000/api/v1/query?format=plain"
API_KEY = "dev-secret-key"

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
            print("\n" + resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error {e.code}: {e.read().decode()}")
