# Quick Start Guide

## 🚀 Get Started in 5 Minutes

## uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

### Prerequisites
- Python 3.9+
- Node.js 16+
- MongoDB 4.4+ (local or Atlas)
- Git

### Windows Users

1. **Open PowerShell as Administrator and run:**
```powershell
cd "C:\Users\kevin\OneDrive\Desktop\JJE PAYMENT"
.\setup.bat
```

2. **Start Backend (new PowerShell window):**
```powershell
cd "C:\Users\kevin\OneDrive\Desktop\JJE PAYMENT\backend"
.\venv\Scripts\activate
python -m uvicorn app.main:app --reload --port 8000
```

3. **Start Frontend (new PowerShell window):**
```powershell
cd "C:\Users\kevin\OneDrive\Desktop\JJE PAYMENT\frontend"
npm run dev
```

4. **Open in browser:**
```
Dashboard: http://localhost:3000
API Docs: http://localhost:8000/docs
```

### Login Roles

- **Admin**: `Mitanshu` / `meeT@123`
- **Normal login**: the existing business login still works, and the selected fiscal year is stored in the browser and sent with every request.
- After admin creates a new fiscal year, it appears in the fiscal-year dropdown on the login screen and in the dashboard header.

### Admin FY Setup

- Sign in as admin.
- Open the dashboard and use the **Admin FY Setup** box to create the next fiscal year, such as `FY-2025-2026`.
- Switch the FY dropdown to work inside that fiscal year's dashboard scope.

### macOS/Linux Users

1. **Run setup script:**
```bash
cd ~/Desktop/JJE\ PAYMENT
chmod +x setup.sh
./setup.sh
```

2. **Start Backend (Terminal 1):**
```bash
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

3. **Start Frontend (Terminal 2):**
```bash
cd frontend
npm run dev
```

4. **Open in browser:**
```
Dashboard: http://localhost:3000
API Docs: http://localhost:8000/docs
```

## 📝 First Time Setup - Manual Steps

### Backend Setup

```bash
# 1. Navigate to backend
cd backend

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create .env file
cp .env.example .env
# Edit .env with your MongoDB URL

# 6. Start server
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Start dev server
npm run dev
```

## ✨ Usage

1. **Upload Invoice Excel**
   - Click "Upload" in navigation
   - Select "Invoice Excel"
   - Choose your Excel file
   - Click to upload

2. **Upload Bank Statement**
   - Click "Upload" in navigation
   - Select "Bank Statement"
   - Choose your Excel file
   - Click to upload

3. **Run Payment Matching**
   - Click "Match Payments" button
   - Wait for processing
   - Dashboard updates automatically

4. **View Analytics**
   - Check Summary Cards
   - Browse Party-wise status
   - View Monthly trends
   - Filter by party or status

## 🔗 API Endpoints

All endpoints documented in Swagger UI at: **http://localhost:8000/docs**

Key endpoints:
- `POST /api/upload/invoices` - Upload invoice file
- `POST /api/upload/bank-statements` - Upload payment file
- `POST /api/match-payments` - Run matching algorithm
- `GET /api/dashboard/summary` - Get dashboard data
- `GET /api/bills/` - List all invoices
- `GET /api/payments/` - List all payments

## 🆘 Troubleshooting

### Port Already in Use
```bash
# Change port in backend
python -m uvicorn app.main:app --port 9000

# Change port in frontend (vite.config.js)
# Modify: port: 3001
```

### MongoDB Connection Error
```bash
# Ensure MongoDB is running
# Windows:
mongod

# macOS:
brew services start mongodb-community

# Linux:
sudo systemctl start mongod

# Or use MongoDB Atlas connection string in .env
```

### Dependencies Installation Failed
```bash
# Clear cache and reinstall
pip install --no-cache-dir -r requirements.txt
npm cache clean --force && npm install
```

### Frontend Not Loading
- Check if backend is running at http://localhost:8000
- Clear browser cache (Ctrl+Shift+Del)
- Check browser console for errors (F12)

## 📞 Need Help?

1. Check API documentation: http://localhost:8000/docs
2. Review browser console (F12) for frontend errors
3. Check backend terminal for error messages
4. Verify MongoDB connection and data

## 🎯 Next Steps

- Customize the matching algorithm in `backend/app/services/matcher.py`
- Modify dashboard colors in `frontend/tailwind.config.cjs`
- Add more filters or reports to the dashboard
- Set up automated matching on a schedule
- Deploy to production

---

**Happy tracking! 🎉**
