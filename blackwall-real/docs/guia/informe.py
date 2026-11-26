#!/usr/bin/env python3
"""Informe del proyecto final (estructura de la sección 14 de la guía). Uso: python3 docs/guia/informe.py → docs/Informe-Proyecto-Final-Blackwall.pdf"""
import json
import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from base import CSS, esc, nota, tabla, term  # noqa: E402

DOCS = os.path.dirname(AQUI)
RAIZ = os.path.dirname(DOCS)
HTML = os.path.join(AQUI, "informe.html")
PDF = os.path.join(DOCS, "Informe-Proyecto-Final-Blackwall.pdf")
REPO = "https://github.com/Cesar-campbell/Blackwall"
LOGO = '<svg width="54" height="54" viewBox="0 0 64 64"><circle cx="32" cy="32" r="26" fill="none" stroke="#e8f0f9" stroke-width="5" stroke-dasharray="42 12.45" transform="rotate(-80 32 32)"/><circle cx="32" cy="32" r="16" fill="#0a4d8c"/><path d="M26.5 31v-3.5a5.5 5.5 0 0 1 11 0V31" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round"/><rect x="23.5" y="30.5" width="17" height="13" rx="2.5" fill="#fff"/><circle cx="32" cy="36" r="2" fill="#0a4d8c"/><rect x="31.2" y="37" width="1.6" height="3.6" rx=".6" fill="#0a4d8c"/></svg>'
EXTRA = """.shot{margin-left:auto;margin-right:auto}section.sec{break-before:auto;margin-top:6mm}section.sec h1{font-size:16pt}section.salto{break-before:page}
figcaption{font-weight:400;font-size:8.4pt;color:#33425a;text-align:center}figcaption b{color:var(--azul)}
h2{font-size:11.5pt}p{text-align:justify}.cover h1{font-size:30pt}.firma td{border:0;border-bottom:1px solid #9db4cf;padding:.5em .3em;font-size:10pt}
@page{@bottom-left{content:"Blackwall · Informe del proyecto final";font:500 8pt Inter;color:#8793a3}}.duo{break-inside:avoid}section.sec h1{break-after:avoid}.tc{break-after:avoid}table.t td,table.t th{font-size:8pt}.tc{font-size:8.3pt;color:var(--mut);margin:.8em 0 .1em;font-weight:600}"""

FIGS = []


def fig(archivo, texto, ancho="100%", carpeta="img"):
    n = len(FIGS) + 1
    FIGS.append((n, texto))
    return f'<figure class="shot" style="width:{ancho}"><img src="{carpeta}/{archivo}" alt=""><figcaption><b>Figura {n}.</b> {texto}</figcaption></figure>'


def figev(archivo, texto, ancho="100%"):
    return fig(archivo, texto, ancho, "../../evidencias/capturas")


def figtxt(nombre, texto, lineas=None):
    n = len(FIGS) + 1
    FIGS.append((n, texto))
    return f'<div>{term(nombre, None, lineas)}<div class="small" style="text-align:center;margin-top:-.4em;margin-bottom:.8em"><b style="color:#003366">Figura {n}.</b> {texto}</div></div>'


def figsvg(svg, texto, ancho="100%"):
    n = len(FIGS) + 1
    FIGS.append((n, texto))
    return f'<figure style="width:{ancho};margin-left:auto;margin-right:auto">{svg}<figcaption><b>Figura {n}.</b> {texto}</figcaption></figure>'


def duo(a, b):
    return f'<div class="duo">{a}{b}</div>'


def tt(n, texto):
    return f'<div class="tc">Tabla {n}. {texto}</div>'


from s1 import ARQ  # noqa: E402
from s2 import secuencia  # noqa: E402
from diagramas import cadena, ciclos, decision  # noqa: E402

S = []


def sec(n, t, h, salto=False):
    S.append((n, t, h, salto))


res = json.load(open(os.path.join(RAIZ, "evidencias", "resultados-pruebas-final.json")))

# ---------------------------------------------------------------------------------------------- 1
sec("1", "Introducción y objetivos", f"""
<p>Blackwall es una aplicación web de gestión de incidentes de seguridad construida para demostrar, con un sistema real y reproducible, cómo se identifica, autentica y autoriza a las personas que lo usan. Los usuarios reportan incidentes, los analistas los atienden y el auditor revisa la trazabilidad; cada rol ve y hace solo lo que su función requiere.</p>
<p><b>Objetivo general.</b> Diseñar, implementar y demostrar un sistema en el que una aplicación propia identifique a sus usuarios, los autentique contra un directorio mediante OpenID Connect y autorice sus operaciones según una matriz de roles derivada de las necesidades funcionales.</p>
<p><b>Objetivos específicos.</b> (1) Aplicar una nomenclatura consistente para usuarios, grupos, roles, clientes y scopes. (2) Implementar autenticación OAuth 2.0 / OpenID Connect con Authorization Code y PKCE usando herramientas gratuitas. (3) Integrar un directorio LDAP como fuente única de identidades y grupos. (4) Elaborar una matriz de roles y permisos y aplicarla en el backend. (5) Verificar con pruebas positivas y negativas que la autorización se cumple y justificar cada herramienta seleccionada.</p>
<p>El código, las guías y las evidencias están publicados en <b>{REPO}</b>.</p>
""")

