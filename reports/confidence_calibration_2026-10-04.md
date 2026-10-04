# Confidence calibration — 2026-10-04

4419 observations (2213 held out, odd ids). Fit on even ids; labels are weak (LiveCareer HTML).

| field | n | mean confidence | observed accuracy | abs gap (ECE) |
|---|---|---|---|---|
| edu.degree | 228 | 0.797 | 0.803 | 0.085 |
| edu.institution | 197 | 0.627 | 0.513 | 0.114 |
| period | 872 | 0.971 | 0.981 | 0.012 |
| work.title | 916 | 0.940 | 0.952 | 0.015 |

### Buckets (fit on all)

- edu.degree `canon=0|has_course=0`: acc 0.672 (n=62)
- edu.degree `canon=0|has_course=1`: acc 0.748 (n=109)
- edu.degree `canon=1|has_course=0`: acc 0.875 (n=86)
- edu.degree `canon=1|has_course=1`: acc 0.833 (n=214)
- edu.institution `kw=0|short=0`: acc 0.143 (n=5)
- edu.institution `kw=0|short=1`: acc 0.231 (n=11)
- edu.institution `kw=1|short=0`: acc 0.303 (n=31)
- edu.institution `kw=1|short=1`: acc 0.615 (n=351)
- period `both=0|any=0`: acc 0.111 (n=7)
- period `both=0|any=1`: acc 0.071 (n=12)
- period `both=1|any=1`: acc 0.984 (n=1701)
- work.title `lex=0|short=0|dated=0`: acc 0.077 (n=11)
- work.title `lex=0|short=0|dated=1`: acc 0.455 (n=20)
- work.title `lex=0|short=1|dated=0`: acc 0.062 (n=14)
- work.title `lex=0|short=1|dated=1`: acc 0.705 (n=59)
- work.title `lex=1|short=0|dated=0`: acc 0.250 (n=2)
- work.title `lex=1|short=0|dated=1`: acc 0.772 (n=55)
- work.title `lex=1|short=1|dated=0`: acc 0.524 (n=19)
- work.title `lex=1|short=1|dated=1`: acc 0.979 (n=1650)
