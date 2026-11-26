#!/usr/bin/env python3
"""Configura Keycloak de forma reproducible (realm, roles, scopes, clientes, federación LDAP,
mapeo grupo→rol, MFA por rol). Es idempotente: se puede ejecutar varias veces.

Lee los secretos de $BW_HOME/blackwall.env (nunca van en el repositorio).
"""
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BW_HOME = os.environ.get("BW_HOME", os.path.expanduser("~/.local/share/blackwall"))
KC = os.environ.get("BW_KC_URL", "https://acceso.localhost:8443")   # dirección con la que este script habla con Keycloak
REALM = "proyecto-accesos"
APP = os.environ.get("BW_APP_URL", "https://app.localhost:8444")   # dirección pública de la aplicación


def cargar_env():
    env = {}
    with open(os.path.join(BW_HOME, "blackwall.env")) as f:
        for linea in f:
            if "=" in linea and not linea.startswith("#"):
                k, v = linea.strip().split("=", 1)
                env[k] = v
    return env


ENV = cargar_env()
CTX = ssl.create_default_context(cafile=os.path.join(BW_HOME, "certs", "ca.crt"))

# ----------------------------------------------------------------------------- matriz de roles → scopes
# Una sola fuente de verdad: guía 8.1 / 8.2 (scope = <recurso>:<acción>, sufijo _propios = control por propiedad)
ROLES = {
    "ROL_ADMIN": ["usuarios:admin", "config:admin", "casos:leer", "casos:escribir", "casos:borrar",
                  "comentarios:escribir", "comentarios:borrar", "auditoria:leer", "estadisticas:leer"],
    "ROL_ANALISTA": ["casos:leer", "casos:escribir", "comentarios:escribir", "estadisticas:leer", "usuarios:leer"],
    "ROL_AUDITOR": ["casos:leer", "auditoria:leer", "estadisticas:leer", "usuarios:leer"],
    "ROL_USUARIO": ["casos:crear", "casos:leer_propios", "casos:escribir_propios",
                    "comentarios:escribir_propios", "estadisticas:leer_propios"],
    "ROL_INVITADO": ["estadisticas:publicas"],
}
# Grupo del directorio → rol de la aplicación (guía, sección 8.2)
GRUPO_A_ROL = {
    "GRP_TI_ADMIN": "ROL_ADMIN",
    "GRP_SOC_ANALISTA": "ROL_ANALISTA",
    "GRP_CUM_AUDITOR": "ROL_AUDITOR",
    "GRP_USR_USUARIO": "ROL_USUARIO",
    "GRP_PUB_INVITADO": "ROL_INVITADO",
}
MFA_OBLIGATORIO = ["ROL_ADMIN", "ROL_AUDITOR"]  # guía 7.2


# ----------------------------------------------------------------------------- cliente HTTP mínimo
class Admin:
    def __init__(self):
        self.tok = None
        self.exp = 0

    def token(self):
        if self.tok and time.time() < self.exp - 20:
            return self.tok
        d = urllib.parse.urlencode({"grant_type": "password", "client_id": "admin-cli",
                                    "username": ENV["KC_ADMIN_USER"], "password": ENV["KC_ADMIN_PASSWORD"]}).encode()
        r = urllib.request.urlopen(urllib.request.Request(f"{KC}/realms/master/protocol/openid-connect/token", d), context=CTX)
        j = json.load(r)
        self.tok, self.exp = j["access_token"], time.time() + j["expires_in"]
        return self.tok

    def call(self, metodo, ruta, cuerpo=None, ok=(200, 201, 204), realm=True):
        url = f"{KC}/admin/realms{'/' + REALM if realm else ''}{ruta}"
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        req = urllib.request.Request(url, datos, method=metodo, headers={
            "Authorization": "Bearer " + self.token(), "Content-Type": "application/json"})
        try:
            r = urllib.request.urlopen(req, context=CTX)
            cuerpo_r = r.read()
            return r.status, (json.loads(cuerpo_r) if cuerpo_r else None), r.headers
        except urllib.error.HTTPError as e:
            texto = e.read().decode()
            if e.code in ok:
                return e.code, None, e.headers
            raise SystemExit(f"[!] {metodo} {ruta} -> {e.code}: {texto[:400]}")

    def get(self, ruta, **kw):
        return self.call("GET", ruta, **kw)[1]