# ---------------------------------------------------------------------------------------------- 2
sec("2", "Marco teórico", f"""
{tabla(["Concepto", "Idea central", "Cómo se aplica en el proyecto"], [
    ["<b>Identificación</b>", "Afirmar quién se es mediante una identidad digital única.", "Cuenta <code>apellido.nombre</code> en el directorio, con grupo y rol."],
    ["<b>Autenticación</b>", "Demostrar esa identidad con uno o más factores (algo que se sabe, algo que se tiene).", "Contraseña validada por el directorio y código TOTP (RFC 6238)."],
    ["<b>Autorización</b>", "Decidir qué puede hacer una identidad ya autenticada.", "RBAC con scopes, en el servidor, denegando por defecto."],
    ["<b>OAuth 2.0</b> (RFC 6749, 9700)", "Marco para delegar acceso limitado a una aplicación sin entregarle la contraseña.", "Flujo Authorization Code; sin Implicit ni Password Grant."],
    ["<b>OpenID Connect</b>", "Capa de identidad sobre OAuth 2.0: el ID token informa quién inició sesión.", "El ID token se valida con <code>iss</code>, <code>aud</code>, <code>exp</code>, <code>nonce</code> y firma."],
    ["<b>PKCE</b> (RFC 7636)", "Secreto de un solo uso (<code>code_verifier</code>) que impide usar un código interceptado.", "Método S256 en cada inicio de sesión."],
    ["<b>JWT / JWKS</b> (RFC 7519, 7517)", "Token firmado de tres partes verificable con la clave pública del emisor.", "Firma RS256 verificada en cada llamada a la API."],
    ["<b>RBAC</b> (INCITS 359)", "Los permisos se asignan a roles, no a personas; mínimo privilegio.", "5 roles y 16 scopes <code>recurso:acción</code>."],
    ["<b>LDAP / LDAPS</b> (RFC 4511)", "Protocolo para consultar y modificar un directorio de usuarios, cifrado en LDAPS.", "OpenLDAP como fuente única; Keycloak se federa por LDAPS."],
    ["<b>OWASP A01:2021</b>", "Control de acceso roto: el riesgo más frecuente en aplicaciones web (IDOR/BOLA).", "Control por propiedad con el <code>sub</code> del token."],
], anchos=["20%", "42%", "38%"], clases="t")}
""")

