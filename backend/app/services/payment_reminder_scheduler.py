import asyncio
from datetime import datetime, timedelta

from app.core.config import logger
from app.services import payment_reminder_email_service


def _parse_dt(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except Exception:
            return None
    return None


def _pending_amount(bill):
    grand_total = float(bill.get('grand_total') or 0)
    paid_amount = float(bill.get('paid_amount') or bill.get('total_paid') or 0)
    remaining_amount = bill.get('remaining_amount')
    if remaining_amount is not None:
        try:
            return max(0.0, float(remaining_amount))
        except Exception:
            pass
    return max(0.0, grand_total - paid_amount)


async def run_scheduler_loop(db):
    """Run a daily loop that resends due reminders and closes paid ones."""
    while True:
        try:
            now = datetime.utcnow()
            configs_col = db['payment_reminder_configs']
            active_configs = await configs_col.find({'is_active': True}).to_list(length=None)

            for config in active_configs:
                try:
                    invoice_numbers = [str(value) for value in (config.get('invoice_numbers') or []) if str(value or '').strip()]
                    if not invoice_numbers:
                        await configs_col.update_one({'_id': config['_id']}, {'$set': {'is_active': False, 'closed_at': now, 'updated_at': now, 'payment_status': 'Payment Received - Reminder Closed'}})
                        continue

                    unpaid_bills = []
                    for invoice_no in invoice_numbers:
                        bill = await db['bills'].find_one({'invoice_no': invoice_no})
                        if not bill:
                            continue
                        if str(bill.get('status') or '').upper() == 'PAID' or _pending_amount(bill) <= 0:
                            continue
                        unpaid_bills.append(bill)

                    if not unpaid_bills:
                        await configs_col.update_one(
                            {'_id': config['_id']},
                            {'$set': {'is_active': False, 'closed_at': now, 'updated_at': now, 'payment_status': 'Payment Received - Reminder Closed', 'days_left': 0}},
                        )
                        next_reminder = sent_at + timedelta(days=reminder_days)
                        await db['payment_reminder_history'].insert_one({
                            'partyName': config.get('party_name'),
                            'partyEmail': config.get('party_email'),
                            'reminderType': config.get('reminder_type'),
                            'invoiceNumbers': invoice_numbers,
                            'invoiceDates': config.get('invoice_dates') or [],
                            'invoiceIds': config.get('invoice_ids') or [],
                            'totalAmount': 0,
                            'totalPendingAmount': 0,
                            'reminderDays': int(config.get('reminder_days') or 0),
                            'reminderDaysLabel': config.get('reminder_days_label') or f"Custom - {int(config.get('reminder_days') or 0)} days",
                            'emailSubject': 'Payment Received - Reminder Closed',
                            'emailStatus': 'sent',
                            'sentAt': now,
                            'nextReminderDate': None,
                            'daysLeft': 0,
                            'paymentStatus': 'Payment Received - Reminder Closed',
                            'errorMessage': None,
                            'closedAt': now,
                            'createdAt': now,
                            'updatedAt': now,
                        })
                        continue

                    next_reminder_date = _parse_dt(config.get('next_reminder_date'))
                    days_left = (next_reminder_date.date() - now.date()).days if next_reminder_date else 0
                    if next_reminder_date and now.date() < next_reminder_date.date():
                        await configs_col.update_one({'_id': config['_id']}, {'$set': {'days_left': days_left, 'updated_at': now}})
                        continue

                    party_name = config.get('party_name') or ''
                    party_email = config.get('party_email') or ''
                    reminder_type = config.get('reminder_type') or 'single'
                    reminder_days = int(config.get('reminder_days') or 0)

                    if reminder_type == 'single':
                        bill = unpaid_bills[0]
                        pending = _pending_amount(bill)
                        try:
                            payment_reminder_email_service.send_single_invoice_reminder(party_name, party_email, bill, pending)
                            email_status = 'sent'
                            error_message = None
                        except Exception as exc:
                            email_status = 'failed'
                            error_message = str(exc)

                        sent_at = datetime.utcnow()
                        await db['payment_reminder_history'].insert_one({
                            'partyName': party_name,
                            'partyEmail': party_email,
                            'reminderType': 'single',
                            'invoiceNumbers': [str(bill.get('invoice_no') or '')],
                            'invoiceDates': [bill.get('invoice_date')],
                            'invoiceIds': [str(bill.get('_id'))] if bill.get('_id') else [],
                            'totalAmount': float(bill.get('grand_total') or 0),
                            'totalPendingAmount': pending,
                            'reminderDays': reminder_days,
                            'reminderDaysLabel': config.get('reminder_days_label') or f"Custom - {reminder_days} days",
                            'emailSubject': f"Payment Reminder - Invoice {bill.get('invoice_no')}",
                            'emailStatus': email_status,
                            'sentAt': sent_at,
                            'nextReminderDate': next_reminder,
                            'daysLeft': reminder_days,
                            'paymentStatus': str(bill.get('status') or 'UNPAID').upper(),
                            'errorMessage': error_message,
                            'closedAt': None,
                            'createdAt': sent_at,
                            'updatedAt': sent_at,
                        })
                        await configs_col.update_one(
                            {'_id': config['_id']},
                            {'$set': {'last_reminder_sent_at': sent_at, 'next_reminder_date': next_reminder, 'days_left': reminder_days, 'updated_at': sent_at, 'payment_status': 'UNPAID', 'is_active': True}},
                        )

                    else:
                        total_pending = sum(_pending_amount(bill) for bill in unpaid_bills)
                        try:
                            payment_reminder_email_service.send_multiple_invoice_reminder(party_name, party_email, unpaid_bills, total_pending)
                            email_status = 'sent'
                            error_message = None
                        except Exception as exc:
                            email_status = 'failed'
                            error_message = str(exc)

                        sent_at = datetime.utcnow()
                        next_reminder = sent_at + timedelta(days=reminder_days)
                        await db['payment_reminder_history'].insert_one({
                            'partyName': party_name,
                            'partyEmail': party_email,
                            'reminderType': 'multiple',
                            'invoiceNumbers': [str(bill.get('invoice_no') or '') for bill in unpaid_bills],
                            'invoiceDates': [bill.get('invoice_date') for bill in unpaid_bills],
                            'invoiceIds': [str(bill.get('_id')) for bill in unpaid_bills if bill.get('_id')],
                            'totalAmount': sum(float(bill.get('grand_total') or 0) for bill in unpaid_bills),
                            'totalPendingAmount': total_pending,
                            'reminderDays': reminder_days,
                            'reminderDaysLabel': config.get('reminder_days_label') or f"Custom - {reminder_days} days",
                            'emailSubject': 'Payment Reminder - Pending Invoices',
                            'emailStatus': email_status,
                            'sentAt': sent_at,
                            'nextReminderDate': next_reminder,
                            'daysLeft': reminder_days,
                            'paymentStatus': 'UNPAID',
                            'errorMessage': error_message,
                            'closedAt': None,
                            'createdAt': sent_at,
                            'updatedAt': sent_at,
                        })
                        await configs_col.update_one(
                            {'_id': config['_id']},
                            {
                                '$set': {
                                    'invoice_numbers': [str(bill.get('invoice_no') or '') for bill in unpaid_bills],
                                    'invoice_ids': [str(bill.get('_id')) for bill in unpaid_bills if bill.get('_id')],
                                    'invoice_dates': [bill.get('invoice_date') for bill in unpaid_bills],
                                    'last_reminder_sent_at': sent_at,
                                    'next_reminder_date': next_reminder,
                                    'days_left': reminder_days,
                                    'updated_at': sent_at,
                                    'payment_status': 'UNPAID',
                                    'is_active': True,
                                }
                            },
                        )

                except Exception as exc:
                    logger.error(f"Error processing reminder config {config.get('_id')}: {exc}")

        except Exception as exc:
            logger.error(f"Payment reminder scheduler error: {exc}")

        await asyncio.sleep(24 * 60 * 60)