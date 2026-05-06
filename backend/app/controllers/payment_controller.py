"""
Payment controller for handling payment-related business logic
"""
from typing import List, Optional
from datetime import datetime
from typing import Any
try:
    from motor.motor_asyncio import AsyncIOMotorDatabase
except Exception:
    AsyncIOMotorDatabase = Any
import logging

logger = logging.getLogger(__name__)


class PaymentController:
    """Controller for payment operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db['payments']
    
    async def create_payment(self, payment_data: dict, fiscal_year: Optional[str] = None) -> dict:
        """Create a new payment and tag with fiscal year if provided or derivable."""
        try:
            payment_data['created_at'] = datetime.utcnow()
            payment_data['updated_at'] = datetime.utcnow()

            # Attach fiscal year if provided, else try to derive from payment_date
            if fiscal_year:
                payment_data['fiscal_year'] = fiscal_year
            else:
                pd = payment_data.get('payment_date')
                if pd:
                    try:
                        from app.core.fiscal import fiscal_year_label_from_date
                        payment_data['fiscal_year'] = fiscal_year_label_from_date(pd)
                    except Exception:
                        pass

            result = await self.collection.insert_one(payment_data)
            payment_data['_id'] = result.inserted_id

            logger.info(f"✓ Created payment: {payment_data.get('payment_id')}")
            return payment_data
        except Exception as e:
            logger.error(f"✗ Error creating payment: {str(e)}")
            raise

    async def create_payments_bulk(self, payments_data: List[dict], fiscal_year: Optional[str] = None) -> int:
        """Create multiple payments and tag with fiscal year when provided."""
        try:
            for payment in payments_data:
                payment['created_at'] = datetime.utcnow()
                payment['updated_at'] = datetime.utcnow()
                if fiscal_year:
                    payment['fiscal_year'] = fiscal_year
                else:
                    pd = payment.get('payment_date')
                    if pd:
                        try:
                            from app.core.fiscal import fiscal_year_label_from_date
                            payment['fiscal_year'] = fiscal_year_label_from_date(pd)
                        except Exception:
                            pass

            result = await self.collection.insert_many(payments_data)
            logger.info(f"✓ Created {len(result.inserted_ids)} payments")
            return len(result.inserted_ids)
        except Exception as e:
            logger.error(f"✗ Error creating payments: {str(e)}")
            raise
    
    async def get_payment(self, payment_id: str, fiscal_year: Optional[str] = None) -> Optional[dict]:
        """Get a payment by ID, optionally constrained to fiscal_year."""
        query = {'payment_id': payment_id}
        if fiscal_year:
            query['fiscal_year'] = fiscal_year
        return await self.collection.find_one(query)
    
    async def get_payments(self, filters: dict = None, skip: int = 0, limit: int = 100, fiscal_year: Optional[str] = None) -> List[dict]:
        """Get payments with optional filters and optional fiscal_year constraint"""
        query = filters or {}
        if fiscal_year:
            query['fiscal_year'] = fiscal_year
        cursor = self.collection.find(query).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def get_payments_by_party(self, party_name: str, fiscal_year: Optional[str] = None) -> List[dict]:
        """Get all payments for a party, optionally scoped to fiscal_year"""
        query = {'party_name': party_name}
        if fiscal_year:
            query['fiscal_year'] = fiscal_year
        return await self.collection.find(query).to_list(length=None)
    
    async def get_unmatched_payments(self, fiscal_year: Optional[str] = None) -> List[dict]:
        """Get payments that are not yet matched to invoices, optionally scoped to fiscal_year"""
        query = {'matched_invoice_nos': {'$eq': []}}
        if fiscal_year:
            query['fiscal_year'] = fiscal_year
        return await self.collection.find(query).to_list(length=None)
    
    async def update_payment_matches(
        self,
        payment_id: str,
        matched_invoice_nos: List[str]
    ) -> bool:
        """Update matched invoices for a payment"""
        try:
            result = await self.collection.update_one(
                {'payment_id': payment_id},
                {
                    '$set': {
                        'matched_invoice_nos': matched_invoice_nos,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"✗ Error updating payment: {str(e)}")
            return False
    
    async def delete_payment(self, payment_id: str) -> bool:
        """Delete a payment"""
        try:
            result = await self.collection.delete_one({'payment_id': payment_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"✗ Error deleting payment: {str(e)}")
            return False
    
    async def count_payments(self, filters: dict = None, fiscal_year: Optional[str] = None) -> int:
        """Count payments matching filters, with optional fiscal_year"""
        query = filters or {}
        if fiscal_year:
            query['fiscal_year'] = fiscal_year
        return await self.collection.count_documents(query)