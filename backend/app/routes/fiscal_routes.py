"""Fiscal year listing and admin management routes."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Body
import hmac
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.routes.auth_routes import _get_auth_settings, _verify_password, AUTH_SETTINGS_ID
from app.core.config import settings

router = APIRouter(prefix="/api/fiscal", tags=["Fiscal"])


class FiscalYearCreateRequest(BaseModel):
    value: str = Field(min_length=4, max_length=32)
    label: str | None = None


class DeleteFiscalYearRequest(BaseModel):
    password: str


def _require_admin(request: Request) -> None:
    if getattr(request.state, "role", "user") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/years")
async def list_fiscal_years(db: AsyncIOMotorDatabase = Depends(get_db)):
    docs = await db["fiscal_years"].find({}, {"_id": 0}).sort("value", -1).to_list(length=100)
    return {"status": "success", "data": docs}


@router.post("/years")
async def create_fiscal_year(payload: FiscalYearCreateRequest, request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    _require_admin(request)

    fiscal_value = payload.value.strip()
    if not fiscal_value:
        raise HTTPException(status_code=400, detail="Fiscal year value is required")

    collection = db["fiscal_years"]
    existing = await collection.find_one({"value": fiscal_value})
    if existing:
        raise HTTPException(status_code=409, detail="Fiscal year already exists")

    record = {
        "value": fiscal_value,
        "label": (payload.label or fiscal_value).strip(),
        "status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await collection.insert_one(record)

    return {
        "status": "success",
        "message": f"Fiscal year {fiscal_value} created successfully",
        "fiscal_year": {"value": record["value"], "label": record["label"], "status": record["status"]},
    }


@router.delete("/years/{fiscal_value}")
async def delete_fiscal_year(
    fiscal_value: str,
    payload: DeleteFiscalYearRequest = Body(...),
    request: Request = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Delete a fiscal year — requires admin role and password confirmation in request body."""
    _require_admin(request)

    value = fiscal_value.strip()
    if not value:
        raise HTTPException(status_code=400, detail="Fiscal year value is required")

    # Verify provided password either against configured admin password or stored auth settings
    provided = (payload.password or "").strip()
    if not provided:
        raise HTTPException(status_code=401, detail="Admin password required to delete fiscal year")

    # Check configured admin password first
    try:
        if settings.ADMIN_PASSWORD and hmac.compare_digest(provided, str(settings.ADMIN_PASSWORD)):
            authorized = True
        else:
            # Fallback to stored auth settings (primary account)
            auth_settings = await _get_auth_settings(db)
            password_hash = str(auth_settings.get("password_hash") or "")
            authorized = _verify_password(provided, password_hash)
    except Exception:
        authorized = False

    if not authorized:
        raise HTTPException(status_code=401, detail="Invalid admin password")

    result = await db["fiscal_years"].delete_one({"value": value})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Fiscal year not found")

    return {
        "status": "success",
        "message": f"Fiscal year {value} removed successfully",
    }
