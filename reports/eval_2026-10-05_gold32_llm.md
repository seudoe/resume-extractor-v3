# Eval report — baseline-llm — 2026-10-05T20:36:26

Gold set: 32 drafted/verified files (0 verified, 32 draft/unverified), plus 1 not yet hand-labelled (excluded from scoring).
Candidate: 32/32 gold files had a matching candidate prediction.

> **All gold used here is unverified draft** (Checkpoint 4B hasn't happened yet). Per PROMPT.md §1.5/§4.1, these numbers are NOT to be treated as reported accuracy until the user verifies the gold labels.

## Scalar fields

| Field | Accuracy | N applicable |
|---|---|---|
| metaDetails.name | 100.0% | 32 |
| metaDetails.email | 100.0% | 32 |
| metaDetails.linkedin | 38.1% | 21 |
| metaDetails.github_profile | 23.5% | 17 |
| metaDetails.phone_no | 100.0% | 26 |
| summary | 100.0% | 7 |

## Entity sections

| Section | Precision | Recall | F1 | Omission rate |
|---|---|---|---|---|
| workHistory | 96.9% | 99.4% | 0.965 | 0.6% |
| education | 100.0% | 100.0% | 1.000 | 0.0% |
| projects | 96.4% | 96.4% | 0.964 | 3.6% |
| certifications | 98.4% | 98.4% | 0.984 | 1.6% |
| awards | 66.4% | 60.6% | 0.612 | 39.4% |

## Skills

Precision 91.0%, recall 91.9%, F1 0.899

## Hallucination / schema / determinism

- Hallucination rate (mean over scored files): 5.5%
- Schema validity: 90.6%
- Crash rate: 0.0%

## Worst files (lowest mean entity F1)

- `vickyresume_apr26_pdf`: mean entity F1 0.600
- `vedant_patil_pdf`: mean entity F1 0.667
- `resume_asif_4_0_pdf`: mean entity F1 0.750
- `entry_level_software_engineer_resume_pdf`: mean entity F1 0.767
- `26_9_30_csihead_pdf`: mean entity F1 0.800
- `aagam_esume_apr26_pdf`: mean entity F1 0.800
- `aryanniravshah_anirudhfr_resume_apr2026_pdf`: mean entity F1 0.800
- `mohd_asifshershahvadi_internshalaresume_pdf`: mean entity F1 0.800
- `resume_asif_goal_2_pdf`: mean entity F1 0.800
- `resume_asif_goal_intgoog_mar26_pdf`: mean entity F1 0.800

## Delta vs baseline-v3

- workHistory F1: 0.801 -> 0.965 (+0.165)
- education F1: 0.827 -> 1.000 (+0.173)
- projects F1: 0.755 -> 0.964 (+0.209)
- certifications F1: 0.677 -> 0.984 (+0.307)
- awards F1: 0.635 -> 0.612 (-0.023)
