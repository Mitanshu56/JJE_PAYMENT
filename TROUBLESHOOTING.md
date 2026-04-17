# Payment Tracking Dashboard - Troubleshooting Guide

## 🔧 Common Issues and Solutions

---

## 1. Setup & Installation Issues

### Issue: Python not found / "python is not recognized"

**Error Message:**
```
'python' is not recognized as an internal or external command
```

**Solution (Windows):**
1. Ensure Python is installed: `python --version`
2. If not, download from https://www.python.org/
3. **Important**: Check "Add Python to PATH" during installation
4. Restart PowerShell/CMD after installation
5. Verify: `python --version`

**Solution (macOS/Linux):**
```bash
# Check if Python 3 is installed
python3 --version

# If not, install via Homebrew (macOS)
brew install python3

# Create alias for convenience
alias python=python3
```

---

### Issue: npm or Node not found

**Error Message:**
```
'npm' is not recognized / npm: command not found
```

**Solution:**
1. Download Node.js from https://nodejs.org/
2. Choose LTS (Long Term Support) version
3. Install with npm included
4. Restart terminal
5. Verify: `node --version` and `npm --version`

---

### Issue: Virtual environment not activating

**Problem:**
```
# Windows
.\venv\Scripts\activate  # Doesn't work

# macOS/Linux
source venv/bin/activate  # Doesn't work
```

**Solution (Windows - PowerShell):**
```powershell
# If you get execution policy error
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then activate
.\venv\Scripts\Activate.ps1
```

**Alternative (Windows - Command Prompt):**
```cmd
.\venv\Scripts\activate.bat
```

---

### Issue: "No such file or directory" during setup

**Error Message:**
```
No such file or directory: 'setup.sh'
```

**Solution:**
1. Ensure you're in the correct directory:
```bash
cd ~/Desktop/"JJE PAYMENT"
# OR
cd C:\Users\kevin\OneDrive\Desktop\"JJE PAYMENT"
```

2. Make setup.sh executable:
```bash
chmod +x setup.sh
./setup.sh
```

---

## 2. Backend Issues

### Issue: Port 8000 already in use

**Error Message:**
```
Address already in use / OSError: [Errno 48] Address already in use
```

**Solution:**

**Windows:**
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with actual number)
taskkill /PID 12345 /F

# Or use different port
python -m uvicorn app.main:app --port 9000
```

**macOS/Linux:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use different port
python -m uvicorn app.main:app --port 9000
```

---

### Issue: MongoDB connection failed

**Error Message:**
```
ServerSelectionTimeoutError: [Errno 111] Connection refused
```

**Causes & Solutions:**

**1. MongoDB not running:**
```bash
# Check if MongoDB is running
# Windows: Look for mongod.exe in Services
# macOS: brew services list
# Linux: sudo systemctl status mongod

# Start MongoDB
# Windows: Search "Services" and start MongoDB
# macOS: brew services start mongodb-community
# Linux: sudo systemctl start mongod
```

**2. Connection string incorrect:**
Check `.env` file:
```env
# Default local
MONGODB_URL=mongodb://localhost:27017

# MongoDB Atlas (cloud)
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/database?retryWrites=true
```

**3. MongoDB version incompatibility:**
```bash
# Check MongoDB version
mongod --version

# Update if needed
# Windows: Download from mongodb.com
# macOS: brew upgrade mongodb-community
# Linux: sudo apt-get upgrade mongodb
```

---

### Issue: Import errors in Python

**Error Message:**
```
ModuleNotFoundError: No module named 'fastapi'
ImportError: cannot import name 'Motor'
```

**Solution:**
```bash
# Activate virtual environment
# Windows
.\venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt --force-reinstall

# Check installation
pip list | grep fastapi
```

---

### Issue: "app.main:app" not found

**Error Message:**
```
No module named 'app.main' / No application instance found
```

**Solution:**
1. Ensure you're in the `backend` directory:
```bash
pwd  # Should show .../backend
cd backend  # If not there
```

2. Verify file structure:
```bash
# backend/app/main.py should exist
ls app/main.py  # macOS/Linux
dir app\main.py  # Windows
```

