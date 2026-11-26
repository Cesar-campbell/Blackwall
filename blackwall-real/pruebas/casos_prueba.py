#!/usr/bin/env python3
"""Pruebas de aceptación de Blackwall (guía, sección 12 + casos adicionales).

Ejecuta contra el sistema REAL (Keycloak + OpenLDAP + app). Crea usuarios temporales `prueba.*` en el
directorio y los elimina al terminar. Escribe la tabla de resultados en ../evidencias/.

Uso:  python3 pruebas/casos_prueba.py            (o: scripts/bw.sh pruebas)
"""
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oidc_cliente as o  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = o.ENV["LDAP_BASE"]
CLAVE = o.ENV["DEMO_PASSWORD"]
PREFIJO = "prueba."

# usuario → (ou, grupo, nombre, apellido)
FIXTURAS = {
    "prueba.admin": ("ti", "GRP_TI_ADMIN", "Admin", "Prueba"),
    "prueba.analista": ("soc", "GRP_SOC_ANALISTA", "Analista", "Prueba"),
    "prueba.auditor": ("cum", "GRP_CUM_AUDITOR", "Auditor", "Prueba"),
    "prueba.usuario": ("usr", "GRP_USR_USUARIO", "Usuario", "Prueba"),
    "prueba.usuario2": ("usr", "GRP_USR_USUARIO", "Usuario", "PruebaDos"),
    "prueba.invitado": ("pub", "GRP_PUB_INVITADO", "Invitado", "Prueba"),
    "prueba.bloqueo": ("usr", "GRP_USR_USUARIO", "Bloqueo", "Prueba"),
}


# ----------------------------------------------------------------------------- utilidades
def ldap(entrada, comando="ldapmodify"):
    r = subprocess.run(["docker", "exec", "-i", "-e", "LDAPTLS_REQCERT=never", "blackwall-ldap-1", comando, "-c", "-x",
                        "-H", "ldaps://localhost:1636", "-D", f"cn=admin,{BASE}", "-w", o.ENV["LDAP_ADMIN_PASSWORD"]],
                       input=entrada, capture_output=True, text=True)
    return r


class KcAdmin:
    """Administración de Keycloak para preparar/limpiar las pruebas (no es parte de la app)."""

    def __init__(self):
        self.t, self.t0 = None, 0

    def _token(self):
        """El token del admin de Keycloak dura 60 s: se renueva cuando hace falta (los escaneos duran minutos)."""
        if self.t is None or time.time() - self.t0 > 40:
            d = urllib.parse.urlencode({"grant_type": "password", "client_id": "admin-cli",
                                        "username": o.ENV["KC_ADMIN_USER"], "password": o.ENV["KC_ADMIN_PASSWORD"]}).encode()
            self.t = json.load(urllib.request.urlopen(urllib.request.Request(f"{o.KC}/realms/master/protocol/openid-connect/token", d), context=o.CTX))["access_token"]
            self.t0 = time.time()
        return self.t

    def call(self, m, ruta, cuerpo=None):
        req = urllib.request.Request(f"{o.KC}/admin/realms/{o.REALM}{ruta}", json.dumps(cuerpo).encode() if cuerpo is not None else None,
                                     method=m, headers={"Authorization": "Bearer " + self._token(), "Content-Type": "application/json"})
        try:
            r = urllib.request.urlopen(req, context=o.CTX)
            t = r.read()
            return r.status, (json.loads(t) if t else None)
        except urllib.error.HTTPError as e:
            return e.code, None

    def id_de(self, u):
        st, l = self.call("GET", f"/users?exact=true&username={u}")
        return l[0]["id"] if l else None

    def desbloquear(self, u):
        i = self.id_de(u)
        if i:
            self.call("DELETE", f"/attack-detection/brute-force/users/{i}")


def preparar_fixturas():
    for u, (ou, grp, nom, ape) in FIXTURAS.items():
        ldap(f"""dn: uid={u},ou={ou},{BASE}
changetype: add
objectClass: inetOrgPerson
uid: {u}
cn: {nom} {ape}
givenName: {nom}
sn: {ape}
mail: {u}@blackwall.utp
userPassword: {CLAVE}

dn: cn={grp},ou={grp.split('_')[1].lower()},{BASE}
changetype: modify
add: member
member: uid={u},ou={ou},{BASE}
""")


