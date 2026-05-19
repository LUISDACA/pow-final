# AWS Nativo con systemd

Esta guia describe el despliegue final en AWS EC2 usando servicios nativos, sin contenedores.

## Variables del Entorno

```bash
GATEWAY_PUBLIC_IP="3.149.234.60"
GATEWAY_PRIVATE_IP="10.0.1.33"
API_PRIVATE_IP="10.0.11.168"
KAFKA_PRIVATE_IP="10.0.21.209"
APP_PRIVATE_IP="10.0.21.138"
ADMIN_PUBLIC_IP="190.253.181.253"
```

## Kafka

```bash
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@10.0.21.209
cd /opt/fraud-log-pipeline
git pull
export KAFKA_PRIVATE_IP="10.0.21.209"
export KAFKA_LOG_RETENTION_HOURS=24
chmod +x infra/aws/native/kafka/*.sh
infra/aws/native/kafka/install-kafka.sh
```

Validar:

```bash
sudo systemctl status kafka --no-pager
/opt/kafka/bin/kafka-topics.sh --bootstrap-server 10.0.21.209:9092 --list
```

## APP / DB / Dashboard

```bash
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@10.0.21.138
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
sudo systemctl status postgresql --no-pager
sudo systemctl status fraud-consumer --no-pager
sudo systemctl status fraud-dashboard --no-pager
```

## API Productora

```bash
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@10.0.11.168
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

## Gateway Nginx

```bash
cd /opt/fraud-log-pipeline
git pull
export API_PRIVATE_IP="10.0.11.168"
export APP_PRIVATE_IP="10.0.21.138"
chmod +x infra/aws/native/gateway/install-gateway.sh
infra/aws/native/gateway/install-gateway.sh
```

Para TLS DuckDNS, usar:

```bash
sudo cp infra/aws/native/gateway/nginx-tls-duckdns.conf.template /etc/nginx/nginx.conf
sudo sed -i "s/API_PRIVATE_IP/10.0.11.168/g" /etc/nginx/nginx.conf
sudo sed -i "s/APP_PRIVATE_IP/10.0.21.138/g" /etc/nginx/nginx.conf
sudo nginx -t
sudo systemctl reload nginx
```

Validar:

```bash
curl -k https://api.fraud-log-pipeline.duckdns.org/ingest/
curl -k https://dashboard.fraud-log-pipeline.duckdns.org/api/health
sudo systemctl status nginx --no-pager
```

## nftables

Aplicar las plantillas por rol:

- `infra/nftables/gateway.nft`
- `infra/nftables/api.nft`
- `infra/nftables/kafka.nft`
- `infra/nftables/processing-dashboard-db.nft`

Siempre validar antes de aplicar:

```bash
sudo nft -c -f archivo.rendered.nft
sudo nft -f archivo.rendered.nft
sudo cp archivo.rendered.nft /etc/sysconfig/nftables.conf
sudo systemctl restart nftables
sudo nft list ruleset
```

## Pruebas Finales

Desde Windows:

```powershell
curl.exe "https://api.fraud-log-pipeline.duckdns.org/ingest/"
curl.exe "https://dashboard.fraud-log-pipeline.duckdns.org/api/health"
```

SQL Injection vulnerable:

```powershell
curl.exe "https://api.fraud-log-pipeline.duckdns.org/ingest/lab/vulnerable-search?username=alice%27%20UNION%20SELECT%2099,%27mallory%27,%27mallory@example.com%27,%27admin%27--"
```

SQL Injection reparado:

```powershell
curl.exe "https://api.fraud-log-pipeline.duckdns.org/ingest/lab/safe-search?username=alice%27%20UNION%20SELECT%2099,%27mallory%27,%27mallory@example.com%27,%27admin%27--"
```

Alertas:

```bash
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@10.0.21.138
sudo -u postgres psql -d fraud_logs_db -P pager=off \
  -c "SELECT alert_type, severity, ip_address, endpoint, created_at FROM fraud_alerts ORDER BY created_at DESC LIMIT 10;"
```
