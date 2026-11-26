from base import c, duo, img, img_ev, nota, tabla, term

ARQ = """<svg viewBox="0 0 760 330" width="100%" role="img" aria-label="Arquitectura">
<defs><marker id="f" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#0a4d8c"/></marker></defs>
<g font-size="11" fill="#18222e">
<rect x="8" y="125" width="120" height="70" rx="9" fill="#e8f0f9" stroke="#0a4d8c"/><text x="68" y="154" text-anchor="middle" font-weight="700">Navegador</text><text x="68" y="172" text-anchor="middle" font-size="9" fill="#5d6878">Chromium / Firefox</text>
<rect x="215" y="125" width="165" height="70" rx="9" fill="#003366"/><text x="297" y="150" text-anchor="middle" fill="#fff" font-weight="700">Aplicación Blackwall</text><text x="297" y="166" text-anchor="middle" fill="#cfe0f2" font-size="9">Apache + PHP 8.3 · API /api/*</text><text x="297" y="181" text-anchor="middle" fill="#cfe0f2" font-size="9">app.localhost:8444 (HTTPS)</text>
<rect x="215" y="250" width="165" height="55" rx="9" fill="#f6f9fc" stroke="#9db4cf"/><text x="297" y="274" text-anchor="middle" font-weight="700">SQLite</text><text x="297" y="291" text-anchor="middle" font-size="9" fill="#5d6878">casos · comentarios · auditoría</text>
<rect x="470" y="18" width="165" height="70" rx="9" fill="#0a4d8c"/><text x="552" y="44" text-anchor="middle" fill="#fff" font-weight="700">Keycloak 26.8</text><text x="552" y="60" text-anchor="middle" fill="#cfe0f2" font-size="9">Proveedor de identidad · OIDC · TOTP</text><text x="552" y="75" text-anchor="middle" fill="#cfe0f2" font-size="9">acceso.localhost:8443 (HTTPS)</text>
<rect x="470" y="232" width="165" height="70" rx="9" fill="#e8f0f9" stroke="#0a4d8c"/><text x="552" y="258" text-anchor="middle" font-weight="700">OpenLDAP 2.6</text><text x="552" y="274" text-anchor="middle" font-size="9" fill="#5d6878">Directorio · usuarios · grupos · ppolicy</text><text x="552" y="289" text-anchor="middle" font-size="9" fill="#5d6878">ldap:1636 (LDAPS)</text>
<rect x="660" y="18" width="92" height="70" rx="9" fill="#f6f9fc" stroke="#9db4cf"/><text x="706" y="48" text-anchor="middle" font-weight="700">PostgreSQL</text><text x="706" y="64" text-anchor="middle" font-size="9" fill="#5d6878">datos de Keycloak</text>
</g>
<g stroke="#0a4d8c" stroke-width="1.6" fill="none" marker-end="url(#f)">
<path d="M130 160H213" marker-start="url(#f)"/>
<path d="M68 125V53H468" marker-start="url(#f)"/>
<path d="M380 140L468 66" marker-start="url(#f)"/>
<path d="M380 182L468 252" marker-start="url(#f)"/>
<path d="M552 90V230" marker-start="url(#f)"/>
<path d="M637 53H658" marker-start="url(#f)"/>
<path d="M297 197V248"/>
</g>
<g font-size="9" fill="#0a4d8c" font-weight="600">
<text x="171" y="152" text-anchor="middle">HTTPS</text>
<text x="260" y="45" text-anchor="middle">HTTPS · inicio de sesión</text>
<text x="404" y="96" text-anchor="middle" transform="rotate(-40 404 96)">token · JWKS</text>
<text x="412" y="205" text-anchor="middle" transform="rotate(38 412 205)">LDAPS · altas/bajas</text>
<text x="560" y="164" text-anchor="start">LDAPS · contraseña y grupos</text>
</g></svg>"""