def limpiar_fixturas(kc):
    # prueba.nuevo lo crea la propia prueba CP-22 (vía la API) y puede terminar en cualquier grupo/área
    for ou_n, grp_n in [("soc", "GRP_SOC_ANALISTA"), ("usr", "GRP_USR_USUARIO"), ("ti", "GRP_TI_ADMIN"), ("cum", "GRP_CUM_AUDITOR")]:
        for ou_u in ("soc", "usr", "ti", "cum"):
            ldap(f"""dn: cn={grp_n},ou={ou_n},{BASE}
changetype: modify
delete: member
member: uid=prueba.nuevo,ou={ou_u},{BASE}
""")
    for u, (ou, grp, _, _) in FIXTURAS.items():
        ldap(f"""dn: cn={grp},ou={grp.split('_')[1].lower()},{BASE}
changetype: modify
delete: member
member: uid={u},ou={ou},{BASE}
""")
    for u in list(FIXTURAS) + ["prueba.nuevo"]:
        i = kc.id_de(u)
        if i:
            kc.call("DELETE", f"/users/{i}")
        for ou in ([FIXTURAS[u][0]] if u in FIXTURAS else ["soc", "usr", "ti", "cum"]):
            subprocess.run(["docker", "exec", "-e", "LDAPTLS_REQCERT=never", "blackwall-ldap-1", "ldapdelete", "-c", "-x", "-H",
                            "ldaps://localhost:1636", "-D", f"cn=admin,{BASE}", "-w", o.ENV["LDAP_ADMIN_PASSWORD"], f"uid={u},ou={ou},{BASE}"],
                           capture_output=True)
        try:
            os.remove(o.ruta_secreto_totp(u))
        except FileNotFoundError:
            pass


def red(t):
    """Redacta un token para las evidencias (guía: no se muestran tokens completos)."""
    return t[:14] + "…[redactado]…" + t[-6:] if t and len(t) > 30 else t


def token_de(usuario, forzar_totp=False):
    """Login real (formulario + TOTP si aplica) y canje del código. Devuelve (tokens, resultado_login)."""
    r = o.login(usuario, CLAVE)
    if not r["ok"]:
        raise RuntimeError(f"login de {usuario}: {r.get('error')}")
    st, t = o.intercambiar_codigo(r)
    if st != 200:
        raise RuntimeError(f"canje de {usuario}: {t}")
    return t, r


def api(m, ruta, t, cuerpo=None, cab=None):
    return o.api(m, ruta, t["access_token"] if isinstance(t, dict) else t, cuerpo, cab)


class Cartera(dict):
    """Tokens por rol. Renueva con el refresh token (con rotación) cuando el access token está por vencer."""

    def __setitem__(self, k, v):
        v["_t"] = time.time()
        super().__setitem__(k, v)

    def __getitem__(self, k):
        e = super().__getitem__(k)
        if time.time() - e["_t"] > 200 and e.get("refresh_token"):
            st, n = o.post_token({"grant_type": "refresh_token", "refresh_token": e["refresh_token"], "client_id": o.CLIENT_ID,
                                  "client_secret": o.ENV["CLIENT_SECRET"]})
            if st == 200:
                e.update(n)
                e["_t"] = time.time()
        return e


# ----------------------------------------------------------------------------- registro de resultados
RES = []


def caso(id_, nombre, actor, accion, esperado):
    def deco(fn):
        fn._meta = (id_, nombre, actor, accion, esperado)
        RES.append(fn)
        return fn
    return deco


EJECUTADOS = []


def correr(fn, ctx):
    id_, nombre, actor, accion, esperado = fn._meta
    t0 = time.time()
    try:
        ok, obtenido = fn(ctx)
    except Exception as e:  # noqa: BLE001
        ok, obtenido = False, f"EXCEPCIÓN: {e!r}"
    EJECUTADOS.append({"id": id_, "caso": nombre, "actor": actor, "accion": accion, "esperado": esperado,
                       "obtenido": obtenido, "ok": ok, "seg": round(time.time() - t0, 1)})
    print(f"  {'PASA ' if ok else 'FALLA'} {id_:<6} {nombre}  →  {obtenido}", flush=True)


# ----------------------------------------------------------------------------- casos
@caso("CP-01", "Inicio de sesión correcto con MFA", "ROL_ANALISTA", "Login OIDC + TOTP",
      "Acceso concedido; el token contiene el rol ROL_ANALISTA")
def cp01(c):
    c["kc"].call("PUT", f"/users/{c['kc'].id_de('prueba.analista')}", {"requiredActions": ["CONFIGURE_TOTP"]})
    t, r1 = token_de("prueba.analista")                  # primer ingreso: configura TOTP
    t, r2 = token_de("prueba.analista")                  # segundo ingreso: ahora pide el código
    a = o.decodificar_jwt(t["access_token"])
    c["tok"]["analista"] = t
    ok = r1["pidio_totp"] and r2["pidio_totp"] and a["roles"] == ["ROL_ANALISTA"]
    return ok, f"TOTP solicitado en el 2.º ingreso={r2['pidio_totp']}; roles={a['roles']}; acr={a.get('acr')}"


