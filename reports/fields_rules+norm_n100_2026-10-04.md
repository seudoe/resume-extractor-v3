# Stage 10 field eval — rules+norm — 2026-10-04

## A. LiveCareer (weak HTML labels, held-out)

| metric | accuracy | n |
|---|---|---|
| edu.degree | 83.6% | 116 |
| edu.entry_recall | 55.4% | 222 |
| edu.school | 53.9% | 115 |
| edu.year | 82.3% | 96 |
| work.end | 96.6% | 381 |
| work.entry_recall | 83.5% | 473 |
| work.start | 96.9% | 385 |

work entries predicted 450 vs labelled 473 (title-correct matches 395)

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
| workHistory.type | 82.4% |
| workHistory.period.isCurrent | 98.0% |
| workHistory.period.start | 100.0% |
| workHistory.period.end | 100.0% |
| education.institution | 82.8% |
| education.field.type | 57.8% |
| education.field.course | 52.1% |
| education.period.end | 0.0% |
| projects.title | 91.3% |
| certifications.name | 77.8% |
| certifications.issuer | 0.0% |
| certifications.type | 0.0% |
| awards.name | 52.9% |
| awards.issuingBody | 17.6% |

## C. Skills names vs LLM JSONs (AAA)

| variant | P | R | F1 |
|---|---|---|---|
| listed + tech lines | 63.2% | 80.2% | 69.0% |
| + bullet mentions | 63.2% | 80.2% | 69.0% |
