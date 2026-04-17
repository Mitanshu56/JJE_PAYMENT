"""Payment model"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Payment(BaseModel):
    """Payment model"""
    payment_id: str
    party_name: str
    amount: float
    payment_date: datetime
    reference: Optional[str] = None
    matched_invoice_nos: list = []
    notes: Optional[str] = None
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()
    
    class Config:
        json_schema_extra = {
            "example": {
                "payment_id": "PAY-2024-001",
                "party_name": "ABC Corporation",
                "amount": 11800.0,
                "payment_date": "2024-01-20T00:00:00",
                "reference": "Bank Ref #123456",
                "matched_invoice_nos": ["INV-2024-001"]
            }
        }
