# Seguridad

## Autenticacion del dashboard

- Access token JWT de corta duracion.
- Refresh token en cookie `httpOnly`.
- Rotacion de refresh token en cada renovacion.
- CSRF con cookie legible por frontend y header `X-CSRF-Token`.
- 2FA TOTP con QR para apps autenticadoras.

## Perimetro local

Nginx aplica:

- Rate limit general para `/ingest/`.
- Rate limit mas estricto para `/api/auth/login`.
- Reenvio de `X-Forwarded-For` para registrar IP real en logs.

## Perimetro EC2

Las plantillas de `infra/nftables` separan permisos por rol:

- Gateway: solo 80/443 publico y SSH desde IP admin.
- API: solo recibe HTTP desde gateway.
- Kafka: solo recibe 9092 desde API y consumer.
- Procesamiento/dashboard/DB: dashboard solo desde gateway, PostgreSQL local.

Kafka y PostgreSQL no deben exponerse a Internet.
