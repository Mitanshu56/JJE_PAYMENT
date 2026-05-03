"""Backfill legacy records with fiscal year labels.

By default this tags records missing fiscal_year with the active fiscal year
so they appear in the selected FY dashboard. You can override the target FY
with --target-fy if you want to place legacy data into a different bucket.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
import sys
from pathlib import Path

import motor.motor_asyncio

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.fiscal import current_fiscal_year_label


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill missing fiscal_year values")
    parser.add_argument(
        "--target-fy",
        dest="target_fy",
        default=current_fiscal_year_label(),
        help="Fiscal year label to assign to legacy records (default: current FY)",
    )
    parser.add_argument(
        "--mongo-url",
        dest="mongo_url",
        default="mongodb://localhost:27017",
        help="MongoDB connection string",
    )
    parser.add_argument(
        "--db-name",
        dest="db_name",
        default="payment_tracking",
        help="MongoDB database name",
    )
    parser.add_argument(
        "--include-existing",
        action="store_true",
        help="Also rewrite records that already have a fiscal_year",
    )
    return parser


async def _backfill_collection(collection, target_fy: str, include_existing: bool) -> int:
    query = {} if include_existing else {"$or": [{"fiscal_year": {"$exists": False}}, {"fiscal_year": None}, {"fiscal_year": ""}]}
    update_result = await collection.update_many(
        query,
        {
            "$set": {
                "fiscal_year": target_fy,
                "updated_at": datetime.utcnow(),
            }
        },
    )
    return int(update_result.modified_count or 0)


async def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    client = motor.motor_asyncio.AsyncIOMotorClient(args.mongo_url)
    db = client[args.db_name]

    target_fy = args.target_fy.strip()
    if not target_fy:
        target_fy = current_fiscal_year_label()

    bills_count = await _backfill_collection(db["bills"], target_fy, args.include_existing)
    payments_count = await _backfill_collection(db["payments"], target_fy, args.include_existing)
    uploads_count = await _backfill_collection(db["upload_logs"], target_fy, args.include_existing)

    await db["fiscal_years"].update_one(
        {"value": target_fy},
        {
            "$setOnInsert": {
                "value": target_fy,
                "label": f"FY {target_fy}",
                "created_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )

    print(
        f"Backfilled fiscal_year={target_fy}: bills={bills_count}, payments={payments_count}, upload_logs={uploads_count}"
    )


if __name__ == "__main__":
    asyncio.run(main())