# AWS por consola + SSH

Esta guia explica como desplegar el proyecto en AWS usando la consola web para crear la infraestructura y SSH para instalar/levantar los servicios.

La idea es:

```text
Tu PC
  |
  | SSH
  v
EC2-1 Gateway publica
  |
  | SSH interno
  v
EC2 privadas: API, Kafka, App/DB/Dashboard
```

El gateway funciona como punto de entrada publico y tambien como bastion SSH para llegar a las instancias privadas.

## 0. Archivos importantes

| Archivo | Uso |
| --- | --- |
| `infra/aws/cloudformation-4ec2.yml` | Crea VPC, subnets, NAT, security groups y 4 EC2 |
| `infra/aws/env.example` | Variables base para AWS |
| `infra/aws/remote/kafka/docker-compose.yml` | Compose para EC2 Kafka |
| `infra/aws/remote/api/docker-compose.yml` | Compose para EC2 API |
| `infra/aws/remote/app/docker-compose.yml` | Compose para EC2 App/DB/Dashboard |
| `infra/aws/remote/gateway/docker-compose.yml` | Compose para EC2 Gateway |
| `infra/aws/remote/gateway/nginx.conf.template` | Nginx para conectar Gateway con API y Dashboard |

## 1. Crear Key Pair para SSH

En AWS Console:

1. Entra a **EC2**.
2. Ve a **Network & Security > Key Pairs**.
3. Click en **Create key pair**.
4. Nombre sugerido:

```text
fraud-log-key
```

5. Tipo: `RSA`.
6. Formato:
   - `.pem` si usaras PowerShell, Git Bash, Linux o macOS.
   - `.ppk` si usaras PuTTY.
7. Descarga y guarda el archivo.

Ruta local recomendada en Windows:

```text
C:\Users\TU_USUARIO\.ssh\fraud-log-key.pem
```

En PowerShell, restringe permisos del archivo:

```powershell
icacls "$env:USERPROFILE\.ssh\fraud-log-key.pem" /inheritance:r
icacls "$env:USERPROFILE\.ssh\fraud-log-key.pem" /grant:r "$env:USERNAME:R"
```

## 2. Crear infraestructura con CloudFormation

En AWS Console:

1. Entra a **CloudFormation**.
2. Click en **Create stack**.
3. Elige **With new resources**.
4. En la pantalla **Prerequisite - Prepare template**, marca:

```text
Choose an existing template
```

No uses `Build from Infrastructure Composer` para este proyecto, porque ya tenemos el template YAML listo.

5. En **Specify template**, selecciona:

```text
Upload a template file
```

6. Sube:

```text
infra/aws/cloudformation-4ec2.yml
```

7. Click en **Next**.
8. Stack name:

```text
fraud-log-pipeline
```

9. Parameters:

| Parametro | Valor |
| --- | --- |
| `AdminCidr` | Tu IP publica con `/32`, por ejemplo `190.10.20.30/32` |
| `KeyName` | `fraud-log-key` o el nombre de tu key pair |
| `GatewayInstanceType` | `t3.micro` para demo |
| `ApiInstanceType` | `t3.micro` para demo |
| `KafkaInstanceType` | `t3.small` recomendado |
| `AppInstanceType` | `t3.small` recomendado |

Para ver tu IP publica, abre en el navegador:

```text
https://checkip.amazonaws.com/
```

10. En la pantalla final, marca la casilla de IAM capabilities.
11. Click en **Submit**.
12. Espera hasta `CREATE_COMPLETE`.

## 3. Copiar IPs del stack

En CloudFormation:

1. Abre el stack `fraud-log-pipeline`.
2. Ve a **Outputs**.
3. Copia:

```text
GatewayPublicIp
GatewayPrivateIp
ApiPrivateIp
KafkaPrivateIp
AppPrivateIp
```

Ejemplo ficticio:

```text
GatewayPublicIp = 54.10.20.30
GatewayPrivateIp = 10.0.1.50
ApiPrivateIp = 10.0.11.25
KafkaPrivateIp = 10.0.21.33
AppPrivateIp = 10.0.21.44
```

