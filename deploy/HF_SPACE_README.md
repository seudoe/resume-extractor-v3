---
title: Resume Extractor v3
emoji: 📄
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

LLM-free resume extractor (PDF / DOCX -> iFind `ParsedResumeData` JSON). `POST /extract` with a multipart `file`.

    curl -X POST "$SPACE_URL/extract" -F "file=@resume.pdf"            # add ?debug=true or ?confidence=true
    curl "$SPACE_URL/health"
