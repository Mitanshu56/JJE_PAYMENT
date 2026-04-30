"""Fiscal year listing routes."""
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db

router = APIRouter(prefix="/api/fiscal", tags=["Fiscal"])


@router.get("/years")
async def list_fiscal_years(db: AsyncIOMotorDatabase = Depends(get_db)):
    docs = await db["fiscal_years"].find({}, {"_id": 0}).sort("value", -1).to_list(length=100)
    return {"status": "success", "data": docs}
