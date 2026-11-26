# Blackwall (versión real)

Gestión de incidentes con identificación, autenticación y autorización **reales** (Ciberseguridad II, UTP). Reemplaza al prototipo simulado en el navegador (`../sigi.html`): aquí cada pieza que pide la guía existe y corre.

| Pieza de la guía | Qué se usa | Dónde |
|---|---|---|
| Directorio (LDAP/AD) | **OpenLDAP** 2.6 por **LDAPS**, política de contraseñas (`ppolicy`) | `ldap/`, `scripts/preparar.sh` |
| Proveedor de identidad | **Keycloak 26.8** en HTTPS, realm `proyecto-accesos`, TOTP | `keycloak/configurar.py` |
| Aplicación + API | **PHP 8.3 + Apache** en HTTPS, `firebase/php-jwt` (JWKS) | `app/` |
| HTTPS en todo | CA propia + certificados con `openssl` | `scripts/preparar.sh` |
| Pruebas CP-xx (31) | Python (login real con PKCE y TOTP) | `pruebas/casos_prueba.py` |
| Escaneo | **OWASP ZAP** (Docker) | `pruebas/zap_escaneo.py` |
| Verificar el cifrado | `tcpdump` + `tshark` (los `.pcap` abren en Wireshark) | `scripts/captura.sh` |

## Arquitectura

```
 Navegador ──HTTPS──► app.localhost:8444  (Apache + PHP)
    │                    │  /auth/*  sesión y tokens (solo en el servidor)
    │                    │  /api/*   exige Authorization: Bearer; valida firma RS256 (JWKS), iss, aud, exp y scopes
    │                    ├──HTTPS──► Keycloak (token, JWKS, logout, API de administración)
    │                    └──LDAPS──► OpenLDAP (alta/baja/cambio de usuarios con la cuenta svc-blackwall-sync)
    └──HTTPS──► acceso.localhost:8443 ──LDAPS──► OpenLDAP (valida la contraseña y lee los grupos)
                    └─► PostgreSQL (red interna de Docker)
```

Login: Authorization Code + **PKCE (S256)** con `state` y `nonce`. El navegador nunca ve el refresh token; el access token (5 min) vive solo en memoria de la página. El refresh token **rota** en cada uso. No hay Implicit ni Password Grant.

Lista de lo que estaba simulado y cómo está ahora: [`SIMULADO-VS-REAL.md`](SIMULADO-VS-REAL.md).

## Puesta en marcha

Requisitos: Docker (Compose v2), `python3`, `openssl`. No se instala nada global.

```bash
cd proyecto-final/blackwall-real
scripts/bw.sh arriba          # secretos + certificados + contenedores + configuración de Keycloak (3–5 min la primera vez)
scripts/bw.sh credenciales    # contraseña de las cuentas de demostración y del admin de Keycloak
```

Luego abre <https://app.localhost:8444>. `*.localhost` resuelve a tu máquina sin tocar `/etc/hosts`.
El certificado lo firma la CA del laboratorio (`~/.local/share/blackwall/certs/ca.crt`): importa ese archivo en el navegador (Firefox: *Ajustes → Privacidad → Ver certificados → Autoridades → Importar*) o acepta la advertencia.

Si editas el tema de login (`keycloak/temas/`), recrea el contenedor (`docker compose up -d --force-recreate keycloak`): `docker restart` deja una copia vieja del CSS en caché.

Los secretos y certificados quedan en `~/.local/share/blackwall/` (fuera del repositorio y fuera de la carpeta que sirve Apache). Para empezar de cero: `scripts/bw.sh limpiar && rm -rf ~/.local/share/blackwall`.

### Cuentas de demostración

Todas con la misma contraseña (`scripts/bw.sh credenciales`; cumple la política de 12+ caracteres).

| Usuario | Grupo del directorio | Rol | TOTP |
|---|---|---|---|
| `campbell.cesar` | `GRP_TI_ADMIN` | `ROL_ADMIN` | **obligatorio** |
| `cruz.irvin`, `pinto.nicole` | `GRP_SOC_ANALISTA` | `ROL_ANALISTA` | opcional |
| `galvez.angel` | `GRP_CUM_AUDITOR` | `ROL_AUDITOR` | **obligatorio** |
| `ejemplo.usuario`, `ejemplo.usuario2` | `GRP_USR_USUARIO` | `ROL_USUARIO` | opcional |
| `cordero.moises` | `GRP_PUB_INVITADO` | `ROL_INVITADO` | opcional |
| `svc-blackwall-sync` | (ou=servicio) | cuenta de servicio, **sin login** | — |

**Primer ingreso de admin/auditor:** Keycloak muestra un QR; escanéalo con una app autenticadora (FreeOTP, Aegis, Google Authenticator…) y escribe el código de 6 dígitos. Desde ahí cada login pide el código.

## Nomenclatura (guía, sección 6)

| Elemento | Formato | Ejemplos en este proyecto |
|---|---|---|
| Usuario | `apellido.nombre` (homónimo: `perez.juan2`) | `campbell.cesar`, `cruz.irvin` |
| Cuenta de servicio | `svc-<app>-<función>` | `svc-blackwall-sync` |
| Grupo | `GRP_<ÁREA>_<ROL>` | `GRP_SOC_ANALISTA` |
| Rol | `ROL_<NOMBRE>` | `ROL_AUDITOR` |
| Cliente OIDC | `cli-<app>-<entorno>` | `cli-blackwall-dev`, `cli-blackwall-sync-dev` |
| Scope | `<recurso>:<acción>` (`_propios` = control por propiedad) | `casos:leer`, `casos:leer_propios` |
| OU por área | minúsculas | `ou=ti`, `ou=soc`, `ou=cum`, `ou=usr`, `ou=pub`, `ou=servicio` |

