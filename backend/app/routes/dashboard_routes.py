"""
Matching and Dashboard API routes
"""
from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from app.core.database import get_db
from app.controllers.bill_controller import BillController
from app.controllers.payment_controller import PaymentController
from app.services.matcher import PaymentMatcher
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Matching & Dashboard"])

STANDARD_PAYMENT_MODES = ['CASH', 'CHEQUE', 'UPI', 'NEFT']


def _normalize_payment_mode(mode: str | None) -> str:
    value = str(mode or '').strip().upper()
    return value or 'UNKNOWN'


@router.post("/match-payments")
async def match_payments(db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Run payment matching algorithm to match payments with invoices.
    Updates bill statuses based on matches.
    """
    try:
        bill_controller = BillController(db)
        payment_controller = PaymentController(db)
        
        # Get all unpaid bills
        bills = await bill_controller.get_bills()
        
        # Get all payments
        payments = await payment_controller.get_payments(limit=10000)
        
        if not bills or not payments:
            raise HTTPException(status_code=400, detail="No bills or payments to match")
        
        # Run matching algorithm
        matcher = PaymentMatcher()
        matched_bills = matcher.match_payments(bills, payments)
        
        # Update bills in database
        update_count = await bill_controller.bulk_update_bills(matched_bills)
        
        # Update payment matches
        for bill in matched_bills:
            for payment_id in bill.get('matched_payment_ids', []):
                payment = next((p for p in payments if p['payment_id'] == payment_id), None)
                if payment:
                    invoice_nos = payment.get('matched_invoice_nos', [])
                    if bill['invoice_no'] not in invoice_nos:
                        invoice_nos.append(bill['invoice_no'])
                        await payment_controller.update_payment_matches(payment_id, invoice_nos)
        
        logger.info(f"✓ Matched {update_count} bills with payments")
        
        return {
            'status': 'success',
            'message': f'Successfully matched {update_count} bills',
            'bills_matched': update_count,
            'matched_bills': matched_bills
        }
    
    except Exception as e:
        logger.error(f"✗ Error matching payments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    latest_upload_only: bool = False,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get dashboard summary statistics"""
    try:
        bill_controller = BillController(db)
        payment_controller = PaymentController(db)
        
        # Determine filters
        filters = {}
        if latest_upload_only:
            latest_invoice_upload = await db['upload_logs'].find_one(
                {'file_type': 'invoice'},
                sort=[('created_at', -1)]
            )
            latest_batch_id = (latest_invoice_upload or {}).get('upload_batch_id')
            if latest_batch_id:
                filters['last_upload_batch_id'] = latest_batch_id
        
        # Get bills (optionally filtered to latest upload)
        bills = await bill_controller.get_bills(filters=filters, limit=10000)
        
        # Calculate summary
        total_billing = sum(b.get('grand_total', 0) for b in bills)
        total_paid = sum(b.get('paid_amount', 0) for b in bills)
        total_pending = sum(b.get('remaining_amount', 0) for b in bills)
        
        paid_invoices = len([b for b in bills if b.get('status') == 'PAID'])
        partial_invoices = len([b for b in bills if b.get('status') == 'PARTIAL'])
        unpaid_invoices = len([b for b in bills if b.get('status') == 'UNPAID'])
        
        payments = await payment_controller.get_payments(limit=100000)
        payment_count = len(payments)

        received_by_mode = {mode: 0.0 for mode in STANDARD_PAYMENT_MODES}
        for payment in payments:
            mode = _normalize_payment_mode(payment.get('payment_mode'))
            received_amount = float(
                payment.get('actual_received_amount')
                if payment.get('actual_received_amount') is not None
                else (payment.get('amount') or 0)
            )
            received_by_mode[mode] = float(received_by_mode.get(mode, 0.0)) + received_amount

        received_by_mode_list = [
            {
                'mode': mode,
                'amount': amount,
            }
            for mode, amount in sorted(received_by_mode.items(), key=lambda item: item[0])
        ]
        
        return {
            'status': 'success',
            'summary': {
                'total_billing': total_billing,
                'total_paid': total_paid,
                'total_pending': total_pending,
                'paid_percentage': (total_paid / total_billing * 100) if total_billing > 0 else 0,
                'invoice_stats': {
                    'paid': paid_invoices,
                    'partial': partial_invoices,
                    'unpaid': unpaid_invoices,
                    'total': len(bills)
                },
                'payment_records': payment_count,
                'received_by_mode': received_by_mode_list,
            }
        }
    except Exception as e:
        logger.error(f"✗ Error getting dashboard summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/party-summary")
async def get_party_summary(latest_upload_only: bool = False, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get party-wise payment summary"""
    try:
        bill_controller = BillController(db)
        
        # Determine filters
        filters = {}
        if latest_upload_only:
            latest_invoice_upload = await db['upload_logs'].find_one(
                {'file_type': 'invoice'},
                sort=[('created_at', -1)]
            )
            latest_batch_id = (latest_invoice_upload or {}).get('upload_batch_id')
            if latest_batch_id:
                filters['last_upload_batch_id'] = latest_batch_id
        
        bills = await bill_controller.get_bills(filters=filters, limit=10000)
        
        matcher = PaymentMatcher()
        party_stats = matcher.get_party_summary(bills)
        
        return {
            'status': 'success',
            'party_summary': party_stats
        }
    except Exception as e:
        logger.error(f"✗ Error getting party summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/monthly-summary")
async def get_monthly_summary(latest_upload_only: bool = False, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get monthly payment summary"""
    try:
        bill_controller = BillController(db)
        
        # Determine filters
        filters = {}
        if latest_upload_only:
            latest_invoice_upload = await db['upload_logs'].find_one(
                {'file_type': 'invoice'},
                sort=[('created_at', -1)]
            )
            latest_batch_id = (latest_invoice_upload or {}).get('upload_batch_id')
            if latest_batch_id:
                filters['last_upload_batch_id'] = latest_batch_id
        
        bills = await bill_controller.get_bills(filters=filters, limit=10000)
        
        matcher = PaymentMatcher()
        monthly_stats = matcher.get_monthly_summary(bills)
        
        return {
            'status': 'success',
            'monthly_summary': monthly_stats
        }
    except Exception as e:
        logger.error(f"✗ Error getting monthly summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    }
