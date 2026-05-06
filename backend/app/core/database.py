"""
Database connection and initialization
"""
from typing import Any
try:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
except Exception:
    AsyncIOMotorClient = Any
    AsyncIOMotorDatabase = Any
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Global database instance
db_client: AsyncIOMotorClient = None
db: AsyncIOMotorDatabase = None


async def connect_db():
    """Connect to MongoDB"""
    global db_client, db
    try:
        db_client = AsyncIOMotorClient(settings.MONGODB_URL)
        db = db_client[settings.MONGODB_DB_NAME]
        
        # Test connection
        await db.command("ping")
        logger.info("✓ Connected to MongoDB successfully")
        
        # Create indexes
        await create_indexes()
    except Exception as e:
        logger.error(f"✗ Failed to connect to MongoDB: {str(e)}")
        raise


async def close_db():
    """Close MongoDB connection"""
    global db_client
    if db_client:
        db_client.close()
        logger.info("✓ Closed MongoDB connection")


async def create_indexes():
    """Create database indexes for performance"""
    try:
        async def safe_create_index(collection, *args, **kwargs):
            try:
                await collection.create_index(*args, **kwargs)
            except Exception as exc:
                if 'same name as the requested index' in str(exc) or getattr(exc, 'code', None) == 86:
                    logger.info("Index already exists, skipping: %s %s", args, kwargs)
                    return
                raise

        # Bills indexes
        bills_col = db["bills"]
        # Migrate from legacy unique invoice_no index to invoice_key uniqueness.
        try:
            await bills_col.drop_index("invoice_no_1")
        except Exception:
            pass

        await safe_create_index(bills_col, "invoice_key", unique=True, sparse=True)
        await safe_create_index(bills_col, "invoice_no")
        await safe_create_index(bills_col, "party_name")
        await safe_create_index(bills_col, "invoice_date")
        await safe_create_index(bills_col, "status")
        await safe_create_index(bills_col, [("last_upload_batch_id", 1), ("created_at", -1)])
        
        # Payments indexes
        payments_col = db["payments"]
        await safe_create_index(payments_col, "payment_id", unique=True, sparse=True)
        await safe_create_index(payments_col, "party_name")
        await safe_create_index(payments_col, "payment_date")
        await safe_create_index(payments_col, "reference")
        
        # Parties indexes
        parties_col = db["parties"]
        await safe_create_index(parties_col, "party_name", unique=True, sparse=True)
        
        # Upload logs
        logs_col = db["upload_logs"]
        await safe_create_index(logs_col, "created_at")
        await safe_create_index(logs_col, "file_name")
        await safe_create_index(logs_col, [("file_type", 1), ("created_at", -1)])

        # Authentication reset tokens
        reset_tokens_col = db["password_reset_tokens"]
        await safe_create_index(reset_tokens_col, "token_hash", unique=True)
        await safe_create_index(reset_tokens_col, "expires_at", expireAfterSeconds=0)

        # Authentication settings
        auth_settings_col = db["auth_settings"]
        await safe_create_index(auth_settings_col, "_id")

        # Statement entries indexes
        statements_col = db["statement_entries"]
        await safe_create_index(statements_col, "month_key")
        await safe_create_index(statements_col, "value_date")
        await safe_create_index(statements_col, "upload_batch_id")
        
        # Fiscal year master and FY-aware indexes
        fiscal_col = db["fiscal_years"]
        # seed current fiscal year if missing - do not block startup on failures
        try:
            from app.core.fiscal import current_fiscal_year_label

            current_fy = current_fiscal_year_label()
            await fiscal_col.update_one({"value": current_fy}, {"$setOnInsert": {"value": current_fy, "start_date": None, "end_date": None, "status": "active"}}, upsert=True)
        except Exception:
            pass

        # Add FY-related indexes on main collections
        try:
            await safe_create_index(bills_col, [("fiscal_year", 1), ("invoice_key", 1)], unique=True, sparse=True)
        except Exception:
            # ignore if index exists or invalid
            pass
        try:
            await safe_create_index(payments_col, [("fiscal_year", 1), ("payment_id", 1)], unique=True, sparse=True)
        except Exception:
            pass
        try:
            await safe_create_index(bills_col, [("fiscal_year", 1), ("party_name", 1)])
            await safe_create_index(payments_col, [("fiscal_year", 1), ("party_name", 1)])
        except Exception:
            pass
        
        logger.info("✓ Database indexes created successfully")
    except Exception as e:
        logger.error(f"✗ Failed to create indexes: {str(e)}")
        raise


def get_db() -> AsyncIOMotorDatabase:
    """Get database instance for use in routes"""
    if db is None:
        raise RuntimeError("Database not initialized. Call connect_db() first.")
    return db
