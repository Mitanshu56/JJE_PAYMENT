import asyncio
import motor.motor_asyncio
import hashlib
import secrets
from datetime import datetime

def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt_bytes = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 200_000)
    return f"{salt_bytes.hex()}:{digest.hex()}"

async def reset_auth():
    client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["payment_tracking"]
    new_hash = _hash_password("meeT@meet")
    result = await db["auth_settings"].update_one(
        {"_id": "primary_auth"},
        {"$set": {"password_hash": new_hash, "updated_at": datetime.utcnow()}}
    )
    print("Updated:", result.modified_count)
    auth = await db["auth_settings"].find_one({"_id": "primary_auth"})
    print("Password hash now:", auth.get("password_hash"))

asyncio.run(reset_auth())
