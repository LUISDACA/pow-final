# Pruebas locales

Levantar stack:

```powershell
docker compose up --build -d
```

Ver estado:

```powershell
docker compose ps
```

Probar gateway:

```powershell
Invoke-RestMethod http://localhost:8080/gateway/health
```

Probar API productora por Nginx:

```powershell
Invoke-RestMethod http://localhost:8080/ingest/
```

Generar login fallido:

```powershell
Invoke-RestMethod -Method Post http://localhost:8080/ingest/auth/login `
  -ContentType "application/json" `
  -Body '{"email":"test@test.com","password":"wrong"}'
```

Generar SQLi controlado de laboratorio:

```powershell
Invoke-RestMethod "http://localhost:8080/ingest/lab/vulnerable-search?username=demo%27%20OR%201%3D1--"
```

Consultar logs:

```powershell
docker compose exec -T postgres psql -U fraud_user -d fraud_logs_db `
  -c "SELECT event_type, ip_address, endpoint, status_code, created_at FROM access_logs ORDER BY created_at DESC LIMIT 10;"
```

Consultar alertas:

```powershell
docker compose exec -T postgres psql -U fraud_user -d fraud_logs_db `
  -c "SELECT alert_type, severity, ip_address, endpoint, created_at FROM fraud_alerts ORDER BY created_at DESC LIMIT 10;"
```
