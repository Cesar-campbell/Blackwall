#!/usr/bin/env python3
"""Guía resumida (~20 páginas) de Blackwall. Uso: python3 docs/guia/resumen.py → docs/Guia-Resumida-Blackwall.pdf"""
import json
import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from base import CSS, img, img_ev, nota, tabla, term  # noqa: E402
from s1 import ARQ  # noqa: E402
from s2 import secuencia  # noqa: E402

DOCS = os.path.dirname(AQUI)
RAIZ = os.path.dirname(DOCS)
HTML = os.path.join(AQUI, "resumen.html")
PDF = os.path.join(DOCS, "Guia-Resumida-Blackwall.pdf")
LOGO = '<svg width="54" height="54" viewBox="0 0 64 64"><circle cx="32" cy="32" r="26" fill="none" stroke="#e8f0f9" stroke-width="5" stroke-dasharray="42 12.45" transform="rotate(-80 32 32)"/><circle cx="32" cy="32" r="16" fill="#0a4d8c"/><path d="M26.5 31v-3.5a5.5 5.5 0 0 1 11 0V31" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round"/><rect x="23.5" y="30.5" width="17" height="13" rx="2.5" fill="#fff"/><circle cx="32" cy="36" r="2" fill="#0a4d8c"/><rect x="31.2" y="37" width="1.6" height="3.6" rx=".6" fill="#0a4d8c"/></svg>'
EXTRA = ".shot{margin-left:auto;margin-right:auto}section.sec{break-before:auto;margin-top:7mm}section.sec h1{font-size:16pt;break-after:avoid}section.salto{break-before:page}"

S = []


def sec(n, t, h):
    S.append((n, t, h))


# 1 ----------------------------------------------------------------------------------------------
sec("1", "Qué es Blackwall", f"""
<p class="lead"><b>Blackwall</b> es una aplicación web para <b>gestionar incidentes de seguridad</b>: las personas reportan (phishing, equipos perdidos, accesos sospechosos), los analistas los atienden y el auditor revisa la trazabilidad. Cada quien ve y hace <b>solo lo que su rol permite</b>.</p>
{tabla(["Pilar", "Pregunta", "Cómo se resuelve"], [
    ["<b>Identificación</b>", "¿Quién eres?", "Cuenta <code>apellido.nombre</code> en el directorio, con grupo <code>GRP_*</code> y rol <code>ROL_*</code>"],
    ["<b>Autenticación</b>", "¿Puedes demostrarlo?", "Contraseña validada por el directorio + código TOTP (obligatorio para admin y auditor), con OpenID Connect y PKCE"],
    ["<b>Autorización</b>", "¿Qué puedes hacer?", "Matriz de roles aplicada <b>en el servidor</b>, en cada endpoint, denegando por defecto"],
], anchos=["16%", "20%", "64%"])}
{tabla(["Rol", "Qué puede hacer", "Segundo factor"], [
    ["<code>ROL_ADMIN</code>", "Gestiona usuarios y configuración; opera casos; solo <b>lee</b> la auditoría", "<span class='pill al'>obligatorio</span>"],
    ["<code>ROL_ANALISTA</code>", "Ve, crea y actualiza casos y comenta. No borra ni administra", "<span class='pill mut'>opcional</span>"],
    ["<code>ROL_AUDITOR</code>", "Solo lectura: casos, auditoría y estadísticas", "<span class='pill al'>obligatorio</span>"],
    ["<code>ROL_USUARIO</code>", "Reporta incidentes y ve/edita <b>solo los suyos</b>", "<span class='pill mut'>opcional</span>"],
    ["<code>ROL_INVITADO</code>", "Solo cifras públicas", "<span class='pill mut'>opcional</span>"],
], anchos=["18%", "66%", "16%"])}
{img_ev("admin-inicio.png", "Así se ve la aplicación (administrador)", [(16.5, 22, "Menú según el rol."), (95, 45, "Estadísticas de los casos."), (93, 10, "Usuario, rol y Salir.")], "86%")}
""")

# 2 ----------------------------------------------------------------------------------------------
sec("2", "Arquitectura y dónde se guarda cada dato", f"""
<p>Cuatro servicios en contenedores Docker (sobre Fedora/Nobara), todos con TLS entre sí.</p>
{ARQ}
{tabla(["Dato", "Dónde", "Cómo"], [
    ["Usuarios, grupos y contraseñas", "OpenLDAP", "Contraseña con hash salado <code>{SSHA}</code>"],
    ["Perfil, roles, sesiones y secreto TOTP", "PostgreSQL de Keycloak", "Keycloak no guarda la contraseña"],
    ["Casos, comentarios y auditoría", "SQLite de la app", "Consultas preparadas; dueño por <code>sub</code>"],
    ["Tokens", "Sesión del servidor", "El navegador solo recibe una cookie de sesión segura"],
], anchos=["32%", "28%", "40%"])}
""")

