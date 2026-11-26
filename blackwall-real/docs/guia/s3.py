import json
import os

from base import AQUI, duo, esc, img, nota, tabla, term

RAIZ = os.path.dirname(os.path.dirname(AQUI))


def f(rows):
    return tabla(["Función", "Qué hace"], rows, anchos=["33%", "67%"])


def secciones():
    s = []

    s.append(("14", "El código del servidor (PHP): qué funciones hay", f"""
<p>Son 9 archivos pequeños en <code>app/src/</code> más el controlador frontal <code>app/public/index.php</code>. Cada uno hace <b>una sola cosa</b>.</p>
{term("codigo-lineas", "Tamaño del código propio")}
<h2>Config.php · Http.php · Sesion.php · Db.php</h2>
{f([
    ["<code>Config::get(clave)</code>", "Lee un ajuste de las variables de entorno; falla si falta (así los secretos nunca están en el código)."],
    ["<code>Http::pedir(...)</code> / <code>Http::json(...)</code>", "Hace peticiones HTTPS con cURL <b>verificando el certificado</b> contra la CA del laboratorio."],
    ["<code>Sesion::iniciar()</code>", "Abre la sesión con cookie <code>__Host-bw</code> (Secure, HttpOnly, SameSite=Lax, modo estricto)."],
    ["<code>Sesion::destruir()</code>", "Borra la sesión y la cookie (cierre de sesión)."],
    ["<code>Db::pdo()</code>", "Abre SQLite, crea las tablas (casos, comentarios, auditoría) y siembra casos de ejemplo la primera vez."],
    ["<code>Db::idCaso()</code> / <code>numCaso()</code>", "Convierten entre el número interno y el formato <code>INC-007</code> (y rechazan formatos raros)."],
    ["<code>Db::auditar(...)</code>", "Anota un evento: usuario, acción, permitido/denegado, detalle e IP."],
])}
<h2>Oidc.php · Tokens.php (autenticación)</h2>
{f([
    ["<code>Oidc::descubrir()</code>", "Descarga (y guarda 1 h) las direcciones de Keycloak desde el documento de descubrimiento."],
    ["<code>Oidc::urlLogin()</code>", "Crea <code>code_verifier</code>, <code>state</code> y <code>nonce</code> aleatorios, los guarda en la sesión y arma la URL de Keycloak con el desafío PKCE (S256)."],
    ["<code>Oidc::intercambiar(code)</code>", "Cambia el código por tokens enviando el <code>code_verifier</code> y el secreto del cliente."],
    ["<code>Oidc::renovar(refresh)</code>", "Pide un access token nuevo; Keycloak rota el refresh token."],
    ["<code>Oidc::revocar(refresh)</code>", "Cierra la sesión en Keycloak (back-channel)."],
    ["<code>Oidc::urlCierreSesion(idToken)</code>", "URL para que el navegador cierre también la sesión de Keycloak y regrese a la app."],
    ["<code>Tokens::verificar(jwt, tipo, nonce)</code>", "<b>El guardia.</b> Exige RS256 con <code>kid</code>, verifica la firma con el JWKS, y comprueba <code>exp</code>, <code>iss</code>, <code>aud</code>, <code>typ</code> y (para el ID token) <code>nonce</code>. Rechaza <code>alg=none</code> y HS256."],
    ["<code>Tokens::claves()</code>", "Obtiene las claves públicas y las guarda 10 min; si aparece una clave nueva (rotación), recarga."],
])}
<h2>Ldap.php · Keycloak.php (integraciones)</h2>
{f([
    ["<code>Ldap::listar()</code>", "Lee todas las personas y grupos del directorio y deduce el rol de cada una."],
    ["<code>Ldap::crear(...)</code>", "Crea el usuario en la OU de su área y lo agrega a su grupo; el directorio aplica la política de contraseñas."],
    ["<code>Ldap::actualizar(...)</code>", "Cambia nombre y grupo (primero agrega al nuevo grupo, luego quita del anterior: nunca queda sin rol por error)."],
    ["<code>Ldap::eliminar(...)</code>", "Quita al usuario de su grupo y borra su entrada."],
    ["<code>Ldap::desbloquear(...)</code>", "Quita el bloqueo de la política de contraseñas."],
    ["<code>Keycloak::admin(...)</code>", "Llama a la API de administración con la cuenta de servicio (client credentials, token en caché)."],
    ["<code>Keycloak::eventos()</code>", "Trae inicios de sesión, fallos y bloqueos y los traduce al formato de la auditoría."],
    ["<code>Keycloak::tieneOtp() / bloqueado() / desbloquear()</code>", "Estado del segundo factor y del bloqueo de un usuario."],
    ["<code>Keycloak::realm() / actualizarRealm()</code>", "Leen y cambian los parámetros de seguridad (pantalla Configuración)."],
])}
<h2>Api.php (autorización) e index.php (rutas)</h2>
{f([
    ["<code>Api::autenticar()</code>", "Extrae el Bearer, lo valida con <code>Tokens::verificar</code> y arma el <code>Principal</code> (sub, usuario, roles, scopes). Sin token válido → 401."],
    ["<code>Api::exigir(scope…)</code>", "Comprueba que el token tenga el scope; si no, registra el intento y responde 403."],
    ["<code>Api::enrutar()</code>", "Tabla de rutas permitidas. Lo que no está aquí responde 404 (<b>denegar por defecto</b>)."],
    ["<code>Api::esMio(caso)</code>", "Control por propiedad: compara el <code>sub</code> del token con el dueño del caso."],
    ["<code>listarCasos / crearCaso / verCaso / editarCaso / borrarCaso</code>", "Casos: cada una aplica su scope y, para ROL_USUARIO, la propiedad."],
    ["<code>comentar / editarComentario / borrarComentario</code>", "Comentarios, con las mismas reglas."],
    ["<code>listarUsuarios / crearUsuario / editarUsuario / borrarUsuario / desbloquearUsuario</code>", "Administración de usuarios en el directorio; no permite tocar la propia cuenta."],
    ["<code>auditoria / verConfig / guardarConfig / estadisticas</code>", "Auditoría combinada, parámetros de seguridad y cifras según el alcance del scope."],
    ["<code>index.php  /auth/login</code>", "Inicia el flujo OIDC. Si no hay sesión, <code>/</code> redirige aquí."],
    ["<code>index.php  /callback</code>", "Verifica <code>state</code>, canjea el código, valida ID token y access token, regenera la sesión (anti fijación) y registra el LOGIN."],
    ["<code>index.php  /auth/sesion</code>", "Entrega a la página el access token vigente; renueva con rotación si le queda poco."],
    ["<code>index.php  /auth/logout</code>", "Exige token CSRF, revoca en Keycloak y destruye la sesión."],
    ["<code>index.php  /auth/cambiar-clave</code>", "Reinicia el login con la acción <code>UPDATE_PASSWORD</code>: el cambio lo hace Keycloak contra el directorio."],
])}
"""))

    s.append(("15", "Interfaz, scripts y herramientas de apoyo", f"""
<h2>Interfaz (<code>app/public/assets/app.js</code>)</h2>
<p>No contiene reglas de seguridad ni datos: todo lo pide a la API. Solo oculta lo que el rol no puede usar.</p>
{f([
    ["<code>pedirSesion() / token()</code>", "Obtiene y renueva el access token (se guarda solo en memoria)."],
    ["<code>call(método, ruta, cuerpo)</code>", "Llama a la API con <code>Authorization: Bearer</code> y devuelve estado + datos."],
    ["<code>render() / go(vista)</code>", "Dibuja la vista pedida; si la API responde 403 muestra la pantalla “Acceso denegado”."],
    ["<code>VIEWS.inicio / casos / usuarios / auditoria / config / cuenta</code>", "Cada pantalla pide sus datos y arma su HTML (todo texto se escapa con <code>esc()</code> contra XSS)."],
    ["<code>abrirCaso() / formCaso() / formUser()</code>", "Ventanas de detalle y de formularios."],
    ["<code>salir()</code>", "Cierra sesión con token CSRF y sigue la redirección de Keycloak."],
])}
<h2>Scripts de operación</h2>
{f([
    ["<code>scripts/bw.sh</code>", "Atajo: <code>arriba</code>, <code>abajo</code>, <code>estado</code>, <code>credenciales</code>, <code>pruebas</code>, <code>limpiar</code>, <code>logs</code>."],
    ["<code>scripts/preparar.sh</code>", "Crea la CA y los certificados, genera los secretos aleatorios y los archivos LDIF del directorio (idempotente)."],
    ["<code>ldap/init.sh</code>", "Activa la política de contraseñas por defecto y los permisos (ACL) del directorio."],
    ["<code>keycloak/configurar.py</code>", "Configura Keycloak por API: <code>realm()</code>, <code>roles()</code>, <code>scopes()</code>, <code>clientes()</code>, <code>ldap()</code>, <code>grupos_a_roles()</code>, <code>flujo_mfa()</code>."],
    ["<code>scripts/captura.sh</code>", "Captura el tráfico de un login con tcpdump y busca claves y tokens en el <code>.pcap</code>; incluye un control sin TLS."],
])}
<h2>Pruebas y evidencias</h2>
{f([
    ["<code>pruebas/oidc_cliente.py</code>", "“Navegador” en Python: hace el login real (formulario, PKCE, TOTP con anti-replay), canjea el código y llama a la API."],
    ["<code>pruebas/casos_prueba.py</code>", "Los 27 casos CP; crea usuarios temporales <code>prueba.*</code> y los borra; escribe la tabla de resultados."],
    ["<code>pruebas/zap_escaneo.py</code>", "Lanza OWASP ZAP en Docker (autenticado y sin sesión) y resume las alertas."],
    ["<code>pruebas/ui_capturas.cjs</code> · <code>kc_consola.cjs</code>", "Chromium automatizado: prueba la interfaz real y toma las capturas."],
])}
"""))

    res = json.load(open(os.path.join(RAIZ, "evidencias", "resultados-pruebas-final.json")))
    filas = [[c["id"], esc(c["caso"]), esc(c["actor"]), esc(c["esperado"]), "<span class='pill ok'>Pasa</span>" if c["ok"] else "<span class='pill no'>Falla</span>"] for c in res["casos"]]
    s.append(("16", "Pruebas de seguridad (27 casos)", f"""
<p>Los casos <b>CP-01 a CP-10</b> son los de la guía; <b>CP-11 a CP-27</b> los agregamos. Se ejecutan contra el sistema real (login con PKCE y TOTP incluidos) con un solo comando: <code>scripts/bw.sh pruebas</code>. Resultado: <b>{res['pasan']} de {res['total']} pasan</b>.</p>
{tabla(["ID", "Caso", "Rol / actor", "Resultado esperado", "Estado"], filas, anchos=["7%", "29%", "14%", "40%", "10%"])}
"""))

    s.append(("17", "OWASP ZAP: antes y después", f"""
<p>ZAP escanea la aplicación buscando fallos conocidos (pasivo y activo). Se corrió <b>antes</b> de endurecer y <b>después</b>.</p>
{duo(img("zap-antes.png", "ANTES: 0 altas · 2 medias · 4 bajas · 4 informativas"), img("zap-despues.png", "DESPUÉS: 0 altas · 0 medias · 0 bajas"))}
{tabla(["Riesgo", "Alerta", "Corrección"], [
    ["<span class='pill al'>Media</span>", "Sin Content-Security-Policy", "CSP estricta (<code>default-src 'none'; script-src 'self'; …</code>) sin <code>unsafe-inline</code>"],
    ["<span class='pill al'>Media</span>", "Sin protección anti-clickjacking", "<code>X-Frame-Options: DENY</code> y <code>frame-ancestors 'none'</code>"],
    ["<span class='pill mut'>Baja</span>", "XSS persistente en respuesta JSON", "JSON con <code>&lt; &gt; &amp;</code> escapados, <code>nosniff</code> y escape en la interfaz"],
    ["<span class='pill mut'>Baja</span>", "Versión del servidor visible", "<code>ServerTokens Prod</code>, <code>expose_php=Off</code>"],
    ["<span class='pill mut'>Baja</span>", "Sin HSTS", "<code>Strict-Transport-Security</code>"],
    ["<span class='pill mut'>Baja</span>", "Falta <code>X-Content-Type-Options</code>", "<code>nosniff</code>"],
], anchos=["10%", "35%", "55%"])}
"""))

    s.append(("18", "Verificación del cifrado (captura de red)", f"""
<p>La guía pide comprobar que no viajan contraseñas ni tokens en texto plano. Se capturó el tráfico de un login real con <b>tcpdump</b> dentro de la red de Keycloak y se analizó con <b>tshark</b> (la versión de consola de Wireshark). El archivo <code>evidencias/login-https.pcap</code> se abre directamente en Wireshark.</p>
{term("tshark-paquetes", "Paquetes del login: TCP, saludo TLS (SNI) y datos de aplicación ya cifrados", 24)}
{term("captura-login", "Resultado del análisis: 0 coincidencias con HTTPS; el control sin TLS sí las muestra")}
{nota("<b>Lectura:</b> con HTTPS solo se ve el saludo TLS y bloques ilegibles. El experimento de control (HTTP plano) muestra que, sin TLS, contraseña y token sí serían visibles: por eso el cifrado es obligatorio.", "ok")}
"""))

    s.append(("19", "Hallazgos que encontraron las pruebas y cómo se corrigieron", f"""
<p>Al probar de verdad aparecieron fallos reales. Esto es lo que debe contarse en la sustentación: <b>se detectaron, se corrigieron y se volvió a probar</b>.</p>
{tabla(["Hallazgo", "Detectado por", "Causa", "Corrección"], [
    ["<b>El auditor podía modificar casos</b> (escalada de privilegios)", "CP-07", "Un rol técnico compuesto compartido hacía que los permisos del admin alcanzaran al auditor", "Se eliminó el rol compuesto; el TOTP obligatorio se decide por condiciones por rol"],
    ["El cambio de duración del token no tenía efecto", "CP-03", "Un atributo del cliente pisaba el valor del realm", "Se quitó el atributo"],
    ["Un cambio de grupo no cambiaba el rol", "CP-23", "Caché de usuarios de Keycloak", "Federación LDAP sin caché"],
    ["Eventos de Keycloak ausentes en la auditoría", "CP-02, CP-24", "Keycloak 26.8 exige el scope <code>kc-admin-api</code>", "Scope agregado con roles mínimos"],
    ["Errores de PHP visibles al usuario", "CP-02", "La imagen no traía <code>php.ini</code>", "<code>display_errors=Off</code>, <code>expose_php=Off</code>"],
    ["Usuarios mostrados como “cuenta de servicio”", "Revisión visual → CP-26", "Lectura incorrecta de las clases de objeto del directorio", "Corregido y cubierto con CP-26"],
    ["Librería JWT con aviso de seguridad", "<code>composer install</code>", "Versión 6.x afectada", "Se usa la 7.x"],
], anchos=["26%", "13%", "31%", "30%"])}
<h2>Qué estaba simulado antes y cómo está ahora</h2>
{tabla(["Pieza", "Antes (prototipo en el navegador)", "Ahora (real)"], [
    ["Directorio", "Un objeto JavaScript", "OpenLDAP con LDAPS, OU, grupos y ppolicy"],
    ["Proveedor de identidad", "Funciones que imitaban a Keycloak", "Keycloak 26.8 en HTTPS"],
    ["Contraseñas y bloqueo", "Comparación y contador en memoria", "Validadas por el directorio; bloqueo real"],
    ["Segundo factor", "Un código inventado a la vista", "TOTP real (RFC 6238), obligatorio por rol"],
    ["PKCE, state, nonce", "Pasos dibujados", "Flujo real Authorization Code + PKCE"],
    ["Tokens", "Firmados con un secreto en el código", "RS256 con JWKS, vida de 5 min, refresh rotativo"],
    ["API y RBAC", "Funciones en el navegador", "Backend PHP: valida token y scope en cada endpoint"],
    ["Datos y auditoría", "Memoria (se perdían al recargar)", "SQLite persistente + eventos de Keycloak"],
    ["HTTPS y secretos", "Ninguno / secreto en el código", "TLS en todo; secretos en variables de entorno"],
    ["Pruebas, ZAP, Wireshark", "Motor simulado / no aplicaba", "27 casos reales, ZAP antes y después, captura de red"],
], anchos=["22%", "34%", "44%"])}
"""))

    s.append(("20", "Cumplimiento de la rúbrica y de los requisitos de la guía", f"""
<p>Verificación punto por punto contra la sección 12 (rúbrica) y la sección 7.2 (requisitos obligatorios).</p>
{tabla(["Criterio (peso)", "Qué pide para “Excelente”", "Estado", "Evidencia"], [
    ["Nomenclatura (15%)", "Completa, aplicada a todos los objetos, con ejemplos y reglas; homónimos resueltos", "<span class='pill ok'>Cumple</span>", "Sección 4, sin excepciones"],
    ["Autenticación (25%)", "Authorization Code + PKCE; valida ID token y access token (iss, aud, exp, nonce, firma); MFA activo; HTTPS; logout correcto", "<span class='pill ok'>Cumple</span>", "Secciones 9 y 10; CP-01, 03, 04, 11–18"],
    ["Directorio (15%)", "LDAP/AD operativo como fuente única; mapeo grupo→rol automático; política de contraseñas aplicada", "<span class='pill ok'>Cumple</span>", "Secciones 6 y 7; CP-22, CP-23, CP-27"],
    ["Autorización (20%)", "Matriz completa; mínimo privilegio; deny-by-default en backend; control por propiedad; justificación por rol", "<span class='pill ok'>Cumple</span>", "Secciones 12 y 13; CP-05 a CP-08, 19 a 21"],
    ["Pruebas (10%)", "≥10 casos positivos y negativos con evidencia; hallazgos de ZAP documentados y remediados", "<span class='pill ok'>Cumple</span>", "27 casos; ZAP antes y después; captura de red"],
    ["Herramientas (5%)", "Cada una justifica licencia, costo, compatibilidad, alternativas y fuentes", "<span class='pill ok'>Cumple</span>", "Sección 3"],
    ["Informe (10%)", "Completo según la estructura; demostración sin fallas", "<span class='pill al'>Pendiente</span>", "Lo redacta la compañera con esta guía; la demostración ya funciona"],
], anchos=["16%", "38%", "12%", "34%"])}
<h2>Requisitos obligatorios (sección 7.2)</h2>
{tabla(["Requisito", "Estado", "Cómo se cumple"], [
    ["HTTPS en todos los componentes", "<span class='pill ok'>Sí</span>", "App, Keycloak, LDAPS y PostgreSQL con TLS (la base rechaza conexiones sin cifrar)"],
    ["<code>redirect_uri</code> exacta; sin Implicit ni Password Grant", "<span class='pill ok'>Sí</span>", "Sin comodines; ambos flujos deshabilitados (CP-09, CP-15)"],
    ["Access token de 5–15 min; refresh con rotación", "<span class='pill ok'>Sí</span>", "5 min; rotación activa (CP-03, CP-16)"],
    ["Contraseñas: 12+, sin repetir las últimas 5, bloqueo tras 5 fallos", "<span class='pill ok'>Sí</span>", "<code>ppolicy</code> y Keycloak (CP-02, CP-22, CP-27)"],
    ["TOTP obligatorio para ADMIN y AUDITOR", "<span class='pill ok'>Sí</span>", "Flujo con condiciones por rol (CP-11, CP-12)"],
    ["Secretos fuera del código", "<span class='pill ok'>Sí</span>", "Variables de entorno en <code>~/.local/share/blackwall/</code>, excluido del repositorio"],
    ["Logout que revoque en IdP y app", "<span class='pill ok'>Sí</span>", "CP-17"],
    ["Documentar y diagramar la autenticación", "<span class='pill ok'>Sí</span>", "Sección 9"],
], anchos=["38%", "10%", "52%"])}
{nota("<b>Pendientes de ustedes antes de entregar:</b> (1) que <code>campbell.cesar</code> y <code>galvez.angel</code> configuren el TOTP con su celular en su primer ingreso (se ve el QR); (2) el informe en PDF con la estructura de la sección 14 de la guía, <b>declarando el uso de herramientas de inteligencia artificial</b>; (3) el enlace al repositorio (la guía lo exige) y no incluir contraseñas ni tokens completos.", "al")}
"""))

    s.append(("21", "Cómo operarla, demostrarla y repartir la exposición", f"""
<h2>Comandos</h2>
{tabla(["Para…", "Comando (desde <code>proyecto-final/blackwall-real</code>)"], [
    ["Levantar todo (primera vez o tras reiniciar)", "<code>scripts/bw.sh arriba</code>"],
    ["Ver la contraseña de las cuentas", "<code>scripts/bw.sh credenciales</code>"],
    ["Abrir la app", "<code>https://app.localhost:8444</code>"],
    ["Correr las 27 pruebas", "<code>scripts/bw.sh pruebas</code>"],
    ["Apagar / empezar de cero", "<code>scripts/bw.sh abajo</code> / <code>scripts/bw.sh limpiar</code>"],
], anchos=["40%", "60%"])}
<h2>Guion de la demostración (lo que pide la guía)</h2>
<ol>
<li><b>Inicio de sesión con cada rol:</b> administrador (con TOTP), analista, auditor (con TOTP), usuario e invitado. Mostrar cómo cambia el menú.</li>
<li><b>Intento denegado:</b> con el analista, abrir <code>#config</code> en la dirección → pantalla 403.</li>
<li><b>Control por propiedad:</b> con <code>ejemplo.usuario</code>, ver que solo aparecen sus casos.</li>
<li><b>Revisión de la auditoría:</b> con el auditor, mostrar el 403 recién generado y los inicios de sesión.</li>
<li><b>Bloqueo:</b> cinco contraseñas incorrectas seguidas y mostrar el bloqueo en Usuarios (el administrador lo desbloquea).</li>
</ol>
<h2>Reparto sugerido de temas (todos deben dominar todo)</h2>
<p>La profesora indicó que todos deben conocer toda la aplicación. Este reparto es solo para <b>preparar</b> cada bloque a fondo; el resto debe poder responder lo básico.</p>
{tabla(["Bloque", "Secciones de esta guía", "Preguntas que deben saber responder"], [
    ["1. Visión, arquitectura y Docker", "1, 2, 5", "¿Qué hace la app? ¿Qué corre en cada contenedor? ¿Dónde se guarda cada dato? ¿Por qué HTTPS en todo?"],
    ["2. Directorio y nomenclatura", "4, 6", "¿Por qué OpenLDAP y no AD? ¿Cómo se guardan las contraseñas? ¿Qué es una OU y un grupo? ¿Qué hace ppolicy?"],
    ["3. Keycloak y autenticación", "7, 9, 10", "¿Qué es OIDC, PKCE, state y nonce? ¿Por qué la app no ve la contraseña? ¿Cómo funciona el TOTP?"],
    ["4. Autorización y código", "11, 12, 13, 14", "¿Qué es RBAC? ¿Qué es un scope? ¿Qué es denegar por defecto? ¿Cómo evitas que un usuario vea casos ajenos?"],
    ["5. Pruebas, ZAP y red", "16, 17, 18, 19", "¿Qué prueba cada CP? ¿Qué encontró ZAP y cómo se corrigió? ¿Cómo se verificó el cifrado?"],
    ["6. Informe y herramientas", "3, 20, 22", "¿Por qué estas herramientas? ¿Qué falta en la rúbrica? ¿Qué cambiarían para producción?"],
], anchos=["24%", "18%", "58%"])}
<h2>Si preguntan “¿qué cambiarían para producción?”</h2>
<ul><li>Gestor de secretos con rotación en lugar de variables de entorno.</li><li>Certificados de una CA pública o corporativa.</li><li>Auditoría centralizada de solo-anexar (SIEM) y copias de seguridad del proveedor de identidad.</li><li>Alta disponibilidad de Keycloak y del directorio, y una imagen de OpenLDAP mantenida.</li><li>Un servicio de directorio corporativo (AD) con Kerberos si la organización ya lo tiene.</li></ul>
"""))

    G = [
        ("Access token", "Token de corta duración (5 min) que la app envía a la API para demostrar quién eres y qué puedes hacer."),
        ("AD DS", "Active Directory Domain Services: el directorio de Microsoft. Aquí no se usa; se usa OpenLDAP."),
        ("Anti-replay", "Protección que impide reutilizar un código ya usado (Keycloak rechaza el mismo TOTP dos veces)."),
        ("Authorization Code", "Flujo de OAuth donde Keycloak entrega un código de un solo uso que la app cambia por tokens."),
        ("Autenticación", "Comprobar que eres quien dices ser (contraseña, código TOTP)."),
        ("Autorización", "Decidir qué puedes hacer una vez identificado."),
        ("Bearer", "Forma de enviar el token: cabecera <code>Authorization: Bearer …</code>."),
        ("Bind (LDAP)", "Iniciar sesión en el directorio con un usuario y contraseña para verificarlos."),
        ("CA (autoridad certificadora)", "Entidad que firma certificados. Aquí es una CA propia del laboratorio."),
        ("Claim", "Dato dentro de un token (por ejemplo <code>roles</code> o <code>exp</code>)."),
        ("Client (cliente OIDC)", "Aplicación registrada en Keycloak para poder pedir inicios de sesión (<code>cli-blackwall-dev</code>)."),
        ("Client scope", "Permiso nombrado en Keycloak (<code>casos:leer</code>) que se concede según el rol."),
        ("Contenedor", "Programa aislado con todo lo que necesita para correr; Docker los gestiona."),
        ("Control por propiedad", "Aunque tengas el permiso, solo accedes a registros cuyo creador eres tú."),
        ("CSP", "Content-Security-Policy: cabecera que limita de dónde puede cargar el navegador scripts, imágenes y estilos."),
        ("CSRF", "Ataque en que otra web hace que tu navegador ejecute una acción sin que lo sepas."),
        ("Deny-by-default", "Todo lo que no está permitido explícitamente se rechaza."),
        ("Directorio", "Base de datos especializada en personas, grupos y permisos (LDAP)."),
        ("Docker Compose", "Archivo que describe varios contenedores y cómo se conectan."),
        ("Federación", "Keycloak usa el directorio como fuente de usuarios en lugar de guardar las contraseñas."),
        ("Grupo (GRP_*)", "Conjunto de usuarios en el directorio; determina el rol."),
        ("Hash salado", "Transformación irreversible de la contraseña con un dato aleatorio (sal); permite verificarla sin guardarla."),
        ("HSTS", "Cabecera que obliga al navegador a usar siempre HTTPS con ese sitio."),
        ("ID token", "Token OIDC que prueba quién inició sesión; la app lo valida y no lo envía a la API."),
        ("IdP", "Proveedor de identidad: el sistema que autentica (Keycloak)."),
        ("IDOR / BOLA", "Fallo de acceder a datos ajenos cambiando un identificador en la petición."),
        ("Issuer (iss)", "Quién emitió el token; debe ser Keycloak."),
        ("JWKS", "Lista de claves públicas con las que se verifican las firmas de los tokens."),
        ("JWT", "Token en formato de tres partes (cabecera, datos, firma)."),
        ("LDAP / LDAPS", "Protocolo para consultar un directorio / su versión cifrada."),
        ("Mínimo privilegio", "Dar a cada rol solo los permisos que necesita."),
        ("Nonce", "Valor aleatorio de un solo uso que liga el ID token a un inicio de sesión concreto."),
        ("OAuth 2.0", "Marco para dar acceso limitado a una app sin entregarle la contraseña."),
        ("OIDC", "OpenID Connect: capa de identidad sobre OAuth 2.0."),
        ("OU", "Unidad organizativa: carpeta dentro del directorio, una por área."),
        ("PKCE", "Mecanismo que protege el código de autorización con un secreto de un solo uso (<code>code_verifier</code>)."),
        ("ppolicy", "Módulo de OpenLDAP que aplica la política de contraseñas y el bloqueo."),
        ("RBAC", "Control de acceso basado en roles."),
        ("Realm", "Espacio aislado dentro de Keycloak con sus usuarios, clientes y reglas."),
        ("Refresh token", "Token de larga vida que permite pedir otro access token; rota en cada uso."),
        ("redirect_uri", "Dirección a la que Keycloak puede devolver al usuario; debe coincidir exactamente."),
        ("Rol (ROL_*)", "Conjunto de permisos asignado según el grupo."),
        ("RS256", "Firma con clave privada RSA y SHA-256; se verifica con la clave pública."),
        ("Scope", "Permiso con forma <code>recurso:acción</code> dentro del token."),
        ("SIEM", "Sistema que centraliza y analiza registros de seguridad (para producción)."),
        ("SNI", "Nombre del servidor que el navegador envía al iniciar TLS."),
        ("state", "Valor aleatorio que une la respuesta de Keycloak con la solicitud original (anti-CSRF)."),
        ("sub", "Identificador único e inmutable del usuario en el token."),
        ("TLS", "Cifrado del canal (la “S” de HTTPS)."),
        ("TOTP", "Código de 6 dígitos que cambia cada 30 s, calculado con un secreto y la hora."),
        ("XSS", "Inyección de scripts maliciosos en una página."),
        ("ZAP", "OWASP Zed Attack Proxy: escáner de seguridad web."),
    ]
    s.append(("22", "Glosario", f"""
<p class="small">Términos en orden alfabético.</p>
{tabla(["Término", "Significado"], [[f"<b>{a}</b>", b] for a, b in G], anchos=["24%", "76%"])}
"""))
    s.append(("23", "Referencias", """
<ul>
<li>IETF (2012). RFC 6749: The OAuth 2.0 Authorization Framework.</li>
<li>IETF (2015). RFC 7636: Proof Key for Code Exchange by OAuth Public Clients (PKCE).</li>
<li>IETF (2015). RFC 7519: JSON Web Token (JWT). RFC 7515 (JWS) · RFC 7517 (JWK) · RFC 7518 (JWA).</li>
<li>IETF (2012). RFC 6750: The OAuth 2.0 Authorization Framework: Bearer Token Usage.</li>
<li>IETF (2025). RFC 9700: Best Current Practice for OAuth 2.0 Security.</li>
<li>IETF (2011). RFC 6238: TOTP: Time-Based One-Time Password Algorithm. RFC 4226 (HOTP).</li>
<li>IETF (2018). RFC 8446: The Transport Layer Security (TLS) Protocol Version 1.3.</li>
<li>IETF (2006). RFC 4511: Lightweight Directory Access Protocol (LDAP): The Protocol.</li>
<li>IETF (2012). RFC 6797: HTTP Strict Transport Security (HSTS).</li>
<li>OpenID Foundation (2014). OpenID Connect Core 1.0 · RP-Initiated Logout 1.0.</li>
<li>NIST (2017). SP 800-63B: Digital Identity Guidelines: Authentication and Lifecycle Management.</li>
<li>NIST (2004). INCITS 359-2004: Role-Based Access Control.</li>
<li>OWASP (2021). OWASP Top 10:2021, A01 Broken Access Control. OWASP ASVS v4.0.3.</li>
<li>Keycloak: keycloak.org/documentation · OpenLDAP: openldap.org/doc · OWASP ZAP: zaproxy.org/docs · Wireshark: wireshark.org/docs.</li>
</ul>"""))
    return s
