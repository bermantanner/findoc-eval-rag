# Eval Benchmarks — NVIDIA FY2025 10-K

**Run:** 2026-08-24 11:09  
**Document ID:** `752be9f8-1141-4338-9992-348c1642aaaf`  
**Judge model:** gpt-4o-mini (`temperature=0`)  
**Passes:** 3

## Summary

| Metric | Result |
|---|---|
| **Answer Correctness** | **60% ± 0pp over 3 runs** |
| Scores per pass | 6/10, 6/10, 6/10 |
| Unstable questions | 0/10 |
| Retrieval confidence ≥ 0.6 | 9.0/10 — *proxy, not a retrieval metric* |
| Avg latency | 2.4s |
| P95 latency | 6.1s |
| Transport errors | 0 |

> The error bar is the headline number. LLM output is sampled, so a benchmark
> without a spread cannot distinguish a real improvement from a re-roll.

## Per-Question Results

| # | Question | Correct | Stable | Top Sim | Judge Reason (last pass) |
|---|---|---|---|---|---|
| 1 | What was NVIDIA's total revenue for fiscal year 2025... | PASS (3/3) | yes | 0.69 | The actual answer correctly states NVIDIA's total revenue for fiscal year 2025 in a different format, which matches the expected answer within normal rounding. |
| 2 | What was NVIDIA's Data Center segment revenue in fis... | FAIL (0/3) | yes | 0.67 | The actual answer incorrectly states 'Insufficient data' when a correct answer exists. |
| 3 | What was NVIDIA's Gaming segment revenue in fiscal y... | FAIL (0/3) | yes | 0.68 | The actual answer indicates a lack of data despite a correct answer existing. |
| 4 | What was NVIDIA's net income for fiscal year 2025? | PASS (3/3) | yes | 0.72 | The actual answer correctly states NVIDIA's net income in a different format that matches the expected answer within normal rounding. |
| 5 | What was NVIDIA's gross margin percentage for fiscal... | PASS (3/3) | yes | 0.66 | The actual answer provides the correct gross margin percentage with appropriate precision. |
| 6 | Who is the President and Chief Executive Officer of ... | PASS (3/3) | yes | 0.71 | The actual answer correctly identifies Jensen Huang as the President and Chief Executive Officer of NVIDIA, using a different name format. |
| 7 | Where is NVIDIA's principal executive office located... | FAIL (0/3) | yes | 0.57 [!] | The actual answer incorrectly states 'Insufficient data' when a correct answer exists. |
| 8 | What were NVIDIA's research and development expenses... | PASS (3/3) | yes | 0.68 | The actual answer correctly states the R&D expenses in fiscal year 2025, matching the expected answer when converted to the same unit. |
| 9 | How many full-time employees did NVIDIA have at the ... | PASS (3/3) | yes | 0.71 | The actual answer correctly states the number of full-time employees as approximately 36,000, matching the expected answer. |
| 10 | What manufacturing risk does NVIDIA identify related... | FAIL (0/3) | yes | 0.62 | The actual answer provides a detailed list of risks but does not mention the specific consequences of these risks on NVIDIA's ability to supply products and the potential harm to its business. |

## By Tag

| Tag | Correct | Questions |
|---|---|---|
| segments | 0/6 | 2 |
| risk-factors | 0/3 | 1 |
| supply-chain | 0/3 | 1 |
| company-info | 3/6 | 2 |
| financials | 12/18 | 6 |
| revenue | 3/3 | 1 |
| profitability | 6/6 | 2 |
| leadership | 3/3 | 1 |
| expenses | 3/3 | 1 |

## Failed and Unstable Cases

### nvda_002 — 0/3 passes correct

**Question:** What was NVIDIA's Data Center segment revenue in fiscal year 2025?

**Expected:** $115.19 billion

**Actual (last pass):** Insufficient data in source document.

**Judge:** The actual answer incorrectly states 'Insufficient data' when a correct answer exists.

**Pages retrieved:** [78, 79, 41, 6, 36]

### nvda_003 — 0/3 passes correct

**Question:** What was NVIDIA's Gaming segment revenue in fiscal year 2025?

**Expected:** $11.35 billion

**Actual (last pass):** Insufficient data in source document.

**Judge:** The actual answer indicates a lack of data despite a correct answer existing.

**Pages retrieved:** [6, 78, 41, 38, 36]

### nvda_007 — 0/3 passes correct

**Question:** Where is NVIDIA's principal executive office located?

**Expected:** 2788 San Tomas Expressway, Santa Clara, California 95051

**Actual (last pass):** Insufficient data in source document.

**Judge:** The actual answer incorrectly states 'Insufficient data' when a correct answer exists.

**Pages retrieved:** [5, 11, 36, 13, 4]

### nvda_010 — 0/3 passes correct

**Question:** What manufacturing risk does NVIDIA identify related to its reliance on third-party suppliers?

**Expected:** NVIDIA relies on a limited number of third-party manufacturers, including TSMC, to produce its semiconductors. Disruptions to these manufacturing relationships — due to geopolitical tensions, natural disasters, or capacity constraints — could impair NVIDIA's ability to supply products and materially harm its business.

**Actual (last pass):** NVIDIA identifies several manufacturing risks related to its reliance on third-party suppliers, including:

- Lack of guaranteed supply of wafer, component, and capacity.
- Decommitment by suppliers.
- Potential higher wafer and component prices resulting from incorrectly estimating demand and failing to place orders with sufficient quantities or timely.
- Failure by foundries or contract manufacturers to procure raw materials or provide adequate levels of manufacturing or test capacity for products.
- Failure by foundries to develop, obtain, or successfully implement high-quality process tech...

**Judge:** The actual answer provides a detailed list of risks but does not mention the specific consequences of these risks on NVIDIA's ability to supply products and the potential harm to its business.

**Pages retrieved:** [18, 21, 28, 36, 11]

