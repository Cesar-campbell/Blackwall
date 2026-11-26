# Servidor Blackwall

Deja la aplicación **real** (Blackwall) encendida en tu laptop y accesible desde internet, para que compañeros, la profesora o cualquiera con el enlace entren desde su casa o la universidad, con su propio usuario y su propio segundo factor (MFA). Todo se guarda en esta laptop, así que la auditoría muestra lo que hace **cada persona**.

## Cómo se usa

| Quiero… | Comando (desde esta carpeta) |
|---|---|
| Ver el enlace para compartir | `./servidor.sh enlace` |
| Ver si todo está bien (servicios, memoria, respuesta desde internet) | `./servidor.sh estado` |
| Apagar el servidor (conserva los datos) | `./servidor.sh detener` |
| Encenderlo de nuevo | `./servidor.sh iniciar` |
| Usarlo **sin internet** (solo en esta laptop) | `./servidor.sh local`  (vuelve con `./servidor.sh publico`) |
| Ver qué está haciendo | `./servidor.sh logs` |
| **Apagar y borrar TODO** al terminar | `./servidor.sh eliminar` (pide confirmación con `--si`) |

Instalación (una sola vez): `./servidor.sh instalar`. Después **arranca solo al encender la laptop**, sin iniciar sesión, y se levanta solo si algo se cae.

## Cómo funciona

```
Compañero (su casa)  ──HTTPS──►  Cloudflare  ──túnel──►  tu laptop
                                                          │
                                       proxy (Caddy) ─────┤  /         → aplicación
                                                          │  /acceso/  → inicio de sesión (Keycloak)
                                                          └─ directorio (OpenLDAP) y bases de datos: solo red interna
```

- **Una sola dirección pública** con certificado válido (lo pone Cloudflare). El túnel sale desde tu laptop hacia Cloudflare: no se abre ningún puerto del router.
- La consola de administración de Keycloak, su realm `master`, la consola de cuenta y las métricas **no se publican** (el proxy responde 404).
- La auditoría guarda la **IP real** de cada visitante.
- Memoria total de los servicios: unos 700 MB.

## Importante

- **Enlace fijo y gratis (Tailscale Funnel):** si existe el archivo `~/.local/share/blackwall/servidor/tailscale-url` (con la dirección `https://<equipo>.<red>.ts.net`), el servidor usa esa dirección y no cambia nunca. Se configura una vez: instalar `tailscaled`/`tailscale` en `~/.local/bin`, iniciar sesión (`tailscale up --hostname=blackwall`), activar **HTTPS Certificates** en la consola de Tailscale y **Funnel**, y guardar la dirección en ese archivo. Sin ese archivo se usa un túnel temporal de Cloudflare, cuyo enlace **cambia** en cada reinicio. Con dominio propio también se puede un túnel con nombre de Cloudflare (`tunel-fijo.env` con `TUNEL_TOKEN` y `URL_FIJA`).
- Mientras el enlace esté activo, **cualquiera que lo tenga puede ver la pantalla de acceso**. Entre usuarios y contraseñas la seguridad la da la propia aplicación (bloqueo tras 5 intentos, MFA, etc.). Antes de compartirlo: entra con `campbell.cesar` y **configura su segundo factor** (si no, quien conozca la contraseña podría registrar el suyo).
- Cada compañero necesita su cuenta: se crea en la pantalla **Usuarios** (formato `apellido.nombre`).
- La laptop debe estar **encendida y con internet**. El servicio evita que se suspenda (también al cerrar la tapa).
- Los túneles gratuitos (Cloudflare "quick tunnels" y Tailscale Funnel) son para pruebas y demostraciones; no tienen garantía de disponibilidad. Al eliminar todo, quita también el dispositivo `blackwall` en la consola de Tailscale.

## Qué hay aquí

| Archivo | Para qué |
|---|---|
| `servidor.sh` | Todos los comandos y el servicio de arranque |
| `docker-compose.publico.yml` | Cambia la configuración para el modo público y agrega el proxy |
| `Caddyfile` | Reglas del proxy (qué se publica y qué se bloquea) |

El túnel (`cloudflared`) se instala solo en tu usuario (`~/.local/bin`), sin permisos de administrador. Los secretos y certificados están en `~/.local/share/blackwall/`, fuera de los repositorios.
