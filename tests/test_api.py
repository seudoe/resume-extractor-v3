import io
import sys
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rx3 import api  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(api.app) as c:  # runs the lifespan: model load (rules only here) + warm-up
        yield c


def make_pdf(pages=1, password=None) -> bytes:
    pdf = pymupdf.open()
    for _ in range(pages):
        page = pdf.new_page()
        for i, row in enumerate(["Jane Doe", "jane.doe@example.com", "EXPERIENCE", "Senior Engineer, Acme Inc.  Jan 2022 - Present", "EDUCATION", "B.Tech in Computer Science  Aug 2016 - May 2020", "Indian Institute of Technology"]):
            page.insert_text((50, 60 + i * 22), row, fontsize=18 if i == 0 else 11)
    if password:
        return pdf.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password)
    return pdf.tobytes()


def post(client, data, name="resume.pdf", **params):
    return client.post("/extract", files={"file": (name, io.BytesIO(data), "application/octet-stream")}, params=params)


def test_health_version_and_root(client):
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["startup_ms"] is not None and "models_loaded" in h and h["limits"]["max_pages"] == 5
    assert client.get("/version").json()["version"] == h["version"]
    assert client.get("/").json()["service"] == "resume-extractor-v3"


def test_extract_returns_schema_and_legacy_meta_and_flags(client):
    r = post(client, make_pdf())
    assert r.status_code == 200
    body = r.json()
    assert body["metaDetails"]["name"] == "Jane Doe" and body["workHistory"][0]["title"] == "Senior Engineer"
    assert body["_meta"] == {"name": "Jane Doe", "email": "jane.doe@example.com", "phone": "", "github": None, "linkedin": None, "otherLinks": []}
    assert "_debug" not in body and "_confidence" not in body
    d = post(client, make_pdf(), debug="true", confidence="true").json()
    assert "timings_ms" in d["_debug"] and "workHistory[0].title" in d["_confidence"]


def test_rejections(client):
    assert post(client, b"hello", "notes.txt").status_code == 415  # not on the allow-list
    assert post(client, b"x" * 20, "resume.doc").status_code == 415  # no LibreOffice in the test environment
    assert post(client, b"", "resume.pdf").status_code == 422
    assert post(client, b"%PDF-1.7 not really a pdf", "broken.pdf").status_code == 422
    assert post(client, make_pdf(password="secret")).status_code == 422  # password-protected
    assert post(client, make_pdf(pages=api.MAX_PAGES + 1)).status_code == 422  # too many pages


def test_size_limit(client, monkeypatch):
    monkeypatch.setattr(api, "MAX_BYTES", 1000)
    r = post(client, make_pdf())
    assert r.status_code == 413
