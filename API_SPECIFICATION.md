# API Specification

## Authentication
Currently, the API is open (no authentication). For production, implement JWT or API key authentication.

## Base URL
```
http://localhost:8000
```

---

## Endpoints

### Health Check

#### GET /api/health
Health check endpoint to verify API is running.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-20T10:30:45.123456"
}
```

---

## File Upload Endpoints

### Upload Invoice File

#### POST /api/upload/invoices
Upload Excel file containing invoices. Supports label-based invoice extraction.

**Request:**
- `Content-Type: multipart/form-data`
- `file: File` - Excel file (.xlsx, .xls)

**Example with cURL:**
```bash
curl -X POST "http://localhost:8000/api/upload/invoices" \
  -H "accept: application/json" \
  -F "file=@invoices.xlsx"
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Successfully imported 5 invoices",
  "invoices_count": 5,
  "invoices": [
    {
      "invoice_no": "INV-2024-001",
      "party_name": "ABC Corporation",
      "gst_no": "18AABCT1234A1Z5",
      "invoice_date": "2024-01-15",
      "net_amount": 10000,
      "cgst": 900,
      "sgst": 900,
      "grand_total": 11800,
      "site": "Delhi",
      "status": "UNPAID",
      "paid_amount": 0,
      "remaining_amount": 11800
    }
  ]
}
```

**Error Response (400):**
```json
{
  "detail": "No valid invoices found in file"
}
```

---

### Upload Bank Statement

#### POST /api/upload/bank-statements
Upload Excel file containing bank statement/payments.

**Request:**
- `Content-Type: multipart/form-data`
- `file: File` - Excel file (.xlsx, .xls)

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Successfully imported 3 payments",
  "payments_count": 3,
  "payments": [
    {
      "payment_id": "PAY-123456789",
      "party_name": "ABC Corporation",
      "amount": 11800,
      "payment_date": "2024-01-20",
      "reference": "CHQ-123456",
      "matched_invoice_nos": []
    }
  ]
}
```

---

### Get Upload History

#### GET /api/upload/history
Get history of all uploaded files.

**Parameters:**
- `limit: int` (Query) - Maximum number of records (default: 50)

**Response (200 OK):**
```json
{
  "status": "success",
  "upload_history": [
    {
      "_id": "507f1f77bcf86cd799439011",
      "file_name": "invoices_jan2024.xlsx",
      "file_type": "invoice",
      "records_count": 15,
      "created_at": "2024-01-20T10:30:45.123456"
    },
    {
      "_id": "507f1f77bcf86cd799439012",
      "file_name": "bank_statement_jan2024.xlsx",
      "file_type": "bank_statement",
      "records_count": 8,
      "created_at": "2024-01-20T11:15:30.654321"
    }
  ]
}
```

---

## Bill Management Endpoints

### List Bills

#### GET /api/bills/
Get all bills with optional filtering.

**Parameters:**
- `skip: int` (Query) - Number of records to skip (default: 0)
- `limit: int` (Query) - Maximum records to return (default: 100)
- `status: string` (Query) - Filter by status: PAID, UNPAID, PARTIAL
- `party: string` (Query) - Filter by party name (case-insensitive)

**Example:**
```
GET /api/bills/?skip=0&limit=10&status=UNPAID&party=ABC
```

**Response (200 OK):**
```json
{
  "status": "success",
  "total": 25,
  "skip": 0,
  "limit": 10,
  "bills": [
    {
      "_id": "507f1f77bcf86cd799439011",
      "invoice_no": "INV-2024-001",
      "party_name": "ABC Corporation",
      "gst_no": "18AABCT1234A1Z5",
      "invoice_date": "2024-01-15T00:00:00",
      "net_amount": 10000,
      "cgst": 900,
      "sgst": 900,
      "grand_total": 11800,
      "site": "Delhi",
      "status": "UNPAID",
      "paid_amount": 0,
      "remaining_amount": 11800,
      "matched_payment_ids": [],
      "created_at": "2024-01-20T10:30:45.123456",
      "updated_at": "2024-01-20T10:30:45.123456"
    }
  ]
}
```

---

### Get Single Bill

#### GET /api/bills/{invoice_no}
Get details of a specific bill.

**Parameters:**
- `invoice_no: string` (Path) - Invoice number

**Response (200 OK):**
```json
{
  "status": "success",
  "bill": {
    "_id": "507f1f77bcf86cd799439011",
    "invoice_no": "INV-2024-001",
    "party_name": "ABC Corporation",
    "gst_no": "18AABCT1234A1Z5",
    "invoice_date": "2024-01-15T00:00:00",
    "net_amount": 10000,
    "cgst": 900,
    "sgst": 900,
    "grand_total": 11800,
    "site": "Delhi",
    "status": "UNPAID",
    "paid_amount": 0,
    "remaining_amount": 11800,
    "matched_payment_ids": []
  }
}
```

**Error Response (404):**
```json
{
  "detail": "Bill not found"
}
```

---

### Get Bills by Party

#### GET /api/bills/party/{party_name}
Get all bills for a specific party.

**Response (200 OK):**
```json
{
  "status": "success",
  "party": "ABC Corporation",
  "bills": [
    { /* bill objects */ }
  ]
}
```

---

### Delete Bill

