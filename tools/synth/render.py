"""Render structured synthetic resumes to PDF with Chromium (Playwright). Ground truth = exactly what was printed.

    uv run python -m tools.synth.render --n 1200 --seed 0          # data/synthetic/<family>/<id>.pdf + <id>.json

Per resume the *printed* strings (title, company, location, date text, degree text, ...) are saved next to the PDF, so
labels never depend on re-parsing. Randomised per resume: date format, range separator, "Present" word, section order,
heading synonyms, whether locations / results are shown, degree abbreviation vs full name, ordering of skills."""

import argparse
import html
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from synth.data import DEGREE_FULL, load_pool, make_resume  # noqa: E402
from synth.families import BY_NAME, FAMILIES, Family  # noqa: E402

OUT = ROOT / "data" / "synthetic"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
HEADINGS = {
    "work": ["Experience", "Work Experience", "Professional Experience", "Employment History", "Work History", "Career History"],
    "edu": ["Education", "Academic Background", "Education & Qualifications", "Academic Qualifications"],
    "skills": ["Skills", "Technical Skills", "Core Competencies", "Skills & Tools", "Key Skills"],
    "langs": ["Languages", "Language Proficiency"],
    "certs": ["Certifications", "Certificates", "Licenses & Certifications"],
    "summary": ["Summary", "Professional Summary", "Profile", "Objective"],
}
DATE_STYLES = ["Mon YYYY", "Month YYYY", "MM/YYYY", "YYYY-MM", "Mon 'YY", "YYYY"]
PRESENT = ["Present", "Current", "Till Date", "Ongoing"]
SEPS = [" – ", " - ", " to ", " — "]


def esc(s) -> str:
    return html.escape(str(s))


class Fmt:
    """Per-resume random choices; every printed date goes through here so ground truth records it."""

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.date = rng.choice(DATE_STYLES)
        self.sep = rng.choice(SEPS)
        self.present = rng.choice(PRESENT)
        self.full_degree = rng.random() < 0.5
        self.show_loc = rng.random() < 0.8
        self.show_result = rng.random() < 0.7
        self.year_only = self.date == "YYYY"

    def point(self, ym) -> str:
        y, m = ym
        d = self.date
        return {"Mon YYYY": f"{MONTHS[m - 1][:3]} {y}", "Month YYYY": f"{MONTHS[m - 1]} {y}", "MM/YYYY": f"{m:02d}/{y}", "YYYY-MM": f"{y}-{m:02d}",
                "Mon 'YY": f"{MONTHS[m - 1][:3]} '{str(y)[2:]}", "YYYY": str(y)}[d]

    def range(self, start, end) -> tuple[str, str, str]:
        a = self.point(start)
        b = self.present if end is None else self.point(end)
        return a + self.sep + b, a, b

    def degree(self, d: str) -> str:
        return DEGREE_FULL.get(d, d) if self.full_degree else d


def work_rec(w: dict, fm: Fmt) -> dict:
    text, a, b = fm.range(w["start"], w["end"])
    return {"title": w["title"], "company": w["company"], "location": w["location"] if fm.show_loc else "", "dates": text, "start_text": a, "end_text": b, "bullets": w["bullets"], "tagline": w.get("tagline", "")}


def edu_rec(e: dict, fm: Fmt) -> dict:
    yr = str(e["year"]) if fm.year_only or fm.rng.random() < 0.6 else f"{e['start_year']} – {e['year']}"
    return {"institution": e["institution"], "degree": fm.degree(e["degree"]), "course": e["course"], "dates": yr, "result": e["result"] if fm.show_result else ""}


