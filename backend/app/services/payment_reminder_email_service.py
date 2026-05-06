from email.message import EmailMessage
from datetime import datetime
from typing import Any
from app.core.config import settings, logger
import smtplib


def _send_email(subject: str, to_email: str, html: str, text: str) -> None:
    smtp_username = (settings.SMTP_USERNAME or "").strip()
    smtp_password = (settings.SMTP_PASSWORD or "").replace(" ", "")

    if not smtp_username or not smtp_password:
        raise RuntimeError("SMTP credentials are not configured")

    from_email = (settings.SMTP_FROM_EMAIL or smtp_username).strip()

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
    except Exception as exc:
        logger.error(f"Failed to send payment reminder email: {exc}")
        raise


def _format_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, str) and value:
        # Try to parse and reformat
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt.strftime("%d/%m/%Y")
        except Exception:
            return value[:10]
    return "N/A"


def _invoice_values(invoice: dict, pending_amount: float | None = None) -> dict:
        invoice_amount = float(invoice.get('grand_total') or invoice.get('invoice_amount') or 0)
        paid_amount = float(invoice.get('paid_amount') or invoice.get('total_paid') or 0)
        derived_pending = max(0.0, invoice_amount - paid_amount)
        return {
                'invoiceNumber': invoice.get('invoice_no') or invoice.get('invoiceNumber') or '',
                'invoiceDate': _format_date(invoice.get('invoice_date') or invoice.get('invoiceDate')),
                'invoiceAmount': invoice_amount,
                'pendingAmount': derived_pending if pending_amount is None else float(pending_amount or 0),
        }


def _build_text_fallback(party_name: str, rows: list[dict], total_pending_amount: float) -> str:
        lines = [
                f"Dear {party_name},",
                "",
                "This is a gentle reminder regarding your pending invoice payment(s).",
                "",
        ]
        for row in rows:
                lines.extend([
                        f"Invoice Number: {row['invoiceNumber']}",
                        f"Invoice Date: {row['invoiceDate']}",
                        f"Invoice Amount: ₹{row['invoiceAmount']:.2f}",
                        f"Pending Amount: ₹{row['pendingAmount']:.2f}",
                        "",
                ])
        lines.extend([
                f"Total Pending Amount: ₹{total_pending_amount:.2f}",
                "",
                "This is a computer-generated payment reminder. If you have already made the payment, kindly ignore this email or contact us for confirmation.",
                "",
                "Thank you,",
                "Accounts Department",
        ])
        return "\n".join(lines)


