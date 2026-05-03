from __future__ import annotations

import asyncio
import sys
from collections import defaultdict
from datetime import datetime
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
    return sum(1 for ch in text if ch.isdigit()) == 0


def _doc_sort_key(doc: dict) -> tuple:
    created_at = doc.get('created_at')
    invoice_date = doc.get('invoice_date')
    return (
        created_at if isinstance(created_at, datetime) else datetime.max,
        invoice_date if isinstance(invoice_date, datetime) else datetime.max,
        str(doc.get('_id') or ''),
    )


async def main() -> None:
    client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['payment_tracking']
    collection = db['bills']

    bills = await collection.find({}, {'invoice_no': 1, 'created_at': 1, 'invoice_date': 1, '_id': 1}).to_list(length=None)

    grouped = defaultdict(list)
    invalid_ids = []
    for bill in bills:
        invoice_no = str(bill.get('invoice_no') or '').strip()
        if _looks_invalid_invoice_no(invoice_no):
            invalid_ids.append(bill['_id'])
            continue
        grouped[invoice_no].append(bill)

    duplicate_ids = []
    kept = {}
    for invoice_no, docs in grouped.items():
        docs_sorted = sorted(docs, key=_doc_sort_key)
        kept[invoice_no] = docs_sorted[0]['_id']
        duplicate_ids.extend(doc['_id'] for doc in docs_sorted[1:])

    total_delete = len(invalid_ids) + len(duplicate_ids)
    if total_delete == 0:
        print('No cleanup required')
        return

    deleted_invalid = 0
    deleted_duplicates = 0

    if invalid_ids:
        result = await collection.delete_many({'_id': {'$in': invalid_ids}})
        deleted_invalid = int(result.deleted_count or 0)

    if duplicate_ids:
        result = await collection.delete_many({'_id': {'$in': duplicate_ids}})
        deleted_duplicates = int(result.deleted_count or 0)

    print(f'invalid_deleted={deleted_invalid}')
    print(f'duplicate_deleted={deleted_duplicates}')
    print(f'kept_unique_invoices={len(kept)}')


if __name__ == '__main__':
    asyncio.run(main())