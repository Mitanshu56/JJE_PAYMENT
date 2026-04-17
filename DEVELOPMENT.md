# Development and Testing Guide

## 🧪 Testing

### Backend Testing

#### Setup
```bash
cd backend
pip install pytest pytest-asyncio pytest-cov
```

#### Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_bill_controller.py

# Run verbose
pytest -v
```

#### Sample Test File (tests/test_bill_controller.py)
```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_upload_invoices():
    """Test invoice upload"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with open("sample_invoices.xlsx", "rb") as f:
            response = await client.post(
                "/api/upload/invoices",
                files={"file": f}
            )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

@pytest.mark.asyncio
async def test_get_bills():
    """Test get all bills"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/bills/")
        assert response.status_code == 200
        assert "bills" in response.json()
```

### Frontend Testing

#### Setup
```bash
cd frontend
npm install --save-dev vitest jsdom @testing-library/react @testing-library/jest-dom
```

#### Run Tests
```bash
# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Watch mode
npm test -- --watch
```

#### Sample Test File (src/components/__tests__/SummaryCards.test.jsx)
```javascript
import { render, screen } from '@testing-library/react'
import SummaryCards from '../dashboard/SummaryCards'

describe('SummaryCards', () => {
  const mockSummary = {
    total_billing: 100000,
    total_paid: 70000,
    total_pending: 30000,
    paid_percentage: 70,
    invoice_stats: {
      paid: 10,
      unpaid: 5,
      partial: 2,
      total: 17
    }
  }

  test('renders summary cards', () => {
    render(<SummaryCards summary={mockSummary} />)
    expect(screen.getByText('Total Billing')).toBeInTheDocument()
    expect(screen.getByText('Total Received')).toBeInTheDocument()
  })

  test('displays correct values', () => {
    render(<SummaryCards summary={mockSummary} />)
    expect(screen.getByText('₹100,000')).toBeInTheDocument()
  })
})
```

---

## 🔍 Code Quality

### Linting

#### Backend
```bash
cd backend
pip install flake8 black isort

# Format code
black app/

# Check imports
isort app/

# Lint
flake8 app/
```

#### Frontend
```bash
cd frontend
npm install --save-dev eslint eslint-config-react-app

# Lint
npm run lint

# Auto-fix
npx eslint . --fix
```

### Code Coverage

#### Backend
```bash
pytest --cov=app --cov-report=html
# Open htmlcov/index.html
```

#### Frontend
```bash
npm test -- --coverage
```

---

## 🐛 Debugging

### Backend Debugging

#### Using Python Debugger
```python
# In your code
import pdb; pdb.set_trace()

# Or use breakpoint() in Python 3.7+
breakpoint()
```

#### Using VS Code
1. Install Python extension
2. Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload"
      ],
      "jinja": true,
      "justMyCode": true
    }
  ]
}
```

### Frontend Debugging

#### Browser DevTools
1. Open browser (F12)
2. Go to "Console" tab
3. View network requests in "Network" tab
4. Debug JavaScript in "Sources" tab

#### VS Code Extension
1. Install "Debugger for Chrome"
2. Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "chrome",
      "request": "launch",
      "name": "Launch Chrome",
      "url": "http://localhost:3000",
      "webRoot": "${workspaceFolder}/frontend",
      "sourceMapPathOverride": {
        "${workspaceFolder}/frontend/src/*": "${webRoot}/src/*"
      }
    }
  ]
}
```

---

## 📝 Logging

### Backend Logging

```python
import logging

logger = logging.getLogger(__name__)

# Different log levels
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")
```

Configure logging in `app/core/config.py`:
```python
LOG_LEVEL=INFO  # Change to DEBUG for more verbose logging
```

### Frontend Logging

```javascript
// Console logging
console.log('Info message')
console.warn('Warning message')
console.error('Error message')

// Structure logs
console.log('API Response:', {
  status: response.status,
  data: response.data,
  timestamp: new Date().toISOString()
})
```

---

## 🔧 Common Development Tasks

### Adding a New API Endpoint

1. Create controller method in `app/controllers/`
2. Create route handler in `app/routes/`
3. Add endpoint function with proper docstring
4. Test with Swagger UI
5. Update documentation

Example:
```python
# In routes/new_routes.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/new", tags=["New"])

