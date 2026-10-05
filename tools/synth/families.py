"""Template families for the synthetic resume renderer (PROMPT.md §5 Stage 10.1).

A family is a fixed combination of: page layout, section-header style, work-entry style, education-entry style, font stack,
colours and bullet glyph. Splits are made by family (whole families held out), so the families must differ in *structure*,
not just in colour. Twelve families; `TEST_FAMILIES` / `DEV_FAMILIES` are never used for training.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Family:
    name: str
    layout: str  # single | sidebar-left | sidebar-right | banner | table
    header: str  # caps-rule | bold-color | smallcaps | plain-bold | boxed
    work: str  # W1..W7 (see render.py)
    edu: str  # E1..E5
    font: str
    color: str
    bullet: str
    size: float = 10.5


FAMILIES = [
    Family("classic", "single", "caps-rule", "W1", "E1", "Georgia, 'Times New Roman', serif", "#222", "•"),
    Family("jake", "single", "smallcaps", "W2", "E1", "'Times New Roman', serif", "#000", "•", 10.0),
    Family("sidebar_left", "sidebar-left", "bold-color", "W1", "E4", "Calibri, Arial, sans-serif", "#1f4e79", "▪"),
    Family("sidebar_right", "sidebar-right", "caps-rule", "W6", "E3", "'Segoe UI', Arial, sans-serif", "#7a1f3d", "–"),
    Family("banner", "banner", "bold-color", "W7", "E5", "'Trebuchet MS', Arial, sans-serif", "#0b6e4f", "●"),
    Family("indian_student", "single", "plain-bold", "W3", "E2", "Arial, Helvetica, sans-serif", "#111", "•", 10.0),
    Family("timeline", "table", "plain-bold", "W4", "E4", "Cambria, Georgia, serif", "#333", "•"),
    Family("plain_stacked", "single", "plain-bold", "W5", "E4", "Verdana, Arial, sans-serif", "#000", "-", 10.0),
    Family("boxed", "single", "boxed", "W2", "E5", "Tahoma, Arial, sans-serif", "#2c3e50", "◦"),
    Family("compact", "single", "bold-color", "W3", "E3", "Arial, sans-serif", "#444", "•", 9.5),
    Family("modern_two_line", "single", "caps-rule", "W6", "E1", "'Segoe UI', Calibri, sans-serif", "#34495e", "›"),
    Family("tagline_stacked", "single", "caps-rule", "W8", "E5", "Calibri, Arial, sans-serif", "#222", "●"),  # company+location / tagline / title / dates
    Family("company_row", "single", "bold-color", "W9", "E1", "'Segoe UI', Arial, sans-serif", "#1b4f72", "•"),  # "Company, City ... dates" then the title
    Family("table_docx", "table", "caps-rule", "W1", "E2", "Calibri, Arial, sans-serif", "#000", "•"),
]
BY_NAME = {f.name: f for f in FAMILIES}
TEST_FAMILIES = {"jake", "table_docx", "banner"}  # structure the model never sees in training
DEV_FAMILIES = {"boxed", "modern_two_line"}
# Tagline-style families: adding them (v2 adapter) did NOT help on the 32-resume gold (work F1 .776 vs .801) and one of three
# runs went unstable, so they are excluded from the default training mix; `build_gliner_data.py --include-extra` brings them back.
EXTRA_FAMILIES = {"tagline_stacked", "company_row"}
TRAIN_FAMILIES = {f.name for f in FAMILIES} - TEST_FAMILIES - DEV_FAMILIES - EXTRA_FAMILIES
