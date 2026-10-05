# Eval report — baseline-v3 — 2026-10-05T13:26:49

Gold set: 32 drafted/verified files (0 verified, 32 draft/unverified), plus 1 not yet hand-labelled (excluded from scoring).
Candidate: 32/32 gold files had a matching candidate prediction.

> **All gold used here is unverified draft** (Checkpoint 4B hasn't happened yet). Per PROMPT.md §1.5/§4.1, these numbers are NOT to be treated as reported accuracy until the user verifies the gold labels.

## Scalar fields

| Field | Accuracy | N applicable |
|---|---|---|
| metaDetails.name | 100.0% | 32 |
| metaDetails.email | 100.0% | 32 |
| metaDetails.linkedin | 66.7% | 21 |
| metaDetails.github_profile | 76.5% | 17 |
| metaDetails.phone_no | 100.0% | 26 |
| summary | 71.4% | 7 |

## Entity sections

| Section | Precision | Recall | F1 | Omission rate |
|---|---|---|---|---|
| workHistory | 83.2% | 77.9% | 0.788 | 22.1% |
| education | 78.7% | 87.8% | 0.818 | 12.2% |
| projects | 86.2% | 69.0% | 0.723 | 31.0% |
| certifications | 84.4% | 67.2% | 0.677 | 32.8% |
| awards | 83.0% | 60.7% | 0.635 | 39.3% |

## Skills

Precision 65.9%, recall 83.2%, F1 0.726

## Hallucination / schema / determinism

- Hallucination rate (mean over scored files): 3.0%
- Schema validity: 100.0%
- Crash rate: 0.0%

## Worst files (lowest mean entity F1)

- `simple_hipster_cv_pdf`: mean entity F1 0.200
- `entry_level_software_engineer_resume_pdf`: mean entity F1 0.460
- `jenil_shah_resume_12_pdf`: mean entity F1 0.500
- `altacv_template_pdf`: mean entity F1 0.520
- `data_analyst_ats_compatible_pdf`: mean entity F1 0.533
- `entry_level_software_engineer2_template_17_pdf`: mean entity F1 0.547
- `aryanniravshah_anirudhfr_resume_apr2026_pdf`: mean entity F1 0.550
- `resume_block_pdf`: mean entity F1 0.600
- `vedant_patil_pdf`: mean entity F1 0.600
- `entry_level_data_analyst2_template_17_pdf`: mean entity F1 0.627

## Delta vs baseline-rx3

- workHistory F1: 0.667 -> 0.788 (+0.122)
- education F1: 0.667 -> 0.818 (+0.151)
- projects F1: 0.333 -> 0.723 (+0.390)
- certifications F1: 0.333 -> 0.677 (+0.344)
- awards F1: 0.200 -> 0.635 (+0.435)
