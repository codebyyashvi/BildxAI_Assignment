import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.routes import router as api_router
from app.core.config import settings
from app.core.exceptions import AdGenException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("bildx-adgen")

app = FastAPI(
    title="Bildx AI - AI Image-Ad Generator API",
    description="Grounded AI ad copy and visual composition generator with predictable concurrency and reliability.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Safe global exception handling - prevents credential & stack trace exposure
@app.exception_handler(AdGenException)
async def adgen_exception_handler(request: Request, exc: AdGenException):
    logger.warning(f"AdGenException caught [{exc.status_code}]: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception during request {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    # Mask internal configuration & stack traces
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."}
    )

# Include API routes under /api
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {
        "service": "Bildx AI Image-Ad Generator",
        "status": "online",
        "docs": "/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