# ---- entry styles ------------------------------------------------------------------------------------------------
def W(style: str, w: dict, bullet: str, layout: str) -> str:
    loc, d = esc(w["location"]), esc(w["dates"])
    lis = "".join(f"<li>{esc(b)}</li>" for b in w["bullets"])
    ul = f"<ul class='b'>{lis}</ul>" if lis else ""
    comp_loc = esc(w["company"]) + (f", {loc}" if loc else "")
    if layout == "table":
        return f"<table class='t'><tr><td class='tl'>{d}</td><td><b>{esc(w['title'])}</b><br>{comp_loc}{ul}</td></tr></table>" if style == "W4" else \
               f"<table class='t'><tr><td><b>{esc(w['title'])}</b><br><i>{comp_loc}</i></td><td class='r'>{d}</td></tr></table>{ul}"
    if style == "W1":
        return f"<div class='row'><b>{esc(w['title'])}</b><span>{d}</span></div><div><i>{comp_loc}</i></div>{ul}"
    if style == "W2":
        return f"<div class='row'><b>{esc(w['company'])}</b><span>{d}</span></div><div class='row'><i>{esc(w['title'])}</i><i>{loc}</i></div>{ul}"
    if style == "W3":
        parts = [esc(w["title"]), esc(w["company"])] + ([loc] if loc else []) + [d]
        return f"<div><b>{parts[0]}</b> | " + " | ".join(parts[1:]) + f"</div>{ul}"
    if style == "W4":
        return f"<div class='tl-row'><div class='tl'>{d}</div><div><b>{esc(w['title'])}</b><br>{comp_loc}{ul}</div></div>"
    if style == "W5":
        return f"<div>{esc(w['title'])}</div><div>{d}</div><div>{comp_loc}</div>{ul}"
    if style == "W6":
        return f"<div><b>{esc(w['title'])}, {esc(w['company'])}</b>" + (f" — {loc}" if loc else "") + f"</div><div class='muted'>{d}</div>{ul}"
    if style == "W8":  # company, location / tagline / title / dates, one per line
        return f"<div><b>{comp_loc}</b></div><div class='muted'>{esc(w.get('tagline', ''))}</div><div><b>{esc(w['title'])}</b></div><div>{d}</div>{ul}"
    if style == "W9":  # "Company, City" with the dates on the same row, the title underneath
        return f"<div class='row'><b>{comp_loc}</b><span>{d}</span></div><div><i>{esc(w['title'])}</i></div>{ul}"
    if style == "W7":
        return f"<div class='row'><span><b>{esc(w['title'])}</b> at {esc(w['company'])}" + (f" ({loc})" if loc else "") + f"</span><small>{d}</small></div>{ul}"
    raise ValueError(style)


def E(style: str, e: dict, layout: str) -> str:
    inst, deg, course, d, res = esc(e["institution"]), esc(e["degree"]), esc(e["course"]), esc(e["dates"]), esc(e["result"])
    dc = f"{deg} in {course}" if course else deg
    if layout == "table" and style == "E2":
        return f"<tr><td>{dc}</td><td>{inst}</td><td>{d}</td><td>{res}</td></tr>"
    if style == "E1":
        return f"<div class='row'><b>{inst}</b><span>{d}</span></div><div><i>{dc}</i>" + (f" — {res}" if res else "") + "</div>"
    if style == "E2":
        return f"<tr><td>{dc}</td><td>{inst}</td><td>{d}</td><td>{res}</td></tr>"
    if style == "E3":
        return f"<div><b>{dc}</b> | {inst} | {d}" + (f" | {res}" if res else "") + "</div>"
    if style == "E4":
        return f"<div>{dc}</div><div>{inst}</div><div>{d}</div>" + (f"<div>{res}</div>" if res else "")
    if style == "E5":
        return f"<div><b>{inst}</b></div><div>{dc} ({d})" + (f" — {res}" if res else "") + "</div>"
    raise ValueError(style)


def head(fam: Family, text: str) -> str:
    cls = {"caps-rule": "h-caps", "bold-color": "h-color", "smallcaps": "h-sc", "plain-bold": "h-plain", "boxed": "h-box"}[fam.header]
    return f"<h2 class='{cls}'>{esc(text)}</h2>"


CSS = """
@page{size:A4;margin:14mm}
body{font-family:%(font)s;font-size:%(size)spt;color:%(color)s;margin:0;line-height:1.28}
.row{display:flex;justify-content:space-between;gap:12px}.muted{color:#666}small{font-size:.85em}
h1{font-size:2em;margin:0}.sub{margin:2px 0 6px}
h2{margin:12px 0 4px;font-size:1.1em}.h-caps{text-transform:uppercase;border-bottom:1px solid %(color)s}
.h-color{color:%(color)s}.h-sc{font-variant:small-caps;border-bottom:1px solid #000;font-size:1.2em}.h-plain{font-weight:bold}
.h-box{background:%(color)s;color:#fff;padding:2px 6px}
ul.b{margin:3px 0 6px 18px;padding:0;list-style:%(bullet)s}.entry{margin-bottom:8px}
table.t{width:100%%;border-collapse:collapse}td{vertical-align:top;padding:2px 6px 2px 0}td.r{text-align:right;white-space:nowrap}td.tl{width:22%%;color:#555}
.tl-row{display:flex;gap:14px}.tl-row .tl{width:22%%;color:#555}
.band{background:%(color)s;color:#fff;padding:14px 16px;margin:-14mm -14mm 10px -14mm;padding-left:14mm}
.cols{display:flex;gap:18px}.side{width:30%%}.main{width:70%%}.side .entry{margin-bottom:4px}
"""