# ---------------------------------------------------------------------------------------------- 3
justif = [
    ["<b>Keycloak 26.8</b>", "Proveedor de identidad: OIDC, TOTP, federación LDAP, eventos", "Apache 2.0 · gratis", "Contenedor; no depende de internet", "Auth0, Okta, Entra ID (límites y nube)", "keycloak.org/documentation"],
    ["<b>OpenLDAP 2.6</b>", "Directorio de usuarios, grupos y política de contraseñas (<code>ppolicy</code>)", "OpenLDAP PL · gratis", "LDAPS; federa con Keycloak", "Samba AD DC, Windows AD DS, FreeIPA", "openldap.org/doc"],
    ["<b>Docker 29 / Compose</b>", "Despliegue reproducible de los servicios", "Apache 2.0 · gratis en Linux", "Mismo resultado en cualquier equipo", "Podman, instalación nativa", "docs.docker.com"],
    ["<b>OpenSSL 3</b>", "CA propia y certificados TLS", "Apache 2.0 · gratis", "Ya incluido en el sistema", "mkcert, Let's Encrypt", "openssl.org"],
    ["<b>PHP 8.3 + Apache 2.4</b>", "Aplicación y API protegida", "PHP License / Apache 2.0", "Extensión LDAP nativa; stack del curso", "Python + Flask + Authlib", "php.net · httpd.apache.org"],
    ["<b>firebase/php-jwt 7</b>", "Verificación de firmas RS256 con JWKS", "BSD-3 · gratis", "Fija el algoritmo por clave", "Firma manual, lcobucci/jwt", "github.com/firebase/php-jwt"],
    ["<b>PostgreSQL 16 · SQLite</b>", "Datos de Keycloak · datos de la app", "Libres · gratis", "PostgreSQL recomendado por Keycloak", "H2, MySQL", "postgresql.org · sqlite.org"],
    ["<b>OWASP ZAP 2.17</b>", "Escaneo pasivo y activo", "Apache 2.0 · gratis", "Automatizable en Docker", "Burp Community, Nikto", "zaproxy.org"],
    ["<b>tcpdump + tshark</b>", "Captura y análisis de tráfico (Wireshark en consola)", "BSD / GPLv2 · gratis", "Corre dentro de la red del contenedor", "Wireshark gráfico", "wireshark.org/docs"],
    ["<b>Python 3 · Chromium</b>", "Pruebas con login real (PKCE + TOTP) y capturas", "PSF · BSD · gratis", "Repetible con un comando", "Postman, Bruno, Selenium", "python.org"],
    ["<b>Git y GitHub</b>", "Control de versiones y entrega del código", "Gratis", "—", "GitLab", "github.com"],
]
sec("3", "Diseño", f"""
<h2>3.1 Nomenclatura</h2>
{tt(1, "Convención aplicada a todos los objetos del proyecto.")}
{tabla(["Elemento", "Formato", "Ejemplos reales", "Dónde"], [
    ["Usuario", "<code>apellido.nombre</code> (homónimo: número)", "<code>campbell.cesar</code>, <code>cruz.irvin</code>", "OpenLDAP (<code>uid</code>)"],
    ["Cuenta de servicio", "<code>svc-&lt;app&gt;-&lt;función&gt;</code>", "<code>svc-blackwall-sync</code>", "<code>ou=servicio</code>; sin login interactivo"],
    ["Grupo", "<code>GRP_&lt;ÁREA&gt;_&lt;ROL&gt;</code>", "<code>GRP_SOC_ANALISTA</code>", "OpenLDAP"],
    ["Rol", "<code>ROL_&lt;NOMBRE&gt;</code>", "<code>ROL_AUDITOR</code>", "Keycloak y claim <code>roles</code>"],
    ["Cliente OIDC", "<code>cli-&lt;app&gt;-&lt;entorno&gt;</code>", "<code>cli-blackwall-dev</code>", "Keycloak"],
    ["Scope", "<code>&lt;recurso&gt;:&lt;acción&gt;</code>", "<code>casos:leer</code>, <code>casos:leer_propios</code>", "Keycloak y cada endpoint"],
], anchos=["17%", "29%", "30%", "24%"], clases="t")}
<h2>3.2 Arquitectura</h2>
<p>Cuatro servicios en contenedores Docker se comunican por una red interna con TLS. La aplicación nunca recibe la contraseña: el navegador la entrega a Keycloak, que la valida contra el directorio. Los datos se guardan en tres lugares: OpenLDAP (usuarios, grupos, contraseñas con hash salado SSHA), PostgreSQL (copia del perfil, sesiones y secreto TOTP) y SQLite (casos, comentarios y auditoría).</p>
{figsvg(ARQ, "Arquitectura de Blackwall. En ámbar, la ruta de la contraseña: llega a Keycloak y al directorio, nunca a la aplicación.", "96%")}
<h2>3.3 Secuencia de autenticación (Authorization Code + PKCE)</h2>
{figsvg(secuencia(), "Inicio de sesión en cuatro fases (Authorization Code + PKCE): la aplicación genera PKCE, state y nonce; Keycloak valida contraseña y TOTP; la aplicación canjea el código y valida los tokens.", "96%")}
<h2>3.4 Selección de herramientas y justificación</h2>
{tt(2, "Herramientas, licencia, costo, compatibilidad, alternativas evaluadas y fuente.")}
{tabla(["Herramienta", "Función", "Licencia · costo", "Compatibilidad", "Alternativas evaluadas", "Fuente"], justif, anchos=["15%", "22%", "13%", "17%", "18%", "15%"], clases="t")}
<p>La guía permite elegir herramientas distintas a las sugeridas si se justifican. Se eligió <b>OpenLDAP</b> (alternativa admitida a Active Directory) por ser liviano y federarse con Keycloak por LDAPS; <b>PHP</b> por ser el stack del curso, con código corto y fácil de auditar; y un <b>cliente de pruebas propio en Python</b> en lugar de Postman o Bruno porque automatiza el flujo completo con PKCE y TOTP y permite repetir las 31 pruebas con un solo comando. Como límite, la imagen de contenedor de OpenLDAP utilizada (<i>bitnamilegacy</i>) ya no recibe actualizaciones de seguridad: es aceptable en laboratorio, pero en producción se usaría una imagen mantenida.</p>
""", True)

