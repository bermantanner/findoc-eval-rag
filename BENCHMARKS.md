# Eval Benchmarks — NVIDIA FY2025 10-K

**Run:** 2026-08-24 10:40  
**Document ID:** `752be9f8-1141-4338-9992-348c1642aaaf`  
**Judge model:** gpt-4o-mini  
**Retrieval hit threshold:** similarity ≥ 0.6

## Summary

| Metric | Result |
|---|---|
| Answer Correctness | 7/10 (70%) |
| Retrieval Hit Rate | 9/10 (90%) |
| Avg Latency | 1.8s |
| P95 Latency | 1.9s |

## Per-Question Results

| # | Question | Correct? | Top Sim | Latency | Judge Reason |
|---|---|---|---|---|---|
| 1 | What was NVIDIA's total revenue for fiscal year 2025? | ✔️ | 0.69 | 1.5s | The actual answer correctly states NVIDIA's total revenue for fiscal year 2025 in a different format that matches the expected answer within normal rounding. |
| 2 | What was NVIDIA's Data Center segment revenue in fiscal... | ✖️ | 0.67 | 1.6s | The actual answer states 'Insufficient data' while a correct answer exists. |
| 3 | What was NVIDIA's Gaming segment revenue in fiscal year... | ✖️ | 0.68 | 1.3s | The actual answer incorrectly states 'Insufficient data' when a correct answer exists. |
| 4 | What was NVIDIA's net income for fiscal year 2025? | ✔️ | 0.72 | 1.3s | The actual answer correctly states NVIDIA's net income in a different format that matches the expected answer within normal rounding. |
| 5 | What was NVIDIA's gross margin percentage for fiscal ye... | ✔️ | 0.66 | 1.2s | The actual answer provides the correct gross margin percentage of 75.0%, which matches the expected answer. |
| 6 | Who is the President and Chief Executive Officer of NVI... | ✔️ | 0.71 | 1.1s | The actual answer correctly identifies Jensen Huang as the President and Chief Executive Officer of NVIDIA, using a different but acceptable name format. |
| 7 | Where is NVIDIA's principal executive office located? | ✖️ | 0.57 [!] | 1.9s | The actual answer incorrectly states 'Insufficient data' when a correct answer exists. |
| 8 | What were NVIDIA's research and development expenses in... | ✔️ | 0.68 | 1.5s | The actual answer correctly states the R&D expenses in fiscal year 2025, matching the expected answer when converted to the same unit. |
| 9 | How many full-time employees did NVIDIA have at the end... | ✔️ | 0.71 | 1.2s | The actual answer correctly states the number of full-time employees as approximately 36,000, matching the expected answer. |
| 10 | What manufacturing risk does NVIDIA identify related to... | ✔️ | 0.62 | 5.3s | The actual answer accurately identifies the risks associated with NVIDIA's reliance on third-party suppliers and provides detailed context that aligns with the expected answer. |

## Failed Cases

### nvda_002

**Question:** What was NVIDIA's Data Center segment revenue in fiscal year 2025?

**Expected:** $115.19 billion

**Actual:** Insufficient data in source document.

**Judge:** The actual answer states 'Insufficient data' while a correct answer exists.

### nvda_003

**Question:** What was NVIDIA's Gaming segment revenue in fiscal year 2025?

**Expected:** $11.35 billion

**Actual:** Insufficient data in source document.

**Judge:** The actual answer incorrectly states 'Insufficient data' when a correct answer exists.

### nvda_007

**Question:** Where is NVIDIA's principal executive office located?

**Expected:** 2788 San Tomas Expressway, Santa Clara, California 95051

**Actual:** Insufficient data in source document.

**Judge:** The actual answer incorrectly states 'Insufficient data' when a correct answer exists.

