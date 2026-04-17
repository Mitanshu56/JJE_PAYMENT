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


async def reconcile_bills_from_payments(db: AsyncIOMotorDatabase) -> dict:
    """Rebuild bill paid/remaining/status from current payments collection."""
    bill_controller = BillController(db)
    payment_controller = PaymentController(db)

    # Reset all bills to unpaid baseline.
    all_bills = await bill_controller.get_bills(limit=100000)
    for bill in all_bills:
        grand_total = float(bill.get('grand_total') or 0.0)
        await db['bills'].update_one(
            {'_id': bill['_id']},
            {
                '$set': {
                    'paid_amount': 0.0,
                    'remaining_amount': grand_total,
                    'status': 'UNPAID',
                    'matched_payment_ids': [],
                    'updated_at': datetime.utcnow(),
                }
            },
        )

    payments = await payment_controller.get_payments(limit=100000)
    payments = sorted(
        payments,
        key=lambda p: (
            p.get('payment_date') or datetime.min,
            p.get('created_at') or datetime.min,
        ),
    )

    applied_rows = 0
    for payment in payments:
        payment_id = payment.get('payment_id')
        party_name = payment.get('party_name')
        if not payment_id or not party_name:
            continue

        amount = float(payment.get('amount') or 0.0)
        if amount <= 0:
            continue

        old_allocations = payment.get('allocations') or []
        bill_ids = [str(a.get('bill_id')) for a in old_allocations if a.get('bill_id')]
        invoice_nos = [a.get('invoice_no') for a in old_allocations if a.get('invoice_no')]

        if not invoice_nos:
            invoice_nos = [inv for inv in (payment.get('matched_invoice_nos') or []) if inv]

        allocation = await bill_controller.apply_payment_to_bills(
            amount=amount,
            party_name=party_name,
            bill_ids=bill_ids,
            invoice_nos=invoice_nos,
            payment_id=payment_id,
        )

        applied_rows += len(allocation.get('allocations') or [])

        await db['payments'].update_one(
            {'_id': payment['_id']},
            {
                '$set': {
                    'matched_invoice_nos': [
                        a.get('invoice_no')
                        for a in (allocation.get('allocations') or [])
                        if a.get('invoice_no')
                    ],
                    'allocations': allocation.get('allocations') or [],
                    'applied_amount': float(allocation.get('applied_amount') or 0.0),
                    'unapplied_amount': float(allocation.get('remaining_amount') or 0.0),
                    'updated_at': datetime.utcnow(),
                }
            },
        )

    return {
        'bills_reset': len(all_bills),
        'payments_processed': len(payments),
        'allocation_rows_applied': applied_rows,
    }


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


class EditManualPaymentRequest(BaseModel):
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
            'allocations': allocation['allocations'],
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


