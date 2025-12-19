from __future__ import annotations

import uuid
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    user_id: uuid.UUID
    email: EmailStr
    credits_balance: int


class SignedUploadRequest(BaseModel):
    content_type: Literal["image/png", "image/jpeg", "image/webp"]
    file_ext: Literal["png", "jpg", "jpeg", "webp"]


class SignedUploadResponse(BaseModel):
    upload_url: str
    gcs_uri: str
    object_name: str
    expires_in_minutes: int


class CreateJobRequest(BaseModel):
    input_gcs_uri: str
    resolution: Literal[512, 1024, 1536] = 1024
    seed: int = 0
    decimation_target: int = 500_000
    texture_size: int = 2048


class CreateJobResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    cost_credits: int


class JobResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    created_at: str
    updated_at: str
    input_gcs_uri: str
    output_gcs_uri: Optional[str] = None
    output_download_url: Optional[str] = None
    error_text: Optional[str] = None
    cost_credits: int
    params: dict


class JobListItem(BaseModel):
    job_id: uuid.UUID
    status: str
    created_at: str
    updated_at: str
    resolution: int | None = None
    cost_credits: int


class ListJobsResponse(BaseModel):
    jobs: list[JobListItem]


class StripeCheckoutRequest(BaseModel):
    credits: int = Field(gt=0, le=100000)


class StripeCheckoutResponse(BaseModel):
    url: str


class NowPaymentsInvoiceRequest(BaseModel):
    credits: int = Field(gt=0, le=100000)
    pay_currency: str = "usdt"


class NowPaymentsInvoiceResponse(BaseModel):
    invoice_url: str
    invoice_id: str