# ---------------------------------------------------------------------------------------------- 4
sec("4", "Implementación", f"""
<h2>4.1 Infraestructura y cifrado</h2>
<p>Un único archivo de Docker Compose define los servicios; un script prepara una autoridad certificadora propia (RSA 4096) y certificados de servidor para la aplicación, Keycloak, LDAPS y PostgreSQL. Los secretos se generan aleatoriamente y se guardan fuera del repositorio. Todas las conexiones usan TLS 1.3 verificado contra esa CA; PostgreSQL rechaza conexiones sin cifrar.</p>
{figtxt("tls-conexiones", "Conexiones TLS 1.3 verificadas contra la CA del laboratorio (aplicación y proveedor de identidad).", 17)}
<h2>4.2 Directorio (OpenLDAP)</h2>
<p>Una unidad organizativa por área (<code>ti</code>, <code>soc</code>, <code>cum</code>, <code>usr</code>, <code>pub</code>, <code>servicio</code>), un grupo <code>GRP_*</code> por rol y siete usuarios más la cuenta de servicio. La política de contraseñas (NIST SP 800-63B) se aplica en el propio directorio con el módulo <code>ppolicy</code>: mínimo 12 caracteres, historial de 5 y bloqueo tras 5 fallos. Solo la cuenta de servicio puede escribir; nadie anónimo lee.</p>
{duo(figtxt("ldap-grupos", "Grupos del directorio y sus miembros.", 16), figtxt("ldap-politica", "Política de contraseñas aplicada por OpenLDAP.", 16))}
<h2>4.3 Proveedor de identidad (Keycloak)</h2>
<p>El realm <code>proyecto-accesos</code> se configura por un script reproducible. El <i>group mapper</i> LDAP importa los grupos y cada grupo tiene asignado su rol, de modo que el mapeo grupo→rol es automático. El cliente <code>cli-blackwall-dev</code> usa Authorization Code con PKCE S256, <code>redirect_uri</code> exacta y tiene deshabilitados Implicit y Password Grant. El segundo factor TOTP es obligatorio para <code>ROL_ADMIN</code> y <code>ROL_AUDITOR</code> mediante condiciones por rol en el flujo de inicio de sesión. El access token dura 5 minutos y el refresh token rota en cada uso.</p>
{duo(fig("kc-federacion.png", "Federación con el directorio (LDAP)."), fig("kc-flujos.png", "Flujo de inicio de sesión con TOTP por rol."))}
<h2>4.4 Aplicación y API</h2>
<p>La aplicación PHP valida cada token (firma RS256 con JWKS, <code>iss</code>, <code>aud</code>, <code>exp</code> y tipo) y exige el scope propio de cada endpoint. Lo no declarado responde 404 y lo no permitido 403 (denegar por defecto). El rol nunca se toma de la interfaz. El navegador solo conserva una cookie de sesión (<code>Secure</code>, <code>HttpOnly</code>, <code>SameSite</code>); los tokens viven en el servidor. El cierre de sesión revoca la sesión en Keycloak y en la aplicación.</p>
{duo(figev("admin-login.png", "Pantalla de acceso."), figev("admin-inicio.png", "Inicio del administrador."))}
{duo(figev("admin-usuarios.png", "Gestión de usuarios (alta, edición, baja)."), figev("admin-auditoria.png", "Auditoría: eventos permitidos y denegados."))}
{duo(figev("analista-denegado.png", "Un analista abre Configuración: 403."), figev("usuario-casos.png", "Un usuario solo ve los casos que reportó."))}
<h2>4.5 Sesión por ciclos e inactividad (por rol)</h2>
<p>Además de los requisitos de la guía se implementó una política de sesión controlada por el servidor y definida por rol: cada renovación del acceso es un <i>ciclo</i>; al agotar los ciclos máximos, o si no hay actividad real durante el tiempo configurado, la sesión se cierra (con aviso previo “¿Sigues ahí?”) y la API deja de aceptar el token de inmediato. El administrador la configura en la pantalla Configuración y cada cierre queda en la auditoría.</p>
{figsvg(ciclos(), "Política de sesión: con actividad el acceso se renueva por ciclos hasta agotarlos; sin actividad se avisa y se cierra al superar el límite.", "96%")}
{duo(figev("admin-config-rol.png", "Configuración: política de sesión por rol."), figev("usuario-aviso.png", "Aviso antes de cerrar por inactividad."))}
""", True)

# ---------------------------------------------------------------------------------------------- 5
sec("5", "Matriz de roles aplicada y justificación", f"""
{figsvg(cadena(), "De grupo a permiso: el directorio define el grupo, Keycloak lo convierte en rol y scopes, y la API comprueba el scope en cada petición.", "96%")}
{figsvg(decision(), "Cómo decide la API cada petición: token, sesión, permiso y propiedad, en ese orden; lo no declarado responde 404.", "62%")}
{tt(3, "Matriz de roles (C = crear, R = leer, U = actualizar, D = borrar, — = sin acceso) y scopes asociados.")}
{tabla(["Recurso", "ADMIN", "ANALISTA", "AUDITOR", "USUARIO", "INVITADO"], [
    ["Usuarios del sistema", "CRUD <code>usuarios:admin</code>", "R <code>usuarios:leer</code>", "R <code>usuarios:leer</code>", "—", "—"],
    ["Casos de incidentes", "CRUD <code>casos:leer, escribir, borrar</code>", "CRU <code>casos:leer, escribir</code>", "R <code>casos:leer</code>", "CR propios <code>casos:crear, leer_propios, escribir_propios</code>", "—"],
    ["Comentarios", "CRUD <code>comentarios:escribir, borrar</code>", "CRU <code>comentarios:escribir</code>", "—", "CR en sus casos <code>comentarios:escribir_propios</code>", "—"],
    ["Panel de estadísticas", "R <code>estadisticas:leer</code>", "R <code>estadisticas:leer</code>", "R <code>estadisticas:leer</code>", "R lo suyo <code>estadisticas:leer_propios</code>", "R público <code>estadisticas:publicas</code>"],
    ["Registros de auditoría", "R <code>auditoria:leer</code>", "—", "R <code>auditoria:leer</code>", "—", "—"],
    ["Configuración del sistema", "CRU <code>config:admin</code>", "—", "—", "—", "—"],
], anchos=["16%", "20%", "16%", "14%", "22%", "12%"], clases="t")}
{tt(4, "Justificación de cada asignación (mínimo privilegio).")}
{tabla(["Rol", "Necesidad funcional", "Justificación"], [
    ["ADMIN", "Administrar cuentas y configuración", "Solo <b>lee</b> la auditoría para no poder alterar la trazabilidad de sus propias acciones."],
    ["ANALISTA", "Gestionar y resolver casos", "Opera el día a día; no borra casos ni administra usuarios."],
    ["AUDITOR", "Revisar cumplimiento y trazabilidad", "Solo lectura: separación de funciones; quien audita no opera ni modifica."],
    ["USUARIO", "Reportar incidentes propios y consultar su estado", "Control por propiedad: aunque tenga el scope, solo accede a registros cuyo <code>sub</code> es el suyo."],
    ["INVITADO", "Consultar información pública", "Acceso mínimo, sin datos internos."],
], anchos=["12%", "30%", "58%"], clases="t")}
<p>La asignación sigue el flujo directorio → Keycloak → aplicación: cada usuario pertenece a un grupo <code>GRP_&lt;ÁREA&gt;_&lt;ROL&gt;</code>; Keycloak lo mapea al rol <code>ROL_&lt;NOMBRE&gt;</code> y concede únicamente los scopes de ese rol; la API verifica el scope en cada endpoint y no confía en el rol que llegue desde la interfaz.</p>
""")

