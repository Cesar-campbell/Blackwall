# Hallazgos de OWASP ZAP: antes y después

Escaneo con ZAP (Automation Framework, Docker): requestor + spider + passive + **active scan**, autenticado como `ejemplo.usuario` (mínimo privilegio) y sin sesión. Informes completos: `zap-antes.html` / `zap-despues.html` (y `.json`).

| Riesgo | Alerta (CWE) | Antes | Después | Corrección |
|---|---|---|---|---|
| Medium | Content Security Policy (CSP) Header Not Set (693) | 2 | 0 | `Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'`. Se pudo sin `unsafe-inline`: la UI no usa estilos ni scripts en línea (las barras se dimensionan por CSSOM) |
| Medium | Missing Anti-clickjacking Header (1021) | 2 | 0 | `X-Frame-Options: DENY` + `frame-ancestors 'none'` |
| Low | Cross Site Scripting Weakness (Persistent in JSON Response) (79) | 2 | 0 | ZAP guardó cargas `<script>` como casos y la API las devolvía con `<` y `>` sin escapar. Ahora el JSON sale con `JSON_HEX_TAG\|AMP\|APOS\|QUOT` (`<`…) y con `X-Content-Type-Options: nosniff`. La interfaz además escapa todo con `esc()` |
| Low | Server Leaks Version Information (497) | 5 | 0 | `ServerTokens Prod`, `ServerSignature Off`, `expose_php=Off` |
| Low | Strict-Transport-Security Header Not Set (319) | 5 | 0 | `Strict-Transport-Security: max-age=31536000; includeSubDomains` |
| Low | X-Content-Type-Options Header Missing (693) | 5 | 0 | `X-Content-Type-Options: nosniff` |
| Info | Re-examine Cache-control Directives (525) | 5 | 0 | `Cache-Control: no-store, no-cache, must-revalidate, private` (una sola vez, desde Apache) |
| Info | Information Disclosure – Suspicious Comments (615) | 1 | 1 | Aceptado: es el comentario de cabecera de `app.js`; no contiene datos sensibles |
| Info | Session Management Response Identified (-1) | 3 | 2 | Informativa: ZAP detecta la cookie de sesión `__Host-bw` (`Secure; HttpOnly; SameSite=Lax`, prefijo `__Host-`) |
| Info | User Agent Fuzzer (0) | 3 | 3 | Informativa: ZAP prueba distintos User-Agent; sin diferencias de comportamiento |

**Totales:** antes → 0 altas · 2 medias · 4 bajas · 4 informativas; después → 0 altas · 0 medias · 0 bajas · 3 informativas.

Notas honestas: el escaneo cubre la superficie de la aplicación (`app.localhost:8444`); Keycloak y OpenLDAP son productos de terceros y no se escanearon. ZAP se ejecutó con `sslAcceptAll` porque el certificado lo firma la CA del laboratorio.
