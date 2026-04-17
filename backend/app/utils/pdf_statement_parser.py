"""
PDF statement parsing utilities.
Extracts only credited/deposit rows with required columns.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, List, Optional

import pdfplumber


DATE_RE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")


def _normalize_text(value) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").strip()
    return re.sub(r"\s+", " ", text)


def _parse_date(value: str) -> Optional[datetime]:
    if not value:
        return None

    raw = value.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue

    matched = DATE_RE.search(raw)
    if matched:
        token = matched.group(1)
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
            try:
                return datetime.strptime(token, fmt)
            except ValueError:
                continue

    return None


def _parse_amount(value: str) -> float:
    if not value:
        return 0.0

    cleaned = str(value).upper().replace(",", "").replace("₹", "").strip()

    # Ignore debit markers for deposit extraction.
    if " DR" in cleaned or cleaned.endswith("DR"):
        return 0.0

    numbers = re.findall(r"-?\d+(?:\.\d+)?", cleaned)
    if not numbers:
        return 0.0

    amount = float(numbers[-1])
    return amount if amount > 0 else 0.0


def _find_header_map(rows: List[List[str]]) -> Optional[Dict[str, int]]:
    for row in rows:
        normalized = [_normalize_text(cell).lower() for cell in row]

        value_idx = next((i for i, cell in enumerate(normalized) if "value date" in cell or cell == "date"), None)
        narration_idx = next((i for i, cell in enumerate(normalized) if "narration" in cell or "description" in cell), None)
        ref_idx = next((i for i, cell in enumerate(normalized) if "cheque" in cell or "ref" in cell or "utr" in cell), None)
        deposit_idx = next((i for i, cell in enumerate(normalized) if "deposit" in cell or "credit" in cell), None)

        if value_idx is not None and narration_idx is not None and deposit_idx is not None:
            return {
                "value_date": value_idx,
                "narration": narration_idx,
                "reference": ref_idx,
                "deposit": deposit_idx,
            }
    return None


class PDFStatementParser:
    """Parser for bank statement PDFs."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def parse(self) -> List[Dict]:
        entries: List[Dict] = []

        with pdfplumber.open(self.file_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables() or []
                for table in tables:
                    rows = [[_normalize_text(cell) for cell in row] for row in table if row]
                    if not rows:
                        continue

                    header_map = _find_header_map(rows)
                    if not header_map:
                        continue

                    header_row_idx = next(
                        (
                            idx
                            for idx, row in enumerate(rows)
                            if _normalize_text(row[header_map["value_date"]]).lower() in ("value date", "date")
                            or "value date" in _normalize_text(row[header_map["value_date"]]).lower()
                        ),
                        0,
                    )

                    for row in rows[header_row_idx + 1 :]:
                        value_date_raw = row[header_map["value_date"]] if header_map["value_date"] < len(row) else ""
                        narration_raw = row[header_map["narration"]] if header_map["narration"] < len(row) else ""
                        deposit_raw = row[header_map["deposit"]] if header_map["deposit"] < len(row) else ""
                        reference_raw = ""
                        if header_map["reference"] is not None and header_map["reference"] < len(row):
                            reference_raw = row[header_map["reference"]]

                        value_date = _parse_date(value_date_raw)
                        if not value_date:
                            continue

                        deposit = _parse_amount(deposit_raw)
                        if deposit <= 0:
                            continue

                        narration = _normalize_text(narration_raw)
                        reference = _normalize_text(reference_raw)

                        month_key = value_date.strftime("%Y-%m")
                        month_label = value_date.strftime("%b %Y")

                        entries.append(
                            {
                                "value_date": value_date,
                                "value_date_display": value_date.strftime("%d/%m/%Y"),
                                "narration": narration,
                                "reference": reference,
                                "deposit": deposit,
                                "month_key": month_key,
                                "month_label": month_label,
                            }
                        )

        # Deduplicate exact duplicates from repeated page table extraction.
        unique = {}
        for row in entries:
            key = (
                row["value_date_display"],
                row.get("narration", ""),
                row.get("reference", ""),
                round(float(row.get("deposit", 0.0)), 2),
            )
            unique[key] = row

        return list(unique.values())