## Cómo se aplica la autorización

1. **Directorio:** cada persona está en un grupo `GRP_*` (OpenLDAP).
2. **Keycloak:** el *group mapper* LDAP importa los grupos; cada grupo tiene asignado un rol `ROL_*` (mapeo automático, lectura en vivo, sin caché). Cada scope `<recurso>:<acción>` es un *client scope* restringido a los roles que lo necesitan; el token solo lleva los scopes que el rol permite.
3. **API:** cada endpoint exige su scope (`denegar por defecto`: lo no listado responde 404 y sin token 401) y aplica control por propiedad con el `sub` del token. **Nunca** se confía en el rol que mande la interfaz; el menú de la UI solo oculta opciones.

Matriz (`ROL_*` → scopes) en `keycloak/configurar.py` (`ROLES`), única fuente de verdad.

## Pruebas, ZAP y captura de red

```bash
scripts/bw.sh pruebas                          # 31 casos CP-xx contra el sistema real → evidencias/resultados-pruebas.md
python3 pruebas/zap_escaneo.py <etiqueta>      # escaneo ZAP autenticado y sin sesión → evidencias/zap-<etiqueta>.*
scripts/captura.sh --auto                      # tcpdump del login + búsqueda de claves/tokens → evidencias/captura-login.txt
```

Las pruebas crean usuarios temporales `prueba.*` en el directorio y los borran al terminar (los TOTP de las pruebas son de esos usuarios, no de los reales).

Interfaz en un navegador real (capturas para el informe): `pruebas/ui_capturas.cjs` (Chromium + `puppeteer-core`, instalado en una carpeta temporal).

## Hallazgos que encontraron las propias pruebas (antes → después)

| Hallazgo | Detectado por | Causa | Corrección |
|---|---|---|---|
| **El auditor podía modificar casos** (escalada de privilegios) | CP-07 | El rol técnico compuesto `MFA_OBLIGATORIO` (hijo de admin y auditor) hacía que los scopes de `ROL_ADMIN` alcanzaran también a `ROL_AUDITOR` | Se eliminó el rol compuesto; el TOTP obligatorio se decide con condiciones por rol (`ROL_ADMIN`, `ROL_AUDITOR`) en el flujo de login |
| El token no expiraba cuando se cambiaba la vida desde *Configuración* | CP-03 | Un atributo del cliente (`access.token.lifespan`) pisaba el valor del realm | Se quitó el atributo; manda el valor del realm |
| Un cambio de grupo en el directorio no cambiaba el rol | CP-23 | Caché de usuarios de Keycloak | Proveedor LDAP con `NO_CACHE` |
| Eventos de Keycloak ausentes en la auditoría | CP-02/CP-24 | Keycloak 26.8 exige el scope `kc-admin-api` (audiencia propia) en su API de administración | Se agregó el scope a la cuenta de servicio, con roles mínimos y `fullScopeAllowed=false` |
| Errores de PHP visibles en las respuestas | CP-02 | La imagen `php:apache` no trae `php.ini` (`display_errors` activo) | `php.ini-production` + `display_errors=Off`, `expose_php=Off` |
| Usuarios listados todos como «cuenta de servicio» | Revisión de la interfaz → CP-26 | La detección recorría mal las clases de objeto del LDAP | Se recorren por índice; CP-26 lo cubre |
| La pantalla Configuración no guardaba nada | CP-28 a CP-31 (al probar la sesión por ciclos) | La app reenviaba todo el realm a Keycloak y PHP convertía `{}` en `[]` | Se envían solo los campos que cambian |
| Pestaña Usuarios lenta (≈0,5 s) | Medición | 3 consultas a Keycloak por persona en cada visita | Caché de 30 s que se borra al modificar usuarios; estáticos comprimidos y con caché |
| Librería JWT con aviso de seguridad | `composer install` | `firebase/php-jwt` 6.x tiene un advisory | Se usa la 7.x |

Resultados completos: `evidencias/resultados-pruebas-antes.md` (20/25) → `evidencias/resultados-pruebas-final.md` (31/31).

### OWASP ZAP: antes → después

| | Altas | Medias | Bajas | Informativas |
|---|---|---|---|---|
| Antes (`evidencias/zap-antes.html`) | 0 | 2 (sin CSP, sin anti-clickjacking) | 4 (XSS persistente en JSON, versión del servidor, HSTS, `nosniff`) | 4 |
| Después (`evidencias/zap-despues.html`) | 0 | **0** | **0** | 3 (inherentes al escaneo) |

Qué se cambió para cada alerta: `evidencias/hallazgos-zap.md`. Cabeceras: `app/apache.conf`; JSON escapado: `app/src/Api.php`.

### Captura de red (CP-10)

`evidencias/login-https.pcap` (ábrelo en Wireshark): TLS 1.3 con `TLS_AES_256_GCM_SHA384`; 0 apariciones de la contraseña, de `eyJ` (JWT), del secreto del cliente o del `code_verifier`. `evidencias/control-http.pcap` es el mismo tipo de envío **sin** TLS: ahí sí se ve todo.

## Límites conocidos (lab ≠ producción)

- Certificados de una CA propia; ZAP se ejecuta con `sslAcceptAll` (no confía en esa CA).
- Keycloak en modo `start` con un único nodo. La base de datos de Keycloak solo acepta conexiones TLS (`verify-full`).
- La contraseña de `svc-blackwall-sync` (puede escribir en el directorio) está en variables de entorno del contenedor; en producción iría a un gestor de secretos con rotación.
- Auditoría en SQLite local + eventos de Keycloak; en producción, un SIEM/almacén centralizado y de solo-anexar.
- Sin respaldo del IdP ni alta disponibilidad.
