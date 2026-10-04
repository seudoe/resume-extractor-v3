# Eval report — baseline-llm — 2026-10-04T15:47:31

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
| summary | 100.0% | 1 |

## Entity sections

| Section | Precision | Recall | F1 | Omission rate |
|---|---|---|---|---|
| workHistory | 100.0% | 100.0% | 1.000 | 0.0% |
| education | 100.0% | 100.0% | 1.000 | 0.0% |
| projects | 77.8% | 77.8% | 0.778 | 22.2% |
| certifications | 100.0% | 100.0% | 1.000 | 0.0% |
| awards | 66.7% | 66.7% | 0.667 | 33.3% |

## Skills

Precision 92.9%, recall 100.0%, F1 0.960

## Hallucination / schema / determinism

- Hallucination rate (mean over scored files): 5.4%
- Schema validity: 100.0%
- Crash rate: 0.0%

## Worst files (lowest mean entity F1)

- `vedant_patil_pdf`: mean entity F1 0.667
- `sambhavmirajgaonkarresume_pdf`: mean entity F1 1.000
- `simple_hipster_cv_pdf`: mean entity F1 1.000

## Delta vs baseline-v2

- workHistory F1: 0.667 -> 1.000 (+0.333)
- education F1: 0.444 -> 1.000 (+0.556)
- projects F1: 0.000 -> 0.778 (+0.778)
- certifications F1: 0.333 -> 1.000 (+0.667)
- awards F1: 0.133 -> 0.667 (+0.533)
