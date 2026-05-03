from __future__ import annotations

import asyncio
import sys
from collections import Counter
from pathlib import Path

import motor.motor_asyncio

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


async def main() -> None:
    client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['payment_tracking']
    bills = await db['bills'].find({}, {'invoice_no': 1, 'party_name': 1, 'invoice_date': 1, 'created_at': 1, 'updated_at': 1, 'fiscal_year': 1, '_id': 1}).to_list(length=None)
    counter = Counter(str(b.get('invoice_no') or '').strip() for b in bills)
    duplicates = sorted([key for key, count in counter.items() if count > 1])

    print(f'duplicate_keys={len(duplicates)}')
    for key in duplicates:
        docs = [b for b in bills if str(b.get('invoice_no') or '').strip() == key]
        print(f'=== invoice_no={key} ===')
        for doc in docs:
            print(doc)


if __name__ == '__main__':
    asyncio.run(main())