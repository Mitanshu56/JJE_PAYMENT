# Payment Tracking Dashboard System

A complete full-stack application for tracking payments and invoices with intelligent payment matching.

## 🎯 Features

- **Invoice Upload**: Import Excel invoice files with label-based extraction
- **Bank Statement Upload**: Import payment records from bank statements
- **Smart Matching**: Fuzzy name matching, amount matching with tolerance, and date proximity detection
- **Real-time Dashboard**: Monitor payment status, party-wise analytics, and monthly trends
- **Multi-invoice Support**: Handle multiple invoices per sheet or multiple sheets
- **Production-Ready**: Error handling, logging, validation, and comprehensive API documentation

## 🏗️ Project Structure

```
├── backend/                          # Python FastAPI Backend
│   ├── app/
│   │   ├── routes/                  # API endpoints
│   │   │   ├── upload_routes.py    # File upload endpoints
│   │   │   ├── bill_routes.py      # Invoice management
│   │   │   ├── payment_routes.py   # Payment management
│   │   │   └── dashboard_routes.py # Analytics & matching
│   │   ├── controllers/             # Business logic
│   │   │   ├── bill_controller.py
│   │   │   └── payment_controller.py
│   │   ├── services/                # Core algorithms
│   │   │   └── matcher.py           # Payment matching engine
│   │   ├── models/                  # Data models
│   │   │   ├── bill.py
│   │   │   ├── payment.py
│   │   │   └── party.py
│   │   ├── utils/                   # Utility functions
│   │   │   └── excel_parser.py     # Label-based Excel parsing
│   │   ├── core/                    # Core configuration
│   │   │   ├── config.py           # Settings
│   │   │   └── database.py         # MongoDB connection
│   │   └── main.py                 # FastAPI app entry point
│   ├── requirements.txt              # Python dependencies
│   └── .env.example                 # Environment variables template
│
├── frontend/                         # React + Vite Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── dashboard/          # Dashboard summary
│   │   │   ├── tables/             # Data tables
│   │   │   ├── charts/             # Analytics charts
│   │   │   ├── FileUpload.jsx      # Upload component
│   │   │   └── Header.jsx          # Navigation header
│   │   ├── services/
│   │   │   └── api.js              # API client
│   │   ├── pages/
│   │   │   └── Dashboard.jsx       # Main dashboard page
│   │   ├── App.jsx                 # Root component
│   │   ├── main.jsx                # React entry point
│   │   └── index.css               # Tailwind styles
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.cjs
│   └── index.html
│
└── README.md                         # This file
```

## 📋 Prerequisites

- Python 3.9+
- Node.js 16+
- MongoDB 4.4+
- Git

## 🚀 Setup Instructions

### 1. Backend Setup

#### Step 1.1: Navigate to backend directory
```bash
cd backend
```

#### Step 1.2: Create virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### Step 1.3: Install dependencies
```bash
pip install -r requirements.txt
```

#### Step 1.4: Create .env file
```bash
# Copy the example file
cp .env.example .env

# Edit .env with your settings
# MONGODB_URL=mongodb://localhost:27017
# MONGODB_DB_NAME=payment_tracking
# DEBUG=True
```

#### Step 1.5: Ensure MongoDB is running
```bash
# On Windows (if installed locally)
mongod

# Or use MongoDB Atlas connection string
# MONGODB_URL=mongodb+srv://user:password@cluster.mongodb.net/database?retryWrites=true&w=majority
```