## 4. Habilitar SSH desde Gateway hacia privadas

El template permite SSH publico solo al gateway. Las EC2 privadas no tienen IP publica.

Para conectarte a privadas por SSH necesitas usar el gateway como bastion.

Antes de correr comandos desde PowerShell, define la IP publica real del gateway. Reemplaza el valor de ejemplo por `GatewayPublicIp` de CloudFormation:

```powershell
$GATEWAY_PUBLIC_IP = "PEGAR_GatewayPublicIp_AQUI"
```

Ejemplo:

```powershell
$GATEWAY_PUBLIC_IP = "3.145.20.30"
```

### Opcion A: reenviar la llave al gateway

Desde tu PC:

```powershell
scp -i "$env:USERPROFILE\.ssh\fraud-log-key.pem" `
  "$env:USERPROFILE\.ssh\fraud-log-key.pem" `
  ec2-user@${GATEWAY_PUBLIC_IP}:/home/ec2-user/fraud-log-key.pem
```

Luego entra al gateway:

```powershell
ssh -i "$env:USERPROFILE\.ssh\fraud-log-key.pem" ec2-user@$GATEWAY_PUBLIC_IP
```

Dentro del gateway:

```bash
chmod 400 /home/ec2-user/fraud-log-key.pem
```

Define las IPs privadas reales usando los outputs de CloudFormation. Reemplaza estos valores por tus outputs:

```bash
API_PRIVATE_IP="PEGAR_ApiPrivateIp"
KAFKA_PRIVATE_IP="PEGAR_KafkaPrivateIp"
APP_PRIVATE_IP="PEGAR_AppPrivateIp"
```

Ejemplo:

```bash
API_PRIVATE_IP="10.0.11.25"
KAFKA_PRIVATE_IP="10.0.21.33"
APP_PRIVATE_IP="10.0.21.44"
```

Conectar a una instancia privada:

```bash
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@$API_PRIVATE_IP
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@$KAFKA_PRIVATE_IP
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@$APP_PRIVATE_IP
```

Importante: esos tres comandos se ejecutan desde el gateway. Si el prompt ya dice algo como:

```text
[ec2-user@ip-10-0-11-168 ~]$
```

entonces ya estas dentro de la EC2 API. Para volver al gateway:

```bash
exit
```

El prompt del gateway en este despliegue se parece a:

```text
[ec2-user@ip-10-0-1-33 ~]$
```

No intentes entrar desde API hacia API usando la llave del gateway; esa llave solo fue copiada al gateway.

### Opcion B: ProxyJump desde tu PC

No copias la llave al gateway. Usas el gateway como salto.

Estos comandos son para PowerShell en tu PC, no para ejecutarlos dentro del gateway Linux:

```powershell
ssh -i "$env:USERPROFILE\.ssh\fraud-log-key.pem" `
  -J ec2-user@$GATEWAY_PUBLIC_IP `
  ec2-user@API_PRIVATE_IP
```

Para Kafka:

```powershell
ssh -i "$env:USERPROFILE\.ssh\fraud-log-key.pem" `
  -J ec2-user@$GATEWAY_PUBLIC_IP `
  ec2-user@KAFKA_PRIVATE_IP
```

Para App:

```powershell
ssh -i "$env:USERPROFILE\.ssh\fraud-log-key.pem" `
  -J ec2-user@$GATEWAY_PUBLIC_IP `
  ec2-user@APP_PRIVATE_IP
```

Si `ProxyJump` falla en PowerShell, usa la opcion A.

Si ya estas dentro del gateway, no uses `C:\...`, no uses `-J` y no uses backticks de PowerShell. Desde el gateway usa Bash asi:

```bash
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@$API_PRIVATE_IP
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@$KAFKA_PRIVATE_IP
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@$APP_PRIVATE_IP
```

## 5. Verificar security groups para SSH interno

El template ya deja SSH publico solo al gateway y SSH interno desde el security group del gateway hacia API, Kafka y App.