# 3 ----------------------------------------------------------------------------------------------
sec("3", "Herramientas y por qué se eligieron", f"""
{tabla(["Herramienta", "Para qué", "Licencia / costo", "Alternativa descartada"], [
    ["<b>Keycloak 26.8</b>", "Identidad: OIDC, OAuth 2.0, TOTP, federación LDAP", "Apache 2.0 · gratis", "Auth0, Okta, Entra ID (límites y nube)"],
    ["<b>OpenLDAP 2.6</b>", "Directorio y política de contraseñas", "OpenLDAP PL · gratis", "Samba AD, Windows AD DS"],
    ["<b>Docker + Compose</b>", "Despliegue reproducible", "Apache 2.0 · gratis en Linux", "Podman, instalación nativa"],
    ["<b>OpenSSL</b>", "CA propia y certificados TLS", "Apache 2.0 · gratis", "mkcert, Let's Encrypt"],
    ["<b>PHP 8.3 + Apache</b>", "Aplicación y API", "PHP License / Apache 2.0", "Flask + Authlib"],
    ["<b>firebase/php-jwt</b>", "Verificar firmas RS256 (JWKS)", "BSD-3 · gratis", "Firma a mano"],
    ["<b>PostgreSQL · SQLite</b>", "Datos de Keycloak · datos de la app", "Libres · gratis", "H2, MySQL"],
    ["<b>OWASP ZAP</b>", "Escaneo de seguridad", "Apache 2.0 · gratis", "Burp Community"],
    ["<b>tcpdump + tshark</b>", "Captura y análisis de tráfico (Wireshark en consola)", "BSD / GPLv2 · gratis", "Wireshark gráfico"],
    ["<b>Python · Chromium</b>", "Pruebas automáticas y capturas", "PSF · BSD · gratis", "Postman, Selenium"],
], anchos=["20%", "34%", "23%", "23%"])}
{nota("<b>Límite a declarar:</b> la imagen de OpenLDAP usada (<code>bitnamilegacy</code>) ya no recibe actualizaciones; en producción se usaría una mantenida.", "al")}
{tabla(["Elemento", "Formato", "Ejemplo"], [
    ["Usuario", "<code>apellido.nombre</code>", "<code>campbell.cesar</code>"],
    ["Cuenta de servicio", "<code>svc-&lt;app&gt;-&lt;función&gt;</code>", "<code>svc-blackwall-sync</code>"],
    ["Grupo", "<code>GRP_&lt;ÁREA&gt;_&lt;ROL&gt;</code>", "<code>GRP_SOC_ANALISTA</code>"],
    ["Rol · Cliente · Scope", "<code>ROL_*</code> · <code>cli-&lt;app&gt;-&lt;entorno&gt;</code> · <code>recurso:acción</code>", "<code>ROL_AUDITOR</code> · <code>cli-blackwall-dev</code> · <code>casos:leer</code>"],
], anchos=["22%", "40%", "38%"])}
""")

