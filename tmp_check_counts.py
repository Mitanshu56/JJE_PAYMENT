from pathlib import Path
import sys
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / 'backend'
sys.path.insert(0, str(BACKEND))

from app.utils.excel_parser import InvoiceParser

workbook_path = ROOT / 'Copy of bill 25-26.xlsx'
parser = InvoiceParser(str(workbook_path))
invoices = parser.parse()
print('parsed_count', len(invoices))
print('first_10', [(inv.get('invoice_no'), inv.get('party_name')) for inv in invoices[:10]])

client = MongoClient('mongodb://localhost:27017')
col = client['payment_tracking']['bills']
print('db_count', col.count_documents({}))
print('db_first_10', [(doc.get('invoice_no'), doc.get('party_name')) for doc in col.find({}, {'invoice_no': 1, 'party_name': 1}).sort([('_id', 1)]).limit(10)])
client.close()