# ---------------------------------------------------------------------------------------------- 6
filas = [[c["id"], esc(c["caso"]), esc(c["actor"]), esc(c["accion"]), esc(c["esperado"]), "Pasa" if c["ok"] else "Falla"] for c in res["casos"]]
sec("6", "Pruebas y resultados", f"""
<p>Las pruebas se ejecutan contra el sistema real (login con PKCE y TOTP incluidos) con un solo comando. Los casos CP-01 a CP-10 son los sugeridos por la guía; CP-11 a CP-31 se agregaron para cubrir segundo factor, PKCE, rotación de refresh token, cierre de sesión, control por propiedad, administración de usuarios, política de contraseñas y la política de sesión por rol. <b>Resultado: {res['pasan']} de {res['total']} casos pasan</b> (la guía exige un mínimo de 10).</p>
{tt(5, "Tabla de pruebas de aceptación (positivas y negativas).")}
{tabla(["ID", "Caso", "Rol / actor", "Acción", "Resultado esperado", "Estado"], filas, anchos=["6%", "22%", "13%", "20%", "33%", "6%"], clases="t")}
<h2>6.1 Escaneo con OWASP ZAP: antes y después</h2>
<p>Se ejecutó un escaneo pasivo y activo (autenticado y sin sesión) antes y después del endurecimiento. Resultado: de 2 alertas medias y 4 bajas a ninguna.</p>
{duo(fig("zap-antes.png", "ZAP antes: 0 altas, 2 medias, 4 bajas."), fig("zap-despues.png", "ZAP después: 0 altas, 0 medias, 0 bajas."))}
<h2>6.2 Verificación del cifrado</h2>
<p>Se capturó el tráfico de un inicio de sesión real con tcpdump y se analizó con tshark (la versión de consola de Wireshark; los archivos <code>.pcap</code> abren en Wireshark). Con HTTPS no se observó ninguna contraseña, token, secreto de cliente ni <code>code_verifier</code>; el experimento de control sin TLS sí los mostró.</p>
{figtxt("captura-login", "Análisis del tráfico del login: 0 coincidencias con HTTPS; el control sin TLS sí expone los datos.")}
<h2>6.3 Análisis de hallazgos y su corrección</h2>
{tt(6, "Hallazgos de seguridad detectados por las pruebas y por ZAP, y su corrección.")}
{tabla(["Hallazgo", "Detectado por", "Corrección"], [
    ["<b>El auditor podía modificar casos</b> (escalada de privilegios): un rol técnico compuesto compartido hacía que los permisos del administrador alcanzaran al auditor", "CP-07", "Se eliminó el rol compuesto; el segundo factor se decide con condiciones por rol"],
    ["Un atributo del cliente pisaba la vida del token configurada", "CP-03", "Se quitó el atributo; manda el valor del realm"],
    ["Un cambio de grupo en el directorio no cambiaba el rol", "CP-23", "Federación LDAP sin caché"],
    ["La auditoría no mostraba los eventos de Keycloak", "CP-02, CP-24", "Scope <code>kc-admin-api</code> exigido por Keycloak 26.8, con permisos mínimos"],
    ["La pantalla de Configuración no guardaba los cambios", "CP-28 a CP-31", "Se envían a Keycloak solo los campos modificados"],
    ["Sin CSP ni protección anti-clickjacking (medias); XSS persistente en JSON, versión del servidor visible, sin HSTS ni <code>nosniff</code> (bajas)", "ZAP", "CSP estricta, <code>X-Frame-Options</code>, HSTS, <code>nosniff</code>, JSON escapado y ocultar la versión"],
    ["Errores de PHP visibles al usuario; librería JWT con aviso de seguridad", "CP-02; instalación", "<code>display_errors=Off</code>; se usa <code>php-jwt</code> 7.x"],
], anchos=["50%", "14%", "36%"], clases="t")}
""", True)

# ---------------------------------------------------------------------------------------------- 7
sec("7", "Consideraciones finales", f"""
<p><b>¿Qué diferencia práctica se observó entre identificar, autenticar y autorizar?</b> Identificar es afirmar quién se es (el usuario <code>campbell.cesar</code>); autenticar es demostrarlo (contraseña validada por el directorio y código TOTP); autorizar es decidir qué se puede hacer. Un analista con sesión válida —ya identificado y autenticado— recibe 403 al pedir la configuración (CP-08): la identidad era correcta, pero el rol no tenía el permiso.</p>
<p><b>¿Por qué el access token no debe contener contraseñas ni datos innecesarios?</b> Un JWT está firmado pero no cifrado: cualquiera que lo vea puede leer su contenido, y los tokens circulan por cabeceras, registros y herramientas de depuración. Por minimización de datos, el token de Blackwall solo lleva el identificador del usuario, su rol, sus scopes y los tiempos de validez, y dura 5 minutos; la contraseña nunca sale de Keycloak y el directorio.</p>
<p><b>¿Qué riesgo existe si la autorización se implementa solo en la interfaz?</b> Que cualquiera puede llamar directamente a la API (con <code>curl</code>, por ejemplo) saltándose los botones ocultos. En Blackwall el menú solo oculta opciones; el servidor valida el token y el scope en cada endpoint. Las pruebas CP-05 a CP-08 y CP-19 a CP-21 lo comprueban llamando a la API directamente, y el hallazgo CP-07 mostró que un error de configuración también puede abrir permisos, por lo que verificar en el servidor es indispensable.</p>
<p><b>¿Qué cambiaríamos para llevar el sistema a producción?</b> Un gestor de secretos con rotación en lugar de variables de entorno; rotación periódica de las claves de firma; certificados de una CA pública o corporativa; auditoría centralizada y de solo anexar (SIEM); respaldo y alta disponibilidad del proveedor de identidad y del directorio; una imagen de OpenLDAP mantenida (o Active Directory si la organización ya lo usa); segundo factor para todos los roles; y límites de tasa y un WAF delante de la aplicación.</p>
<p><b>¿Qué herramienta gratuita elegiríamos de nuevo y cuál cambiaríamos?</b> Volveríamos a elegir Keycloak (estándares completos y federación LDAP), Docker (reproducibilidad) y OWASP ZAP (automatizable y con resultados accionables). Cambiaríamos la imagen de OpenLDAP utilizada por una mantenida o por Samba AD, y complementaríamos tshark con la interfaz gráfica de Wireshark para la evidencia visual.</p>
""")

