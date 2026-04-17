from pymongo import MongoClient

c = MongoClient('mongodb://localhost:27017')
col = c['payment_tracking']['bills']

# Find all copies of invoice 1
copies = list(col.find({'invoice_no': '1'}, {'_id': 1, 'invoice_no': 1, 'party_name': 1, 'grand_total': 1, 'created_at': 1}).sort([('created_at', 1)]))

print(f'Found {len(copies)} copies of invoice 1:')
for i, rec in enumerate(copies, 1):
    print(f"  Copy {i}: ID={rec['_id']}, Party={rec.get('party_name')}, Amount={rec.get('grand_total')}, Created={rec.get('created_at')}")

# Delete the older one
if len(copies) > 1:
    old_id = copies[0]['_id']
    result = col.delete_one({'_id': old_id})
    print(f'\nDeleted older duplicate (ID: {old_id}): {result.deleted_count} record(s)')
    
    # Verify new count
    new_total = col.count_documents({})
    print(f'New total invoice count: {new_total}')

c.close()
