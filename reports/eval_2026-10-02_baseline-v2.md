# Eval report — baseline-v2 — 2026-10-02T19:21:45

Gold set: 3 drafted/verified files (0 verified, 3 draft/unverified), plus 28 not yet hand-labelled (excluded from scoring).
Candidate: 3/3 gold files had a matching candidate prediction.

> **All gold used here is unverified draft** (Checkpoint 4B hasn't happened yet). Per PROMPT.md §1.5/§4.1, these numbers are NOT to be treated as reported accuracy until the user verifies the gold labels.

## Scalar fields

| Field | Accuracy | N applicable |
|---|---|---|
| metaDetails.name | 33.3% | 3 |
| metaDetails.email | 66.7% | 3 |
| metaDetails.phone_no | 66.7% | 3 |
| metaDetails.linkedin | 50.0% | 2 |
| metaDetails.github_profile | 50.0% | 2 |
| summary | 0.0% | 1 |

## Entity sections

| Section | Precision | Recall | F1 | Omission rate |
|---|---|---|---|---|
| workHistory | 66.7% | 66.7% | 0.667 | 33.3% |
| education | 100.0% | 33.3% | 0.444 | 66.7% |
| projects | 0.0% | 0.0% | 0.000 | 100.0% |
| certifications | 66.7% | 33.3% | 0.333 | 66.7% |
| awards | 41.7% | 33.3% | 0.133 | 66.7% |

## Skills

Precision 22.2%, recall 18.2%, F1 0.200

## Hallucination / schema / determinism

- Hallucination rate (mean over scored files): 49.1%
- Schema validity: 100.0%
- Crash rate: 0.0%

## Worst files (lowest mean entity F1)

- `simple_hipster_cv_pdf`: mean entity F1 0.000
- `sambhavmirajgaonkarresume_pdf`: mean entity F1 0.413
- `vedant_patil_pdf`: mean entity F1 0.533
