# Block-level field accuracy — dev_lc (255 blocks) — 2026-10-05

## zero-shot @ confidence >= 0.5

| field | n | precision | recall | F1 |
|---|---|---|---|---|
| education.degree | 51 | 81.6% | 60.8% | 69.7% |
| education.field_of_study | 46 | 56.4% | 47.8% | 51.8% |
| education.institution | 63 | 77.2% | 69.8% | 73.3% |
| workHistory.company | 0 | 0.0% | 0.0% | 0.0% |
| workHistory.location | 0 | 0.0% | 0.0% | 0.0% |
| workHistory.title | 187 | 54.5% | 3.2% | 6.1% |

## zero-shot @ confidence >= 0.9

| field | n | precision | recall | F1 |
|---|---|---|---|---|
| education.degree | 51 | 83.3% | 49.0% | 61.7% |
| education.field_of_study | 46 | 58.8% | 21.7% | 31.7% |
| education.institution | 63 | 81.2% | 61.9% | 70.3% |
| workHistory.company | 0 | 0.0% | 0.0% | 0.0% |
| workHistory.location | 0 | 0.0% | 0.0% | 0.0% |
| workHistory.title | 187 | 33.3% | 1.1% | 2.1% |

## lora @ confidence >= 0.5

| field | n | precision | recall | F1 |
|---|---|---|---|---|
| education.degree | 51 | 86.0% | 84.3% | 85.1% |
| education.field_of_study | 46 | 80.0% | 87.0% | 83.3% |
| education.institution | 63 | 91.8% | 88.9% | 90.3% |
| workHistory.company | 0 | 0.0% | 0.0% | 0.0% |
| workHistory.location | 0 | 0.0% | 0.0% | 0.0% |
| workHistory.title | 187 | 83.5% | 43.3% | 57.0% |

## lora @ confidence >= 0.9

| field | n | precision | recall | F1 |
|---|---|---|---|---|
| education.degree | 51 | 87.0% | 78.4% | 82.5% |
| education.field_of_study | 46 | 80.0% | 52.2% | 63.2% |
| education.institution | 63 | 94.2% | 77.8% | 85.2% |
| workHistory.company | 0 | 0.0% | 0.0% | 0.0% |
| workHistory.location | 0 | 0.0% | 0.0% | 0.0% |
| workHistory.title | 187 | 91.5% | 40.1% | 55.8% |

