# Fraud Log Pipeline

Pipeline de procesamiento de logs con analisis heuristico de fraude, desplegado en AWS EC2 con servicios nativos `systemd`.

## Estado Final

El proyecto esta desplegado en AWS sin Docker.

- Gateway publico con Nginx, HTTPS, rate limiting y nftables.
- API productora FastAPI en instancia privada.
- Kafka broker en instancia privada.
- PostgreSQL, consumer heuristico y dashboard en instancia privada.
- Dashboard protegido con JWT, refresh token, CSRF y 2FA TOTP.
- Certificado wildcard Let's Encrypt para `*.fraud-log-pipeline.duckdns.org`.
- SSL Labs A+ para `api.fraud-log-pipeline.duckdns.org`.

## URLs de Demo

- API: `https://api.fraud-log-pipeline.duckdns.org/ingest/`
- Dashboard: `https://dashboard.fraud-log-pipeline.duckdns.org/`
- SSL Labs: `https://www.ssllabs.com/ssltest/analyze.html?d=api.fraud-log-pipeline.duckdns.org`

## Arquitectura

| Instancia | Rol | IP |
|---|---|---|
| EC2-1 | Gateway, Nginx, TLS, nftables | `10.0.1.33` / `3.149.234.60` |
| EC2-2 | API productora FastAPI | `10.0.11.168` |
| EC2-3 | Kafka broker | `10.0.21.209` |
| EC2-4 | PostgreSQL, consumer y dashboard | `10.0.21.138` |

Flujo:

```text
Cliente externo
    -> Nginx HTTPS
    -> API productora
    -> Kafka
    -> Consumer heuristico
    -> PostgreSQL
    -> Dashboard seguro
```

## Componentes

- `producer-api/`: API FastAPI que genera logs y los publica en Kafka.
- `fraud-consumer/`: consumidor Kafka con reglas de SQLi, fuerza bruta y scraping.
- `dashboard/`: dashboard FastAPI con autenticacion, JWT, refresh token, CSRF y TOTP.
- `infra/postgres/`: esquema inicial de PostgreSQL.
- `infra/nftables/`: reglas de firewall por rol.
- `infra/aws/native/`: scripts y servicios `systemd` para AWS sin Docker.
- `infra/aws/cloudformation-4ec2.yml`: infraestructura base de 4 EC2.
- `docs/evidencias-entrega-aws.md`: informe listo para pegar capturas y pasar a Word.

## Credenciales Demo

```text
Email: admin@example.com
Password: Admin2026Grupo4
```

## Pruebas Rapidas

### API y Dashboard

```powershell
curl.exe "https://api.fraud-log-pipeline.duckdns.org/ingest/"
curl.exe "https://dashboard.fraud-log-pipeline.duckdns.org/api/health"
```

### SQL Injection Vulnerable

```powershell
curl.exe "https://api.fraud-log-pipeline.duckdns.org/ingest/lab/vulnerable-search?username=alice%27%20UNION%20SELECT%2099,%27mallory%27,%27mallory@example.com%27,%27admin%27--"
```

### SQL Injection Reparado

```powershell
curl.exe "https://api.fraud-log-pipeline.duckdns.org/ingest/lab/safe-search?username=alice%27%20UNION%20SELECT%2099,%27mallory%27,%27mallory@example.com%27,%27admin%27--"
```

### Fuerza Bruta

```powershell
$body = @{ email = "test@test.com"; password = "wrong" } | ConvertTo-Json -Compress
1..5 | ForEach-Object {
  Invoke-RestMethod -Method Post "https://api.fraud-log-pipeline.duckdns.org/ingest/auth/login" -ContentType "application/json" -Body $body
}
```

### Alertas en PostgreSQL

Desde Gateway:

```bash
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@10.0.21.138
sudo -u postgres psql -d fraud_logs_db -P pager=off \
  -c "SELECT alert_type, severity, ip_address, endpoint, created_at FROM fraud_alerts ORDER BY created_at DESC LIMIT 10;"
```

## Documentacion

- [Arquitectura](docs/arquitectura.md)
- [Seguridad](docs/seguridad.md)
- [Diagrama](docs/diagrama.md)
- [AWS desde consola](docs/aws-consola-paso-a-paso.md)
- [AWS sin Docker](docs/aws-sin-docker.md)
- [Evidencias de entrega AWS](docs/evidencias-entrega-aws.md)
- [Infraestructura AWS](infra/aws/README.md)

## Nota de TLS

El certificado wildcard fue emitido con Let's Encrypt usando DNS-01 manual sobre DuckDNS.

```text
Certificado: *.fraud-log-pipeline.duckdns.org
Ruta: /etc/letsencrypt/live/fraud-log-pipeline-wildcard/
```

La renovacion no es automatica porque se uso modo manual. Debe repetirse el proceso Certbot DNS-01 antes de la fecha de expiracion.
