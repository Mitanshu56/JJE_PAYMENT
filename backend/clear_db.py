from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017")
db = client["payment_tracking"]

# Drop collections to start fresh
collections_to_clear = ["bills", "upload_logs"]

for collection in collections_to_clear:
    col = db[collection]
    count = col.count_documents({})
    if count > 0:
        col.delete_many({})
        print(f"✓ Cleared '{collection}': {count} records deleted")
    else:
        print(f"  '{collection}': already empty")

# Verify
print("\n✓ Database cleanup complete. Starting fresh state:")
for collection in collections_to_clear:
    count = db[collection].count_documents({})
    print(f"  {collection}: {count} records")

# Keep payments collection info for reference
payment_count = db["payments"].count_documents({})
print(f"\n  payments (preserved): {payment_count} records")

client.close()
