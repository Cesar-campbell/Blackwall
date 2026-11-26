"""Cliente OIDC mínimo para las pruebas: hace el login real contra Keycloak (formulario + TOTP)
con Authorization Code + PKCE, igual que lo haría un navegador. Solo biblioteca estándar.
"""
import base64
import hashlib
import hmac
import html
import http.cookiejar
import json
import os
import re
import secrets
import ssl
import struct
import time
import urllib.error
import urllib.parse
import urllib.request

BW_HOME = os.environ.get("BW_HOME", os.path.expanduser("~/.local/share/blackwall"))
KC = os.environ.get("BW_KC_URL", "https://acceso.localhost:8443")
REALM = "proyecto-accesos"
ISSUER = f"{KC}/realms/{REALM}"
APP = os.environ.get("BW_APP_URL", "https://app.localhost:8444")
CLIENT_ID = "cli-blackwall-dev"
REDIRECT = APP + "/callback"
CTX = ssl.create_default_context() if os.environ.get("BW_PUBLICO") == "1" else ssl.create_default_context(cafile=os.path.join(BW_HOME, "certs", "ca.crt"))


def env():
    d = {}
    for linea in open(os.path.join(BW_HOME, "blackwall.env")):
        if "=" in linea:
            k, v = linea.strip().split("=", 1)
            d[k] = v
    return d


ENV = env()


class SinRedireccion(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def decodificar_jwt(t):
    """Solo para inspeccionar (NO valida la firma: eso lo hace la API)."""
    p = t.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))


def totp(secreto_b32, t=None, paso=30, digitos=6):
    """RFC 6238 (HMAC-SHA1) sobre el secreto en base32."""
    clave = base64.b32decode(secreto_b32.replace(" ", "").upper() + "=" * (-len(secreto_b32.replace(" ", "")) % 8))
    c = int((t or time.time()) // paso)
    h = hmac.new(clave, struct.pack(">Q", c), hashlib.sha1).digest()
    o = h[-1] & 0x0F
    n = (struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF) % (10 ** digitos)
    return str(n).zfill(digitos)


_ultimo_paso = {}


def codigo_fresco(usuario, secreto):
    """Keycloak rechaza reutilizar un código TOTP en la misma ventana de 30 s (anti-replay): se espera la siguiente."""
    paso = int(time.time() // 30)
    if _ultimo_paso.get(usuario) == paso:
        time.sleep(30 - time.time() % 30 + 0.5)
        paso += 1
    _ultimo_paso[usuario] = paso
    return totp(secreto)


def ruta_secreto_totp(usuario):
    return os.path.join(BW_HOME, f"totp-{usuario}.secret")


class Navegador:
    """Un 'navegador' con su propio jar de cookies."""

    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar),
                                              urllib.request.HTTPSHandler(context=CTX), SinRedireccion())

    def pedir(self, url, datos=None, cabeceras=None):
        """Devuelve (status, cuerpo, location)."""
        cuerpo = urllib.parse.urlencode(datos).encode() if datos is not None else None
        req = urllib.request.Request(url, cuerpo, headers=cabeceras or {})
        try:
            r = self.op.open(req)
            return r.status, r.read().decode("utf-8", "replace"), None
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace"), e.headers.get("Location")


def _form(htmltxt):
    m = re.search(r'<form[^>]*action="([^"]+)"', htmltxt)
    return html.unescape(m.group(1)) if m else None


def _mensaje_error(htmltxt):
    m = re.search(r'id="input-error[^"]*"[^>]*>\s*([^<]+)', htmltxt) or re.search(
        r'class="[^"]*alert-error[^"]*"[^>]*>.*?<span[^>]*>\s*([^<]+)', htmltxt, re.S)
    return html.unescape(m.group(1).strip()) if m else None