#### DELETE /api/bills/{invoice_no}
Delete a specific bill.

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Bill INV-2024-001 deleted successfully"
}
```

---

## Payment Management Endpoints

### List Payments

#### GET /api/payments/
Get all payments with optional filtering.

**Parameters:**
- `skip: int` (Query) - Number of records to skip (default: 0)
- `limit: int` (Query) - Maximum records to return (default: 100)
- `party: string` (Query) - Filter by party name

**Response (200 OK):**
```json
{
  "status": "success",
  "total": 15,
  "skip": 0,
  "limit": 100,
  "payments": [
    {
      "_id": "507f1f77bcf86cd799439021",
      "payment_id": "PAY-123456789",
      "party_name": "ABC Corporation",
      "amount": 11800,
      "payment_date": "2024-01-20T00:00:00",
      "reference": "CHQ-123456",
      "matched_invoice_nos": ["INV-2024-001"],
      "notes": "",
      "created_at": "2024-01-20T10:30:45.123456",
      "updated_at": "2024-01-20T10:30:45.123456"
    }
  ]
}
```

---

### Get Single Payment

#### GET /api/payments/{payment_id}
Get details of a specific payment.

**Response (200 OK):**
```json
{
  "status": "success",
  "payment": { /* payment object */ }
}
```

---

### Get Payments by Party

#### GET /api/payments/party/{party_name}
Get all payments for a specific party.

**Response (200 OK):**
```json
{
  "status": "success",
  "party": "ABC Corporation",
  "payments": [ /* payment objects */ ]
}
```

---

### Delete Payment

#### DELETE /api/payments/{payment_id}
Delete a specific payment.

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Payment PAY-123456789 deleted successfully"
}
```

---

## Dashboard & Matching Endpoints

### Match Payments

#### POST /api/match-payments
Run the payment matching algorithm to match payments with invoices.

**Request:**
- No request body required

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Successfully matched 12 bills",
  "bills_matched": 12,
  "matched_bills": [
    {
      "invoice_no": "INV-2024-001",
      "party_name": "ABC Corporation",
      "grand_total": 11800,
      "status": "PAID",
      "paid_amount": 11800,
      "remaining_amount": 0,
      "matched_payment_ids": ["PAY-123456789"]
    }
  ]
}
```

---

### Dashboard Summary

#### GET /api/dashboard/summary
Get dashboard summary statistics.

**Response (200 OK):**
```json
{
  "status": "success",
  "summary": {
    "total_billing": 500000,
    "total_paid": 350000,
    "total_pending": 150000,
    "paid_percentage": 70.0,
    "invoice_stats": {
      "paid": 25,
      "partial": 5,
      "unpaid": 20,
      "total": 50
    },
    "payment_records": 35
  }
}
```

---

### Party Summary

#### GET /api/dashboard/party-summary
Get party-wise payment summary.

**Response (200 OK):**
```json
{
  "status": "success",
  "party_summary": [
    {
      "party_name": "ABC Corporation",
      "total_billed": 100000,
      "total_paid": 80000,
      "pending_amount": 20000,
      "invoice_count": 10,
      "paid_count": 8,
      "unpaid_count": 2
    },
    {
      "party_name": "XYZ Industries",
      "total_billed": 150000,
      "total_paid": 120000,
      "pending_amount": 30000,
      "invoice_count": 15,
      "paid_count": 12,
      "unpaid_count": 3
    }
  ]
}
```

---

### Monthly Summary

#### GET /api/dashboard/monthly-summary
Get monthly payment statistics.

**Response (200 OK):**
```json
{
  "status": "success",
  "monthly_summary": [
    {
      "month": "2024-01",
      "total_billed": 250000,
      "total_paid": 180000,
      "total_pending": 70000,
      "invoice_count": 25
    },
    {
      "month": "2024-02",
      "total_billed": 300000,
      "total_paid": 220000,
      "total_pending": 80000,
      "invoice_count": 30
    }
  ]
}
```

---

## Error Responses

All errors follow this format:

**400 - Bad Request:**
```json
{
  "detail": "Only Excel files (.xlsx, .xls) allowed"
}
```

**404 - Not Found:**
```json
{
  "detail": "Bill not found"
}
```

**500 - Internal Server Error:**
```json
{
  "detail": "Error processing file: [error message]"
}
```

---

## Rate Limiting

Currently not implemented. Recommended for production:
- 100 requests per minute per IP for public endpoints
- 1000 requests per minute per IP for authenticated endpoints

---

## Example Workflow

```javascript
// 1. Upload invoices
POST /api/upload/invoices -> 5 invoices created

// 2. Upload bank statements
POST /api/upload/bank-statements -> 3 payments created

// 3. Get dashboard summary
GET /api/dashboard/summary -> {total_billing: 60000, total_paid: 0, ...}

// 4. Run matching algorithm
POST /api/match-payments -> 3 bills matched

// 5. Get updated summary
GET /api/dashboard/summary -> {total_billing: 60000, total_paid: 45000, ...}

// 6. Get party summary
GET /api/dashboard/party-summary -> [{party: "ABC Corp", billed: 60000, paid: 45000, ...}]
```

---

## Pagination

For list endpoints, use `skip` and `limit`:

```
GET /api/bills/?skip=0&limit=20    # First 20 records
GET /api/bills/?skip=20&limit=20   # Next 20 records
GET /api/bills/?skip=40&limit=20   # Records 40-60
```

---

## Filtering

### By Status
```
GET /api/bills/?status=PAID
GET /api/bills/?status=UNPAID
GET /api/bills/?status=PARTIAL
```

### By Party (case-insensitive)
```
GET /api/bills/?party=ABC
```

### Combined
```
GET /api/bills/?status=UNPAID&party=ABC&skip=0&limit=50
```

---

See `main.md` for more documentation and examples.
