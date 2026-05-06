from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.services import payment_reminder_email_service


router = APIRouter(prefix="/api/payment-reminders", tags=["PaymentReminders"])


def _norm(value: Any) -> str:
    return str(value or '').strip()


def _iso(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _parse_dt(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except Exception:
            return None
    return None


def _pending_amount(bill: Dict[str, Any]) -> float:
    grand_total = float(bill.get('grand_total') or 0)
    paid_amount = float(bill.get('paid_amount') or bill.get('total_paid') or 0)
    remaining_amount = bill.get('remaining_amount')
    if remaining_amount is not None:
        try:
            return max(0.0, float(remaining_amount))
        except Exception:
            pass
    return max(0.0, grand_total - paid_amount)


def _reminder_days_label(reminder_days: int) -> str:
    days = int(reminder_days or 0)
    if days in {20, 30, 45}:
        return f"{days} days"
    return f"Custom - {days} days"


def _config_key(party_name: str, reminder_type: str, invoice_numbers: List[str]) -> str:
    numbers = '|'.join(sorted(_norm(value) for value in invoice_numbers if _norm(value)))
    return f"{_norm(party_name).lower()}|{reminder_type}|{numbers}"


def _days_left(next_reminder_date: Optional[datetime], now: Optional[datetime] = None) -> int:
    if not next_reminder_date:
        return 0
    now = now or datetime.utcnow()
    return (next_reminder_date.date() - now.date()).days


async def _get_saved_email(db: AsyncIOMotorDatabase, party_name: str) -> Optional[str]:
    party = _norm(party_name)
    if not party:
        return None

    contact = await db['party_contacts'].find_one({'party_name': {'$regex': f'^{party}$', '$options': 'i'}})
    if contact and contact.get('email'):
        return contact.get('email')

    existing = await db['parties'].find_one({'party_name': {'$regex': f'^{party}$', '$options': 'i'}})
    return existing.get('email') if existing else None


async def _save_email(db: AsyncIOMotorDatabase, party_name: str, email: str) -> None:
    now = datetime.utcnow()
    await db['party_contacts'].update_one(
        {'party_name': {'$regex': f'^{_norm(party_name)}$', '$options': 'i'}},
        {
            '$set': {
                'partyName': _norm(party_name),
                'party_name': _norm(party_name),
                'email': email,
                'updatedAt': now,
            },
            '$setOnInsert': {'createdAt': now},
        },
        upsert=True,
    )


async def _load_active_configs(db: AsyncIOMotorDatabase, party_name: str) -> List[Dict[str, Any]]:
    return await db['payment_reminder_configs'].find({
        'party_name': {'$regex': f'^{_norm(party_name)}$', '$options': 'i'},
        'is_active': True,
    }).sort([('updated_at', -1)]).to_list(length=1000)


async def _load_party_bills(db: AsyncIOMotorDatabase, party_name: str, fiscal_year: Optional[str] = None) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = {
        'party_name': {'$regex': f'^{_norm(party_name)}$', '$options': 'i'},
        'status': {'$in': ['UNPAID', 'PARTIAL']},
    }
    if fiscal_year:
        query['fiscal_year'] = fiscal_year

    bills = await db['bills'].find(query).sort([('invoice_date', 1), ('invoice_no', 1)]).to_list(length=1000)
    active_configs = await _load_active_configs(db, party_name)
    active_map: Dict[str, Dict[str, Any]] = {}
    now = datetime.utcnow()
    for config in active_configs:
        next_reminder_date = _parse_dt(config.get('next_reminder_date'))
        days_left = config.get('days_left')
        if days_left is None:
            days_left = _days_left(next_reminder_date, now)
        for invoice_no in config.get('invoice_numbers') or []:
            active_map[_norm(invoice_no)] = {
                'next_reminder_date': _iso(next_reminder_date),
                'days_left': days_left,
                'reminder_type': config.get('reminder_type'),
                'payment_status': config.get('payment_status') or 'UNPAID',
            }

    enriched = []
    for bill in bills:
        invoice_no = _norm(bill.get('invoice_no'))
        active_info = active_map.get(invoice_no, {})
        pending = _pending_amount(bill)
        enriched.append({
            **bill,
            '_id': str(bill.get('_id')) if bill.get('_id') else None,
            'invoice_date': _iso(bill.get('invoice_date')),
            'pending_amount': pending,
            'payment_status': str(bill.get('status') or 'UNPAID').upper(),
            'reminder_status': 'Reminder Active' if active_info else 'Unpaid',
            'reminder_active': bool(active_info),
            'next_reminder_date': active_info.get('next_reminder_date'),
            'days_left': active_info.get('days_left'),
            'reminder_type': active_info.get('reminder_type'),
        })
    return enriched


async def _normalize_config(db: AsyncIOMotorDatabase, config: Dict[str, Any]) -> Dict[str, Any]:
    next_dt = _parse_dt(config.get('next_reminder_date'))
    last_dt = _parse_dt(config.get('last_reminder_sent_at'))
    created_dt = _parse_dt(config.get('created_at'))
    updated_dt = _parse_dt(config.get('updated_at'))
    days_left = config.get('days_left')
    if days_left is None:
        days_left = _days_left(next_dt)
    return {
        '_id': str(config.get('_id')) if config.get('_id') else None,
        'partyName': config.get('party_name'),
        'partyEmail': config.get('party_email'),
        'reminderType': config.get('reminder_type'),
        'invoiceIds': [str(value) for value in (config.get('invoice_ids') or [])],
        'invoiceNumbers': [str(value) for value in (config.get('invoice_numbers') or [])],
        'invoiceDates': [_iso(value) for value in (config.get('invoice_dates') or [])],
        'reminderDays': int(config.get('reminder_days') or 0),
        'lastReminderSentAt': _iso(last_dt),
        'nextReminderDate': _iso(next_dt),
        'daysLeft': days_left,
        'isActive': bool(config.get('is_active', True)),
        'paymentStatus': config.get('payment_status') or 'UNPAID',
        'createdAt': _iso(created_dt),
        'updatedAt': _iso(updated_dt),
        'closedAt': _iso(_parse_dt(config.get('closed_at'))),
        'reminderDaysLabel': _reminder_days_label(int(config.get('reminder_days') or 0)),
    }


async def _normalize_history(doc: Dict[str, Any]) -> Dict[str, Any]:
    next_dt = _parse_dt(doc.get('nextReminderDate') or doc.get('next_reminder_date'))
    sent_dt = _parse_dt(doc.get('sentAt') or doc.get('sent_at'))
    return {
        '_id': str(doc.get('_id')) if doc.get('_id') else None,
        'partyName': doc.get('partyName') or doc.get('party_name'),
        'partyEmail': doc.get('partyEmail') or doc.get('party_email'),
        'reminderType': doc.get('reminderType') or doc.get('reminder_type'),
        'invoiceNumbers': doc.get('invoiceNumbers') or doc.get('invoice_numbers') or [],
        'invoiceDates': doc.get('invoiceDates') or doc.get('invoice_dates') or [],
        'invoiceIds': doc.get('invoiceIds') or doc.get('invoice_ids') or [],
        'totalAmount': doc.get('totalAmount') if doc.get('totalAmount') is not None else doc.get('total_amount', 0),
        'totalPendingAmount': doc.get('totalPendingAmount') if doc.get('totalPendingAmount') is not None else doc.get('total_pending_amount', 0),
        'reminderDays': doc.get('reminderDays') if doc.get('reminderDays') is not None else doc.get('reminder_days', 0),
        'reminderDaysLabel': doc.get('reminderDaysLabel') or _reminder_days_label(int(doc.get('reminderDays') or doc.get('reminder_days') or 0)),
        'emailSubject': doc.get('emailSubject') or doc.get('email_subject'),
        'emailStatus': doc.get('emailStatus') or doc.get('email_status'),
        'sentAt': _iso(sent_dt),
        'nextReminderDate': _iso(next_dt),
        'daysLeft': doc.get('daysLeft') if doc.get('daysLeft') is not None else _days_left(next_dt, sent_dt or datetime.utcnow()),
        'paymentStatus': doc.get('paymentStatus') or doc.get('payment_status') or 'UNPAID',
        'errorMessage': doc.get('errorMessage') or doc.get('error_message'),
        'closedAt': _iso(_parse_dt(doc.get('closedAt') or doc.get('closed_at'))),
        'createdAt': _iso(_parse_dt(doc.get('createdAt') or doc.get('created_at'))),
        'updatedAt': _iso(_parse_dt(doc.get('updatedAt') or doc.get('updated_at'))),
        'action': doc.get('action') or doc.get('message'),
    }


async def _upsert_config(
    db: AsyncIOMotorDatabase,
    *,
    party_name: str,
    party_email: str,
    reminder_type: str,
    invoices: List[Dict[str, Any]],
    reminder_days: int,
    payment_status: str,
    sent_at: datetime,
) -> Dict[str, Any]:
    invoice_numbers = [_norm(inv.get('invoice_no')) for inv in invoices if _norm(inv.get('invoice_no'))]
    config_key = _config_key(party_name, reminder_type, invoice_numbers)
    next_reminder_date = sent_at + timedelta(days=max(0, int(reminder_days or 0)))
    payload = {
        'config_key': config_key,
        'party_name': _norm(party_name),
        'party_email': party_email,
        'reminder_type': reminder_type,
        'invoice_ids': [str(inv.get('_id')) for inv in invoices if inv.get('_id')],
        'invoice_numbers': invoice_numbers,
        'invoice_dates': [_iso(inv.get('invoice_date')) for inv in invoices],
        'reminder_days': int(reminder_days or 0),
        'last_reminder_sent_at': sent_at,
        'next_reminder_date': next_reminder_date,
        'days_left': max(0, int(reminder_days or 0)),
        'is_active': payment_status != 'PAID',
        'payment_status': payment_status,
        'closed_at': None,
        'updated_at': sent_at,
    }
    existing = await db['payment_reminder_configs'].find_one({'config_key': config_key})
    if existing:
        await db['payment_reminder_configs'].update_one({'_id': existing['_id']}, {'$set': payload, '$setOnInsert': {'created_at': existing.get('created_at') or sent_at}})
        payload['_id'] = existing['_id']
        payload['created_at'] = existing.get('created_at') or sent_at
    else:
        payload['created_at'] = sent_at
        result = await db['payment_reminder_configs'].insert_one(payload)
        payload['_id'] = result.inserted_id
    return await _normalize_config(db, payload)


async def _record_history(
    db: AsyncIOMotorDatabase,
    *,
    party_name: str,
    party_email: str,
    reminder_type: str,
    invoices: List[Dict[str, Any]],
    reminder_days: int,
    email_subject: str,
    email_status: str,
    sent_at: datetime,
    error_message: Optional[str],
    payment_status: str,
    closed_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    invoice_numbers = [_norm(inv.get('invoice_no')) for inv in invoices if _norm(inv.get('invoice_no'))]
    invoice_dates = [_iso(inv.get('invoice_date')) for inv in invoices]
    invoice_ids = [str(inv.get('_id')) for inv in invoices if inv.get('_id')]
    total_amount = 0.0
    total_pending = 0.0
    for inv in invoices:
        grand_total = float(inv.get('grand_total') or 0)
        paid_amount = float(inv.get('paid_amount') or inv.get('total_paid') or 0)
        pending_amount = max(0.0, grand_total - paid_amount)
        total_amount += grand_total
        total_pending += pending_amount

    doc = {
        'partyName': _norm(party_name),
        'partyEmail': party_email,
        'reminderType': reminder_type,
        'invoiceNumbers': invoice_numbers,
        'invoiceDates': invoice_dates,
        'invoiceIds': invoice_ids,
        'totalAmount': total_amount,
        'totalPendingAmount': total_pending,
        'reminderDays': int(reminder_days or 0),
        'reminderDaysLabel': _reminder_days_label(int(reminder_days or 0)),
        'emailSubject': email_subject,
        'emailStatus': email_status,
        'sentAt': sent_at,
        'nextReminderDate': sent_at + timedelta(days=max(0, int(reminder_days or 0))),
        'daysLeft': max(0, int(reminder_days or 0)),
        'paymentStatus': payment_status,
        'errorMessage': error_message,
        'closedAt': closed_at,
        'createdAt': sent_at,
        'updatedAt': sent_at,
    }
    result = await db['payment_reminder_history'].insert_one(doc)
    doc['_id'] = result.inserted_id
    return await _normalize_history(doc)


async def _send_single_flow(
    db: AsyncIOMotorDatabase,
    *,
    party_name: str,
    party_email: str,
    invoice_no: str,
    reminder_days: int,
) -> Dict[str, Any]:
    now = datetime.utcnow()
    bill = await db['bills'].find_one({'invoice_no': invoice_no})
    if not bill:
        raise HTTPException(status_code=404, detail='invoice not found')

    pending = _pending_amount(bill)
    if str(bill.get('status') or '').upper() == 'PAID' or pending <= 0:
        await db['payment_reminder_configs'].update_one(
            {'config_key': _config_key(party_name, 'single', [invoice_no])},
            {'$set': {'is_active': False, 'payment_status': 'Payment Received - Reminder Closed', 'closed_at': now, 'updated_at': now}},
            upsert=True,
        )
        history = await _record_history(
            db,
            party_name=party_name,
            party_email=party_email,
            reminder_type='single',
            invoices=[],
            reminder_days=reminder_days,
            email_subject=f'Payment Reminder - Invoice {invoice_no}',
            email_status='sent',
            sent_at=now,
            error_message=None,
            payment_status='Payment Received - Reminder Closed',
            closed_at=now,
        )
        return {'email_status': 'sent', 'history': history, 'closed': True}

    email_subject = f"Payment Reminder - Invoice {invoice_no}"
    try:
        payment_reminder_email_service.send_single_invoice_reminder(party_name, party_email, bill, pending)
        email_status = 'sent'
        error_message = None
    except Exception as exc:
        email_status = 'failed'
        error_message = str(exc)

    history = await _record_history(
        db,
        party_name=party_name,
        party_email=party_email,
        reminder_type='single',
        invoices=[bill],
        reminder_days=reminder_days,
        email_subject=email_subject,
        email_status=email_status,
        sent_at=now,
        error_message=error_message,
        payment_status=str(bill.get('status') or 'UNPAID').upper(),
    )

    config = None
    if email_status == 'sent':
        config = await _upsert_config(
            db,
            party_name=party_name,
            party_email=party_email,
            reminder_type='single',
            invoices=[bill],
            reminder_days=reminder_days,
            payment_status=str(bill.get('status') or 'UNPAID').upper(),
            sent_at=now,
        )

    return {'email_status': email_status, 'error_message': error_message, 'history': history, 'config': config}


async def _send_multiple_flow(
    db: AsyncIOMotorDatabase,
    *,
    party_name: str,
    party_email: str,
    invoice_numbers: List[str],
    reminder_days: int,
) -> Dict[str, Any]:
    now = datetime.utcnow()
    bills: List[Dict[str, Any]] = []
    for invoice_no in invoice_numbers:
        bill = await db['bills'].find_one({'invoice_no': invoice_no})
        if not bill:
            continue
        if str(bill.get('status') or '').upper() == 'PAID' or _pending_amount(bill) <= 0:
            continue
        bills.append(bill)

    if not bills:
        history = await _record_history(
            db,
            party_name=party_name,
            party_email=party_email,
            reminder_type='multiple',
            invoices=[],
            reminder_days=reminder_days,
            email_subject='Payment Received - Reminder Closed',
            email_status='sent',
            sent_at=now,
            error_message=None,
            payment_status='Payment Received - Reminder Closed',
            closed_at=now,
        )
        await db['payment_reminder_configs'].update_one(
            {'config_key': _config_key(party_name, 'multiple', invoice_numbers)},
            {'$set': {'is_active': False, 'payment_status': 'Payment Received - Reminder Closed', 'closed_at': now, 'updated_at': now}},
            upsert=True,
        )
        return {'email_status': 'sent', 'history': history, 'closed': True}

    total_pending = sum(_pending_amount(bill) for bill in bills)
    try:
        payment_reminder_email_service.send_multiple_invoice_reminder(party_name, party_email, bills, total_pending)
        email_status = 'sent'
        error_message = None
    except Exception as exc:
        email_status = 'failed'
        error_message = str(exc)

    history = await _record_history(
        db,
        party_name=party_name,
        party_email=party_email,
        reminder_type='multiple',
        invoices=bills,
        reminder_days=reminder_days,
        email_subject='Payment Reminder - Pending Invoices',
        email_status=email_status,
        sent_at=now,
        error_message=error_message,
        payment_status='UNPAID',
    )

    config = None
    if email_status == 'sent':
        config = await _upsert_config(
            db,
            party_name=party_name,
            party_email=party_email,
            reminder_type='multiple',
            invoices=bills,
            reminder_days=reminder_days,
            payment_status='UNPAID',
            sent_at=now,
        )

    return {'email_status': email_status, 'error_message': error_message, 'history': history, 'config': config}


async def _stop_invoice_in_configs(db: AsyncIOMotorDatabase, *, invoice_number: Optional[str] = None, invoice_id: Optional[str] = None, party_name: Optional[str] = None) -> Dict[str, Any]:
    """Stop/deactivate an invoice reminder in any active config(s).
    Returns a summary with affected configs and created history entries.
    """
    now = datetime.utcnow()
    query = {'is_active': True}
    if party_name:
        query['party_name'] = {'$regex': f'^{_norm(party_name)}$', '$options': 'i'}

    or_clauses = []
    if invoice_number:
        or_clauses.append({'invoice_numbers': invoice_number})
    if invoice_id:
        or_clauses.append({'invoice_ids': invoice_id})
    if or_clauses:
        query['$or'] = or_clauses

    configs = await db['payment_reminder_configs'].find(query).to_list(length=100)
    histories = []
    affected = []
    for cfg in configs:
        cfg_id = cfg.get('_id')
        reminder_type = cfg.get('reminder_type') or 'single'
        invoice_numbers = [str(x) for x in (cfg.get('invoice_numbers') or [])]
        invoice_ids = [str(x) for x in (cfg.get('invoice_ids') or [])]
        invoice_dates = [x for x in (cfg.get('invoice_dates') or [])]

        # determine which invoice(s) to stop
        targets = []
        if invoice_number and invoice_number in invoice_numbers:
            idx = invoice_numbers.index(invoice_number)
            targets.append({'invoice_no': invoice_numbers[idx], '_id': invoice_ids[idx] if idx < len(invoice_ids) else None, 'invoice_date': invoice_dates[idx] if idx < len(invoice_dates) else None})
        elif invoice_id and invoice_id in invoice_ids:
            idx = invoice_ids.index(invoice_id)
            targets.append({'invoice_no': invoice_numbers[idx] if idx < len(invoice_numbers) else None, '_id': invoice_ids[idx], 'invoice_date': invoice_dates[idx] if idx < len(invoice_dates) else None})

        if not targets:
            continue

        # For multiple configs, remove only the target invoice
        if reminder_type == 'multiple' and len(invoice_numbers) > 1:
            # remove target(s)
            for t in targets:
                if t.get('invoice_no') in invoice_numbers:
                    i = invoice_numbers.index(t.get('invoice_no'))
                    invoice_numbers.pop(i)
                    if i < len(invoice_ids):
                        invoice_ids.pop(i)
                    if i < len(invoice_dates):
                        invoice_dates.pop(i)

            await db['payment_reminder_configs'].update_one({'_id': cfg_id}, {'$set': {'invoice_numbers': invoice_numbers, 'invoice_ids': invoice_ids, 'invoice_dates': invoice_dates, 'updated_at': now}})
            affected.append({'config_id': str(cfg_id), 'action': 'removed_invoice'})
            # record a stopped history for each removed invoice
            for t in targets:
                bill = await db['bills'].find_one({'invoice_no': t.get('invoice_no')})
                invoices = [bill] if bill else []
                history = await _record_history(
                    db,
                    party_name=cfg.get('party_name'),
                    party_email=cfg.get('party_email'),
                    reminder_type=cfg.get('reminder_type') or 'multiple',
                    invoices=invoices,
                    reminder_days=int(cfg.get('reminder_days') or 0),
                    email_subject=f"Reminder stopped - Invoice {t.get('invoice_no')}",
                    email_status='stopped',
                    sent_at=now,
                    error_message=None,
                    payment_status=str(bill.get('status') or 'UNPAID').upper() if bill else 'UNPAID',
                    closed_at=None,
                )
                # attach action text
                await db['payment_reminder_history'].update_one({'_id': history.get('_id')}, {'$set': {'action': 'Reminder stopped manually'}})
                histories.append(history)

        else:
            # single or last invoice in config -> deactivate the config
            await db['payment_reminder_configs'].update_one({'_id': cfg_id}, {'$set': {'is_active': False, 'closed_at': now, 'updated_at': now}})
            affected.append({'config_id': str(cfg_id), 'action': 'deactivated'})
            # record history for stopped invoice(s)
            for t in targets:
                bill = await db['bills'].find_one({'invoice_no': t.get('invoice_no')})
                invoices = [bill] if bill else []
                history = await _record_history(
                    db,
                    party_name=cfg.get('party_name'),
                    party_email=cfg.get('party_email'),
                    reminder_type=cfg.get('reminder_type') or 'single',
                    invoices=invoices,
                    reminder_days=int(cfg.get('reminder_days') or 0),
                    email_subject=f"Reminder stopped - Invoice {t.get('invoice_no')}",
                    email_status='stopped',
                    sent_at=now,
                    error_message=None,
                    payment_status=str(bill.get('status') or 'UNPAID').upper() if bill else 'UNPAID',
                    closed_at=now,
                )
                await db['payment_reminder_history'].update_one({'_id': history.get('_id')}, {'$set': {'action': 'Reminder stopped manually'}})
                histories.append(history)

    return {'affected': affected, 'histories': histories}


@router.patch('/stop/{invoice_no}')
async def stop_reminder_by_invoice(invoice_no: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Stop reminder for an invoice number across active configs."""
    if not invoice_no:
        raise HTTPException(status_code=400, detail='invoice_no required')
    result = await _stop_invoice_in_configs(db, invoice_number=str(invoice_no))
    return {'status': 'success', 'result': result}


@router.patch('/stop')
async def stop_reminder(payload: dict, db: AsyncIOMotorDatabase = Depends(get_db)):
    invoice_id = payload.get('invoiceId') or payload.get('invoice_id') or payload.get('invoiceNumber') or payload.get('invoice_no')
    party_name = payload.get('partyName') or payload.get('party_name')
    if not invoice_id:
        raise HTTPException(status_code=400, detail='invoiceId required')
    # Try numeric invoice match first, otherwise treat as invoice id
    result = await _stop_invoice_in_configs(db, invoice_number=str(invoice_id), party_name=party_name)
    return {'status': 'success', 'result': result}


@router.get("/parties")
async def get_parties(request: Request = None, db: AsyncIOMotorDatabase = Depends(get_db)):
    fiscal = getattr(request.state, 'fiscal_year', None) if request is not None else None
    query: Dict[str, Any] = {'status': {'$in': ['UNPAID', 'PARTIAL']}}
    if fiscal:
        query['fiscal_year'] = fiscal

    pipeline = [
        {'$match': query},
        {
            '$group': {
                '_id': '$party_name',
                'invoice_count': {'$sum': 1},
                'pending_amount': {
                    '$sum': {
                        '$max': [0, {'$subtract': ['$grand_total', {'$ifNull': ['$paid_amount', {'$ifNull': ['$total_paid', 0]}]}]}]
                    }
                }
            }
        },
        {'$project': {'_id': 0, 'party_name': '$_id', 'invoice_count': 1, 'pending_amount': 1}},
        {'$sort': {'party_name': 1}},
    ]
    parties = await db['bills'].aggregate(pipeline).to_list(length=1000)
    return {'status': 'success', 'parties': parties}


@router.get("/party/{party_name}")
async def get_party(party_name: str, request: Request = None, db: AsyncIOMotorDatabase = Depends(get_db)):
    fiscal = getattr(request.state, 'fiscal_year', None) if request is not None else None
    saved_email = await _get_saved_email(db, party_name)
    bills = await _load_party_bills(db, party_name, fiscal_year=fiscal)
    active_configs = await _load_active_configs(db, party_name)
    normalized_configs = [await _normalize_config(db, config) for config in active_configs]
    return {
        'status': 'success',
        'partyName': _norm(party_name),
        'email': saved_email,
        'bills': bills,
        'activeConfigs': normalized_configs,
    }


@router.post("/party-email")
async def save_party_email(payload: dict, db: AsyncIOMotorDatabase = Depends(get_db)):
    party = payload.get('party_name') or payload.get('partyName')
    email = payload.get('email') or payload.get('party_email')
    if not party or not email:
        raise HTTPException(status_code=400, detail='party_name and email required')
    await _save_email(db, party, email)
    return {'status': 'success'}


@router.post("/send-single")
async def send_single(payload: dict, request: Request = None, db: AsyncIOMotorDatabase = Depends(get_db)):
    party = payload.get('party_name') or payload.get('partyName')
    email = payload.get('party_email') or payload.get('partyEmail')
    invoice_no = payload.get('invoice_no') or payload.get('invoiceNumber')
    reminder_days = int(payload.get('reminder_days') or payload.get('reminderDays') or 0)
    if not (party and email and invoice_no):
        raise HTTPException(status_code=400, detail='party_name, party_email and invoice_no required')
    result = await _send_single_flow(db, party_name=party, party_email=email, invoice_no=str(invoice_no), reminder_days=reminder_days)
    return {'status': result['email_status'], **result}


@router.post("/send-multiple")
async def send_multiple(payload: dict, request: Request = None, db: AsyncIOMotorDatabase = Depends(get_db)):
    party = payload.get('party_name') or payload.get('partyName')
    email = payload.get('party_email') or payload.get('partyEmail')
    invoice_nos = payload.get('invoice_numbers') or payload.get('invoiceNumbers') or []
    reminder_days = int(payload.get('reminder_days') or payload.get('reminderDays') or 0)
    if not (party and email and invoice_nos):
        raise HTTPException(status_code=400, detail='party_name, party_email and invoice_numbers required')
    result = await _send_multiple_flow(db, party_name=party, party_email=email, invoice_numbers=[str(value) for value in invoice_nos], reminder_days=reminder_days)
    return {'status': result['email_status'], **result}


@router.get('/history')
async def get_history(limit: int = 100, db: AsyncIOMotorDatabase = Depends(get_db)):
    docs = await db['payment_reminder_history'].find().sort([('sentAt', -1), ('sent_at', -1)]).to_list(length=limit)
    return {'status': 'success', 'history': [await _normalize_history(doc) for doc in docs]}


@router.get('/history/{party_name}')
async def get_history_by_party(party_name: str, limit: int = 100, db: AsyncIOMotorDatabase = Depends(get_db)):
    docs = await db['payment_reminder_history'].find({
        '$or': [
            {'partyName': {'$regex': party_name, '$options': 'i'}},
            {'party_name': {'$regex': party_name, '$options': 'i'}},
        ]
    }).sort([('sentAt', -1), ('sent_at', -1)]).to_list(length=limit)
    return {'status': 'success', 'history': [await _normalize_history(doc) for doc in docs]}


@router.delete('/history/{party_name}')
async def delete_history_by_party(party_name: str, payload: dict, request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    from app.routes.auth_routes import _verify_password
    
    # Get logged-in user
    logged_in_user = getattr(request.state, 'user', None)
    if not logged_in_user:
        raise HTTPException(status_code=401, detail='User not authenticated')
    
    # Get entered password from payload
    password = payload.get('password') or payload.get('pwd')
    if not password:
        raise HTTPException(status_code=400, detail='Password required')
    
    # Get auth settings from database to verify password
    auth_settings = await db['auth_settings'].find_one({'_id': 'primary_auth'})
    if not auth_settings or not auth_settings.get('password_hash'):
        raise HTTPException(status_code=500, detail='Authentication system not configured')
    
    # Verify password against stored hash
    if not _verify_password(password, auth_settings.get('password_hash')):
        raise HTTPException(status_code=401, detail='Invalid password')
    
    now = datetime.utcnow()
    party_norm = _norm(party_name)
    
    # Delete all history for this party
    history_result = await db['payment_reminder_history'].delete_many({
        '$or': [
            {'partyName': {'$regex': f'^{party_norm}$', '$options': 'i'}},
            {'party_name': {'$regex': f'^{party_norm}$', '$options': 'i'}},
        ]
    })
    
    # Deactivate/update active reminder configs for this party
    configs_result = await db['payment_reminder_configs'].update_many(
        {'party_name': {'$regex': f'^{party_norm}$', '$options': 'i'}},
        {'$set': {'is_active': False, 'closed_at': now, 'updated_at': now, 'status': 'history_deleted'}}
    )
    
    return {
        'status': 'success',
        'message': 'Payment reminder history deleted and reminders reset successfully',
        'deleted_history_count': history_result.deleted_count,
        'updated_config_count': configs_result.modified_count,
    }