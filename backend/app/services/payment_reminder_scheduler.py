import asyncio
from datetime import datetime, timedelta
from app.services import payment_reminder_email_service
from app.core.config import logger

async def run_scheduler_loop(db):
    """Run once daily: check active configs and send reminders."""
    while True:
        try:
            now = datetime.utcnow()
            configs_col = db['payment_reminder_configs']
            configs = await configs_col.find({'is_active': True}).to_list(length=None)
            for cfg in configs:
                try:
                    reminder_days = int(cfg.get('reminder_days') or 0)
                    last_sent = cfg.get('last_reminder_sent_at')
                    # if never sent or it's been >= reminder_days
                    should_send = False
                    if not last_sent:
                        should_send = True
                    else:
                        if isinstance(last_sent, str):
                            # Attempt parse
                            try:
                                last_sent_dt = datetime.fromisoformat(last_sent)
                            except Exception:
                                last_sent_dt = last_sent
                        else:
                            last_sent_dt = last_sent

                        if isinstance(last_sent_dt, datetime):
                            delta = now - last_sent_dt
                            if delta.days >= reminder_days:
                                should_send = True

                    if not should_send:
                        continue

                    # Fetch relevant invoices
                    invoice_ids = cfg.get('invoice_ids') or []
                    invoice_numbers = cfg.get('invoice_numbers') or []
                    party = cfg.get('party_name')
                    email = cfg.get('party_email')

                    if cfg.get('reminder_type') == 'single' and invoice_numbers:
                        invoice_no = invoice_numbers[0]
                        bill = await db['bills'].find_one({'invoice_no': invoice_no})
                        if not bill:
                            continue
                        pending = float(bill.get('grand_total') or 0) - float(bill.get('total_paid') or 0)
                        if pending <= 0:
                            # Mark inactive to stop future reminders
                            await configs_col.update_one({'_id': cfg['_id']}, {'$set': {'is_active': False}})
                            continue
                        try:
                            payment_reminder_email_service.send_single_invoice_reminder(party, email, bill, pending)
                            email_status = 'sent'
                            error = None
                        except Exception as exc:
                            email_status = 'failed'
                            error = str(exc)

                        history = {
                            'party_name': party,
                            'party_email': email,
                            'reminder_type': 'single',
                            'invoice_numbers': [invoice_no],
                            'invoice_ids': [str(bill.get('_id'))] if bill.get('_id') else [],
                            'total_amount': float(bill.get('grand_total') or 0),
                            'total_pending_amount': pending,
                            'reminder_days': reminder_days,
                            'email_subject': f"Payment Reminder - Invoice {invoice_no}",
                            'email_status': email_status,
                            'error_message': error,
                            'sent_at': datetime.utcnow()
                        }
                        await db['payment_reminder_history'].insert_one(history)
                        await configs_col.update_one({'_id': cfg['_id']}, {'$set': {'last_reminder_sent_at': datetime.utcnow()}})

                    elif cfg.get('reminder_type') == 'multiple' and invoice_numbers:
                        bills = await db['bills'].find({'invoice_no': {'$in': invoice_numbers}}).to_list(length=None)
                        total_pending = 0.0
                        total_amount = 0.0
                        unpaid_bills = []
                        for b in bills:
                            amt = float(b.get('grand_total') or 0)
                            paid = float(b.get('total_paid') or 0)
                            pending = max(0.0, amt - paid)
                            if pending > 0:
                                unpaid_bills.append(b)
                                total_pending += pending
                                total_amount += amt

                        if not unpaid_bills:
                            await configs_col.update_one({'_id': cfg['_id']}, {'$set': {'is_active': False}})
                            continue

                        try:
                            payment_reminder_email_service.send_multiple_invoice_reminder(party, email, unpaid_bills, total_pending)
                            email_status = 'sent'
                            error = None
                        except Exception as exc:
                            email_status = 'failed'
                            error = str(exc)

                        history = {
                            'party_name': party,
                            'party_email': email,
                            'reminder_type': 'multiple',
                            'invoice_numbers': invoice_numbers,
                            'invoice_ids': [str(b.get('_id')) for b in unpaid_bills if b.get('_id')],
                            'total_amount': total_amount,
                            'total_pending_amount': total_pending,
                            'reminder_days': reminder_days,
                            'email_subject': 'Payment Reminder - Pending Invoices',
                            'email_status': email_status,
                            'error_message': error,
                            'sent_at': datetime.utcnow()
                        }
                        await db['payment_reminder_history'].insert_one(history)
                        await configs_col.update_one({'_id': cfg['_id']}, {'$set': {'last_reminder_sent_at': datetime.utcnow()}})

                except Exception as exc:
                    logger.error(f"Error processing config {cfg.get('_id')}: {exc}")

        except Exception as exc:
            logger.error(f"Payment reminder scheduler error: {exc}")

        # Sleep until next day (approx)
        await asyncio.sleep(24 * 60 * 60)

*** End Patch