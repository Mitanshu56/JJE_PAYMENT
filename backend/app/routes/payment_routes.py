"""
Payment management API routes
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from pydantic import BaseModel, Field
from app.controllers.bill_controller import BillController
from app.core.database import get_db
from app.controllers.payment_controller import PaymentController
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["Payments"])


class ManualPaymentRequest(BaseModel):
    party_name: str
    amount: float = Field(gt=0)
    payment_mode: str
    actual_received_amount: Optional[float] = None
    invoice_nos: List[str] = []
    bill_ids: List[str] = []
    reference: Optional[str] = None
    notes: Optional[str] = None
    payment_date: Optional[datetime] = None
    cheque_date: Optional[str] = None
    party_bank_name: Optional[str] = None
    cheque_amount: Optional[float] = None
    deposit_date: Optional[str] = None
    upi_id: Optional[str] = None
    upi_transfer_date: Optional[str] = None


@router.post("/manual")
async def create_manual_payment(payload: ManualPaymentRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Create a manual payment and allocate it across selected bills."""
    try:
        payment_controller = PaymentController(db)
        bill_controller = BillController(db)

        payment_id = f"MAN-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[:-3]}"
        normalized_mode = (payload.payment_mode or '').strip().upper()
        effective_payment_date = payload.payment_date or datetime.utcnow()

        cheque_date = payload.cheque_date
        party_bank_name = payload.party_bank_name
        cheque_amount = payload.cheque_amount
        deposit_date = payload.deposit_date
        upi_id = payload.upi_id
        upi_transfer_date = payload.upi_transfer_date

        if normalized_mode == 'CHEQUE':
            if not cheque_date:
                cheque_date = effective_payment_date.strftime('%Y-%m-%d')
            if not deposit_date:
                deposit_date = effective_payment_date.strftime('%Y-%m-%d')
            if cheque_amount is None:
                cheque_amount = float(payload.actual_received_amount) if payload.actual_received_amount is not None else float(payload.amount)

        if normalized_mode == 'UPI':
            upi_id = (upi_id or '').strip()
            if not upi_transfer_date:
                upi_transfer_date = effective_payment_date.strftime('%Y-%m-%d')

        allocation = await bill_controller.apply_payment_to_bills(
            amount=payload.amount,
            party_name=payload.party_name,
            bill_ids=payload.bill_ids,
            invoice_nos=payload.invoice_nos,
            payment_id=payment_id,
        )

        payment_doc = {
            'payment_id': payment_id,
            'party_name': payload.party_name,
            'amount': float(payload.amount),
            'actual_received_amount': float(payload.actual_received_amount) if payload.actual_received_amount is not None else float(payload.amount),
            'payment_date': effective_payment_date,
            'reference': payload.reference,
            'notes': payload.notes,
            'payment_mode': normalized_mode,
            'cheque_date': cheque_date,
            'party_bank_name': party_bank_name,
            'cheque_amount': cheque_amount,
            'deposit_date': deposit_date,
            'upi_id': upi_id,
            'upi_transfer_date': upi_transfer_date,
            'matched_invoice_nos': [a['invoice_no'] for a in allocation['allocations'] if a.get('invoice_no')],
            'applied_amount': allocation['applied_amount'],
            'unapplied_amount': allocation['remaining_amount'],
        }

        created_payment = await payment_controller.create_payment(payment_doc)

        if '_id' in created_payment:
            created_payment['_id'] = str(created_payment['_id'])
        if isinstance(created_payment.get('payment_date'), datetime):
            created_payment['payment_date'] = created_payment['payment_date'].isoformat()

        return {
            'status': 'success',
            'payment': created_payment,
            'allocation': allocation,
        }
    except Exception as e:
        logger.error(f"✗ Error creating manual payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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
            if isinstance(payment.get('upi_transfer_date'), datetime):
                payment['upi_transfer_date'] = payment['upi_transfer_date'].isoformat()
        
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
            if isinstance(payment.get('upi_transfer_date'), datetime):
                payment['upi_transfer_date'] = payment['upi_transfer_date'].isoformat()
        
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
