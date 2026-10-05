"""Turn `FILES/resume_data.csv` rows into structured synthetic resumes (exact ground truth for the renderer).

The CSV is sparse (mostly one job / one degree per row, "N/A" locations), so each synthetic resume starts from one row and
borrows extra work/education entries from random other rows. Entries are unrelated people's jobs stitched together; that's
fine for block-level field extraction, which is what this data trains. Deterministic for a given seed."""

import ast
import csv
import random
import re
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parents[3] / "FILES" / "resume_data.csv"
FIRST = "Aarav Priya Rohan Sneha Karan Ananya Vikram Meera Arjun Isha Rahul Neha Aditya Kavya Siddharth Pooja Nikhil Riya James Emily Michael Sarah David Laura Daniel Emma Robert Olivia Chris Hannah Omar Fatima Liam Sofia Noah Ava Ethan Mia Lucas Chloe".split()
LAST = "Sharma Verma Patel Iyer Reddy Nair Gupta Mehta Kulkarni Joshi Singh Rao Smith Johnson Brown Taylor Miller Wilson Moore Clark Lewis Walker Hall Young Allen King Wright Lopez Hill Scott Green Adams Baker Nelson Carter Perez Khan Ali Costa Silva Novak".split()
CITIES = ["Mumbai, India", "Pune, India", "Bengaluru, India", "Delhi, India", "Hyderabad, India", "Chennai, India", "Ahmedabad, India",
          "New York, NY", "Austin, TX", "Seattle, WA", "Chicago, IL", "Boston, MA", "San Francisco, CA", "London, UK", "Toronto, Canada",
          "Berlin, Germany", "Singapore", "Remote"]
DEGREE_FULL = {"B.Tech": "Bachelor of Technology", "M.Tech": "Master of Technology", "B.E": "Bachelor of Engineering", "B.Sc": "Bachelor of Science",
               "M.Sc": "Master of Science", "MBA": "Master of Business Administration", "BCA": "Bachelor of Computer Applications",
               "MCA": "Master of Computer Applications", "B.Com": "Bachelor of Commerce", "BBA": "Bachelor of Business Administration",
               "B.A": "Bachelor of Arts", "M.A": "Master of Arts", "Diploma": "Diploma", "PhD": "Doctor of Philosophy"}
_NONE = {"", "n/a", "none", "null", "nan", "[none]"}


def _lst(s: str) -> list:
    s = (s or "").strip()
    if not s or s.lower() in _NONE:
        return []
    try:
        v = ast.literal_eval(s)
    except (ValueError, SyntaxError):
        return [s]
    return [x for x in (v if isinstance(v, list) else [v]) if x is not None]


_PLACEHOLDER = re.compile(r"^(company( name)?|city( ?, ?state)?|state|n/?a|unknown)$", re.I)


def _clean(x) -> str:
    x = re.sub(r"\s+", " ", str(x)).strip()
    return "" if x.lower() in _NONE or _PLACEHOLDER.match(x) else x


def _flat(v) -> list:
    return [y for x in v for y in (_flat(x) if isinstance(x, list) else [x])]


def load_pool() -> dict:
    """Entry pools harvested from every CSV row."""
    work, edu, skills, langs, certs = [], [], [], [], []
    csv.field_size_limit(10**9)
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            comps, pos = _lst(r["professional_company_names"]), _lst(r["positions"])
            starts, ends, locs = _lst(r["start_dates"]), _lst(r["end_dates"]), _lst(r["locations"])
            bl = [b.strip() for b in (r["responsibilities"] or "").split("\n") if 8 < len(b.strip()) < 140]
            for i, (c, p) in enumerate(zip(comps, pos)):
                c, p = _clean(c), _clean(p)
                if c and p and len(c) < 60 and len(p) < 60:
                    work.append({"company": c, "title": p, "location": _clean(locs[i]) if i < len(locs) else "",
                                 "start": _clean(starts[i]) if i < len(starts) else "", "end": _clean(ends[i]) if i < len(ends) else "",
                                 "bullets": bl[i * 3 : i * 3 + 3]})
            insts, degs, years = _lst(r["educational_institution_name"]), _lst(r["degree_names"]), _lst(r["passing_years"])
            fields, res = _lst(r["major_field_of_studies"]), _lst(r["educational_results"])
            for i, ins in enumerate(insts):
                ins = _clean(ins)
                if ins and len(ins) < 90:
                    edu.append({"institution": ins, "degree": _clean(degs[i]) if i < len(degs) else "", "year": _clean(years[i]) if i < len(years) else "",
                                "course": _clean(fields[i]) if i < len(fields) else "", "result": _clean(res[i]) if i < len(res) else ""})
            skills += [_clean(s) for s in _flat(_lst(r["skills"])) if _clean(s)]
            langs += [_clean(s) for s in _lst(r["languages"]) if _clean(s)]
            certs += [_clean(s) for s in _flat(_lst(r["certification_skills"])) if _clean(s)]
    return {"work": work, "edu": edu, "skills": sorted(set(skills)), "langs": sorted(set(langs)) or ["English", "Hindi"], "certs": sorted(set(certs))}