# ---------------------------------------------------------------------------------------------- 8
sec("8", "Conclusiones", f"""
<ul>
<li>Se construyó un sistema funcional donde la aplicación <b>no ve ni almacena contraseñas</b>: las valida el directorio a través de Keycloak con Authorization Code + PKCE, y el segundo factor TOTP es obligatorio para administrador y auditor.</li>
<li>El directorio OpenLDAP funciona como <b>fuente única</b> de identidades y grupos, con mapeo automático grupo→rol y política de contraseñas aplicada en el propio directorio.</li>
<li>La <b>autorización se aplica en el servidor</b>: matriz por rol, mínimo privilegio, denegar por defecto y control por propiedad; no depende de la interfaz.</li>
<li>Se ejecutaron <b>31 pruebas positivas y negativas</b> con evidencia; el escaneo con ZAP pasó de 2 alertas medias y 4 bajas a ninguna y se verificó que no viajan credenciales en texto plano.</li>
<li>Las propias pruebas descubrieron fallos reales (entre ellos una escalada de privilegios del auditor) que se corrigieron y se volvieron a probar: la verificación continua es parte del diseño seguro.</li>
<li>Todo el sistema se levanta con un comando y quedó publicado y reproducible en el repositorio del proyecto.</li>
</ul>
""")

# ---------------------------------------------------------------------------------------------- 9
sec("9", "Declaración del uso de herramientas de inteligencia artificial", f"""
<p>Conforme a lo exigido en la guía, se declara que en este proyecto se utilizó un asistente de inteligencia artificial: <b>Claude Code</b> (Anthropic, modelo Claude Sonnet 5.5). Se empleó como apoyo para: escribir y revisar código de la aplicación y de los scripts de infraestructura; configurar Keycloak y OpenLDAP; diseñar y automatizar las pruebas; ejecutar y analizar los escaneos; y redactar la documentación y las guías. El equipo definió los requisitos, decidió las herramientas, ejecutó el sistema, revisó los resultados y validó las pruebas; los resultados presentados provienen de ejecuciones reales documentadas en el repositorio.</p>
""")

# ---------------------------------------------------------------------------------------------- 10
sec("10", "Referencias", """
<ul class="small" style="font-size:8.6pt">
<li>IETF. (2012). <i>RFC 6749: The OAuth 2.0 Authorization Framework</i>. https://www.rfc-editor.org/rfc/rfc6749</li>
<li>IETF. (2015). <i>RFC 7636: Proof Key for Code Exchange by OAuth Public Clients (PKCE)</i>. https://www.rfc-editor.org/rfc/rfc7636</li>
<li>IETF. (2015). <i>RFC 7519: JSON Web Token (JWT)</i>. RFC 7515 (JWS), RFC 7517 (JWK), RFC 7518 (JWA).</li>
<li>IETF. (2025). <i>RFC 9700: Best Current Practice for OAuth 2.0 Security</i>.</li>
<li>IETF. (2011). <i>RFC 6238: TOTP: Time-Based One-Time Password Algorithm</i>.</li>
<li>IETF. (2018). <i>RFC 8446: The Transport Layer Security (TLS) Protocol Version 1.3</i>.</li>
<li>IETF. (2006). <i>RFC 4511: Lightweight Directory Access Protocol (LDAP): The Protocol</i>.</li>
<li>OpenID Foundation. (2014). <i>OpenID Connect Core 1.0</i>. https://openid.net/specs/openid-connect-core-1_0.html</li>
<li>NIST. (2017). <i>SP 800-63B: Digital Identity Guidelines: Authentication and Lifecycle Management</i>.</li>
<li>NIST. (2004). <i>INCITS 359-2004: Role-Based Access Control</i>.</li>
<li>OWASP. (2021). <i>OWASP Top 10:2021, A01 Broken Access Control</i>. OWASP. (2019). <i>Application Security Verification Standard (ASVS) v4.0.3</i>.</li>
<li>Keycloak. (2026). <i>Keycloak documentation</i>. https://www.keycloak.org/documentation</li>
<li>OpenLDAP Project. (2026). <i>OpenLDAP Administrator's Guide</i>. https://www.openldap.org/doc/</li>
<li>OWASP. (2026). <i>ZAP documentation</i>. https://www.zaproxy.org/docs/</li>
</ul>""")