# 4 ----------------------------------------------------------------------------------------------
sec("4", "Protocolos y estándares", f"""
{tabla(["Protocolo", "En palabras simples", "Dónde / prueba"], [
    ["<b>HTTPS / TLS 1.3</b> (RFC 8446)", "El canal va cifrado: nadie en medio lee contraseñas ni tokens", "App, Keycloak, LDAPS y base de datos · captura de red"],
    ["<b>OAuth 2.0</b> (RFC 6749, 9700)", "Permite a una app obtener permisos limitados sin conocer la contraseña", "App ↔ Keycloak · sin Implicit ni Password (CP-15)"],
    ["<b>OpenID Connect</b>", "Añade identidad: el ID token dice quién inició sesión", "Login · validación con <code>nonce</code>"],
    ["<b>PKCE</b> (RFC 7636)", "Secreto de un solo uso: si roban el código, no sirve sin él", "CP-14"],
    ["<b>JWT / JWS / JWKS</b> (RFC 7519, 7515, 7517)", "Token firmado que se verifica con la clave pública de Keycloak (RS256)", "CP-03, CP-04"],
    ["<b>TOTP</b> (RFC 6238)", "Código de 6 dígitos que cambia cada 30 s", "CP-01, CP-11, CP-13"],
    ["<b>LDAP / LDAPS</b> (RFC 4511)", "Consultar y modificar el directorio de usuarios, cifrado", "Keycloak y app ↔ OpenLDAP"],
    ["<b>NIST 800-63B</b>", "Contraseñas de 12+, sin repetir las últimas 5, bloqueo tras 5 fallos", "CP-02, CP-22, CP-27"],
    ["<b>RBAC · mínimo privilegio</b>", "Permisos por rol; solo lo necesario; lo no permitido se rechaza", "CP-05 a CP-08, CP-19 a CP-21"],
    ["<b>OWASP A01</b> (control de acceso roto)", "Impedir acceder a datos ajenos (IDOR/BOLA)", "Control por <code>sub</code> · CP-06, CP-20"],
    ["<b>Cabeceras de seguridad</b> (HSTS, CSP…)", "El navegador fuerza HTTPS y no ejecuta scripts ajenos", "ZAP: 0 medias / 0 bajas"],
    ["<b>Cookies seguras · CSRF</b>", "Cookie <code>Secure; HttpOnly; SameSite</code>; <code>state</code> y token CSRF", "CP-17, CP-18"],
], anchos=["27%", "46%", "27%"])}
""")

# 5 ----------------------------------------------------------------------------------------------
sec("5", "El inicio de sesión paso a paso", f"""
<p>Lo más importante de explicar: <b>la aplicación nunca ve tu contraseña</b>. Se la pide Keycloak y él se la pregunta al directorio.</p>
{secuencia()}
{tabla(["Valor", "Para qué sirve"], [
    ["<code>code_challenge</code> / <code>code_verifier</code> (PKCE)", "El código de autorización solo sirve con el secreto original"],
    ["<code>state</code>", "Une la respuesta con la solicitud (anti-CSRF)"],
    ["<code>nonce</code>", "Une el ID token a este inicio de sesión (anti-reutilización)"],
], anchos=["38%", "62%"])}
""")

# 6 ----------------------------------------------------------------------------------------------
sec("6", "El token, la sesión y el cierre", f"""
<p>Un <b>JWT</b> tiene tres partes: cabecera (algoritmo), datos (quién eres y qué puedes) y firma. Los datos se leen, pero no se pueden alterar sin romper la firma.</p>
{term("jwt-decodificado", "Access token real (firma y datos sensibles redactados)", 34)}
{tabla(["Dato", "Qué comprueba la app"], [
    ["<code>iss</code> · <code>aud</code>", "Que lo emitió Keycloak y que es para esta aplicación"],
    ["<code>exp</code>", "Vence a los 5 minutos: vencido → 401"],
    ["<code>sub</code> · <code>roles</code> · <code>scope</code>", "Quién es, su rol y sus permisos (el rol nunca se toma de la interfaz)"],
], anchos=["30%", "70%"])}
<ul><li><b>Sesión:</b> el navegador solo tiene una cookie; el access token vive en memoria y se renueva solo.</li><li><b>Refresh token:</b> rota en cada uso; reutilizar uno viejo se rechaza (CP-16).</li><li><b>Salir:</b> revoca la sesión en Keycloak, destruye la de la app y exige token CSRF (CP-17).</li></ul>
""")

# 7 ----------------------------------------------------------------------------------------------
sec("7", "El directorio: OpenLDAP", f"""
<p>Fuente única de usuarios y grupos: una OU por área, un grupo <code>GRP_*</code> por rol y la política de contraseñas del directorio (<code>ppolicy</code>).</p>
{term("ldap-grupos", "Grupos y sus miembros", 22)}
{term("ldap-politica", "Política de contraseñas: 12+ caracteres, historial de 5, bloqueo tras 5 fallos")}
{term("ldap-hash", "Una contraseña guardada: hash salado, nunca texto")}
""")