3. Run from correct directory:
```bash
python -m uvicorn app.main:app --reload
```

---

### Issue: CORS errors in browser

**Error Message:**
```
Access to XMLHttpRequest at 'http://localhost:8000/api/...' from origin 
'http://localhost:3000' has been blocked by CORS policy
```

**Solution:**

The backend should have CORS enabled by default. Verify in `app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (development only)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

For production, restrict origins:
```python
allow_origins=[
    "https://yourdomain.com",
    "https://www.yourdomain.com"
]
```

---

### Issue: File upload fails

**Error Message:**
```
413 Payload Too Large
413 Request Entity Too Large
```

**Solution:**
1. Check max file size in `.env`:
```env
MAX_UPLOAD_SIZE=52428800  # 50MB in bytes
```

2. Increase if needed:
```env
MAX_UPLOAD_SIZE=104857600  # 100MB
```

3. Restart backend for changes to take effect

---

## 3. Frontend Issues

### Issue: Port 3000 already in use

**Error Message:**
```
Port 3000 is in use. Trying alternative port.
(Vite will try 3001, 3002, etc.)
```

**Solution:**
```bash
cd frontend

# Use different port
npm run dev -- --port 5173

# Or kill the process using port 3000
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# macOS/Linux
lsof -i :3000
kill -9 <PID>
```

---

### Issue: npm packages not installed

**Error Message:**
```
Cannot find module 'react' / react is not installed
```

**Solution:**
```bash
cd frontend

# Remove old node_modules (if corrupted)
rm -rf node_modules package-lock.json  # macOS/Linux
rmdir /s node_modules  # Windows

# Reinstall
npm install

# Verify
npm list react
```

---

### Issue: "Cannot GET /" or blank page

**Problem:**
Dashboard shows blank or error page

**Solution:**
1. Check browser console (F12) for errors
2. Check that backend is running:
```bash
curl http://localhost:8000/api/health
# Should return: {"status": "healthy"}
```

3. Check API connection:
   - Open http://localhost:3000
   - Open DevTools (F12)
   - Network tab
   - Try a button action
   - Look for failed API requests

4. If API calls fail:
   - Backend may not be running
   - Port may have changed
   - Check frontend `.env` or API configuration

---

### Issue: Webpack/Vite build error

**Error Message:**
```
[plugin:vite:import-analysis] Failed to parse source map
```

**Solution:**
```bash
cd frontend

# Clear cache
rm -rf node_modules .vite  # macOS/Linux
rmdir /s node_modules .vite  # Windows

# Reinstall and rebuild
npm install
npm run build
```

---

## 4. Docker Issues

### Issue: Docker daemon not running

**Error Message:**
```
Cannot connect to the Docker daemon
docker: error during connect
```

**Solution:**

**Windows:**
1. Install Docker Desktop from https://www.docker.com/products/docker-desktop
2. Launch "Docker Desktop" application
3. Wait for it to fully start

**macOS:**
```bash
# Start Docker
open /Applications/Docker.app

# Or via Homebrew
brew install docker
```

**Linux:**
```bash
# Start Docker daemon
sudo systemctl start docker

# Enable auto-start
sudo systemctl enable docker
```

---

### Issue: Docker image build fails

**Error Message:**
```
docker: no such file or directory
ERROR: Service 'backend' failed to build
```

**Solution:**
```bash
# Ensure Docker is running
docker ps

# Try building again
docker-compose build --no-cache

# If still fails, check Dockerfile
docker build -t payment-backend ./backend
```

---

### Issue: Container exits immediately

**Problem:**
```
docker-compose up → Container starts then stops
```

**Solution:**
```bash
# Check logs
docker-compose logs backend
docker-compose logs frontend

# Check specific errors
docker logs <container_id>

# Rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up
```

---

### Issue: Cannot connect to MongoDB in Docker

**Error Message:**
```
ServerSelectionTimeoutError: [Errno 111] Connection refused
```

**Solution:**
1. Ensure MongoDB container is running:
```bash
docker-compose ps
# Should show 'mongodb' in UP state
```

2. Check MongoDB connection string in `.env`:
```env
# In container, use service name (not localhost)
MONGODB_URL=mongodb://mongodb:27017
```

3. Restart containers:
```bash
docker-compose down
docker-compose up -d
docker-compose logs -f
```

---

## 5. Database Issues

### Issue: "Cannot find database" error

**Error Message:**
```
MongoServerError: no namespace
E11000: duplicate key error
```

**Solution:**
1. Check database name in `.env`:
```env
MONGODB_DB_NAME=payment_tracking
```

2. Database creates automatically on first write

3. Verify connection:
```bash
mongosh "mongodb://localhost:27017"
show databases
use payment_tracking
show collections
```

---

### Issue: Duplicate key error on upload

**Error Message:**
```
E11000 duplicate key error collection
```

**Cause:**
Trying to insert bill/payment with same invoice_no/payment_id

**Solution:**
1. Check if data already exists:
```bash
# View existing data
db.bills.find({invoice_no: "INV001"})

# Delete if needed
db.bills.deleteOne({invoice_no: "INV001"})
```

2. Ensure files don't have duplicate entries

3. Clear database and start fresh:
```bash
# Drop collections
db.bills.drop()
db.payments.drop()
```

---

### Issue: Out of memory error

**Error Message:**
```
MongoMemoryError / out of memory
```

**Solution:**
1. Reduce batch size in code
2. Clear old upload logs:
```bash
db.upload_logs.deleteMany({
    created_at: {$lt: new Date(Date.now() - 30*24*60*60*1000)}
})
```

3. Increase MongoDB memory limit
4. Consider data archival strategy

---

## 6. Payment Matching Issues

### Issue: No payments matching

**Problem:**
"Match Payments" completes but shows no matches

**Causes & Solutions:**

**1. Matching thresholds too strict:**
```env
# Try loosening these in .env
FUZZY_MATCH_THRESHOLD=80      # Lower from 90
DATE_PROXIMITY_DAYS=7         # Increase from 3
AMOUNT_TOLERANCE_PERCENT=0.5  # Increase from 0.1
```

**2. Data format issues:**
- Party names must be similar enough
- Amounts must match (or be within tolerance)
- Dates must be within window

**3. Debug matching:**
```python
# Check matching scores in backend logs
# Look for matching logic in app/services/matcher.py
```

**Example for debugging:**
```bash
# Enable debug logging
LOG_LEVEL=DEBUG python -m uvicorn app.main:app --reload
```

---

### Issue: Too many false matches

**Problem:**
Unrelated bills are matching

**Solution:**
Tighten matching parameters:
```env
FUZZY_MATCH_THRESHOLD=90      # Increase from 80
DATE_PROXIMITY_DAYS=3         # Decrease from 7
AMOUNT_TOLERANCE_PERCENT=0.1  # Decrease from 0.5
```

---

## 7. Excel Upload Issues

### Issue: "Invalid file" or "File not supported"

**Error Message:**
```
File must be in Excel format (.xlsx or .xls)
```

**Solutions:**
1. Ensure file is .xlsx or .xls format
2. Save from Excel (not PDF or CSV)
3. Check file size < MAX_UPLOAD_SIZE
4. File must have valid Excel structure

---

### Issue: "No data extracted"

**Problem:**
File uploads but no data is parsed

**Causes & Solutions:**

**1. Wrong invoice format:**
The parser expects label-based format:
```
Invoice No: INV001
Party Name: ABC Company
Amount: 10000
```

Not column-based:
```
| Invoice No | Party Name | Amount |
```

**2. Check invoice structure:**
- Include labels like "Invoice No:", "Party Name:", etc.
- Or see `backend/app/utils/excel_parser.py` for pattern matching

**3. Try sample files:**
- Create test Excel with clear labels
- Run through parser
- Check logs for extraction details

---

### Issue: Parser crashes on specific file

**Error Message:**
```
ValueError / KeyError / IndexError during parsing
```

**Solution:**
1. Enable debug logging:
```env
LOG_LEVEL=DEBUG
```

2. Check file format:
   - No merged cells
   - No images or embedded objects
   - Standard fonts
   - Valid date formats

3. Simplify file structure if possible

4. Report file to developers if issue persists

---

## 8. Performance Issues

### Issue: Slow dashboard loading

**Causes & Solutions:**

**1. Large dataset:**
- Implement pagination
- Filter by date range
- Archive old data

**2. Slow queries:**
- Add database indexes:
```bash
db.bills.createIndex({party_name: 1})
db.payments.createIndex({party_name: 1})
```

**3. Network latency:**
- Check browser Network tab
- Monitor backend response times
- Consider caching

---

### Issue: Slow file upload

**Causes & Solutions:**

**1. Large file:**
- Split into smaller files
- Increase timeout settings

**2. Parser performance:**
- Optimize Excel file structure
- Reduce number of sheets
- Ensure data is clean

**3. Database performance:**
- Check MongoDB is not indexing during upload
- Ensure sufficient disk space
- Check RAM usage

---

## 9. API Issues

### Issue: API endpoint returns 404

**Error Message:**
```
404 Not Found
```

**Solution:**
1. Check API is running on correct port:
```bash
curl http://localhost:8000/api/health
```

2. Verify endpoint path:
   - Check `API_SPECIFICATION.md` for correct path
   - Ensure method (GET/POST) is correct

3. Check route is registered in `app/main.py`

---

### Issue: API returns 500 error

**Error Message:**
```
500 Internal Server Error
```

**Solution:**
1. Check backend logs for error details
2. Enable debug logging:
```env
DEBUG=True
LOG_LEVEL=DEBUG
```

3. Restart backend
4. Test with Swagger UI: http://localhost:8000/docs

---

### Issue: Authentication errors

**Problem:**
API returns 401 Unauthorized

**Solution:**
(Authentication not implemented in v1.0)
Future enhancement: Add JWT tokens

---

## 10. General Troubleshooting

### Checklist for Most Issues

- [ ] Is backend running on port 8000?
- [ ] Is frontend running on port 3000?
- [ ] Is MongoDB running?
- [ ] Are ports not already in use?
- [ ] Are environment variables correct?
- [ ] Are virtual environments activated?
- [ ] Are dependencies installed?
- [ ] Are file paths correct?
- [ ] Is internet connection working?
- [ ] Are there any error logs?

---

### Useful Debugging Commands

**Backend:**
```bash
# Check if running
curl http://localhost:8000/api/health

