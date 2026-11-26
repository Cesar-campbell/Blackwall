from base import duo, img, img_ev, nota, tabla, term


def secuencia():
    cols = {"Navegador": 70, "Aplicación": 270, "Keycloak": 480, "Directorio": 680}
    msgs = [
        ("Navegador", "Aplicación", "1  Abre la app (sin sesión)"),
        ("Aplicación", "Navegador", "2  Redirige a Keycloak: code_challenge, state, nonce"),
        ("Navegador", "Keycloak", "3  Pide la pantalla de acceso"),
        ("Navegador", "Keycloak", "4  Envía usuario y contraseña"),
        ("Keycloak", "Directorio", "5  ¿Es correcta la contraseña? (LDAPS)"),
        ("Keycloak", "Navegador", "6  Pide el código TOTP (admin y auditor)"),
        ("Navegador", "Keycloak", "7  Envía el código de 6 dígitos"),
        ("Keycloak", "Navegador", "8  Redirige a /callback con code + state"),
        ("Navegador", "Aplicación", "9  Entrega code + state a la app"),
        ("Aplicación", "Keycloak", "10  POST /token: code + code_verifier"),
        ("Keycloak", "Aplicación", "11  ID token + access token + refresh token"),
        ("Aplicación", "Aplicación", "12  Valida firma, iss, aud, exp y nonce"),
        ("Aplicación", "Navegador", "13  Cookie de sesión: entra a la app"),
    ]
    h = 58 + 27 * len(msgs)
    o = [f'<svg viewBox="0 0 760 {h}" width="100%" role="img" aria-label="Secuencia de inicio de sesión"><defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z" fill="#0a4d8c"/></marker></defs>']
    for n, x in cols.items():
        o.append(f'<rect x="{x-50}" y="4" width="100" height="26" rx="6" fill="#003366"/><text x="{x}" y="22" text-anchor="middle" fill="#fff" font-size="11" font-weight="700">{n}</text>')
        o.append(f'<line x1="{x}" y1="30" x2="{x}" y2="{h-6}" stroke="#9db4cf" stroke-dasharray="4 3"/>')
    y = 56
    for a, b, t in msgs:
        xa, xb = cols[a], cols[b]
        if a == b:
            o.append(f'<rect x="{xa+6}" y="{y-12}" width="190" height="18" rx="4" fill="#e6f6ec" stroke="#16803c"/><text x="{xa+12}" y="{y+1}" font-size="9.5" fill="#16803c" font-weight="600">{t}</text>')
        else:
            o.append(f'<line x1="{xa}" y1="{y}" x2="{xb + (-7 if xb > xa else 7)}" y2="{y}" stroke="#0a4d8c" stroke-width="1.5" marker-end="url(#a)"/>')
            tx = (xa + xb) / 2
            o.append(f'<text x="{tx}" y="{y-5}" text-anchor="middle" font-size="9.5" fill="#18222e">{t}</text>')
        y += 27
    o.append("</svg>")
    return "".join(o)