# 8 ----------------------------------------------------------------------------------------------
sec("8", "Keycloak: el proveedor de identidad", f"""
<p><i>Capturas de la consola de administración (está en inglés).</i> Todo se configura por script reproducible.</p>
{img("kc-federacion.png", "Federación con el directorio", "78%", mirar=[(None, None, "<b>directorio-blackwall</b>, tipo LDAP, habilitado."), (None, None, "Keycloak valida contraseñas contra OpenLDAP.")])}
{img("kc-flujos.png", "Flujos de autenticación", "78%", mirar=[(None, None, "<b>browser-blackwall</b> es el flujo en uso."), (None, None, "Tiene ramas de segundo factor obligatorio (admin y auditor) y voluntario.")])}
{img("kc-clientes.png", "Clientes", "78%", mirar=[(None, None, "<b>cli-blackwall-dev</b>: la aplicación (PKCE, sin Implicit)."), (None, None, "<b>cli-blackwall-sync-dev</b>: cuenta de servicio con permisos mínimos.")])}
{tabla(["Requisito de la guía", "Valor"], [
    ["Access token 5–15 min · refresh con rotación", "5 min · rotación activa"],
    ["Bloqueo tras 5 intentos fallidos", "Espera de 60 s, hasta 15 min"],
    ["Mapeo grupo → rol y permisos por rol", "Automático (<i>group mapper</i> + <i>client scopes</i>)"],
], anchos=["60%", "40%"])}
""")

# 9 ----------------------------------------------------------------------------------------------
sec("9", "La aplicación por pantallas (1/2)", f"""
<p>El menú solo muestra lo que el rol puede usar; <b>quien decide es el servidor</b>. Los números rojos indican qué mirar.</p>
{img_ev("admin-login.png", "Pantalla de acceso", [(8, 11, "Logo y nombre."), (3.5, 45, "Leyenda del sistema."), (95.5, 41, "Usuario y contraseña (pantalla del servidor de identidad)."), (95.5, 61, "Entrar; si es admin/auditor pide el código del celular.")], "80%")}
{img_ev("admin-casos.png", "Casos (administrador)", [(16.5, 22, "Menú: estamos en Casos."), (80, 13, "Reportar un incidente."), (97, 40, "Lista de casos."), (97, 31, "<b>Abrir</b> y <b>Borrar</b> (solo admin).")], "80%")}
""")
sec("9b", "La aplicación por pantallas (2/2)", f"""
{img_ev("admin-usuarios.png", "Usuarios del directorio (administrador)", [(80, 13, "Crear un usuario."), (56, 22, "El grupo decide el rol."), (79, 27, "<b>Pendiente</b>: exige segundo factor y aún no lo configura."), (98, 27, "Editar, eliminar, desbloquear.")], "80%")}
{img_ev("admin-auditoria.png", "Auditoría", [(45, 22, "Buscador."), (33.5, 28, "Quién hizo la acción."), (60.5, 28, "<b>Permitido</b> o <b>Denegado</b>."), (74, 28, "Detalle del motivo.")], "80%")}
""")
sec("9c", "La aplicación por pantallas (otros roles)", f"""
{img_ev("analista-denegado.png", "Analista abre Configuración escribiendo la dirección", [(16.5, 26, "El menú no ofrece Configuración..."), (66, 20, "...y aun así el servidor responde <b>403</b>."), (78, 30, "Queda registrado en la auditoría.")], "80%")}
{img_ev("usuario-casos.png", "Usuario: solo ve sus casos", [(16.5, 16, "Menú reducido."), (96, 40, "Solo 3 de los 6 casos: los suyos (control por propiedad)."), (80, 13, "Puede reportar incidentes.")], "80%")}
{img_ev("invitado-inicio.png", "Invitado", [(16.5, 16, "Menú mínimo."), (96, 31, "Solo cifras públicas.")], "80%")}
""")

# 10 ---------------------------------------------------------------------------------------------
sec("10", "Matriz de roles y permisos", f"""
{tabla(["Recurso", "ADMIN", "ANALISTA", "AUDITOR", "USUARIO", "INVITADO"], [
    ["Usuarios", "CRUD", "R", "R", "—", "—"],
    ["Casos", "CRUD", "CRU", "R", "CR propios", "—"],
    ["Comentarios", "CRUD", "CRU", "—", "CR en sus casos", "—"],
    ["Estadísticas", "R", "R", "R", "R lo suyo", "R público"],
    ["Auditoría", "R", "—", "R", "—", "—"],
    ["Configuración", "CRU", "—", "—", "—", "—"],
], anchos=["20%", "14%", "14%", "14%", "24%", "14%"])}
{tabla(["Rol", "Por qué no tiene más (mínimo privilegio)"], [
    ["ADMIN", "Solo <b>lee</b> la auditoría: no puede alterar la huella de sus propias acciones"],
    ["ANALISTA", "Opera el día a día; no borra casos ni administra usuarios"],
    ["AUDITOR", "<b>Separación de funciones</b>: quien audita no opera ni modifica"],
    ["USUARIO", "Control por propiedad: solo accede a registros cuyo <code>sub</code> es el suyo"],
    ["INVITADO", "Acceso mínimo, sin datos internos"],
], anchos=["14%", "86%"])}
{nota("<b>Dos reglas clave:</b> (1) <i>denegar por defecto</i>: ruta no declarada → 404, sin el permiso → 403; (2) la API <b>nunca confía</b> en el rol que muestre la interfaz: lo lee del token firmado.", "ok")}
{tabla(["Endpoint", "Permiso", "Respuestas"], [
    ["<code>GET · POST /api/casos</code>", "<code>casos:leer</code> o <code>leer_propios</code> · <code>crear</code>", "200/201 · 403"],
    ["<code>GET · PUT /api/casos/{id}</code>", "<code>casos:leer</code> / <code>escribir</code> (o <code>_propios</code>)", "200 · 403 · 404"],
    ["<code>DELETE /api/casos/{id}</code>", "<code>casos:borrar</code>", "200 · 403"],
    ["<code>/api/usuarios…</code>", "<code>usuarios:leer</code> (lectura) · <code>usuarios:admin</code> (cambios)", "200/201 · 400 · 403"],
    ["<code>GET /api/auditoria</code> · <code>/api/config</code>", "<code>auditoria:leer</code> · <code>config:admin</code>", "200 · 403"],
], anchos=["34%", "44%", "22%"])}
""")

