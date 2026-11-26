# Blackwall

Aplicación web de **gestión de incidentes de seguridad** con identificación, autenticación y autorización reales. Proyecto final de **Ciberseguridad II** (Universidad Tecnológica de Panamá, FISC).

> *Nadie cruza sin ser verificado.*

| Pilar | Cómo se resuelve |
|---|---|
| **Identificación** | Usuarios `apellido.nombre` en un directorio **OpenLDAP**, grupos `GRP_*` y roles `ROL_*` |
| **Autenticación** | **Keycloak** con OpenID Connect (Authorization Code + **PKCE**), **TOTP** obligatorio para administrador y auditor, HTTPS en todo |
| **Autorización** | Matriz de roles aplicada **en el servidor** (API PHP), con scopes `recurso:acción`, denegar por defecto y control por propiedad |

## Qué incluye

- `blackwall-real/` — la aplicación y su infraestructura (Docker Compose: OpenLDAP + Keycloak + PostgreSQL + app PHP), configuración reproducible de Keycloak, **31 pruebas de seguridad**, escaneo OWASP ZAP, captura de red y evidencias.
- `servidor-blackwall/` — para dejar la aplicación **accesible desde internet** desde tu propia laptop (túnel gratuito, arranque automático, apagado y borrado con un comando).
- `blackwall-real/docs/Guia-Tecnica-Blackwall.pdf` — guía técnica con capturas, protocolos, funciones y glosario.
- `RESUMEN.md` — estado del proyecto.

## Cómo ejecutarlo

Requisitos: Linux con **Docker** (Compose v2), `python3` y `openssl`. No se instala nada global.

```bash
cd blackwall-real
scripts/bw.sh arriba          # certificados + secretos + contenedores + configuración (3–5 min la primera vez)
scripts/bw.sh credenciales    # contraseña de las cuentas de demostración
```

Abre <https://app.localhost:8444>. El certificado lo firma una CA del laboratorio (`~/.local/share/blackwall/certs/ca.crt`): impórtala en el navegador o acepta la advertencia.

**Para que otras personas entren por internet:** ver [`servidor-blackwall/README.md`](servidor-blackwall/README.md).

Los secretos se generan al instalar y quedan **fuera del repositorio** (`~/.local/share/blackwall/`).

## Cuentas de demostración

| Usuario | Rol | Segundo factor |
|---|---|---|
| `campbell.cesar` | Administrador | obligatorio (se configura al primer ingreso) |
| `cruz.irvin`, `pinto.nicole` | Analista | opcional |
| `galvez.angel` | Auditor | obligatorio |
| `ejemplo.usuario`, `ejemplo.usuario2` | Usuario | opcional |
| `cordero.moises` | Invitado | opcional |

## Pruebas y evidencias

```bash
cd blackwall-real
scripts/bw.sh pruebas        # 31 casos contra el sistema real
```

Resultados en `blackwall-real/evidencias/` (tabla de pruebas, OWASP ZAP antes y después, captura de red, capturas de la interfaz). Más detalle en [`blackwall-real/README.md`](blackwall-real/README.md) y [`blackwall-real/SIMULADO-VS-REAL.md`](blackwall-real/SIMULADO-VS-REAL.md).

## Estructura

```
blackwall-real/        aplicación + infraestructura + pruebas + documentación
  app/                 aplicación PHP (src/, public/) y su Dockerfile
  keycloak/            configuración de Keycloak por API y tema de inicio de sesión
  ldap/ db/            directorio y base de datos
  scripts/             preparar, levantar y capturar tráfico
  pruebas/             27 casos CP, escaneo ZAP, capturas de la interfaz
  docs/                guía técnica (PDF y fuente)
  evidencias/          resultados
servidor-blackwall/    publicación por internet (túnel, proxy, servicio)
```

## Seguridad

Los certificados, claves y contraseñas **no** están en este repositorio. Este es un proyecto académico de laboratorio: antes de usarlo fuera de ese contexto, cambia todas las credenciales y revisa los límites descritos en `blackwall-real/README.md`.
