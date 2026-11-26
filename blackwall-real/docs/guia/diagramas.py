"""Diagramas SVG de Blackwall (hechos a mano, sin librerías). Cada uno muestra UN mecanismo con las flechas etiquetadas.
Colores con significado: azul = tráfico normal · ámbar = la contraseña · verde = permitido · rojo = denegado · gris = apoyo."""

AZ, AZ2, SOFT, AM, VE, RO, GR, TX, LN = "#0a4d8c", "#003366", "#e8f0f9", "#b45309", "#16803c", "#c62828", "#5d6878", "#18222e", "#dbe2ea"


def _defs(p):
    return "<defs>" + "".join(
        f'<marker id="{p}{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="{c}"/></marker>'
        for k, c in (("b", AZ), ("a", AM), ("v", VE), ("r", RO), ("g", GR))) + "</defs>"


def _lab(x, y, t, c=TX, s=11.5):
    w = len(t) * s * 0.55 + 14
    return (f'<rect x="{x - w / 2:.1f}" y="{y - 9}" width="{w:.1f}" height="18" rx="9" fill="#fff" stroke="{LN}"/>'
            f'<text x="{x}" y="{y + 4}" text-anchor="middle" font-size="{s}" font-weight="600" fill="{c}">{t}</text>')


def _caja(x, y, w, h, t1, t2="", fondo="#fff", borde=AZ, color=AZ2, s=13.5):
    o = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fondo}" stroke="{borde}" stroke-width="1.8"/>'
    if t2:
        o += f'<text x="{x + w / 2}" y="{y + h / 2 - 3}" text-anchor="middle" font-size="{s}" font-weight="700" fill="{color}">{t1}</text>'
        o += f'<text x="{x + w / 2}" y="{y + h / 2 + 14}" text-anchor="middle" font-size="11" fill="{"#cfe0f2" if fondo in (AZ, AZ2) else GR}">{t2}</text>'
    else:
        o += f'<text x="{x + w / 2}" y="{y + h / 2 + 5}" text-anchor="middle" font-size="{s}" font-weight="700" fill="{color}">{t1}</text>'
    return o


def _cil(x, y, w, h, t1, t2):
    r = 9
    return (f'<path d="M{x} {y + r}v{h - 2 * r}a{w / 2} {r} 0 0 0 {w} 0v-{h - 2 * r}" fill="#fff" stroke="{AZ}" stroke-width="1.8"/>'
            f'<ellipse cx="{x + w / 2}" cy="{y + r}" rx="{w / 2}" ry="{r}" fill="{SOFT}" stroke="{AZ}" stroke-width="1.8"/>'
            f'<text x="{x + w / 2}" y="{y + h / 2 + 4}" text-anchor="middle" font-size="13" font-weight="700" fill="{AZ2}">{t1}</text>'
            f'<text x="{x + w / 2}" y="{y + h / 2 + 19}" text-anchor="middle" font-size="10.5" fill="{GR}">{t2}</text>')


def _flecha(pts, p, c="b", color=AZ, dash=False, w=2):
    d = " ".join(f"{x},{y}" for x, y in pts)
    return f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{w}"{" stroke-dasharray=\"5 4\"" if dash else ""} marker-end="url(#{p}{c})"/>'


def _svg(w, h, cuerpo, etiqueta, p):
    return f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{etiqueta}">{_defs(p)}{cuerpo}</svg>'


