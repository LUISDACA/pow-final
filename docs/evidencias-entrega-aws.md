# Pipeline de Procesamiento de Logs con Analisis de Fraude

## Informe de Evidencias de Implementacion en AWS

**Proyecto:** Pipeline de Procesamiento de Logs con Analisis de Fraude  
**Grupo:** 4  
**Plataforma:** AWS EC2  
**Dominio:** `fraud-log-pipeline.duckdns.org`  
**API:** `https://api.fraud-log-pipeline.duckdns.org/ingest/`  
**Dashboard:** `https://dashboard.fraud-log-pipeline.duckdns.org/`  
**Fecha:** 2026  

---

## Instrucciones para completar el documento

Este documento esta preparado para copiarse a Microsoft Word o Google Docs. En cada seccion se indica la evidencia requerida, el comando usado y el resultado esperado.

Para completar la entrega:

1. Ejecutar el comando indicado.
2. Tomar captura de pantalla del resultado.
3. Pegar la imagen debajo del bloque marcado como **Figura**.
4. Mantener el texto explicativo debajo de cada imagen.

> Nota: los comandos estan escritos para la demo desplegada en AWS. Algunos comandos se ejecutan desde Windows PowerShell y otros desde las instancias EC2 por SSH.

---

## Tabla de Contenido

1. Objetivo del proyecto  
2. Arquitectura implementada en AWS  
3. Inventario de instancias EC2  
4. Evidencias de Gateway, Nginx y HTTPS  
5. Evidencias de Kafka  
6. Evidencias de PostgreSQL, consumer y dashboard  
7. Evidencias de nftables  
8. Evidencias de SQL Injection vulnerable y reparado  
9. Evidencias de fuerza bruta  
10. Evidencias de almacenamiento de alertas  
11. Evidencias de dashboard seguro  
12. Evidencias de JWT, refresh token y CSRF  
13. Evidencias de 2FA TOTP con QR  
14. Evidencias de TLS y SSL Labs  
15. Prueba end-to-end  
16. Conclusiones  
17. Anexos  

---

# 1. Objetivo del Proyecto

El objetivo del proyecto es construir un pipeline seguro de procesamiento de logs en tiempo real. Las aplicaciones web generan eventos de acceso y los envian a Kafka. Posteriormente, un consumidor analiza los logs usando reglas heuristicas para detectar intentos de SQL Injection, fuerza bruta y scraping. Las alertas se almacenan en PostgreSQL y se visualizan mediante un dashboard protegido con JWT, refresh token en cookie httpOnly, CSRF y autenticacion 2FA TOTP.

Adicionalmente, la arquitectura se protege mediante Nginx, TLS, nftables y reglas de limitacion de solicitudes.

---

# 2. Arquitectura Implementada en AWS

La solucion se desplego en AWS EC2 usando cuatro instancias con responsabilidades separadas:

| Instancia | Rol | Componentes |
|---|---|---|
| EC2-1 | Gateway / seguridad perimetral | Nginx, TLS, rate limiting, nftables |
| EC2-2 | API productora | FastAPI, endpoints de login, SQLi lab, envio a Kafka |
| EC2-3 | Kafka broker | Apache Kafka en modo KRaft, topics y retencion |
| EC2-4 | Procesamiento, DB y dashboard | Consumer heuristico, PostgreSQL, dashboard seguro |

El flujo general es:

```text
Usuario / atacante simulado
        |
        v
Gateway Nginx + TLS + nftables
        |
        v
API productora FastAPI
        |
        v
Kafka topics
        |
        v
Consumer heuristico
        |
        v
PostgreSQL
        |
        v
Dashboard seguro
```

---

# 3. Inventario de Instancias EC2

| Rol | IP privada | IP publica | Servicio principal |
|---|---:|---:|---|
| Gateway | `10.0.1.33` | `3.149.234.60` | Nginx HTTPS |
| API | `10.0.11.168` | No publica | FastAPI producer |
| Kafka | `10.0.21.209` | No publica | Apache Kafka |
| APP / DB / Dashboard | `10.0.21.138` | No publica | PostgreSQL, consumer, dashboard |

**Evidencia requerida:** vista de AWS EC2 mostrando las cuatro instancias, sus nombres, estado `Running`, IP privada y, en el Gateway, IP publica.

**Figura 1. Instancias EC2 desplegadas en AWS**

Pegar captura aqui:


**Descripcion:** En la figura se observan las cuatro instancias EC2 usadas para separar la arquitectura por roles. Solo el Gateway expone IP publica; las demas instancias se mantienen privadas.

---

# 4. Evidencias de Gateway, Nginx y HTTPS

