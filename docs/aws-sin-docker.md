# AWS sin Docker

Esta guia migra el despliegue EC2 a servicios nativos con `systemd`:

- Gateway: Nginx instalado en el host.
- API: FastAPI + Python venv + Uvicorn.
- Kafka: Apache Kafka instalado en `/opt/kafka`.
- App: PostgreSQL, consumer y dashboard con servicios `systemd`.
- nftables: reglas directas sobre puertos reales, sin Docker bridge/NAT.

## Variables reales

Usa tus IPs actuales:

```bash
GATEWAY_PUBLIC_IP="3.149.234.60"
GATEWAY_PRIVATE_IP="10.0.1.33"
API_PRIVATE_IP="10.0.11.168"
KAFKA_PRIVATE_IP="10.0.21.209"
APP_PRIVATE_IP="10.0.21.138"
ADMIN_PUBLIC_IP="190.253.181.253"
```

## 1. Detener Docker antes de migrar

En cada instancia donde vas a migrar:

```bash
cd /opt/fraud-log-pipeline 2>/dev/null || true
docker compose down 2>/dev/null || true
sudo systemctl disable --now docker 2>/dev/null || true
```

En Gateway, si el compose estaba dentro de `gateway/`:

```bash
cd /opt/fraud-log-pipeline/gateway 2>/dev/null || true
docker compose down 2>/dev/null || true
sudo systemctl disable --now docker 2>/dev/null || true
```

## 2. Kafka nativo

Desde Gateway:

```bash
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@10.0.21.209
```

Dentro de Kafka:

```bash
cd /opt/fraud-log-pipeline
git pull
export KAFKA_PRIVATE_IP="10.0.21.209"
export KAFKA_LOG_RETENTION_HOURS=24
chmod +x infra/aws/native/kafka/*.sh
infra/aws/native/kafka/install-kafka.sh
```

Validar:

```bash
/opt/kafka/bin/kafka-topics.sh --bootstrap-server 10.0.21.209:9092 --list
sudo systemctl status kafka --no-pager
```

## 3. App, DB y Dashboard nativos

Desde Gateway:

```bash
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@10.0.21.138
```

Dentro de App:

```bash
cd /opt/fraud-log-pipeline
git pull
export KAFKA_PRIVATE_IP="10.0.21.209"
export POSTGRES_USER="fraud_user"
export POSTGRES_PASSWORD="FraudDb_2026_Grupo4"
export JWT_SECRET_KEY="fraud-log-pipeline-jwt-secret-2026-grupo4"
export ADMIN_EMAIL="admin@example.com"
export ADMIN_PASSWORD="Admin2026Grupo4"
chmod +x infra/aws/native/app/install-app.sh
infra/aws/native/app/install-app.sh
```

Validar:

```bash
curl http://localhost:3000/api/health
sudo systemctl status fraud-consumer --no-pager
sudo systemctl status fraud-dashboard --no-pager
sudo -u postgres psql -d fraud_logs_db -c "SELECT COUNT(*) FROM users;"
```

## 4. API nativa

Desde Gateway:

```bash
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@10.0.11.168
```

Dentro de API:

```bash
cd /opt/fraud-log-pipeline
git pull
export KAFKA_PRIVATE_IP="10.0.21.209"
chmod +x infra/aws/native/api/install-api.sh
infra/aws/native/api/install-api.sh
```

Validar:

```bash
curl http://localhost:8000/
sudo systemctl status fraud-producer-api --no-pager
```

## 5. Gateway Nginx nativo

En Gateway:

```bash
cd /opt/fraud-log-pipeline
git pull
export API_PRIVATE_IP="10.0.11.168"
export APP_PRIVATE_IP="10.0.21.138"
chmod +x infra/aws/native/gateway/install-gateway.sh
infra/aws/native/gateway/install-gateway.sh
```

Validar:

```bash
curl http://localhost/gateway/health
curl http://localhost/ingest/
sudo nginx -t
sudo systemctl status nginx --no-pager
```

Desde tu PC:

```powershell
curl.exe "http://3.149.234.60/gateway/health"
curl.exe "http://3.149.234.60/ingest/"
```

## 6. nftables sin Docker

Sin Docker, las reglas son mas simples. Puedes aplicar las plantillas actuales por rol:

- `infra/nftables/gateway.nft`
- `infra/nftables/api.nft`
- `infra/nftables/kafka.nft`
- `infra/nftables/processing-dashboard-db.nft`

Renderiza IPs antes de aplicar y valida siempre con `nft -c`:

```bash
sudo nft -c -f archivo.rendered.nft
sudo nft -f archivo.rendered.nft
sudo nft list ruleset
```

En API ya no necesitas `DOCKER-USER`; el puerto real es `8000`.

## 7. Pruebas finales

Desde tu PC:

```powershell
curl.exe "http://3.149.234.60/ingest/"
curl.exe "http://3.149.234.60/ingest/lab/vulnerable-search?username=alice%27%20UNION%20SELECT%2099,%27mallory%27,%27mallory@example.com%27,%27admin%27--"
curl.exe "http://3.149.234.60/ingest/lab/safe-search?username=alice%27%20UNION%20SELECT%2099,%27mallory%27,%27mallory@example.com%27,%27admin%27--"
```

En App:

```bash
sudo -u postgres psql -d fraud_logs_db -P pager=off \
  -c "SELECT alert_type, severity, ip_address, endpoint, created_at FROM fraud_alerts ORDER BY created_at DESC LIMIT 10;"
```
