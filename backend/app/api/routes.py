from typing import List, Optional
from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import FileResponse
from app.schemas.generation import (
    GenerationRequest,
    GenerationResponse,
    ProductContext
)
from app.services.orchestrator import orchestrator
from app.core.exceptions import (
    CapacityExceededError,
    GenerationNotFoundError,
    PermanentError
)
from app.core.config import settings

router = APIRouter()

# Fictional sample products for 1-click marketer testing
SAMPLE_PRODUCTS = [
    {
        "product_name": "ROAM Lock 750",
        "image_url": "https://bildx.ai/samples/assets/roam-front.webp",
        "product_description": "A 750 ml insulated steel tumbler with a locking sip lid.",
        "target_audience": "Commuters, gym users and day hikers",
        "key_benefits": [
            "Up to 12 hours cold",
            "Carry loop",
            "Locking lid"
        ],
        "tone": "Adventurous and practical"
    },
    {
        "product_name": "Aura Glow Lamp",
        "image_url": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=800&auto=format&fit=crop&q=80",
        "product_description": "Sculptural ambient desk lamp with warm brass accents and dimmable circadian LED lighting.",
        "target_audience": "Remote professionals, architects and interior enthusiasts",
        "key_benefits": [
            "Warm circadian glow",
            "Solid machined brass",
            "Touch dimmer control"
        ],
        "tone": "Sophisticated and calming"
    },
    {
        "product_name": "Zenith Trail Runner",
        "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800&auto=format&fit=crop&q=80",
        "product_description": "Ultra-lightweight all-terrain trail running shoes with responsive grip lugs and breathable mesh.",
        "target_audience": "Marathoners, trail runners and fitness athletes",
        "key_benefits": [
            "Vibram high-traction outsole",
            "Water-repellent mesh",
            "Zero heel friction"
        ],
        "tone": "Energetic and relentless"
    }
]

@router.post(
    "/generations",
    response_model=GenerationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create Ad Generation",
    description="Enqueue a new image ad generation task. Returns 202 Accepted with tracking ID."
)
async def create_ad_generation(
    request: GenerationRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    key = idempotency_key or request.idempotency_key

    try:
        context = ProductContext(
            image_url=request.image_url,
            product_name=request.product_name,
            product_description=request.product_description,
            target_audience=request.target_audience,
            key_benefits=request.key_benefits,
            tone=request.tone
        )
        record = await orchestrator.create_generation(context, idempotency_key=key)

        image_url = f"/api/generations/{record.id}/image" if record.image_relative_path else None

        return GenerationResponse(
            id=record.id,
            status=record.status,
            created_at=record.created_at,
            creative_output=record.creative_output,
            image_url=image_url,
            metadata=record.metadata,
            error_message=record.error_message
        )
    except CapacityExceededError as ce:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ce.message
        )
    except PermanentError as pe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=pe.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue generation task."
        )

@router.get(
    "/generations/{generation_id}",
    response_model=GenerationResponse,
    summary="Get Generation Status & Result"
)
async def get_generation_status(generation_id: str):
    try:
        record = orchestrator.get_generation(generation_id)
        image_url = f"/api/generations/{record.id}/image" if record.image_relative_path else None

        return GenerationResponse(
            id=record.id,
            status=record.status,
            created_at=record.created_at,
            creative_output=record.creative_output,
            image_url=image_url,
            metadata=record.metadata,
            error_message=record.error_message
        )
    except GenerationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation '{generation_id}' not found."
        )

@router.get(
    "/generations/{generation_id}/image",
    summary="Download Completed Ad Image"
)
async def download_ad_image(generation_id: str):
    try:
        record = orchestrator.get_generation(generation_id)
        if not record.image_relative_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ad image is not ready or generation failed."
            )

        file_path = settings.STORAGE_DIR / record.image_relative_path
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ad image file was not found on disk."
            )

        clean_name = "".join(c for c in record.context.product_name if c.isalnum() or c in ("-", "_")).rstrip()
        filename = f"{clean_name or 'product'}_ad.png"

        return FileResponse(
            path=file_path,
            media_type="image/png",
            filename=filename,
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f'inline; filename="{filename}"'
            }
        )
    except GenerationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation '{generation_id}' not found."
        )

@router.get("/samples", summary="Get Pre-configured Sample Products")
async def get_samples():
    return SAMPLE_PRODUCTS

@router.get("/health", summary="Health Check & System Metrics")
async def health_check():
    return {
        "status": "healthy",
        "provider": settings.AI_PROVIDER,
        "concurrency_limit": settings.MAX_CONCURRENT_GENERATIONS,
        "max_queue_size": settings.MAX_QUEUE_SIZE,
        "active_provider_calls": orchestrator.active_provider_calls,
        "pending_count": orchestrator.pending_count,
        "total_records": len(orchestrator.records)
    }
