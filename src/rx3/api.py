"""FastAPI service (PROMPT.md §5 Stage 14).

    uvicorn rx3.api:app --host 0.0.0.0 --port 7860

POST /extract  multipart `file` (PDF / DOCX / DOC) -> ParsedResumeData JSON (+ legacy `_meta` for ifind's normaliseHFOutput).
               ?debug=true adds `_debug`, ?confidence=true adds `_confidence`.
GET  /, /health (status, version, git sha, models loaded, startup time), /version.

Limits (env): RX3_MAX_BYTES (10 MB), RX3_MAX_PAGES (5), RX3_TIMEOUT_S (25, keep < 30). One extraction runs at a time (the models
use all the configured threads); further requests queue. Models are loaded and warmed up once at startup."""

import asyncio
import os
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

import pymupdf
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from rx3.ifind_log import RequestLogMiddleware, get_logger, setup
from rx3.pipeline import VERSION, TooManyPages, UnreadableDocument, UnsupportedFormat, extract

setup("rx3")
log = get_logger("api")
MAX_BYTES = int(os.environ.get("RX3_MAX_BYTES", 10 * 1024 * 1024))
MAX_PAGES = int(os.environ.get("RX3_MAX_PAGES", 5))
TIMEOUT_S = float(os.environ.get("RX3_TIMEOUT_S", 25))
ALLOWED = {".pdf", ".docx", ".doc"}
_pool = ThreadPoolExecutor(max_workers=1)  # one extraction at a time
_state: dict = {"started": time.time(), "startup_ms": None, "warmup_ms": None, "models": {}}


def git_sha() -> str:
    if os.environ.get("RX3_GIT_SHA"):
        return os.environ["RX3_GIT_SHA"]
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=Path(__file__).resolve().parent, capture_output=True, text=True, timeout=3)
        return out.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001
        return "unknown"


def _warmup_pdf() -> bytes:
    pdf = pymupdf.open()
    page = pdf.new_page()
    for i, row in enumerate(["Jane Doe", "jane.doe@example.com", "EXPERIENCE", "Senior Engineer, Acme Inc.  Jan 2022 - Present",
                             "EDUCATION", "B.Tech in Computer Science  Aug 2016 - May 2020", "Indian Institute of Technology", "SKILLS", "Python, SQL"]):
        page.insert_text((50, 60 + i * 22), row, fontsize=18 if i == 0 else 11)
    return pdf.tobytes()


def legacy_meta(out: dict) -> dict:
    """The `_meta` object ifind's normaliseHFOutput reads (name, email, phone, github, linkedin, otherLinks)."""
    m = out.get("metaDetails") or {}
    return {"name": m.get("name", ""), "email": m.get("email", ""), "phone": m.get("phone_no", ""), "github": m.get("github_profile"),
            "linkedin": m.get("linkedin"), "otherLinks": [{"label": x.get("name", ""), "url": x.get("link", "")} for x in m.get("extra_links", [])]}


@asynccontextmanager
async def lifespan(app: FastAPI):
    t0 = time.perf_counter()
    gliner_on = os.environ.get("RX3_ENABLE_GLINER") == "1"
    models = {"gliner": False, "adapter": None, "ocr_tesseract": shutil.which("tesseract") is not None, "libreoffice": shutil.which("soffice") is not None}
    if gliner_on:
        from rx3.fields.gliner import shared_refiner

        refiner = shared_refiner()
        refiner._load()  # load weights now, not on the first request
        models.update(gliner=True, adapter=refiner.adapter)
    _state["models"] = models
    w0 = time.perf_counter()
    extract(_warmup_pdf(), "warmup.pdf")  # warm caches (skill tables, tokenizer, first forward pass)
    _state["warmup_ms"] = round((time.perf_counter() - w0) * 1000)
    _state["startup_ms"] = round((time.perf_counter() - t0) * 1000)
    log.ok("rx3 ready", extra={"f": {"version": VERSION, "ms": _state["startup_ms"], "warmup_ms": _state["warmup_ms"], **{f"model_{k}": v for k, v in models.items()}}})
    yield
    _pool.shutdown(wait=False, cancel_futures=True)


app = FastAPI(title="resume-extractor-v3", version=VERSION, lifespan=lifespan)
app.add_middleware(RequestLogMiddleware)


@app.get("/")
def root() -> dict:
    return {"service": "resume-extractor-v3", "version": VERSION, "extract": "POST /extract (multipart `file`)", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok" if _state["startup_ms"] is not None else "starting", "version": VERSION, "git_sha": git_sha(), "models_loaded": _state["models"],
            "startup_ms": _state["startup_ms"], "warmup_ms": _state["warmup_ms"], "uptime_s": round(time.time() - _state["started"], 1),
            "limits": {"max_bytes": MAX_BYTES, "max_pages": MAX_PAGES, "timeout_s": TIMEOUT_S}}


@app.get("/version")
def version() -> dict:
    return {"version": VERSION, "git_sha": git_sha()}


def _convert_doc(data: bytes) -> bytes:
    """Legacy .doc -> .docx through LibreOffice when it is installed; otherwise a clear 415."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise HTTPException(415, "'.doc' needs LibreOffice, which is not installed on this server; upload a PDF or DOCX")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "in.doc"
        src.write_bytes(data)
        try:
            subprocess.run([soffice, "--headless", "--convert-to", "docx", "--outdir", tmp, str(src)], check=True, timeout=20, capture_output=True)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(422, f"could not convert .doc: {e}") from e
        return (Path(tmp) / "in.docx").read_bytes()


async def _read_limited(file: UploadFile) -> bytes:
    buf = bytearray()
    while chunk := await file.read(1024 * 1024):
        buf += chunk
        if len(buf) > MAX_BYTES:
            raise HTTPException(413, f"file larger than {MAX_BYTES // (1024 * 1024)} MB")
    return bytes(buf)


@app.post("/extract")
async def extract_endpoint(file: UploadFile = File(...), debug: bool = Query(False), confidence: bool = Query(False)) -> JSONResponse:
    t_start = time.perf_counter()
    name = file.filename or ""
    ext = Path(name).suffix.lower()
    if ext and ext not in ALLOWED:
        raise HTTPException(415, f"unsupported file type {ext!r} (PDF, DOCX or DOC)")
    data = await _read_limited(file)
    if not data:
        raise HTTPException(422, "empty file")
    if ext == ".doc":
        data, name = _convert_doc(data), "resume.docx"
    loop = asyncio.get_running_loop()
    job = loop.run_in_executor(_pool, lambda: extract(data, name, debug=debug, with_confidence=confidence, max_pages=MAX_PAGES))
    try:
        out = await asyncio.wait_for(job, timeout=TIMEOUT_S)
    except asyncio.TimeoutError:
        log.warning("extraction timed out", extra={"f": {"file": name, "timeout_s": TIMEOUT_S}})
        raise HTTPException(504, f"extraction exceeded {TIMEOUT_S:.0f} s") from None
    except UnsupportedFormat as e:
        raise HTTPException(415, str(e)) from e
    except (UnreadableDocument, TooManyPages) as e:
        raise HTTPException(422, str(e)) from e
    except Exception as e:  # noqa: BLE001
        log.exception("extraction failed", extra={"f": {"file": name}})
        raise HTTPException(500, "extraction failed") from e
    out["_meta"] = legacy_meta(out)
    log.ok("resume extracted", extra={"f": {"file": name, "bytes": len(data), "ms": round((time.perf_counter() - t_start) * 1000), "debug": debug or None}})
    return JSONResponse(out)