# 11 ---------------------------------------------------------------------------------------------
sec("11", "El código: qué hace cada parte", f"""
{tabla(["Archivo / función", "Qué hace"], [
    ["<code>Tokens::verificar()</code>", "<b>El guardia</b>: exige RS256, verifica la firma con JWKS y comprueba <code>exp</code>, <code>iss</code>, <code>aud</code>, <code>typ</code> y <code>nonce</code>"],
    ["<code>Oidc::urlLogin()</code> · <code>intercambiar()</code>", "Crea PKCE, <code>state</code> y <code>nonce</code>; cambia el código por tokens con el <code>code_verifier</code>"],
    ["<code>Oidc::renovar()</code> · <code>revocar()</code>", "Renueva con rotación y cierra la sesión en Keycloak"],
    ["<code>Api::autenticar()</code> · <code>exigir()</code>", "Valida el Bearer (401) y comprueba el permiso (403)"],
    ["<code>Api::enrutar()</code>", "Tabla de rutas permitidas; lo demás → 404 (denegar por defecto)"],
    ["<code>Api::esMio()</code>", "Control por propiedad con el <code>sub</code> del token"],
    ["<code>Ldap::crear / actualizar / eliminar</code>", "Administran usuarios y grupos en el directorio"],
    ["<code>Keycloak::eventos()</code>", "Trae inicios de sesión, fallos y bloqueos para la auditoría"],
    ["<code>Db::auditar()</code>", "Registra usuario, acción, permitido/denegado e IP real"],
    ["<code>index.php</code> (<code>/callback</code>, <code>/auth/*</code>)", "Verifica <code>state</code>, valida tokens, regenera la sesión; sesión y logout con CSRF"],
    ["<code>app.js</code>", "Pide todo a la API con Bearer; muestra el 403; no contiene reglas de seguridad"],
    ["<code>keycloak/configurar.py</code>", "Configura Keycloak por API: realm, roles, scopes, clientes, federación, MFA"],
    ["<code>scripts/bw.sh</code> · <code>servidor.sh</code>", "Levantar, probar y publicar la aplicación"],
], anchos=["38%", "62%"])}
""")

# 12 ---------------------------------------------------------------------------------------------
res = json.load(open(os.path.join(RAIZ, "evidencias", "resultados-pruebas-final.json")))
filas = [[c["id"], c["caso"], c["actor"], "<span class='pill ok'>Pasa</span>" if c["ok"] else "<span class='pill no'>Falla</span>"] for c in res["casos"]]
sec("12", f"Pruebas de seguridad: {res['pasan']} de {res['total']} pasan", f"""
<p>CP-01 a CP-10 son los de la guía; CP-11 a CP-27 los agregamos. Se ejecutan contra el sistema real, con login, PKCE y TOTP incluidos: <code>scripts/bw.sh pruebas</code>.</p>
{tabla(["ID", "Caso", "Rol / actor", "Estado"], filas, anchos=["9%", "58%", "21%", "12%"])}
""")

