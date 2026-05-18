#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/opt/fraud-log-pipeline"
ENV_DIR="/etc/fraud-log-pipeline"

if [[ -z "${KAFKA_PRIVATE_IP:-}" ]]; then
  echo "KAFKA_PRIVATE_IP is required"
  exit 1
fi

sudo dnf install -y python3 python3-pip git nftables

cd "$PROJECT_DIR/producer-api"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

sudo mkdir -p "$ENV_DIR"
sudo tee "$ENV_DIR/api.env" >/dev/null <<EOF
KAFKA_BOOTSTRAP_SERVERS=${KAFKA_PRIVATE_IP}:9092
EOF

sudo cp "$PROJECT_DIR/infra/aws/native/api/fraud-producer-api.service" /etc/systemd/system/fraud-producer-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now fraud-producer-api
sudo systemctl status fraud-producer-api --no-pager
