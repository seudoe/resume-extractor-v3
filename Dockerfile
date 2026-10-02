# Placeholder — filled in at Stage 14 (API service, Docker, HF Space).
# Target: python:3.11-slim, uv sync --frozen --no-dev, non-root user, port 7860.
FROM python:3.11-slim
WORKDIR /app
EXPOSE 7860
CMD ["python", "-c", "print('resume-extractor-v3: not implemented yet, see PROMPT.md Stage 14')"]
