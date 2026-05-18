# Despliegue EC2

## Distribucion propuesta

| Instancia | Rol | Componentes |
| --- | --- | --- |
| EC2-1 | Gateway | Nginx, TLS, rate limiting, nftables |
| EC2-2 | API productora | FastAPI producer |
| EC2-3 | Kafka | Broker Kafka |
| EC2-4 | Procesamiento + DB + Dashboard | Consumer, PostgreSQL, dashboard |

## Red sugerida

- VPC: `10.0.0.0/16`
- AZ-A publica: gateway.
- AZ-A privada: API.
- AZ-B privada: Kafka.
- AZ-B privada: consumer, dashboard y PostgreSQL.

## Orden de instalacion

1. Crear VPC, subnets, route tables y security groups con `infra/aws/cloudformation-4ec2.yml`.
2. Instalar Docker o runtimes equivalentes.
3. Configurar `nftables` por instancia desde `infra/nftables`.
4. Desplegar PostgreSQL y aplicar `infra/postgres/init.sql`.
5. Desplegar Kafka y crear topics.
6. Desplegar `producer-api`.
7. Desplegar `fraud-consumer`.
8. Desplegar `dashboard`.
9. Configurar Nginx con `infra/nginx/prod-gateway.conf`.
10. Agregar TLS wildcard con DNS-01 y validar con SSL Labs.

## Variables que deben cambiarse

- `JWT_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `ADMIN_PASSWORD`
- IPs privadas en `nftables`
- dominios en `prod-gateway.conf`
- rutas de certificados TLS

## Automatizacion incluida

Se agrego una base de despliegue en `infra/aws`:

- `cloudformation-4ec2.yml`: crea VPC, subnets publica/privadas, NAT Gateway, security groups, rol SSM y 4 EC2.
- `env.example`: variables que se copian como `.env` en las instancias.
- `remote/kafka/docker-compose.yml`: Kafka en EC2-3.
- `remote/api/docker-compose.yml`: API productora en EC2-2.
- `remote/app/docker-compose.yml`: PostgreSQL, consumer y dashboard en EC2-4.
- `remote/gateway/docker-compose.yml`: Nginx en EC2-1.
- `remote/gateway/nginx.conf.template`: plantilla Nginx con `API_PRIVATE_IP` y `APP_PRIVATE_IP`.

La maquina local aun no tiene AWS CLI instalado. Antes de crear recursos reales:

```powershell
aws --version
aws configure
aws sts get-caller-identity
```

Si prefieres hacerlo sin AWS CLI local, sigue la guia:

- [AWS desde la consola](aws-consola-paso-a-paso.md)

Crear stack:

```powershell
aws cloudformation deploy `
  --region us-east-1 `
  --stack-name fraud-log-pipeline `
  --template-file infra/aws/cloudformation-4ec2.yml `
  --capabilities CAPABILITY_NAMED_IAM `
  --parameter-overrides `
    AdminCidr=TU_IP_PUBLICA/32 `
    KeyName=TU_KEY_PAIR
```

Obtener IPs:

```powershell
aws cloudformation describe-stacks `
  --region us-east-1 `
  --stack-name fraud-log-pipeline `
  --query "Stacks[0].Outputs"
```

Eliminar stack al terminar la demo:

```powershell
aws cloudformation delete-stack `
  --region us-east-1 `
  --stack-name fraud-log-pipeline
```
