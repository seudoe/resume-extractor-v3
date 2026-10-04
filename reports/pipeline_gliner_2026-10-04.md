# Stage 12 pipeline eval (GLiNER on) — 2026-10-04

224 resumes (AAA all + stratified LiveCareer), 0 crashes.

- Schema validity: **100.0%** (224/224)
- Hallucination (independent metric, derived values exempt): **0.18%** (26/14747 strings); per-resume mean AAA 0.61%, LiveCareer 0.13%
- Strings dropped by the pipeline's own grounding: 21
- Determinism (2 processes, PYTHONHASHSEED 0 vs 1, 12 files, byte-identical JSON): **True**

### Latency per stage (ms, warm process, this machine)

| stage | p50 | p95 |
|---|---|---|
| ingest | 23.6 | 54.8 |
| ocr | 0.2 | 0.5 |
| layout | 10.9 | 21.8 |
| sections | 4.1 | 9.5 |
| header | 8.1 | 14.3 |
| entries | 1867.9 | 3326.4 |
| gliner | 1865.6 | 3323.4 |
| normalise | 33.4 | 79.6 |
| ground | 2.7 | 5.9 |
| confidence | 0.4 | 1.1 |
| validate | 0.4 | 0.8 |
| total | 1971.3 | 3492.9 |

### Hallucination examples (independent metric)

- AAA/AltaCV_Template: 'Portfolio'
- AAA/AltaCV_Template: 'Portfolio'
- AAA/Entry_Level_Resume_Template__LaTeX_: 'Portfolio'
- AAA/Resume_Asif_4.0: 'MOHD ASIF SHERSHAHVADI'
- AAA/SambhavMirajgaonkarResume: 'Docker [€]'
- AAA/Simple_Hipster_CV: 'University of California'
- AAA/Simple_Hipster_CV: 'Portfolio'
- AAA/resume-block: 'Mohd Asif Shershahvadi'
- AGRICULTURE/84512719: 'Develop and manage\xa0projects and budgets'
- APPAREL/36136569: 'email'
- AUTOMOBILE/22946204: 'Portfolio'
- BPO/63158213: 'F5\xa0Networks'
- BPO/63158213: 'PPP Multilink\xa0Routing: OSPF'
- BPO/63158213: 'Transparent Bridging LAN: Ethernet'
- BPO/63158213: 'Token\xa0Ring'
- CHEF/12155206: 'read\xa0and write in\xa0English'
- CHEF/12155206: '\u200bOrganized & distributed MedicAlert collateral to surrounding medical\xa0community.'
- CHEF/12155206: 'Room mom,\xa0Reading & math groups,\xa0chaperone,\xa0baker, Hospitality & Garden Club, Ski & Chess Club'
- CONSTRUCTION/27243670: 'Construction Industry Research and Information Association\xa0 ( CIRIA )'
- DIGITAL-MEDIA/19861776: 'process reengineering'
- DIGITAL-MEDIA/17132168: 'Presenting and speaking\xa0 Educating and training'
- HEALTHCARE/98309114: 'Portfolio'
- INFORMATION-TECHNOLOGY/20001721: 'Presented various projects including\xa0 VPN, RDMS, and IT Proposals \xa0to several classes and instructors .'
- INFORMATION-TECHNOLOGY/20001721: '\u200b'
- PUBLIC-RELATIONS/37087371: 'Portfolio'

### Dropped by grounding (first 15)

- ACCOUNTANT/78403342 education[1].field.course: 'QuickBooks Certificate : Payroll , 2012   ï1⁄4\u200b'
- ACCOUNTANT/12202337 education[0].field.course: 'Finance  ,  , USA'
- ACCOUNTANT/12202337 education[1].field.course: 'Medical Technology  ,  , USA'
- AGRICULTURE/26835781 education[0].field.course: 'Plant and Soil Science Agriculture   Carbondale (SIUC) ,  Plant and Soil Science Agriculture Education'
- AGRICULTURE/26835781 education[1].field.course: 'Agriculture Economics International Trade North   ,  Agriculture Economics International Trade'
- AGRICULTURE/26835781 education[2].field.course: 'Agriculture   ,  Agriculture Business'
- APPAREL/13386301 education[0].field.course: 'Graphic Arts/   ï1⁄4\u200b'
- BANKING/25162378 education[0].field.course: 'Business Management Marketing  : Graduated Cum Laude Business Management Marketing Graduated Cum Laude'
- CONSULTANT/88691367 education[0].field.course: 'Economics   ï1⁄4\u200b  Economics Accounting'
- CONSULTANT/30863060 education[0].field.course: 'Information Management    Information Management Systems'
- DESIGNER/20986595 education[2].field.course: 'Accounting Marketing ,   Accounting Marketing'
- DIGITAL-MEDIA/17132168 education[0].field.course: 'Marketing Management Assumption university  , Thailand   Diploma Assumtion University Bangkok, Bangkok, thailand Matt-Sci, 2006 Hadyai vittayalai school'
- DIGITAL-MEDIA/17432318 education[0].field.course: 'Business Management,   Business Management, Marketing'
- FINANCE/14722634 education[0].field.course: 'Business   Business'
- FITNESS/63282405 workHistory[0].title: 'Customer Service Representactive  Processed applications'
