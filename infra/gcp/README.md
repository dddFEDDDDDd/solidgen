# GCP deploy (Cloud Shell) — Solidgen v1

Target project: `solidgen-481701` (region `us-central1`).

## 0) One-time: clone + init submodules
```bash
git clone https://github.com/dddFEDDDDDDDd/solidgen.git
cd solidgen
git submodule update --init --recursive
```

## 1) Bootstrap GCP resources
```bash
cd infra/gcp
bash 01_bootstrap.sh
```

## 2) Deploy Cloud Run services (API + Web)
```bash
bash 02_deploy_api.sh
bash 03_deploy_web.sh
```

## 3) Create GPU worker VM and start worker
```bash
bash 04_create_worker_vm.sh
```

Notes:
- The scripts are designed to be **safe to re-run**.
- You will be prompted to set a few secrets (Stripe/NOWPayments/JWT) unless already present.




