# Proyecto final: Seguridad en accesos (Blackwall)

Guía: `Guia_Proyecto_Final_2026.pdf` (Ciberseguridad II, UTP). Objetivo: una app que **identifique** usuarios, los **autentique** contra un directorio vía OpenID Connect (Authorization Code + PKCE, con TOTP) y **autorice** por roles (RBAC) en el backend.

## Archivos

- **`blackwall-real/`: la versión REAL (2026-11-25).** Docker Compose con OpenLDAP (LDAPS + política de contraseñas), Keycloak 26.8 (HTTPS, federación LDAP, TOTP por rol, scopes `recurso:accion`) y la app PHP 8.3 con login OIDC Authorization Code + PKCE, validación RS256/JWKS y RBAC en cada endpoint. Incluye pruebas CP-01..CP-25, escaneo ZAP, captura de red y su propio `README.md` (cómo levantarla, arquitectura, hallazgos). Interfaz: igual que el prototipo (panel de marca a la izquierda y acceso a la derecha; el acceso es el tema de login de Keycloak) y **sin textos técnicos dentro de la app** (nada de tokens, PKCE, Keycloak): eso queda en el backend. Lista de lo simulado vs lo real: `blackwall-real/SIMULADO-VS-REAL.md`. Arranque: `blackwall-real/scripts/bw.sh arriba` → <https://app.localhost:8444>. Secretos y certificados en `~/.local/share/blackwall/` (no en el repo).
- `sigi.html`: **prototipo simulado** (la app se llama **Blackwall**; el archivo conserva el nombre por historial). Keycloak, directorio y API están **simulados en el navegador**. Es lo que está publicado en Netlify; la versión real no se puede publicar ahí (necesita Docker).
- `sigi-con-documentacion.html`: respaldo de la versión anterior con las vistas de documentación (rúbrica, entregables, etc.). No es parte de la app.
- `app-propuestas.html`, `propuestas.html`: propuestas de diseño anteriores (referencia).

## Marca

- Nombre: **Blackwall**. Eslogan: «Nadie cruza sin ser verificado». Cuenta de servicio: `svc-blackwall-sync`.
- Logo elegido: **anillo de tres arcos con candado** en azul UTP (`#003366`, `#0a4d8c`, `#e8f0f9`). Se dibuja en SVG dentro de `sigi.html` (función `LOGO`) y también es el favicon.
- **Publicada en Netlify:** <https://blackwall-utp.netlify.app> (HTTPS automático). Se sube la carpeta `publicar/` (`index.html` = copia de `sigi.html`, más `_headers` con cabeceras de seguridad). Tras cada cambio en `sigi.html`: copiarlo a `publicar/index.html` y volver a arrastrar la carpeta.
- Verificada el 2026-11-23: carga, login con TOTP y vistas funcionan en la URL pública.
- Propuestas de logo (referencia): `logo-anillo.html` (elegido), `logo-corporativo.html`, `logos-corporativos-2.html`, `logos-cyberpunk.html`, `logos-blackwall.html`.

## sigi.html (app Blackwall)

- Flujo: login → verificación TOTP (admin y auditor obligatorio; analista habilitado) → app según rol.
- Secciones: Inicio, Casos, Usuarios, Auditoría, Configuración, Mi cuenta. El menú muestra solo lo permitido, pero la API decide: abrir `#config` sin permiso da 403 y queda en la auditoría.
- Cuentas de demostración (clave `Utp-Acceso-2026!`): campbell.cesar (admin), cruz.irvin y pinto.nicole (analistas), galvez.angel (auditor), cordero.moises (invitado), ejemplo.usuario y ejemplo.usuario2 (rol Usuario, cuentas de ejemplo para reemplazar por nombres reales). `svc-sigi-sync` es la cuenta de servicio, sin login. **Falta un usuario con ROL_USUARIO** (se crea desde Usuarios como admin).
- Matriz 8.1 completa: admin con CRUD de usuarios, casos y comentarios; analista CRU; auditor solo lectura; usuario crea sus casos y edita título/descripción de los suyos mientras estén abiertos ("U limitado"); invitado ve cifras públicas.
- Seguridad: PKCE (S256), state/nonce, redirect_uri exacta, token de 5–15 min con refresh rotativo, bloqueo tras 5 fallos, clave de 12+ sin reutilizar las últimas 5, logout que revoca, deny-by-default, control por propiedad.

## Estado de la versión real (`blackwall-real/`)