## 4.1 Validacion del Gateway

**Comandos ejecutados en Gateway:**

```bash
curl http://localhost/gateway/health
curl http://localhost/ingest/
curl http://localhost/api/health
sudo systemctl status nginx --no-pager
```

**Resultado esperado:**

```text
{"status":"ok","service":"gateway"}
{"status":"ok","service":"producer-api"}
{"status":"ok","service":"dashboard"}
nginx active (running)
```

**Figura 2. Gateway Nginx respondiendo y enroutando hacia API y dashboard**

Pegar captura aqui:


**Descripcion:** Esta evidencia demuestra que el Gateway recibe las solicitudes y las enruta correctamente hacia la API productora y el dashboard.

## 4.2 Validacion HTTPS por Dominio

**Comandos ejecutados desde Windows PowerShell:**

```powershell
curl.exe "https://api.fraud-log-pipeline.duckdns.org/ingest/"
curl.exe "https://dashboard.fraud-log-pipeline.duckdns.org/api/health"
```

**Resultado esperado:**

```text
producer-api OK
dashboard OK
```

**Figura 3. Validacion HTTPS de API y dashboard**

Pegar captura aqui:


**Descripcion:** La figura demuestra que los servicios son accesibles mediante HTTPS usando subdominios protegidos por certificado wildcard.

---

# 5. Evidencias de Kafka

Kafka se instalo de forma nativa en la instancia `10.0.21.209`, sin Docker, usando Apache Kafka en modo KRaft.

**Comandos ejecutados desde Gateway:**

```bash
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@10.0.21.209
sudo systemctl status kafka --no-pager
/opt/kafka/bin/kafka-topics.sh --bootstrap-server 10.0.21.209:9092 --list
```

**Topics esperados:**

```text
fraud.alerts
logs.api
logs.auth
logs.sql_injection
```

**Figura 4. Kafka activo y topics creados**

Pegar captura aqui:


**Descripcion:** La evidencia muestra que Kafka esta activo y que los topics se encuentran separados por tipo de evento. Esto permite procesar eventos de autenticacion, API y SQL Injection de forma independiente.

---

# 6. Evidencias de PostgreSQL, Consumer y Dashboard

La instancia APP/DB/Dashboard contiene PostgreSQL, el consumer heuristico y el dashboard.

**Comandos ejecutados en `10.0.21.138`:**

```bash
sudo systemctl status postgresql --no-pager
sudo systemctl status fraud-consumer --no-pager
sudo systemctl status fraud-dashboard --no-pager
curl http://localhost:3000/api/health
```

**Resultado esperado:**

```text
postgresql active (running)
fraud-consumer active (running)
fraud-dashboard active (running)
{"status":"ok","service":"dashboard"}
```

**Figura 5. PostgreSQL, consumer y dashboard activos**

Pegar captura aqui:


**Descripcion:** Esta evidencia confirma que la base de datos, el consumidor de eventos y el dashboard se ejecutan como servicios nativos de `systemd`.

---

# 7. Evidencias de nftables

nftables se configuro en cada instancia para permitir solo el trafico necesario y aplicar rate limiting en accesos sensibles.

## 7.1 nftables en Gateway

**Comandos:**

```bash
sudo systemctl status nftables --no-pager
sudo nft list ruleset
```

**Reglas esperadas:**

```text
80/443 permitidos desde Internet
SSH 22 permitido solo desde IP administradora con limit rate 4/minute
Politica por defecto drop
```

**Figura 6. nftables en Gateway**

Pegar captura aqui:


**Descripcion:** El Gateway permite el trafico web HTTPS/HTTP y restringe SSH a la IP administradora con rate limiting.

## 7.2 nftables en API

**Comandos:**

```bash
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@10.0.11.168
sudo systemctl status nftables --no-pager
sudo nft list ruleset
sudo systemctl status fraud-producer-api --no-pager
```

**Reglas esperadas:**

```text
SSH 22 solo desde Gateway 10.0.1.33 con limit rate 4/minute
API 8000 solo desde Gateway 10.0.1.33 con limit rate 30/second
```

**Figura 7. nftables en API productora**

Pegar captura aqui:


**Descripcion:** La API no queda expuesta directamente a Internet; solo acepta trafico desde el Gateway.

## 7.3 nftables en Kafka

**Comandos:**

```bash
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@10.0.21.209
sudo systemctl status nftables --no-pager
sudo nft list ruleset
```

**Reglas esperadas:**

```text
SSH 22 solo desde Gateway 10.0.1.33 con limit rate 4/minute
Kafka 9092 solo desde API 10.0.11.168 y APP 10.0.21.138
```

