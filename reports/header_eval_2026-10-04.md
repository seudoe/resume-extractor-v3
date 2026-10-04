# Header eval — 2026-10-04

Gold: 32 resumes, status **drafted** (verified_by: None). **Unverified gold: not a reported accuracy.**

### rx3 rules (ingest + layout + header)

| Field | Accuracy | N (gold has value) | Spurious (gold empty) |
|---|---|---|---|
| name | 100.0% | 32 | 0 |
| email | 100.0% | 32 | 0 |
| phone_no | 100.0% | 26 | 0 |
| linkedin | 95.2% | 21 | 0 |
| github_profile | 94.1% | 17 | 0 |
| city | 91.3% | 23 | 0 |
| state | 100.0% | 12 | 0 |
| country | 100.0% | 7 | 0 |
| postal_code | 100.0% | 4 | 0 |
| extra_links (P / R) | 100.0% / 100.0% | 26 | 0 |

### LLM JSONs (reference only)

| Field | Accuracy | N (gold has value) | Spurious (gold empty) |
|---|---|---|---|
| name | 100.0% | 32 | 0 |
| email | 100.0% | 32 | 0 |
| phone_no | 88.5% | 26 | 0 |
| linkedin | 52.4% | 21 | 0 |
| github_profile | 41.2% | 17 | 1 |
| city | 100.0% | 23 | 1 |
| state | 100.0% | 12 | 5 |
| country | 100.0% | 7 | 17 |
| postal_code | 100.0% | 4 | 0 |
| extra_links (P / R) | 50.0% / 19.2% | 26 | 5 |

### Targets (PROMPT.md §4.7), rx3 rules
- name: 100.0% vs target 97% — MET
- email: 100.0% vs target 98% — MET
- phone_no: 100.0% vs target 98% — MET
- linkedin: 95.2% vs target 98% — MISSED
- github_profile: 94.1% vs target 98% — MISSED

### rx3 failures (predicted vs gold)

- `Data Analyst - ats compatible` **city**: predicted `` / gold `Bay Area`
- `Simple_Hipster_CV` **linkedin**: predicted `None` / gold `alexjohnson`
- `Simple_Hipster_CV` **github_profile**: predicted `None` / gold `alexjohnson`
- `social-media-strategist2 - Template 16 ` **city**: predicted `` / gold `Grand Rapids`
