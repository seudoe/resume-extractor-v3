# Stage 10 field eval — rules — 2026-10-04

## A. LiveCareer (weak HTML labels, held-out)

| metric | accuracy | n |
|---|---|---|
| edu.degree | 81.2% | 117 |
| edu.entry_recall | 54.3% | 230 |
| edu.school | 43.4% | 113 |
| edu.year | 85.6% | 90 |
| work.end | 99.0% | 395 |
| work.entry_recall | 82.9% | 514 |
| work.start | 99.5% | 401 |

work entries predicted 464 vs labelled 514 (title-correct matches 426)

## B. AAA agreement with LLM JSONs

32 AAA resumes vs LLM JSON (reference is LLM output, not gold)

| section | P | R | F1 |
|---|---|---|---|
| workHistory | 63.1% | 56.4% | 56.6% |
| education | 72.3% | 80.7% | 75.1% |
| projects | 87.2% | 70.3% | 73.5% |
| certifications | 84.4% | 67.2% | 67.7% |
| awards | 62.5% | 46.7% | 45.6% |

| sub-field | acc |
|---|---|
| workHistory.company | 57.6% |
| workHistory.title | 78.0% |
| workHistory.location | 8.3% |
| workHistory.type | 70.6% |
| workHistory.period.isCurrent | 98.0% |
| workHistory.period.start | 100.0% |
| workHistory.period.end | 100.0% |
| education.institution | 82.8% |
| education.field.type | 59.9% |
| education.field.course | 52.1% |
| education.period.end | 0.0% |
| projects.title | 91.3% |
| certifications.name | 77.8% |
| certifications.issuer | 0.0% |
| certifications.type | 0.0% |
| awards.name | 52.9% |
| awards.issuingBody | 17.6% |
