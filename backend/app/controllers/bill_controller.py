"""
Bill controller for handling bill-related business logic
"""
from typing import List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.bill import Bill, BillStatus
from bson import ObjectId
import re
import logging

logger = logging.getLogger(__name__)


class BillController:
    """Controller for bill operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db['bills']

    def _normalize_text(self, value: Optional[str]) -> str:
        return str(value or '').strip().lower()

    def _build_invoice_key(self, bill_data: dict) -> str:
        """
        Build a stable identity key for invoice upserts.

        Important: exclude mutable fields (like invoice_date) so edits in source
        files update an existing record instead of creating a new one.
        """
        invoice_no = self._normalize_text(bill_data.get('invoice_no'))
        party_name = self._normalize_text(bill_data.get('party_name'))
        site = self._normalize_text(bill_data.get('site'))
        return f"{invoice_no}|{party_name}|{site}"

    async def _find_legacy_matching_bill(self, bill_data: dict, exclude_id: Optional[ObjectId] = None) -> Optional[dict]:
        """Find old records created before stable key logic (or with stale keys)."""
        invoice_no = self._normalize_text(bill_data.get('invoice_no'))
        party_name = self._normalize_text(bill_data.get('party_name'))
        site = self._normalize_text(bill_data.get('site'))

        if not invoice_no:
            return None

        fallback_query = {
            'invoice_no_norm': invoice_no,
            'party_name_norm': party_name,
            'site_norm': site,
        }
        if exclude_id:
            fallback_query['_id'] = {'$ne': exclude_id}
        legacy = await self.collection.find_one(fallback_query)
        if legacy:
            return legacy

        # Backward-compatibility path for records that predate *_norm fields.
        escaped_invoice = re.escape(invoice_no)
        escaped_party = re.escape(party_name)
        escaped_site = re.escape(site)

        legacy_query = {
            'invoice_no': {'$regex': f'^{invoice_no}$', '$options': 'i'},
            'party_name': {'$regex': f'^{party_name}$', '$options': 'i'},
            '$or': [
                {'site': {'$exists': False}},
                {'site': None},
                {'site': ''},
                {'site': {'$regex': f'^{escaped_site}$', '$options': 'i'}},
            ],
        }
        legacy_query['invoice_no'] = {'$regex': f'^{escaped_invoice}$', '$options': 'i'}
        legacy_query['party_name'] = {'$regex': f'^{escaped_party}$', '$options': 'i'}
        if exclude_id:
            legacy_query['_id'] = {'$ne': exclude_id}

        return await self.collection.find_one(legacy_query)
    
    async def _consolidate_duplicate_keys(self, invoice_key: str) -> Optional[dict]:
        """
        Find and consolidate duplicate invoice_key records.
        Keeps the oldest record, merges payment data, deletes duplicates.
        Returns the consolidated record, or None if only one exists.
        """
        duplicates = await self.collection.find({'invoice_key': invoice_key})\
            .sort([('created_at', 1)])\
            .to_list(length=None)
        
        if len(duplicates) <= 1:
            return duplicates[0] if duplicates else None
        
        # Keep the first (oldest) record
        primary = duplicates[0]
        to_delete = duplicates[1:]
        
        # Merge payment data from duplicates into primary
        merged_payment_ids = set(primary.get('matched_payment_ids') or [])
        for dup in to_delete:
            merged_payment_ids.update(dup.get('matched_payment_ids') or [])
        
        await self.collection.update_one(
            {'_id': primary['_id']},
            {'$set': {'matched_payment_ids': list(merged_payment_ids)}}
        )
        
        # Delete duplicates
        for dup in to_delete:
            await self.collection.delete_one({'_id': dup['_id']})
        
        logger.info(f"✓ Consolidated {len(to_delete)} duplicate invoice_key records: {invoice_key}")
        return primary

    async def create_bill(self, bill_data: dict, fiscal_year: Optional[str] = None) -> dict:
        """Create a new bill and tag with fiscal year if provided or derivable."""
        try:
            # Attach timestamps
            bill_data['created_at'] = datetime.utcnow()
            bill_data['updated_at'] = datetime.utcnow()

            # Determine fiscal year: explicit param takes precedence, then invoice_date if present
            if fiscal_year:
                bill_data['fiscal_year'] = fiscal_year
            else:
                invoice_date = bill_data.get('invoice_date')
                if invoice_date:
                    try:
                        from app.core.fiscal import fiscal_year_label_from_date
                        bill_data['fiscal_year'] = fiscal_year_label_from_date(invoice_date)
                    except Exception:
                        pass

            result = await self.collection.insert_one(bill_data)
            bill_data['_id'] = result.inserted_id

            logger.info(f"✓ Created bill: {bill_data.get('invoice_no')}")
            return bill_data
        except Exception as e:
            logger.error(f"✗ Error creating bill: {str(e)}")
            raise

    async def create_bills_bulk(self, bills_data: List[dict], upload_batch_id: Optional[str] = None, fiscal_year: Optional[str] = None) -> dict:
        """Create or update multiple bills and return import statistics."""
        try:
            stats = {
                'total_in_file': len(bills_data),
                'new_records': 0,
                'updated_records': 0,
                'unchanged_records': 0,
                'skipped_records': 0,
            }

            for bill in bills_data:
                invoice_no = str(bill.get('invoice_no') or '').strip()
                if not invoice_no:
                    logger.warning("Skipping bill without invoice_no")
                    stats['skipped_records'] += 1
                    continue

                now = datetime.utcnow()
                grand_total = float(bill.get('grand_total') or 0.0)
                invoice_key = self._build_invoice_key(bill)
                invoice_no_norm = self._normalize_text(invoice_no)
                party_name_norm = self._normalize_text(bill.get('party_name') or 'Unknown Party')
                site_norm = self._normalize_text(bill.get('site'))

                # Determine fiscal year for this bill: explicit param wins, else derive from invoice_date if present
                bill_fiscal = fiscal_year
                if not bill_fiscal:
                    invoice_date_val = bill.get('invoice_date')
                    if invoice_date_val:
                        try:
                            from app.core.fiscal import fiscal_year_label_from_date
                            bill_fiscal = fiscal_year_label_from_date(invoice_date_val)
                        except Exception:
                            bill_fiscal = None

                set_doc = {
                    'invoice_key': invoice_key,
                    'invoice_no': invoice_no,
                    'invoice_no_norm': invoice_no_norm,
                    'party_name': bill.get('party_name', 'Unknown Party'),
                    'party_name_norm': party_name_norm,
                    'gst_no': bill.get('gst_no'),
                    'invoice_date': bill.get('invoice_date'),
                    'net_amount': float(bill.get('net_amount') or 0.0),
                    'cgst': float(bill.get('cgst') or 0.0),
                    'sgst': float(bill.get('sgst') or 0.0),
                    'grand_total': grand_total,
                    'site': bill.get('site'),
                    'site_norm': site_norm,
                    'last_upload_batch_id': upload_batch_id,
                    'last_seen_upload_at': now,
                    'updated_at': now,
                }

                # Attach fiscal year to both set and setOnInsert where available
                if bill_fiscal:
                    set_doc['fiscal_year'] = bill_fiscal
                    set_on_insert_doc = {
                        'created_at': now,
                        'status': BillStatus.UNPAID,
                        'paid_amount': 0.0,
                        'remaining_amount': grand_total,
                        'matched_payment_ids': [],
                        'fiscal_year': bill_fiscal,
                    }
                else:
                    set_on_insert_doc = {
                        'created_at': now,
                        'status': BillStatus.UNPAID,
                        'paid_amount': 0.0,
                        'remaining_amount': grand_total,
                        'matched_payment_ids': [],
                    }

                # Primary path: fast upsert by stable identity key.
                upserted_id = None
                modified_count = 0
                matched_count = 0

                try:
                    result = await self.collection.update_one(
                        {'invoice_key': invoice_key},
                        {
                            '$set': set_doc,
                            '$setOnInsert': set_on_insert_doc,
                        },
                        upsert=True
                    )
                    upserted_id = result.upserted_id
                    modified_count = result.modified_count
                    matched_count = result.matched_count
                except Exception as e:
                    # Handle E11000 duplicate key error by consolidating duplicates
                    if 'E11000' in str(e):
                        logger.warning(f"E11000 duplicate key for {invoice_key}, consolidating duplicates...")
                        # Consolidate all duplicate records with this invoice_key
                        await self._consolidate_duplicate_keys(invoice_key)

                        # After consolidation, find the consolidated record and update it
                        existing = await self.collection.find_one({'invoice_key': invoice_key})
                        if existing:
                            # Update the consolidated record
                            result = await self.collection.update_one(
                                {'_id': existing['_id']},
                                {'$set': set_doc},
                                upsert=False
                            )
                            modified_count = result.modified_count
                            matched_count = result.matched_count
                        else:
                            # If no record found after consolidation, insert new one
                            insert_doc = {**set_doc, **set_on_insert_doc}
                            insert_result = await self.collection.insert_one(insert_doc)
                            upserted_id = insert_result.inserted_id
                    else:
                        raise

                if upserted_id:
                    # If this was inserted, we may have matched a stale-key duplicate case.
                    # Attempt to merge into an older legacy record and drop the just-inserted duplicate.
                    legacy = await self._find_legacy_matching_bill(bill, exclude_id=upserted_id)
                    if legacy and str(legacy.get('_id')) != str(upserted_id):
                        await self.collection.update_one(
                            {'_id': legacy['_id']},
                            {
                                '$set': set_doc,
                                '$setOnInsert': set_on_insert_doc,
                            },
                            upsert=False,
                        )
                        await self.collection.delete_one({'_id': upserted_id})
                        stats['updated_records'] += 1
                        continue

                    stats['new_records'] += 1
                elif modified_count > 0:
                    stats['updated_records'] += 1
                elif matched_count > 0:
                    stats['unchanged_records'] += 1

            logger.info(
                "✓ Invoice import stats: "
                f"new={stats['new_records']}, "
                f"updated={stats['updated_records']}, "
                f"unchanged={stats['unchanged_records']}, "
                f"skipped={stats['skipped_records']}"
            )
            return stats
        except Exception as e:
            logger.error(f"✗ Error creating bills: {str(e)}")
            raise
    
    async def get_bill(self, invoice_no: str) -> Optional[dict]:
        """Get a bill by invoice number."""
        invoice_no = str(invoice_no or '').strip()
        if not invoice_no:
            return None

        return await self.collection.find_one({'invoice_no': invoice_no})
    
    async def get_bills(self, filters: dict = None, skip: int = 0, limit: int = 100) -> List[dict]:
        """Get bills with optional filters"""
        query = filters or {}
        # Use numeric collation so invoice numbers sort naturally: 1, 2, 3 ... 10.
        cursor = self.collection.find(query).sort([
            ('invoice_no', 1),
        ]).collation({
            'locale': 'en',
            'numericOrdering': True,
        }).skip(skip).limit(limit)
        bills = await cursor.to_list(length=limit)
        await self._enrich_missing_gst_by_party(bills)
        return bills

    async def _enrich_missing_gst_by_party(self, bills: List[dict]) -> None:
        """Fill missing GST numbers from other invoices of the same party."""
        parties_missing_gst = {
            bill.get('party_name')
            for bill in bills
            if bill.get('party_name') and not bill.get('gst_no')
        }

        if not parties_missing_gst:
            return

        party_gst_docs = await self.collection.aggregate([
            {
                '$match': {
                    'party_name': {'$in': list(parties_missing_gst)},
                    'gst_no': {
                        '$regex': r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][A-Z0-9]Z[A-Z0-9]$'
                    }
                }
            },
            {
                '$group': {
                    '_id': '$party_name',
                    'gst_no': {'$first': '$gst_no'}
                }
            }
        ]).to_list(length=None)

        party_to_gst = {doc['_id']: doc.get('gst_no') for doc in party_gst_docs if doc.get('gst_no')}

        for bill in bills:
            if bill.get('gst_no'):
                continue
            party_name = bill.get('party_name')
            if party_name in party_to_gst:
                bill['gst_no'] = party_to_gst[party_name]
    
    async def get_bills_by_party(self, party_name: str) -> List[dict]:
        """Get all bills for a party"""
        return await self.collection.find({'party_name': party_name}).to_list(length=None)
    
    async def get_unpaid_bills(self) -> List[dict]:
        """Get all unpaid bills"""
        return await self.collection.find({'status': BillStatus.UNPAID}).to_list(length=None)
    
    async def update_bill_status(self, invoice_no: str, status: str, paid_amount: float = 0) -> bool:
        """Update bill status"""
        try:
            result = await self.collection.update_one(
                {'invoice_no': invoice_no},
                {
                    '$set': {
                        'status': status,
                        'paid_amount': paid_amount,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"✗ Error updating bill: {str(e)}")
            return False
    
    async def bulk_update_bills(self, bills_data: List[dict]) -> int:
        """Bulk update multiple bills"""
        try:
            update_count = 0
            for bill in bills_data:
                invoice_no = bill.get('invoice_no')
                result = await self.collection.update_one(
                    {'invoice_no': invoice_no},
                    {
                        '$set': {
                            'status': bill.get('status', BillStatus.UNPAID),
                            'paid_amount': bill.get('paid_amount', 0),
                            'remaining_amount': bill.get('remaining_amount', 0),
                            'matched_payment_ids': bill.get('matched_payment_ids', []),
                            'updated_at': datetime.utcnow()
                        }
                    },
                    upsert=True
                )
                if result.modified_count > 0 or result.upserted_id:
                    update_count += 1
            
            logger.info(f"✓ Updated {update_count} bills")
            return update_count
        except Exception as e:
            logger.error(f"✗ Error bulk updating bills: {str(e)}")
            raise
    
    async def delete_bill(self, invoice_no: str) -> bool:
        """Delete a bill"""
        try:
            result = await self.collection.delete_one({'invoice_no': invoice_no})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"✗ Error deleting bill: {str(e)}")
            return False
    
    async def count_bills(self, filters: dict = None) -> int:
        """Count bills matching filters"""
        query = filters or {}
        return await self.collection.count_documents(query)

    async def apply_payment_to_bills(
        self,
        *,
        amount: float,
        party_name: str,
        bill_ids: Optional[List[str]] = None,
        invoice_nos: Optional[List[str]] = None,
        payment_id: Optional[str] = None,
        fiscal_year: Optional[str] = None,
    ) -> dict:
        """Allocate a payment amount across selected bills and update bill status/amounts.
        Adds an optional `fiscal_year` filter so allocations occur only within that fiscal.
        """
        remaining_amount = float(amount or 0.0)
        if remaining_amount <= 0:
            return {
                'applied_amount': 0.0,
                'remaining_amount': 0.0,
                'allocations': [],
            }

        query = {'party_name': party_name}
        # Enforce fiscal filter when provided
        if fiscal_year:
            query['fiscal_year'] = fiscal_year

        or_filters = []

        if bill_ids:
            object_ids = []
            for bill_id in bill_ids:
                try:
                    object_ids.append(ObjectId(bill_id))
                except Exception:
                    continue
            if object_ids:
                or_filters.append({'_id': {'$in': object_ids}})

        if invoice_nos:
            safe_invoice_nos = [str(inv).strip() for inv in invoice_nos if str(inv).strip()]
            if safe_invoice_nos:
                or_filters.append({'invoice_no': {'$in': safe_invoice_nos}})

        if or_filters:
            query['$or'] = or_filters

        bills = await self.collection.find(query).sort([('invoice_date', 1), ('_id', 1)]).to_list(length=None)

        allocations = []
        applied_total = 0.0

        for bill in bills:
            if remaining_amount <= 0:
                break

            grand_total = float(bill.get('grand_total') or 0.0)
            paid_amount = float(bill.get('paid_amount') or 0.0)
            due_amount = max(0.0, grand_total - paid_amount)
            if due_amount <= 0:
                continue

            applied = min(due_amount, remaining_amount)
            new_paid = paid_amount + applied
            new_remaining = max(0.0, grand_total - new_paid)

            if new_remaining == 0:
                new_status = BillStatus.PAID
            elif new_paid > 0:
                new_status = BillStatus.PARTIAL
            else:
                new_status = BillStatus.UNPAID

            update_doc = {
                '$set': {
                    'paid_amount': new_paid,
                    'remaining_amount': new_remaining,
                    'status': new_status,
                    'updated_at': datetime.utcnow(),
                }
            }

            if payment_id:
                existing_matches = bill.get('matched_payment_ids') or []
                if payment_id not in existing_matches:
                    update_doc['$set']['matched_payment_ids'] = [*existing_matches, payment_id]

            await self.collection.update_one({'_id': bill['_id']}, update_doc)

            allocations.append({
                'bill_id': str(bill['_id']),
                'invoice_no': bill.get('invoice_no'),
                'allocated_amount': applied,
                'status': new_status,
            })

            applied_total += applied
            remaining_amount -= applied

        return {
            'applied_amount': applied_total,
            'remaining_amount': max(0.0, remaining_amount),
            'allocations': allocations,
        }

    async def revert_payment_from_bills(
        self,
        *,
        payment_id: str,
        allocations: List[dict],
        party_name: Optional[str] = None,
        fiscal_year: Optional[str] = None,
    ) -> dict:
        """Revert bill amounts previously allocated by a payment.
        Optionally restricts the search to a fiscal_year when provided.
        """
        reverted_total = 0.0
        reverted_allocations = []

        for allocation in allocations or []:
            allocation_amount = float(allocation.get('allocated_amount') or 0.0)
            if allocation_amount <= 0:
                continue

            bill = None
            bill_id = allocation.get('bill_id')
            invoice_no = allocation.get('invoice_no')

            if bill_id:
                try:
                    bill = await self.collection.find_one({'_id': ObjectId(str(bill_id))})
                except Exception:
                    bill = None

            if not bill and invoice_no:
                invoice_query = {'invoice_no': invoice_no}
                if party_name:
                    invoice_query['party_name'] = party_name
                if fiscal_year:
                    invoice_query['fiscal_year'] = fiscal_year
                bill = await self.collection.find_one(invoice_query)

            if not bill:
                continue

            grand_total = float(bill.get('grand_total') or 0.0)
            paid_amount = float(bill.get('paid_amount') or 0.0)
            new_paid_amount = max(0.0, paid_amount - allocation_amount)
            new_remaining = max(0.0, grand_total - new_paid_amount)

            if new_remaining == 0:
                new_status = BillStatus.PAID
            elif new_paid_amount > 0:
                new_status = BillStatus.PARTIAL
            else:
                new_status = BillStatus.UNPAID

            matched_payment_ids = [pid for pid in (bill.get('matched_payment_ids') or []) if pid != payment_id]

            await self.collection.update_one(
                {'_id': bill['_id']},
                {
                    '$set': {
                        'paid_amount': new_paid_amount,
                        'remaining_amount': new_remaining,
                        'status': new_status,
                        'matched_payment_ids': matched_payment_ids,
                        'updated_at': datetime.utcnow(),
                    }
                },
            )

            reverted_total += min(paid_amount, allocation_amount)
            reverted_allocations.append({
                'bill_id': str(bill['_id']),
                'invoice_no': bill.get('invoice_no'),
                'reverted_amount': min(paid_amount, allocation_amount),
            })

        return {
            'reverted_amount': reverted_total,
            'allocations': reverted_allocations,
        }