def build_html(fam: Family, r: dict, fm: Fmt, rng: random.Random) -> tuple[str, dict]:
    work = [work_rec(w, fm) for w in r["work"]]
    edu = [edu_rec(e, fm) for e in r["education"]]
    hs = {k: rng.choice(v) for k, v in HEADINGS.items()}
    contact = f"{esc(r['email'])} | {esc(r['phone'])} | {esc(r['city'])}"
    wh = "".join(f"<div class='entry'>{W(fam.work, w, fam.bullet, fam.layout)}</div>" for w in work)
    if fam.edu == "E2":
        eh = "<table class='t'><tr><td><b>Degree</b></td><td><b>Institution</b></td><td><b>Year</b></td><td><b>Result</b></td></tr>" + "".join(E("E2", e, fam.layout) for e in edu) + "</table>"
    else:
        eh = "".join(f"<div class='entry'>{E(fam.edu, e, fam.layout)}</div>" for e in edu)
    skills = ", ".join(esc(s) for s in r["skills"])
    side_blocks = [(hs["skills"], f"<div>{skills}</div>"), (hs["langs"], "<div>" + ", ".join(esc(x) for x in r["languages"]) + "</div>")]
    main_blocks = [(hs["summary"], f"<div>{esc(r['summary'])}</div>"), (hs["work"], wh), (hs["edu"], eh)]
    if r["certs"]:
        side_blocks.append((hs["certs"], "".join(f"<div>{esc(c)}</div>" for c in r["certs"])))
    sec = lambda blocks: "".join(head(fam, t) + body for t, body in blocks)  # noqa: E731
    top = f"<h1>{esc(r['name'])}</h1><div class='sub'>{esc(r['headline'])}</div><div>{contact}</div>"
    if fam.layout in ("sidebar-left", "sidebar-right"):
        side, main = f"<div class='side'><div>{contact}</div>{sec(side_blocks)}</div>", f"<div class='main'><h1>{esc(r['name'])}</h1><div class='sub'>{esc(r['headline'])}</div>{sec(main_blocks)}</div>"
        body = f"<div class='cols'>{side + main if fam.layout == 'sidebar-left' else main + side}</div>"
    else:
        order = main_blocks[:1] + [side_blocks[0]] + main_blocks[1:] + side_blocks[1:]
        rng.shuffle(order[1:])  # section order varies; summary first
        top_html = f"<div class='band'>{top}</div>" if fam.layout == "banner" else top
        body = top_html + sec(order)
    doc = f"<html><head><meta charset='utf-8'><style>{CSS % {'font': fam.font, 'size': fam.size, 'color': fam.color, 'bullet': {'•': 'disc', '▪': 'square', '–': 'none', '●': 'disc', '◦': 'circle', '›': 'none', '-': 'none'}[fam.bullet]}}</style></head><body>{body}</body></html>"
    truth = {"name": r["name"], "email": r["email"], "work": work, "education": edu, "skills": r["skills"], "headings": hs, "date_style": fm.date}
    return doc, truth


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1200, help="resumes in total (spread over all families)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--families", nargs="*", help="only these families")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    pool = load_pool()
    fams = [BY_NAME[f] for f in args.families] if args.families else FAMILIES
    per = max(1, args.n // len(fams))
    manifest = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for fam in fams:
            (OUT / fam.name).mkdir(parents=True, exist_ok=True)
            for i in range(per):
                rng = random.Random(f"{args.seed}-{fam.name}-{i}")
                resume = make_resume(rng, pool)
                doc, truth = build_html(fam, resume, Fmt(rng), rng)
                page.set_content(doc)
                rid = f"{fam.name}_{args.seed}_{i:04d}"
                page.pdf(path=str(OUT / fam.name / f"{rid}.pdf"), format="A4", print_background=True)
                (OUT / fam.name / f"{rid}.json").write_text(json.dumps({"id": rid, "family": fam.name, **truth}, ensure_ascii=False), encoding="utf-8")
                manifest.append({"id": rid, "family": fam.name})
            print("done", fam.name, per, flush=True)
        browser.close()
    (OUT / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


if __name__ == "__main__":
    main()