# =========================================================================================== 1. Arquitectura
def arquitectura():
    p = "ar"
    o = [f'<rect x="165" y="12" width="587" height="384" rx="14" fill="#f6f9fc" stroke="#9db4cf" stroke-dasharray="6 4"/>',
         f'<text x="180" y="32" font-size="11.5" font-weight="700" fill="{GR}">TU LAPTOP · DOCKER · RED INTERNA CON TLS</text>',
         _caja(8, 165, 122, 72, "Navegador", "cualquier lugar", SOFT),
         _caja(180, 165, 100, 72, "Proxy", "Caddy", "#fff"),
         _caja(355, 52, 150, 84, "Aplicación", "PHP · API /api/*", AZ2, AZ2, "#fff"),
         _caja(355, 262, 150, 84, "Keycloak", "login · tokens · TOTP", AZ, AZ, "#fff"),
         _cil(610, 48, 126, 78, "SQLite", "casos · auditoría"),
         _caja(610, 163, 126, 74, "OpenLDAP", "usuarios · grupos", SOFT),
         _cil(610, 274, 126, 78, "PostgreSQL", "datos de Keycloak")]
    # tráfico normal
    o.append(_flecha([(130, 201), (178, 201)], p))
    o.append(_lab(154, 184, "HTTPS", AZ2, 10.5))
    o.append(_flecha([(280, 186), (318, 186), (318, 94), (353, 94)], p))
    o.append(_lab(318, 140, "/ app", AZ2, 10.5))
    o.append(_flecha([(430, 138), (430, 260)], p))
    o.append(_lab(430, 199, "canjea código · pide claves", AZ2, 11))
    o.append(_flecha([(507, 82), (608, 82)], p))
    o.append(_lab(557, 66, "escribe", AZ2, 10.5))
    o.append(_flecha([(507, 118), (608, 190)], p))
    o.append(_lab(548, 143, "altas y bajas", AZ2, 10.5))
    o.append(_flecha([(507, 330), (608, 330)], p))
    o.append(_lab(557, 314, "guarda", AZ2, 10.5))
    # la contraseña (ámbar): navegador → proxy → Keycloak → directorio
    o.append(_flecha([(280, 216), (318, 216), (318, 304), (353, 304)], p, "a", AM, False, 3))
    o.append(_lab(318, 262, "/acceso", AM, 10.5))
    o.append(_flecha([(507, 292), (608, 222)], p, "a", AM, False, 3))
    o.append(_lab(552, 249, "¿contraseña correcta?", AM, 10.5))
    # leyenda
    o.append(f'<line x1="186" y1="364" x2="214" y2="364" stroke="{AM}" stroke-width="3"/><text x="222" y="368" font-size="11" fill="{TX}"><tspan font-weight="700" fill="{AM}">Ruta de la contraseña:</tspan> la aplicación nunca la ve</text>')
    o.append(f'<line x1="186" y1="382" x2="214" y2="382" stroke="{AZ}" stroke-width="2"/><text x="222" y="386" font-size="11" fill="{TX}">Resto del tráfico (todo cifrado)</text>')
    return _svg(760, 408, "".join(o), "Arquitectura: la contraseña solo viaja del navegador a Keycloak y al directorio; la aplicación no la ve", p)