Hecho: directorio OpenLDAP (OU por área, grupos `GRP_*`, 7 usuarios + cuenta de servicio, ppolicy: 12+ caracteres, historial 5, bloqueo tras 5), Keycloak (realm `proyecto-accesos`, clientes `cli-blackwall-dev` y `cli-blackwall-sync-dev`, mapeo grupo→rol, TOTP obligatorio para admin y auditor, refresh con rotación, token de 5 min), app PHP con API protegida, 27 casos de prueba (todos pasan), ZAP antes/después y captura de red (0 claves/tokens en claro con HTTPS).
Pendientes anotados (sin hacer, a pedido del usuario, 2026-11-25):
- **Guía técnica en PDF: HECHA (2026-11-25)** → `blackwall-real/docs/Guia-Tecnica-Blackwall.pdf` (46 págs., capturas con números rojos y «qué mirar»: herramientas y su justificación, protocolos, flujo de login, funciones, API, matriz, 27 pruebas, ZAP, captura de red, cumplimiento de la rúbrica, reparto de temas para la exposición y glosario). Fuente en `blackwall-real/docs/guia/` (se regenera con `python3 docs/guia/generar.py`). Es para la compañera que redacta el informe y para repartir la exposición.
- **GENERAR EL INFORME FINAL EN PDF cuando se reinicie el límite de uso del usuario (pedido explícito, 2026-11-25).** Debe ser **corto: unas 10–15 páginas, nada exagerado** (la guía anterior tenía ~50 y fue demasiado). Estructura que pide la guía (sección 14): portada, resumen (máx. 200 palabras), índice, marco teórico breve, diseño (nomenclatura, arquitectura, herramientas justificadas), implementación con capturas, matriz de roles, tabla de pruebas (`evidencias/resultados-pruebas-final.md`) y hallazgos de ZAP (`evidencias/hallazgos-zap.md`), reflexiones (5 preguntas de la sección 13), conclusiones, referencias APA/IEEE, anexos mínimos, **declaración del uso de IA**. Sin contraseñas ni tokens completos. Material listo en `blackwall-real/` (`README.md`, `SIMULADO-VS-REAL.md`, `evidencias/`).
- **Aviso de bloqueo en el login:** tras 5 intentos fallidos Keycloak bloquea la cuenta 1 min, pero la pantalla sigue mostrando el mismo mensaje genérico de credenciales inválidas (no hay aviso visible de bloqueo). Además, con un usuario que no existe nunca se bloquea nada (visto en los eventos: `user_not_found`). Decidir si se muestra un mensaje de bloqueo (a costa de revelar que la cuenta existe).
- **Ocultar el nombre del servidor de identidad en la barra de direcciones:** cambiar `keycloak.localhost:8443` por un nombre neutro (p. ej. `acceso.localhost`); implica regenerar certificados y actualizar compose, `configurar.py`, `Http.php` (RESOLVE_MAP) y las pruebas.
Cambios del 2026-11-25 (tarde): administrador de Keycloak permanente `campbell.cesar` (se eliminó `kcadmin`), PostgreSQL de Keycloak solo con TLS (`verify-full`), prueba CP-27 (historial y longitud de contraseñas).
Pendiente: **informe final en PDF** (portada, marco teórico, diseño, capturas, matriz, tabla de pruebas, reflexiones, referencias) y **actualizar las guías PDF** (`Guia-Completa`/`Guia-Corta`), que todavía describen el prototipo simulado; declarar el uso de IA en el informe (lo exige la guía).

Nomenclatura: usuarios `apellido.nombre`, grupos `GRP_<AREA>_<ROL>`, roles `ROL_*`, cliente `cli-blackwall-dev`, scopes `recurso:accion`.

## Documentos

- `Guia-Completa-Blackwall.pdf` (55 págs.): **la guía larga**, con todo y capturas: qué pide la profesora, protocolos explicados, protocolos → dónde están en la app y verificación (Parte 6), recorrido pantalla por pantalla, cómo se construye la versión real, guion de sustentación, **presentación del avance** (Parte 7: guion, demo, láminas, preguntas, lista de verificación) y anexos. Fuente: `guias/completa.html`.
- `Guia-Corta-Blackwall.pdf` (4 págs.): **resumen y avance**: la idea, roles, recorrido con capturas, protocolos con estado (Cumple/Simulado/Pendiente), dónde estamos y orden de la demo. Fuente: `guias/corta.html`. Las capturas están en `guias/img/` (`g_*` para la guía larga, `p_*` para la demo).
- `archivo-viejo/`: las tres guías anteriores (aún con el nombre «SIGI») y sus fuentes; se pueden borrar.

## Verificación del prototipo simulado (2026-11-23)

28 comprobaciones automáticas del motor de `sigi.html` (login+TOTP, claims del token, bloqueo, token expirado y con firma alterada, RBAC por rol, control por propiedad, deny-by-default, rotación de refresh, logout, política de contraseñas, cuenta de servicio): **todas pasan**. CP-01..CP-08 de la guía pasan en el prototipo; **CP-09 (redirect_uri) y CP-10 (Wireshark) requieren el entorno real** (Keycloak + HTTPS). Diferencias con lo real: firma del JWT con SHA-256 + secreto (no RS256/JWKS), TOTP con hash (no RFC 6238 completo), `state` solo se muestra en el flujo.
