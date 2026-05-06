from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_db
from app.controllers.payment_reminder_controller import PaymentReminderController
from app.services import payment_reminder_email_service
from datetime import datetime

router = APIRouter(prefix="/api/payment-reminders", tags=["PaymentReminders"]) 


@router.get("/parties")
async def get_parties(request: Request = None, db: AsyncIOMotorDatabase = Depends(get_db)):
    fiscal = getattr(request.state, 'fiscal_year', None) if request is not None else None
    controller = PaymentReminderController(db)
    parties = await controller.list_parties_with_invoices(fiscal_year=fiscal)
    return {'status': 'success', 'parties': parties}


@router.get("/party/{party_name}")
async def get_party(party_name: str, request: Request = None, db: AsyncIOMotorDatabase = Depends(get_db)):
    fiscal = getattr(request.state, 'fiscal_year', None) if request is not None else None
    controller = PaymentReminderController(db)
    bills = await controller.get_party_invoices(party_name, fiscal_year=fiscal)
    # fetch saved email from parties collection
    parties_col = db['parties']
    saved = await parties_col.find_one({'party_name': {'$regex': f'^{party_name}$', '$options': 'i'}})
    saved_email = saved.get('email') if saved else None
    return {'status': 'success', 'party': party_name, 'email': saved_email, 'bills': bills}


@router.post("/party-email")
async def save_party_email(payload: dict, db: AsyncIOMotorDatabase = Depends(get_db)):
    party = payload.get('party_name')
    email = payload.get('email')
    if not party or not email:
        raise HTTPException(status_code=400, detail='party_name and email required')
    controller = PaymentReminderController(db)
    await controller.save_party_email(party, email)
    return {'status': 'success'}


@router.post("/send-single")
async def send_single(payload: dict, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        party = payload.get('party_name')
        email = payload.get('party_email')
        invoice_no = payload.get('invoice_no')
        reminder_days = int(payload.get('reminder_days') or 0)

        if not (party and email and invoice_no):
            raise HTTPException(status_code=400, detail='party_name, party_email and invoice_no required')

        # fetch invoice
        bill = await db['bills'].find_one({'invoice_no': invoice_no})
        if not bill:
            raise HTTPException(status_code=404, detail='invoice not found')

        pending = float(bill.get('grand_total') or 0) - float(bill.get('total_paid') or 0)

        # send email
        try:
            payment_reminder_email_service.send_single_invoice_reminder(party, email, bill, pending)
            status = 'sent'
            error = None
        except Exception as exc:
            status = 'failed'
            error = str(exc)

        # record history
        history_doc = {
            'party_name': party,
            'party_email': email,
            'reminder_type': 'single',
            'invoice_numbers': [invoice_no],
            'invoice_ids': [str(bill.get('_id'))] if bill.get('_id') else [],
            'total_amount': float(bill.get('grand_total') or 0),
            'total_pending_amount': pending,
            'reminder_days': reminder_days,
            'email_subject': f"Payment Reminder - Invoice {invoice_no}",
            'email_status': status,
            'error_message': error,
        }
        await db['payment_reminder_history'].insert_one(history_doc)

        return {'status': 'success' if status == 'sent' else 'failed'}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-multiple")
async def send_multiple(payload: dict, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        party = payload.get('party_name')
        email = payload.get('party_email')
        invoice_nos = payload.get('invoice_numbers') or []
        reminder_days = int(payload.get('reminder_days') or 0)

        if not (party and email and invoice_nos):
            raise HTTPException(status_code=400, detail='party_name, party_email and invoice_numbers required')

        bills = await db['bills'].find({'invoice_no': {'$in': invoice_nos}}).to_list(length=None)
        if not bills:
            raise HTTPException(status_code=404, detail='invoices not found')

        total_pending = 0.0
        total_amount = 0.0
        for bill in bills:
            amt = float(bill.get('grand_total') or 0)
            paid = float(bill.get('total_paid') or 0)
            pending = max(0.0, amt - paid)
            total_amount += amt
            total_pending += pending

        try:
            payment_reminder_email_service.send_multiple_invoice_reminder(party, email, bills, total_pending)
            status = 'sent'
            error = None
        except Exception as exc:
            status = 'failed'
            error = str(exc)

        history_doc = {
            'party_name': party,
            'party_email': email,
            'reminder_type': 'multiple',
            'invoice_numbers': invoice_nos,
            'invoice_ids': [str(b.get('_id')) for b in bills if b.get('_id')],
            'total_amount': total_amount,
            'total_pending_amount': total_pending,
            'reminder_days': reminder_days,
            'email_subject': 'Payment Reminder - Pending Invoices',
            'email_status': status,
            'error_message': error,
        }
        await db['payment_reminder_history'].insert_one(history_doc)

        return {'status': 'success' if status == 'sent' else 'failed'}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/history')
async def get_history(limit: int = 100, db: AsyncIOMotorDatabase = Depends(get_db)):
    docs = await db['payment_reminder_history'].find().sort([('sent_at', -1)]).to_list(length=limit)
    for d in docs:
        if '_id' in d:
            d['_id'] = str(d['_id'])
    return {'status': 'success', 'history': docs}


@router.get('/history/{party_name}')
async def get_history_by_party(party_name: str, limit: int = 100, db: AsyncIOMotorDatabase = Depends(get_db)):
    docs = await db['payment_reminder_history'].find({'party_name': {'$regex': party_name, '$options': 'i'}}).sort([('sent_at', -1)]).to_list(length=limit)
    for d in docs:
        if '_id' in d:
            d['_id'] = str(d['_id'])
    return {'status': 'success', 'history': docs}

*** End Patch