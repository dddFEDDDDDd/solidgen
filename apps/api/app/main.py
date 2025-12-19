from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

import stripe
from fastapi import Body, Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import get_current_user, get_db
from app.gcp import get_pubsub_publisher, pubsub_topic_path, sign_gcs_download_url, sign_gcs_upload_url
from app.models import CreditLedger, Job, JobStatus, LedgerReason, User, WebhookEvent
from app.schemas import (
    AuthResponse,
    CreateJobRequest,
    CreateJobResponse,
    JobResponse,
    JobListItem,
    LoginRequest,
    ListJobsResponse,
    MeResponse,
    NowPaymentsInvoiceRequest,
    NowPaymentsInvoiceResponse,
    SignupRequest,
    SignedUploadRequest,
    SignedUploadResponse,
    StripeCheckoutRequest,
    StripeCheckoutResponse,
)
from app.security import create_access_token, hash_password, verify_password


app = FastAPI(title="solidgen-api")


def _parse_cors_origins() -> list[str]:
    if settings.cors_origins.strip() == "*":
        return ["*"]
    return [o.strip() for o in settings.cors_origins.split(",") if o.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
@app.get("/healthz")
def healthz():
    return {"ok": True, "service": "solidgen-api"}


@app.on_event("startup")
def _startup_migrate_best_effort():
    """
    Lightweight schema bootstrap to keep v1 deploys simple.
    Uses a Postgres advisory lock to avoid concurrent creates.
    """
    from app.db import engine
    from app.models import Base

    with engine.begin() as conn:
        # 64-bit lock key; any constant is fine for this DB
        got = conn.execute(text("SELECT pg_try_advisory_lock(9876543210)")).scalar()
        if got:
            Base.metadata.create_all(bind=conn)
            conn.execute(text("SELECT pg_advisory_unlock(9876543210)"))


@app.post("/v1/auth/signup", response_model=AuthResponse)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email.lower()).one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=req.email.lower(), password_hash=hash_password(req.password), credits_balance=0)
    db.add(user)
    db.commit()
    db.refresh(user)
    return AuthResponse(access_token=create_access_token(str(user.id)))


@app.post("/v1/auth/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower()).one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return AuthResponse(access_token=create_access_token(str(user.id)))


@app.get("/v1/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return MeResponse(user_id=user.id, email=user.email, credits_balance=user.credits_balance)


@app.post("/v1/uploads/sign", response_model=SignedUploadResponse)
def sign_upload(req: SignedUploadRequest, user: User = Depends(get_current_user)):
    res = sign_gcs_upload_url(content_type=req.content_type, file_ext=req.file_ext, user_id=user.id)
    return SignedUploadResponse(
        upload_url=res.url,
        gcs_uri=res.gcs_uri,
        object_name=res.object_name,
        expires_in_minutes=settings.gcs_signed_url_exp_minutes,
    )


def _cost_for_resolution(resolution: int) -> int:
    # v1 pricing knobs (tune later)
    return {512: 1, 1024: 3, 1536: 8}.get(resolution, 3)


@app.post("/v1/jobs", response_model=CreateJobResponse)
def create_job(req: CreateJobRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cost = _cost_for_resolution(req.resolution)
    if user.credits_balance < cost:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient credits")

    job_id = uuid.uuid4()
    job = Job(
        id=job_id,
        user_id=user.id,
        status=JobStatus.QUEUED,
        input_gcs_uri=req.input_gcs_uri,
        params={
            "resolution": req.resolution,
            "seed": req.seed,
            "decimation_target": req.decimation_target,
            "texture_size": req.texture_size,
        },
        cost_credits=cost,
    )

    # Atomic-ish charge + job insert
    user.credits_balance -= cost
    ledger = CreditLedger(
        user_id=user.id,
        job_id=job_id,
        delta_credits=-cost,
        reason=LedgerReason.JOB_CHARGE,
    )

    db.add(job)
    db.add(ledger)
    db.commit()
    db.refresh(job)

    publisher = get_pubsub_publisher()
    publisher.publish(pubsub_topic_path(), json.dumps({"job_id": str(job.id)}).encode("utf-8"))

    return CreateJobResponse(job_id=job.id, status=job.status.value, cost_credits=cost)


@app.get("/v1/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    download_url = None
    if job.output_gcs_uri:
        try:
            download_url = sign_gcs_download_url(gcs_uri=job.output_gcs_uri)
        except Exception:
            download_url = None

    return JobResponse(
        job_id=job.id,
        status=job.status.value,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
        input_gcs_uri=job.input_gcs_uri,
        output_gcs_uri=job.output_gcs_uri,
        output_download_url=download_url,
        error_text=job.error_text,
        cost_credits=job.cost_credits,
        params=job.params,
    )


@app.get("/v1/jobs", response_model=ListJobsResponse)
def list_jobs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    jobs = (
        db.query(Job)
        .filter(Job.user_id == user.id)
        .order_by(Job.created_at.desc())
        .limit(100)
        .all()
    )
    items = []
    for j in jobs:
        items.append(
            JobListItem(
                job_id=j.id,
                status=j.status.value,
                created_at=j.created_at.isoformat(),
                updated_at=j.updated_at.isoformat(),
                resolution=(j.params or {}).get("resolution"),
                cost_credits=j.cost_credits,
            )
        )
    return ListJobsResponse(jobs=items)


@app.post("/v1/billing/stripe/checkout-session", response_model=StripeCheckoutResponse)
def stripe_checkout(req: StripeCheckoutRequest, user: User = Depends(get_current_user)):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    stripe.api_key = settings.stripe_secret_key

    # v1: $1 per credit (tune later)
    amount_cents = int(req.credits) * 100

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"Solidgen credits ({req.credits})"},
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            }
        ],
        success_url=settings.stripe_success_url,
        cancel_url=settings.stripe_cancel_url,
        metadata={"user_id": str(user.id), "credits": str(req.credits)},
    )
    return StripeCheckoutResponse(url=session.url)


