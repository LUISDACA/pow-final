#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/opt/fraud-log-pipeline"
ENV_DIR="/etc/fraud-log-pipeline"

if [[ -z "${KAFKA_PRIVATE_IP:-}" ]]; then
  echo "KAFKA_PRIVATE_IP is required"
  exit 1
fi

POSTGRES_USER="${POSTGRES_USER:-fraud_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-FraudDb_2026_Grupo4}"
JWT_SECRET_KEY="${JWT_SECRET_KEY:-fraud-log-pipeline-jwt-secret-2026-grupo4}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-Admin2026Grupo4}"

sudo dnf install -y python3 python3-pip git nftables
sudo dnf install -y postgresql15-server postgresql15 || sudo dnf install -y postgresql-server postgresql

sudo systemctl daemon-reload

if ! sudo systemctl cat postgresql.service >/dev/null 2>&1; then
  echo "postgresql.service not found after install"
  exit 1
fi

if [[ ! -d /var/lib/pgsql/data/base ]]; then
  sudo postgresql-setup --initdb || true
fi

sudo systemctl enable --now postgresql

sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${POSTGRES_USER}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER ${POSTGRES_USER} WITH PASSWORD '${POSTGRES_PASSWORD}';"

sudo -u postgres psql -c "ALTER USER ${POSTGRES_USER} WITH PASSWORD '${POSTGRES_PASSWORD}';"

PG_HBA=$(sudo -u postgres psql -Atc "SHOW hba_file;")
if ! sudo grep -q '^host all all 127\.0\.0\.1/32 scram-sha-256' "$PG_HBA"; then
  sudo cp "$PG_HBA" "${PG_HBA}.bak.$(date +%Y%m%d%H%M%S)"
  sudo sed -i '1ihost all all ::1/128 scram-sha-256' "$PG_HBA"
  sudo sed -i '1ihost all all 127.0.0.1/32 scram-sha-256' "$PG_HBA"
  sudo systemctl restart postgresql
fi

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='fraud_logs_db'" | grep -q 1 || \
  sudo -u postgres createdb -O "${POSTGRES_USER}" fraud_logs_db

sudo -u postgres psql -d fraud_logs_db -f "$PROJECT_DIR/infra/postgres/init.sql"

cd "$PROJECT_DIR/fraud-consumer"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

cd "$PROJECT_DIR/dashboard"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

sudo mkdir -p "$ENV_DIR"
sudo tee "$ENV_DIR/app.env" >/dev/null <<EOF
KAFKA_BOOTSTRAP_SERVERS=${KAFKA_PRIVATE_IP}:9092
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/fraud_logs_db
JWT_SECRET_KEY=${JWT_SECRET_KEY}
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=7
ADMIN_EMAIL=${ADMIN_EMAIL}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
COOKIE_SECURE=false
EOF

sudo cp "$PROJECT_DIR/infra/aws/native/app/fraud-consumer.service" /etc/systemd/system/fraud-consumer.service
sudo cp "$PROJECT_DIR/infra/aws/native/app/fraud-dashboard.service" /etc/systemd/system/fraud-dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable --now fraud-consumer fraud-dashboard
sudo systemctl status fraud-consumer --no-pager
sudo systemctl status fraud-dashboard --no-pager