A = Admin()


def paso(t):
    print(f"[+] {t}")


def esperar_keycloak():
    for _ in range(90):
        try:
            urllib.request.urlopen(f"{KC}/realms/master", context=CTX)
            return
        except Exception:
            time.sleep(3)
    sys.exit("Keycloak no responde en " + KC)


# ----------------------------------------------------------------------------- 1. realm
def realm():
    paso(f"Realm {REALM}")
    cfg = {
        "realm": REALM, "enabled": True, "displayName": "Blackwall · UTP", "sslRequired": "all",
        "registrationAllowed": False, "resetPasswordAllowed": False, "rememberMe": False,
        "loginWithEmailAllowed": False, "duplicateEmailsAllowed": False, "editUsernameAllowed": False,
        # Vida corta del access token (guía 7.2: 5–15 min) y refresh token con rotación
        "accessTokenLifespan": 300, "accessCodeLifespan": 60, "ssoSessionIdleTimeout": 1800,
        "ssoSessionMaxLifespan": 36000, "revokeRefreshToken": True, "refreshTokenMaxReuse": 0,
        # Bloqueo temporal tras 5 intentos fallidos
        "bruteForceProtected": True, "failureFactor": 5, "waitIncrementSeconds": 60, "maxFailureWaitSeconds": 900,
        "minimumQuickLoginWaitSeconds": 60, "quickLoginCheckMilliSeconds": 1000, "maxDeltaTimeSeconds": 43200,
        "permanentLockout": False,
        # Política de contraseñas (NIST 800-63B): 12+ caracteres y no reutilizar las últimas 5
        "passwordPolicy": "length(12) and passwordHistory(5)",
        "otpPolicyType": "totp", "otpPolicyAlgorithm": "HmacSHA1", "otpPolicyDigits": 6, "otpPolicyPeriod": 30,
        "loginTheme": "blackwall", "internationalizationEnabled": True, "supportedLocales": ["es"], "defaultLocale": "es",
        # Eventos = registro de auditoría del lado del IdP
        "eventsEnabled": True, "eventsListeners": ["jboss-logging"], "adminEventsEnabled": True,
        "adminEventsDetailsEnabled": True,
        "enabledEventTypes": ["LOGIN", "LOGIN_ERROR", "LOGOUT", "LOGOUT_ERROR", "CODE_TO_TOKEN", "CODE_TO_TOKEN_ERROR",
                              "REFRESH_TOKEN", "REFRESH_TOKEN_ERROR", "UPDATE_PASSWORD", "UPDATE_PASSWORD_ERROR",
                              "UPDATE_TOTP", "REMOVE_TOTP", "RESTART_AUTHENTICATION", "INVALID_SIGNATURE",
                              "USER_DISABLED_BY_TEMPORARY_LOCKOUT", "USER_DISABLED_BY_PERMANENT_LOCKOUT",
                              "CLIENT_LOGIN_ERROR", "INTROSPECT_TOKEN_ERROR", "TOKEN_EXCHANGE_ERROR"],
    }
    existe = A.call("GET", "", ok=(404,))[1]
    if existe is None:
        A.call("POST", "", cfg, realm=False)
    else:
        A.call("PUT", "", cfg)
    return A.get("")["id"]


# ----------------------------------------------------------------------------- 2. roles
def roles():
    paso("Roles de aplicación (ROL_*)")
    # Versión anterior usaba un rol compuesto MFA_OBLIGATORIO: filtraba scopes de ROL_ADMIN hacia ROL_AUDITOR (hallazgo CP-07)
    A.call("DELETE", "/roles/MFA_OBLIGATORIO", ok=(204, 404))
    for r in ROLES:
        A.call("POST", "/roles", {"name": r, "description": "Rol de aplicación Blackwall"}, ok=(201, 409))
    return {r["name"]: r for r in A.get("/roles?max=200") if r["name"] in ROLES}


