"""
File upload API routes
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
import tempfile
import os
from datetime import datetime
from app.core.database import get_db
from app.utils.excel_parser import InvoiceParser, BankStatementParser
from app.controllers.bill_controller import BillController
from app.controllers.payment_controller import PaymentController
import logging

logger = logging.getLogger(__name__)

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
            # Parse invoices
            parser = InvoiceParser(temp_path)
            invoices = parser.parse()
            
            if not invoices:
                raise HTTPException(status_code=400, detail="No valid invoices found in file")
            
            # Store in database
            bill_controller = BillController(db)
            deleted_result = await db['bills'].delete_many({})
            if deleted_result.deleted_count:
                logger.info(f"✓ Cleared {deleted_result.deleted_count} existing bills before import")
            inserted_count = await bill_controller.create_bills_bulk(invoices)
            
            # Log upload
            await db['upload_logs'].insert_one({
                'file_name': file.filename,
                'file_type': 'invoice',
                'records_count': inserted_count,
                'created_at': datetime.utcnow()
            })
            
            return {
                'status': 'success',
                'message': f'Successfully imported {inserted_count} invoices',
                'invoices_count': inserted_count,
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
