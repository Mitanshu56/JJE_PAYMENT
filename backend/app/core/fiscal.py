"""Fiscal year helper utilities."""
from datetime import date, datetime


def fiscal_year_label_from_date(dt: date | datetime) -> str:
    y = dt.year
    m = dt.month
    if m >= 4:
        return f"FY-{y}-{y+1}"
    return f"FY-{y-1}-{y}"


def current_fiscal_year_label() -> str:
    return fiscal_year_label_from_date(date.today())