#### Step 1.6: Start the backend server
```bash
# From backend directory
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend should be running at: **http://localhost:8000**

### 2. Frontend Setup

#### Step 2.1: Navigate to frontend directory (in new terminal)
```bash
cd frontend
```

#### Step 2.2: Install dependencies
```bash
npm install
```

#### Step 2.3: Start development server
```bash
npm run dev
```

Frontend should be running at: **http://localhost:3000**

## 📚 API Documentation

Once the backend is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key API Endpoints

#### Upload Endpoints
- `POST /api/upload/invoices` - Upload invoice Excel file
- `POST /api/upload/bank-statements` - Upload bank statement Excel file
- `GET /api/upload/history` - Get upload history

#### Bill Management
- `GET /api/bills/` - List all bills with filters
- `GET /api/bills/{invoice_no}` - Get specific bill
- `GET /api/bills/party/{party_name}` - Get bills by party
- `DELETE /api/bills/{invoice_no}` - Delete bill

#### Payment Management
- `GET /api/payments/` - List all payments
- `GET /api/payments/{payment_id}` - Get specific payment
- `GET /api/payments/party/{party_name}` - Get payments by party
- `DELETE /api/payments/{payment_id}` - Delete payment

#### Dashboard & Matching
- `POST /api/match-payments` - Run payment matching algorithm
- `GET /api/dashboard/summary` - Get dashboard summary
- `GET /api/dashboard/party-summary` - Get party-wise summary
- `GET /api/dashboard/monthly-summary` - Get monthly summary
- `GET /api/health` - Health check

## 🧠 Excel File Format

### Invoice Excel Format (Label-Based)

The system expects invoices to have a label-based layout (like printed invoices):

```
Invoice No.:           INV-2024-001
Invoice Date:          15-01-2024
Party Name:            ABC Corporation
Party GST No.:         18AABCT1234A1Z5

Line Items:
Item 1                 $1000
Item 2                 $2000

Net Amount:            $3000
CGST (9%):             $270
SGST (9%):             $270
Grand Total:           $3540

Site:                  Delhi
```

The system will:
- Automatically detect invoice blocks
- Extract values using label matching (fuzzy regex)
- Handle multiple invoices per sheet
- Support multiple sheets

### Bank Statement Format

Standard Excel format with columns like:
```
Date | Description | Amount | Reference
2024-01-20 | ABC Corporation | 3540 | CHQ-123456
```

The system will auto-detect headers and extract payment data.

## 🎯 Payment Matching Algorithm

The matching system uses a scoring mechanism (0-100 points):

1. **Party Name Matching** (40 points)
   - Uses fuzzy matching (token_set_ratio)
   - Threshold: 80% similarity

2. **Amount Matching** (40 points)
   - Exact match (within 0.5% tolerance): 40 points
   - Close match (within 5%): 30 points
   - Reasonable match (within 10%): 20 points
   - Loose match (within 20%): 10 points

3. **Date Proximity** (20 points)
   - Same day: 20 points
   - Within 3 days: 15 points
   - Within 7 days (configurable): 10 points
   - Within 30 days: 5 points

**Match Result**:
- Score > 80: PAID/PARTIAL (depending on amount match)
- Score < 80: UNPAID (no match found)
- Multiple partial matches: PARTIAL status

## 📊 Dashboard Features

### 1. Summary Cards
- Total Billing
- Total Received
- Pending Amount
- Total Invoices with status breakdown

### 2. Charts
- Monthly Revenue Trend (Line chart)
- Paid vs Pending by Month (Bar chart)
- Overall Payment Status (Pie chart)
- Billed vs Collected (Bar chart)

### 3. Party Summary Table
- Party-wise total billing, paid, and pending amounts
- Collection percentage progress bar
- Health status indicator

### 4. Invoices Table
- Invoice list with filters (status, party)
- Status indicators (PAID, PARTIAL, UNPAID)
- Paid and remaining amount tracking
- Delete functionality

## 🔄 Workflow Example

1. **Upload Invoice Excel**
   - Click "Upload" button
   - Select invoice file
   - System extracts and stores invoices

2. **Upload Bank Statement**
   - Click "Upload" button
   - Switch to "Bank Statement"
   - Select bank statement file
   - System extracts and stores payments

3. **Run Payment Matching**
   - Click "Match Payments" button
   - System matches payments with invoices
   - Updates bill statuses (PAID/PARTIAL/UNPAID)

4. **View Dashboard**
   - See summary cards with totals
   - View party-wise payment status
   - Analyze monthly trends with charts
   - Filter and search invoices

## 🔧 Configuration

Edit `backend/app/core/config.py` to customize:

```python
# Matching thresholds
FUZZY_MATCH_THRESHOLD = 80        # % similarity for name matching
DATE_PROXIMITY_DAYS = 7            # Days window for date matching
AMOUNT_TOLERANCE_PERCENT = 0.5     # % tolerance for amount matching

# File uploads
MAX_UPLOAD_SIZE = 50 * 1024 * 1024 # 50MB
ALLOWED_EXTENSIONS = ["xlsx", "xls"]

