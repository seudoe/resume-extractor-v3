# Section eval — 2026-10-04

Gold: 32 resumes, status **drafted** (verified_by: None). **Unverified gold: not a reported accuracy.** Rules were tuned on these resumes (development set).

- Heading detection: precision 98.0%, recall 99.0% (tp 194, fp 4, fn 2)
- Canonical section on matched headings: 191/194 = 98.5%
- **Line-level section assignment: 1450/1506 = 96.3%** (target 95%: MET)
- Unlocatable gold headings (no matching line): 1

### Worst files (line accuracy)

- `Simple_Hipster_CV`: 55.3% of 76 lines
- `Entry_Level_Resume_Template__LaTeX_`: 88.3% of 60 lines
- `director-of-business-development2  - Template 15`: 93.8% of 64 lines
- `AltaCV_Template`: 94.9% of 79 lines
- `resume-block`: 95.2% of 63 lines
- `entry-level-data-analyst2 - Template 17`: 98.4% of 61 lines
- `entry-level-software-engineer2 - Template 17`: 98.4% of 61 lines
- `chief-information-officer-cio3  - Template 15`: 98.4% of 62 lines
- `data-analyst2 - Template 18`: 98.4% of 64 lines
- `26-9-30-csiHead`: 100.0% of 37 lines

### Top line confusions (gold -> predicted)

- skills -> other: 11 lines
- certifications -> other: 9 lines
- workHistory -> publications: 7 lines
- workHistory -> header: 7 lines
- summary -> other: 6 lines
- skills -> None: 5 lines
- publications -> other: 3 lines
- other -> certifications: 3 lines
- other -> summary: 3 lines
- other -> projects: 1 lines

### Heading errors

- `AltaCV_Template` SPURIOUS heading 'opensource' -> projects
- `Entry_Level_Resume_Template__LaTeX_` heading 'research' gold=workHistory pred=publications
- `Simple_Hipster_CV` MISSED heading 'shortresum' (workHistory)
- `Simple_Hipster_CV` heading 'specialization' gold=skills pred=other
- `Simple_Hipster_CV` heading 'curriculum' gold=projects pred=other
- `director-of-business-development2  - Template 15` SPURIOUS heading 'developmentprofessional' -> certifications
- `resume-block` MISSED heading 'websitesportfoliosprofiles' (other)
- `resume-block` SPURIOUS heading 'websitesportfolios' -> other
- `resume-block` SPURIOUS heading 'profiles' -> summary
