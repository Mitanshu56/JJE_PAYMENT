from pymongo import MongoClient

c = MongoClient('mongodb://localhost:27017')
col = c['payment_tracking']['bills']

# Count total
total = col.count_documents({})
print(f'Total bills in DB: {total}')

# Find the last few invoices sorted numerically
last_invoices = list(col.find(
    {},
    {'_id': 0, 'invoice_no': 1, 'party_name': 1, 'grand_total': 1}
).sort([('invoice_no', -1)]).limit(5))

print(f'\nLast 5 invoices by invoice_no:')
for inv in last_invoices:
    print(inv)

# Check for any with no invoice_no
no_invoice_no = list(col.find(
    {'$or': [{'invoice_no': {'$exists': False}}, {'invoice_no': None}, {'invoice_no': ''}]},
    {'_id': 1, 'invoice_no': 1, 'party_name': 1}
).limit(5))

if no_invoice_no:
    print(f'\nRecords with no invoice_no: {len(no_invoice_no)}')
    for rec in no_invoice_no:
        print(f"  ID: {rec['_id']}, invoice_no: {rec.get('invoice_no')}, party: {rec.get('party_name')}")

# Check for duplicate invoices
all_invoices = list(col.find({}, {'_id': 0, 'invoice_no': 1}).sort([('invoice_no', 1)]))
inv_counts = {}
for inv in all_invoices:
    inv_no = inv.get('invoice_no')
    inv_counts[inv_no] = inv_counts.get(inv_no, 0) + 1

duplicates = {k: v for k, v in inv_counts.items() if v > 1}
if duplicates:
    print(f'\nDuplicate invoices: {duplicates}')

c.close()