def _build_html(party_name: str, rows: list[dict], total_pending_amount: float) -> str:
        invoice_rows = "".join(
                f"""
                    <tr>
                        <td class="invoice-table-cell">{row['invoiceNumber']}</td>
                        <td class="invoice-table-cell">{row['invoiceDate']}</td>
                        <td class="invoice-table-cell invoice-amount">₹{row['invoiceAmount']:,.2f}</td>
                        <td class="invoice-table-cell invoice-pending"><strong>₹{row['pendingAmount']:,.2f}</strong></td>
                    </tr>
                """
                for row in rows
        )

        return f"""
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style type="text/css">
        @media only screen and (max-width: 600px) {{
            .email-container {{
                padding: 10px !important;
            }}
            .email-card {{
                border-radius: 0 !important;
            }}
            .email-header {{
                padding: 14px 16px !important;
            }}
            .email-heading {{
                font-size: 18px !important;
                margin: 0 !important;
            }}
            .email-subheading {{
                font-size: 12px !important;
                margin: 4px 0 0 !important;
            }}
            .email-content {{
                padding: 14px !important;
            }}
            .email-text {{
                font-size: 13px !important;
            }}
            .email-strong {{
                font-size: 13px !important;
            }}
            .invoice-table {{
                font-size: 11px !important;
            }}
            .invoice-table-cell {{
                padding: 6px !important;
                font-size: 11px !important;
            }}
            .amount-box {{
                padding: 12px !important;
                font-size: 14px !important;
            }}
            .amount-value {{
                display: block !important;
                text-align: center !important;
                margin-top: 8px !important;
                font-size: 16px !important;
            }}
            .warning-note {{
                font-size: 12px !important;
                padding: 10px !important;
                line-height: 1.5 !important;
            }}
            .email-footer {{
                font-size: 11px !important;
                padding: 10px 16px !important;
            }}
            .table-wrapper {{
                overflow-x: auto !important;
                width: 100% !important;
                -webkit-overflow-scrolling: touch !important;
            }}
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f6f8;">
    <div class="email-container" style="width: 100%; background-color: #f4f6f8; padding: 20px 10px;">
        <div class="email-card" style="max-width: 700px; width: 100%; margin: 0 auto; background: #ffffff; border-radius: 10px; overflow: hidden; border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">

            <div class="email-header" style="background-color: #1f2937; color: #ffffff; padding: 20px 24px;">
                <h2 class="email-heading" style="margin: 0; font-size: 22px; color: #ffffff;">Payment Reminder</h2>
                <p class="email-subheading" style="margin: 6px 0 0 0; font-size: 14px; color: #e5e7eb;">Pending Invoice Payment Notification</p>
            </div>

            <div class="email-content" style="padding: 24px;">
                <p class="email-text" style="font-size: 15px; color: #111827; margin: 0 0 12px 0;">
                    Dear <span class="email-strong" style="font-weight: 600;">{party_name}</span>,
                </p>

                <p class="email-text" style="font-size: 15px; color: #374151; line-height: 1.6; margin: 0 0 16px 0;">
                    This is a gentle reminder regarding your pending invoice payment(s). Please find the invoice details below:
                </p>

                <div class="table-wrapper" style="overflow-x: auto; width: 100%; margin: 18px 0;">
                    <table class="invoice-table" style="width: 100%; border-collapse: collapse; font-size: 14px; table-layout: auto; word-break: break-word;">
                        <thead>
                            <tr style="background-color: #f3f4f6;">
                                <th style="border: 1px solid #d1d5db; padding: 10px; text-align: left; font-size: 13px; font-weight: 600; color: #111827;">Invoice No</th>
                                <th style="border: 1px solid #d1d5db; padding: 10px; text-align: left; font-size: 13px; font-weight: 600; color: #111827;">Date</th>
                                <th style="border: 1px solid #d1d5db; padding: 10px; text-align: right; font-size: 13px; font-weight: 600; color: #111827;">Amount</th>
                                <th style="border: 1px solid #d1d5db; padding: 10px; text-align: right; font-size: 13px; font-weight: 600; color: #111827;">Pending</th>
                            </tr>
                        </thead>
                        <tbody>
                            {invoice_rows}
                        </tbody>
                    </table>
                </div>

                <div class="amount-box" style="margin-top: 20px; background-color: #f9fafb; border: 1px solid #e5e7eb; padding: 16px; border-radius: 8px; text-align: left;">
                    <p style="margin: 0; font-size: 16px; color: #111827;">
                        <strong>Total Pending Amount:</strong>
                    </p>
                    <p class="amount-value" style="margin: 8px 0 0 0; font-size: 18px; color: #b91c1c; font-weight: bold; text-align: center;">
                        ₹{total_pending_amount:,.2f}
                    </p>
                </div>

                <p class="email-text" style="font-size: 15px; color: #374151; line-height: 1.6; margin: 20px 0;">
                    We request you to kindly process the pending payment at your earliest convenience.
                </p>

                <div class="warning-note" style="font-size: 14px; color: #92400e; line-height: 1.6; background-color: #fff7ed; border-left: 4px solid #f97316; padding: 12px; margin: 18px 0; word-break: break-word;">
                    <strong>Note:</strong> This is a computer-generated payment reminder. If you have already made the payment, kindly ignore this email or contact us for confirmation.
                </div>

                <p class="email-text" style="font-size: 15px; color: #374151; margin-top: 22px;">
                    Thank you,<br/>
                    <strong>Accounts Department</strong>
                </p>
            </div>

            <div class="email-footer" style="background-color: #f3f4f6; padding: 14px 24px; text-align: center; font-size: 12px; color: #6b7280;">
                This email was generated automatically by the Payment Reminder System.
            </div>

        </div>
    </div>
</body>
</html>
"""


def build_single_invoice_body(party_name: str, invoice: dict, pending_amount: float) -> str:
        row = _invoice_values(invoice, pending_amount=pending_amount)
        return _build_text_fallback(party_name, [row], row['pendingAmount'])


def build_multiple_invoice_body(party_name: str, invoices: list, total_pending: float) -> str:
        rows = [_invoice_values(inv) for inv in invoices]
        return _build_text_fallback(party_name, rows, total_pending)


def send_single_invoice_reminder(party_name: str, party_email: str, invoice: dict, pending_amount: float) -> None:
    subject = "Payment Reminder - Pending Invoice(s)"
    row = _invoice_values(invoice, pending_amount=pending_amount)
    html = _build_html(party_name, [row], row['pendingAmount'])
    text = build_single_invoice_body(party_name, invoice, pending_amount)
    _send_email(subject, party_email, html, text)


def send_multiple_invoice_reminder(party_name: str, party_email: str, invoices: list, total_pending: float) -> None:
    subject = "Payment Reminder - Pending Invoice(s)"
    rows = [_invoice_values(inv) for inv in invoices]
    html = _build_html(party_name, rows, total_pending)
    text = build_multiple_invoice_body(party_name, invoices, total_pending)
    _send_email(subject, party_email, html, text)