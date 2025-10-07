# Guía de Despliegue en Servidor Ubuntu

## Requisitos Previos

- Ubuntu Server 20.04 o superior
- Docker y Docker Compose instalados
- Acceso SSH al servidor
- (Opcional) Dominio apuntando a la IP del servidor para HTTPS

## Instalación de Docker en Ubuntu

Si no tienes Docker instalado, ejecuta:

```bash
# Actualizar paquetes
sudo apt update
sudo apt upgrade -y

# Instalar dependencias
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Agregar clave GPG de Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Agregar repositorio de Docker
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Habilitar Docker para que inicie con el sistema
sudo systemctl enable docker
sudo systemctl start docker

# Agregar tu usuario al grupo docker (opcional, para no usar sudo)
sudo usermod -aG docker $USER
# Cerrar sesión y volver a entrar para que tome efecto
```

## Pasos de Despliegue

### 1. Clonar el repositorio en el servidor

```bash
cd /opt
sudo git clone https://github.com/RHV044/whatsapp-mcp-server.git
cd whatsapp-mcp-server
```

### 2. Crear directorios necesarios

```bash
sudo mkdir -p nginx/conf.d
sudo mkdir -p certbot/conf
sudo mkdir -p certbot/www
```

### 3. Configurar el firewall (UFW)

```bash
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

### 4. Construir y levantar los servicios

```bash
# Construir las imágenes
sudo docker compose build

# Levantar todos los servicios
sudo docker compose up -d

# Ver los logs para el QR code de WhatsApp (primera vez)
sudo docker compose logs -f whatsapp-bridge
```

### 5. Escanear código QR

Cuando veas el código QR en los logs:
1. Abre WhatsApp en tu teléfono
2. Ve a Configuración → Dispositivos vinculados
3. Escanea el código QR

### 6. Verificar que todo funciona

```bash
# Ver estado de los contenedores
sudo docker compose ps

# Verificar health de los servicios
curl http://localhost/health

# Ver logs en tiempo real
sudo docker compose logs -f
```

## Auto-reinicio con Systemd

Para que los servicios se levanten automáticamente al reiniciar el servidor:

### 1. Crear servicio systemd

```bash
sudo nano /etc/systemd/system/whatsapp-mcp.service
```

Pega este contenido:

```ini
[Unit]
Description=WhatsApp MCP Server
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/whatsapp-mcp-server
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

### 2. Habilitar y arrancar el servicio

```bash
sudo systemctl daemon-reload
sudo systemctl enable whatsapp-mcp.service
sudo systemctl start whatsapp-mcp.service
sudo systemctl status whatsapp-mcp.service
```

Ahora el servicio se levantará automáticamente cuando reinicies el servidor.

## Configurar HTTPS con Let's Encrypt (Opcional)

Si tienes un dominio apuntando a tu servidor:

### 1. Editar la configuración de Nginx

```bash
sudo nano nginx/conf.d/whatsapp-mcp.conf
```

Cambia `server_name _;` por `server_name tu-dominio.com;`

### 2. Obtener certificado SSL

```bash
# Asegúrate de que tu dominio apunte a la IP del servidor
sudo docker compose run --rm certbot certonly \
  --webroot \
  -w /var/www/certbot \
  -d tu-dominio.com \
  --email tu-email@ejemplo.com \
  --agree-tos \
  --no-eff-email
```

### 3. Habilitar HTTPS en Nginx

Edita `nginx/conf.d/whatsapp-mcp.conf` y descomenta el bloque del servidor HTTPS (las líneas que empiezan con `#`).

Cambia `tu-dominio.com` por tu dominio real.

### 4. Agregar redirect HTTP → HTTPS

En el bloque HTTP del archivo de configuración, agrega:

```nginx
# Redirigir HTTP a HTTPS (excepto para Certbot)
location / {
    return 301 https://$server_name$request_uri;
}
```

### 5. Reiniciar Nginx

```bash
sudo docker compose restart nginx
```

