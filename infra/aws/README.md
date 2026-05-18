# AWS deployment

Este directorio prepara el despliegue real en AWS con 4 EC2:

- EC2-1: gateway Nginx.
- EC2-2: producer API.
- EC2-3: Kafka.
- EC2-4: consumer, PostgreSQL y dashboard.

## Pre-requisitos

1. Instalar AWS CLI v2.
2. Configurar credenciales:

```powershell
aws configure
aws sts get-caller-identity
```

3. Tener un EC2 Key Pair creado en la region elegida.
4. Saber tu IP publica para `AdminCidr`, por ejemplo `x.x.x.x/32`.

## Crear infraestructura

Ejemplo:

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

Ver salidas:

```powershell
aws cloudformation describe-stacks `
  --region us-east-1 `
  --stack-name fraud-log-pipeline `
  --query "Stacks[0].Outputs"
```

## Desplegar servicios

Despues de crear el stack:

1. Copia el codigo de `producer-api` a la EC2 API.
2. Copia `infra/aws/remote/api/docker-compose.yml` a la EC2 API.
3. Copia `infra/aws/remote/kafka/docker-compose.yml` a la EC2 Kafka.
4. Copia `dashboard`, `fraud-consumer` e `infra/postgres/init.sql` a la EC2 App.
5. Copia `infra/aws/remote/app/docker-compose.yml` a la EC2 App.
6. Copia `infra/aws/remote/gateway/docker-compose.yml` y `nginx.conf` renderizado a la EC2 Gateway.

Las EC2 privadas se administran mejor con AWS Systems Manager Session Manager. El template ya agrega el rol `AmazonSSMManagedInstanceCore`.

## Costos

Este stack crea recursos con costo, incluyendo EC2, EBS y un NAT Gateway. Para demo corta, elimina el stack al terminar:

```powershell
aws cloudformation delete-stack `
  --region us-east-1 `
  --stack-name fraud-log-pipeline
```
