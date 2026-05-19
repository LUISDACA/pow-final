# Arquitectura

El proyecto implementa un pipeline de logs con deteccion heuristica de fraude desplegado en AWS EC2 con servicios nativos.

## Componentes

1. **Gateway Nginx:** recibe trafico HTTPS, aplica rate limiting y enruta hacia API o dashboard.
2. **API productora FastAPI:** genera eventos de login, acceso API y pruebas SQLi de laboratorio.
3. **Kafka broker:** organiza eventos en topics por tipo.
4. **Consumer heuristico:** consume logs, detecta patrones sospechosos y guarda alertas.
5. **PostgreSQL:** persiste logs, alertas, usuarios y refresh tokens.
6. **Dashboard:** muestra eventos y alertas con JWT, refresh token, CSRF y 2FA TOTP.
7. **nftables:** protege cada instancia permitiendo solo el trafico necesario.

## Distribucion AWS

| Rol | IP privada | Servicio |
|---|---:|---|
| Gateway | `10.0.1.33` | Nginx, TLS, nftables |
| API | `10.0.11.168` | FastAPI producer |
| Kafka | `10.0.21.209` | Apache Kafka KRaft |
| APP / DB / Dashboard | `10.0.21.138` | PostgreSQL, consumer, dashboard |

## Flujo

```text
Cliente externo
    -> Gateway Nginx HTTPS
    -> API productora
    -> Kafka topics
    -> Consumer heuristico
    -> PostgreSQL
    -> Dashboard seguro
```

## Topics Kafka

- `logs.auth`
- `logs.api`
- `logs.sql_injection`
- `fraud.alerts`

## URLs principales

- API: `https://api.fraud-log-pipeline.duckdns.org/ingest/`
- Dashboard: `https://dashboard.fraud-log-pipeline.duckdns.org/`
- Health API: `https://api.fraud-log-pipeline.duckdns.org/ingest/`
- Health dashboard: `https://dashboard.fraud-log-pipeline.duckdns.org/api/health`

## Seguridad por capas

- TLS wildcard Let's Encrypt para `*.fraud-log-pipeline.duckdns.org`.
- Nginx con rate limiting para API y login del dashboard.
- nftables en cada instancia.
- Kafka no expuesto a Internet.
- PostgreSQL no expuesto a Internet.
- Dashboard con JWT, refresh token httpOnly, CSRF y TOTP.
