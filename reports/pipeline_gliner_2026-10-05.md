# Stage 12 pipeline eval (GLiNER on) — 2026-10-05

128 resumes (AAA all + stratified LiveCareer), 0 crashes.

- Schema validity: **100.0%** (128/128)
- Hallucination (independent metric, derived values exempt): **0.15%** (13/8394 strings); per-resume mean AAA 0.60%, LiveCareer 0.06%
- Strings dropped by the pipeline's own grounding: 3
- Determinism (2 processes, PYTHONHASHSEED 0 vs 1, 12 files, byte-identical JSON): **True**

### Latency per stage (ms, warm process, this machine)

| stage | p50 | p95 |
|---|---|---|
| ingest | 19.4 | 61.7 |
| ocr | 0.2 | 0.5 |
| layout | 7.6 | 26.6 |
| sections | 2.9 | 9.6 |
| header | 5.3 | 16.6 |
| entries | 958.7 | 3251.5 |
| gliner | 956.2 | 3245.6 |
| normalise | 23.2 | 78.7 |
| ground | 2.0 | 6.0 |
| confidence | 0.4 | 1.3 |
| validate | 0.3 | 0.9 |
| total | 1015.9 | 3527.4 |

### Hallucination examples (independent metric)

- AAA/AltaCV_Template: 'Portfolio'
- AAA/AltaCV_Template: 'Portfolio'
- AAA/Entry_Level_Resume_Template__LaTeX_: 'Portfolio'
- AAA/Resume_Asif_4.0: 'MOHD ASIF SHERSHAHVADI'
- AAA/SambhavMirajgaonkarResume: 'Docker [€]'
- AAA/Simple_Hipster_CV: 'University of California'
- AAA/Simple_Hipster_CV: 'Portfolio'
- AAA/resume-block: 'Mohd Asif Shershahvadi'
- AGRICULTURE/21868149: 'attaché'
- BPO/95625660: 'Degree Institution/ /School University/Board Year M.B.A -HR Annamalai University'
- FINANCE/78229715: 'Reviewed accountantÆs book entries to ensure accuracy of the G/L.'
- FINANCE/23573064: 'Microsoft Office'
- HR/72231872: 'Portfolio'

### Dropped by grounding (first 15)

- AGRICULTURE/21868149 education[3].field.course: '2014 October) Overall Degree Class: 2.1 Dissertation: Distinction Executive Certificate in Project Management, Monitoring and Evaluation with the  in Post-Harvest Management and Grading of Cereals, Pulses and Oil Seeds Certificate in Fish Farming as a Business (Aquaculture) Served in the Midlands State University Electoral College for Students Representative Council (SRC) Advanced Level'
- APPAREL/28998957 education[1].field.course: 'SAS Training Center New York, NY Administering Microsoft Windows NT 4.0, New Horizons Training Center Braintree, MA Fundamentals of Solaris 2, Sun    Introduction to Software Design & Development Massasoit Community College Boston University Center for Information Technology  Concepts & Facilities of Emerging Technologies'
- BANKING/19920687 certifications[0].name: 'Wachovia Bank, N.A., a Wells Fargo Company Licensed Financial Specialist - University California - Irvine, Certificate in Project Management'