# 13 ---------------------------------------------------------------------------------------------
sec("13", "OWASP ZAP y captura de red", f"""
{img("zap-antes.png", "ZAP ANTES: 0 altas · 2 medias · 4 bajas", "62%")}
{img("zap-despues.png", "ZAP DESPUÉS: 0 altas · 0 medias · 0 bajas", "62%")}
{tabla(["Hallazgo", "Corrección"], [
    ["Sin CSP · sin anti-clickjacking (medias)", "CSP estricta y <code>X-Frame-Options: DENY</code>"],
    ["XSS en JSON · versión visible · sin HSTS · sin <code>nosniff</code> (bajas)", "JSON escapado, <code>ServerTokens Prod</code>, HSTS y <code>nosniff</code>"],
], anchos=["50%", "50%"])}
""")
sec("13b", "Verificación del cifrado (captura de red)", f"""
<p>Se capturó un login real con <b>tcpdump</b> y se analizó con <b>tshark</b> (Wireshark en consola). El <code>.pcap</code> abre en Wireshark.</p>
{term("captura-login", "Con HTTPS: 0 contraseñas y 0 tokens en claro. El control sin TLS sí los muestra")}
{term("db-tls", "La base de datos solo acepta conexiones cifradas")}
""")

# 14 ---------------------------------------------------------------------------------------------
sec("14", "Hallazgos corregidos y antes/después", f"""
{tabla(["Hallazgo", "Detectado por", "Corrección"], [
    ["<b>El auditor podía modificar casos</b> (escalada de privilegios)", "CP-07", "Se eliminó un rol compuesto compartido que le daba permisos del admin"],
    ["El cambio de duración del token no tenía efecto", "CP-03", "Un atributo del cliente pisaba el valor del realm"],
    ["Un cambio de grupo no cambiaba el rol", "CP-23", "Federación LDAP sin caché"],
    ["Eventos de Keycloak ausentes en la auditoría", "CP-02, CP-24", "Scope <code>kc-admin-api</code> con permisos mínimos"],
    ["Errores de PHP visibles al usuario", "CP-02", "<code>display_errors=Off</code>"],
    ["Usuarios mostrados como “cuenta de servicio”", "CP-26", "Lectura corregida del directorio"],
], anchos=["46%", "16%", "38%"])}
{tabla(["Antes (prototipo en el navegador)", "Ahora (real)"], [
    ["Directorio: un objeto JavaScript", "OpenLDAP con LDAPS, grupos y política de contraseñas"],
    ["Keycloak y tokens simulados", "Keycloak real; JWT RS256 con JWKS; refresh rotativo"],
    ["Contraseñas y bloqueo en memoria", "Validados por el directorio; bloqueo real"],
    ["Segundo factor inventado", "TOTP real (RFC 6238), obligatorio por rol"],
    ["API en el navegador", "Backend PHP: valida token y permiso en cada endpoint"],
    ["Datos y auditoría en memoria", "SQLite persistente + eventos de Keycloak"],
    ["Sin HTTPS ni secretos fuera del código", "TLS en todo; secretos en variables de entorno"],
], anchos=["46%", "54%"])}
""")

# 15 ---------------------------------------------------------------------------------------------
sec("15", "Cumplimiento de la rúbrica", f"""
{tabla(["Criterio (peso)", "Estado", "Evidencia"], [
    ["Nomenclatura (15%)", "<span class='pill ok'>Cumple</span>", "Sección 3, sin excepciones"],
    ["Autenticación OAuth/OIDC (25%)", "<span class='pill ok'>Cumple</span>", "PKCE, validación de tokens, MFA, HTTPS, logout · CP-01, 03, 04, 11–18"],
    ["Directorio (15%)", "<span class='pill ok'>Cumple</span>", "LDAP como fuente única, mapeo automático, política · CP-22, 23, 27"],
    ["Autorización (20%)", "<span class='pill ok'>Cumple</span>", "Matriz, mínimo privilegio, denegar por defecto, propiedad · CP-05 a 08, 19 a 21"],
    ["Pruebas y evidencias (10%)", "<span class='pill ok'>Cumple</span>", "27 casos, ZAP antes/después, captura de red"],
    ["Herramientas (5%)", "<span class='pill ok'>Cumple</span>", "Sección 3 (licencia, costo, alternativas)"],
    ["Informe (10%)", "<span class='pill al'>Pendiente</span>", "Lo redacta la compañera con esta guía"],
], anchos=["32%", "14%", "54%"])}
{tabla(["Requisito obligatorio (7.2)", "Estado"], [
    ["HTTPS en todos los componentes (app, Keycloak, LDAPS, base de datos)", "<span class='pill ok'>Sí</span>"],
    ["<code>redirect_uri</code> exacta; sin Implicit ni Password Grant", "<span class='pill ok'>Sí</span>"],
    ["Access token 5–15 min; refresh con rotación", "<span class='pill ok'>Sí</span>"],
    ["Contraseñas 12+, sin repetir las últimas 5, bloqueo tras 5 fallos", "<span class='pill ok'>Sí</span>"],
    ["TOTP obligatorio para ADMIN y AUDITOR", "<span class='pill ok'>Sí</span>"],
    ["Secretos fuera del código · logout que revoque en IdP y app", "<span class='pill ok'>Sí</span>"],
], anchos=["84%", "16%"])}
{nota("<b>Antes de entregar:</b> (1) que el administrador y el auditor configuren su TOTP con su celular en el primer ingreso; (2) el informe en PDF según la sección 14 de la guía, <b>declarando el uso de herramientas de inteligencia artificial</b>; (3) el enlace al repositorio; sin contraseñas ni tokens completos.", "al")}
""")

