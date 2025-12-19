#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/../00_env.sh"

echo "Installing base packages..."
sudo apt-get update
sudo apt-get install -y git build-essential curl

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
  git clone "https://github.com/dddFEDDDDDDDd/solidgen.git" /opt/solidgen
fi

cd /opt/solidgen
git pull
git submodule update --init --recursive

echo "Installing TRELLIS.2 dependencies (this is GPU/CUDA heavy and may take a while)..."
echo "NOTE: This step uses upstream setup.sh (Conda). Ensure conda is available on this VM image."

if ! command -v conda >/dev/null 2>&1; then
  echo "ERROR: conda not found. Use a Deep Learning VM image with conda preinstalled, or install Miniconda."
  exit 1
fi

# Make sure "conda activate" works in non-interactive shells.
CONDA_SH=""
if [ -f "/opt/conda/etc/profile.d/conda.sh" ]; then
  # Common on Deep Learning VM images
  CONDA_SH="/opt/conda/etc/profile.d/conda.sh"
  source "$CONDA_SH"
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
  CONDA_SH="$HOME/miniconda3/etc/profile.d/conda.sh"
  source "$CONDA_SH"
fi
if [ -z "$CONDA_SH" ]; then
  echo "ERROR: Could not find conda.sh"
  exit 1
fi

# setup.sh is designed to be sourced from the TRELLIS.2 repo root.
export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}"
pushd vendor/trellis2_upstream >/dev/null
. ./setup.sh --new-env --basic --flash-attn --nvdiffrast --cumesh --o-voxel --flexgemm
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
DATABASE_URL=postgresql://${DB_USER}:${DB_PASS}@127.0.0.1:5432/${DB_NAME}
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


