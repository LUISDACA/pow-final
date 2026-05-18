# Fraud Log Pipeline

Pipeline local de procesamiento de logs con deteccion heuristica de fraude.

## Componentes

- Nginx gateway con rate limiting.
- FastAPI producer API.
- Kafka en modo KRaft.
- Consumer Python con reglas SQLi, fuerza bruta y scraping.
- PostgreSQL.
- Dashboard con JWT, refresh token, CSRF y TOTP.

## Inicio rapido

```powershell
docker compose up --build -d
```

Abrir:

- Gateway y dashboard: http://localhost:8080/
- API productora via gateway: http://localhost:8080/ingest/
- Gateway health: http://localhost:8080/gateway/health

Credenciales demo:

- Email: `admin@example.com`
- Password: `Admin123`

## Pruebas utiles

```powershell
Invoke-RestMethod http://localhost:8080/gateway/health
Invoke-RestMethod http://localhost:8080/ingest/
```

```powershell
Invoke-RestMethod -Method Post http://localhost:8080/ingest/auth/login `
  -ContentType "application/json" `
  -Body '{"email":"test@test.com","password":"wrong"}'
```

```powershell
Invoke-RestMethod "http://localhost:8080/ingest/lab/vulnerable-search?username=demo%27%20OR%201%3D1--"
```

## Documentacion

- [Arquitectura](docs/arquitectura.md)
- [Seguridad](docs/seguridad.md)
- [Pruebas locales](docs/pruebas-locales.md)
- [Despliegue EC2](docs/despliegue-ec2.md)
- [Evidencias](docs/evidencias.md)
- [Diagrama](docs/diagrama.md)
- [AWS](infra/aws/README.md)
- [AWS desde consola](docs/aws-consola-paso-a-paso.md)
- [AWS sin Docker](docs/aws-sin-docker.md)