# =========================================================================================== 2. Secuencia del login
def secuencia():
    p = "se"
    X = {"nav": 92, "app": 300, "kc": 500, "ldap": 690}
    nom = {"nav": ("Navegador", "tú"), "app": ("Aplicación", "Blackwall"), "kc": ("Keycloak", "identidad"), "ldap": ("Directorio", "OpenLDAP")}
    fases = [("1 · PEDIR ACCESO", 58, 150, "#f3f7fc"), ("2 · CREDENCIALES Y SEGUNDO FACTOR", 150, 336, "#fff8ed"),
             ("3 · CÓDIGO DE UN SOLO USO", 336, 416, "#f3f7fc"), ("4 · TOKENS Y SESIÓN", 416, 572, "#effaf2")]
    o = []
    for t, y0, y1, c in fases:
        o.append(f'<rect x="0" y="{y0}" width="760" height="{y1 - y0}" fill="{c}"/>')
        o.append(f'<text x="8" y="{y0 + 14}" font-size="10.5" font-weight="700" fill="{GR}" letter-spacing=".05em">{t}</text>')
    for k, x in X.items():
        a, b = nom[k]
        o.append(f'<line x1="{x}" y1="48" x2="{x}" y2="572" stroke="#9db4cf" stroke-dasharray="4 4"/>')
        o.append(f'<rect x="{x - 62}" y="4" width="124" height="44" rx="9" fill="{AZ2}"/>'
                 f'<text x="{x}" y="24" text-anchor="middle" font-size="13.5" font-weight="700" fill="#fff">{a}</text>'
                 f'<text x="{x}" y="40" text-anchor="middle" font-size="10.5" fill="#cfe0f2">{b}</text>')
    msgs = [(1, "nav", "app", "Abre la app", AZ, False, "#f3f7fc"), (2, "app", "nav", "Redirige (PKCE · state)", AZ, False, "#f3f7fc"),
            (3, "nav", "kc", "Usuario y contraseña", AM, False, "#fff8ed"), (4, "kc", "ldap", "¿Contraseña correcta?", AM, False, "#fff8ed"),
            (5, "ldap", "kc", "Sí", AM, True, "#fff8ed"), (6, "kc", "nav", "Pide el código TOTP", AZ, False, "#fff8ed"),
            (7, "nav", "kc", "Código de 6 dígitos", AZ, False, "#fff8ed"), (8, "kc", "nav", "Código de un solo uso", AZ, False, "#f3f7fc"),
            (9, "nav", "app", "Entrega ese código", AZ, False, "#f3f7fc"), (10, "app", "kc", "Canjea código + verifier", AZ, False, "#effaf2"),
            (11, "kc", "app", "ID · acceso · refresh", AZ, True, "#effaf2"), (12, "app", "app", "Verifica firma, iss, aud, exp, nonce", VE, False, "#effaf2"),
            (13, "app", "nav", "Cookie de sesión", VE, False, "#effaf2")]
    ys = {1: 96, 2: 130, 3: 186, 4: 218, 5: 250, 6: 282, 7: 314, 8: 372, 9: 402, 10: 450, 11: 484, 12: 518, 13: 552}
    for n, d, h, t, c, dash, fondo in msgs:
        y = ys[n]
        xa, xb = X[d], X[h]
        marca = {AZ: "b", AM: "a", VE: "v"}[c]
        if d == h:
            o.append(f'<rect x="{xa + 10}" y="{y - 14}" width="236" height="28" rx="8" fill="#fff" stroke="{VE}" stroke-width="1.6"/>'
                     f'<text x="{xa + 22}" y="{y + 5}" font-size="11.5" font-weight="600" fill="{VE}">{t}</text>')
            cx = xa - 14
        else:
            o.append(_flecha([(xa, y), (xb + (-9 if xb > xa else 9), y)], p, marca, c, dash, 2.2))
            desp = 12 if xb > xa else -12
            o.append(f'<text x="{(xa + xb) / 2 + desp}" y="{y - 8}" text-anchor="middle" font-size="11.5" font-weight="600" fill="{TX}" '
                     f'stroke="{fondo}" stroke-width="4" paint-order="stroke">{t}</text>')
            cx = xa + (14 if xb > xa else -14)
        o.append(f'<circle cx="{cx}" cy="{y}" r="9" fill="{c}"/><text x="{cx}" y="{y + 4}" text-anchor="middle" font-size="10.5" font-weight="700" fill="#fff">{n}</text>')
    o.append(f'<text x="752" y="168" text-anchor="end" font-size="11.5" font-weight="700" fill="{AM}">La aplicación nunca ve la contraseña</text>')
    return _svg(760, 582, "".join(o), "Inicio de sesión en cuatro fases: la contraseña solo pasa por Keycloak y el directorio; la app recibe un código y lo canjea por tokens", p)


# =========================================================================================== 3. Decisión de acceso
def decision():
    p = "de"
    o = []
    o.append(_caja(150, 6, 260, 40, "Petición a /api/… con Bearer", "", SOFT, AZ, AZ2, 13))
    pasos = [("¿Token válido?", "firma RS256 · iss · aud · exp · tipo", "401", "No autenticado", 76),
             ("¿La sesión sigue activa?", "inactividad · ciclos · cerrada", "401", "Sesión cerrada", 168),
             ("¿Tiene el permiso (scope)?", "casos:leer · config:admin · …", "403", "Prohibido", 260),
             ("¿Es de su propiedad?", "solo permisos _propios (sub del token)", "404", "No se revela", 352)]
    o.append(_flecha([(280, 46), (280, 74)], p))
    for i, (q, sub, cod, res, y) in enumerate(pasos):
        o.append(_caja(150, y, 260, 56, q, sub, "#fff", AZ, AZ2, 13.5))
        o.append(_flecha([(410, y + 28), (470, y + 28)], p, "r", RO))
        o.append(_lab(440, y + 14, "no", RO, 11))
        o.append(f'<rect x="472" y="{y + 8}" width="168" height="40" rx="20" fill="#fdecec" stroke="{RO}" stroke-width="1.6"/>'
                 f'<text x="492" y="{y + 33}" font-size="16" font-weight="800" fill="{RO}">{cod}</text>'
                 f'<text x="528" y="{y + 32}" font-size="11.5" font-weight="600" fill="{RO}">{res}</text>')
        o.append(_flecha([(280, y + 56), (280, y + 92 - 2 if i < 3 else y + 92 - 2)], p, "v", VE))
        o.append(_lab(300, y + 74, "sí", VE, 11))
    o.append(f'<rect x="150" y="446" width="260" height="44" rx="22" fill="#e6f6ec" stroke="{VE}" stroke-width="1.8"/>'
             f'<text x="280" y="473" text-anchor="middle" font-size="14" font-weight="800" fill="{VE}">200 · se atiende la petición</text>')
    o.append(f'<text x="470" y="470" font-size="11" fill="{GR}">Lo que no está declarado</text><text x="470" y="485" font-size="11" fill="{GR}">responde 404 (denegar por defecto)</text>')
    return _svg(660, 500, "".join(o), "La API decide cada petición en cuatro comprobaciones seguidas: token, sesión, permiso y propiedad", p)


