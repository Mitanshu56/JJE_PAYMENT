"""
Database connection and initialization
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
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
        # Bills indexes
        bills_col = db["bills"]
        # Migrate from legacy unique invoice_no index to invoice_key uniqueness.
        try:
            await bills_col.drop_index("invoice_no_1")
        except Exception:
            pass

        await bills_col.create_index("invoice_key", unique=True, sparse=True)
        await bills_col.create_index("invoice_no")
        await bills_col.create_index("party_name")
        await bills_col.create_index("invoice_date")
        await bills_col.create_index("status")
        
        # Payments indexes
        payments_col = db["payments"]
        await payments_col.create_index("payment_id", unique=True, sparse=True)
        await payments_col.create_index("party_name")
        await payments_col.create_index("payment_date")
        await payments_col.create_index("reference")
        
        # Parties indexes
        parties_col = db["parties"]
        await parties_col.create_index("party_name", unique=True, sparse=True)
        
        # Upload logs
        logs_col = db["upload_logs"]
        await logs_col.create_index("created_at")
        await logs_col.create_index("file_name")

        # Statement entries indexes
        statements_col = db["statement_entries"]
        await statements_col.create_index("month_key")
        await statements_col.create_index("value_date")
        await statements_col.create_index("upload_batch_id")
        
        logger.info("✓ Database indexes created successfully")
    except Exception as e:
        logger.error(f"✗ Failed to create indexes: {str(e)}")
        raise


def get_db() -> AsyncIOMotorDatabase:
    """Get database instance for use in routes"""
    if db is None:
        raise RuntimeError("Database not initialized. Call connect_db() first.")
    return db