# Database
MONGODB_URL = "mongodb://localhost:27017"
MONGODB_DB_NAME = "payment_tracking"
```

## 📁 Database Collections

### bills
```json
{
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
  "created_at": "2024-01-15T00:00:00",
  "updated_at": "2024-01-15T00:00:00"
}
```

### payments
```json
{
  "payment_id": "PAY-2024-001",
  "party_name": "ABC Corporation",
  "amount": 11800,
  "payment_date": "2024-01-20T00:00:00",
  "reference": "Bank Ref #123456",
  "matched_invoice_nos": ["INV-2024-001"],
  "notes": "",
  "created_at": "2024-01-20T00:00:00",
  "updated_at": "2024-01-20T00:00:00"
}
```

### parties
```json
{
  "party_name": "ABC Corporation",
  "gst_no": "18AABCT1234A1Z5",
  "contact_person": "John Doe",
  "email": "john@abc.com",
  "phone": "+91-9876543210",
  "address": "123 Business St, Delhi",
  "total_billed": 50000,
  "total_paid": 30000,
  "pending_amount": 20000,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-15T00:00:00"
}
```

## ⚙️ Environment Variables

Create `.env` file in backend directory:

```env
# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=payment_tracking

# Application Settings
DEBUG=True
LOG_LEVEL=INFO
API_TITLE=Payment Tracking Dashboard API
API_VERSION=1.0.0

# File Upload
MAX_UPLOAD_SIZE=52428800

# Matching Engine
FUZZY_MATCH_THRESHOLD=80
DATE_PROXIMITY_DAYS=7
AMOUNT_TOLERANCE_PERCENT=0.5
```

## 🧪 Testing

### Backend Testing
```bash
cd backend
# Run tests (requires pytest)
pytest tests/
```

### Frontend Testing
```bash
cd frontend
# Run tests (requires Jest)
npm test
```

## 📝 Example Excel Templates

### Invoice Template
Save as `.xlsx` and upload:
```
Invoice No.        | INV-2024-001
Date               | 15-01-2024
Party Name         | ABC Corporation
GST No.            | 18AABCT1234A1Z5
Net Amount         | 10000
CGST               | 900
SGST               | 900
Grand Total        | 11800
Site               | Delhi
```

### Bank Statement Template
```
Date           | Description        | Amount | Reference
20-01-2024     | ABC Corporation    | 11800  | CHQ-123456
25-01-2024     | XYZ Industries     | 5000   | NEFT-789012
```

## 🐛 Troubleshooting

### MongoDB Connection Issues
- Ensure MongoDB is running: `mongod`
- Check connection string in `.env`
- Verify network connectivity if using MongoDB Atlas

### CORS Errors
- Backend CORS is configured for `*` (change in production)
- Ensure frontend is on `http://localhost:3000`
- Backend should be on `http://localhost:8000`

### File Upload Issues
- Check file size limit (default 50MB)
- Ensure file is valid Excel format (.xlsx or .xls)
- Check browser console for detailed error messages

### Matching Not Working
- Ensure payments have clear party names
- Check fuzzy matching threshold in config
- Verify date formats are consistent

## 📈 Production Deployment

### Backend
```bash
# Use production ASGI server (not uvicorn)
pip install gunicorn
gunicorn app.main:app -w 4 -b 0.0.0.0:8000

# Or use Docker
docker build -t payment-dashboard-backend .
docker run -p 8000:8000 payment-dashboard-backend
```

### Frontend
```bash
# Build optimized production bundle
npm run build

# Serve with production server (nginx, etc)
# dist/ folder contains static files
```

### Environment
- Set `DEBUG=False`
- Use production MongoDB instance
- Configure CORS properly
- Set up logging and monitoring
- Use HTTPS/SSL
- Enable authentication

## 📞 Support

For issues or questions:
1. Check API documentation at `/docs`
2. Review error logs in backend console
3. Check browser console for frontend errors
4. Verify database connection and data

## 📄 License

This project is built for educational and demonstration purposes.

## 🎓 Key Technologies

- **Backend**: FastAPI, Pandas, OpenPyXL, Rapidfuzz, Motor (async MongoDB)
- **Frontend**: React 18, Vite, Tailwind CSS, Recharts
- **Database**: MongoDB
- **Other**: Python 3.9+, Node.js 16+

---

**Ready to track your payments efficiently! 🎉**
