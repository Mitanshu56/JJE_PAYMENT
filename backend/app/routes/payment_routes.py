"""
Payment management API routes
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from app.core.database import get_db
from app.controllers.payment_controller import PaymentController
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["Payments"])


@router.get("/")
async def get_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    party: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get all payments with optional filters"""
    try:
        controller = PaymentController(db)
        filters = {}
        
        if party:
            filters['party_name'] = {'$regex': party, '$options': 'i'}
        
        payments = await controller.get_payments(filters, skip, limit)
        total = await controller.count_payments(filters)
        
        # Convert ObjectId to string
        for payment in payments:
            if '_id' in payment:
                payment['_id'] = str(payment['_id'])
            if isinstance(payment.get('payment_date'), datetime):
                payment['payment_date'] = payment['payment_date'].isoformat()
        
        return {
            'status': 'success',
            'total': total,
            'skip': skip,
            'limit': limit,
            'payments': payments
        }
    except Exception as e:
        logger.error(f"✗ Error retrieving payments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{payment_id}")
async def get_payment(payment_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get a specific payment by ID"""
    try:
        controller = PaymentController(db)
        payment = await controller.get_payment(payment_id)
        
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        # Convert ObjectId to string
        if '_id' in payment:
            payment['_id'] = str(payment['_id'])
        if isinstance(payment.get('payment_date'), datetime):
            payment['payment_date'] = payment['payment_date'].isoformat()
        
        return {
            'status': 'success',
            'payment': payment
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ Error retrieving payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/party/{party_name}")
async def get_payments_by_party(party_name: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get all payments for a specific party"""
    try:
        controller = PaymentController(db)
        payments = await controller.get_payments_by_party(party_name)
        
        # Convert ObjectId to string
        for payment in payments:
            if '_id' in payment:
                payment['_id'] = str(payment['_id'])
            if isinstance(payment.get('payment_date'), datetime):
                payment['payment_date'] = payment['payment_date'].isoformat()
        
        return {
            'status': 'success',
            'party': party_name,
            'payments': payments
        }
    except Exception as e:
        logger.error(f"✗ Error retrieving party payments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{payment_id}")
async def delete_payment(payment_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Delete a payment"""
    try:
        controller = PaymentController(db)
        success = await controller.delete_payment(payment_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        return {
            'status': 'success',
            'message': f'Payment {payment_id} deleted successfully'
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ Error deleting payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