# =========================================================================================== 4. Cadena de autorización
def cadena():
    p = "ca"
    o = []
    cols = [(10, "OpenLDAP", "directorio", SOFT, AZ, AZ2, ["usuario", "cruz.irvin", "miembro de", "GRP_SOC_ANALISTA"]),
            (212, "Keycloak", "identidad", AZ, AZ, "#fff", ["GRP_SOC_ANALISTA", "→ ROL_ANALISTA", "→ scopes del rol", "(5 permisos)"]),
            (414, "Token", "access token · 5 min", SOFT, AZ, AZ2, ["roles: ROL_ANALISTA", "scope: casos:leer", "casos:escribir …", "sub: identificador"]),
            (616, "API", "servidor", AZ2, AZ2, "#fff", ["GET /api/config", "exige: config:admin", "el token no lo tiene", "→ 403"])]
    for x, t1, t2, fondo, borde, color, lineas in cols:
        o.append(_caja(x, 40, 154, 64, t1, t2, fondo, borde, color, 15))
        o.append(f'<rect x="{x}" y="136" width="154" height="102" rx="10" fill="#fff" stroke="{LN}"/>')
        for i, l in enumerate(lineas):
            fw = "700" if i in (1, 3) else "400"
            col = RO if (t1 == "API" and i == 3) else (AZ2 if i in (1, 3) else GR)
            o.append(f'<text x="{x + 77}" y="{160 + i * 22}" text-anchor="middle" font-size="11.5" font-weight="{fw}" fill="{col}">{l}</text>')
        o.append(f'<line x1="{x + 77}" y1="104" x2="{x + 77}" y2="134" stroke="#9db4cf" stroke-dasharray="3 3"/>')
    for x, etq in ((164, "grupo → rol"), (366, "emite el token"), (568, "envía Bearer")):
        o.append(_flecha([(x, 72), (x + 46, 72)], p))
        o.append(_lab(x + 23, 54, etq, AZ2, 10))
    o.append(f'<text x="385" y="14" text-anchor="middle" font-size="11" font-weight="700" fill="{GR}" letter-spacing=".05em">EJEMPLO: UN ANALISTA</text>')
    o.append(f'<text x="390" y="266" text-anchor="middle" font-size="12" fill="{TX}">Cambiar a una persona de grupo en el directorio cambia su rol <tspan font-weight="700" fill="{AZ2}">en su siguiente token</tspan>; no hay nada que reconfigurar en la aplicación.</text>')
    return _svg(780, 280, "".join(o), "Cómo un grupo del directorio se convierte en permisos que la API comprueba", p)


