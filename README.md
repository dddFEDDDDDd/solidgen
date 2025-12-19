# Solidgen (TRELLIS.2 Platform)

Solidgen is a production-oriented platform for **image → 3D** generation built on **Microsoft TRELLIS.2**.

## Architecture (v1)
- **Web**: Next.js (Cloud Run)
- **API**: FastAPI control plane (Cloud Run)
- **GPU Worker**: long-running worker (Compute Engine GPU VM)
- **Storage**: Cloud Storage (uploads + outputs)
- **Queue**: Pub/Sub (job dispatch)
- **DB**: Cloud SQL Postgres (users, jobs, credits ledger, webhook idempotency)

```
apps/
  api/        # FastAPI control plane
  web/        # Next.js UI
  worker/     # GPU worker (TRELLIS.2 inference + GLB export)
infra/
  gcp/        # Cloud Shell runbook + deploy scripts
vendor/
  trellis2_upstream/   # git submodule: microsoft/TRELLIS.2
```

## Local dev (high level)
- The **API** and **Web** can run locally without a GPU (mocked worker / no inference).
- The **Worker** must run on Linux + NVIDIA GPU to run TRELLIS.2 and `o-voxel` post-processing.

## Deploy (GCP us-central1)
See `infra/gcp/README.md`.

