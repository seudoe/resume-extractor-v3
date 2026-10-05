# Block-level field accuracy — test_synth (1899 blocks) — 2026-10-05

## zero-shot @ confidence >= 0.5

| field | n | precision | recall | F1 |
|---|---|---|---|---|
| education.degree | 676 | 74.4% | 61.4% | 67.3% |
| education.field_of_study | 646 | 91.7% | 85.9% | 88.7% |
| education.institution | 676 | 79.4% | 76.6% | 78.0% |
| workHistory.company | 1223 | 87.1% | 79.8% | 83.3% |
| workHistory.location | 974 | 59.2% | 46.6% | 52.2% |
| workHistory.title | 1223 | 80.8% | 63.9% | 71.4% |

## zero-shot @ confidence >= 0.9

| field | n | precision | recall | F1 |
|---|---|---|---|---|
| education.degree | 676 | 85.8% | 49.0% | 62.3% |
| education.field_of_study | 646 | 94.7% | 76.9% | 84.9% |
| education.institution | 676 | 83.0% | 75.0% | 78.8% |
| workHistory.company | 1223 | 91.7% | 75.2% | 82.7% |
| workHistory.location | 974 | 71.4% | 16.9% | 27.4% |
| workHistory.title | 1223 | 92.7% | 49.1% | 64.2% |

## lora @ confidence >= 0.5

| field | n | precision | recall | F1 |
|---|---|---|---|---|
| education.degree | 676 | 98.8% | 85.9% | 91.9% |
| education.field_of_study | 646 | 94.8% | 87.0% | 90.7% |
| education.institution | 676 | 98.2% | 90.1% | 94.0% |
| workHistory.company | 1223 | 97.6% | 91.4% | 94.4% |
| workHistory.location | 974 | 68.3% | 64.7% | 66.4% |
| workHistory.title | 1223 | 99.2% | 88.7% | 93.7% |

## lora @ confidence >= 0.9

| field | n | precision | recall | F1 |
|---|---|---|---|---|
| education.degree | 676 | 99.5% | 84.9% | 91.6% |
| education.field_of_study | 646 | 95.2% | 82.8% | 88.6% |
| education.institution | 676 | 99.3% | 89.6% | 94.2% |
| workHistory.company | 1223 | 98.7% | 89.8% | 94.0% |
| workHistory.location | 974 | 70.6% | 62.8% | 66.5% |
| workHistory.title | 1223 | 99.7% | 84.4% | 91.4% |

