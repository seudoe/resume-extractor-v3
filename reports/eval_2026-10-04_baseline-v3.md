# Eval report — baseline-v3 — 2026-10-04T22:20:18

Gold set: 3 drafted/verified files (0 verified, 3 draft/unverified), plus 28 not yet hand-labelled (excluded from scoring).
Candidate: 3/3 gold files had a matching candidate prediction.

> **All gold used here is unverified draft** (Checkpoint 4B hasn't happened yet). Per PROMPT.md §1.5/§4.1, these numbers are NOT to be treated as reported accuracy until the user verifies the gold labels.

## Scalar fields

| Field | Accuracy | N applicable |
|---|---|---|
| metaDetails.name | 100.0% | 3 |
| metaDetails.email | 100.0% | 3 |
| metaDetails.phone_no | 100.0% | 3 |
| metaDetails.linkedin | 50.0% | 2 |
| metaDetails.github_profile | 50.0% | 2 |
| summary | 0.0% | 1 |

## Entity sections

| Section | Precision | Recall | F1 | Omission rate |
|---|---|---|---|---|
| workHistory | 100.0% | 66.7% | 0.667 | 33.3% |
| education | 66.7% | 66.7% | 0.667 | 33.3% |
| projects | 66.7% | 33.3% | 0.333 | 66.7% |
| certifications | 33.3% | 33.3% | 0.333 | 66.7% |
| awards | 66.7% | 14.3% | 0.200 | 85.7% |

## Skills

Precision 52.7%, recall 67.0%, F1 0.575

## Hallucination / schema / determinism

- Hallucination rate (mean over scored files): 3.0%
- Schema validity: 100.0%
- Crash rate: 0.0%

## Worst files (lowest mean entity F1)

- `simple_hipster_cv_pdf`: mean entity F1 0.000
- `vedant_patil_pdf`: mean entity F1 0.600
- `sambhavmirajgaonkarresume_pdf`: mean entity F1 0.720

## Delta vs baseline-rx3

- workHistory F1: 0.667 -> 0.667 (+0.000)
- education F1: 0.667 -> 0.667 (+0.000)
- projects F1: 0.333 -> 0.333 (+0.000)
- certifications F1: 0.333 -> 0.333 (+0.000)
- awards F1: 0.200 -> 0.200 (+0.000)