@app.post("/v1/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    if not settings.stripe_webhook_secret or not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature")

    provider = "stripe"
    event_id = event["id"]
    existing = db.query(WebhookEvent).filter(WebhookEvent.provider == provider, WebhookEvent.event_id == event_id).one_or_none()
    if existing and existing.processed_at is not None:
        return {"ok": True, "idempotent": True}

    wh = existing or WebhookEvent(provider=provider, event_id=event_id, payload=event)
    db.add(wh)
    db.commit()
    db.refresh(wh)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata") or {}
        user_id = metadata.get("user_id")
        credits = metadata.get("credits")
        if user_id and credits:
            _apply_credit_purchase(
                db=db,
                provider="stripe",
                external_id=event_id,
                user_id=uuid.UUID(user_id),
                credits=int(credits),
            )

    wh.processed_at = datetime.utcnow()
    db.add(wh)
    db.commit()
    return {"ok": True}


def _apply_credit_purchase(*, db: Session, provider: str, external_id: str, user_id: uuid.UUID, credits: int):
    user = db.query(User).filter(User.id == user_id).with_for_update().one_or_none()
    if not user:
        return

    # Idempotency for “credit add” on provider/external_id
    already = (
        db.query(CreditLedger)
        .filter(CreditLedger.provider == provider, CreditLedger.external_id == external_id)
        .one_or_none()
    )
    if already:
        return

    user.credits_balance += credits
    ledger = CreditLedger(
        user_id=user.id,
        job_id=None,
        delta_credits=credits,
        reason=LedgerReason.CREDIT_PURCHASE_STRIPE if provider == "stripe" else LedgerReason.CREDIT_PURCHASE_NOWPAYMENTS,
        provider=provider,
        external_id=external_id,
    )
    db.add(ledger)
    db.add(user)
    db.commit()


@app.post("/v1/billing/nowpayments/invoice", response_model=NowPaymentsInvoiceResponse)
def nowpayments_invoice(req: NowPaymentsInvoiceRequest, request: Request, user: User = Depends(get_current_user)):
    if not settings.nowpayments_api_key:
        raise HTTPException(status_code=500, detail="NOWPayments not configured")

    # v1: $1 per credit
    price_amount = float(req.credits)
    base_url = str(request.base_url).rstrip("/")
    payload = {
        "price_amount": price_amount,
        "price_currency": "usd",
        "pay_currency": req.pay_currency,
        "order_id": f"solidgen:{user.id}:{uuid.uuid4()}",
        "order_description": f"Solidgen credits ({req.credits})",
        "success_url": settings.stripe_success_url,
        "cancel_url": settings.stripe_cancel_url,
        "ipn_callback_url": f"{base_url}/v1/webhooks/nowpayments",
        "is_fixed_rate": True,
        "is_fee_paid_by_user": True,
        "metadata": {"user_id": str(user.id), "credits": str(req.credits)},
    }
    r = __nowpayments_post("/v1/invoice", payload)
    return NowPaymentsInvoiceResponse(invoice_url=r["invoice_url"], invoice_id=str(r["id"]))


def __nowpayments_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    import requests

    r = requests.post(
        f"https://api.nowpayments.io{path}",
        headers={"x-api-key": settings.nowpayments_api_key, "Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


@app.post("/v1/webhooks/nowpayments")
async def nowpayments_webhook(request: Request, db: Session = Depends(get_db)):
    """
    NOWPayments IPN/webhook.

    v1 behavior:
    - verify signature if ipn secret configured (best effort)
    - on confirmed/finished payment, credit user
    """
    body = await request.body()
    if settings.nowpayments_ipn_secret:
        import hmac
        import hashlib

        sig = (
            request.headers.get("x-nowpayments-sig")
            or request.headers.get("X-Nowpayments-Sig")
            or request.headers.get("x-nowpayments-signature")
            or request.headers.get("X-Nowpayments-Signature")
        )
        if not sig:
            raise HTTPException(status_code=400, detail="Missing NOWPayments signature")
        expected = hmac.new(settings.nowpayments_ipn_secret.encode("utf-8"), body, hashlib.sha512).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(status_code=400, detail="Invalid NOWPayments signature")

    data = json.loads(body.decode("utf-8"))

    provider = "nowpayments"
    event_id = str(data.get("payment_id") or data.get("invoice_id") or uuid.uuid4())

    existing = db.query(WebhookEvent).filter(WebhookEvent.provider == provider, WebhookEvent.event_id == event_id).one_or_none()
    if existing and existing.processed_at is not None:
        return {"ok": True, "idempotent": True}

    wh = existing or WebhookEvent(provider=provider, event_id=event_id, payload=data)
    db.add(wh)
    db.commit()
    db.refresh(wh)

    status_str = str(data.get("payment_status") or "").lower()
    if status_str in {"finished", "confirmed"}:
        meta = data.get("metadata") or {}
        user_id = meta.get("user_id")
        credits = meta.get("credits")
        if user_id and credits:
            _apply_credit_purchase(
                db=db,
                provider="nowpayments",
                external_id=event_id,
                user_id=uuid.UUID(user_id),
                credits=int(credits),
            )

    wh.processed_at = datetime.utcnow()
    db.add(wh)
    db.commit()
    return {"ok": True}