@router.put("/manual/{payment_id}")
async def edit_manual_payment(
    payment_id: str,
    payload: EditManualPaymentRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Edit an existing manual payment and re-allocate it across selected bills."""
    try:
        payment_controller = PaymentController(db)
        bill_controller = BillController(db)

        existing_payment = await payment_controller.get_payment(payment_id)
        if not existing_payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        party_name = existing_payment.get('party_name')
        if not party_name:
            raise HTTPException(status_code=400, detail="Invalid payment: party is missing")

        normalized_mode = (payload.payment_mode or '').strip().upper()
        effective_payment_date = payload.payment_date or existing_payment.get('payment_date') or datetime.utcnow()

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

        old_allocations = existing_payment.get('allocations') or []
        if not old_allocations:
            old_invoice_nos = [inv for inv in (existing_payment.get('matched_invoice_nos') or []) if inv]
            if old_invoice_nos:
                fallback_amount = float(existing_payment.get('applied_amount') or existing_payment.get('amount') or 0.0)
                per_invoice = fallback_amount / len(old_invoice_nos) if old_invoice_nos else 0.0
                old_allocations = [
                    {
                        'invoice_no': inv,
                        'allocated_amount': per_invoice,
                    }
                    for inv in old_invoice_nos
                ]

        await bill_controller.revert_payment_from_bills(
            payment_id=payment_id,
            allocations=old_allocations,
            party_name=party_name,
        )

        allocation = await bill_controller.apply_payment_to_bills(
            amount=payload.amount,
            party_name=party_name,
            bill_ids=payload.bill_ids,
            invoice_nos=payload.invoice_nos,
            payment_id=payment_id,
        )

        if not allocation['allocations']:
            # Restore old allocation if new allocation could not be applied.
            if old_allocations:
                restore_ids = [str(a.get('bill_id')) for a in old_allocations if a.get('bill_id')]
                restore_invoice_nos = [a.get('invoice_no') for a in old_allocations if a.get('invoice_no')]
                restore_amount = float(existing_payment.get('applied_amount') or existing_payment.get('amount') or 0.0)
                if restore_amount > 0:
                    await bill_controller.apply_payment_to_bills(
                        amount=restore_amount,
                        party_name=party_name,
                        bill_ids=restore_ids,
                        invoice_nos=restore_invoice_nos,
                        payment_id=payment_id,
                    )
            raise HTTPException(status_code=400, detail='No amount could be allocated to selected invoices')

        update_doc = {
            'amount': float(payload.amount),
            'actual_received_amount': float(payload.actual_received_amount) if payload.actual_received_amount is not None else float(payload.amount),
            'payment_mode': normalized_mode,
            'reference': payload.reference,
            'notes': payload.notes,
            'payment_date': effective_payment_date,
            'cheque_date': cheque_date,
            'party_bank_name': party_bank_name,
            'cheque_amount': cheque_amount,
            'deposit_date': deposit_date,
            'upi_id': upi_id,
            'upi_transfer_date': upi_transfer_date,
            'matched_invoice_nos': [a['invoice_no'] for a in allocation['allocations'] if a.get('invoice_no')],
            'allocations': allocation['allocations'],
            'applied_amount': allocation['applied_amount'],
            'unapplied_amount': allocation['remaining_amount'],
            'updated_at': datetime.utcnow(),
        }

        await db['payments'].update_one({'payment_id': payment_id}, {'$set': update_doc})
        updated_payment = await payment_controller.get_payment(payment_id)

        if '_id' in updated_payment:
            updated_payment['_id'] = str(updated_payment['_id'])
        if isinstance(updated_payment.get('payment_date'), datetime):
            updated_payment['payment_date'] = updated_payment['payment_date'].isoformat()
        if isinstance(updated_payment.get('upi_transfer_date'), datetime):
            updated_payment['upi_transfer_date'] = updated_payment['upi_transfer_date'].isoformat()

        return {
            'status': 'success',
            'message': f'Payment {payment_id} updated successfully',
            'payment': updated_payment,
            'allocation': allocation,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ Error editing manual payment: {str(e)}")
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
        bill_controller = BillController(db)

        existing_payment = await controller.get_payment(payment_id)
        if not existing_payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        allocations = existing_payment.get('allocations') or []
        if not allocations:
            old_invoice_nos = [inv for inv in (existing_payment.get('matched_invoice_nos') or []) if inv]
            if old_invoice_nos:
                fallback_amount = float(existing_payment.get('applied_amount') or existing_payment.get('amount') or 0.0)
                per_invoice = fallback_amount / len(old_invoice_nos) if old_invoice_nos else 0.0
                allocations = [
                    {
                        'invoice_no': inv,
                        'allocated_amount': per_invoice,
                    }
                    for inv in old_invoice_nos
                ]

        await bill_controller.revert_payment_from_bills(
            payment_id=payment_id,
            allocations=allocations,
            party_name=existing_payment.get('party_name'),
        )

        success = await controller.delete_payment(payment_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Payment not found")

        reconcile_result = await reconcile_bills_from_payments(db)
        
        return {
            'status': 'success',
            'message': f'Payment {payment_id} deleted successfully',
            'reconcile': reconcile_result,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ Error deleting payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
