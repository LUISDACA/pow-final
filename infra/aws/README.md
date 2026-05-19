# Infraestructura AWS

Este directorio contiene la infraestructura y los scripts usados para el despliegue final en AWS EC2 sin Docker.

## Componentes

- `cloudformation-4ec2.yml`: plantilla base para crear VPC, subnets, security groups, IAM role SSM y 4 instancias EC2.
- `env.example`: ejemplo de variables para el despliegue.
- `native/`: scripts de instalacion nativa y servicios `systemd`.

## Roles EC2

| Instancia | Rol | Componentes |
|---|---|---|
| EC2-1 | Gateway | Nginx, TLS, nftables |
| EC2-2 | API productora | FastAPI + Uvicorn |
| EC2-3 | Kafka | Apache Kafka KRaft |
| EC2-4 | Procesamiento + DB + Dashboard | PostgreSQL, consumer, dashboard |

## Despliegue Nativo

La guia principal de despliegue esta en:

- `docs/aws-consola-paso-a-paso.md`
- `docs/aws-sin-docker.md`

Scripts principales:

```text
native/gateway/install-gateway.sh
native/api/install-api.sh
native/kafka/install-kafka.sh
native/app/install-app.sh
```

Servicios `systemd`:

```text
fraud-producer-api.service
kafka.service
fraud-consumer.service
fraud-dashboard.service
nginx.service
postgresql.service
nftables.service
```

## Seguridad

La segmentacion por firewall se encuentra en:

```text
infra/nftables/
```

El Gateway usa HTTPS con certificado wildcard:

```text
*.fraud-log-pipeline.duckdns.org
```

Plantilla Nginx TLS:

```text
native/gateway/nginx-tls-duckdns.conf.template
```

## Limpieza de Costos

Si se creo la infraestructura con CloudFormation, eliminar el stack al finalizar la demo evita costos continuos:

```powershell
aws cloudformation delete-stack `
  --region us-east-2 `
  --stack-name fraud-log-pipeline
```
