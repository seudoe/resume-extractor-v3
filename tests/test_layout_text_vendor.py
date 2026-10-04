"""resume-data/layout_text.py is a standalone vendored copy of rx3's reading
pipeline (the LLM-labelling script can't depend on this repo's venv). These
tests keep the copy honest: same lines, same features, same heading set, and a
renderer that carries what the LLM needs. Skipped without ../resume-data."""

import importlib.util
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rx3.ingest.pdf import ingest_pdf  # noqa: E402
from rx3.layout import analyze_layout  # noqa: E402
from rx3.sections import synonyms  # noqa: E402

DATA = Path(__file__).resolve().parent.parent.parent / "resume-data"
MODULE = DATA / "layout_text.py"
AAA = DATA / "PDFs" / "AAA"

pytestmark = pytest.mark.skipif(not (MODULE.exists() and AAA.exists()), reason="resume-data/ not present")

SAMPLE = ["AltaCV_Template.pdf", "Simple_Hipster_CV.pdf", "SambhavMirajgaonkarResume.pdf",
          "Entry_Level_Resume_Template__LaTeX_.pdf", "Resume_Asif_4.0.pdf", "VickyResume-apr26.pdf",
          "chief-information-officer-cio3  - Template 15.pdf", "Aagam_esume-apr26.pdf"]


@pytest.fixture(scope="module")
def lt():
    spec = importlib.util.spec_from_file_location("layout_text", MODULE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["layout_text"] = mod  # dataclasses need the module registered
    spec.loader.exec_module(mod)
    return mod


def signature(l):
    f = l.features
    return (l.text, round(f.rel_size, 3), f.bold, f.all_caps, f.color_differs, f.rule_below, f.is_bullet, f.region)


@pytest.mark.parametrize("name", SAMPLE)
def test_vendored_pipeline_matches_rx3(lt, name):
    path = AAA / name
    if not path.exists():
        pytest.skip(f"{name} missing")
    data = path.read_bytes()
    theirs = [[signature(l) for l in pg.lines] for pg in lt.layout_document(data)]
    ours = [[signature(l) for l in pg.lines] for pg in analyze_layout(ingest_pdf(data)).pages]
    assert theirs == ours


def test_heading_guard_set_is_not_stale(lt):
    assert set(lt._HEADING_PHRASES) == set(synonyms._LOOKUP), "regenerate _HEADING_PHRASES from rx3.sections.synonyms"


def test_render_carries_layout_cells_and_link_targets(lt):
    path = AAA / "SambhavMirajgaonkarResume.pdf"
    if not path.exists():
        pytest.skip("Sambhav missing")
    text = lt.render_layout_text(path)
    assert lt.FORMAT_VERSION in text and "=== PAGE 1 ===" in text
    assert " ⇥ " in text  # cells kept apart
    assert "-> https://www.linkedin.com/in/sambhav-m/" in text  # the real target, not the icon-order guess
    assert "-> https://github.com/sam-wlh-ds" in text
    assert "CAPS" in text and "RULE" in text  # headings are visible as headings
