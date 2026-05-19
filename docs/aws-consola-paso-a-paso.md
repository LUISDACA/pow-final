# AWS desde Consola y SSH

Guia breve para operar la demo final desplegada en AWS.

## 1. Datos Reales de la Demo

```text
Gateway public IP: 3.149.234.60
Gateway private IP: 10.0.1.33
API private IP: 10.0.11.168
Kafka private IP: 10.0.21.209
APP private IP: 10.0.21.138
Dominio API: https://api.fraud-log-pipeline.duckdns.org/ingest/
Dominio dashboard: https://dashboard.fraud-log-pipeline.duckdns.org/
```

## 2. Entrar al Gateway desde Windows

```powershell
ssh -i "C:\Users\luis-\Desktop\.ssh\fraud-log-key.pem" ec2-user@3.149.234.60
```

## 3. Entrar a Instancias Privadas desde Gateway

```bash
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@10.0.11.168
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@10.0.21.209
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@10.0.21.138
```

## 4. Clonar o Actualizar Repositorio

En cada instancia:

```bash
cd /opt
sudo rm -rf fraud-log-pipeline
sudo git clone https://github.com/LUISDACA/pow-final.git fraud-log-pipeline
sudo chown -R ec2-user:ec2-user fraud-log-pipeline
cd fraud-log-pipeline
```

Para actualizar:

```bash
cd /opt/fraud-log-pipeline
git pull
```

## 5. Instalar Servicios Nativos

### Kafka

```bash
export KAFKA_PRIVATE_IP="10.0.21.209"
export KAFKA_LOG_RETENTION_HOURS=24
chmod +x infra/aws/native/kafka/*.sh
infra/aws/native/kafka/install-kafka.sh
```

### APP / DB / Dashboard

```bash
export KAFKA_PRIVATE_IP="10.0.21.209"
export POSTGRES_USER="fraud_user"
export POSTGRES_PASSWORD="FraudDb_2026_Grupo4"
export JWT_SECRET_KEY="fraud-log-pipeline-jwt-secret-2026-grupo4"
export ADMIN_EMAIL="admin@example.com"
export ADMIN_PASSWORD="Admin2026Grupo4"
chmod +x infra/aws/native/app/install-app.sh
infra/aws/native/app/install-app.sh
```

### API

```bash
export KAFKA_PRIVATE_IP="10.0.21.209"
chmod +x infra/aws/native/api/install-api.sh
infra/aws/native/api/install-api.sh
```

### Gateway

```bash
export API_PRIVATE_IP="10.0.11.168"
export APP_PRIVATE_IP="10.0.21.138"
chmod +x infra/aws/native/gateway/install-gateway.sh
infra/aws/native/gateway/install-gateway.sh
```

## 6. Configurar HTTPS DuckDNS

Certificado emitido:

```text
*.fraud-log-pipeline.duckdns.org
```

Aplicar plantilla Nginx TLS:

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
```

## 7. Validar Servicios

Gateway:

```bash
sudo systemctl status nginx --no-pager
sudo systemctl status nftables --no-pager
```

API:

```bash
sudo systemctl status fraud-producer-api --no-pager
curl http://localhost:8000/
```

Kafka:

```bash
sudo systemctl status kafka --no-pager
/opt/kafka/bin/kafka-topics.sh --bootstrap-server 10.0.21.209:9092 --list
```

APP:

```bash
sudo systemctl status postgresql --no-pager
sudo systemctl status fraud-consumer --no-pager
sudo systemctl status fraud-dashboard --no-pager
curl http://localhost:3000/api/health
```

## 8. Prueba End-to-End

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

Fuerza bruta:

```powershell
$body = @{ email = "test@test.com"; password = "wrong" } | ConvertTo-Json -Compress
1..5 | ForEach-Object {
  Invoke-RestMethod -Method Post "https://api.fraud-log-pipeline.duckdns.org/ingest/auth/login" -ContentType "application/json" -Body $body
}
```

Consultar alertas:

```bash
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@10.0.21.138
sudo -u postgres psql -d fraud_logs_db -P pager=off \
  -c "SELECT alert_type, severity, ip_address, endpoint, created_at FROM fraud_alerts ORDER BY created_at DESC LIMIT 10;"
```

## 9. Dashboard

URL:

```text
https://dashboard.fraud-log-pipeline.duckdns.org/
```

Credenciales:

```text
admin@example.com
Admin2026Grupo4
```

## 10. SSL Labs

```text
https://www.ssllabs.com/ssltest/analyze.html?d=api.fraud-log-pipeline.duckdns.org
```