## Comandos Útiles

### Ver logs

```bash
# Todos los servicios
sudo docker compose logs -f

# Solo un servicio específico
sudo docker compose logs -f whatsapp-bridge
sudo docker compose logs -f whatsapp-mcp-server
sudo docker compose logs -f nginx
```

### Reiniciar servicios

```bash
# Reiniciar todo
sudo docker compose restart

# Reiniciar un servicio específico
sudo docker compose restart whatsapp-bridge
```

### Detener servicios

```bash
sudo docker compose down
```

### Actualizar el código

```bash
cd /opt/whatsapp-mcp-server
sudo git pull
sudo docker compose build
sudo docker compose up -d
```

### Ver recursos usados

```bash
docker stats
```

### Limpiar imágenes antiguas

```bash
sudo docker image prune -a
```

## Acceso desde Internet

Una vez desplegado, puedes acceder a los servicios desde:

- **HTTP**: `http://tu-servidor-ip/mcp/` o `http://tu-dominio.com/mcp/`
- **HTTPS** (si configuraste SSL): `https://tu-dominio.com/mcp/`

### URLs disponibles:

- MCP Server: `/mcp/`
- Bridge API: `/bridge/`
- Health check: `/health`

## Troubleshooting

### Los servicios no inician

```bash
sudo docker compose logs
sudo journalctl -u whatsapp-mcp -n 50
```

### QR code no aparece

```bash
sudo docker compose down
sudo rm -rf ./whatsapp-bridge/data/*
sudo docker compose up -d
sudo docker compose logs -f whatsapp-bridge
```

### Error de permisos

```bash
sudo chown -R $USER:$USER /opt/whatsapp-mcp-server
```

### Puerto ocupado

```bash
# Ver qué proceso usa el puerto
sudo lsof -i :80
sudo lsof -i :443

# Detener servicio que usa el puerto (ejemplo con Apache)
sudo systemctl stop apache2
sudo systemctl disable apache2
```

### Certificado SSL no se renueva

```bash
# Renovar manualmente
sudo docker compose run --rm certbot renew
sudo docker compose restart nginx
```

## Backup de Datos

Es importante hacer backup de la carpeta con los datos de WhatsApp:

```bash
# Backup
sudo tar -czf whatsapp-backup-$(date +%Y%m%d).tar.gz \
  /opt/whatsapp-mcp-server/whatsapp-bridge/data

# Restaurar
sudo tar -xzf whatsapp-backup-20250106.tar.gz -C /
```

## Seguridad

Recomendaciones:

1. **No expongas el puerto 8080 del bridge directamente** - Solo accede a través de Nginx
2. **Configura UFW** para limitar accesos
3. **Usa HTTPS** siempre que sea posible
4. **Actualiza regularmente** el sistema y Docker
5. **Monitorea los logs** periódicamente

```bash
# Ver intentos de acceso
sudo docker compose logs nginx | grep -i error

# Ver conexiones activas
sudo docker compose exec nginx netstat -an | grep ESTABLISHED
```

## Monitoreo

Para ver si los servicios están funcionando correctamente:

```bash
# Health check
curl http://localhost/health

# Ver memoria y CPU usada
docker stats --no-stream

# Ver si los contenedores están "healthy"
docker ps --format "table {{.Names}}\t{{.Status}}"
```

## Desinstalar

Si necesitas eliminar todo:

```bash
# Detener y eliminar contenedores
sudo docker compose down -v

# Eliminar imágenes
sudo docker rmi rhv044/whatsapp-bridge:prod rhv044/whatsapp-mcp-server:prod

# Eliminar servicio systemd
sudo systemctl stop whatsapp-mcp
sudo systemctl disable whatsapp-mcp
sudo rm /etc/systemd/system/whatsapp-mcp.service
sudo systemctl daemon-reload

# Eliminar archivos (CUIDADO: esto elimina todos los datos)
sudo rm -rf /opt/whatsapp-mcp-server
```
