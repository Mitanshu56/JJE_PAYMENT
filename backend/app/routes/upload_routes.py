"""
File upload API routes
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Request
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
import tempfile
import os
import math
import re
from datetime import datetime, timezone
from pydantic import BaseModel
from bson import ObjectId
from app.core.database import get_db
from app.utils.excel_parser import InvoiceParser, BankStatementParser
from app.utils.pdf_statement_parser import PDFStatementParser
from app.controllers.bill_controller import BillController
from app.controllers.payment_controller import PaymentController
from app.routes.payment_routes import reconcile_bills_from_payments
import logging

logger = logging.getLogger(__name__)

PARTY_STOP_WORDS = {
    'NEFT',
    'RTGS',
    'IMPS',
    'INFLOW',
    'INFLOWS',
    'TRANSFER',
    'TRF',
    'SBIN',
    'HDFC',
    'ICIC',
    'AXIS',
    'KKBK',
    'PUNB',
    'UBIN',
    'UTR',
    'CHQ',
    'CHEQUE',
    'REF',
}

PARTY_PREFIX_STOP_WORDS = {
    'BY',
    'CLG',
    'NEFT',
    'RTGS',
    'IMPS',
    'INFLOW',
    'INFLOWS',
    'TRANSFER',
    'TRF',
}

PARTY_GENERIC_TOKENS = {
    'ELECTRICAL',
    'ELECTRICALS',
    'ENTERPRISE',
    'ENTERPRISES',
    'TRADERS',
    'TRADING',
    'SERVICES',
    'SERVICE',
    'PRIVATE',
    'LIMITED',
    'PVT',
    'LTD',
    'INDIA',
    'COMPANY',
    'CO',
}

MONTH_LABELS = {
    1: 'Jan',
    2: 'Feb',
    3: 'Mar',
    4: 'Apr',
    5: 'May',
    6: 'Jun',
    7: 'Jul',
    8: 'Aug',
    9: 'Sep',
    10: 'Oct',
    11: 'Nov',
    12: 'Dec',
}


def _month_number_from_key(month_key: str) -> int | None:
    try:
        return int(month_key.split('-')[1])
    except (AttributeError, IndexError, ValueError):
        return None


def _year_from_key(month_key: str) -> int | None:
    try:
        return int(month_key.split('-')[0])
    except (AttributeError, IndexError, ValueError):
        return None


def _fiscal_year_from_key(month_key: str) -> str | None:
    year = _year_from_key(month_key)
    month = _month_number_from_key(month_key)
    if year is None or month is None:
        return None

    start_year = year if month >= 4 else year - 1
    end_year = start_year + 1
    return f"FY-{start_year}-{end_year}"


def _normalize_fiscal_year_value(value: str | None) -> str | None:
    raw = str(value or '').strip().upper().replace(' ', '')
    if not raw:
        return None

    raw = raw.replace('FYFY-', 'FY-')
    if not raw.startswith('FY'):
        raw = f'FY-{raw}'

    numbers = re.findall(r'\d+', raw)
    if len(numbers) >= 2:
        start_year = int(numbers[0])
        end_year_raw = int(numbers[1])
        end_year = end_year_raw if end_year_raw >= 1000 else ((start_year // 100) * 100) + end_year_raw
        return f'FY-{start_year}-{end_year}'

    return raw.replace('FY', 'FY-').replace('FY--', 'FY-')


def _fiscal_year_label(fiscal_year: str) -> str:
    normalized = _normalize_fiscal_year_value(fiscal_year) or str(fiscal_year or '').strip()
    if normalized.startswith('FY-'):
        return normalized.replace('FY-', 'FY ', 1)
    if normalized.startswith('FY '):
        return normalized
    return f"FY {normalized}"


def _group_statement_rows(rows):
    months = {}

    for row in rows:
        key = row.get('month_key') or ''
        label = row.get('month_label') or key
        if not key:
            continue

        if key not in months:
            row_fiscal_year = _normalize_fiscal_year_value(row.get('fiscal_year')) or _fiscal_year_from_key(key)
            months[key] = {
                'month_key': key,
                'month_label': label,
                'fiscal_year': row_fiscal_year,
                'total_deposit': 0.0,
                'count': 0,
                'rows': [],
            }

        entry = {
            'id': str(row.get('_id')) if row.get('_id') else None,
            'value_date': row.get('value_date_display') or (row.get('value_date').strftime('%d/%m/%Y') if row.get('value_date') else ''),
            'narration': row.get('narration') or '',
            'reference': row.get('reference') or '',
            'deposit': float(row.get('deposit') or 0.0),
            'source_file': row.get('source_file') or '',
        }
        months[key]['rows'].append(entry)
        months[key]['total_deposit'] += entry['deposit']
        months[key]['count'] += 1

    grouped = list(months.values())
    grouped.sort(key=lambda m: m['month_key'], reverse=True)
    return grouped


def _normalize_party_text(value: str) -> str:
    text = re.sub(r'[^A-Z0-9 ]+', ' ', (value or '').upper())
    return re.sub(r'\s+', ' ', text).strip()


def _tokenize_party_text(value: str) -> list[str]:
    normalized = _normalize_party_text(value)
    tokens = [token for token in normalized.split(' ') if len(token) > 1]
    return [token for token in tokens if token not in PARTY_STOP_WORDS and not token.isdigit()]


def _trim_candidate_tokens(tokens: list[str]) -> list[str]:
    cleaned = [token for token in tokens if token]

    while cleaned and cleaned[0] in PARTY_PREFIX_STOP_WORDS:
        cleaned = cleaned[1:]

    stop_prefixes = ('SBIN', 'HDFC', 'ICIC', 'AXIS', 'KKBK', 'PUNB', 'UBIN')
    trimmed = []
    for token in cleaned:
        if token in PARTY_STOP_WORDS:
            break
        if token.startswith(stop_prefixes):
            break
        if token.isdigit():
            break
        if re.fullmatch(r'[A-Z]{4,}\d{3,}[A-Z\d]*', token):
            break
        trimmed.append(token)

    return trimmed


def _extract_party_from_narration(narration: str) -> str:
    raw = _normalize_party_text(narration)
    if not raw:
        return ''

    patterns = [
        r'\bBY[-\s]+(.+)',
        r'\bNEFT[-_\s]+(.+)',
        r'\bRTGS[-_\s]+(.+)',
        r'\bIMPS[-_\s]+(.+)',
    ]

    candidate = raw
    for pattern in patterns:
        matched = re.search(pattern, raw)
        if matched:
            candidate = matched.group(1).strip()
            break

    tokens = _trim_candidate_tokens(candidate.split(' '))
    if not tokens:
        fallback_tokens = _trim_candidate_tokens(raw.split(' '))
        tokens = fallback_tokens[:4]

    return ' '.join(tokens).strip()


def _build_party_lookup(bills: list[dict]) -> dict:
    lookup = {}
    for bill in bills:
        party_name = str(bill.get('party_name') or '').strip()
        if not party_name:
            continue

        party_norm = _normalize_party_text(party_name)
        if not party_norm:
            continue

        entry = lookup.get(party_norm)
        if not entry:
            entry = {
                'party_name': party_name,
                'party_norm': party_norm,
                'party_tokens': set(_tokenize_party_text(party_name)),
                'bills': [],
            }
            lookup[party_norm] = entry

        entry['bills'].append(bill)

    return lookup


def _party_match_score(extracted_name: str, candidate_norm: str, candidate_tokens: set[str]) -> float:
    extracted_norm = _normalize_party_text(extracted_name)
    if not extracted_norm:
        return 0.0

    # Preserve strong exact-name match (case-insensitive by normalization).
    if extracted_norm == candidate_norm:
        return 1.0

    ext_tokens = set(_tokenize_party_text(extracted_name))
    if not ext_tokens or not candidate_tokens:
        return 0.0

    ext_core_tokens = {token for token in ext_tokens if token not in PARTY_GENERIC_TOKENS}
    cand_core_tokens = {token for token in candidate_tokens if token not in PARTY_GENERIC_TOKENS}

    # If extracted NEFT name has only generic words, avoid forced mapping.
    if not ext_core_tokens:
        return 0.0

    # Phrase containment should not map on generic single words like ELECTRICALS.
    if (extracted_norm in candidate_norm or candidate_norm in extracted_norm) and len(ext_core_tokens) >= 2:
        return 0.92

    core_overlap = len(ext_core_tokens & cand_core_tokens)
    if core_overlap == 0:
        return 0.0

    overlap = len(ext_tokens & candidate_tokens)
    if overlap == 0:
        return 0.0

    ratio_ext = core_overlap / max(len(ext_core_tokens), 1)
    ratio_cand = core_overlap / max(len(cand_core_tokens), 1)
    return min(0.9, (ratio_ext * 0.75) + (ratio_cand * 0.25))


def _serialize_date(value) -> str:
    if not value:
        return ''
    if hasattr(value, 'strftime'):
        return value.strftime('%d/%m/%Y')
    return str(value)


def _serialize_datetime(value) -> str:
    if not value:
        return ''
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return str(value)

router = APIRouter(prefix="/api/upload", tags=["Upload"])


class StatementNeftConfirmRequest(BaseModel):
    statement_entry_id: str
    confirmed: bool = True
    invoice_no: str | None = None


@router.post("/invoices")
async def upload_invoices(
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
    request: Request = None,
):
    """
    Upload invoice Excel file for extraction and storage.
    
    Supports multiple invoices per sheet or multiple sheets.
    """
    try:
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) allowed")
        
        # Determine fiscal year from request state (middleware)
        fiscal = getattr(request.state, 'fiscal_year', None) if request is not None else None

        # Save temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            contents = await file.read()
            temp_file.write(contents)
            temp_path = temp_file.name
        
        try:
            previous_upload = await db['upload_logs'].find_one(
                {'file_type': 'invoice', **({'fiscal_year': fiscal} if fiscal else {})},
                sort=[('created_at', -1)]
            )

            upload_batch_id = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')

            # Parse invoices
            parser = InvoiceParser(temp_path)
            invoices = parser.parse()
            
            if not invoices:
                raise HTTPException(status_code=400, detail="No valid invoices found in file")

            bill_controller = BillController(db)

            def _norm_date(value):
                if value is None:
                    return ''
                if hasattr(value, 'strftime'):
                    return value.strftime('%Y-%m-%d')
                value_str = str(value).strip()
                return value_str[:10] if value_str else ''

            def _norm_num(value):
                try:
                    return round(float(value or 0.0), 2)
                except Exception:
                    return 0.0

            # Build snapshot to report accurate log stats for refreshed uploads (scoped to fiscal if present).
            existing_filter = {'fiscal_year': fiscal} if fiscal else {}
            existing_bills = await db['bills'].find(
                existing_filter,
                {
                    'invoice_key': 1,
                    'invoice_date': 1,
                    'net_amount': 1,
                    'cgst': 1,
                    'sgst': 1,
                    'grand_total': 1,
                }
            ).to_list(length=100000)

            existing_by_key = {
                str(doc.get('invoice_key') or ''): doc
                for doc in existing_bills
                if doc.get('invoice_key')
            }

            log_new_records = 0
            log_updated_records = 0
            log_unchanged_records = 0
            for invoice in invoices:
                invoice_key = bill_controller._build_invoice_key(invoice)
                existing = existing_by_key.get(invoice_key)
                if not existing:
                    log_new_records += 1
                    continue

                existing_signature = (
                    _norm_date(existing.get('invoice_date')),
                    _norm_num(existing.get('net_amount')),
                    _norm_num(existing.get('cgst')),
                    _norm_num(existing.get('sgst')),
                    _norm_num(existing.get('grand_total')),
                )
                incoming_signature = (
                    _norm_date(invoice.get('invoice_date')),
                    _norm_num(invoice.get('net_amount')),
                    _norm_num(invoice.get('cgst')),
                    _norm_num(invoice.get('sgst')),
                    _norm_num(invoice.get('grand_total')),
                )

                if incoming_signature == existing_signature:
                    log_unchanged_records += 1
                else:
                    log_updated_records += 1

            # Always treat invoice upload as the latest source of truth.
            # Clear prior bills and stale payment-to-invoice links before re-import (scoped to fiscal).
            await db['bills'].delete_many({'fiscal_year': fiscal} if fiscal else {})
            await db['payments'].update_many(
                ({'fiscal_year': fiscal} if fiscal else {}),
                {
                    '$set': {
                        'matched_invoice_nos': [],
                    }
                }
            )
            
            # Store in database (pass fiscal through)
            import_stats = await bill_controller.create_bills_bulk(invoices, upload_batch_id=upload_batch_id, fiscal_year=fiscal)

            # Rebuild bill totals/status from existing payments and saved allocations (scoped to fiscal).
            rematched_bills = 0
            reconcile_summary = await reconcile_bills_from_payments(db, fiscal_year=fiscal)
            rematched_bills = int(reconcile_summary.get('allocation_rows_applied') or 0)

            total_bills_after_upload = await db['bills'].count_documents({'fiscal_year': fiscal} if fiscal else {})
            upload_time = datetime.now(timezone.utc)
            
            # Log upload with accurate statistics
            await db['upload_logs'].insert_one({
                'file_name': file.filename,
                'file_type': 'invoice',
                'total_in_file': import_stats['total_in_file'],
                'new_records': log_new_records,
                'updated_records': log_updated_records,
                'unchanged_records': log_unchanged_records,
                'skipped_records': import_stats['skipped_records'],
                'total_processed': log_new_records + log_updated_records,
                'total_bills_after_upload': total_bills_after_upload,
                'upload_batch_id': upload_batch_id,
                'created_at': upload_time,
            })

            previous_upload_at = previous_upload.get('created_at') if previous_upload else None
            
            return {
                'status': 'success',
                'message': (
                    f"Upload complete: {log_new_records} new, "
                    f"{log_updated_records} updated, "
                    f"{log_unchanged_records} unchanged, "
                    f"{rematched_bills} rematched"
                ),
                'invoices_count': log_new_records,
                'import_summary': {
                    'total_in_file': import_stats['total_in_file'],
                    'new_records': log_new_records,
                    'updated_records': log_updated_records,
                    'unchanged_records': log_unchanged_records,
                    'skipped_records': import_stats['skipped_records'],
                    'rematched_bills': rematched_bills,
                    'total_bills_after_upload': total_bills_after_upload,
                    'upload_batch_id': upload_batch_id,
                    'current_upload_at': upload_time,
                    'previous_upload_at': previous_upload_at,
                },
                'invoices': invoices[:5]  # Return first 5 for preview
            }
        
        finally:
            # Clean up temp file. On Windows, file release can lag briefly.
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError as cleanup_error:
                    logger.warning(f"Could not delete temp file {temp_path}: {cleanup_error}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ Error uploading invoices: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.post("/bank-statements")
async def upload_bank_statement(
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
    request: Request = None,
):
    """
    Upload bank statement Excel file for payment extraction and storage.
    """
    try:
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) allowed")

        fiscal = getattr(request.state, 'fiscal_year', None) if request is not None else None
        
        # Save temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            contents = await file.read()
            temp_file.write(contents)
            temp_path = temp_file.name
        
        try:
            # Parse payments
            parser = BankStatementParser(temp_path)
            payments = parser.parse()
            
            if not payments:
                raise HTTPException(status_code=400, detail="No valid payments found in file")
            
            # Store in database (pass fiscal through)
            payment_controller = PaymentController(db)
            inserted_count = await payment_controller.create_payments_bulk(payments, fiscal_year=fiscal)
            
            # Log upload
            await db['upload_logs'].insert_one({
                'file_name': file.filename,
                'file_type': 'bank_statement',
                'records_count': inserted_count,
                'fiscal_year': fiscal,
                'created_at': datetime.utcnow()
            })
            
            return {
                'status': 'success',
                'message': f'Successfully imported {inserted_count} payments',
                'payments_count': inserted_count,
                'payments': payments[:5]  # Return first 5 for preview
            }
        
        finally:
            # Clean up temp file. On Windows, file release can lag briefly.
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError as cleanup_error:
                    logger.warning(f"Could not delete temp file {temp_path}: {cleanup_error}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ Error uploading bank statement: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.get("/history")
async def get_upload_history(limit: int = 50, db: AsyncIOMotorDatabase = Depends(get_db), request: Request = None):
    """Get history of uploaded files (scoped to fiscal if selected)"""
    try:
        fiscal = getattr(request.state, 'fiscal_year', None) if request is not None else None
        query = {'fiscal_year': fiscal} if fiscal else {}
        logs = await db['upload_logs'].find(query)\
            .sort('created_at', -1)\
            .limit(limit)\
            .to_list(length=limit)
        
        # Convert ObjectId to string for JSON serialization
        for log in logs:
            if '_id' in log:
                log['_id'] = str(log['_id'])
        
        return {
            'status': 'success',
            'upload_history': logs
        }
    except Exception as e:
        logger.error(f"✗ Error retrieving upload history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invoices/last")
async def get_last_invoice_upload(db: AsyncIOMotorDatabase = Depends(get_db), request: Request = None):
    """Get last invoice upload timestamp and summary stats."""
    try:
        fiscal = getattr(request.state, 'fiscal_year', None) if request is not None else None
        last_log = await db['upload_logs'].find_one(
            {'file_type': 'invoice', **({'fiscal_year': fiscal} if fiscal else {})},
            sort=[('created_at', -1)]
        )

        if not last_log:
            return {
                'status': 'success',
                'last_upload': None,
            }

        return {
            'status': 'success',
            'last_upload': {
                'file_name': last_log.get('file_name'),
                'uploaded_at': last_log.get('created_at'),
                'new_records': int(last_log.get('new_records', last_log.get('records_count', 0)) or 0),
                'updated_records': int(last_log.get('updated_records', 0) or 0),
                'unchanged_records': int(last_log.get('unchanged_records', 0) or 0),
                'skipped_records': int(last_log.get('skipped_records', 0) or 0),
                'total_in_file': int(last_log.get('total_in_file', 0) or 0),
                'total_bills_after_upload': int(last_log.get('total_bills_after_upload', 0) or 0),
            }
        }
    except Exception as e:
        logger.error(f"✗ Error retrieving last invoice upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/statements/pdf")
async def upload_statement_pdf(file: UploadFile = File(...), db: AsyncIOMotorDatabase = Depends(get_db), request: Request = None):
    """Upload bank statement PDF and extract credited/deposit rows only."""
    try:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files (.pdf) allowed")

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            contents = await file.read()
            temp_file.write(contents)
            temp_path = temp_file.name

        try:
            parser = PDFStatementParser(temp_path)
            rows = parser.parse()

            if not rows:
                raise HTTPException(status_code=400, detail="No credited/deposit rows found in PDF")

            upload_batch_id = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
            now = datetime.utcnow()
            fiscal = _normalize_fiscal_year_value(getattr(request.state, 'fiscal_year', None) if request is not None else None)
            docs = []
            for row in rows:
                docs.append({
                    'upload_batch_id': upload_batch_id,
                    'fiscal_year': fiscal,
                    'source_file': file.filename,
                    'value_date': row['value_date'],
                    'value_date_display': row['value_date_display'],
                    'narration': row.get('narration') or '',
                    'reference': row.get('reference') or '',
                    'deposit': float(row.get('deposit') or 0.0),
                    'month_key': row['month_key'],
                    'month_label': row['month_label'],
                    'created_at': now,
                })

            result = await db['statement_entries'].insert_many(docs)
            inserted_count = len(result.inserted_ids)

            await db['upload_logs'].insert_one({
                'file_name': file.filename,
                'file_type': 'statement_pdf',
                'records_count': inserted_count,
                'upload_batch_id': upload_batch_id,
                'fiscal_year': fiscal,
                'created_at': now,
            })

            preview = []
            for row in docs[:5]:
                preview.append({
                    'value_date': row['value_date_display'],
                    'narration': row['narration'],
                    'reference': row['reference'],
                    'deposit': row['deposit'],
                })

            return {
                'status': 'success',
                'message': f'Successfully extracted {inserted_count} credited/deposit rows',
                'rows_count': inserted_count,
                'upload_batch_id': upload_batch_id,
                'rows': preview,
            }
        finally:
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError as cleanup_error:
                    logger.warning(f"Could not delete temp file {temp_path}: {cleanup_error}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ Error uploading statement PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing statement PDF: {str(e)}")


@router.get("/statements/monthly")
async def get_statement_rows_monthly(
    fiscal_year: str | None = None,
    year: int | None = None,
    month: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(4, ge=1, le=24),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get extracted statement rows grouped month-wise for UI display with FY/year/month filters."""
    try:
        rows = await db['statement_entries'].find().sort('value_date', -1).to_list(length=None)

        grouped = _group_statement_rows(rows)
        selected_fiscal_year = _normalize_fiscal_year_value(fiscal_year)

        fiscal_years = []
        years = []
        months_available = []
        seen_fy = set()
        seen_years = set()
        seen_months = set()

        for item in grouped:
            fy = _normalize_fiscal_year_value(item.get('fiscal_year') or _fiscal_year_from_key(item.get('month_key') or ''))
            if fy and fy not in seen_fy:
                seen_fy.add(fy)
                fiscal_years.append({
                    'value': fy,
                    'label': _fiscal_year_label(fy),
                })

            year_key = _year_from_key(item['month_key'])
            if year_key is not None and year_key not in seen_years:
                seen_years.add(year_key)
                years.append(year_key)

            month_key = _month_number_from_key(item['month_key'])
            if month_key is not None and month_key not in seen_months:
                seen_months.add(month_key)
                months_available.append({
                    'value': month_key,
                    'label': MONTH_LABELS.get(month_key, str(month_key)),
                })

        if selected_fiscal_year is None and year is None and month is None and fiscal_years:
            selected_fiscal_year = fiscal_years[0]['value']
        filtered = grouped

        if selected_fiscal_year:
            filtered = [
                item
                for item in filtered
                if _normalize_fiscal_year_value(item.get('fiscal_year') or _fiscal_year_from_key(item.get('month_key') or '')) == selected_fiscal_year
            ]

        if year is not None:
            filtered = [item for item in filtered if _year_from_key(item['month_key']) == year]

        if month is not None:
            filtered = [item for item in filtered if _month_number_from_key(item['month_key']) == month]

        total_months = len(filtered)
        total_pages = math.ceil(total_months / page_size) if total_months else 0
        current_page = min(page, total_pages) if total_pages else 1
        start = (current_page - 1) * page_size
        end = start + page_size
        paged_months = filtered[start:end]

        return {
            'status': 'success',
            'months': paged_months,
            'total_rows': sum(m['count'] for m in filtered),
            'total_months': total_months,
            'pagination': {
                'page': current_page,
                'page_size': page_size,
                'total_pages': total_pages,
                'has_previous': current_page > 1,
                'has_next': total_pages > 0 and current_page < total_pages,
            },
            'filters': {
                'fiscal_year': selected_fiscal_year,
                'year': year,
                'month': month,
            },
            'available_filters': {
                'fiscal_years': fiscal_years,
                'years': years,
                'months': months_available,
            },
        }
    except Exception as e:
        logger.error(f"✗ Error retrieving monthly statement rows: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/statements/match')
async def get_statement_match(
    fiscal_year: str | None = None,
    neft_only: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Extract party names from statement narration and map them to invoice parties."""
    try:
        statement_rows = await db['statement_entries'].find({}).sort('value_date', -1).to_list(length=None)
        selected_fiscal_year = _normalize_fiscal_year_value(fiscal_year)
        if selected_fiscal_year:
            statement_rows = [
                row for row in statement_rows
                if _normalize_fiscal_year_value(row.get('fiscal_year') or _fiscal_year_from_key(row.get('month_key') or '')) == selected_fiscal_year
            ]

        if neft_only:
            statement_rows = [
                row for row in statement_rows
                if 'NEFT' in _normalize_party_text(str(row.get('narration') or ''))
            ]

        bills = await db['bills'].find({}).to_list(length=None)
        party_lookup = _build_party_lookup(bills)
        parties = list(party_lookup.values())

        total_rows = len(statement_rows)
        start = (page - 1) * page_size
        end = start + page_size
        paged_rows = statement_rows[start:end]

        matched_count = 0
        results = []
        extracted_party_set = set()

        for row in paged_rows:
            narration = str(row.get('narration') or '')
            extracted_name = _extract_party_from_narration(narration)
            if extracted_name:
                extracted_party_set.add(extracted_name)

            best_match = None
            best_score = 0.0
            if extracted_name:
                for candidate in parties:
                    score = _party_match_score(
                        extracted_name,
                        candidate['party_norm'],
                        candidate['party_tokens'],
                    )
                    if score > best_score:
                        best_score = score
                        best_match = candidate

            is_matched = best_match is not None and best_score >= 0.70
            if is_matched:
                matched_count += 1

            invoices = []
            party_payment_total = 0.0
            party_pending_total = 0.0
            party_invoice_grand_total = 0.0
            if is_matched:
                sorted_bills = sorted(
                    best_match['bills'],
                    key=lambda bill: (bill.get('invoice_date') or datetime.min),
                )

                for bill in sorted_bills:
                    grand_total = float(bill.get('grand_total') or 0.0)
                    paid_amount = float(bill.get('paid_amount') or 0.0)
                    remaining_amount = float(bill.get('remaining_amount') or 0.0)
                    party_invoice_grand_total += grand_total
                    party_payment_total += paid_amount
                    party_pending_total += remaining_amount
                    invoices.append(
                        {
                            'id': str(bill.get('_id')),
                            'invoice_no': bill.get('invoice_no') or '',
                            'invoice_date': _serialize_date(bill.get('invoice_date')),
                            'grand_total': grand_total,
                            'paid_amount': paid_amount,
                            'remaining_amount': remaining_amount,
                            'status': bill.get('status') or 'UNPAID',
                            'matched_payment_ids': bill.get('matched_payment_ids') or [],
                        }
                    )

            results.append(
                {
                    'statement_entry': {
                        'id': str(row.get('_id')),
                        'value_date': row.get('value_date_display') or _serialize_date(row.get('value_date')),
                        'deposit': float(row.get('deposit') or 0.0),
                        'narration': narration,
                        'reference': row.get('reference') or '',
                        'month_key': row.get('month_key') or '',
                        'source_file': row.get('source_file') or '',
                        'neft_confirmed': bool(row.get('neft_confirmed') or False),
                        'confirmed_payment_id': row.get('confirmed_payment_id') or '',
                        'confirmed_invoice_no': row.get('confirmed_invoice_no') or '',
                        'created_at': _serialize_datetime(row.get('created_at')),
                    },
                    'extracted_party_name': extracted_name,
                    'matched': is_matched,
                    'match_confidence': round(best_score, 2) if is_matched else 0.0,
                    'matched_party': {
                        'party_name': best_match['party_name'],
                        'invoice_count': len(invoices),
                        'total_billed': round(party_invoice_grand_total, 2),
                        'total_paid': round(party_payment_total, 2),
                        'total_pending': round(party_pending_total, 2),
                        'invoice_grand_total': round(party_invoice_grand_total, 2),
                        'invoice_paid_total': round(party_payment_total, 2),
                        'invoice_pending_total': round(party_pending_total, 2),
                    } if is_matched else None,
                    'invoices': invoices,
                }
            )

        return {
            'status': 'success',
            'rows': results,
            'available_parties': sorted(extracted_party_set),
            'summary': {
                'total_rows': total_rows,
                'page_rows': len(results),
                'matched_rows': matched_count,
                'unmatched_rows': len(results) - matched_count,
            },
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_pages': math.ceil(total_rows / page_size) if total_rows else 0,
            },
        }
    except Exception as e:
        logger.error(f"✗ Error retrieving statement match rows: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/statements/neft-confirm')
async def confirm_statement_neft_payment(
    payload: StatementNeftConfirmRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Confirm/unconfirm a NEFT statement row as an actual payment and update bill totals."""
    try:
        try:
            entry_id = ObjectId(str(payload.statement_entry_id))
        except Exception:
            raise HTTPException(status_code=400, detail='Invalid statement entry id')

        entry = await db['statement_entries'].find_one({'_id': entry_id})
        if not entry:
            raise HTTPException(status_code=404, detail='Statement entry not found')

        narration = str(entry.get('narration') or '')
        if 'NEFT' not in _normalize_party_text(narration):
            raise HTTPException(status_code=400, detail='Selected row is not a NEFT entry')

        bill_controller = BillController(db)
        payment_controller = PaymentController(db)

        if payload.confirmed:
            if entry.get('neft_confirmed') and entry.get('confirmed_payment_id'):
                return {
                    'status': 'success',
                    'message': 'NEFT entry already confirmed',
                    'confirmed': True,
                    'payment_id': entry.get('confirmed_payment_id'),
                }

            invoice_no = str(payload.invoice_no or '').strip()
            if not invoice_no:
                raise HTTPException(status_code=400, detail='Invoice number is required to confirm payment')

            extracted_name = _extract_party_from_narration(narration)
            if not extracted_name:
                raise HTTPException(status_code=400, detail='Could not extract party from NEFT narration')

            bills = await db['bills'].find({}).to_list(length=None)
            party_lookup = _build_party_lookup(bills)
            parties = list(party_lookup.values())

            best_match = None
            best_score = 0.0
            for candidate in parties:
                score = _party_match_score(
                    extracted_name,
                    candidate['party_norm'],
                    candidate['party_tokens'],
                )
                if score > best_score:
                    best_score = score
                    best_match = candidate

            if not best_match or best_score < 0.70:
                raise HTTPException(status_code=400, detail='Could not confidently map NEFT party to invoice party')

            amount = float(entry.get('deposit') or 0.0)
            if amount <= 0:
                raise HTTPException(status_code=400, detail='NEFT deposit amount must be greater than zero')

            payment_id = f"NEFT-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[:-3]}"
            matched_party_name = best_match['party_name']

            invoice_doc = await db['bills'].find_one({'invoice_no': invoice_no, 'party_name': matched_party_name})
            if not invoice_doc:
                raise HTTPException(status_code=400, detail='Selected invoice does not belong to matched NEFT party')

            allocation = await bill_controller.apply_payment_to_bills(
                amount=amount,
                party_name=matched_party_name,
                invoice_nos=[invoice_no],
                payment_id=payment_id,
            )

            payment_doc = {
                'payment_id': payment_id,
                'party_name': matched_party_name,
                'amount': amount,
                'actual_received_amount': amount,
                'payment_mode': 'NEFT',
                'payment_date': entry.get('value_date') or datetime.utcnow(),
                'reference': f"{((entry.get('reference') or '').strip() or narration)} | INV:{invoice_no}",
                'notes': f"Statement NEFT confirmation for entry {payload.statement_entry_id} against invoice {invoice_no}",
                'matched_invoice_nos': [a.get('invoice_no') for a in (allocation.get('allocations') or []) if a.get('invoice_no')],
                'allocations': allocation.get('allocations') or [],
                'applied_amount': float(allocation.get('applied_amount') or 0.0),
                'unapplied_amount': float(allocation.get('remaining_amount') or 0.0),
            }
            await payment_controller.create_payment(payment_doc)

            await db['statement_entries'].update_one(
                {'_id': entry_id},
                {
                    '$set': {
                        'neft_confirmed': True,
                        'confirmed_payment_id': payment_id,
                        'confirmed_party_name': matched_party_name,
                        'confirmed_invoice_no': invoice_no,
                        'confirmed_at': datetime.utcnow(),
                    }
                },
            )

            return {
                'status': 'success',
                'message': 'NEFT payment confirmed and applied',
                'confirmed': True,
                'payment_id': payment_id,
                'party_name': matched_party_name,
                'invoice_no': invoice_no,
                'allocation': allocation,
            }

        payment_id = str(entry.get('confirmed_payment_id') or '').strip()
        if payment_id:
            payment = await payment_controller.get_payment(payment_id)
            if payment:
                allocations = payment.get('allocations') or []
                if not allocations:
                    allocations = [
                        {
                            'invoice_no': inv,
                            'allocated_amount': 0.0,
                        }
                        for inv in (payment.get('matched_invoice_nos') or [])
                    ]

                await bill_controller.revert_payment_from_bills(
                    payment_id=payment_id,
                    allocations=allocations,
                    party_name=payment.get('party_name'),
                )
                await payment_controller.delete_payment(payment_id)

        await db['statement_entries'].update_one(
            {'_id': entry_id},
            {
                '$set': {'neft_confirmed': False},
                '$unset': {
                    'confirmed_payment_id': '',
                    'confirmed_party_name': '',
                    'confirmed_invoice_no': '',
                    'confirmed_at': '',
                },
            },
        )

        return {
            'status': 'success',
            'message': 'NEFT confirmation removed',
            'confirmed': False,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ Error confirming NEFT payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/statements/{statement_entry_id}')
async def delete_statement_entry(
    statement_entry_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Delete one statement row by id. If NEFT was confirmed, rollback linked payment first."""
    try:
        try:
            entry_id = ObjectId(str(statement_entry_id))
        except Exception:
            raise HTTPException(status_code=400, detail='Invalid statement entry id')

        entry = await db['statement_entries'].find_one({'_id': entry_id})
        if not entry:
            raise HTTPException(status_code=404, detail='Statement entry not found')

        payment_id = str(entry.get('confirmed_payment_id') or '').strip()
        if payment_id:
            payment_controller = PaymentController(db)
            bill_controller = BillController(db)
            payment = await payment_controller.get_payment(payment_id)
            if payment:
                allocations = payment.get('allocations') or []
                if not allocations:
                    allocations = [
                        {
                            'invoice_no': inv,
                            'allocated_amount': 0.0,
                        }
                        for inv in (payment.get('matched_invoice_nos') or [])
                    ]

                await bill_controller.revert_payment_from_bills(
                    payment_id=payment_id,
                    allocations=allocations,
                    party_name=payment.get('party_name'),
                )
                await payment_controller.delete_payment(payment_id)

        delete_result = await db['statement_entries'].delete_one({'_id': entry_id})
        if delete_result.deleted_count == 0:
            raise HTTPException(status_code=404, detail='Statement entry not found')

        return {
            'status': 'success',
            'message': 'Statement entry removed successfully',
            'deleted_id': statement_entry_id,
            'payment_rollback_applied': bool(payment_id),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ Error deleting statement entry: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/statements/month/{month_key}')
async def delete_statement_month(
    month_key: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Delete all statement rows for one month key (YYYY-MM)."""
    try:
        if not re.fullmatch(r'\d{4}-\d{2}', str(month_key or '').strip()):
            raise HTTPException(status_code=400, detail='Invalid month key. Expected format: YYYY-MM')

        entries = await db['statement_entries'].find({'month_key': month_key}).to_list(length=None)
        if not entries:
            raise HTTPException(status_code=404, detail='No statement rows found for selected month')

        payment_controller = PaymentController(db)
        bill_controller = BillController(db)

        payment_ids = {
            str(entry.get('confirmed_payment_id') or '').strip()
            for entry in entries
            if str(entry.get('confirmed_payment_id') or '').strip()
        }

        rolled_back_payments = 0
        for payment_id in payment_ids:
            payment = await payment_controller.get_payment(payment_id)
            if not payment:
                continue

            allocations = payment.get('allocations') or []
            if not allocations:
                allocations = [
                    {
                        'invoice_no': inv,
                        'allocated_amount': 0.0,
                    }
                    for inv in (payment.get('matched_invoice_nos') or [])
                ]

            await bill_controller.revert_payment_from_bills(
                payment_id=payment_id,
                allocations=allocations,
                party_name=payment.get('party_name'),
            )
            await payment_controller.delete_payment(payment_id)
            rolled_back_payments += 1

        delete_result = await db['statement_entries'].delete_many({'month_key': month_key})

        return {
            'status': 'success',
            'message': f'Statement month {month_key} removed successfully',
            'month_key': month_key,
            'rows_deleted': int(delete_result.deleted_count or 0),
            'payments_rolled_back': rolled_back_payments,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ Error deleting statement month {month_key}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