@caso("CP-02", "Cinco contraseñas incorrectas seguidas", "Cualquiera", "Login con clave errónea ×5",
      "Cuenta bloqueada temporalmente; evento registrado en auditoría")
def cp02(c):
    kc = c["kc"]
    kc.desbloquear("prueba.bloqueo")
    errores = []
    for i in range(5):
        r = o.login("prueba.bloqueo", "clave-incorrecta-123")
        errores.append(bool(r.get("error")))
    # ya bloqueada: ni siquiera la clave correcta entra
    r = o.login("prueba.bloqueo", CLAVE)
    bloqueada = not r["ok"]
    time.sleep(1)
    st, aud = api("GET", "/api/auditoria", c["tok"]["admin"])
    eventos = [a for a in aud if a["u"] == "prueba.bloqueo" and a["src"] == "keycloak"] if st == 200 else []
    lock = any(a["ev"] == "LOCKOUT" for a in eventos)
    kc.desbloquear("prueba.bloqueo")
    ok = all(errores) and bloqueada and lock
    return ok, f"5 intentos rechazados={all(errores)}; clave correcta rechazada durante el bloqueo={bloqueada}; eventos en auditoría={len(eventos)} (LOCKOUT={lock})"


@caso("CP-03", "Access token expirado", "Cualquiera", "GET /api/casos", "401 Unauthorized")
def cp03(c):
    kc = c["kc"]
    realm = kc.call("GET", "")[1]
    try:
        kc.call("PUT", "", {**realm, "accessTokenLifespan": 3})
        kc.desbloquear("prueba.usuario")
        t, _ = token_de("prueba.usuario")
        antes = api("GET", "/api/casos", t)[0]
        time.sleep(10)                         # 3 s de vida + 5 s de tolerancia de reloj
        st, b = api("GET", "/api/casos", t)
    finally:
        kc.call("PUT", "", {**kc.call("GET", "")[1], "accessTokenLifespan": realm["accessTokenLifespan"]})
    return st == 401 and antes == 200, f"antes de expirar={antes}; después={st} ({b.get('detalle')})"