def secciones():
    s = []

    s.append(("1", "Qué es Blackwall y para qué sirve", f"""
<p class="lead"><b>Blackwall</b> es una aplicación web de <b>gestión de incidentes de seguridad</b>: las personas reportan incidentes (correos de phishing, equipos perdidos, accesos sospechosos), los analistas los atienden y el auditor revisa la trazabilidad. Cada persona ve y hace únicamente lo que su rol permite.</p>
<p>Es el proyecto final de <b>Ciberseguridad II</b> (UTP, FISC) y demuestra, con un sistema que funciona de verdad, los tres pilares de la seguridad de accesos:</p>
{tabla(["Pilar", "Pregunta que responde", "Cómo se resuelve en Blackwall"], [
    ["<b>Identificación</b>", "¿Quién eres?", "Cada persona es una cuenta <code>apellido.nombre</code> en el directorio, pertenece a un grupo <code>GRP_*</code> y recibe un rol <code>ROL_*</code>."],
    ["<b>Autenticación</b>", "¿Puedes demostrarlo?", "Contraseña validada por el directorio + segundo factor TOTP (obligatorio para administrador y auditor), con OpenID Connect y PKCE."],
    ["<b>Autorización</b>", "¿Qué puedes hacer?", "Matriz de roles y permisos aplicada <b>en el servidor</b>, en cada endpoint, con denegación por defecto y control por propiedad."],
], anchos=["16%", "22%", "62%"])}
<h2>Los cinco roles</h2>
{tabla(["Rol", "Quién es", "Qué puede hacer", "Segundo factor"], [
    ["<code>ROL_ADMIN</code>", "Administrador (<code>campbell.cesar</code>)", "Gestionar usuarios y configuración; ver y operar todos los casos; leer la auditoría (solo lectura, para no alterar su propia huella).", "<span class='pill al'>obligatorio</span>"],
    ["<code>ROL_ANALISTA</code>", "Analista SOC (<code>cruz.irvin</code>, <code>pinto.nicole</code>)", "Ver, crear y actualizar casos, comentar y ver estadísticas. No borra casos ni administra usuarios.", "<span class='pill mut'>opcional</span>"],
    ["<code>ROL_AUDITOR</code>", "Cumplimiento (<code>galvez.angel</code>)", "Solo lectura: casos, auditoría y estadísticas. Quien audita no opera (separación de funciones).", "<span class='pill al'>obligatorio</span>"],
    ["<code>ROL_USUARIO</code>", "Persona que reporta (<code>ejemplo.usuario</code>)", "Crear incidentes, ver y editar (si siguen abiertos) <b>solo los suyos</b> y comentar en ellos.", "<span class='pill mut'>opcional</span>"],
    ["<code>ROL_INVITADO</code>", "Consulta pública (<code>cordero.moises</code>)", "Ver únicamente cifras públicas.", "<span class='pill mut'>opcional</span>"],
], anchos=["15%", "22%", "50%", "13%"])}
{img_ev("admin-inicio.png", "Así se ve la aplicación por dentro (administrador)", [(8, 22, "Menú lateral según el rol."), (43, 45, "Estadísticas de los casos."), (87, 3, "Usuario, rol y botón Salir.")], "88%")}
"""))

    s.append(("2", "Arquitectura y dónde vive cada dato", f"""
<p>Cuatro servicios corren en contenedores Docker sobre Fedora (Nobara 44), conectados por una red interna. Solo dos puertos se publican hacia el equipo: <code>8443</code> (acceso) y <code>8444</code> (aplicación), ambos solo en <code>127.0.0.1</code>.</p>
{ARQ}
{term("docker-ps", "Contenedores en ejecución")}
<h2>Dónde se guarda cada cosa</h2>
{tabla(["Dato", "Dónde", "Cómo se guarda"], [
    ["Usuarios, grupos y contraseñas", "OpenLDAP · volumen <code>blackwall_ldap-datos</code>", "Contraseña con hash salado <code>{SSHA}</code>; nunca en texto."],
    ["Copia del perfil, roles, sesiones y secreto TOTP", "PostgreSQL de Keycloak · volumen <code>blackwall_kc-db</code>", "Keycloak <b>no</b> guarda la contraseña: la valida contra el directorio."],
    ["Casos, comentarios y auditoría", "SQLite · volumen <code>blackwall_app-datos</code>", "Consultas preparadas; el dueño de cada caso se guarda por <code>sub</code>."],
    ["Tokens de acceso y de refresco", "Sesión del servidor (PHP)", "El navegador solo recibe una cookie de sesión <code>__Host-bw</code> (Secure, HttpOnly, SameSite=Lax). El access token vive en memoria de la página."],
    ["Secretos y certificados", "<code>~/.local/share/blackwall/</code>", "Fuera del repositorio y de la carpeta que sirve Apache. Permisos 600 en el archivo de secretos."],
], anchos=["27%", "37%", "36%"])}
"""))

    justif = [
        ["<b>Keycloak 26.8</b>", "Proveedor de identidad: OIDC, OAuth 2.0, TOTP, federación LDAP, eventos", "Apache 2.0", "Gratis", "Implementación de referencia de código abierto; corre en contenedor; no depende de internet.", "Auth0, Okta, Entra ID (planes gratuitos con límites y cuenta en la nube)", "keycloak.org/documentation"],
        ["<b>OpenLDAP 2.6</b>", "Directorio de usuarios y grupos; política de contraseñas (<code>ppolicy</code>)", "OpenLDAP Public License", "Gratis", "LDAP liviano; la guía lo admite como alternativa a AD; Keycloak lo federa por LDAPS.", "Samba AD DC, Windows Server AD DS (evaluación 180 días), FreeIPA", "openldap.org/doc"],
        ["<b>Docker Engine 29 / Compose 5</b>", "Despliegue reproducible de los 4 servicios", "Apache 2.0", "Gratis en Linux", "Mismo resultado en cualquier equipo; un comando levanta todo.", "Podman, instalación nativa", "docs.docker.com"],
        ["<b>OpenSSL 3</b>", "CA propia y certificados TLS (app, Keycloak, LDAPS)", "Apache 2.0", "Gratis", "Estándar de la industria, ya instalado en el sistema.", "mkcert, Let's Encrypt (requiere dominio público)", "openssl.org"],
        ["<b>PHP 8.3 + Apache 2.4</b>", "Aplicación y API protegida", "PHP License 3.01 / Apache 2.0", "Gratis", "Es el stack del curso; código corto y auditable; extensión LDAP nativa.", "Python + Flask + Authlib (sugerido en la guía)", "php.net · httpd.apache.org"],
        ["<b>firebase/php-jwt 7</b>", "Verificación de firma RS256 con claves JWKS", "BSD-3-Clause", "Gratis", "Librería pequeña y mantenida; fija el algoritmo por clave (evita confusión de algoritmos).", "Implementar la firma a mano; lcobucci/jwt", "github.com/firebase/php-jwt"],
        ["<b>PostgreSQL 16</b>", "Base de datos de Keycloak", "PostgreSQL License", "Gratis", "Base recomendada por Keycloak para uso no efímero.", "H2 integrada (solo desarrollo)", "postgresql.org"],
        ["<b>SQLite 3</b>", "Casos, comentarios y auditoría de la app", "Dominio público", "Gratis", "Sin servidor adicional; suficiente para el alcance.", "MySQL/MariaDB", "sqlite.org"],
        ["<b>OWASP ZAP 2.17</b>", "Escaneo de seguridad (pasivo y activo) antes y después", "Apache 2.0", "Gratis", "Herramienta estándar; automatizable con su Automation Framework; la pide la guía.", "Burp Suite Community, Nikto", "zaproxy.org"],
        ["<b>tcpdump + tshark</b>", "Captura y análisis del tráfico (equivale a Wireshark en consola)", "BSD / GPLv2", "Gratis", "Se ejecuta en el espacio de red del contenedor; los <code>.pcap</code> abren en Wireshark.", "Wireshark (interfaz gráfica)", "tcpdump.org · wireshark.org"],
        ["<b>Python 3 (scripts)</b>", "Configurar Keycloak por API y ejecutar las 27 pruebas con login real", "PSF License", "Gratis", "Permite automatizar PKCE, TOTP y verificación de tokens, y repetir las pruebas.", "Postman, Bruno", "python.org"],
        ["<b>Chromium + puppeteer-core</b>", "Probar la interfaz en un navegador real y sacar capturas", "BSD-3 / Apache 2.0", "Gratis", "Verifica el flujo completo (login, TOTP, pantallas) como lo haría una persona.", "Selenium, Playwright", "pptr.dev"],
    ]
    s.append(("3", "Herramientas utilizadas y su justificación", f"""
<p>La guía permite elegir herramientas distintas a las sugeridas si se justifican por licencia, costo, compatibilidad, alternativas evaluadas y fuentes. Esta tabla lo hace para todas las que usa el proyecto.</p>
{tabla(["Herramienta", "Para qué se usa", "Licencia", "Costo", "Por qué esta", "Alternativas evaluadas", "Fuente"], justif, anchos=["13%", "17%", "10%", "7%", "22%", "17%", "14%"])}
{term("versiones", "Versiones en el equipo de desarrollo")}
{term("php-deps", "Aplicación: versión de PHP, extensiones y librerías")}
{nota("<b>Límite a declarar:</b> la imagen de OpenLDAP (<code>bitnamilegacy/openldap</code>) ya no recibe actualizaciones de seguridad. Es aceptable en laboratorio; en producción se usaría una imagen mantenida o instalación nativa.", "al")}
"""))

    s.append(("4", "Nomenclatura de identificación", f"""
<p>Todos los objetos siguen la convención de la guía (minúsculas, sin acentos ni espacios). Los homónimos se resuelven con un número (<code>perez.juan2</code>) y el correo nunca se usa como identificador.</p>
{tabla(["Elemento", "Formato", "Ejemplos en este proyecto", "Dónde se aplica"], [
    ["Usuario final", "<code>apellido.nombre</code>", "<code>campbell.cesar</code>, <code>cruz.irvin</code>, <code>ejemplo.usuario2</code>", "OpenLDAP (<code>uid</code>); la API valida el formato al crear usuarios"],
    ["Cuenta de servicio", "<code>svc-&lt;app&gt;-&lt;función&gt;</code>", "<code>svc-blackwall-sync</code>", "OpenLDAP, <code>ou=servicio</code>; sin inicio de sesión interactivo"],
    ["Grupo del directorio", "<code>GRP_&lt;ÁREA&gt;_&lt;ROL&gt;</code>", "<code>GRP_TI_ADMIN</code>, <code>GRP_SOC_ANALISTA</code>, <code>GRP_CUM_AUDITOR</code>, <code>GRP_USR_USUARIO</code>, <code>GRP_PUB_INVITADO</code>", "OpenLDAP (<code>groupOfNames</code>)"],
    ["Unidad organizativa", "minúsculas, una por área", "<code>ou=ti</code>, <code>ou=soc</code>, <code>ou=cum</code>, <code>ou=usr</code>, <code>ou=pub</code>, <code>ou=servicio</code>", "OpenLDAP"],
    ["Rol de aplicación", "<code>ROL_&lt;NOMBRE&gt;</code>", "<code>ROL_ADMIN</code>, <code>ROL_ANALISTA</code>, <code>ROL_AUDITOR</code>, <code>ROL_USUARIO</code>, <code>ROL_INVITADO</code>", "Keycloak (roles del realm) y claim <code>roles</code> del token"],
    ["Cliente OIDC", "<code>cli-&lt;app&gt;-&lt;entorno&gt;</code>", "<code>cli-blackwall-dev</code>, <code>cli-blackwall-sync-dev</code>", "Keycloak"],
    ["Scope (permiso)", "<code>&lt;recurso&gt;:&lt;acción&gt;</code>", "<code>casos:leer</code>, <code>usuarios:admin</code>, <code>casos:leer_propios</code>", "Keycloak (client scopes) y cada endpoint de la API"],
    ["Realm", "minúsculas con guion", "<code>proyecto-accesos</code>", "Keycloak"],
], anchos=["16%", "20%", "38%", "26%"])}
{nota("<b>Nota:</b> el administrador de la consola de Keycloak es <code>campbell.cesar</code> (reino <i>master</i>), también con el formato <code>apellido.nombre</code>. No hay excepciones.", "ok")}
"""))

    s.append(("5", "Infraestructura: contenedores, secretos y TLS", f"""
<h2>Docker Compose</h2>
<p>Un solo archivo (<code>docker-compose.yml</code>) define los servicios; el comando <code>scripts/bw.sh arriba</code> prepara certificados y secretos, levanta todo y configura Keycloak por API.</p>
{tabla(["Servicio", "Imagen", "Función", "Puertos"], [
    ["<code>ldap</code>", "bitnamilegacy/openldap 2.6.10", "Directorio; LDAPS; política de contraseñas", "1636 interno"],
    ["<code>ldap-init</code>", "misma imagen (una sola ejecución)", "Aplica la política por defecto y los permisos (ACL) en caliente", "—"],
    ["<code>db</code>", "postgres:16-alpine", "Base de datos de Keycloak (solo acepta conexiones TLS)", "5432 interno"],
    ["<code>keycloak</code>", "quay.io/keycloak/keycloak:26.8.2", "Proveedor de identidad en HTTPS", "127.0.0.1:8443"],
    ["<code>app</code>", "construida con <code>app/Dockerfile</code>", "Apache + PHP 8.3 con TLS", "127.0.0.1:8444"],
], anchos=["14%", "30%", "40%", "16%"])}
<h2>Secretos fuera del código</h2>
<p><code>scripts/preparar.sh</code> genera contraseñas aleatorias (24–32 caracteres) y las guarda en <code>~/.local/share/blackwall/blackwall.env</code> (permiso 600). El repositorio solo contiene plantillas; <code>.gitignore</code> excluye certificados, claves y datos. El directorio del proyecto tiene además un <code>.htaccess</code> que impide que Apache lo sirva.</p>
<h2>Certificados y HTTPS en todos los componentes</h2>
<p>Una <b>CA propia</b> (RSA 4096) firma cuatro certificados de servidor (RSA 2048, SHA-256) con SAN para <code>app</code>, <code>acceso</code>, <code>ldap</code> y <code>db</code>. Las conexiones verifican la cadena: el cliente HTTP de la app usa <code>CURLOPT_CAINFO</code> con la CA y LDAPS exige certificado válido.</p>
{term("tls-ca", "Autoridad certificadora del laboratorio")}
{term("tls-cert", "Certificado del proveedor de identidad (SAN, uso de clave)")}
{term("tls-conexiones", "Conexiones TLS 1.3 verificadas contra la CA: app, proveedor de identidad y directorio")}
{term("db-tls", "La base de datos de Keycloak solo acepta conexiones cifradas (TLS 1.3); una conexión sin cifrar es rechazada")}
"""))

    s.append(("6", "El directorio: OpenLDAP", f"""
<p>Es la <b>fuente única</b> de usuarios y grupos (guía, fase 2): una unidad organizativa por área, un grupo <code>GRP_*</code> por rol y al menos un usuario por rol.</p>
{duo(term("ldap-arbol", "Estructura del directorio (nivel 1)"), term("ldap-grupos", "Grupos y sus miembros"))}
{term("ldap-usuarios", "Usuarios (inetOrgPerson)")}
<h2>Política de contraseñas (NIST SP 800-63B)</h2>
<p>El módulo <code>ppolicy</code> de OpenLDAP aplica la política a todo usuario: mínimo 12 caracteres, historial de las últimas 5, bloqueo tras 5 fallos (60 s) y <code>ppolicy_hash_cleartext</code> para que la contraseña siempre se guarde con hash.</p>
{term("ldap-politica", "Política por defecto (cn=default,ou=politicas)")}
<h2>Permisos mínimos para la cuenta de servicio</h2>
<p>La cuenta <code>svc-blackwall-sync</code> es la única que puede escribir en el directorio (la app la usa para crear, editar y eliminar usuarios). Nadie anónimo lee nada, y cada persona se ve a sí misma. No es una persona (<code>account</code>, no <code>inetOrgPerson</code>), por eso Keycloak nunca la importa como usuario con inicio de sesión.</p>
{term("ldap-acl", "ACL y activación de ppolicy en cn=config")}
{term("ldap-hash", "Una contraseña almacenada: hash salado SSHA, nunca texto")}
"""))

    s.append(("7", "Keycloak: el proveedor de identidad", f"""
<p>Todo se configura por API con un script reproducible (<code>keycloak/configurar.py</code>), no a mano. Las pantallas siguientes son de la consola de administración, ya configurada.</p>
<p><i>Estas son capturas de la consola de administración de Keycloak (está en inglés). Los números rojos de abajo explican qué mirar.</i></p>
{img("kc-realm.png", "El realm: el espacio de Keycloak donde viven nuestros usuarios, clientes y reglas", mirar=[(None, None, "Arriba a la izquierda: <b>Blackwall · UTP</b> es nuestro realm (<code>proyecto-accesos</code>)."), (None, None, "General: nombre y opciones del realm.")])}
{img("kc-tokens.png", "Vida de los tokens", mirar=[(None, None, "<b>Access token lifespan: 5 minutos</b> (la guía pide entre 5 y 15)."), (None, None, "Los demás tiempos controlan la sesión y el código de un solo uso.")])}
<h2>Seguridad del realm</h2>
{tabla(["Requisito (guía 7.2)", "Valor configurado"], [
    ["Access token de vida corta (5–15 min)", "<code>accessTokenLifespan = 300</code> s (editable entre 5 y 15 min desde la pantalla Configuración de la app)"],
    ["Refresh token con rotación", "<code>revokeRefreshToken = true</code>, <code>refreshTokenMaxReuse = 0</code>: cada refresh invalida el anterior"],
    ["Bloqueo temporal tras 5 intentos", "<code>failureFactor = 5</code>, espera de 60 s, máximo 15 min"],
    ["Política de contraseñas", "<code>length(12) and passwordHistory(5)</code> (más <code>ppolicy</code> en el directorio)"],
    ["Eventos de auditoría", "Inicios de sesión, fallos, bloqueos, cambios de contraseña y de TOTP"],
    ["HTTPS obligatorio", "<code>sslRequired = all</code>"],
], anchos=["38%", "62%"])}
{img("kc-seguridad.png", "Defensas del realm", mirar=[(None, None, "Pestaña <b>Brute force detection</b>: bloqueo temporal tras 5 intentos fallidos."), (None, None, "Cabeceras de seguridad que Keycloak envía por defecto.")])}
{img("kc-eventos.png", "Eventos: de aquí sale la auditoría de acceso", mirar=[(None, None, "Cada inicio de sesión (correcto o fallido), cierre de sesión o bloqueo queda registrado."), (None, None, "La pantalla Auditoría de la aplicación lee estos eventos y los une con los suyos.")])}
<h2>Clientes OIDC</h2>
{tabla(["Cliente", "Tipo", "Flujos", "Detalles"], [
    ["<code>cli-blackwall-dev</code>", "Confidencial (con secreto)", "Authorization Code + <b>PKCE S256</b>", "Implicit y Password Grant <b>deshabilitados</b>; <code>redirect_uri</code> exacta (sin comodines); <code>fullScopeAllowed = false</code>; mappers: <code>roles</code>, <code>groups</code>, audiencia"],
    ["<code>cli-blackwall-sync-dev</code>", "Confidencial, solo cuenta de servicio", "Client credentials", "Roles mínimos de administración (ver eventos y usuarios, ajustar parámetros del realm)"],
], anchos=["22%", "20%", "22%", "36%"])}
{img("kc-clientes.png", "Clientes registrados en el realm", mirar=[(None, None, "<b>cli-blackwall-dev</b>: la aplicación (inicia sesión de personas)."), (None, None, "<b>cli-blackwall-sync-dev</b>: cuenta de servicio con permisos mínimos."), (None, None, "Los demás son clientes internos de Keycloak.")])}
<h2>Roles, grupos y scopes</h2>
<p>El <i>group mapper</i> LDAP importa los grupos del directorio y cada grupo tiene asignado su rol (<code>GRP_TI_ADMIN → ROL_ADMIN</code>, etc.): el mapeo es automático y sin caché, de modo que un cambio de grupo se ve en el siguiente token. Cada permiso <code>&lt;recurso&gt;:&lt;acción&gt;</code> es un <i>client scope</i> restringido a los roles que lo necesitan, y el token solo trae los que el rol permite.</p>
{img("kc-roles.png", "Roles de aplicación", mirar=[(None, None, "Los cinco roles <code>ROL_*</code> de la matriz."), (None, None, "El resto son roles propios de Keycloak.")])}
{img("kc-grupos.png", "Grupos importados desde el directorio", mirar=[(None, None, "Los grupos <code>GRP_*</code> vienen de OpenLDAP, no se crearon a mano."), (None, None, "Cada grupo tiene un rol asignado (pestaña Role mapping).")])}
{img("kc-scopes.png", "Client scopes: los permisos recurso:acción", mirar=[(None, None, "Cada permiso (<code>casos:leer</code>, <code>usuarios:admin</code>…) es un scope."), (None, None, "Cada uno está limitado a los roles que lo necesitan.")])}
{img("kc-federacion.png", "Federación con el directorio", mirar=[(None, None, "<b>directorio-blackwall</b>, tipo LDAP, habilitado."), (None, None, "Así Keycloak valida contraseñas contra OpenLDAP en vez de guardarlas.")])}
<h2>Segundo factor por rol</h2>
<p>El flujo de inicio de sesión (<code>browser-blackwall</code>) tiene tres ramas excluyentes: <b>obligatorio</b> si el usuario tiene <code>ROL_ADMIN</code>, <b>obligatorio</b> si tiene <code>ROL_AUDITOR</code>, y <b>voluntario</b> (solo si ya configuró TOTP) para los demás. Si un administrador no lo tiene configurado, Keycloak le obliga a registrarlo en ese mismo inicio de sesión.</p>
{img("kc-flujos.png", "Flujos de autenticación", mirar=[(None, None, "<b>browser-blackwall</b> es el flujo de inicio de sesión propio, el que está en uso."), (None, None, "Dentro tiene las ramas de segundo factor obligatorio (admin y auditor) y voluntario.")])}
{img("kc-politicas.png", "Política de contraseñas del realm", mirar=[(None, None, "Reglas de contraseña aplicadas por Keycloak (largo mínimo y historial)."), (None, None, "El directorio aplica las suyas también (sección 6).")])}
{img("kc-usuarios.png", "Usuarios del realm: Keycloak no lista a los usuarios federados hasta buscarlos; se importan desde el directorio la primera vez que se usan")}
"""))
    return s
