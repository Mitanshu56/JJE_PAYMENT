from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class PaymentReminderConfig(BaseModel):
    party_name: str
    party_email: str
    reminder_type: str = Field(..., description="single|multiple")
    invoice_ids: Optional[List[str]] = []
    invoice_numbers: Optional[List[str]] = []
    reminder_days: int = 30
    is_active: bool = True
    last_reminder_sent_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PaymentReminderHistory(BaseModel):
    party_name: str
    party_email: str
    reminder_type: str
    invoice_numbers: Optional[List[str]] = []
    invoice_ids: Optional[List[str]] = []
    total_amount: float = 0.0
    total_pending_amount: float = 0.0
    reminder_days: int = 0
    email_subject: Optional[str] = None
    email_status: str = Field(default="sent", description="sent|failed")
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None