# ---------------------------------------------------------------------------------------------- A
sec("A", "Anexo A. Código principal y cómo reproducir el sistema", f"""
{tt(7, "Archivos y funciones principales (repositorio " + REPO + ").")}
{tabla(["Archivo / función", "Qué hace"], [
    ["<code>app/src/Tokens.php</code> · <code>verificar()</code>", "Exige RS256, verifica la firma con JWKS y comprueba <code>exp</code>, <code>iss</code>, <code>aud</code>, <code>typ</code> y <code>nonce</code>."],
    ["<code>app/src/Oidc.php</code>", "Crea PKCE, <code>state</code> y <code>nonce</code>; canjea el código; renueva con rotación; revoca la sesión."],
    ["<code>app/src/Api.php</code>", "Autentica el Bearer (401), exige el scope (403), aplica control por propiedad y deniega por defecto (404)."],
    ["<code>app/src/Sesiones.php</code>", "Ciclos, inactividad y cierre inmediato de sesiones, por rol."],
    ["<code>app/src/Ldap.php</code> · <code>Keycloak.php</code>", "Administración de usuarios en el directorio; eventos y parámetros del realm."],
    ["<code>app/public/index.php</code>", "Rutas de sesión: <code>/callback</code>, <code>/auth/sesion</code>, <code>/auth/logout</code>; valida <code>state</code> y regenera la sesión."],
    ["<code>keycloak/configurar.py</code>", "Configura realm, roles, scopes, clientes, federación LDAP, mapeo grupo→rol y MFA por rol."],
    ["<code>pruebas/casos_prueba.py</code>", "Ejecuta los 31 casos contra el sistema real y genera la tabla de resultados."],
], anchos=["38%", "62%"], clases="t")}
<p><b>Reproducir:</b> con Docker, Python 3 y OpenSSL instalados: <code>git clone {REPO}</code>, luego <code>cd Blackwall/blackwall-real &amp;&amp; scripts/bw.sh arriba</code> y abrir <code>https://app.localhost:8444</code>. Las pruebas: <code>scripts/bw.sh pruebas</code>.</p>
""")

# ---------------------------------------------------------------------------------------------- B
sec("B", "Anexo B. Cumplimiento de la rúbrica", f"""
{tabla(["Criterio (peso)", "Evidencia en este informe", "Estado"], [
    ["Identificación y nomenclatura (15%)", "Sección 3.1, tabla 1", "<span class='pill ok'>Cumple</span>"],
    ["Autenticación OAuth 2.0 / OIDC (25%)", "Secciones 3.3, 4.3 y 4.4; pruebas CP-01, 03, 04, 09, 11 a 18", "<span class='pill ok'>Cumple</span>"],
    ["Integración con el directorio (15%)", "Secciones 4.2 y 4.3; CP-22, 23, 27", "<span class='pill ok'>Cumple</span>"],
    ["Autorización: matriz y aplicación (20%)", "Sección 5; CP-05 a 08, 19 a 21", "<span class='pill ok'>Cumple</span>"],
    ["Pruebas de seguridad y evidencias (10%)", "Sección 6; tabla 5; ZAP y captura de red", "<span class='pill ok'>Cumple</span>"],
    ["Justificación de herramientas (5%)", "Sección 3.4, tabla 2", "<span class='pill ok'>Cumple</span>"],
    ["Informe completo (10%)", "Este documento", "<span class='pill ok'>Completo</span>"],
], anchos=["34%", "50%", "16%"], clases="t")}
""")

# ---------------------------------------------------------------------------------------------- notas internas
sec("N", "Notas para quien redacta la versión final (eliminar esta página antes de entregar)", f"""
{nota("Este informe sigue la estructura de la sección 14 de la guía. Está listo para adaptarse: cambiar el formato a su plantilla, completar los datos de la portada y revisar que todo coincida con lo que se presentará.", "al")}
<h2>Qué completar o verificar</h2>
<ul>
<li><b>Portada:</b> número de grupo, fecha de entrega y la ortografía de los nombres de los integrantes (en el sistema figuran Cesar Campbell, Irvin Cruz, Nicole Pinto, Angel Galvez y Moisés Cordero).</li>
<li><b>Resumen:</b> máximo 200 palabras (este tiene unas 170).</li>
<li><b>Entrega:</b> un único PDF con los entregables E1 a E6 y el enlace al repositorio (<b>{REPO}</b>); <b>sin contraseñas, secretos ni tokens completos</b> (ya están redactados en las capturas).</li>
<li><b>Declaración de IA (sección 9):</b> es obligatoria; revisar que describa fielmente el uso.</li>
</ul>
<h2>Pendientes del equipo (no son del documento)</h2>
<ul>
<li>Que el administrador (<code>campbell.cesar</code>) y el auditor (<code>galvez.angel</code>) <b>configuren su segundo factor</b> con su celular en el primer ingreso; conviene una captura de ese momento (código QR) para el informe, tapando la clave.</li>
<li>Entregar a cada compañero <b>su propia contraseña</b> antes de usar el sitio público.</li>
<li>Preparar la <b>demostración en vivo (7 de diciembre)</b>: iniciar sesión con cada rol, un intento denegado (analista abriendo Configuración) y la revisión de la auditoría; mostrar también la sesión por ciclos con una inactividad corta.</li>
<li>Todos deben dominar la aplicación: apoyarse en la <i>Guía técnica</i> (46 págs.) y la <i>Guía resumida</i> (22 págs.) del repositorio, que incluyen glosario y un reparto de temas.</li>
</ul>
<h2>Dónde está cada cosa</h2>
<ul><li>Código y evidencias: <b>{REPO}</b> (carpeta <code>blackwall-real/</code>; resultados en <code>evidencias/</code>).</li><li>Servidor público para la demostración: carpeta <code>servidor-blackwall/</code> (comandos en su README).</li></ul>
""")


