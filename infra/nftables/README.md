# nftables por instancia EC2

Estas plantillas son defensivas y deben ajustarse antes de aplicarlas:

- Reemplaza `ADMIN_PUBLIC_IP`, `GATEWAY_PRIVATE_IP`, `API_PRIVATE_IP`, `KAFKA_PRIVATE_IP` y `APP_PRIVATE_IP`.
- Aplica primero en una sesion SSH de prueba y manten otra sesion abierta.
- En Amazon Linux/Ubuntu instala y habilita `nftables` antes de cargar reglas.

Comando de validacion:

```bash
sudo nft -c -f gateway.nft
```

Comando de aplicacion:

```bash
sudo nft -f gateway.nft
sudo systemctl enable --now nftables
```
