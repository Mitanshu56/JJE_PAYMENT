"""
File upload API routes
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
import tempfile
import os
import math
from datetime import datetime
from app.core.database import get_db
from app.utils.excel_parser import InvoiceParser, BankStatementParser
from app.utils.pdf_statement_parser import PDFStatementParser
from app.controllers.bill_controller import BillController
from app.controllers.payment_controller import PaymentController
import logging

logger = logging.getLogger(__name__)

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
    end_year = (start_year + 1) % 100
    return f"{start_year}-{end_year:02d}"


def _fiscal_year_label(fiscal_year: str) -> str:
    return f"FY {fiscal_year}"


def _group_statement_rows(rows):
    months = {}

    for row in rows:
        key = row.get('month_key') or ''
        label = row.get('month_label') or key
        if not key:
            continue

        if key not in months:
            months[key] = {
                'month_key': key,
                'month_label': label,
                'fiscal_year': _fiscal_year_from_key(key),
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

router = APIRouter(prefix="/api/upload", tags=["Upload"])


@router.post("/invoices")
async def upload_invoices(file: UploadFile = File(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Upload invoice Excel file for extraction and storage.
    
    Supports multiple invoices per sheet or multiple sheets.
    """
    try:
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) allowed")
        
        # Save temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            contents = await file.read()
            temp_file.write(contents)
            temp_path = temp_file.name
        
        try:
            previous_upload = await db['upload_logs'].find_one(
                {'file_type': 'invoice'},
                sort=[('created_at', -1)]
            )

            upload_batch_id = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')

            # Parse invoices
            parser = InvoiceParser(temp_path)
            invoices = parser.parse()
            
            if not invoices:
                raise HTTPException(status_code=400, detail="No valid invoices found in file")
            
            # Store in database
            bill_controller = BillController(db)
            import_stats = await bill_controller.create_bills_bulk(invoices, upload_batch_id=upload_batch_id)
            total_bills_after_upload = await db['bills'].count_documents({})
            upload_time = datetime.utcnow()
            
            # Log upload with accurate statistics
            await db['upload_logs'].insert_one({
                'file_name': file.filename,
                'file_type': 'invoice',
                'total_in_file': import_stats['total_in_file'],
                'new_records': import_stats['new_records'],
                'updated_records': import_stats['updated_records'],
                'unchanged_records': import_stats['unchanged_records'],
                'skipped_records': import_stats['skipped_records'],
                'total_processed': import_stats['new_records'] + import_stats['updated_records'],
                'total_bills_after_upload': total_bills_after_upload,
                'upload_batch_id': upload_batch_id,
                'created_at': upload_time,
            })

            previous_upload_at = previous_upload.get('created_at') if previous_upload else None
            
            return {
                'status': 'success',
                'message': (
                    f"Upload complete: {import_stats['new_records']} new, "
                    f"{import_stats['updated_records']} updated, "
                    f"{import_stats['unchanged_records']} unchanged"
                ),
                'invoices_count': import_stats['new_records'],
                'import_summary': {
                    'total_in_file': import_stats['total_in_file'],
                    'new_records': import_stats['new_records'],
                    'updated_records': import_stats['updated_records'],
                    'unchanged_records': import_stats['unchanged_records'],
                    'skipped_records': import_stats['skipped_records'],
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
async def upload_bank_statement(file: UploadFile = File(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Upload bank statement Excel file for payment extraction and storage.
    """
    try:
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) allowed")
        
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
            
            # Store in database
            payment_controller = PaymentController(db)
            inserted_count = await payment_controller.create_payments_bulk(payments)
            
            # Log upload
            await db['upload_logs'].insert_one({
                'file_name': file.filename,
                'file_type': 'bank_statement',
                'records_count': inserted_count,
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
async def get_upload_history(limit: int = 50, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get history of uploaded files"""
    try:
        logs = await db['upload_logs'].find()\
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
async def get_last_invoice_upload(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get last invoice upload timestamp and summary stats."""
    try:
        last_log = await db['upload_logs'].find_one(
            {'file_type': 'invoice'},
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
async def upload_statement_pdf(file: UploadFile = File(...), db: AsyncIOMotorDatabase = Depends(get_db)):
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
            docs = []
            for row in rows:
                docs.append({
                    'upload_batch_id': upload_batch_id,
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

        fiscal_years = []
        years = []
        months_available = []
        seen_fy = set()
        seen_years = set()
        seen_months = set()

        for item in grouped:
            fy = item.get('fiscal_year')
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

        selected_fiscal_year = fiscal_year
        if selected_fiscal_year is None and year is None and month is None and fiscal_years:
            selected_fiscal_year = fiscal_years[0]['value']
        filtered = grouped

        if selected_fiscal_year:
            filtered = [item for item in filtered if item.get('fiscal_year') == selected_fiscal_year]

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