# ---------------------------------------------------------------------------------------------- armado
def etiqueta(n):
    return n


def construir(pags, pfig):
    toc = "".join(f'<div class="row"><b>{n}</b><span class="t">{t}</span><span class="p">{pags.get(n, "")}</span></div>' for n, t, _, _ in S if n not in ("N",))
    figidx = "".join(f'<div class="row sub"><b>{n}</b><span class="t">{t}</span><span class="p">{pfig.get(n, "")}</span></div>' for n, t in FIGS)
    cuerpo = "".join(
        f'<section class="sec{" salto" if salto else ""}"><h1>{("Anexo" if False else "")}{(n + ". ") if n.isdigit() else ""}{t}</h1>{h}</section>' for n, t, h, salto in S)
    resumen = ("Blackwall es una aplicación web de gestión de incidentes de seguridad que demuestra, con un sistema real y reproducible, la identificación, autenticación y autorización de sus usuarios. "
               "La aplicación no recibe contraseñas: Keycloak las valida contra un directorio OpenLDAP mediante OpenID Connect con Authorization Code y PKCE, y exige un segundo factor TOTP a administrador y auditor. "
               "La autorización se aplica en el servidor con una matriz de cinco roles y dieciséis permisos, denegando por defecto y controlando la propiedad de los registros. "
               "Todos los componentes usan TLS y herramientas gratuitas, justificadas por licencia, costo y compatibilidad. "
               "Treinta y una pruebas positivas y negativas pasan; el escaneo con OWASP ZAP pasó de 2 alertas medias y 4 bajas a ninguna, y una captura de red confirmó que no viajan credenciales en texto plano. "
               "Las pruebas detectaron fallos reales, entre ellos una escalada de privilegios, que se corrigieron y se verificaron de nuevo. El informe describe el diseño, la implementación, los resultados y las lecciones aprendidas.")
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Blackwall · Informe del proyecto final</title><style>{CSS}{EXTRA}</style></head><body>
<div class="cover"><div class="lg">{LOGO}BLACKWALL</div>
<div><div class="eslo">Informe del proyecto final</div><h1>Seguridad en accesos: identificación, autenticación y autorización</h1>
<p>Sistema de acceso seguro con OAuth 2.0 / OpenID Connect y autorización por roles (RBAC) sobre un directorio.</p></div>
<div class="foot" style="font-size:10pt">Universidad Tecnológica de Panamá · Facultad de Ingeniería de Sistemas Computacionales<br>Departamento de Arquitectura y Redes de Computadoras · Ciberseguridad II<br>Facilitadora: Mildred Echezano<br><br>
Integrantes: Cesar Campbell · Irvin Cruz · Nicole Pinto · Angel Galvez · Moisés Cordero<br>Grupo: ________ &nbsp;&nbsp;&nbsp; Fecha: ____ / ____ / ________<br>Repositorio: {REPO}</div></div>
<section><h1>Resumen</h1><p>{resumen}</p><p class="small"><b>Palabras clave:</b> identificación, autenticación, autorización, OAuth 2.0, OpenID Connect, PKCE, RBAC, MFA, OpenLDAP, Keycloak.</p>
<h1 style="margin-top:8mm">Índice general</h1><div class="toc">{toc}</div></section>
<section class="salto"><h1>Índice de figuras</h1><div class="toc">{figidx}</div></section>
{cuerpo}</body></html>"""


def a_pdf():
    subprocess.run(["chromium-browser", "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={PDF}", "--virtual-time-budget=20000", "file://" + HTML], capture_output=True, text=True, timeout=300)
    if not os.path.exists(PDF):
        sys.exit("No se generó el PDF")


def paginas():
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", PDF], capture_output=True, text=True).stdout).group(1))
    tx = {p: subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), "-layout", PDF, "-"], capture_output=True, text=True).stdout for p in range(1, n + 1)}
    pags = {}
    for num, t, _, _ in S:
        plano = re.sub(r"<[^>]+>", "", t)[:26]
        for p in range(3, n + 1):
            pat = rf"^\s*{re.escape(num)}\.\s+{re.escape(plano)}" if num.isdigit() else rf"^\s*{re.escape(plano)}"
            if re.search(pat, tx[p], re.M):
                pags[num] = p
                break
    pfig = {}
    for k, _ in FIGS:
        for p in range(4, n + 1):
            if re.search(rf"Figura {k}\.", tx[p]):
                pfig[k] = p
                break
    return pags, pfig, n


open(HTML, "w").write(construir({}, {}))
a_pdf()
pags, pfig, total = paginas()
open(HTML, "w").write(construir(pags, pfig))
a_pdf()
print("páginas:", total, "· figuras:", len(FIGS), "· secciones:", len(pags), "de", len(S))
print(PDF)
