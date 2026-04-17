"""Bill/Invoice model"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class BillStatus(str, Enum):
    """Bill payment status"""
    PAID = "PAID"
    PARTIAL = "PARTIAL"
    UNPAID = "UNPAID"


class Bill(BaseModel):
    """Invoice/Bill model"""
    invoice_no: str
    party_name: str
    gst_no: Optional[str] = None
    invoice_date: datetime
    net_amount: float
    cgst: float = 0.0
    sgst: float = 0.0
    grand_total: float
    site: Optional[str] = None
    status: BillStatus = BillStatus.UNPAID
    paid_amount: float = 0.0
    remaining_amount: Optional[float] = None
    matched_payment_ids: list = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = False
        json_schema_extra = {
            "example": {
                "invoice_no": "INV-2024-001",
                "party_name": "ABC Corporation",
                "gst_no": "18AABCT1234A1Z5",
                "invoice_date": "2024-01-15T00:00:00",
                "net_amount": 10000.0,
                "cgst": 900.0,
                "sgst": 900.0,
                "grand_total": 11800.0,
                "site": "Delhi",
                "status": "UNPAID"
            }
        }