TAGLINES = ["Education technology startup with 50+ employees", "NYSE-listed recruitment and employer branding company", "Digital marketing agency focusing on search engine marketing",
            "A lender that provides home equity lines of credit in 38 states", "Career training and membership SaaS with 150,000 users", "Augmented reality startup with 50+ employees",
            "Helps personal and wealth clients build financial strength", "Provides quality assurance and control testing for global markets", "Global logistics provider serving 40 countries",
            "Venture-backed healthcare analytics company", "Family-owned retail chain with 120 stores", "Public sector research institute", "B2B payments platform processing $2B annually"]


def _ym(rng: random.Random, y0: int, y1: int) -> tuple[int, int]:
    return rng.randint(y0, y1), rng.randint(1, 12)


def make_resume(rng: random.Random, pool: dict) -> dict:
    """One structured synthetic resume: scalar header, work[], education[], skills[], with dates as (y, m) tuples (None = present)."""
    name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
    n_work, n_edu = rng.choice([1, 2, 2, 3, 3, 4, 5]), rng.choice([1, 2, 2, 3])
    work, y = [], rng.randint(2021, 2025)
    end = (y, rng.randint(1, 10))
    for i, w in enumerate(rng.sample(pool["work"], n_work)):
        dur = rng.randint(6, 40)
        e_total = end[0] * 12 + end[1] - 1
        s_total = e_total - dur
        start = (s_total // 12, s_total % 12 + 1)
        cur = i == 0 and rng.random() < 0.45
        work.append({"title": w["title"], "company": w["company"],
                     "location": w["location"] if _clean(w["location"]) else rng.choice(CITIES), "start": start, "end": None if cur else end, "tagline": rng.choice(TAGLINES),
                     "bullets": (w.get("bullets") or [])[: rng.randint(1, 4)] or ["Delivered projects on time and supported the wider team."]})
        end = (start[0], max(1, start[1] - rng.randint(1, 4)))
    edu, gy = [], rng.randint(2012, 2026)
    for e in rng.sample(pool["edu"], n_edu):
        deg = e["degree"] or rng.choice(list(DEGREE_FULL))
        edu.append({"institution": e["institution"], "degree": deg, "course": e["course"] or rng.choice(["Computer Science", "Information Technology", "Electronics", "Mechanical Engineering", "Commerce", "Data Science"]),
                    "year": gy, "start_year": gy - rng.choice([2, 3, 4]), "result": rng.choice(["CGPA: %.2f" % rng.uniform(6.5, 9.8), "GPA: %.1f" % rng.uniform(2.8, 4.0), "Percentage: %d%%" % rng.randint(60, 95), ""])})
        gy -= rng.randint(2, 4)
    skills = rng.sample(pool["skills"], min(len(pool["skills"]), rng.randint(6, 14)))
    first, last = name.split()[0].lower(), name.split()[-1].lower()
    return {"name": name, "email": f"{first}.{last}{rng.randint(1, 99)}@{rng.choice(['gmail.com', 'outlook.com', 'yahoo.com'])}",
            "phone": f"+91 {rng.randint(70000, 99999)} {rng.randint(10000, 99999)}", "city": rng.choice(CITIES),
            "headline": work[0]["title"], "summary": "Motivated professional with hands-on experience delivering reliable results in fast-paced teams.",
            "work": work, "education": edu, "skills": skills, "languages": rng.sample(pool["langs"], min(2, len(pool["langs"]))),
            "certs": rng.sample(pool["certs"], min(2, len(pool["certs"]))) if pool["certs"] else []}
