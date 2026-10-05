```mermaid

flowchart TD

%% =========================================================
%% INPUT
%% =========================================================

PDF["📄 Resume PDF"]
DOCX["📄 Resume DOCX"]

INPUT{"Input format?"}

PDF --> INPUT
DOCX --> INPUT


%% =========================================================
%% INGESTION
%% =========================================================

INPUT -->|PDF| PDF_INGEST["PDF Ingestion"]

PDF_INGEST --> PYMUPDF["PyMuPDF<br/>fitz<br/><br/>PDF text + spans + fonts + coordinates + links + drawings"]

INPUT -->|DOCX| DOCX_INGEST["DOCX Ingestion"]

DOCX_INGEST --> PYDOCX["python-docx<br/><br/>Paragraphs + runs + styles"]


%% =========================================================
%% PDF TEXT QUALITY
%% =========================================================

PYMUPDF --> QUALITY["Text Quality Check"]

QUALITY --> TEXT_OK{"Usable text<br/>with coordinates?"}

TEXT_OK -->|YES| PDF_SPANS["Extract PDF Spans"]
TEXT_OK -->|NO / SCANNED| RENDER["Render PDF Page<br/>~300 DPI"]

RENDER --> OCR_CHOICE{"OCR Engine"}

OCR_CHOICE -->|Option A| RAPIDOCR["RapidOCR<br/>PaddleOCR models<br/>ONNX Runtime"]
OCR_CHOICE -->|Option B| TESSERACT["Tesseract OCR"]

RAPIDOCR --> OCR_OUTPUT["OCR Text + Bounding Boxes"]
TESSERACT --> OCR_OUTPUT

PDF_SPANS --> PDF_META["Font + Layout Metadata"]
OCR_OUTPUT --> OCR_META["OCR Layout Metadata"]


%% =========================================================
%% DOCUMENT IR
%% =========================================================

PDF_META --> IR
OCR_META --> IR
PYDOCX --> IR

IR["📦 Document IR<br/>Intermediate Representation"]

IR --> PAGE["Page"]
PAGE --> BLOCK["Block"]
BLOCK --> LINE["Line"]
LINE --> SPAN["Span"]

%% FIXED: Collapsed to a single line
SPAN --> SPAN_DATA["Span data:<br/>text<br/>font<br/>font size<br/>bold / italic<br/>color<br/>bounding box<br/>page number"]

LINE --> PROVENANCE["Provenance<br/>source page + line IDs + character spans"]


%% =========================================================
%% LAYOUT ANALYSIS
%% =========================================================

IR --> LAYOUT["🧭 Layout Analysis"]

LAYOUT --> XYCUT["Recursive XY-Cut<br/><br/>Detect whitespace / gutters<br/>→ split page into regions / columns"]

XYCUT --> REGIONS["Page Regions / Columns"]

REGIONS --> READING["Reading Order"]

READING --> LINE_IDS["Ordered Line IDs<br/><br/>L0, L1, L2 ... Ln"]

LINE_IDS --> POINTER["🔗 Pointer-Based Representation<br/><br/>Models/rules return line IDs<br/>instead of generating text"]


%% =========================================================
%% PARALLEL HEADER / SECTION / LINK PROCESSING
%% =========================================================

LINE_IDS --> PARALLEL{"Parallel Extraction"}

PARALLEL --> HEADER["Header Extraction"]
PARALLEL --> SECTIONS["Section Segmentation"]
PARALLEL --> LINKS["Link Extraction"]
PARALLEL --> CONTACT["Contact Extraction"]


%% =========================================================
%% HEADER
%% =========================================================

HEADER --> NAME_RULES["Name Heuristics<br/><br/>• largest font<br/>• top of page<br/>• bold<br/>• 1–5 words<br/>• alphabetic<br/>• no @ / URL"]

NAME_RULES --> NAME["👤 Name"]

HEADER --> TITLE["Professional Title<br/>Rule-based / context-based"]


%% =========================================================
%% CONTACT
%% =========================================================

CONTACT --> EMAIL_REGEX["Email Regex"]
CONTACT --> PHONE_LIB["phonenumbers<br/>Python library"]
CONTACT --> LOCATION_RULES["Location Rules / Extraction"]

EMAIL_REGEX --> EMAIL["📧 Email"]
PHONE_LIB --> PHONE["📱 Normalized Phone"]
LOCATION_RULES --> LOCATION["📍 Location"]


%% =========================================================
%% LINKS
%% =========================================================

LINKS --> PDF_LINKS["PyMuPDF<br/>page.get_links()"]

LINKS --> URL_REGEX["URL Detection<br/>Regex / text scanning"]

PDF_LINKS --> LINK_MERGE["Merge / Normalize Links"]
URL_REGEX --> LINK_MERGE

LINK_MERGE --> LINKEDIN["LinkedIn"]
LINK_MERGE --> GITHUB["GitHub"]
LINK_MERGE --> PORTFOLIO["Portfolio / Website"]


%% =========================================================
%% SECTION SEGMENTATION
%% =========================================================

SECTIONS --> SECTION_HEADING["Identify Heading Lines"]

SECTION_HEADING --> SYNONYMS["Section Synonym Dictionary"]

SYNONYMS --> RAPIDFUZZ["RapidFuzz<br/>Fuzzy String Matching"]

RAPIDFUZZ --> SECTION_RULE_RESULT["Rule-Based Section Classification"]

%% FIXED: Collapsed to a single line
SECTION_HEADING --> SECTION_FEATURES["Heading Features:<br/>font size<br/>bold<br/>ALL CAPS<br/>spacing<br/>color<br/>text content<br/>rule/border below"]

SECTION_FEATURES --> CLASSIFIER_CHOICE{"Optional Learned<br/>Section Classifier"}

CLASSIFIER_CHOICE -->|Logistic Regression| LOGREG["Logistic Regression"]
CLASSIFIER_CHOICE -->|LightGBM| LIGHTGBM["LightGBM<br/>Gradient-Boosted Trees"]
CLASSIFIER_CHOICE -->|DeBERTa option| DEBERTA["DeBERTa<br/>Token / Sequence Classifier"]

SECTION_RULE_RESULT --> SECTION_MERGE["Section Decision"]
LOGREG --> SECTION_MERGE
LIGHTGBM --> SECTION_MERGE
DEBERTA --> SECTION_MERGE

SECTION_MERGE --> EDUCATION["🎓 Education Section"]
SECTION_MERGE --> EXPERIENCE["💼 Work / Experience Section"]
SECTION_MERGE --> PROJECTS["🛠 Projects Section"]
SECTION_MERGE --> SKILLS["⚙ Skills Section"]
SECTION_MERGE --> AWARDS["🏆 Awards Section"]
SECTION_MERGE --> CERTS["📜 Certifications Section"]
SECTION_MERGE --> INTERESTS["⭐ Interests Section"]
SECTION_MERGE --> OTHER["Other Sections"]


%% =========================================================
%% ENTRY SEGMENTATION
%% =========================================================

EDUCATION --> ENTRY_EDU["Education Entry Segmentation"]
EXPERIENCE --> ENTRY_WORK["Work Entry Segmentation"]
PROJECTS --> ENTRY_PROJECT["Project Entry Segmentation"]
AWARDS --> ENTRY_AWARD["Award Entry Segmentation"]
CERTS --> ENTRY_CERT["Certification Entry Segmentation"]


%% =========================================================
%% RULE-BASED ENTRY EXTRACTION
%% =========================================================

ENTRY_EDU --> RULES_EDU["Rule-Based Extraction"]
ENTRY_WORK --> RULES_WORK["Rule-Based Extraction"]
ENTRY_PROJECT --> RULES_PROJECT["Rule-Based Extraction"]

RULES_EDU --> DATE_RULES["Date / Date-Range Rules"]
RULES_WORK --> DATE_RULES
RULES_PROJECT --> DATE_RULES

DATE_RULES --> DATEPARSER["dateparser<br/>Human Date Parsing"]

DATEPARSER --> NORMALIZED_DATES["Normalized Dates<br/>YYYY-MM-DD"]


%% =========================================================
%% GLINER EXTRACTION
%% =========================================================

ENTRY_EDU --> GLINER_CHECK{"Rules sufficient?"}
ENTRY_WORK --> GLINER_CHECK
ENTRY_PROJECT --> GLINER_CHECK

GLINER_CHECK -->|YES| RULE_RESULT["Use Rule Result"]
GLINER_CHECK -->|NO| GLINER["GLiNER2<br/>fastino/gliner2.5-base-v1"]

%% FIXED: Collapsed to a single line
GLINER --> ENTITY_LABELS["Flexible Entity Labels:<br/>company<br/>title<br/>institution<br/>degree<br/>program<br/>location<br/>type"]

ENTITY_LABELS --> GLINER_SPANS["Entity Spans"]

GLINER_SPANS --> POINTER


%% =========================================================
%% EDUCATION
%% =========================================================

RULES_EDU --> EDU_FIELDS["Education Fields"]

EDU_FIELDS --> INSTITUTION["Institution"]
EDU_FIELDS --> DEGREE["Degree"]
EDU_FIELDS --> PROGRAM["Program / Course"]
EDU_FIELDS --> PERIOD["Period"]
EDU_FIELDS --> GPA["GPA / CGPA"]


%% =========================================================
%% WORK
%% =========================================================

RULES_WORK --> WORK_FIELDS["Work Fields"]

WORK_FIELDS --> COMPANY["Company"]
WORK_FIELDS --> JOB_TITLE["Job Title"]
WORK_FIELDS --> WORK_PERIOD["Employment Period"]
WORK_FIELDS --> RESPONSIBILITIES["Responsibilities / Bullets"]


%% =========================================================
%% PROJECTS
%% =========================================================

RULES_PROJECT --> PROJECT_FIELDS["Project Fields"]

PROJECT_FIELDS --> PROJECT_NAME["Project Name"]
PROJECT_FIELDS --> PROJECT_DESC["Description"]
PROJECT_FIELDS --> PROJECT_TECH["Technologies"]
PROJECT_FIELDS --> PROJECT_PERIOD["Project Period"]


%% =========================================================
%% SKILLS
%% =========================================================

SKILLS --> SKILL_EXTRACT["Skill Extraction"]

SKILL_EXTRACT --> SKILL_DICT["Skill Dictionary"]
SKILL_DICT --> ALIAS["Alias / Taxonomy Mapping"]

SKILL_EXTRACT --> AHO["Aho-Corasick<br/>Multi-Pattern Matching"]

AHO --> SKILL_MATCHES["Detected Skill Mentions"]

ALIAS --> SKILL_NORMALIZE["Skill Normalization"]

SKILL_MATCHES --> SKILL_NORMALIZE

SKILL_NORMALIZE --> SKILLS_FINAL["Normalized Skills"]


%% =========================================================
%% AWARDS
%% =========================================================

AWARDS --> AWARD_RULES["Keyword / Context Rules"]

%% FIXED: Collapsed to a single line
AWARD_RULES --> AWARD_KEYWORDS["winner<br/>1st / 2nd / 3rd<br/>rank<br/>finalist<br/>hackathon<br/>competition"]

AWARD_KEYWORDS --> AWARD_FINAL["Awards"]


%% =========================================================
%% CERTIFICATIONS
%% =========================================================

CERTS --> CERT_RULES["Certification Rules"]

%% FIXED: Collapsed to a single line
CERT_RULES --> CERT_KEYWORDS["certified<br/>certificate<br/>Coursera<br/>NPTEL<br/>Udemy<br/>credential"]

CERT_KEYWORDS --> CERT_FINAL["Certifications"]


%% =========================================================
%% NORMALIZATION
%% =========================================================

EDU_FIELDS --> NORMALIZE
WORK_FIELDS --> NORMALIZE
PROJECT_FIELDS --> NORMALIZE
SKILLS_FINAL --> NORMALIZE
AWARD_FINAL --> NORMALIZE
CERT_FINAL --> NORMALIZE
NAME --> NORMALIZE
EMAIL --> NORMALIZE
PHONE --> NORMALIZE
LOCATION --> NORMALIZE
LINK_MERGE --> NORMALIZE

NORMALIZE["🔧 Normalization Layer"]

NORMALIZE --> DATE_NORM["Date Normalization<br/>dateparser"]
NORMALIZE --> DEGREE_NORM["Degree Normalization"]
NORMALIZE --> SKILL_NORM["Skill Normalization"]
NORMALIZE --> AWARD_NORM["Award Normalization"]
NORMALIZE --> CERT_NORM["Certification Normalization"]
NORMALIZE --> TEXT_NORM["Text Normalization"]


%% =========================================================
%% GROUNDING
%% =========================================================

DATE_NORM --> GROUND
DEGREE_NORM --> GROUND
SKILL_NORM --> GROUND
AWARD_NORM --> GROUND
CERT_NORM --> GROUND
TEXT_NORM --> GROUND

GROUND["🛡 Grounding / Provenance Verification"]

GROUND --> EXACT["Exact Source Match"]

GROUND --> FUZZY["Fuzzy Source Match"]

FUZZY --> JARO["Jaro-Winkler Similarity"]

EXACT --> GROUND_DECISION
JARO --> GROUND_DECISION

GROUND_DECISION{"Value exists in<br/>source resume?"}

GROUND_DECISION -->|YES| GROUNDED["Keep + attach line ID / character span"]
GROUND_DECISION -->|NO| DROP["❌ Drop / Reject fabricated value"]

GROUNDED --> DEDUP


%% =========================================================
%% DEDUPLICATION
%% =========================================================

DEDUP["Entity Deduplication"]

DEDUP --> FUZZY_DEDUP["Fuzzy-Key Matching"]
FUZZY_DEDUP --> UNIQUE["Unique Entities"]


%% =========================================================
%% CONFIDENCE
%% =========================================================

UNIQUE --> CONFIDENCE["Confidence Scoring"]

CONFIDENCE --> CALIBRATION["Confidence Calibration<br/>Development Set"]

CALIBRATION --> CONFIDENT_DATA["Fields + Confidence Scores"]


%% =========================================================
%% VALIDATION
%% =========================================================

CONFIDENT_DATA --> PYDANTIC["Pydantic v2"]

PYDANTIC --> SCHEMA["ParsedResumeData Schema"]

SCHEMA --> VALID{"Schema Valid?"}

VALID -->|NO| ERROR["Validation Error"]
VALID -->|YES| JSON["📦 ParsedResumeData JSON"]


%% =========================================================
%% API / DEPLOYMENT
%% =========================================================

JSON --> FASTAPI["FastAPI<br/>/extract"]

FASTAPI --> UVICORN["Uvicorn<br/>ASGI Server"]

UVICORN --> DOCKER["Docker<br/>python:3.11-slim"]

DOCKER --> HF["Hugging Face Space<br/>2 vCPU / 16 GB RAM / No GPU"]

HF --> IFIND["iFind Application"]


%% =========================================================
%% OPTIONAL SLM PATH
%% =========================================================

GLINER_CHECK -.->|Optional fallback if justified| SLM_CHECK{"Optional SLM<br/>enabled?"}

SLM_CHECK -->|NO| RULE_RESULT

SLM_CHECK -->|YES| SLM["Small Language Model"]

SLM --> QWEN["Qwen3-0.6B / Qwen3-1.7B"]
SLM --> NUEXTRACT["NuExtract-tiny"]

QWEN --> GGUF["GGUF Model Format"]
NUEXTRACT --> GGUF

GGUF --> LLAMACPP["llama.cpp<br/>CPU Inference"]

LLAMACPP --> SECTION_PROMPT["Process ONE section<br/>not entire resume"]

SECTION_PROMPT --> SLM_POINTER["Return source line pointers"]

SLM_POINTER --> POINTER


%% =========================================================
%% TRAINING DATA PIPELINE
%% =========================================================

subgraph TRAINING["🧠 Offline Training / Model Improvement"]

LIVECAREER["LiveCareer<br/>PDF + HTML"]
SYNTH["Synthetic Resume Generator"]
GOLD["Gold Set<br/>Real Human-Verified Resumes"]

LIVECAREER --> ALIGN["HTML ↔ PDF Alignment"]
ALIGN --> TRAIN_DATA["Training Examples"]

SYNTH --> TEMPLATES["10+ Resume Template Families"]
TEMPLATES --> SYNTH_PDF["Synthetic PDF"]
SYNTH_PDF --> SYNTH_GT["Known Ground Truth"]
SYNTH_GT --> TRAIN_DATA

TRAIN_DATA --> GLINER_TRAIN["GLiNER2 Fine-Tuning"]

GLINER_TRAIN --> LORA["LoRA<br/>Low-Rank Adaptation"]

LORA --> RTX["RTX 2050 / Kaggle T4"]
RTX --> TRAINED_MODEL["Fine-Tuned GLiNER Model"]

TRAINED_MODEL --> GLINER

end


%% =========================================================
%% EVALUATION
%% =========================================================

subgraph EVAL["📊 Evaluation / Benchmarking"]

GOLD --> METRICS["Evaluation Metrics"]

METRICS --> NAME_ACC["Name Accuracy"]
METRICS --> ENTITY_F1["Entity Precision / Recall / F1"]
METRICS --> TOKEN_F1["Token F1"]
METRICS --> HALLUCINATION["Hallucination Rate"]
METRICS --> SCHEMA_VALID["Schema Validity"]
METRICS --> DETERMINISM["Determinism"]
METRICS --> LATENCY["Latency<br/>p50 / p95 / max"]
METRICS --> MEMORY["RAM / CPU"]
METRICS --> THROUGHPUT["Throughput"]

ENTITY_F1 --> HUNGARIAN["Hungarian Algorithm<br/>scipy.optimize.linear_sum_assignment"]

TOKEN_F1 --> TOKEN_COMPARE["Token Comparison"]

METRICS --> CERWER["CER / WER<br/>jiwer"]

end


%% =========================================================
%% TESTING
%% =========================================================

subgraph TESTING["🧪 Testing"]

PYTEST["pytest"]
UNIT["Unit Tests"]
INTEGRATION["Integration Tests"]
REGRESSION["Regression Tests"]

PYTEST --> UNIT
PYTEST --> INTEGRATION
PYTEST --> REGRESSION

UNIT --> CI["Automated CI"]
INTEGRATION --> CI
REGRESSION --> CI

end


%% =========================================================
%% PERFORMANCE / BENCHMARKING
%% =========================================================

subgraph BENCH["⚡ Performance Benchmarking"]

PSUTIL["psutil<br/>CPU / RAM"]
DOCKER_BENCH["Docker Resource Limits"]
BENCH_SUITE["Benchmark Suite"]

BENCH_SUITE --> PSUTIL
BENCH_SUITE --> DOCKER_BENCH

RAPIDOCR --> BENCH_SUITE
TESSERACT --> BENCH_SUITE

end


%% =========================================================
%% STYLE
%% =========================================================

classDef input fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
classDef parser fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
classDef ml fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
classDef algo fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
classDef validation fill:#fce4ec,stroke:#c2185b,stroke-width:2px
classDef deployment fill:#ede7f6,stroke:#512da8,stroke-width:2px
classDef evaluation fill:#fff8e1,stroke:#ff8f00,stroke-width:2px
classDef output fill:#e0f2f1,stroke:#00695c,stroke-width:3px

class PDF,DOCX input
class PYMUPDF,PYDOCX,RAPIDOCR,TESSERACT,FASTAPI,UVICORN,DOCKER,HF parser
class GLINER,LOGREG,LIGHTGBM,DEBERTA,QWEN,NUEXTRACT,LORA ml
class XYCUT,RAPIDFUZZ,AHO,JARO,HUNGARIAN,LLAMACPP algo

%% FIXED: Changed Pydantic to PYDANTIC (to match node ID)
class PYDANTIC,GROUND,VALID validation

%% FIXED: Changed ParsedResumeData to SCHEMA (to match node ID)
class JSON,SCHEMA output

class GOLD,METRICS,NAME_ACC,ENTITY_F1,TOKEN_F1,HALLUCINATION,LATENCY evaluation

```