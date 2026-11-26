# Qué estaba simulado y cómo está ahora

Prototipo anterior: `../sigi.html` (todo corría dentro del navegador). Versión real: esta carpeta.

| # | Pieza | Antes (simulado) | Ahora (real) | Cómo comprobarlo |
|---|---|---|---|---|
| 1 | Directorio de usuarios | Un objeto JavaScript (`DIR`) | **OpenLDAP** por LDAPS, una OU por área y grupos `GRP_*` | CP-22, CP-26; `docker exec blackwall-ldap-1 ldapsearch …` |
| 2 | Proveedor de identidad | Funciones JS que imitaban a Keycloak | **Keycloak 26.8** en HTTPS, realm `proyecto-accesos` | `https://acceso.localhost:8443` |
| 3 | Validación de la contraseña | Comparación con una constante en el navegador | La valida el directorio (bind LDAP) a través de Keycloak; la app nunca la ve | CP-02, CP-10 |
| 4 | Política de contraseñas (12+, últimas 5) | Una función JS | `ppolicy` en OpenLDAP + política del realm | CP-22 (clave corta rechazada) |
| 5 | Bloqueo tras 5 intentos | Un contador en memoria | Protección de fuerza bruta de Keycloak + `ppolicy`; queda en la auditoría | CP-02 |
| 6 | Segundo factor (TOTP) | Un hash inventado, con el código a la vista | **TOTP real (RFC 6238)**, obligatorio para admin y auditor, con anti-replay | CP-01, CP-11, CP-12, CP-13 |
| 7 | OAuth 2.0 / OIDC con PKCE, `state`, `nonce` | Pasos dibujados en pantalla | Authorization Code + PKCE (S256) real; sin Implicit ni Password Grant | CP-14, CP-15, CP-18 |
| 8 | `redirect_uri` exacta | Texto en la pantalla | La valida Keycloak | CP-09 |
| 9 | Tokens (JWT) | Firmados con SHA-256 y un secreto en el código | **RS256**, claves públicas del IdP (JWKS), vida de 5 min | CP-03, CP-04 |
| 10 | Refresh token con rotación | Un `Set` en memoria | Rotación real: el anterior queda inválido | CP-16 |
| 11 | Cierre de sesión | Borraba una variable | Revoca la sesión en el IdP y destruye la de la app (con CSRF) | CP-17 |
| 12 | Mapeo grupo → rol | Constante `GRUPOS` | *Group mapper* LDAP de Keycloak; sin caché, el cambio se ve en el siguiente token | CP-23 |
| 13 | Scopes `recurso:accion` | Tabla `SCOPES` en JS | *Client scopes* de Keycloak restringidos por rol | CP-19, CP-21 |
| 14 | API y RBAC | Funciones JS en el navegador | **Backend PHP**: valida el token y el scope en cada endpoint; denegar por defecto | CP-05…08, CP-20, CP-21 |
| 15 | Control por propiedad | Por nombre de usuario | Por el `sub` del token | CP-06, CP-20 |
| 16 | Casos y comentarios | Arreglos en memoria (se perdían al recargar) | Base de datos SQLite persistente, consultas preparadas | CP-25 |
| 17 | Auditoría | Arreglo en memoria | Tabla propia + eventos de Keycloak (inicios de sesión, fallos, bloqueos) | CP-24 |
| 18 | Alta, edición y baja de usuarios | Modificaba el objeto `DIR` | Escribe en el LDAP con `svc-blackwall-sync` (permisos limitados por ACL) | CP-22, CP-23 |
| 19 | Cuenta de servicio | Una fila decorativa | Cuenta LDAP real, sin inicio de sesión interactivo | CP-26 |
| 20 | Configuración (vida del token, intentos, bloqueo) | Objeto en memoria | Parámetros del realm de Keycloak | CP-03, CP-08 |
| 21 | HTTPS | Ninguno (HTML estático) | TLS en la app, en Keycloak y LDAPS, con CA propia | CP-10 |
| 22 | Secretos | `demo-firma` y la clave dentro del código | Variables de entorno, fuera del repositorio | `~/.local/share/blackwall/` |
| 23 | Pruebas | 28 comprobaciones del motor simulado | 27 casos contra el sistema real | `scripts/bw.sh pruebas` |
| 24 | OWASP ZAP | No aplicaba | Hecho: antes 0/2/4 (alta/media/baja) → después 0/0/0 | `evidencias/hallazgos-zap.md` |
| 25 | Wireshark / captura de red | No aplicaba | Hecho: 0 claves y 0 tokens en claro con HTTPS | `evidencias/captura-login.txt` |
| 26 | Dónde corre | Netlify (estático) | Docker en el equipo (no se puede publicar en Netlify) | `scripts/bw.sh arriba` |

## Estado del segundo factor (MFA)

- **Ya funciona en el sistema:** Keycloak lo exige a `ROL_ADMIN` y `ROL_AUDITOR`; para los demás roles es opcional. Las pruebas lo verifican con usuarios temporales.
- **Falta de su parte:** que `campbell.cesar` y `galvez.angel` lo configuren con su propio celular. La primera vez que inicien sesión aparece un QR: se escanea con una app autenticadora (FreeOTP, Aegis, Google Authenticator…) y se escribe el código. Hasta entonces la pantalla de Usuarios los muestra como «2 pasos: pendiente».
- **Para la evidencia del informe:** conviene capturar ese primer ingreso con el celular real.

## Lo que sigue sin ser real

- Los casos de ejemplo de la base de datos (INC-001 a INC-006) y los nombres `ejemplo.usuario` son datos de demostración.
- El certificado lo firma una CA del laboratorio (no una pública).
- Informe final en PDF y actualización de las guías PDF: pendientes.
