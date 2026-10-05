# Eval report — baseline-v3 — 2026-10-05T19:04:01

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
| workHistory | 84.3% | 80.0% | 0.801 | 20.0% |
| education | 80.5% | 87.5% | 0.827 | 12.5% |
| projects | 85.1% | 74.0% | 0.755 | 26.0% |
| certifications | 84.4% | 67.2% | 0.677 | 32.8% |
| awards | 83.0% | 60.7% | 0.635 | 39.3% |

## Skills

Precision 65.9%, recall 83.2%, F1 0.726

## Hallucination / schema / determinism

- Hallucination rate (mean over scored files): 3.1%
- Schema validity: 100.0%
- Crash rate: 0.0%

## Worst files (lowest mean entity F1)

- `simple_hipster_cv_pdf`: mean entity F1 0.200
- `entry_level_software_engineer_resume_pdf`: mean entity F1 0.460
- `jenil_shah_resume_12_pdf`: mean entity F1 0.500
- `altacv_template_pdf`: mean entity F1 0.520
- `data_analyst_ats_compatible_pdf`: mean entity F1 0.533
- `resume_block_pdf`: mean entity F1 0.533
- `aryanniravshah_anirudhfr_resume_apr2026_pdf`: mean entity F1 0.600
- `mohd_asifshershahvadi_internshalaresume_pdf`: mean entity F1 0.600
- `vedant_patil_pdf`: mean entity F1 0.600
- `entry_level_data_analyst2_template_17_pdf`: mean entity F1 0.627

## Delta vs baseline-rx3

- workHistory F1: 0.667 -> 0.801 (+0.134)
- education F1: 0.667 -> 0.827 (+0.161)
- projects F1: 0.333 -> 0.755 (+0.422)
- certifications F1: 0.333 -> 0.677 (+0.344)
- awards F1: 0.200 -> 0.635 (+0.435)
