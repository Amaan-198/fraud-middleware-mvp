"""
Allianz Fraud Middleware - FastAPI Application

Main entry point for the fraud detection API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import decision

app = FastAPI(
    title="Allianz Fraud Middleware",
    description="Real-time fraud detection with sub-100ms latency",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for demo UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(decision.router, prefix="/v1", tags=["decisions"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Allianz Fraud Middleware",
        "status": "operational",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "components": {
            "api": "up",
            "rules_engine": "up",
            "ml_engine": "up",
            "policy_engine": "up"
        }
    }