# See all logs
docker-compose logs backend

# Follow logs in real-time
docker-compose logs -f backend

# Restart service
docker-compose restart backend
```

**Frontend:**
```bash
# Check if running
curl http://localhost:3000

# See all logs
docker-compose logs frontend

# Clear cache
rm -rf .vite build node_modules
```

**Database:**
```bash
# Connect to MongoDB
mongosh

# Show databases
show databases

# Use database
use payment_tracking

# Show collections
show collections

# View data
db.bills.find()
```

---

### Getting Help

1. **Check logs:**
   ```bash
   docker-compose logs --tail=50
   ```

2. **Review documentation:**
   - README.md
   - API_SPECIFICATION.md
   - DEVELOPMENT.md

3. **Check configuration:**
   - .env file
   - CONFIGURATION.md

4. **Test individually:**
   - Backend: http://localhost:8000/docs
   - Frontend: http://localhost:3000
   - Database: mongosh

5. **Enable debug mode:**
   ```env
   DEBUG=True
   LOG_LEVEL=DEBUG
   ```

---

### Emergency Reset

If something is very broken:

```bash
# Stop everything
docker-compose down

# Remove containers and volumes
docker-compose down -v

# Clean up
rm -rf backend/venv frontend/node_modules
rm backend/.env

# Start fresh
cp backend/.env.example backend/.env
./setup.sh  # or setup.bat

# Run again
docker-compose up
```

---

## 📞 Still Need Help?

1. **Check** all documentation files (README.md, etc.)
2. **Search** this file for your error message
3. **Enable** debug logging and check error details
4. **Try** the emergency reset above
5. **Review** configuration in CONFIGURATION.md

---

**Version**: 1.0.0
**Last Updated**: 2024

---

*For detailed debugging, check the relevant section above. Most issues have a simple solution!*
