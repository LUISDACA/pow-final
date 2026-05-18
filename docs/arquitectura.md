# Arquitectura

El proyecto implementa un pipeline local de logs con deteccion heuristica de fraude:

1. Nginx `gateway` recibe trafico HTTP y aplica rate limiting.
2. `producer-api` genera eventos de login, acceso API y pruebas SQLi de laboratorio.
3. Kafka organiza eventos en `logs.auth`, `logs.api`, `logs.sql_injection` y `fraud.alerts`.
4. `fraud-consumer` consume eventos, guarda logs y crea alertas.
5. PostgreSQL persiste `access_logs`, `fraud_alerts`, `users` y `refresh_tokens`.
6. `dashboard` muestra logs y alertas con JWT, refresh token, CSRF y TOTP.

## Servicios locales

| Servicio | Puerto | Uso |
| --- | ---: | --- |
| gateway | 8080 | Entrada principal local |
| producer-api | 8000 | API productora directa para depuracion |
| dashboard | 3000 | Dashboard directo para depuracion |
| kafka | 9092 | Broker local |
| postgres | 5432 | Base de datos local |

## Rutas principales

- `GET /gateway/health`
- `GET /`
- `POST /api/auth/login`
- `GET /api/dashboard/summary`
- `GET /ingest/`
- `POST /ingest/auth/login`
- `GET /ingest/api/products`
- `GET /ingest/lab/vulnerable-search?username=...`
