"""
Main FastAPI application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings, logger
from app.core.database import connect_db, close_db
from app.routes import upload_routes, bill_routes, payment_routes, dashboard_routes


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

# Include routers
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