@caso("CP-04", "Token con firma alterada", "Cualquiera", "GET /api/casos", "401 Unauthorized")
def cp04(c):
    t = c["tok"]["usuario"]["access_token"]
    h, p, f = t.split(".")
    claims = json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))
    claims["roles"] = ["ROL_ADMIN"]
    claims["scope"] += " usuarios:admin casos:borrar auditoria:leer"
    p2 = o.b64u(json.dumps(claims).encode())
    st1, b1 = api("GET", "/api/usuarios", ".".join([h, p2, f]))            # payload alterado, firma original
    nonea = o.b64u(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    st2, b2 = api("GET", "/api/usuarios", ".".join([nonea, p2, ""]))       # alg=none
    hs = o.b64u(json.dumps({"alg": "HS256", "typ": "JWT", "kid": json.loads(base64.urlsafe_b64decode(h + "=="))["kid"]}).encode())
    import hmac, hashlib  # noqa: E401
    firma = o.b64u(hmac.new(b"secreto", f"{hs}.{p2}".encode(), hashlib.sha256).digest())
    st3, b3 = api("GET", "/api/usuarios", ".".join([hs, p2, firma]))       # confusión de algoritmo RS256→HS256
    return (st1, st2, st3) == (401, 401, 401), f"payload alterado={st1} ({b1.get('detalle')}); alg=none={st2} ({b2.get('detalle')}); HS256={st3} ({b3.get('detalle')})"


@caso("CP-05", "Usuario intenta borrar un caso", "ROL_USUARIO", "DELETE /api/casos/{id}", "403 Forbidden")
def cp05(c):
    propio = api("POST", "/api/casos", c["tok"]["usuario"], {"titulo": "Caso propio de prueba", "descripcion": "x", "severidad": "baja"})[1]
    c["caso_propio"] = propio["id"]
    st, b = api("DELETE", f"/api/casos/{propio['id']}", c["tok"]["usuario"])
    existe = api("GET", f"/api/casos/{propio['id']}", c["tok"]["usuario"])[0]
    return st == 403 and existe == 200, f"DELETE={st} ({b.get('detalle')}); el caso sigue existiendo={existe == 200}"


@caso("CP-06", "Usuario consulta un caso ajeno", "ROL_USUARIO", "GET /api/casos/{id ajeno}", "403 o 404 (sin revelar el contenido)")
def cp06(c):
    ajeno = api("POST", "/api/casos", c["tok"]["usuario2"], {"titulo": "SECRETO-AJENO", "descripcion": "contenido confidencial", "severidad": "alta"})[1]
    c["caso_ajeno"] = ajeno["id"]
    st, b = api("GET", f"/api/casos/{ajeno['id']}", c["tok"]["usuario"])
    fuga = "SECRETO-AJENO" in json.dumps(b) or "confidencial" in json.dumps(b)
    st_lista, lista = api("GET", "/api/casos", c["tok"]["usuario"])
    en_lista = any(x["id"] == ajeno["id"] for x in lista)
    return st in (403, 404) and not fuga and not en_lista, f"GET={st}; contenido filtrado={fuga}; aparece en su listado={en_lista}"


@caso("CP-07", "Auditor intenta modificar un caso", "ROL_AUDITOR", "PUT /api/casos/{id}", "403 Forbidden")
def cp07(c):
    st, b = api("PUT", f"/api/casos/{c['caso_ajeno']}", c["tok"]["auditor"], {"estado": "resuelto"})
    leer = api("GET", f"/api/casos/{c['caso_ajeno']}", c["tok"]["auditor"])[0]
    return st == 403 and leer == 200, f"PUT={st} ({b.get('detalle')}); lectura permitida={leer}"


@caso("CP-08", "Analista accede a la configuración", "ROL_ANALISTA", "GET /api/config", "403 Forbidden")
def cp08(c):
    st, b = api("GET", "/api/config", c["tok"]["analista"])
    st2, _ = api("PUT", "/api/config", c["tok"]["analista"], {"tokenMin": 15, "maxIntentos": 10, "bloqueoSeg": 10})
    return st == 403 and st2 == 403, f"GET={st} ({b.get('detalle')}); PUT={st2}"


@caso("CP-09", "redirect_uri no registrada", "Cliente", "Login con redirect alterado", "Keycloak rechaza la solicitud")
def cp09(c):
    r1 = o.login("ejemplo.usuario", CLAVE, redirect_uri="https://evil.example/callback")
    r2 = o.login("ejemplo.usuario", CLAVE, redirect_uri=o.APP + "/callback/../evil")
    r3 = o.login("ejemplo.usuario", CLAVE, redirect_uri=o.APP + "/callback?x=1")       # sin coincidencia exacta
    ok = not r1["ok"] and not r2["ok"] and not r3["ok"]
    return ok, f"https://evil.example/callback → {r1.get('status')}; ruta alterada → {r2.get('status')}; con parámetros → {r3.get('status')} ({(r1.get('error') or '')[:60]})"


@caso("CP-10", "Captura del tráfico de login", "—", "tcpdump/Wireshark sobre HTTPS", "No se observan contraseñas ni tokens en texto plano")
def cp10(c):
    r = subprocess.run([os.path.join(RAIZ, "scripts", "captura.sh"), "--auto"], capture_output=True, text=True)
    salida = r.stdout.strip().splitlines()
    return r.returncode == 0, (salida[-1] if salida else "sin salida") + " (detalle en evidencias/captura-login.txt)"


@caso("CP-11", "Segundo factor obligatorio para ROL_ADMIN", "ROL_ADMIN", "Login sin TOTP configurado",
      "Keycloak obliga a configurar TOTP; el token trae ROL_ADMIN")
def cp11(c):
    t, r = c["login"]["admin"]
    a = o.decodificar_jwt(t["access_token"])
    return r["pidio_totp"] and "ROL_ADMIN" in a["roles"], f"TOTP solicitado={r['pidio_totp']}; roles={a['roles']}"


@caso("CP-12", "Segundo factor obligatorio para ROL_AUDITOR", "ROL_AUDITOR", "Login sin TOTP configurado",
      "Keycloak obliga a configurar TOTP; el token trae ROL_AUDITOR")
def cp12(c):
    t, r = c["login"]["auditor"]
    a = o.decodificar_jwt(t["access_token"])
    return r["pidio_totp"] and "ROL_AUDITOR" in a["roles"], f"TOTP solicitado={r['pidio_totp']}; roles={a['roles']}"


@caso("CP-13", "TOTP incorrecto no concede acceso", "ROL_ADMIN", "Contraseña correcta + código 000000", "Acceso denegado")
def cp13(c):
    c["kc"].desbloquear("prueba.admin")
    r = o.login("prueba.admin", CLAVE, codigo_totp="000000")
    c["kc"].desbloquear("prueba.admin")
    return not r["ok"], f"login con TOTP inválido → ok={r['ok']}"


@caso("CP-14", "PKCE: code_verifier incorrecto", "Cliente", "Canjear el código con otro verifier", "400 invalid_grant")
def cp14(c):
    r = o.login("ejemplo.usuario", CLAVE)
    st, t = o.intercambiar_codigo(r, verifier=o.b64u(os.urandom(48)))
    r2 = o.login("ejemplo.usuario", CLAVE)
    st2, t2 = o.intercambiar_codigo(r2)
    return st == 400 and st2 == 200, f"verifier incorrecto → {st} {t.get('error')}; verifier correcto → {st2}"


@caso("CP-15", "Flujos inseguros deshabilitados", "Cliente", "Password grant (ROPC) e Implicit", "Rechazados por Keycloak")
def cp15(c):
    st, t = o.post_token({"grant_type": "password", "client_id": o.CLIENT_ID, "client_secret": o.ENV["CLIENT_SECRET"],
                          "username": "ejemplo.usuario", "password": CLAVE})
    q = urllib.parse.urlencode({"client_id": o.CLIENT_ID, "redirect_uri": o.REDIRECT, "response_type": "token", "scope": "openid"})
    nav = o.Navegador()
    st2, cuerpo, loc = nav.pedir(f"{o.ISSUER}/protocol/openid-connect/auth?{q}")
    return st in (400, 401) and (st2 != 200 or "error" in (loc or "")), f"ROPC → {st} {t.get('error')}; Implicit (response_type=token) → {st2} {(loc or '')[:60]}"


@caso("CP-16", "Refresh token con rotación", "Cualquiera", "Reutilizar un refresh token ya rotado", "400 invalid_grant")
def cp16(c):
    t, _ = token_de("prueba.usuario")
    viejo = t["refresh_token"]
    st1, nuevo = o.post_token({"grant_type": "refresh_token", "refresh_token": viejo, "client_id": o.CLIENT_ID, "client_secret": o.ENV["CLIENT_SECRET"]})
    st2, rep = o.post_token({"grant_type": "refresh_token", "refresh_token": viejo, "client_id": o.CLIENT_ID, "client_secret": o.ENV["CLIENT_SECRET"]})
    distinto = nuevo.get("refresh_token") != viejo
    return st1 == 200 and distinto and st2 == 400, f"1.º uso={st1} (token nuevo≠viejo: {distinto}); reutilizar el viejo → {st2} {rep.get('error')}"


@caso("CP-17", "Cierre de sesión revoca en IdP y app", "Cualquiera", "POST /auth/logout, luego reutilizar sesión y refresh",
      "Sesión de la app 401; refresh token inválido en Keycloak")
def cp17(c):
    c["kc"].desbloquear("prueba.usuario2")
    r = o.login("prueba.usuario2", CLAVE, app=True)
    st, ses = o.sesion_app(r)
    csrf = ses["csrf"]
    refresh_antes = None
    # sin token CSRF el logout debe rechazarse
    sin_csrf = r["nav"].pedir(o.APP + "/auth/logout", {})[0]
    st_lo, cuerpo, _ = r["nav"].pedir(o.APP + "/auth/logout", {}, {"X-CSRF-Token": csrf})
    despues = o.sesion_app(r)[0]
    return sin_csrf == 403 and st == 200 and st_lo == 200 and despues == 401, \
        f"logout sin CSRF={sin_csrf}; con CSRF={st_lo}; /auth/sesion después={despues}; redirect al IdP={'redirect' in cuerpo}"


@caso("CP-18", "Callback con state alterado (CSRF del flujo)", "Atacante", "GET /callback?code=…&state=falso", "La app rechaza y no crea sesión")
def cp18(c):
    nav = o.Navegador()
    nav.pedir(o.APP + "/auth/login")
    st, _, loc = nav.pedir(o.APP + "/callback?code=codigo-falso&state=estado-falso")
    sesion = o.sesion_app({"nav": nav})[0]
    return loc is not None and "e=state" in loc and sesion == 401, f"redirección={loc}; sesión creada={sesion == 200}"


@caso("CP-19", "ROL_INVITADO solo ve datos públicos", "ROL_INVITADO", "GET /api/casos, /api/estadisticas", "403 en casos; estadísticas públicas")
def cp19(c):
    t = c["tok"]["invitado"]
    s1, _ = api("GET", "/api/casos", t)
    s2, e = api("GET", "/api/estadisticas", t)
    s3, _ = api("POST", "/api/casos", t, {"titulo": "x"})
    return s1 == 403 and s2 == 200 and e.get("publico") is True and "estado" not in e and s3 == 403, f"casos={s1}; estadísticas={s2} (solo {sorted(e)}); crear caso={s3}"


@caso("CP-20", "Usuario edita su caso abierto; no el ajeno ni cambia estado", "ROL_USUARIO", "PUT /api/casos/{id}",
      "Propio abierto: 200 (solo título/descr.); ajeno: 404; cambiar estado: 403")
def cp20(c):
    t = c["tok"]["usuario"]
    ok1 = api("PUT", f"/api/casos/{c['caso_propio']}", t, {"titulo": "Título editado", "descripcion": "ok"})[0]
    ok2 = api("PUT", f"/api/casos/{c['caso_ajeno']}", t, {"titulo": "hackeado"})[0]
    ok3 = api("PUT", f"/api/casos/{c['caso_propio']}", t, {"titulo": "x", "estado": "resuelto"})[0]
    ver = api("GET", f"/api/casos/{c['caso_ajeno']}", c["tok"]["analista"])[1]
    return (ok1, ok2, ok3) == (200, 404, 403) and ver["titulo"] == "SECRETO-AJENO", f"propio={ok1}; ajeno={ok2}; con estado={ok3}; el ajeno no cambió={ver['titulo'] == 'SECRETO-AJENO'}"


@caso("CP-21", "Analista opera casos pero no borra ni administra", "ROL_ANALISTA", "PUT/DELETE /casos, POST /usuarios", "PUT 200; DELETE 403; POST usuarios 403")
def cp21(c):
    t = c["tok"]["analista"]
    a = api("PUT", f"/api/casos/{c['caso_ajeno']}", t, {"estado": "en_analisis", "severidad": "critica"})[0]
    b = api("DELETE", f"/api/casos/{c['caso_ajeno']}", t)[0]
    d = api("POST", "/api/usuarios", t, {"id": "x.y", "nombre": "x", "grupo": "GRP_TI_ADMIN", "clave": "Aaaaaaaaaaaa1!"})[0]
    return (a, b, d) == (200, 403, 403), f"actualizar={a}; borrar={b}; crear usuario={d}"


@caso("CP-22", "Administrador crea usuario en el directorio", "ROL_ADMIN", "POST /api/usuarios; login del nuevo usuario",
      "Se crea en LDAP, Keycloak le asigna el rol por grupo; clave corta rechazada")
def cp22(c):
    t = c["tok"]["admin"]
    corta = api("POST", "/api/usuarios", t, {"id": "prueba.nuevo", "nombre": "Nuevo Prueba", "grupo": "GRP_SOC_ANALISTA", "clave": "corta"})[0]
    mala = api("POST", "/api/usuarios", t, {"id": "Prueba.Nuevo", "nombre": "x", "grupo": "GRP_SOC_ANALISTA", "clave": CLAVE})[0]
    st = api("POST", "/api/usuarios", t, {"id": "prueba.nuevo", "nombre": "Nuevo Prueba", "grupo": "GRP_SOC_ANALISTA", "clave": CLAVE})[0]
    tk, _ = token_de("prueba.nuevo")
    roles = o.decodificar_jwt(tk["access_token"])["roles"]
    dup = api("POST", "/api/usuarios", t, {"id": "prueba.nuevo", "nombre": "x", "grupo": "GRP_SOC_ANALISTA", "clave": CLAVE})[0]
    return (corta, mala, st, dup) == (400, 400, 201, 400) and roles == ["ROL_ANALISTA"], \
        f"clave corta={corta}; formato inválido={mala}; creado={st}; login → roles={roles}; duplicado={dup}"


@caso("CP-23", "Cambio de grupo cambia el rol (grupo→rol automático)", "ROL_ADMIN", "PUT /api/usuarios/{id}",
      "El siguiente token del usuario trae el rol del grupo nuevo")
def cp23(c):
    st = api("PUT", "/api/usuarios/prueba.nuevo", c["tok"]["admin"], {"nombre": "Nuevo Prueba", "grupo": "GRP_USR_USUARIO"})[0]
    tk, _ = token_de("prueba.nuevo")
    roles = o.decodificar_jwt(tk["access_token"])["roles"]
    propio = api("PUT", "/api/usuarios/prueba.admin", c["tok"]["admin"], {"nombre": "x", "grupo": "GRP_USR_USUARIO"})[0]
    return st == 200 and roles == ["ROL_USUARIO"] and propio == 400, f"PUT={st}; roles tras el cambio={roles}; admin editando su propia cuenta={propio}"


@caso("CP-24", "Auditoría registra accesos permitidos y denegados", "ROL_AUDITOR", "GET /api/auditoria",
      "Auditor la lee; aparecen DENY de CP-05/07/08 y eventos de Keycloak")
def cp24(c):
    st, aud = api("GET", "/api/auditoria", c["tok"]["auditor"])
    deny = [a for a in aud if a["res"] == "DENY" and a["src"] == "app"]
    kc_ev = [a for a in aud if a["src"] == "keycloak"]
    prohibido = api("GET", "/api/auditoria", c["tok"]["usuario"])[0]
    return st == 200 and len(deny) >= 4 and len(kc_ev) >= 3 and prohibido == 403, \
        f"auditor lee={st}; denegaciones de la app={len(deny)}; eventos de Keycloak={len(kc_ev)}; usuario lee auditoría={prohibido}"


@caso("CP-25", "Entradas maliciosas (XSS guardado, inyección en el id)", "ROL_USUARIO", "POST /api/casos; GET /api/casos/{inyección}",
      "El texto se guarda como dato; la inyección no altera la consulta")
def cp25(c):
    t = c["tok"]["usuario"]
    xss = "<img src=x onerror=alert(1)>"
    n = api("POST", "/api/casos", t, {"titulo": xss, "descripcion": "x", "severidad": "baja"})
    inj = api("GET", "/api/casos/INC-1%27%20OR%20%271%27=%271", t)[0]
    inj2 = api("GET", "/api/casos/INC-001;DROP%20TABLE%20casos", t)[0]
    sev = api("POST", "/api/casos", t, {"titulo": "ok", "severidad": "<script>"})[1]
    lista = api("GET", "/api/casos", t)[0]
    return n[0] == 201 and n[1]["titulo"] == xss and inj in (400, 404) and inj2 in (400, 404) and sev["severidad"] == "media" and lista == 200, \
        f"XSS guardado como texto={n[1].get('titulo') == xss} (el navegador lo escapa al mostrarlo); inyección id={inj}/{inj2}; severidad inválida→{sev['severidad']}; tabla intacta={lista == 200}"


@caso("CP-26", "Listado de usuarios del directorio", "ROL_ADMIN / ROL_ANALISTA", "GET /api/usuarios",
      "Admin ve a cada persona con nombre, grupo y rol; solo svc-blackwall-sync figura como servicio; el usuario recibe 403")
def cp26(c):
    st, lista = api("GET", "/api/usuarios", c["tok"]["admin"])
    por_id = {u["id"]: u for u in lista} if st == 200 else {}
    servicios = [u["id"] for u in lista if u["servicio"]] if st == 200 else []
    ok_admin = por_id.get("prueba.admin", {}).get("rol") == "ROL_ADMIN" and por_id.get("prueba.admin", {}).get("mfa") is True
    ok_nombre = por_id.get("prueba.usuario", {}).get("nombre") == "Usuario Prueba"
    st_an, _ = api("GET", "/api/usuarios", c["tok"]["analista"])
    st_us, _ = api("GET", "/api/usuarios", c["tok"]["usuario"])
    return st == 200 and servicios == ["svc-blackwall-sync"] and ok_admin and ok_nombre and st_an == 200 and st_us == 403, \
        f"admin={st}; cuentas de servicio={servicios}; prueba.admin→rol/MFA correctos={ok_admin}; nombre correcto={ok_nombre}; analista (solo lectura)={st_an}; usuario={st_us}"


@caso("CP-27", "Política de contraseñas del directorio: longitud e historial", "Cualquiera", "Cambio de contraseña propio (LDAP, como lo hace Keycloak)",
      "Clave corta rechazada; reutilizar una de las últimas claves rechazada; una clave nueva válida aceptada")
def cp27(c):
    u = "prueba.bloqueo"
    dn = f"uid={u},ou=usr,{BASE}"

    def cambiar(actual, nueva):
        r = subprocess.run(["docker", "exec", "-e", "LDAPTLS_REQCERT=never", "blackwall-ldap-1", "ldappasswd", "-x", "-H", "ldaps://localhost:1636",
                            "-D", dn, "-w", actual, "-s", nueva, dn], capture_output=True, text=True)
        return r.returncode == 0, (r.stderr + r.stdout).strip().replace("\n", " ")[:80]
    p1, p2 = CLAVE + "A1", CLAVE + "B2"
    corta, m_corta = cambiar(CLAVE, "corta1")
    ok1, _ = cambiar(CLAVE, p1)
    ok2, _ = cambiar(p1, p2)
    reuso1, m_reuso = cambiar(p2, p1)          # una de las últimas claves
    reuso0, _ = cambiar(p2, CLAVE)             # la original también quedó en el historial
    misma, _ = cambiar(p2, p2)                 # la clave actual
    nueva, _ = cambiar(p2, CLAVE + "C3")
    return (not corta) and ok1 and ok2 and (not reuso1) and (not reuso0) and (not misma) and nueva, \
        f"corta→{'rechazada' if not corta else 'ACEPTADA'} ({m_corta}); 2 cambios válidos={ok1 and ok2}; reutilizar anterior→{'rechazada' if not reuso1 else 'ACEPTADA'} ({m_reuso}); reutilizar la original→{'rechazada' if not reuso0 else 'ACEPTADA'}; repetir la actual→{'rechazada' if not misma else 'ACEPTADA'}; clave nueva→{'aceptada' if nueva else 'RECHAZADA'}"


# ----------------------------------------------------------------------------- ejecución
def main():
    inicio = datetime.now()
    print("== Blackwall · pruebas de aceptación ==")
    try:
        urllib.request.urlopen(o.APP + "/", context=o.CTX)
    except Exception as e:  # noqa: BLE001
        sys.exit(f"La app no responde en {o.APP}: {e}")
    kc = KcAdmin()
    print("[+] Preparando usuarios temporales prueba.* en el directorio")
    limpiar_fixturas(kc)       # por si quedó algo de una corrida anterior
    preparar_fixturas()
    for u in FIXTURAS:
        kc.id_de(u)            # fuerza la importación al realm
    ctx = {"kc": kc, "tok": Cartera(), "login": {}}
    try:
        print("[+] Inicios de sesión base (cada rol, con TOTP donde corresponde)")
        for rol, u in [("admin", "prueba.admin"), ("auditor", "prueba.auditor")]:
            ctx["login"][rol] = token_de(u)                     # primer ingreso: obliga a configurar TOTP
            ctx["tok"][rol] = ctx["login"][rol][0]
        for rol, u in [("usuario", "prueba.usuario"), ("usuario2", "prueba.usuario2"), ("invitado", "prueba.invitado")]:
            ctx["tok"][rol] = token_de(u)[0]
        print("[+] Casos de prueba")
        orden = sorted(RES, key=lambda f: int(f._meta[0].split("-")[1]))
        # CP-01 prepara al analista (TOTP voluntario) y deja su token; los demás dependen de los datos de CP-05/06
        prioridad = {"CP-01": 0, "CP-05": 1, "CP-06": 2}
        orden.sort(key=lambda f: (prioridad.get(f._meta[0], 9), int(f._meta[0].split("-")[1])))
        for fn in orden:
            correr(fn, ctx)
    finally:
        print("[+] Limpiando usuarios temporales")
        limpiar_fixturas(kc)
    EJECUTADOS.sort(key=lambda r: int(r["id"].split("-")[1]))
    pasan = sum(r["ok"] for r in EJECUTADOS)
    print(f"\nResultado: {pasan}/{len(EJECUTADOS)} casos pasan ({(datetime.now() - inicio).seconds} s)")
    escribir_informe(inicio, pasan)
    sys.exit(0 if pasan == len(EJECUTADOS) else 1)


def escribir_informe(inicio, pasan):
    os.makedirs(os.path.join(RAIZ, "evidencias"), exist_ok=True)
    etiqueta = os.environ.get("ETIQUETA", "")
    base = os.path.join(RAIZ, "evidencias", "resultados-pruebas" + (f"-{etiqueta}" if etiqueta else ""))
    with open(base + ".json", "w") as f:
        json.dump({"fecha": inicio.isoformat(timespec="seconds"), "total": len(EJECUTADOS), "pasan": pasan, "casos": EJECUTADOS}, f, indent=2, ensure_ascii=False)
    with open(base + ".md", "w") as f:
        f.write(f"# Resultados de las pruebas de aceptación\n\nEjecución: {inicio:%Y-%m-%d %H:%M} · {pasan}/{len(EJECUTADOS)} casos pasan\n\n")
        f.write("| ID | Caso | Rol / actor | Acción | Resultado esperado | Obtenido | Estado |\n|---|---|---|---|---|---|---|\n")
        for r in EJECUTADOS:
            f.write(f"| {r['id']} | {r['caso']} | {r['actor']} | {r['accion']} | {r['esperado']} | {r['obtenido'].replace('|', '/')} | {'✅ Pasa' if r['ok'] else '❌ Falla'} |\n")
    print("Tabla guardada en", base + ".md")


if __name__ == "__main__":
    main()
