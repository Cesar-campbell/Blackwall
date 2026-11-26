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

- **El enlace cambia** cada vez que el túnel se reinicia (al encender la laptop, o si se cae internet un rato). Se obtiene siempre con `./servidor.sh enlace`. Para un enlace **fijo** hace falta un dominio: se crea un túnel con nombre en Cloudflare y se guardan `TUNEL_TOKEN` y `URL_FIJA` en `tunel-fijo.env` (el script lo usa solo).
- Mientras el enlace esté activo, **cualquiera que lo tenga puede ver la pantalla de acceso**. Entre usuarios y contraseñas la seguridad la da la propia aplicación (bloqueo tras 5 intentos, MFA, etc.). Antes de compartirlo: entra con `campbell.cesar` y **configura su segundo factor** (si no, quien conozca la contraseña podría registrar el suyo).
- Cada compañero necesita su cuenta: se crea en la pantalla **Usuarios** (formato `apellido.nombre`).
- La laptop debe estar **encendida y con internet**. El servicio evita que se suspenda (también al cerrar la tapa).
- Los túneles gratuitos de Cloudflare ("quick tunnels") son para pruebas y demostraciones; no tienen garantía de disponibilidad.

## Qué hay aquí

| Archivo | Para qué |
|---|---|
| `servidor.sh` | Todos los comandos y el servicio de arranque |
| `docker-compose.publico.yml` | Cambia la configuración para el modo público y agrega el proxy |
| `Caddyfile` | Reglas del proxy (qué se publica y qué se bloquea) |

El túnel (`cloudflared`) se instala solo en tu usuario (`~/.local/bin`), sin permisos de administrador. Los secretos y certificados están en `~/.local/share/blackwall/`, fuera de los repositorios.
