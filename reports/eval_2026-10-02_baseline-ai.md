# Eval report — baseline-ai — 2026-10-02T19:21:46

Gold set: 3 drafted/verified files (0 verified, 3 draft/unverified), plus 28 not yet hand-labelled (excluded from scoring).
Candidate: 2/3 gold files had a matching candidate prediction.

> **All gold used here is unverified draft** (Checkpoint 4B hasn't happened yet). Per PROMPT.md §1.5/§4.1, these numbers are NOT to be treated as reported accuracy until the user verifies the gold labels.

## Scalar fields

| Field | Accuracy | N applicable |
|---|---|---|
| metaDetails.name | 50.0% | 2 |
| metaDetails.email | 0.0% | 2 |
| metaDetails.phone_no | 50.0% | 2 |
| metaDetails.linkedin | 0.0% | 1 |
| metaDetails.github_profile | 100.0% | 1 |

## Entity sections

| Section | Precision | Recall | F1 | Omission rate |
|---|---|---|---|---|
| workHistory | 50.0% | 100.0% | 0.500 | 0.0% |
| education | 0.0% | 0.0% | 0.000 | 100.0% |
| projects | 0.0% | 0.0% | 0.000 | 100.0% |
| certifications | 100.0% | 50.0% | 0.500 | 50.0% |
| awards | 33.3% | 28.6% | 0.308 | 71.4% |

## Skills

Precision 49.5%, recall 30.1%, F1 0.372

## Hallucination / schema / determinism

- Hallucination rate (mean over scored files): 72.0%
- Schema validity: 0.0%
- Crash rate: 33.3%

## Worst files (lowest mean entity F1)

- `vedant_patil_pdf`: mean entity F1 0.200
- `sambhavmirajgaonkarresume_pdf`: mean entity F1 0.323

## Delta vs baseline-v2

- workHistory F1: 0.667 -> 0.500 (-0.167)
- education F1: 0.444 -> 0.000 (-0.444)
- projects F1: 0.000 -> 0.000 (+0.000)
- certifications F1: 0.333 -> 0.500 (+0.167)
- awards F1: 0.133 -> 0.308 (+0.174)