# 16 ---------------------------------------------------------------------------------------------
sec("16", "Demostración y reparto de temas", f"""
<h2>Guion de la demostración en vivo</h2>
<ol><li><b>Inicio de sesión con cada rol</b> (admin y auditor con TOTP): mostrar cómo cambia el menú.</li><li><b>Intento denegado:</b> con el analista, abrir <code>#config</code> → 403.</li><li><b>Control por propiedad:</b> con <code>ejemplo.usuario</code>, solo aparecen sus casos.</li><li><b>Auditoría:</b> con el auditor, ver el 403 recién generado y los inicios de sesión (incluidos los de otros usuarios).</li><li><b>Bloqueo:</b> cinco claves incorrectas y desbloqueo desde Usuarios.</li></ol>
<h2>Reparto sugerido (todos deben dominar todo)</h2>
{tabla(["Bloque", "Secciones", "Debe saber explicar"], [
    ["1. Visión, arquitectura y Docker", "1, 2", "Qué hace la app, qué corre en cada contenedor, dónde se guarda cada dato"],
    ["2. Directorio y nomenclatura", "3, 7", "Por qué OpenLDAP, cómo se guardan las contraseñas, OU y grupos"],
    ["3. Keycloak y autenticación", "4, 5, 6, 8", "OIDC, PKCE, state, nonce, por qué la app no ve la contraseña, TOTP"],
    ["4. Autorización y código", "9, 10, 11", "RBAC, scope, denegar por defecto, control por propiedad"],
    ["5. Pruebas, ZAP y red", "12, 13, 14", "Qué prueba cada CP, qué encontró ZAP, cómo se verificó el cifrado"],
    ["6. Informe y herramientas", "3, 15", "Por qué estas herramientas, qué falta en la rúbrica, qué cambiar en producción"],
], anchos=["27%", "13%", "60%"])}
<h2>Para producción cambiarían</h2>
<ul><li>Gestor de secretos con rotación y certificados de una CA pública.</li><li>Auditoría centralizada de solo-anexar (SIEM) y copias de seguridad del proveedor de identidad.</li><li>Alta disponibilidad de Keycloak y del directorio, e imagen de OpenLDAP mantenida.</li></ul>
""")