Si algo falla, verifica esto en la consola:

1. En AWS Console entra a **EC2 > Security Groups**.
2. Busca:
   - `fraud-log-pipeline-api-sg`
   - `fraud-log-pipeline-kafka-sg`
   - `fraud-log-pipeline-app-sg`
3. En cada uno, agrega inbound rule:
3. Debe existir una inbound rule:

```text
Type: SSH
Port: 22
Source: fraud-log-pipeline-gateway-sg
```

No pongas `0.0.0.0/0` en las privadas.

## 6. Subir el codigo a las EC2

Tienes dos caminos. El mas simple para clase es GitHub.

### Opcion recomendada: GitHub

1. Sube este proyecto a GitHub.
2. En cada EC2:

```bash
cd /opt
sudo rm -rf fraud-log-pipeline
sudo git clone https://github.com/LUISDACA/pow-final.git fraud-log-pipeline
sudo chown -R ec2-user:ec2-user fraud-log-pipeline
cd fraud-log-pipeline
```

Si el repo es privado, puedes:

- Usar HTTPS con token personal.
- Usar SSH deploy key.
- Subir un `.zip` manual.

### Opcion alternativa: SCP desde tu PC al gateway

Desde tu PC, comprime el proyecto:

```powershell
Compress-Archive -Path .\* -DestinationPath .\fraud-log-pipeline.zip -Force
```

Sube al gateway:

```powershell
scp -i "$env:USERPROFILE\.ssh\fraud-log-key.pem" `
  .\fraud-log-pipeline.zip `
  ec2-user@${GATEWAY_PUBLIC_IP}:/home/ec2-user/
```

En el gateway:

```bash
sudo dnf install -y unzip
mkdir -p /opt/fraud-log-pipeline
unzip -o /home/ec2-user/fraud-log-pipeline.zip -d /opt/fraud-log-pipeline
sudo chown -R ec2-user:ec2-user /opt/fraud-log-pipeline
```

Para pasar el zip a privadas desde gateway:

```bash
scp -i /home/ec2-user/fraud-log-key.pem /home/ec2-user/fraud-log-pipeline.zip ec2-user@${API_PRIVATE_IP}:/home/ec2-user/
scp -i /home/ec2-user/fraud-log-key.pem /home/ec2-user/fraud-log-pipeline.zip ec2-user@${KAFKA_PRIVATE_IP}:/home/ec2-user/
scp -i /home/ec2-user/fraud-log-key.pem /home/ec2-user/fraud-log-pipeline.zip ec2-user@${APP_PRIVATE_IP}:/home/ec2-user/
```

En cada privada:

```bash
sudo dnf install -y unzip
sudo rm -rf /opt/fraud-log-pipeline
sudo mkdir -p /opt/fraud-log-pipeline
sudo unzip -o /home/ec2-user/fraud-log-pipeline.zip -d /opt/fraud-log-pipeline
sudo chown -R ec2-user:ec2-user /opt/fraud-log-pipeline
```

## 7. Crear `.env` en cada EC2

En cada EC2, dentro de `/opt/fraud-log-pipeline`, crea `.env`.

Usa las IPs reales del stack:

```bash
cd /opt/fraud-log-pipeline
cat > .env <<'EOF'
POSTGRES_USER=fraud_user
POSTGRES_PASSWORD=CAMBIA_ESTA_PASSWORD
KAFKA_LOG_RETENTION_HOURS=24

JWT_SECRET_KEY=CAMBIA_ESTE_SECRETO_LARGO
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=7
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=CAMBIA_ESTA_PASSWORD_ADMIN
COOKIE_SECURE=false

KAFKA_PRIVATE_IP=PEGAR_KafkaPrivateIp
APP_PRIVATE_IP=PEGAR_AppPrivateIp
API_PRIVATE_IP=PEGAR_ApiPrivateIp
EOF
```

Importante:

- Usa la misma `POSTGRES_PASSWORD` en EC2 App y API si la API llegara a usar DB luego.
- Usa la misma `KAFKA_PRIVATE_IP` en API y App.
- Para HTTP sin TLS, deja `COOKIE_SECURE=false`.
- Cuando tengas HTTPS real, cambia a `COOKIE_SECURE=true`.

## 8. Desplegar Kafka en EC2-3

Conectate a `fraud-log-pipeline-kafka`.

Haz el SSH primero y espera a ver el prompt de Kafka antes de pegar comandos de instalacion. No pegues el bloque completo junto con el `ssh`; si respondes `no` al mensaje de autenticidad del host, los comandos siguientes se ejecutaran en la maquina donde estabas antes.

Desde el gateway:

```bash
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@$KAFKA_PRIVATE_IP
```

Cuando pregunte:

```text
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

responde:

```text
yes
```

Confirma que el prompt sea parecido a:

```text
[ec2-user@ip-10-0-21-209 ~]$
```

Luego ejecuta:

```bash
cd /opt
sudo rm -rf fraud-log-pipeline
sudo git clone https://github.com/LUISDACA/pow-final.git fraud-log-pipeline
sudo chown -R ec2-user:ec2-user fraud-log-pipeline
cd fraud-log-pipeline
cat > .env <<'EOF'
KAFKA_PRIVATE_IP=10.0.21.209
KAFKA_LOG_RETENTION_HOURS=24
EOF
cp infra/aws/remote/kafka/docker-compose.yml docker-compose.yml
docker compose up -d
docker compose ps
```

Ver topics:

```bash
docker exec -it fraud_kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server $KAFKA_PRIVATE_IP:9092 \
  --list
```

Debe mostrar:

```text
fraud.alerts
logs.api
logs.auth
logs.sql_injection
```

## 9. Desplegar App + DB + Dashboard en EC2-4

Conectate a `fraud-log-pipeline-app`.

```bash
cd /opt/fraud-log-pipeline
cp infra/aws/remote/app/docker-compose.yml docker-compose.yml
docker compose up --build -d
docker compose ps
```

Probar dashboard desde la propia EC2 App:

```bash
curl http://localhost:3000/api/health
```

Probar PostgreSQL:

```bash
docker exec -it fraud_postgres psql -U fraud_user -d fraud_logs_db \
  -c "SELECT COUNT(*) FROM users;"
```

## 10. Desplegar API en EC2-2

Conectate a `fraud-log-pipeline-api`.

```bash
cd /opt/fraud-log-pipeline
cp infra/aws/remote/api/docker-compose.yml docker-compose.yml
docker compose up --build -d
docker compose ps
```

Probar API desde la propia EC2 API:

```bash
curl http://localhost:8000/
```

Debe responder:

```json
{"status":"ok","service":"producer-api"}
```

## 11. Desplegar Gateway en EC2-1

Conectate a `fraud-log-pipeline-gateway`.

```bash
cd /opt/fraud-log-pipeline
mkdir -p gateway
cp infra/aws/remote/gateway/docker-compose.yml gateway/docker-compose.yml
cp infra/aws/remote/gateway/nginx.conf.template gateway/nginx.conf
```

Reemplaza IPs:

```bash
sed -i "s/API_PRIVATE_IP/PEGAR_ApiPrivateIp/g" gateway/nginx.conf
sed -i "s/APP_PRIVATE_IP/PEGAR_AppPrivateIp/g" gateway/nginx.conf
```

Levanta gateway:

```bash
cd gateway
docker compose up -d
docker compose ps
docker exec -it fraud_gateway nginx -t
```

## 12. Probar desde tu navegador

Health:

```text
http://GATEWAY_PUBLIC_IP/gateway/health
```

Dashboard:

```text
http://GATEWAY_PUBLIC_IP/
```

API:

```text
http://GATEWAY_PUBLIC_IP/ingest/
```

## 13. Generar eventos de fraude

Desde tu PC:

```powershell
curl.exe -X POST http://GATEWAY_PUBLIC_IP/ingest/auth/login `
  -H "Content-Type: application/json" `
  -d "{\"email\":\"test@test.com\",\"password\":\"wrong\"}"
```