def login(usuario, clave, *, redirect_uri=REDIRECT, enrolar_si_pide=True, codigo_totp=None,
          scope="openid", solo_hasta_formulario=False, app=False):
    """Hace el flujo completo. Devuelve dict con: ok, code, state, nonce, verifier, error, pidio_totp, ..."""
    nav = Navegador()
    verifier = b64u(secrets.token_bytes(48))
    challenge = b64u(hashlib.sha256(verifier.encode()).digest())
    state, nonce = secrets.token_urlsafe(16), secrets.token_urlsafe(16)
    q = urllib.parse.urlencode({"client_id": CLIENT_ID, "redirect_uri": redirect_uri, "response_type": "code",
                                "scope": scope, "state": state, "nonce": nonce,
                                "code_challenge": challenge, "code_challenge_method": "S256"})
    res = {"ok": False, "verifier": verifier, "state": state, "nonce": nonce, "nav": nav, "pidio_totp": False}
    if app:   # la app genera su propio PKCE/state/nonce y guarda la sesión en su cookie
        st, cuerpo, loc = nav.pedir(APP + "/auth/login")
        res["location_login"] = loc
        st, cuerpo, loc = nav.pedir(loc)
    else:
        st, cuerpo, loc = nav.pedir(f"{ISSUER}/protocol/openid-connect/auth?{q}")
    if st != 200:
        res.update(error=f"auth endpoint -> {st} {_mensaje_error(cuerpo) or cuerpo[:120]}", status=st, location=loc)
        return res
    if solo_hasta_formulario:
        res["ok"] = True
        return res
    accion = _form(cuerpo)
    st, cuerpo, loc = nav.pedir(accion, {"username": usuario, "password": clave, "credentialId": ""})
    # Paso 2 (opcional): TOTP o su enrolamiento
    for _ in range(4):
        if st == 302 and loc and loc.startswith(redirect_uri):
            break
        if st == 302 and loc:  # redirección interna de Keycloak (acción requerida, etc.): se sigue
            st, cuerpo, loc = nav.pedir(urllib.parse.urljoin(KC, loc))
            continue
        if st != 200:
            break
        if 'name="totpSecret"' in cuerpo:  # enrolar TOTP por primera vez
            res["pidio_totp"] = True
            if not enrolar_si_pide:
                res["error"] = "pide enrolar TOTP"
                return res
            # El campo oculto trae el secreto "crudo"; la clave en base32 es la que usa una app autenticadora
            crudo = html.unescape((re.search(r'name="totpSecret"[^>]*value="([^"]+)"', cuerpo)
                                   or re.search(r'value="([^"]+)"[^>]*name="totpSecret"', cuerpo)).group(1))
            secreto = base64.b32encode(crudo.encode()).decode()  # así lo codifica Keycloak para las apps
            with open(ruta_secreto_totp(usuario), "w") as f:
                f.write(secreto)
            os.chmod(ruta_secreto_totp(usuario), 0o600)
            st, cuerpo, loc = nav.pedir(_form(cuerpo), {"totp": codigo_fresco(usuario, secreto), "totpSecret": crudo,
                                                        "userLabel": "pruebas", "saveTOTPBtn": ""})
            continue
        if re.search(r'name="otp"', cuerpo):  # pide el código
            res["pidio_totp"] = True
            cod = codigo_totp
            if cod is None:
                with open(ruta_secreto_totp(usuario)) as f:
                    cod = codigo_fresco(usuario, f.read().strip())
            st, cuerpo, loc = nav.pedir(_form(cuerpo), {"otp": cod, "login": "Sign In"})
            continue
        # Otra pantalla (ej. error de credenciales, cuenta bloqueada, acción requerida)
        res["error"] = _mensaje_error(cuerpo) or "pantalla inesperada"
        res["html"] = cuerpo
        return res
    if st == 302 and loc and loc.startswith(redirect_uri):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query)
        res.update(ok=True, code=qs["code"][0], state_recibido=qs.get("state", [None])[0], callback=loc)
        if app:   # el "navegador" sigue la redirección hacia el callback de la app
            st2, _, loc2 = nav.pedir(loc)
            res.update(callback_status=st2, callback_location=loc2)
            res["ok"] = st2 == 302 and loc2 == "/"
    else:
        res.update(error=_mensaje_error(cuerpo) or f"sin redirección (status {st})", status=st, location=loc, html=cuerpo)
    return res


def intercambiar_codigo(res, redirect_uri=REDIRECT, verifier=None):
    """Cambia el code por tokens (como lo haría el backend de la app)."""
    d = {"grant_type": "authorization_code", "code": res["code"], "redirect_uri": redirect_uri,
         "client_id": CLIENT_ID, "client_secret": ENV["CLIENT_SECRET"], "code_verifier": verifier or res["verifier"]}
    return post_token(d)


def post_token(d):
    req = urllib.request.Request(f"{ISSUER}/protocol/openid-connect/token", urllib.parse.urlencode(d).encode())
    try:
        r = urllib.request.urlopen(req, context=CTX)
        return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def tokens(usuario, clave):
    """Atajo: login + intercambio. Devuelve el JSON del endpoint de tokens."""
    r = login(usuario, clave)
    if not r["ok"]:
        raise RuntimeError(f"login de {usuario} falló: {r.get('error')}")
    st, t = intercambiar_codigo(r)
    if st != 200:
        raise RuntimeError(f"token endpoint {st}: {t}")
    return t


def sesion_app(res):
    """Con la cookie de sesión de la app, pide /auth/sesion (token en memoria para el JS)."""
    st, cuerpo, _ = res["nav"].pedir(APP + "/auth/sesion")
    return st, (json.loads(cuerpo) if cuerpo.startswith("{") else {})


def api(metodo, ruta, token=None, cuerpo=None, cabeceras=None):
    """Llamada a la API de la app con Bearer. Devuelve (status, json)."""
    h = {"Content-Type": "application/json", **(cabeceras or {})}
    if token:
        h["Authorization"] = "Bearer " + token
    req = urllib.request.Request(APP + ruta, json.dumps(cuerpo).encode() if cuerpo is not None else None, method=metodo, headers=h)
    try:
        r = urllib.request.urlopen(req, context=CTX)
        t = r.read()
        return r.status, (json.loads(t) if t else {})
    except urllib.error.HTTPError as e:
        t = e.read()
        try:
            return e.code, json.loads(t)
        except Exception:
            return e.code, {"raw": t[:200].decode("utf-8", "replace")}
