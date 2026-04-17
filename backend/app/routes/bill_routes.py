"""
Bill management API routes
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from app.core.database import get_db
from app.controllers.bill_controller import BillController
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bills", tags=["Bills"])


@router.get("/")
async def get_bills(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    party: Optional[str] = None,
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
        
        # Convert ObjectId to string
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


@router.delete("/{invoice_no}")
async def delete_bill(invoice_no: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Delete a bill"""
    try:
        controller = BillController(db)
        success = await controller.delete_bill(invoice_no)
        
        if not success:
            raise HTTPException(status_code=404, detail="Bill not found")
        
        return {
            'status': 'success',
            'message': f'Bill {invoice_no} deleted successfully'
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ Error deleting bill: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