# 17 ---------------------------------------------------------------------------------------------
G = [("Access token", "Token de 5 min que la app envía a la API para probar quién eres y qué puedes hacer."), ("Autenticación", "Comprobar que eres quien dices ser."), ("Autorización", "Decidir qué puedes hacer una vez identificado."),
     ("Bearer", "Forma de enviar el token: <code>Authorization: Bearer …</code>."), ("CA", "Autoridad certificadora: firma certificados (aquí, una propia del laboratorio)."), ("Claim", "Dato dentro de un token (<code>roles</code>, <code>exp</code>…)."),
     ("Client scope", "Permiso nombrado en Keycloak (<code>casos:leer</code>), concedido según el rol."), ("Contenedor", "Programa aislado con todo lo que necesita; Docker los gestiona."), ("Control por propiedad", "Solo accedes a registros cuyo creador eres tú."),
     ("CSP", "Cabecera que limita de dónde carga scripts y estilos el navegador."), ("CSRF", "Ataque en que otra web hace que tu navegador ejecute una acción sin saberlo."), ("Deny-by-default", "Lo no permitido explícitamente se rechaza."),
     ("Directorio", "Base de datos de personas, grupos y permisos (LDAP)."), ("Federación", "Keycloak usa el directorio como fuente de usuarios."), ("Hash salado", "Transformación irreversible de la contraseña con un dato aleatorio."),
     ("HSTS", "Obliga al navegador a usar siempre HTTPS con ese sitio."), ("ID token", "Prueba quién inició sesión; la app lo valida."), ("IdP", "Proveedor de identidad (Keycloak)."),
     ("IDOR / BOLA", "Acceder a datos ajenos cambiando un identificador."), ("JWKS", "Claves públicas para verificar firmas de tokens."), ("JWT", "Token de tres partes: cabecera, datos y firma."),
     ("LDAP / LDAPS", "Protocolo del directorio / su versión cifrada."), ("Mínimo privilegio", "Cada rol recibe solo lo necesario."), ("Nonce", "Valor de un solo uso que liga el ID token a un login."),
     ("OAuth 2.0 / OIDC", "Acceso limitado sin entregar la contraseña / capa de identidad encima."), ("OU", "Unidad organizativa: carpeta del directorio, una por área."), ("PKCE", "Secreto de un solo uso que protege el código de autorización."),
     ("ppolicy", "Módulo de OpenLDAP para política de contraseñas y bloqueo."), ("RBAC", "Control de acceso basado en roles."), ("Realm", "Espacio aislado en Keycloak con sus usuarios y reglas."),
     ("Refresh token", "Permite pedir otro access token; rota en cada uso."), ("redirect_uri", "Dirección de regreso tras el login; debe coincidir exacta."), ("RS256", "Firma RSA con SHA-256; se verifica con clave pública."),
     ("Scope", "Permiso <code>recurso:acción</code> dentro del token."), ("state", "Une la respuesta de Keycloak con la solicitud (anti-CSRF)."), ("sub", "Identificador único e inmutable del usuario."),
     ("TLS", "Cifrado del canal (la “S” de HTTPS)."), ("TOTP", "Código de 6 dígitos que cambia cada 30 s."), ("XSS", "Inyección de scripts maliciosos en una página."), ("ZAP", "Escáner de seguridad web de OWASP.")]
sec("17", "Glosario", tabla(["Término", "Significado"], [[f"<b>{a}</b>", b] for a, b in G], anchos=["22%", "78%"]))


# ------------------------------------------------------------------------------------------------
def etiqueta(n):
    return re.sub(r"[bc]$", "", n)


def construir(pags):
    toc = "".join(f'<div class="row"><b>{n}</b><span class="t">{t}</span><span class="p">{pags.get(n, "")}</span></div>' for n, t, _ in S if not re.search(r"\d[bc]$", n))
    SALTOS = {"7", "8", "9", "13", "13b"}
    cuerpo = "".join(f'<section class="sec{" salto" if n in SALTOS else ""}"><h1>{etiqueta(n)}. {t}</h1>{h}</section>' for n, t, h in S)
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Blackwall · Guía resumida</title><style>{CSS}{EXTRA}</style></head><body>
<div class="cover"><div class="lg">{LOGO}BLACKWALL</div>
<div><div class="eslo">Nadie cruza sin ser verificado</div><h1>Guía resumida de la aplicación</h1><p>Lo esencial para entender, explicar y defender el proyecto: herramientas, protocolos, funciones, pruebas y evidencias.</p></div>
<div class="foot">Proyecto final · Seguridad en accesos: identificación, autenticación y autorización<br>Universidad Tecnológica de Panamá · FISC · Ciberseguridad II<br>Facilitadora: Mildred Echezano</div></div>
<section><h1>Contenido</h1><div class="toc">{toc}</div></section>{cuerpo}</body></html>"""


def a_pdf():
    subprocess.run(["chromium-browser", "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={PDF}", "--virtual-time-budget=20000", "file://" + HTML], capture_output=True, text=True, timeout=300)
    if not os.path.exists(PDF):
        sys.exit("No se generó el PDF")


def paginas():
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", PDF], capture_output=True, text=True).stdout).group(1))
    tx = {p: subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), "-layout", PDF, "-"], capture_output=True, text=True).stdout for p in range(3, n + 1)}
    res = {}
    for num, t, _ in S:
        if re.search(r"\d[bc]$", num):
            continue
        plano = re.sub(r"<[^>]+>", "", t)[:24]
        for p in range(3, n + 1):
            if re.search(rf"^\s*{re.escape(etiqueta(num))}\.\s+{re.escape(plano)}", tx[p], re.M):
                res[num] = p
                break
    return res, n


open(HTML, "w").write(construir({}))
a_pdf()
pags, total = paginas()
open(HTML, "w").write(construir(pags))
a_pdf()
print("páginas:", total, "· secciones localizadas:", len(pags))
print(PDF)
