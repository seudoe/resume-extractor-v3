# LiveCareer held-out heading check — 2026-10-04

184 resumes (stratified over 24 categories, seed 0). Weak labels from HTML `sectiontitle`.

- Heading precision 95.1%, recall 98.0% (tp 1060, fp 55, fn 22)
- Canonical section on matched headings: 1028/1060 = 97.0%

### Most-missed titles

- community service: 2
- computer skills: 1
- activities: 1
- professional leadership: 1
- chronology: 1
- professional development (united states army): 1
- military experience: 1
- summary of skills: 1
- volunteer: 1
- transitional vocation: 1
- nursing expertise: 1
- volunteer associations: 1

### Most common spurious detections

- accomplishments: 10
- volunteer: 4
- skills: 3
- certificate: 2
- socialmedia: 2
- experience: 2
- certification: 2
- courses: 1
- communicationskills: 1
- activities: 1
- contact: 1
- highlights: 1

### Most common canonical disagreements (title, label code -> rules)

- 'work history': LiveCareer says other, rules say workHistory (6x)
- 'activities and honors': LiveCareer says affiliations, rules say awards (6x)
- 'presentations': LiveCareer says other, rules say publications (4x)
- 'relevant experience': LiveCareer says awards, rules say workHistory (3x)
- 'certifications': LiveCareer says affiliations, rules say certifications (1x)
- 'professional development': LiveCareer says workHistory, rules say certifications (1x)
- 'education': LiveCareer says workHistory, rules say education (1x)
- 'experience': LiveCareer says other, rules say workHistory (1x)
- 'military experience': LiveCareer says other, rules say workHistory (1x)
- 'summary of skills': LiveCareer says awards, rules say skills (1x)
