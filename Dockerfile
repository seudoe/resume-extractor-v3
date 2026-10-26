# resume-extractor-v3 service (PROMPT.md Stage 14). Build:  docker build -t rx3 --build-arg GIT_SHA=$(git rev-parse --short HEAD) .
# Run:   docker run --rm --cpus=2 --memory=16g -p 7860:7860 rx3     (HF Space: port 7860, 2 vCPU / 16 GB)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy \
    HF_HOME=/opt/hf TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=2 RX3_TORCH_THREADS=2 RX3_ENABLE_GLINER=1 \
    PATH=/app/.venv/bin:$PATH

# tesseract: OCR fallback for scanned PDFs. libgomp: OpenMP runtime for torch. (LibreOffice for legacy .doc is NOT installed:
# it adds ~500 MB; without it .doc uploads get a clear 415. Add `libreoffice-writer` here if you want .doc support.)
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.12.22 /uv /bin/uv
WORKDIR /app

# 1) dependencies only (cached layer): CPU torch on Linux comes from the pytorch-cpu index pinned in uv.lock
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --extra gliner

# 2) code, schema types, the versioned LoRA adapter
COPY src ./src
COPY types ./types
COPY scripts ./scripts
COPY models/adapters ./models/adapters
COPY models/MODEL_CHECKSUMS.txt ./models/MODEL_CHECKSUMS.txt
RUN uv sync --frozen --no-dev --extra gliner

# 3) bake the pinned base model into the image and verify checksums (build fails on a mismatch); run offline afterwards
RUN python scripts/fetch_models.py
ENV HF_HUB_OFFLINE=1

COPY GIT_SHA* ./
ARG GIT_SHA=unknown
ENV RX3_GIT_SHA=$GIT_SHA

RUN useradd -m -u 1000 app && chown -R app:app /app /opt/hf
USER app
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:7860/health', timeout=4).status == 200 else 1)"
CMD ["uvicorn", "rx3.api:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