@router.get("/endpoint")
async def new_endpoint(db: AsyncDatabase = Depends(get_db)):
    """
    Description of what this endpoint does.
    
    Returns JSON response.
    """
    try:
        # Your logic here
        return {"status": "success", "data": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# In main.py, add:
app.include_router(new_routes.router)
```

### Adding a New Frontend Component

1. Create component file in `src/components/`
2. Import required dependencies
3. Build component with React hooks
4. Export component
5. Use in parent component

Example:
```jsx
// src/components/NewComponent.jsx
import React, { useState, useEffect } from 'react'
import { newAPI } from '../services/api'

export default function NewComponent() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const res = await newAPI.fetch()
      setData(res.data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="component">
      {loading ? <div>Loading...</div> : <div>{/* Render data */}</div>}
    </div>
  )
}
```

---

## 🚀 Performance Optimization

### Backend

1. **Database Indexing**
   - Indexes are created in `app/core/database.py`
   - Add more indexes for frequently filtered fields

2. **Pagination**
   - Use skip/limit for large datasets
   - Implement cursor-based pagination for better performance

3. **Caching**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=128)
   def expensive_operation(param):
       # Cached results
       return result
   ```

### Frontend

1. **Code Splitting**
   ```javascript
   const Dashboard = lazy(() => import('./Dashboard'))
   ```

2. **Memoization**
   ```javascript
   const MemoComponent = memo(Component)
   ```

3. **Lazy Loading Images**
   ```html
   <img loading="lazy" src="..." />
   ```

---

## 📊 Monitoring

### Application Health

1. Health check endpoint: `GET /api/health`
2. Database connectivity test
3. File upload status tracking
4. Error rate monitoring

### Performance Metrics

- API response time
- Database query time
- File upload/processing time
- Dashboard load time

### Logging Strategy

- **DEBUG**: Detailed variable values, function calls
- **INFO**: Application events, successful operations
- **WARNING**: Potential issues, deprecated usage
- **ERROR**: Recoverable errors
- **CRITICAL**: System failures

---

## 🔐 Security Testing

### Backend

```bash
# Security linting
pip install bandit
bandit -r app/
```

### Frontend

```bash
# Dependency vulnerability scanning
npm audit

# Fix vulnerabilities
npm audit fix
```

---

## 📚 Documentation

### Code Documentation

#### Backend
```python
def function_name(param1: str, param2: int) -> dict:
    """
    Brief description of what the function does.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        dict: Description of return value
        
    Raises:
        ValueError: When something is invalid
        
    Example:
        >>> function_name("test", 42)
        {'result': 'success'}
    """
    pass
```

#### Frontend
```javascript
/**
 * Component description
 * 
 * @param {Object} props - Component props
 * @param {string} props.title - Title text
 * @returns {JSX.Element} Rendered component
 * 
 * @example
 * <Component title="Example" />
 */
export default function Component({ title }) {
  return <div>{title}</div>
}
```

---

## 🛠️ Troubleshooting Development Issues

### Port Already in Use
```bash
# Find process using port
# Windows: netstat -ano | findstr :8000
# Linux: lsof -i :8000

# Kill process
# Windows: taskkill /PID <PID> /F
# Linux: kill -9 <PID>
```

### Module Import Errors
```bash
# Verify virtual environment
which python  # or 'where python' on Windows

# Reinstall packages
pip install -r requirements.txt --force-reinstall
```

### Database Connection Issues
```bash
# Test MongoDB connection
python -c "from pymongo import MongoClient; MongoClient('mongodb://localhost:27017').admin.command('ping')"
```

---

## 📋 Development Checklist

- [ ] Environment setup complete
- [ ] Virtual environment activated
- [ ] Dependencies installed
- [ ] Database connection verified
- [ ] Tests passing
- [ ] Code formatted with black/prettier
- [ ] Linting passed
- [ ] Documentation updated
- [ ] Ready for commit

---

For more help, check main README.md or API_SPECIFICATION.md
