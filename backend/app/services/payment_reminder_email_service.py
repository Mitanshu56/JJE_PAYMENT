from email.message import EmailMessage
from datetime import datetime
from app.core.config import settings, logger
import smtplib


def _send_email(subject: str, to_email: str, body: str) -> None:
    smtp_username = (settings.SMTP_USERNAME or "").strip()
    smtp_password = (settings.SMTP_PASSWORD or "").replace(" ", "")

    if not smtp_username or not smtp_password:
        raise RuntimeError("SMTP credentials are not configured")

    from_email = (settings.SMTP_FROM_EMAIL or smtp_username).strip()

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
    except Exception as exc:
        logger.error(f"Failed to send payment reminder email: {exc}")
        raise


def build_single_invoice_body(party_name: str, invoice: dict, pending_amount: float) -> str:
    parts = [
        f"Dear {party_name},",
        "",
        "This is a reminder regarding your pending payment.",
        "",
        f"Invoice Number: {invoice.get('invoice_no')}",
        f"Invoice Amount: ₹{invoice.get('grand_total')}",
        f"Pending Amount: ₹{pending_amount}",
        f"Invoice Date: {invoice.get('invoice_date')}",
        "",
        "Kindly complete the payment as soon as possible.",
        "",
        "Thank you.",
    ]
    return "\n".join(parts)


def build_multiple_invoice_body(party_name: str, invoices: list, total_pending: float) -> str:
    parts = [
        f"Dear {party_name},",
        "",
        "This is a reminder regarding your pending payments.",
        "",
        "Pending Invoice Details:",
    ]
    # invoiceTable
    table_lines = ["Invoice No | Invoice Amount | Pending Amount"]
    for inv in invoices:
        inv_no = inv.get('invoice_no')
        amt = inv.get('grand_total')
        pending = float(inv.get('grand_total') or 0) - float(inv.get('total_paid') or 0)
        table_lines.append(f"{inv_no} | ₹{amt} | ₹{pending}")

    parts.extend(table_lines)
    parts.append("")
    parts.append(f"Total Pending Amount: ₹{total_pending}")
    parts.append("")
    parts.append("Kindly complete the payment as soon as possible.")
    parts.append("")
    parts.append("Thank you.")

    return "\n".join(parts)


def send_single_invoice_reminder(party_name: str, party_email: str, invoice: dict, pending_amount: float) -> None:
    subject = f"Payment Reminder - Invoice {invoice.get('invoice_no')}"
    body = build_single_invoice_body(party_name, invoice, pending_amount)
    _send_email(subject, party_email, body)
    return


def send_multiple_invoice_reminder(party_name: str, party_email: str, invoices: list, total_pending: float) -> None:
    subject = "Payment Reminder - Pending Invoices"
    body = build_multiple_invoice_body(party_name, invoices, total_pending)
    _send_email(subject, party_email, body)
    return

*** End Patch