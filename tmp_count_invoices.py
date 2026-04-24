from app.utils.excel_parser import InvoiceParser

parser = InvoiceParser(r'C:/Users/kevin/OneDrive/Desktop/JJE PAYMENT/Copy of bill 25-26.xlsx')
invoices = parser.parse()
print('parsed_count', len(invoices))
print('first_10', [(inv.get('invoice_no'), inv.get('party_name')) for inv in invoices[:10]])