**Figura 8. nftables en Kafka**

Pegar captura aqui:


**Descripcion:** Kafka no esta expuesto a Internet; solo la API productora y el consumer pueden conectarse al puerto 9092.

## 7.4 nftables en APP / DB / Dashboard

**Comandos:**

```bash
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@10.0.21.138
sudo systemctl status nftables --no-pager
sudo nft list ruleset
```

**Reglas esperadas:**

```text
SSH 22 solo desde Gateway 10.0.1.33 con limit rate 4/minute
Dashboard 3000 solo desde Gateway 10.0.1.33
Politica por defecto drop
```

**Figura 9. nftables en APP / DB / Dashboard**

Pegar captura aqui:


**Descripcion:** El dashboard solo es accesible desde el Gateway. PostgreSQL permanece local en la instancia y no se expone a Internet.

---

# 8. SQL Injection Vulnerable

Se implemento un endpoint de laboratorio vulnerable para demostrar una tecnica UNION-based controlada.

**Endpoint:**

```text
GET /ingest/lab/vulnerable-search
```

**Comando desde Windows PowerShell:**

```powershell
curl.exe "https://api.fraud-log-pipeline.duckdns.org/ingest/lab/vulnerable-search?username=alice%27%20UNION%20SELECT%2099,%27mallory%27,%27mallory@example.com%27,%27admin%27--"
```

**Resultado esperado:**

```text
La respuesta incluye una fila inyectada:
id = 99
username = mallory
role = admin
```

**Figura 10. Explotacion controlada UNION-based en endpoint vulnerable**

Pegar captura aqui:


**Descripcion:** La evidencia muestra que el endpoint vulnerable concatena entrada de usuario y permite demostrar una inyeccion SQL controlada en laboratorio.

---

# 9. Endpoint SQL Injection Reparado

Se implemento un endpoint seguro que usa consulta parametrizada.

**Endpoint:**

```text
GET /ingest/lab/safe-search
```

**Comando desde Windows PowerShell:**

```powershell
curl.exe "https://api.fraud-log-pipeline.duckdns.org/ingest/lab/safe-search?username=alice%27%20UNION%20SELECT%2099,%27mallory%27,%27mallory@example.com%27,%27admin%27--"
```

**Resultado esperado:**

```text
rows: []
```

**Figura 11. Endpoint reparado con consulta parametrizada**

Pegar captura aqui:


**Descripcion:** La consulta parametrizada trata el payload como texto normal, por lo que no se ejecuta la inyeccion. Aun asi, el intento queda registrado para auditoria.

---

# 10. Prueba de Fuerza Bruta

La regla de fuerza bruta genera una alerta cuando una misma IP realiza multiples intentos fallidos de login en una ventana corta.

**Comando desde Windows PowerShell:**

```powershell
$body = @{ email = "test@test.com"; password = "wrong" } | ConvertTo-Json -Compress
1..5 | ForEach-Object {
  Invoke-RestMethod -Method Post "https://api.fraud-log-pipeline.duckdns.org/ingest/auth/login" -ContentType "application/json" -Body $body
}
```

**Resultado esperado:**

```text
Se generan eventos AUTH_FAILED.
El consumer produce una alerta BRUTE_FORCE_ATTEMPT.
```

**Figura 12. Generacion de intentos fallidos de login**

Pegar captura aqui:


**Descripcion:** La prueba simula un ataque de fuerza bruta contra el endpoint de login.

---

# 11. Alertas Almacenadas en PostgreSQL

Las alertas detectadas por el consumer se almacenan en PostgreSQL.

**Comando ejecutado en APP / DB / Dashboard:**

```bash
sudo -u postgres psql -d fraud_logs_db -P pager=off \
  -c "SELECT alert_type, severity, ip_address, endpoint, created_at FROM fraud_alerts ORDER BY created_at DESC LIMIT 10;"
```

**Alertas esperadas:**

```text
SQL_INJECTION_ATTEMPT
BRUTE_FORCE_ATTEMPT
```

**Figura 13. Tabla fraud_alerts con alertas recientes**

Pegar captura aqui:


**Descripcion:** La evidencia confirma que el pipeline completo almacena alertas en base de datos despues del analisis heuristico.

---

# 12. Dashboard Seguro

El dashboard permite visualizar eventos, alertas y resumen del sistema.

**URL:**

```text
https://dashboard.fraud-log-pipeline.duckdns.org/
```

**Credenciales de demo:**

```text
admin@example.com
Admin2026Grupo4
```

**Figura 14. Pantalla de login del dashboard**