# =========================================================================================== 5. Sesión por ciclos
def ciclos():
    p = "ci"
    x0, k = 90, 21.0  # 21 px por minuto → 30 min = 630 px
    o = []
    for m in range(0, 31, 5):
        x = x0 + m * k
        o.append(f'<line x1="{x}" y1="52" x2="{x}" y2="262" stroke="{LN}"/><text x="{x}" y="274" text-anchor="middle" font-size="11" fill="{GR}">{m} min</text>')
    # carril A: con actividad
    o.append(f'<text x="8" y="56" font-size="12" font-weight="800" fill="{AZ2}">A · CON ACTIVIDAD</text><text x="8" y="71" font-size="10.5" fill="{GR}">ciclos de 5 min, máximo 6 (administrador)</text>')
    for i in range(6):
        xa = x0 + i * 5 * k
        o.append(f'<rect x="{xa + 1}" y="84" width="{5 * k - 2}" height="34" rx="6" fill="{AZ if i % 2 == 0 else AZ2}"/>'
                 f'<text x="{xa + 5 * k / 2}" y="106" text-anchor="middle" font-size="12" font-weight="700" fill="#fff">ciclo {i + 1}</text>')
        if i:
            o.append(f'<circle cx="{xa}" cy="84" r="5" fill="{VE}"/>')
    o.append(f'<circle cx="{x0 + 4}" cy="132" r="4.5" fill="{VE}"/><text x="{x0 + 14}" y="136" font-size="11" fill="{VE}" font-weight="700">cada punto: se renueva el acceso</text>')
    o.append(f'<rect x="{x0 + 30 * k + 2}" y="84" width="28" height="34" rx="6" fill="#fdecec" stroke="{RO}"/>')
    o.append(f'<text x="{x0 + 30 * k + 30}" y="136" text-anchor="end" font-size="11.5" font-weight="700" fill="{RO}">Ciclos agotados: hay que iniciar sesión de nuevo (con MFA)</text>')
    # carril B: inactividad
    yb = 178
    o.append(f'<text x="8" y="{yb - 12}" font-size="12" font-weight="800" fill="{AZ2}">B · SIN ACTIVIDAD</text><text x="8" y="{yb + 3}" font-size="10.5" fill="{GR}">límite 5 min, aviso 30 s antes</text>')
    o.append(f'<rect x="{x0 + 1}" y="{yb + 12}" width="{8 * k}" height="30" rx="6" fill="{AZ}"/><text x="{x0 + 4 * k}" y="{yb + 32}" text-anchor="middle" font-size="12" font-weight="700" fill="#fff">trabajando</text>')
    for m in (1, 3, 5, 7):
        o.append(f'<circle cx="{x0 + m * k}" cy="{yb + 12}" r="4.5" fill="{VE}"/>')
    o.append(f'<text x="{x0 + 8 * k + 6}" y="{yb + 8}" font-size="10.5" fill="{GR}">última actividad (minuto 8)</text>')
    o.append(f'<rect x="{x0 + 8 * k}" y="{yb + 12}" width="{4.5 * k}" height="30" fill="#fff8ed" stroke="{AM}" stroke-dasharray="4 3"/><text x="{x0 + 10.25 * k}" y="{yb + 32}" text-anchor="middle" font-size="11.5" font-weight="700" fill="{AM}">sin actividad</text>')
    o.append(f'<rect x="{x0 + 12.5 * k}" y="{yb + 12}" width="{0.5 * k}" height="30" fill="{AM}"/>')
    o.append(f'<line x1="{x0 + 12.5 * k}" y1="{yb + 42}" x2="{x0 + 12.5 * k}" y2="{yb + 62}" stroke="{AM}" stroke-width="1.6"/>')
    o.append(f'<text x="{x0 + 12.5 * k - 6}" y="{yb + 76}" text-anchor="end" font-size="11.5" font-weight="700" fill="{AM}">minuto 12,5 · aparece “¿Sigues ahí?”</text>')
    o.append(f'<rect x="{x0 + 13 * k}" y="{yb + 12}" width="{17 * k}" height="30" fill="#fdecec"/><text x="{x0 + 21.5 * k}" y="{yb + 32}" text-anchor="middle" font-size="11.5" font-weight="700" fill="{RO}">sesión cerrada: el token anterior ya no sirve</text>')
    o.append(f'<line x1="{x0 + 13 * k}" y1="{yb + 12}" x2="{x0 + 13 * k}" y2="{yb + 62}" stroke="{RO}" stroke-width="1.8"/>')
    o.append(f'<text x="{x0 + 13 * k + 6}" y="{yb + 76}" font-size="11.5" font-weight="700" fill="{RO}">minuto 13 · cierre inmediato</text>')
    o.append(f'<text x="380" y="306" text-anchor="middle" font-size="11.5" fill="{TX}">El servidor decide: guarda la última actividad real de cada sesión; si el aviso se ignora, la cierra y lo registra en la auditoría.</text>')
    return _svg(760, 318, "".join(o), "Dos casos de sesión: con actividad se renueva por ciclos hasta agotarlos; sin actividad se avisa y se cierra al pasar el límite", p)


ARQ = arquitectura()
