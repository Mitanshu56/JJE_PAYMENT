"""
Bill management API routes
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId
from app.core.database import get_db
from app.controllers.bill_controller import BillController
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bills", tags=["Bills"])


async def _cleanup_payment_links_after_bill_delete(db: AsyncIOMotorDatabase, bill_doc: dict) -> int:
    """Remove deleted bill references from payments and recalculate applied/unapplied values."""
    payment_collection = db['payments']

    invoice_no = str(bill_doc.get('invoice_no') or '').strip()
    bill_id_str = str(bill_doc.get('_id') or '').strip()
    if not invoice_no and not bill_id_str:
        return 0

    search_conditions = []
    if invoice_no:
        search_conditions.extend([
            {'matched_invoice_nos': invoice_no},
            {'allocations.invoice_no': invoice_no},
        ])
    if bill_id_str:
        search_conditions.append({'allocations.bill_id': bill_id_str})

    if not search_conditions:
        return 0

    affected_payments = await payment_collection.find({'$or': search_conditions}).to_list(length=None)
    touched_payments = 0

    for payment in affected_payments:
        existing_invoices = [
            str(inv).strip()
            for inv in (payment.get('matched_invoice_nos') or [])
            if str(inv or '').strip()
        ]

        existing_allocations = payment.get('allocations') or []
        cleaned_allocations = []
        for alloc in existing_allocations:
            alloc_invoice_no = str(alloc.get('invoice_no') or '').strip()
            alloc_bill_id = str(alloc.get('bill_id') or '').strip()

            is_deleted_row = False
            if bill_id_str and alloc_bill_id == bill_id_str:
                is_deleted_row = True
            elif invoice_no and alloc_invoice_no == invoice_no:
                is_deleted_row = True

            if not is_deleted_row:
                cleaned_allocations.append(alloc)

        invoices_from_allocations = []
        for alloc in cleaned_allocations:
            alloc_invoice_no = str(alloc.get('invoice_no') or '').strip()
            if alloc_invoice_no and alloc_invoice_no not in invoices_from_allocations:
                invoices_from_allocations.append(alloc_invoice_no)

        if invoices_from_allocations:
            matched_invoice_nos = invoices_from_allocations
        else:
            matched_invoice_nos = [inv for inv in existing_invoices if inv != invoice_no]

        applied_amount = float(sum(float(a.get('allocated_amount') or 0.0) for a in cleaned_allocations))
        payment_amount = float(payment.get('amount') or 0.0)
        unapplied_amount = max(0.0, payment_amount - applied_amount)

        await payment_collection.update_one(
            {'_id': payment['_id']},
            {
                '$set': {
                    'matched_invoice_nos': matched_invoice_nos,
                    'allocations': cleaned_allocations,
                    'applied_amount': applied_amount,
                    'unapplied_amount': unapplied_amount,
                    'updated_at': datetime.utcnow(),
                }
            }
        )
        touched_payments += 1

    return touched_payments


@router.get("/")
async def get_bills(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    party: Optional[str] = None,
    month: Optional[int] = Query(None, ge=1, le=12),
    latest_upload_only: bool = Query(False),
    upload_batch_id: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get all bills with optional filters"""
    try:
        controller = BillController(db)
        filters = {}
        
        if status:
            filters['status'] = status
        if party:
            filters['party_name'] = {'$regex': party, '$options': 'i'}
        if month is not None:
            filters['$expr'] = {'$eq': [{'$month': '$invoice_date'}, month]}

        effective_upload_batch_id = None
        if upload_batch_id:
            effective_upload_batch_id = upload_batch_id
            filters['last_upload_batch_id'] = effective_upload_batch_id
        elif latest_upload_only:
            latest_invoice_upload = await db['upload_logs'].find_one(
                {'file_type': 'invoice'},
                sort=[('created_at', -1)]
            )
            latest_batch_id = (latest_invoice_upload or {}).get('upload_batch_id')
            if latest_batch_id:
                effective_upload_batch_id = latest_batch_id
                filters['last_upload_batch_id'] = latest_batch_id
            else:
                # If no batch metadata exists yet, keep backward-compatible behavior.
                latest_upload_only = False
        
        bills = await controller.get_bills(filters, skip, limit)
        total = await controller.count_bills(filters)
        
        # Convert ObjectId to string
        for bill in bills:
            if '_id' in bill:
                bill['_id'] = str(bill['_id'])
            if isinstance(bill.get('invoice_date'), datetime):
                bill['invoice_date'] = bill['invoice_date'].isoformat()
        
        return {
            'status': 'success',
            'total': total,
            'skip': skip,
            'limit': limit,
            'latest_upload_only': latest_upload_only,
            'upload_batch_id': effective_upload_batch_id,
            'bills': bills
        }
    except Exception as e:
        logger.error(f"✗ Error retrieving bills: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{invoice_no}")
async def get_bill(invoice_no: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get a specific bill by invoice number"""
    try:
        controller = BillController(db)
        bill = await controller.get_bill(invoice_no)

        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")

        if '_id' in bill:
            bill['_id'] = str(bill['_id'])
        if isinstance(bill.get('invoice_date'), datetime):
            bill['invoice_date'] = bill['invoice_date'].isoformat()

        return {
            'status': 'success',
            'bill': bill
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ Error retrieving bill: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/party/{party_name}")
async def get_bills_by_party(party_name: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get all bills for a specific party"""
    try:
        controller = BillController(db)
        bills = await controller.get_bills_by_party(party_name)
        
        # Convert ObjectId to string
        for bill in bills:
            if '_id' in bill:
                bill['_id'] = str(bill['_id'])
            if isinstance(bill.get('invoice_date'), datetime):
                bill['invoice_date'] = bill['invoice_date'].isoformat()
        
        return {
            'status': 'success',
            'party': party_name,
            'bills': bills
        }
    except Exception as e:
        logger.error(f"✗ Error retrieving party bills: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/by-id/{bill_id}")
async def delete_bill_by_id(bill_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Delete an exact bill row by ObjectId and cleanup linked payment references."""
    try:
        controller = BillController(db)
        try:
            object_id = ObjectId(str(bill_id))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid bill id")

        existing_bill = await db['bills'].find_one({'_id': object_id})
        if not existing_bill:
            raise HTTPException(status_code=404, detail="Bill not found")

        delete_result = await db['bills'].delete_one({'_id': object_id})
        if delete_result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Bill not found")

        touched_payments = await _cleanup_payment_links_after_bill_delete(db, existing_bill)

        return {
            'status': 'success',
            'message': f"Bill {existing_bill.get('invoice_no')} deleted successfully",
            'payment_links_updated': touched_payments,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ Error deleting bill by id: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{invoice_no}")
async def delete_bill(invoice_no: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Delete a bill by invoice number (legacy path)."""
    try:
        controller = BillController(db)

        existing_bill = await controller.get_bill(invoice_no)
        if not existing_bill:
            raise HTTPException(status_code=404, detail="Bill not found")

        success = await controller.delete_bill(invoice_no)
        if not success:
            raise HTTPException(status_code=404, detail="Bill not found")

        touched_payments = await _cleanup_payment_links_after_bill_delete(db, existing_bill)

        return {
            'status': 'success',
            'message': f'Bill {invoice_no} deleted successfully',
            'payment_links_updated': touched_payments,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ Error deleting bill: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
