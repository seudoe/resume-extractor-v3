# Stage 10 field eval — gliner+norm — 2026-10-04

## A. LiveCareer (weak HTML labels, held-out)

| metric | accuracy | n |
|---|---|---|
| edu.degree | 72.1% | 147 |
| edu.entry_recall | 70.7% | 222 |
| edu.school | 81.2% | 144 |
| edu.year | 77.7% | 121 |
| work.end | 96.6% | 354 |
| work.entry_recall | 76.1% | 473 |
| work.start | 96.9% | 358 |

work entries predicted 450 vs labelled 473 (title-correct matches 360)

## B. AAA agreement with LLM JSONs

32 AAA resumes vs LLM JSON (reference is LLM output, not gold)

| section | P | R | F1 |
|---|---|---|---|
| workHistory | 80.1% | 72.3% | 72.9% |
| education | 60.3% | 63.8% | 61.4% |
| projects | 87.2% | 70.3% | 73.5% |
| certifications | 84.4% | 67.2% | 67.7% |
| awards | 62.5% | 46.7% | 45.6% |

| sub-field | acc |
|---|---|
| workHistory.company | 78.2% |
| workHistory.title | 83.3% |
| workHistory.location | 31.1% |
| workHistory.type | 82.4% |
| workHistory.period.isCurrent | 98.0% |
| workHistory.period.start | 100.0% |
| workHistory.period.end | 100.0% |
| education.institution | 69.0% |
| education.field.type | 49.2% |
| education.field.course | 60.9% |
| education.period.end | 0.0% |
| projects.title | 91.3% |
| certifications.name | 77.8% |
| certifications.issuer | 0.0% |
| certifications.type | 0.0% |
| awards.name | 52.9% |
| awards.issuingBody | 17.6% |
