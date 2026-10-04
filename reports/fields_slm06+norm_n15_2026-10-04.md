# Stage 10 field eval — slm06+norm — 2026-10-04

## A. LiveCareer (weak HTML labels, held-out)

| metric | accuracy | n |
|---|---|---|
| edu.degree | 52.9% | 17 |
| edu.entry_recall | 62.5% | 32 |
| edu.school | 37.5% | 16 |
| edu.year | 58.8% | 17 |
| work.end | 100.0% | 31 |
| work.entry_recall | 47.9% | 71 |
| work.start | 100.0% | 33 |

work entries predicted 68 vs labelled 71 (title-correct matches 34)

## B. AAA agreement with LLM JSONs

32 AAA resumes vs LLM JSON (reference is LLM output, not gold)

| section | P | R | F1 |
|---|---|---|---|
| workHistory | 58.1% | 51.8% | 51.8% |
| education | 66.9% | 76.6% | 70.1% |
| projects | 87.2% | 70.3% | 73.5% |
| certifications | 84.4% | 67.2% | 67.7% |
| awards | 62.5% | 46.7% | 45.6% |

| sub-field | acc |
|---|---|
| workHistory.company | 51.7% |
| workHistory.title | 82.0% |
| workHistory.location | 47.8% |
| workHistory.type | 82.4% |
| workHistory.period.isCurrent | 98.0% |
| workHistory.period.start | 100.0% |
| workHistory.period.end | 100.0% |
| education.institution | 84.4% |
| education.field.type | 23.1% |
| education.field.course | 47.8% |
| education.period.end | 0.0% |
| projects.title | 91.3% |
| certifications.name | 77.8% |
| certifications.issuer | 0.0% |
| certifications.type | 0.0% |
| awards.name | 52.9% |
| awards.issuingBody | 17.6% |
