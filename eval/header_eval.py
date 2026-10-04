"""Stage 8 header metrics: run ingest -> layout -> header rules on the gold
resumes and score name/contact/link/location fields against the hand-labelled
header gold (data/gold/header/header_gold.json). The LLM JSONs are scored the
same way as a reference column (never as gold). Failures are listed with the
predicted vs gold values.

    uv run python -m eval.header_eval
"""

import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import rx3  # noqa: E402,F401  (puts types/ on sys.path)
from _resume_data_layout import GOLD_CATEGORY, json_path, pdf_path  # noqa: E402
from rx3.header import extract_header  # noqa: E402
from rx3.header.gazetteer import COUNTRIES  # noqa: E402
from rx3.ingest.pdf import ingest_pdf  # noqa: E402
from rx3.layout import analyze_layout  # noqa: E402

GOLD = ROOT / "data" / "gold" / "header" / "header_gold.json"
SCALARS = ["name", "email", "phone_no", "linkedin", "github_profile", "city", "state", "country", "postal_code"]
TARGETS = {"name": 0.97, "email": 0.98, "phone_no": 0.98, "linkedin": 0.98, "github_profile": 0.98}  # PROMPT.md §4.7
_COUNTRY = {k.lower(): v.lower() for k, v in COUNTRIES.items()}


def url_norm(v) -> str:
    v = (v or "").strip()
    if not v:
        return ""
    try:
        p = urlparse(v if re.match(r"(?i)https?://", v) else "https://" + v)
    except ValueError:  # e.g. "[a](b)" markdown junk from an LLM
        return v.lower()
    return (p.netloc.lower().removeprefix("www.") + p.path.rstrip("/")).lower()


def norm(field: str, v) -> str:
    if v is None:
        return ""
    v = str(v).strip()
    if field in ("linkedin", "github_profile"):
        return url_norm(v) if "/" in v or "." in v else v.lower()
    if field == "country":
        return _COUNTRY.get(v.lower(), v.lower())
    if field == "phone_no":
        return re.sub(r"\D", "", v)
    return re.sub(r"\s+", " ", v.lower())


def flatten(meta: dict) -> dict:
    a = meta.get("address") or {}
    flat = {f: meta.get(f) for f in ("name", "email", "phone_no", "linkedin", "github_profile")}
    flat.update({"city": a.get("city"), "state": a.get("state"), "country": a.get("country"), "postal_code": a.get("postal_code")})
    flat["extra"] = sorted({url_norm(e.get("link")) for e in meta.get("extra_links") or [] if e.get("link")})
    return flat


def gold_flat(g: dict) -> dict:
    flat = {f: g.get(f) for f in SCALARS}
    flat["extra"] = sorted({url_norm(u) for u in g.get("extra", [])})
    return flat


def score(preds: dict[str, dict], golds: dict[str, dict]) -> dict:
    per_field = {f: {"n": 0, "ok": 0, "spurious": 0} for f in SCALARS}
    extra = {"tp": 0, "fp": 0, "fn": 0}
    failures = []
    for stem, g in golds.items():
        p = preds.get(stem)
        if p is None:
            continue
        for f in SCALARS:
            gv, pv = norm(f, g[f]), norm(f, p[f])
            if gv:
                per_field[f]["n"] += 1
                if pv == gv:
                    per_field[f]["ok"] += 1
                else:
                    failures.append((stem, f, p[f], g[f]))
            elif pv:
                per_field[f]["spurious"] += 1
                failures.append((stem, f + " (spurious)", p[f], g[f]))
        gs, ps = set(g["extra"]), set(p["extra"])
        extra["tp"] += len(gs & ps)
        extra["fp"] += len(ps - gs)
        extra["fn"] += len(gs - ps)
        if gs != ps:
            failures.append((stem, "extra_links", sorted(ps), sorted(gs)))
    return {"per_field": per_field, "extra": extra, "failures": failures}


def run_pipeline(stems: list[str]) -> dict[str, dict]:
    out = {}
    for stem in stems:
        path = pdf_path(GOLD_CATEGORY, stem)
        if path.exists():
            doc = analyze_layout(ingest_pdf(path.read_bytes(), filename=path.name))
            out[stem] = flatten(extract_header(doc, path.name).meta)
    return out


def run_llm(stems: list[str]) -> dict[str, dict]:
    out = {}
    for stem in stems:
        p = json_path(GOLD_CATEGORY, stem)
        if p.exists():
            out[stem] = flatten(json.loads(p.read_text(encoding="utf-8")).get("metaDetails") or {})
    return out


def render(res: dict, label: str) -> list[str]:
    lines = [f"### {label}", "", "| Field | Accuracy | N (gold has value) | Spurious (gold empty) |", "|---|---|---|---|"]
    for f, s in res["per_field"].items():
        acc = f"{s['ok'] / s['n']:.1%}" if s["n"] else "n/a"
        lines.append(f"| {f} | {acc} | {s['n']} | {s['spurious']} |")
    e = res["extra"]
    p = e["tp"] / (e["tp"] + e["fp"]) if e["tp"] + e["fp"] else 1.0
    r = e["tp"] / (e["tp"] + e["fn"]) if e["tp"] + e["fn"] else 1.0
    lines.append(f"| extra_links (P / R) | {p:.1%} / {r:.1%} | {e['tp'] + e['fn']} | {e['fp']} |")
    return lines


def main() -> None:
    gold_all = json.loads(GOLD.read_text(encoding="utf-8"))
    golds = {k: gold_flat(v) for k, v in gold_all.items() if not k.startswith("_")}
    stems = list(golds)
    mine = score(run_pipeline(stems), golds)
    llm = score(run_llm(stems), golds)

    md = [f"# Header eval — {date.today().isoformat()}", ""]
    md.append(f"Gold: {len(golds)} resumes, status **{gold_all['_meta']['status']}** "
              f"(verified_by: {gold_all['_meta']['verified_by']}). **Unverified gold: not a reported accuracy.**")
    md.append("")
    md += render(mine, "rx3 rules (ingest + layout + header)") + [""] + render(llm, "LLM JSONs (reference only)") + [""]
    md.append("### Targets (PROMPT.md §4.7), rx3 rules")
    for f, t in TARGETS.items():
        s = mine["per_field"][f]
        acc = s["ok"] / s["n"] if s["n"] else float("nan")
        md.append(f"- {f}: {acc:.1%} vs target {t:.0%} — {'MET' if acc >= t else 'MISSED'}")
    md += ["", "### rx3 failures (predicted vs gold)", ""]
    for stem, f, pv, gv in mine["failures"]:
        md.append(f"- `{stem}` **{f}**: predicted `{pv}` / gold `{gv}`")

    out = ROOT / "reports" / f"header_eval_{date.today().isoformat()}"
    out.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps({"rx3": mine, "llm": llm}, indent=2, default=str), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
