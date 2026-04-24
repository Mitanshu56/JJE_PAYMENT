"""Main FastAPI application."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings, logger
from app.core.auth import decode_token
from app.core.database import connect_db, close_db
from app.routes import auth_routes, upload_routes, bill_routes, payment_routes, dashboard_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("🚀 Starting Payment Tracking Dashboard API...")
    await connect_db()
    yield
    # Shutdown
    logger.info("🛑 Shutting down...")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Require auth token for protected API endpoints."""
    path = request.url.path

    # Let CORS preflight pass without auth header.
    if request.method == "OPTIONS":
        return await call_next(request)

    public_paths = {
        "/api/auth/login",
        "/api/auth/forgot-password",
        "/api/health",
    }

    if path.startswith("/api") and path not in public_paths:
        auth_header = request.headers.get("authorization", "")
        token = ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

        claims = decode_token(token)
        if not claims:
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})

        request.state.user = claims.get("sub")

    return await call_next(request)

# Include routers
app.include_router(auth_routes.router)
app.include_router(upload_routes.router)
app.include_router(bill_routes.router)
app.include_router(payment_routes.router)
app.include_router(dashboard_routes.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Payment Tracking Dashboard API",
        "version": settings.API_VERSION,
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