def secciones():
    s = []
    P = [
        ["<b>HTTPS / TLS 1.3</b>", "RFC 8446", "El canal va cifrado: nadie en medio puede leer contraseñas ni tokens.", "App, Keycloak, LDAPS y PostgreSQL (certificados propios)", "Captura de red: 0 contraseñas en claro"],
        ["<b>Certificados X.509</b>", "RFC 5280", "Un “carné” digital que prueba que el servidor es quien dice ser, firmado por una CA.", "CA propia + 3 certificados de servidor", "<code>openssl s_client … Verification: OK</code>"],
        ["<b>OAuth 2.0</b>", "RFC 6749 · RFC 9700", "Marco para que una app obtenga permisos limitados sin conocer la contraseña.", "App ↔ Keycloak", "Flujo Authorization Code; sin Implicit ni Password"],
        ["<b>OpenID Connect 1.0</b>", "OIDC Core", "Capa sobre OAuth que añade <i>identidad</i>: el ID token dice quién inició sesión.", "Login de la app", "ID token validado con <code>nonce</code>"],
        ["<b>PKCE (S256)</b>", "RFC 7636", "La app inventa un secreto de un solo uso (<code>code_verifier</code>); si alguien roba el código, no sirve sin él.", "Inicio de sesión", "CP-14"],
        ["<b>JWT / JWS</b>", "RFC 7519 · 7515", "El token es un texto con 3 partes (cabecera, datos, firma) que se puede verificar.", "Access token e ID token", "Sección 9, token decodificado"],
        ["<b>JWKS (RS256)</b>", "RFC 7517 · 7518", "Keycloak firma con una clave privada y publica la clave pública para verificar.", "<code>Tokens.php</code>", "CP-04: firma alterada → 401"],
        ["<b>Bearer token</b>", "RFC 6750", "La API recibe el token en la cabecera <code>Authorization: Bearer …</code>.", "Todos los <code>/api/*</code>", "CP-03, CP-04"],
        ["<b>Cierre de sesión OIDC</b>", "RP-Initiated Logout", "Cerrar sesión también en el servidor de identidad, no solo en la app.", "<code>/auth/logout</code>", "CP-17"],
        ["<b>TOTP</b>", "RFC 6238 (HOTP RFC 4226)", "Código de 6 dígitos que cambia cada 30 s, calculado con un secreto compartido y la hora.", "Segundo factor", "CP-01, CP-11, CP-13"],
        ["<b>LDAP / LDAPS</b>", "RFC 4511", "Protocolo para consultar y modificar un directorio de usuarios; LDAPS lo cifra.", "Keycloak y la app ↔ OpenLDAP", "<code>ldapsearch</code> en la sección 6"],
        ["<b>Política de contraseñas</b>", "NIST SP 800-63B", "Largas (12+), sin repetir las últimas 5, bloqueo tras 5 fallos.", "<code>ppolicy</code> + Keycloak", "CP-02, CP-22"],
        ["<b>Hash salado (SSHA)</b>", "—", "La contraseña se guarda transformada de forma irreversible, con sal aleatoria.", "OpenLDAP", "Sección 6"],
        ["<b>RBAC</b>", "INCITS 359", "Los permisos se asignan a roles, no a personas.", "Matriz de roles en la API", "CP-05 a CP-08, CP-19 a CP-21"],
        ["<b>Mínimo privilegio · denegar por defecto</b>", "Principio", "Cada rol recibe solo lo necesario; lo no permitido explícitamente se rechaza.", "Cada endpoint", "Ruta desconocida → 404; sin scope → 403"],
        ["<b>OWASP A01 · Control de acceso roto</b>", "OWASP Top 10:2021", "El riesgo nº 1: que alguien acceda a datos o funciones que no le tocan (IDOR/BOLA).", "Control por propiedad con <code>sub</code>", "CP-06, CP-20"],
        ["<b>Cabeceras de seguridad</b>", "RFC 6797 (HSTS) · CSP", "Le dicen al navegador que fuerce HTTPS, no incruste la página y no ejecute scripts ajenos.", "<code>apache.conf</code>", "ZAP: 0 medias / 0 bajas"],
        ["<b>Cookies seguras</b>", "RFC 6265bis", "La cookie de sesión va <code>Secure; HttpOnly; SameSite=Lax</code> y con prefijo <code>__Host-</code>.", "<code>Sesion.php</code>", "Cabecera <code>Set-Cookie</code>"],
        ["<b>CSRF</b>", "—", "Impedir que otra web haga acciones por ti: <code>state</code> en el login y token CSRF en el logout.", "<code>/callback</code>, <code>/auth/logout</code>", "CP-17, CP-18"],
    ]
    s.append(("8", "Protocolos y estándares: qué son y dónde se usan", f"""
<p class="lead">Esta tabla es el mapa de todo lo que hay detrás de la aplicación. Cada fila dice <b>qué es en palabras simples</b>, <b>dónde está en el proyecto</b> y <b>qué prueba lo demuestra</b>.</p>
{tabla(["Protocolo / estándar", "Referencia", "En palabras simples", "Dónde se usa", "Cómo comprobarlo"], P, anchos=["18%", "13%", "33%", "19%", "17%"])}
{nota("<b>Para la exposición:</b> no hace falta memorizar los números de RFC; sí saber explicar con tus palabras lo que dice la columna “En palabras simples” y señalar dónde se ve.")}
"""))

    s.append(("9", "El inicio de sesión paso a paso", f"""
<p>Es lo más importante de explicar. La clave: <b>la aplicación nunca ve tu contraseña</b>. Se la pide Keycloak, y Keycloak le pregunta al directorio.</p>
{secuencia()}
<h2>En palabras simples</h2>
<ol>
<li>La app te manda a Keycloak con tres cosas: un <b>desafío PKCE</b> (un secreto de un solo uso, escondido), un <b><code>state</code></b> (para saber que la respuesta es de <i>esta</i> solicitud) y un <b><code>nonce</code></b> (para que el ID token no se pueda reutilizar).</li>
<li>Keycloak valida contraseña (contra el directorio) y, si eres admin o auditor, el código de tu celular.</li>
<li>Keycloak devuelve a la app un <b>código de un solo uso</b>. Solo sirve si la app presenta el secreto PKCE original.</li>
<li>La app cambia el código por <b>tokens</b> y los verifica: firma, emisor, destinatario, vencimiento y nonce. Recién ahí crea su propia sesión.</li>
</ol>
<h2>Las direcciones que Keycloak publica</h2>
{term("oidc-discovery", "Documento de descubrimiento OpenID Connect (campos clave)")}
{term("oidc-jwks", "Claves públicas para verificar firmas (JWKS)")}
"""))

    s.append(("10", "El token por dentro, sesión, renovación y cierre", f"""
<p>Un <b>JWT</b> son tres partes separadas por puntos: <b>cabecera</b> (algoritmo y clave usada), <b>datos</b> (quién eres, qué permisos tienes, cuándo vence) y <b>firma</b> (prueba de que no fue alterado). Los datos se pueden leer, pero no modificar sin que la firma falle.</p>
{term("jwt-decodificado", "Access token real de un usuario (firma y datos sensibles redactados)")}
{tabla(["Dato del token", "Qué significa", "Quién lo comprueba"], [
    ["<code>iss</code>", "Quién lo emitió (Keycloak, realm proyecto-accesos)", "La app: debe coincidir exactamente"],
    ["<code>aud</code>", "Para quién es (cli-blackwall-dev)", "La app: si no coincide, se rechaza"],
    ["<code>exp</code> / <code>iat</code>", "Vence a los 5 minutos / cuándo se emitió", "La app: token vencido → 401"],
    ["<code>sub</code>", "Identificador único e inmutable del usuario", "Control por propiedad (dueño del caso)"],
    ["<code>roles</code>, <code>groups</code>", "Rol y grupo del usuario", "La API (el rol nunca se toma de la interfaz)"],
    ["<code>scope</code>", "Lista de permisos <code>recurso:acción</code>", "Cada endpoint exige el suyo"],
    ["<code>typ</code>", "<code>Bearer</code> (acceso) o <code>ID</code> (identidad)", "La API rechaza un ID token como si fuera de acceso"],
], anchos=["22%", "45%", "33%"])}
<h2>Sesión y renovación</h2>
<ul>
<li>El navegador solo tiene una <b>cookie de sesión</b> (<code>__Host-bw</code>). Los tokens están en el servidor.</li>
<li>El <b>access token</b> (5 min) se guarda en memoria de la página y se envía a la API. Antes de vencer, la página pide uno nuevo.</li>
<li>El <b>refresh token</b> <b>rota</b>: cada vez que se usa, el anterior queda inválido. Si alguien lo roba y lo reutiliza, Keycloak lo rechaza (CP-16).</li>
</ul>
<h2>Cierre de sesión</h2>
<p>Al pulsar <b>Salir</b>: la app revoca la sesión en Keycloak (el refresh token deja de servir), destruye su propia sesión y lleva al navegador a cerrar la sesión de Keycloak. Se exige un token anti-CSRF para que otra web no pueda cerrarla (CP-17).</p>
"""))

    s.append(("11", "La aplicación por pantallas", f"""
<p>La interfaz es la misma para todos; el <b>menú lateral</b> solo muestra lo que el rol puede usar. Pero lo que realmente decide es el servidor: si alguien abre una sección sin permiso, la API responde <b>403</b> y queda registrado en la auditoría. <i>Los números rojos indican qué mirar en cada pantalla.</i></p>
{img_ev("admin-login.png", "Pantalla de acceso", [
    (8, 11, "Logo y nombre de la aplicación."),
    (3.5, 45, "Leyenda: de qué trata el sistema."),
    (95.5, 41, "Aquí se escribe el usuario y la contraseña. <b>Esta pantalla la entrega el servidor de identidad</b>, no la app."),
    (95.5, 61, "Entrar: si eres administrador o auditor, después pide el código de 6 dígitos del celular."),
])}
{img_ev("admin-inicio.png", "Inicio del administrador", [
    (16.5, 22, "Menú lateral: el administrador ve todas las secciones."),
    (95, 19, "Mensaje de bienvenida que explica el rol."),
    (95, 30, "Accesos rápidos a lo que más usa este rol."),
    (95, 45, "Estadísticas de todos los casos, por estado y severidad."),
    (93, 10, "Quién eres y con qué rol; <b>Salir</b> cierra la sesión."),
])}
{img_ev("admin-casos.png", "Casos de incidentes (administrador)", [
    (16.5, 22, "Menú: aquí estamos en Casos."),
    (80, 13, "Reportar un incidente nuevo."),
    (61, 22, "Buscador y filtro por estado."),
    (97, 40, "Lista de casos: título, severidad, estado y quién lo reportó."),
    (97, 31, "<b>Abrir</b> para ver el detalle; <b>Borrar</b> solo aparece para el administrador."),
])}
{img_ev("admin-caso.png", "Detalle de un caso", [
    (71, 24, "Título, severidad, estado y quién lo reportó."),
    (71, 41, "El administrador y el analista pueden cambiar estado y severidad."),
    (71, 60, "Comentarios del caso."),
    (71, 66, "Borrar un comentario: solo el administrador."),
])}
{img_ev("admin-usuarios.png", "Usuarios del directorio (administrador)", [
    (80, 13, "Crear un usuario nuevo."),
    (56, 22, "Grupo del directorio: de él sale el rol."),
    (79, 27, "<b>Pendiente</b>: este rol exige segundo factor y la persona aún no lo configura."),
    (98, 27, "Editar, eliminar y (si está bloqueado) desbloquear."),
])}
{img_ev("admin-usuario-nuevo.png", "Alta de un usuario", [
    (71, 35, "Usuario con formato <code>apellido.nombre</code>."),
    (71, 56, "El grupo decide el rol: el sistema lo asigna solo."),
    (71, 64, "Contraseña inicial (mínimo 12 caracteres; el directorio la valida)."),
    (71, 71, "Crear: se escribe en el directorio."),
])}
{img_ev("admin-auditoria.png", "Auditoría", [
    (45, 22, "Buscador por usuario o evento."),
    (33.5, 28, "Quién hizo la acción."),
    (60.5, 28, "<b>Permitido</b> (verde) o <b>Denegado</b> (rojo)."),
    (74, 28, "Detalle: por qué se permitió o se negó."),
])}
{img_ev("admin-config.png", "Configuración de seguridad (solo administrador)", [
    (56, 27, "Cuánto dura la sesión activa (5 a 15 minutos)."),
    (56, 35, "Intentos fallidos antes de bloquear la cuenta."),
    (56, 44, "Cuánto dura el bloqueo."),
    (34, 51, "Guardar: el cambio se aplica de inmediato."),
])}
"""))

    s.append(("11b", "La aplicación por pantallas (otros roles)", f"""
<p>Mismas pantallas, vistas con otros roles. Fíjate en lo que <b>falta</b> en cada menú: es el mínimo privilegio en acción.</p>
{img_ev("analista-inicio.png", "Analista", [
    (16.5, 22, "Menú: tiene Usuarios, pero no Auditoría ni Configuración."),
    (95, 20, "El mensaje recuerda lo que este rol no puede hacer."),
    (95, 29, "Accesos: ver casos, reportar y ver usuarios."),
])}
{img_ev("analista-denegado.png", "Analista intenta entrar a Configuración (escribiendo la dirección a mano)", [
    (16.5, 26, "El menú no ofrece Configuración..."),
    (66, 20, "...y aun escribiendo la dirección, el servidor responde <b>403</b>."),
    (78, 30, "El motivo (falta el permiso) y aviso de que quedó registrado en la auditoría."),
])}
{img_ev("auditor-inicio.png", "Auditor", [
    (16.5, 27, "Menú: tiene Auditoría; no puede crear ni modificar nada."),
    (95, 20, "Rol de solo lectura: quien audita no opera."),
])}
{img_ev("usuario-casos.png", "Usuario: solo ve los casos que reportó", [
    (16.5, 16, "Menú reducido: sin Usuarios ni Auditoría."),
    (96, 40, "Solo 3 de los 6 casos: los suyos (control por propiedad)."),
    (80, 13, "Puede reportar incidentes."),
])}
{img_ev("usuario-caso.png", "Usuario editando su propio caso abierto", [
    (71, 25, "Puede corregir título y descripción de <b>su</b> caso mientras siga abierto."),
    (71, 62, "Puede comentar, pero no borrar comentarios."),
])}
{img_ev("invitado-inicio.png", "Invitado", [
    (16.5, 16, "Menú mínimo: solo Inicio y Mi cuenta."),
    (96, 31, "Únicamente cifras públicas, sin datos internos."),
])}
{img_ev("admin-cuenta.png", "Mi cuenta", [
    (97, 30, "Tus datos y tu rol."),
    (79, 46, "Segundo factor: obligatorio para este rol."),
    (37, 63, "Cambiar contraseña: reglas de 12+ caracteres y sin repetir las últimas 5."),
    (88, 14, "Cerrar sesión."),
])}
"""))

    s.append(("12", "Matriz de roles y permisos", f"""
<p>La matriz sale de lo que cada rol <i>necesita</i> para trabajar (mínimo privilegio). Un <b>scope</b> es un permiso con forma <code>recurso:acción</code>. Los que terminan en <code>_propios</code> funcionan solo sobre registros cuyo <code>sub</code> es el del propio usuario.</p>
{tabla(["Recurso", "ADMIN", "ANALISTA", "AUDITOR", "USUARIO", "INVITADO"], [
    ["Usuarios del sistema", "CRUD <code>usuarios:admin</code>", "R <code>usuarios:leer</code>", "R <code>usuarios:leer</code>", "—", "—"],
    ["Casos de incidentes", "CRUD <code>casos:leer/escribir/borrar</code>", "CRU <code>casos:leer/escribir</code>", "R <code>casos:leer</code>", "CR propios <code>casos:crear / leer_propios / escribir_propios</code>", "—"],
    ["Comentarios en casos", "CRUD <code>comentarios:escribir/borrar</code>", "CRU <code>comentarios:escribir</code>", "—", "CR solo en sus casos <code>comentarios:escribir_propios</code>", "—"],
    ["Panel de estadísticas", "R <code>estadisticas:leer</code>", "R <code>estadisticas:leer</code>", "R <code>estadisticas:leer</code>", "R solo lo suyo <code>estadisticas:leer_propios</code>", "R público <code>estadisticas:publicas</code>"],
    ["Registros de auditoría", "R <code>auditoria:leer</code>", "—", "R <code>auditoria:leer</code>", "—", "—"],
    ["Configuración del sistema", "CRU <code>config:admin</code>", "—", "—", "—", "—"],
], anchos=["17%", "19%", "16%", "14%", "21%", "13%"])}
<h2>Justificación por rol (mínimo privilegio)</h2>
{tabla(["Rol", "Necesidad", "Por qué no tiene más"], [
    ["ADMIN", "Administrar cuentas y configuración", "Solo <b>lee</b> la auditoría: así no puede alterar la huella de sus propias acciones."],
    ["ANALISTA", "Gestionar y resolver casos", "No borra casos ni administra usuarios: opera el día a día, nada más."],
    ["AUDITOR", "Revisar cumplimiento y trazabilidad", "Solo lectura: <b>separación de funciones</b>, quien audita no opera ni modifica."],
    ["USUARIO", "Reportar incidentes propios y ver su estado", "Control por propiedad: aunque tenga el scope, solo accede a registros cuyo <code>sub</code> es el suyo."],
    ["INVITADO", "Consultar información pública", "Acceso mínimo, sin datos internos."],
], anchos=["12%", "30%", "58%"])}
{nota("<b>Dos reglas que hay que saber explicar:</b> (1) <i>denegar por defecto</i>: toda ruta que no está declarada responde 404 y toda acción sin el scope exigido responde 403; (2) la API <b>nunca confía</b> en el rol que muestre la interfaz: lo lee del token firmado.", "ok")}
"""))

    s.append(("13", "La API: todos los endpoints", f"""
<p>Todas las rutas <code>/api/*</code> aceptan <b>solo</b> <code>Authorization: Bearer</code> (nunca cookies). Primero se valida el token (401 si falla) y luego se exige el scope (403 si falta).</p>
{tabla(["Método y ruta", "Scope exigido", "Respuestas", "Notas"], [
    ["<code>GET /api/yo</code>", "cualquier token válido", "200", "Devuelve sub, usuario, roles y scopes"],
    ["<code>GET /api/casos</code>", "<code>casos:leer</code> o <code>casos:leer_propios</code>", "200 / 403", "Con <i>propios</i>, filtra por <code>sub</code>"],
    ["<code>POST /api/casos</code>", "<code>casos:escribir</code> o <code>casos:crear</code>", "201 / 400 / 403", "Título ≤120, descripción ≤2000, severidad validada"],
    ["<code>GET /api/casos/{id}</code>", "<code>casos:leer</code> o <code>leer_propios</code>", "200 / 403 / 404", "Un caso ajeno devuelve 404 (no revela que existe)"],
    ["<code>PUT /api/casos/{id}</code>", "<code>casos:escribir</code> o <code>escribir_propios</code>", "200 / 400 / 403 / 404", "Usuario: solo suyo, abierto, solo título/descripción"],
    ["<code>DELETE /api/casos/{id}</code>", "<code>casos:borrar</code>", "200 / 403 / 404", "Solo administrador"],
    ["<code>POST /api/casos/{id}/comentarios</code>", "<code>comentarios:escribir</code> o <code>escribir_propios</code>", "201 / 400 / 404", "Usuario: solo en casos propios"],
    ["<code>PUT /api/casos/{id}/comentarios/{n}</code>", "<code>comentarios:escribir</code>", "200 / 404", "Editar"],
    ["<code>DELETE /api/casos/{id}/comentarios/{n}</code>", "<code>comentarios:borrar</code>", "200 / 403 / 404", "Solo administrador"],
    ["<code>GET /api/estadisticas</code>", "<code>estadisticas:leer / leer_propios / publicas</code>", "200 / 403", "Cambia el alcance según el scope"],
    ["<code>GET /api/usuarios</code>", "<code>usuarios:leer</code> o <code>usuarios:admin</code>", "200 / 403", "Lee el directorio; marca MFA y bloqueo"],
    ["<code>POST /api/usuarios</code>", "<code>usuarios:admin</code>", "201 / 400 / 403", "Valida <code>apellido.nombre</code>, clave de 12+ y grupo"],
    ["<code>PUT /api/usuarios/{id}</code>", "<code>usuarios:admin</code>", "200 / 400 / 404", "Cambia nombre y grupo; no a uno mismo"],
    ["<code>DELETE /api/usuarios/{id}</code>", "<code>usuarios:admin</code>", "200 / 400 / 404", "No a uno mismo ni a la cuenta de servicio"],
    ["<code>POST /api/usuarios/{id}/desbloquear</code>", "<code>usuarios:admin</code>", "200", "Quita el bloqueo en directorio y Keycloak"],
    ["<code>GET /api/auditoria</code>", "<code>auditoria:leer</code>", "200 / 403", "Une la auditoría de la app y los eventos de Keycloak"],
    ["<code>GET · PUT /api/config</code>", "<code>config:admin</code>", "200 / 400 / 403", "Vida del token 5–15 min, intentos 3–10, bloqueo 10–3600 s"],
], anchos=["31%", "28%", "14%", "27%"])}
{term("http-api-sin-token", "Sin token la API responde 401 y no revela nada")}
{term("http-cabeceras", "Cabeceras de seguridad que envía la aplicación")}
"""))
    return s