# ----------------------------------------------------------------------------- 3. scopes
def scopes(roles_kc):
    paso("Client scopes <recurso>:<acción> con restricción por rol")
    todos = sorted({s for lst in ROLES.values() for s in lst})
    existentes = {s["name"]: s for s in A.get("/client-scopes")}
    ids = {}
    for s in todos:
        if s not in existentes:
            A.call("POST", "/client-scopes", {
                "name": s, "protocol": "openid-connect", "description": "Permiso Blackwall",
                "attributes": {"include.in.token.scope": "true", "display.on.consent.screen": "false"}})
            existentes = {x["name"]: x for x in A.get("/client-scopes")}
        ids[s] = existentes[s]["id"]
        # El scope solo se concede a quien tenga alguno de estos roles
        roles_del_scope = [roles_kc[r] for r, lst in ROLES.items() if s in lst]
        A.call("POST", f"/client-scopes/{ids[s]}/scope-mappings/realm", roles_del_scope, ok=(204, 200, 409))
    return ids


# ----------------------------------------------------------------------------- 4. clientes
def cliente(rep):
    ex = A.get(f"/clients?clientId={rep['clientId']}")
    if ex:
        A.call("PUT", f"/clients/{ex[0]['id']}", {**rep, "id": ex[0]["id"]})
        return ex[0]["id"]
    A.call("POST", "/clients", rep)
    return A.get(f"/clients?clientId={rep['clientId']}")[0]["id"]


