from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, field_validator

class GenerationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"

class ProductContext(BaseModel):
    image_url: str = Field(..., description="Public product image URL")
    product_name: str = Field(..., min_length=1, max_length=100, description="Product Name")
    product_description: str = Field(..., min_length=5, max_length=1000, description="Product Description")
    target_audience: str = Field(..., min_length=2, max_length=200, description="Target Audience")
    key_benefits: List[str] = Field(..., min_items=1, max_items=10, description="List of key product benefits")
    tone: str = Field(..., min_length=2, max_length=100, description="Desired advertising tone")

    @field_validator("key_benefits")
    @classmethod
    def validate_benefits(cls, v: List[str]) -> List[str]:
        cleaned = [b.strip() for b in v if b and b.strip()]
        if not cleaned:
            raise ValueError("At least one non-empty key benefit must be provided.")
        return cleaned

class GenerationRequest(ProductContext):
    idempotency_key: Optional[str] = Field(None, max_length=128, description="Unique client key to prevent duplicate work")

class CreativeOutput(BaseModel):
    headline: str = Field(..., description="Compelling headline (up to 8 words)")
    supporting_text: str = Field(..., description="Supporting descriptive text (up to 20 words)")
    cta: str = Field(..., description="Call to action (up to 4 words)")
    visual_direction: str = Field(..., description="Visual styling direction for the ad composition")

    @field_validator("headline")
    @classmethod
    def validate_headline_length(cls, v: str) -> str:
        words = v.strip().split()
        if len(words) > 8:
            raise ValueError(f"Headline must be at most 8 words, but received {len(words)}: '{v}'")
        return v.strip()

    @field_validator("supporting_text")
    @classmethod
    def validate_supporting_length(cls, v: str) -> str:
        words = v.strip().split()
        if len(words) > 20:
            raise ValueError(f"Supporting text must be at most 20 words, but received {len(words)}: '{v}'")
        return v.strip()

    @field_validator("cta")
    @classmethod
    def validate_cta_length(cls, v: str) -> str:
        words = v.strip().split()
        if len(words) > 4:
            raise ValueError(f"CTA must be at most 4 words, but received {len(words)}: '{v}'")
        return v.strip()

class GenerationMetadata(BaseModel):
    model: str
    prompt_version: str
    source_url: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    execution_time_ms: Optional[float] = None
    idempotency_key: Optional[str] = None

class GenerationRecord(BaseModel):
    id: str
    status: GenerationStatus
    context: ProductContext
    created_at: datetime
    updated_at: datetime
    creative_output: Optional[CreativeOutput] = None
    image_relative_path: Optional[str] = None
    metadata: Optional[GenerationMetadata] = None
    error_message: Optional[str] = None

class GenerationResponse(BaseModel):
    id: str
    status: GenerationStatus
    created_at: datetime
    creative_output: Optional[CreativeOutput] = None
    image_url: Optional[str] = None
    metadata: Optional[GenerationMetadata] = None
    error_message: Optional[str] = None
