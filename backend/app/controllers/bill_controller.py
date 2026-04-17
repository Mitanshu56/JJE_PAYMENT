"""
Bill controller for handling bill-related business logic
"""
from typing import List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.bill import Bill, BillStatus
import logging

logger = logging.getLogger(__name__)


class BillController:
    """Controller for bill operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db['bills']

    def _build_invoice_key(self, bill_data: dict) -> str:
        """Build a stable key to uniquely identify invoice rows across uploads."""
        invoice_no = str(bill_data.get('invoice_no') or '').strip().lower()
        party_name = str(bill_data.get('party_name') or '').strip().lower()

        invoice_date = bill_data.get('invoice_date')
        if hasattr(invoice_date, 'strftime'):
            invoice_date_part = invoice_date.strftime('%Y-%m-%d')
        else:
            invoice_date_part = str(invoice_date or '').strip().lower()

        site = str(bill_data.get('site') or '').strip().lower()
        return f"{invoice_no}|{party_name}|{invoice_date_part}|{site}"
    
    async def create_bill(self, bill_data: dict) -> dict:
        """Create a new bill"""
        try:
            bill_data['created_at'] = datetime.utcnow()
            bill_data['updated_at'] = datetime.utcnow()
            
            result = await self.collection.insert_one(bill_data)
            bill_data['_id'] = result.inserted_id
            
            logger.info(f"✓ Created bill: {bill_data.get('invoice_no')}")
            return bill_data
        except Exception as e:
            logger.error(f"✗ Error creating bill: {str(e)}")
            raise
    
    async def create_bills_bulk(self, bills_data: List[dict]) -> int:
        """Create or update multiple bills by invoice number."""
        try:
            processed_count = 0

            for bill in bills_data:
                invoice_no = str(bill.get('invoice_no') or '').strip()
                if not invoice_no:
                    logger.warning("Skipping bill without invoice_no")
                    continue

                now = datetime.utcnow()
                grand_total = float(bill.get('grand_total') or 0.0)
                invoice_key = self._build_invoice_key(bill)

                # Upsert keeps re-uploads idempotent and avoids duplicate-key failures.
                result = await self.collection.update_one(
                    {'invoice_key': invoice_key},
                    {
                        '$set': {
                            'invoice_key': invoice_key,
                            'invoice_no': invoice_no,
                            'party_name': bill.get('party_name', 'Unknown Party'),
                            'gst_no': bill.get('gst_no'),
                            'invoice_date': bill.get('invoice_date'),
                            'net_amount': float(bill.get('net_amount') or 0.0),
                            'cgst': float(bill.get('cgst') or 0.0),
                            'sgst': float(bill.get('sgst') or 0.0),
                            'grand_total': grand_total,
                            'site': bill.get('site'),
                            'updated_at': now,
                        },
                        '$setOnInsert': {
                            'created_at': now,
                            'status': BillStatus.UNPAID,
                            'paid_amount': 0.0,
                            'remaining_amount': grand_total,
                            'matched_payment_ids': [],
                        }
                    },
                    upsert=True
                )

                if result.upserted_id or result.matched_count > 0 or result.modified_count > 0:
                    processed_count += 1

            logger.info(f"✓ Upserted {processed_count} bills")
            return processed_count
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
        # Preserve the original upload/insertion order so pagination matches the source sheet.
        cursor = self.collection.find(query).sort([
            ('_id', 1),
        ]).skip(skip).limit(limit)
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