Pegar captura aqui:


**Figura 15. Dashboard con alertas y logs**

Pegar captura aqui:


**Descripcion:** El dashboard esta protegido por autenticacion y muestra alertas generadas en tiempo real a partir de los logs procesados.

---

# 13. JWT, Refresh Token y CSRF

El dashboard usa un esquema de autenticacion seguro:

| Mecanismo | Implementacion |
|---|---|
| Access token JWT | Duracion corta, 15 minutos |
| Refresh token | Cookie `httpOnly` |
| CSRF | Cookie `csrf_token` y header personalizado |
| Logout | Revocacion de refresh token |

**Evidencia sugerida en navegador:**

1. Abrir DevTools.
2. Ir a la pestana Application.
3. Revisar cookies.
4. Verificar `refresh_token` y `csrf_token`.
5. Revisar requests a `/api/auth/refresh` en Network.

**Figura 16. Cookies y tokens del dashboard**

Pegar captura aqui:


**Descripcion:** La evidencia muestra el uso de cookies y tokens para proteger la sesion del dashboard.

---

# 14. 2FA TOTP con QR

El dashboard implementa autenticacion de doble factor usando TOTP.

**Flujo funcional:**

```text
Login con email/password
Setup 2FA
Generacion de secreto TOTP
Generacion de QR en backend
Escaneo con app autenticadora
Validacion de codigo de 6 digitos
Activacion de two_factor_enabled
```

**Apps compatibles:**

```text
Google Authenticator
Microsoft Authenticator
Authy
```

**Figura 17. QR TOTP generado por el backend**

Pegar captura aqui:


**Comando opcional para verificar en PostgreSQL:**

```bash
sudo -u postgres psql -d fraud_logs_db -P pager=off \
  -c "SELECT email, role, two_factor_enabled FROM users;"
```

**Figura 18. Usuario con 2FA activado en PostgreSQL**

Pegar captura aqui:


**Descripcion:** La evidencia confirma que el backend genera el QR TOTP y que el usuario queda con 2FA activado.

---

# 15. TLS Wildcard y SSL Labs

Se emitio un certificado wildcard mediante Let's Encrypt usando validacion DNS-01 con DuckDNS.

**Certificado:**

```text
*.fraud-log-pipeline.duckdns.org
```

**Rutas del certificado en Gateway:**

```text
/etc/letsencrypt/live/fraud-log-pipeline-wildcard/fullchain.pem
/etc/letsencrypt/live/fraud-log-pipeline-wildcard/privkey.pem
```

**Resultado SSL Labs:**

```text
A+
TLS 1.3 soportado
HSTS activo
```

**Figura 19. SSL Labs A+ para api.fraud-log-pipeline.duckdns.org**

Pegar captura aqui:


**Descripcion:** La evidencia demuestra que el servidor expone HTTPS correctamente, soporta TLS moderno y obtiene calificacion A+ en SSL Labs.

**Nota de renovacion:** El certificado fue emitido con DNS-01 manual. Para renovarlo se debe repetir el proceso de Certbot antes de la fecha de expiracion indicada por Let's Encrypt.

---

# 16. Prueba End-to-End del Pipeline

La prueba end-to-end valida el flujo completo:

```text
Cliente externo
    -> Nginx HTTPS
    -> API productora
    -> Kafka
    -> Consumer heuristico
    -> PostgreSQL
    -> Dashboard
```

**Pasos ejecutados:**

1. Enviar payload SQL Injection al endpoint vulnerable.
2. Enviar el mismo payload al endpoint reparado.
3. Generar 5 intentos fallidos de login.
4. Consultar alertas en PostgreSQL.
5. Ver alertas en dashboard.

**Figura 20. Evidencia general del flujo end-to-end**

Pegar captura aqui:


**Descripcion:** Esta evidencia resume que los eventos externos llegan a la API, se publican en Kafka, son procesados por el consumer y finalmente quedan visibles en PostgreSQL y dashboard.

---

# 17. Servicios Activos sin Docker

La version final del despliegue usa servicios nativos con `systemd`.

**Gateway:**

```bash
sudo systemctl status nginx --no-pager
sudo systemctl status nftables --no-pager
```

**API:**

```bash
sudo systemctl status fraud-producer-api --no-pager
```

**Kafka:**

```bash
sudo systemctl status kafka --no-pager
```

**APP / DB / Dashboard:**

```bash
sudo systemctl status postgresql --no-pager
sudo systemctl status fraud-consumer --no-pager
sudo systemctl status fraud-dashboard --no-pager
```

**Figura 21. Servicios activos con systemd**

Pegar captura aqui:


**Descripcion:** Esta evidencia confirma que el despliegue final opera sin Docker, usando servicios nativos del sistema operativo.

---

# 18. Conclusiones

El proyecto cumple con los requisitos tecnicos solicitados. Se desplego una arquitectura en AWS EC2 con cuatro roles separados: Gateway, API productora, Kafka y procesamiento con base de datos y dashboard.

Kafka organiza los logs por topics segun el tipo de evento. El consumer procesa los mensajes en tiempo real y aplica reglas heuristicas para detectar SQL Injection, fuerza bruta y otros comportamientos sospechosos. Las alertas se almacenan en PostgreSQL y se visualizan en un dashboard protegido.

La solucion incorpora controles de seguridad en varias capas: HTTPS con certificado wildcard, Nginx con rate limiting, nftables por instancia, JWT de corta duracion, refresh token en cookie httpOnly, proteccion CSRF y 2FA TOTP con QR generado en backend.

La prueba end-to-end demuestra que un evento malicioso generado desde Internet llega a la API, se publica en Kafka, es detectado por el consumer, se almacena en PostgreSQL y se visualiza en el dashboard.

---

# 19. Checklist de Evidencias

| Evidencia | Estado |
|---|---|
| EC2 con 4 instancias y roles separados | Pendiente de pegar captura |
| Gateway Nginx operativo | Pendiente de pegar captura |
| HTTPS por dominio | Pendiente de pegar captura |
| SSL Labs A+ | Pendiente de pegar captura |
| Kafka activo y topics | Pendiente de pegar captura |
| PostgreSQL activo | Pendiente de pegar captura |
| Consumer activo | Pendiente de pegar captura |
| Dashboard activo | Pendiente de pegar captura |
| nftables en Gateway | Pendiente de pegar captura |
| nftables en API | Pendiente de pegar captura |
| nftables en Kafka | Pendiente de pegar captura |
| nftables en APP | Pendiente de pegar captura |
| SQLi vulnerable UNION-based | Pendiente de pegar captura |
| SQLi reparado parametrizado | Pendiente de pegar captura |
| Fuerza bruta | Pendiente de pegar captura |
| Tabla `fraud_alerts` | Pendiente de pegar captura |
| Dashboard con alertas | Pendiente de pegar captura |
| JWT, refresh token y CSRF | Pendiente de pegar captura |
| QR TOTP 2FA | Pendiente de pegar captura |

---

# 20. Anexos

## 20.1 Comandos Rapidos para la Sustentacion

### Validar API y dashboard HTTPS

```powershell
curl.exe "https://api.fraud-log-pipeline.duckdns.org/ingest/"
curl.exe "https://dashboard.fraud-log-pipeline.duckdns.org/api/health"
```

### SQL Injection vulnerable

```powershell
curl.exe "https://api.fraud-log-pipeline.duckdns.org/ingest/lab/vulnerable-search?username=alice%27%20UNION%20SELECT%2099,%27mallory%27,%27mallory@example.com%27,%27admin%27--"
```

### SQL Injection reparado

```powershell
curl.exe "https://api.fraud-log-pipeline.duckdns.org/ingest/lab/safe-search?username=alice%27%20UNION%20SELECT%2099,%27mallory%27,%27mallory@example.com%27,%27admin%27--"
```

### Fuerza bruta

```powershell
$body = @{ email = "test@test.com"; password = "wrong" } | ConvertTo-Json -Compress
1..5 | ForEach-Object {
  Invoke-RestMethod -Method Post "https://api.fraud-log-pipeline.duckdns.org/ingest/auth/login" -ContentType "application/json" -Body $body
}
```

### Consultar alertas

```bash
ssh -i /home/ec2-user/fraud-log-key.pem ec2-user@10.0.21.138
sudo -u postgres psql -d fraud_logs_db -P pager=off \
  -c "SELECT alert_type, severity, ip_address, endpoint, created_at FROM fraud_alerts ORDER BY created_at DESC LIMIT 10;"
```

## 20.2 Resumen Oral Sugerido

```text
El sistema implementa un pipeline de logs en tiempo real sobre AWS EC2. El trafico entra por un Gateway Nginx con HTTPS y certificado wildcard. La API productora genera eventos de acceso y los envia a Kafka, donde se separan por topics. Un consumer privado analiza los eventos con reglas heuristicas para SQL Injection y fuerza bruta, guarda alertas en PostgreSQL y las muestra en un dashboard protegido con JWT, refresh token, CSRF y 2FA TOTP. Cada instancia esta protegida con nftables, permitiendo solamente el trafico necesario entre capas.
```
