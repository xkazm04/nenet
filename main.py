from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import api_router
from config.logging_config import setup_logging, get_safe_logger

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.backends.inmemory import InMemoryBackend
import redis.asyncio as redis
import os
from contextlib import asynccontextmanager

setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
)

logger = get_safe_logger(__name__)

app = FastAPI(
    title="Top50 service API",
    version="1.0.0",
)


app.include_router(
    api_router,
    prefix="",
    tags=["core"]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to Nene API"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "nene-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)