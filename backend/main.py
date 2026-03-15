"""
Product Detective — FastAPI Backend
Main application entry point
"""
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("product_detective")

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

from api.routes import scraper, analysis, verdict, recommendations, health
from utils.database import connect_db, disconnect_db
from utils.cache import init_cache
from config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle manager."""
    logger.info("🔍 Product Detective booting up...")
    
    # Connect to DB (Resilient for first boot)
    try:
        await connect_db()
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}. Running in degraded mode.")
        
    # Init Cache (Resilient)
    try:
        await init_cache()
    except Exception as e:
        logger.error(f"❌ Cache initialization failed: {e}. Running without cache.")
        
    logger.info("✅ All systems ready. Begin investigation.")
    yield
    logger.info("🔒 Shutting down...")
    await disconnect_db()


app = FastAPI(
    title="Product Detective API",
    description="AI-Powered Purchase Decision Intelligence",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router,           prefix="/api/v1",              tags=["health"])
app.include_router(scraper.router,          prefix="/api/v1/scrape",       tags=["scraper"])
app.include_router(analysis.router,         prefix="/api/v1/analysis",     tags=["analysis"])
app.include_router(verdict.router,          prefix="/api/v1/verdict",      tags=["verdict"])
app.include_router(recommendations.router,  prefix="/api/v1/recommend",    tags=["recommendations"])


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal investigation error."})


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
