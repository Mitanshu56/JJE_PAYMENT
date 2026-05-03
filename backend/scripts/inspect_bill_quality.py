from __future__ import annotations

import asyncio
import sys
from collections import Counter
from pathlib import Path

import motor.motor_asyncio

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _looks_invalid_invoice_no(value: str) -> bool:
    text = str(value or '').strip()
    if not text:
        return True
    lowered = text.lower()
    if lowered in {'date', 'invoice', 'n/a', 'na', 'none'}:
        return True
    digit_count = sum(1 for ch in text if ch.isdigit())
    return digit_count == 0


async def main() -> None:
    client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['payment_tracking']
    bills = await db['bills'].find({}, {'invoice_no': 1, 'party_name': 1, 'invoice_date': 1, 'fiscal_year': 1, '_id': 1}).to_list(length=None)

    counter = Counter(str(b.get('invoice_no') or '').strip() for b in bills)
    duplicates = sorted([key for key, count in counter.items() if count > 1])
    invalid = [b for b in bills if _looks_invalid_invoice_no(str(b.get('invoice_no') or ''))]

    print(f'total={len(bills)}')
    print(f'duplicate_invoice_nos={len(duplicates)}')
    for key in duplicates[:50]:
        print(f'duplicate:{key} count={counter[key]}')
    print(f'invalid_rows={len(invalid)}')
    for row in invalid[:100]:
        print(row)


if __name__ == '__main__':
    asyncio.run(main())