Repite 5 veces para fuerza bruta.

SQLi controlado:

```powershell
curl.exe "http://GATEWAY_PUBLIC_IP/ingest/lab/vulnerable-search?username=demo%27%20OR%201%3D1--"
```

En EC2 App:

```bash
docker exec -it fraud_postgres psql -U fraud_user -d fraud_logs_db \
  -c "SELECT alert_type, severity, ip_address, endpoint, created_at FROM fraud_alerts ORDER BY created_at DESC LIMIT 10;"
```

## 14. Aplicar nftables

Primero reemplaza IPs en las plantillas de `infra/nftables`.

Ejemplo en Gateway:

```bash
cd /opt/fraud-log-pipeline/infra/nftables
cp gateway.nft gateway.rendered.nft
sed -i "s/203.0.113.10/TU_IP_PUBLICA/g" gateway.rendered.nft
sed -i "s/10.0.1.20/PEGAR_ApiPrivateIp/g" gateway.rendered.nft
sed -i "s/10.0.2.40/PEGAR_AppPrivateIp/g" gateway.rendered.nft
sudo nft -c -f gateway.rendered.nft
sudo nft -f gateway.rendered.nft
```

Hazlo solo cuando SSH y servicios ya funcionen. Mantente conectado mientras aplicas reglas.

## 15. Apagar y evitar costos

Cuando termines la demo:

1. Entra a **CloudFormation**.
2. Selecciona `fraud-log-pipeline`.
3. Click en **Delete**.
4. Espera `DELETE_COMPLETE`.

Luego revisa manualmente:

- EC2 apagadas/eliminadas.
- NAT Gateway eliminado.
- Elastic IP liberada.
- Volumenes EBS eliminados.
- Buckets S3 temporales eliminados.

## Problemas comunes

### Windows dice `Load key ... Permission denied`

Esto significa que OpenSSH no puede leer el archivo `.pem` local. No es un error de AWS todavia.

Abre PowerShell como administrador y ejecuta:

```powershell
takeown /F "$env:USERPROFILE\.ssh\fraud-log-key.pem"
icacls "$env:USERPROFILE\.ssh\fraud-log-key.pem" /inheritance:r
icacls "$env:USERPROFILE\.ssh\fraud-log-key.pem" /grant:r "$($env:USERNAME):R"
```

Luego prueba:

```powershell
ssh -i "$env:USERPROFILE\.ssh\fraud-log-key.pem" ec2-user@$GATEWAY_PUBLIC_IP
```

Si despues de eso el error cambia a solo `Permission denied (publickey...)`, entonces la llave no corresponde al Key Pair usado por la EC2 o el usuario no es `ec2-user`.

### No puedo entrar por SSH al gateway

Revisa:

- `AdminCidr` debe ser tu IP publica actual con `/32`.
- Security group del gateway debe permitir puerto 22 desde tu IP.
- La llave `.pem` debe corresponder al Key Pair usado.
- Usuario correcto para Amazon Linux 2023: `ec2-user`.

### No puedo entrar a privadas

Revisa:

- Agregaste inbound SSH desde `gateway-sg` a `api-sg`, `kafka-sg` y `app-sg`.
- Estas usando `ProxyJump` o conectandote desde el gateway.
- Las privadas no tienen IP publica; eso es correcto.

### Docker no existe

El UserData instala Docker. Espera 2 a 5 minutos despues de crear la EC2.

Verifica:

```bash
docker --version
docker compose version
```

### La API no llega a Kafka

Revisa:

- `KAFKA_PRIVATE_IP` correcto en `.env`.
- Security group Kafka permite 9092 desde `api-sg`.
- Kafka esta corriendo.

### El gateway da 502

Revisa:

- `gateway/nginx.conf` tiene `ApiPrivateIp` y `AppPrivateIp` reales.
- API responde en EC2 API: `curl http://localhost:8000/`.
- Dashboard responde en EC2 App: `curl http://localhost:3000/api/health`.
