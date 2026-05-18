#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/opt/fraud-log-pipeline"

if [[ -z "${API_PRIVATE_IP:-}" || -z "${APP_PRIVATE_IP:-}" ]]; then
  echo "API_PRIVATE_IP and APP_PRIVATE_IP are required"
  exit 1
fi

sudo dnf install -y nginx nftables

sudo cp "$PROJECT_DIR/infra/aws/native/gateway/nginx.conf.template" /etc/nginx/nginx.conf
sudo sed -i "s/API_PRIVATE_IP/${API_PRIVATE_IP}/g" /etc/nginx/nginx.conf
sudo sed -i "s/APP_PRIVATE_IP/${APP_PRIVATE_IP}/g" /etc/nginx/nginx.conf

sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx
sudo systemctl status nginx --no-pager
