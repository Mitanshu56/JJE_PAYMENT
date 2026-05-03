"""Migrate fiscal year values in database.

Usage:
  python migrate_fy.py --yes

This script updates documents referencing the old fiscal year to the new value.
It uses settings from app.core.config to connect to MongoDB.
"""
from datetime import datetime
import argparse
import sys

from pymongo import MongoClient

from app.core.config import settings


OLD_FY = "FY-2026-2027"
NEW_FY = "FY-2025-2026"


def connect():
    url = settings.MONGODB_URL
    dbname = settings.MONGODB_DB_NAME
    client = MongoClient(url)
    db = client[dbname]
    return db


def summarize_counts(db, old, new):
    collections = [
        ("fiscal_years", "value"),
        ("bills", "fiscal_year"),
        ("payments", "fiscal_year"),
        ("statement_entries", "fiscal_year"),
        ("upload_logs", "fiscal_year"),
    ]

    summary = {}
    for coll_name, field in collections:
        coll = db[coll_name]
        old_count = coll.count_documents({field: old})
        new_count = coll.count_documents({field: new})
        summary[coll_name] = {"field": field, "old_count": old_count, "new_count": new_count}
    return summary


def run_migration(db, old, new, do_delete_old=True):
    results = {}

    # Ensure new fiscal_year master exists
    fy_col = db["fiscal_years"]
    if fy_col.count_documents({"value": new}) == 0:
        inserted = fy_col.insert_one({
            "value": new,
            "label": new,
            "status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
        results["fiscal_years_inserted"] = 1
    else:
        results["fiscal_years_inserted"] = 0

    # Update target collections
    target_cols = [
        ("bills", "fiscal_year"),
        ("payments", "fiscal_year"),
        ("statement_entries", "fiscal_year"),
        ("upload_logs", "fiscal_year"),
    ]

    for coll_name, field in target_cols:
        coll = db[coll_name]
        res = coll.update_many({field: old}, {"$set": {field: new}})
        results[f"{coll_name}_matched"] = int(res.matched_count)
        results[f"{coll_name}_modified"] = int(res.modified_count)

    # Update fiscal_years master doc: remove old entry
    if do_delete_old:
        del_res = fy_col.delete_many({"value": old})
        results["fiscal_years_deleted"] = int(del_res.deleted_count)

    return results


def print_summary(summary):
    print("Current counts:")
    for coll, info in summary.items():
        print(f" - {coll}: {info['old_count']} entries with OLD, {info['new_count']} with NEW")


def main():
    parser = argparse.ArgumentParser(description="Migrate fiscal year values in DB")
    parser.add_argument("--yes", action="store_true", help="Apply changes without interactive confirmation")
    args = parser.parse_args()

    print(f"Connecting to {settings.MONGODB_URL} / {settings.MONGODB_DB_NAME}")
    db = connect()

    summary = summarize_counts(db, OLD_FY, NEW_FY)
    print_summary(summary)

    if not args.yes:
        confirm = input(f"Proceed to migrate {OLD_FY} -> {NEW_FY}? Type YES to continue: ")
        if confirm.strip().upper() != "YES":
            print("Aborted by user.")
            sys.exit(1)

    print("Running migration...")
    results = run_migration(db, OLD_FY, NEW_FY)

    print("Migration results:")
    for k, v in results.items():
        print(f" - {k}: {v}")

    final = summarize_counts(db, OLD_FY, NEW_FY)
    print("Final counts:")
    print_summary(final)


if __name__ == "__main__":
    main()
