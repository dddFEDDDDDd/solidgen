#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/../00_env.sh"

echo "Installing base packages..."
sudo apt-get update
sudo apt-get install -y git build-essential curl pkg-config libjpeg-dev zlib1g-dev libpng-dev

echo "Installing Cloud SQL Auth Proxy..."
sudo mkdir -p /usr/local/bin
if ! command -v cloud-sql-proxy >/dev/null 2>&1; then
  curl -o cloud-sql-proxy -L "https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.11.0/cloud-sql-proxy.linux.amd64"
  chmod +x cloud-sql-proxy
  sudo mv cloud-sql-proxy /usr/local/bin/cloud-sql-proxy
fi

echo "Cloning solidgen repo (if needed)..."
if [ ! -d "/opt/solidgen/.git" ]; then
  sudo mkdir -p /opt/solidgen
  sudo chown -R "$USER":"$USER" /opt/solidgen
  git clone "https://github.com/dddFEDDDDDd/solidgen.git" /opt/solidgen
fi

cd /opt/solidgen
git pull
git submodule update --init --recursive

echo "Installing TRELLIS.2 dependencies (this is GPU/CUDA heavy and may take a while)..."
echo "NOTE: This step uses upstream setup.sh (Conda). Ensure conda is available on this VM image."

CONDA_SH=""

# Make sure "conda activate" works in non-interactive shells.
if [ -f "/opt/conda/etc/profile.d/conda.sh" ]; then
  # Common on Deep Learning VM images
  CONDA_SH="/opt/conda/etc/profile.d/conda.sh"
  # shellcheck disable=SC1090
  source "$CONDA_SH"
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
  CONDA_SH="$HOME/miniconda3/etc/profile.d/conda.sh"
  # shellcheck disable=SC1090
  source "$CONDA_SH"
fi

if ! command -v conda >/dev/null 2>&1; then
  echo "Conda not found. Installing Miniconda..."
  MINICONDA_DIR="${SOLIDGEN_MINICONDA_DIR:-$HOME/miniconda3}"
  if [ ! -d "$MINICONDA_DIR" ]; then
    curl -fsSL "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh" -o /tmp/miniconda.sh
    bash /tmp/miniconda.sh -b -p "$MINICONDA_DIR"
  fi
  CONDA_SH="$MINICONDA_DIR/etc/profile.d/conda.sh"
  # shellcheck disable=SC1090
  source "$CONDA_SH"
fi

if [ -z "$CONDA_SH" ] || ! command -v conda >/dev/null 2>&1; then
  echo "ERROR: conda not found. Install conda (Miniconda) and try again."
  exit 1
fi

# setup.sh is designed to be sourced from the TRELLIS.2 repo root.
# NOTE: Upstream installs PyTorch cu124, so prefer a CUDA 12.4 toolkit if present.
if [ -z "${CUDA_HOME:-}" ]; then
  if [ -d "/usr/local/cuda-12.4" ]; then
    CUDA_HOME="/usr/local/cuda-12.4"
  else
    CUDA_HOME="/usr/local/cuda"
  fi
fi
export CUDA_HOME
export PATH="$CUDA_HOME/bin:$PATH"

# Make reruns idempotent: upstream uses /tmp/extensions and doesn't clean up.
sudo rm -rf \
  /tmp/extensions/nvdiffrast \
  /tmp/extensions/CuMesh \
  /tmp/extensions/FlexGEMM \
  /tmp/extensions/o-voxel \
  /tmp/extensions/nvdiffrec \
  /tmp/extensions/flash-attention \
  2>/dev/null || true

pushd vendor/trellis2_upstream >/dev/null
# NOTE:
# - flash-attn 2.x does NOT support older GPUs like Tesla P100 (sm60).
# - flexgemm is optional; keep it opt-in to avoid build surprises on older GPUs.
ENV_NAME="${SOLIDGEN_CONDA_ENV_NAME:-trellis2}"
SETUP_ARGS=(--basic --nvdiffrast --cumesh --o-voxel)

if conda env list | awk '{print $1}' | grep -Fxq "$ENV_NAME"; then
  echo "Conda env '$ENV_NAME' already exists; reusing."
  conda activate "$ENV_NAME"
else
  SETUP_ARGS=(--new-env "${SETUP_ARGS[@]}")
fi

if [ "${SOLIDGEN_ENABLE_FLASH_ATTN:-0}" = "1" ]; then
  SETUP_ARGS+=(--flash-attn)
fi
if [ "${SOLIDGEN_ENABLE_FLEXGEMM:-0}" = "1" ]; then
  SETUP_ARGS+=(--flexgemm)
fi
echo "Running TRELLIS.2 setup: ${SETUP_ARGS[*]}"
. ./setup.sh "${SETUP_ARGS[@]}"
popd >/dev/null

echo "Installing worker Python deps into the trellis2 conda env..."
conda activate trellis2
pip install --upgrade pip
pip install -r /opt/solidgen/apps/worker/requirements.txt

echo "Creating systemd services..."
CLOUDSQL_CONN_NAME="${PROJECT_ID}:${REGION}:${CLOUDSQL_INSTANCE}"

echo -n "Enter DB password for user '$DB_USER' (you can copy it from Secret Manager): "
read -r -s DB_PASS
echo

sudo tee /etc/systemd/system/cloud-sql-proxy.service >/dev/null <<EOF
[Unit]
Description=Cloud SQL Auth Proxy
After=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/cloud-sql-proxy --port 5432 ${CLOUDSQL_CONN_NAME}
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

sudo mkdir -p /etc/solidgen
sudo tee /etc/solidgen/worker.env >/dev/null <<EOF
PYTHONPATH=/opt/solidgen/apps/worker
SOLIDGEN_REPO_ROOT=/opt/solidgen
GCP_PROJECT_ID=${PROJECT_ID}
PUBSUB_SUBSCRIPTION=${PUBSUB_SUBSCRIPTION}
GCS_BUCKET=${GCS_BUCKET}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASS}
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=${DB_NAME}
DATABASE_URL=postgresql://${DB_USER}:${DB_PASS}@127.0.0.1:5432/${DB_NAME}
# Default to DINOv3 (HF gated); override with TRELLIS_IMAGE_MODEL_* and set HF token via service drop-in.
TRELLIS_IMAGE_MODEL_ID=facebook/dinov3-vitl16-pretrain-lvd1689m
TRELLIS_IMAGE_MODEL_KIND=dinov3
EOF

sudo tee /etc/systemd/system/solidgen-worker.service >/dev/null <<EOF
[Unit]
Description=Solidgen GPU worker
After=network-online.target cloud-sql-proxy.service
Requires=cloud-sql-proxy.service

[Service]
Type=simple
WorkingDirectory=/opt/solidgen
EnvironmentFile=/etc/solidgen/worker.env
ExecStart=/bin/bash -lc "source ${CONDA_SH} && conda activate trellis2 && python -m solidgen_worker.main"
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now cloud-sql-proxy.service
sudo systemctl enable --now solidgen-worker.service

echo "Worker setup complete."
sudo systemctl status solidgen-worker.service --no-pager -l || true