def clientes(scope_ids):
    paso("Cliente cli-blackwall-dev (Authorization Code + PKCE S256, sin Implicit ni ROPC)")
    mappers = [
        {"name": "roles", "protocol": "openid-connect", "protocolMapper": "oidc-usermodel-realm-role-mapper",
         "config": {"claim.name": "roles", "multivalued": "true", "jsonType.label": "String",
                    "access.token.claim": "true", "id.token.claim": "true", "userinfo.token.claim": "false"}},
        {"name": "groups", "protocol": "openid-connect", "protocolMapper": "oidc-group-membership-mapper",
         "config": {"claim.name": "groups", "full.path": "false", "access.token.claim": "true",
                    "id.token.claim": "true", "userinfo.token.claim": "false"}},
        {"name": "audiencia-api", "protocol": "openid-connect", "protocolMapper": "oidc-audience-mapper",
         "config": {"included.client.audience": "cli-blackwall-dev", "access.token.claim": "true",
                    "id.token.claim": "false", "introspection.token.claim": "true"}},
    ]
    cid = cliente({
        "clientId": "cli-blackwall-dev", "name": "Blackwall (dev)", "protocol": "openid-connect", "enabled": True,
        "publicClient": False, "clientAuthenticatorType": "client-secret", "secret": ENV["CLIENT_SECRET"],
        "standardFlowEnabled": True, "implicitFlowEnabled": False, "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": False, "rootUrl": APP, "baseUrl": APP + "/",
        "redirectUris": [APP + "/callback"], "webOrigins": [],  # coincidencia exacta, sin comodines
        "fullScopeAllowed": False,
        "attributes": {"pkce.code.challenge.method": "S256", "post.logout.redirect.uris": APP + "/",
                       "access.token.lifespan": "",   # vacío = quitar el valor propio y usar el del realm (editable desde la app)
                       "use.refresh.tokens": "true",
                       "frontchannel.logout": "false"},
        "protocolMappers": [],
    })
    existentes = {m["name"] for m in A.get(f"/clients/{cid}/protocol-mappers/models")}
    for m in mappers:
        if m["name"] not in existentes:
            A.call("POST", f"/clients/{cid}/protocol-mappers/models", m)
    # Scopes por defecto: lo mínimo del estándar + los <recurso>:<acción>
    actuales = {s["name"]: s["id"] for s in A.get(f"/clients/{cid}/default-client-scopes")}
    todos = {s["name"]: s["id"] for s in A.get("/client-scopes")}
    for innecesario in ("roles", "web-origins"):
        if innecesario in actuales:
            A.call("DELETE", f"/clients/{cid}/default-client-scopes/{actuales[innecesario]}")
    for nombre, sid in {**{n: todos[n] for n in ("profile", "basic", "acr") if n in todos}, **scope_ids}.items():
        if nombre not in actuales:
            A.call("PUT", f"/clients/{cid}/default-client-scopes/{sid}")

    paso("Cliente de servicio cli-blackwall-sync-dev (client credentials, solo lo necesario)")
    sid = cliente({
        "clientId": "cli-blackwall-sync-dev", "name": "Blackwall (servicio de sincronización)", "protocol": "openid-connect",
        "enabled": True, "publicClient": False, "clientAuthenticatorType": "client-secret",
        "secret": ENV["SYNC_CLIENT_SECRET"], "serviceAccountsEnabled": True, "standardFlowEnabled": False,
        "implicitFlowEnabled": False, "directAccessGrantsEnabled": False, "fullScopeAllowed": False, "redirectUris": [],
    })
    cuenta = A.get(f"/clients/{sid}/service-account-user")
    rm = A.get("/clients?clientId=realm-management")[0]["id"]
    necesarios = {"view-events", "view-users", "query-users", "manage-users", "view-realm", "manage-realm"}
    reps = [r for r in A.get(f"/clients/{rm}/roles") if r["name"] in necesarios]
    A.call("POST", f"/users/{cuenta['id']}/role-mappings/clients/{rm}", reps, ok=(204, 200, 409))
    # Con fullScopeAllowed=false el token solo lleva estos roles; y la API de administración exige el scope kc-admin-api
    A.call("POST", f"/clients/{sid}/scope-mappings/clients/{rm}", reps, ok=(204, 200, 409))
    actuales_sync = {x["name"] for x in A.get(f"/clients/{sid}/default-client-scopes")}
    for sc in A.get("/client-scopes"):
        if sc["name"] == "kc-admin-api" and sc["name"] not in actuales_sync:
            A.call("PUT", f"/clients/{sid}/default-client-scopes/{sc['id']}")


