# Stage 10 field eval — combined+norm — 2026-10-04

## A. LiveCareer (weak HTML labels, held-out)

| metric | accuracy | n |
|---|---|---|
| edu.degree | 75.0% | 12 |
| edu.entry_recall | 43.8% | 32 |
| edu.school | 66.7% | 12 |
| edu.year | 58.3% | 12 |
| work.end | 98.2% | 56 |
| work.entry_recall | 84.5% | 71 |
| work.start | 98.3% | 58 |

work entries predicted 68 vs labelled 71 (title-correct matches 60)

## B. AAA agreement with LLM JSONs

32 AAA resumes vs LLM JSON (reference is LLM output, not gold)

| section | P | R | F1 |
|---|---|---|---|
| workHistory | 83.2% | 75.4% | 76.0% |
| education | 78.4% | 87.8% | 81.5% |
| projects | 87.2% | 70.3% | 73.5% |
| certifications | 84.4% | 67.2% | 67.7% |
| awards | 62.5% | 46.7% | 45.6% |

| sub-field | acc |
|---|---|
| workHistory.company | 84.3% |
| workHistory.title | 78.2% |
| workHistory.location | 12.5% |
| workHistory.type | 76.5% |
| workHistory.period.isCurrent | 100.0% |
| workHistory.period.start | 100.0% |
| workHistory.period.end | 100.0% |
| education.institution | 89.8% |
| education.field.type | 60.9% |
| education.field.course | 61.5% |
| education.period.end | 0.0% |
| projects.title | 91.3% |
| certifications.name | 77.8% |
| certifications.issuer | 0.0% |
| certifications.type | 0.0% |
| awards.name | 52.9% |
| awards.issuingBody | 17.6% |
