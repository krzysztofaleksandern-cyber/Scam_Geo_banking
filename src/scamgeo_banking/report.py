from __future__ import annotations
import csv
from pathlib import Path
from typing import List

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas


def _read_rows(paths: List[Path]) -> List[dict]:
    rows: List[dict] = []
    for p in paths:
        if not p.exists():
            continue
        with p.open("r", encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f)
            for r in rd:
                r["_source_file"] = p.name
                rows.append(r)
    return rows


def _count_by_label(rows: List[dict]) -> dict:
    agg = {"scam": 0, "watch": 0, "ok": 0}
    for r in rows:
        label = (r.get("label") or "").lower()
        if label in agg:
            agg[label] += 1
    return agg


def generate_pdf(inputs: List[Path], pdf_path: Path) -> Path:
    rows = _read_rows(inputs)
    agg = _count_by_label(rows)

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    c = Canvas(str(pdf_path), pagesize=A4)
    w, h = A4

    y = h - 20 * mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, y, "Scam_Geo Banking — Raport")
    y -= 8 * mm
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"Łącznie rekordów: {len(rows)}  |  Scam: {agg['scam']}  Watch: {agg['watch']}  OK: {agg['ok']}")

    y -= 12 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y, "Próbka (max 15):")
    y -= 6 * mm

    c.setFont("Helvetica", 8)
    shown = 0
    for r in rows:
        if shown >= 15:
            break
        title = r.get("title") or r.get("url") or r.get("source") or "—"
        url = r.get("url") or "—"
        label = r.get("label") or "—"
        line = f"[{label}] {title} | {url}"
        c.drawString(20 * mm, y, line[:120])
        y -= 5 * mm
        if y < 25 * mm:
            c.showPage()
            y = h - 20 * mm
            c.setFont("Helvetica", 8)
        shown += 1

    c.showPage()
    c.save()
    return pdf_path