# ----------------------------------------------------------------------------- 5. federación LDAP
def ldap(realm_id):
    paso("Federación con el directorio (OpenLDAP por LDAPS)")
    base = ENV["LDAP_BASE"]
    comp = A.get(f"/components?type=org.keycloak.storage.UserStorageProvider&name=directorio-blackwall")
    cfg = {
        "enabled": ["true"], "priority": ["0"], "editMode": ["WRITABLE"], "syncRegistrations": ["false"],
        "vendor": ["other"], "usernameLDAPAttribute": ["uid"], "rdnLDAPAttribute": ["uid"],
        "uuidLDAPAttribute": ["entryUUID"], "userObjectClasses": ["inetOrgPerson"],
        "connectionUrl": ["ldaps://ldap:1636"], "usersDn": [base], "authType": ["simple"],
        "bindDn": [f"uid=svc-blackwall-sync,ou=servicio,{base}"], "bindCredential": [ENV["SVC_LDAP_PASSWORD"]],
        "searchScope": ["2"], "validatePasswordPolicy": ["true"], "trustEmail": ["false"],
        "useTruststoreSpi": ["ldapsOnly"], "connectionPooling": ["true"], "pagination": ["true"],
        "allowKerberosAuthentication": ["false"], "batchSizeForSync": ["1000"], "fullSyncPeriod": ["-1"],
        "changedSyncPeriod": ["-1"], "cachePolicy": ["NO_CACHE"], "usePasswordModifyExtendedOp": ["true"],
        "importEnabled": ["true"],
    }
    rep = {"name": "directorio-blackwall", "providerId": "ldap", "providerType": "org.keycloak.storage.UserStorageProvider",
           "parentId": realm_id, "config": cfg}
    if comp:
        lid = comp[0]["id"]
        A.call("PUT", f"/components/{lid}", {**rep, "id": lid})
    else:
        st, _, h = A.call("POST", "/components", rep)
        lid = h["Location"].rstrip("/").split("/")[-1]

    tipo = "org.keycloak.storage.ldap.mappers.LDAPStorageMapper"
    mapas = {m["name"]: m for m in A.get(f"/components?parent={lid}&type={tipo}")}

    def mapper(nombre, proveedor, config):
        rep = {"name": nombre, "providerId": proveedor, "providerType": tipo, "parentId": lid, "config": config}
        if nombre in mapas:
            A.call("PUT", f"/components/{mapas[nombre]['id']}", {**rep, "id": mapas[nombre]["id"]})
            return mapas[nombre]["id"]
        _, _, h = A.call("POST", "/components", rep)
        return h["Location"].rstrip("/").split("/")[-1]

    def attr(n, ldap_attr, modelo, mandatorio="false"):
        mapper(n, "user-attribute-ldap-mapper", {
            "ldap.attribute": [ldap_attr], "user.model.attribute": [modelo], "read.only": ["false"],
            "always.read.value.from.ldap": ["true"], "is.mandatory.in.ldap": [mandatorio]})

    # Se reutilizan los nombres de los mapeadores que Keycloak crea por defecto (si no, quedarían duplicados)
    for repetido in ("nombre", "apellido", "correo"):
        if repetido in mapas:
            A.call("DELETE", f"/components/{mapas[repetido]['id']}")
    attr("username", "uid", "username", "true")
    attr("first name", "givenName", "firstName")
    attr("last name", "sn", "lastName", "true")
    attr("email", "mail", "email")

    # Mapeo grupo del directorio → Keycloak. Lectura en vivo desde LDAP (READ_ONLY): si el administrador
    # cambia a alguien de grupo, el siguiente token ya trae el rol nuevo.
    gid = mapper("grupos", "group-ldap-mapper", {
        "groups.dn": [base], "group.name.ldap.attribute": ["cn"], "group.object.classes": ["groupOfNames"],
        "preserve.group.inheritance": ["false"], "ignore.missing.groups": ["true"],
        "membership.ldap.attribute": ["member"], "membership.attribute.type": ["DN"],
        "membership.user.ldap.attribute": ["uid"], "groups.ldap.filter": ["(cn=GRP_*)"], "mode": ["READ_ONLY"],
        "user.roles.retrieve.strategy": ["LOAD_GROUPS_BY_MEMBER_ATTRIBUTE"], "mapped.group.attributes": [""],
        "drop.non.existing.groups.during.sync": ["false"], "groups.path": ["/"]})

    paso("Sincronizando grupos y usuarios desde el directorio")
    A.call("POST", f"/user-storage/{lid}/mappers/{gid}/sync?direction=fedToKeycloak")
    st, res, _ = A.call("POST", f"/user-storage/{lid}/sync?action=triggerFullSync")
    print("    ", res)
    return lid


def grupos_a_roles(roles_kc):
    paso("Mapeo grupo → rol (GRP_* → ROL_*)")
    for g, r in GRUPO_A_ROL.items():
        enc = urllib.parse.quote(g)
        lista = [x for x in A.get(f"/groups?search={enc}&exact=true") if x["name"] == g]
        if not lista:
            sys.exit(f"[!] El grupo {g} no se sincronizó desde el directorio")
        A.call("POST", f"/groups/{lista[0]['id']}/role-mappings/realm", [roles_kc[r]], ok=(204, 200, 409))
        print(f"     {g} → {r}")


