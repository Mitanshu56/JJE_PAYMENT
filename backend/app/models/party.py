"""Party/Vendor model"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Party(BaseModel):
    """Party/Vendor model"""
    party_name: str
    gst_no: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    total_billed: float = 0.0
    total_paid: float = 0.0
    pending_amount: float = 0.0
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()
    
    class Config:
        json_schema_extra = {
            "example": {
                "party_name": "ABC Corporation",
                "gst_no": "18AABCT1234A1Z5",
                "contact_person": "John Doe",
                "email": "john@abc.com",
                "phone": "+91-9876543210",
                "address": "123 Business St, Delhi"
            }
        }
