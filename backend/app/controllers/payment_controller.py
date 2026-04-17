"""
Payment controller for handling payment-related business logic
"""
from typing import List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)


class PaymentController:
    """Controller for payment operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db['payments']
    
    async def create_payment(self, payment_data: dict) -> dict:
        """Create a new payment"""
        try:
            payment_data['created_at'] = datetime.utcnow()
            payment_data['updated_at'] = datetime.utcnow()
            
            result = await self.collection.insert_one(payment_data)
            payment_data['_id'] = result.inserted_id
            
            logger.info(f"✓ Created payment: {payment_data.get('payment_id')}")
            return payment_data
        except Exception as e:
            logger.error(f"✗ Error creating payment: {str(e)}")
            raise
    
    async def create_payments_bulk(self, payments_data: List[dict]) -> int:
        """Create multiple payments"""
        try:
            for payment in payments_data:
                payment['created_at'] = datetime.utcnow()
                payment['updated_at'] = datetime.utcnow()
            
            result = await self.collection.insert_many(payments_data)
            logger.info(f"✓ Created {len(result.inserted_ids)} payments")
            return len(result.inserted_ids)
        except Exception as e:
            logger.error(f"✗ Error creating payments: {str(e)}")
            raise
    
    async def get_payment(self, payment_id: str) -> Optional[dict]:
        """Get a payment by ID"""
        return await self.collection.find_one({'payment_id': payment_id})
    
    async def get_payments(self, filters: dict = None, skip: int = 0, limit: int = 100) -> List[dict]:
        """Get payments with optional filters"""
        query = filters or {}
        cursor = self.collection.find(query).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def get_payments_by_party(self, party_name: str) -> List[dict]:
        """Get all payments for a party"""
        return await self.collection.find({'party_name': party_name}).to_list(length=None)
    
    async def get_unmatched_payments(self) -> List[dict]:
        """Get payments that are not yet matched to invoices"""
        return await self.collection.find({
            'matched_invoice_nos': {'$eq': [] }
        }).to_list(length=None)
    
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
    
    async def count_payments(self, filters: dict = None) -> int:
        """Count payments matching filters"""
        query = filters or {}
        return await self.collection.count_documents(query)