# ----------------------------------------------------------------------------- 6. MFA obligatorio por rol
def flujo_mfa():
    paso("Flujo de login con TOTP obligatorio para ROL_ADMIN y ROL_AUDITOR")
    nombre = "browser-blackwall"
    q = urllib.parse.quote
    # Siempre se reconstruye: primero se desvincula el flujo del realm y se borra la versión anterior
    flujos = {f["alias"]: f for f in A.get("/authentication/flows")}
    if nombre in flujos:
        r = A.get("")
        A.call("PUT", "", {**r, "browserFlow": "browser"})
        A.call("DELETE", f"/authentication/flows/{flujos[nombre]['id']}")
    A.call("POST", "/authentication/flows/browser/copy", {"newName": nombre})
    forms = f"{nombre} forms"
    for e in A.get(f"/authentication/flows/{q(nombre)}/executions"):
        if e.get("displayName", "").endswith("Conditional 2FA") or e.get("displayName", "").endswith("Conditional OTP"):
            A.call("DELETE", f"/authentication/executions/{e['id']}")

    def subflujo(alias):
        A.call("POST", f"/authentication/flows/{q(forms)}/executions/flow",
               {"alias": alias, "type": "basic-flow", "provider": "registration-page-form", "description": alias})
        e = next(x for x in A.get(f"/authentication/flows/{q(forms)}/executions") if x.get("displayName") == alias)
        e["requirement"] = "CONDITIONAL"
        A.call("PUT", f"/authentication/flows/{q(forms)}/executions", e)

    def paso_flujo(sub, proveedor, config=None):
        A.call("POST", f"/authentication/flows/{q(sub)}/executions/execution", {"provider": proveedor})
        e = [x for x in A.get(f"/authentication/flows/{q(sub)}/executions") if x.get("providerId") == proveedor][-1]
        e["requirement"] = "REQUIRED"
        A.call("PUT", f"/authentication/flows/{q(sub)}/executions", e)
        if config:
            A.call("POST", f"/authentication/executions/{e['id']}/config", {"alias": f"{sub} · {config['condUserRole']}", "config": config})

    # Ramas excluyentes (un usuario tiene un solo rol): obligatorio por rol, o voluntario si ya configuró TOTP
    for rol in MFA_OBLIGATORIO:
        sub = f"2FA obligatorio {rol}"
        subflujo(sub)
        paso_flujo(sub, "conditional-user-role", {"condUserRole": rol, "negate": "false"})
        paso_flujo(sub, "auth-otp-form")
    sub = "2FA voluntario"
    subflujo(sub)
    paso_flujo(sub, "conditional-user-configured")
    for rol in MFA_OBLIGATORIO:
        paso_flujo(sub, "conditional-user-role", {"condUserRole": rol, "negate": "true"})
    paso_flujo(sub, "auth-otp-form")
    return nombre


def enlazar_flujo(nombre):
    r = A.get("")
    r["browserFlow"] = nombre
    A.call("PUT", "", r)


def actualizar_urls():
    """Cambia solo las direcciones del cliente de la app (modo público/local): rápido y sin tocar el resto."""
    paso(f"Direcciones del cliente cli-blackwall-dev → {APP}")
    c = A.get("/clients?clientId=cli-blackwall-dev")[0]
    c["rootUrl"], c["baseUrl"] = APP, APP + "/"
    c["redirectUris"] = [APP + "/callback"]
    c["attributes"] = {**c.get("attributes", {}), "post.logout.redirect.uris": APP + "/"}
    A.call("PUT", f"/clients/{c['id']}", c)


if __name__ == "__main__":
    if os.environ.get("BW_SOLO_URLS") == "1":
        esperar_keycloak()
        actualizar_urls()
        sys.exit(0)
    esperar_keycloak()
    rid = realm()
    roles_kc = roles()
    sc = scopes(roles_kc)
    clientes(sc)
    ldap(rid)
    grupos_a_roles(roles_kc)
    enlazar_flujo(flujo_mfa())
    print("\n[ok] Keycloak configurado. Issuer:", f"{KC}/realms/{REALM}")
