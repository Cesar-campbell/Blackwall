#!/usr/bin/env python3
"""Ejecuta comandos reales contra el sistema y guarda su salida (con secretos redactados) en docs/guia/term/*.txt.
Esas salidas se incrustan como "capturas de terminal" en la guía técnica."""
import json
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "pruebas"))
import oidc_cliente as o  # noqa: E402

OUT = os.path.join(RAIZ, "docs", "guia", "term")
os.makedirs(OUT, exist_ok=True)
ENV = o.ENV
BASE = ENV["LDAP_BASE"]
SECRETOS = [ENV[k] for k in ("DEMO_PASSWORD", "CLIENT_SECRET", "SYNC_CLIENT_SECRET", "SVC_LDAP_PASSWORD", "KC_ADMIN_PASSWORD",
                             "LDAP_ADMIN_PASSWORD", "LDAP_CONFIG_PASSWORD", "KC_DB_PASSWORD")]


def limpiar(t):
    for s in SECRETOS:
        t = t.replace(s, "********")
    return t


def sh(cmd, shell=True, entrada=None):
    r = subprocess.run(cmd, shell=shell, capture_output=True, text=True, input=entrada, cwd=RAIZ)
    return limpiar((r.stdout + r.stderr).strip())


def guardar(nombre, comando_mostrado, salida):
    with open(os.path.join(OUT, nombre + ".txt"), "w") as f:
        f.write(f"$ {comando_mostrado}\n{salida}\n")
    print("ok", nombre)


LD = f'docker exec -e LDAPTLS_REQCERT=never blackwall-ldap-1 ldapsearch -LLL -x -H ldaps://localhost:1636 -D cn=admin,{BASE} -w "{ENV["LDAP_ADMIN_PASSWORD"]}"'
CFG = f'docker exec -e LDAPTLS_REQCERT=never blackwall-ldap-1 ldapsearch -LLL -x -H ldaps://localhost:1636 -D cn=admin,cn=config -w "{ENV["LDAP_CONFIG_PASSWORD"]}"'

# --- contenedores
guardar("docker-ps", "docker compose ps", sh("docker ps --filter name=blackwall --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'"))
guardar("versiones", "docker --version; docker compose version; cat /etc/os-release | grep PRETTY_NAME",
        sh("docker --version; docker compose version; grep PRETTY_NAME /etc/os-release; php --version | head -1; python3 --version; node --version"))

# --- directorio
guardar("ldap-arbol", f"ldapsearch -H ldaps://… -b {BASE} -s one dn", sh(f"{LD} -b {BASE} -s one dn | grep '^dn'"))
guardar("ldap-usuarios", f"ldapsearch -H ldaps://… -b {BASE} '(objectClass=inetOrgPerson)' uid cn",
        sh(f"{LD} -b {BASE} '(objectClass=inetOrgPerson)' uid cn | grep -v '^$'"))
guardar("ldap-grupos", f"ldapsearch -H ldaps://… -b {BASE} '(objectClass=groupOfNames)' cn member",
        sh(f"{LD} -b {BASE} '(objectClass=groupOfNames)' cn member | grep -v '^$'"))
guardar("ldap-politica", f"ldapsearch -H ldaps://… -b cn=default,ou=politicas,{BASE}",
        sh(f"{LD} -b cn=default,ou=politicas,{BASE} | grep -v '^$'"))
guardar("ldap-acl", "ldapsearch -b olcDatabase={2}mdb,cn=config olcAccess olcPPolicyDefault",
        sh(f"{CFG} -b cn=config '(|(olcDatabase={{2}}mdb)(olcOverlay={{0}}ppolicy))' olcAccess olcPPolicyDefault olcPPolicyUseLockout olcPPolicyHashCleartext | grep -v '^$'"))
guardar("ldap-hash", f"ldapsearch … -b uid=cruz.irvin,ou=soc,{BASE} userPassword",
        sh(f"{LD} -b uid=cruz.irvin,ou=soc,{BASE} -t userPassword | grep -v '^$'; docker exec -e LDAPTLS_REQCERT=never blackwall-ldap-1 sh -c 'echo; echo \"userPassword (decodificado, primeros caracteres):\"; ldapsearch -LLL -x -H ldaps://localhost:1636 -D cn=admin,{BASE} -w \"{ENV['LDAP_ADMIN_PASSWORD']}\" -b uid=cruz.irvin,ou=soc,{BASE} userPassword | grep userPassword:: | cut -d\" \" -f2 | base64 -d | cut -c1-12; echo \"…[hash salado]\"'"))

# --- TLS / certificados
C = os.path.join(o.BW_HOME, "certs")
guardar("tls-cert", "openssl x509 -in keycloak.crt -noout -subject -issuer -dates -ext subjectAltName,keyUsage,extendedKeyUsage",
        sh(f"openssl x509 -in {C}/keycloak.crt -noout -subject -issuer -dates -ext subjectAltName,keyUsage,extendedKeyUsage"))
guardar("tls-ca", "openssl x509 -in ca.crt -noout -subject -dates -ext basicConstraints,keyUsage",
        sh(f"openssl x509 -in {C}/ca.crt -noout -subject -dates -ext basicConstraints,keyUsage"))
tls = []
for nombre, hostport in [("app", "app.localhost:8444"), ("keycloak (IdP)", "acceso.localhost:8443")]:
    s = sh(f"echo | openssl s_client -connect {hostport} -CAfile {C}/ca.crt -brief 2>&1 | head -8")
    tls.append(f"--- {nombre}\n{s}")
s = sh(f"echo | docker exec -i -e LDAPTLS_CACERT=/certs/ca.crt blackwall-app-1 openssl s_client -connect ldap:1636 -CAfile /certs/ca.crt -brief 2>&1 | head -8")
tls.append(f"--- directorio (LDAPS, desde el contenedor de la app)\n{s}")
guardar("tls-conexiones", "openssl s_client -connect <host:puerto> -CAfile ca.crt -brief", "\n".join(tls))

# --- PostgreSQL con TLS
guardar("db-tls", "psql: conexiones de Keycloak a la base (pg_stat_ssl) y un intento SIN TLS",
        sh("docker exec -u postgres blackwall-db-1 psql -U keycloak -d keycloak -c \"SELECT usename, ssl, version AS tls, cipher FROM pg_stat_ssl s JOIN pg_stat_activity a USING (pid) WHERE datname='keycloak' LIMIT 2;\"; echo; echo '--- intento de conexión sin cifrar:'; docker run --rm --network blackwall_bw -e PGPASSWORD=x postgres:16-alpine psql 'host=db user=keycloak dbname=keycloak sslmode=disable' -c 'select 1' 2>&1 | head -2"))

# --- cabeceras HTTP de la app
guardar("http-cabeceras", "curl -sI --cacert ca.crt https://app.localhost:8444/", sh(f"curl -sI --cacert {C}/ca.crt https://app.localhost:8444/"))
guardar("http-api-sin-token", "curl -si --cacert ca.crt https://app.localhost:8444/api/casos",
        sh(f"curl -si --cacert {C}/ca.crt https://app.localhost:8444/api/casos | head -12"))

# --- OIDC: descubrimiento y JWKS
guardar("oidc-discovery", "curl -s https://acceso.localhost:8443/realms/proyecto-accesos/.well-known/openid-configuration | jq (campos clave)",
        json.dumps({k: v for k, v in json.load(__import__("urllib.request").request.urlopen(o.ISSUER + "/.well-known/openid-configuration", context=o.CTX)).items()
                    if k in ("issuer", "authorization_endpoint", "token_endpoint", "jwks_uri", "end_session_endpoint", "grant_types_supported",
                             "response_types_supported", "code_challenge_methods_supported", "id_token_signing_alg_values_supported")}, indent=2))
j = json.load(__import__("urllib.request").request.urlopen(o.ISSUER + "/protocol/openid-connect/certs", context=o.CTX))
for k in j["keys"]:
    k["n"] = k["n"][:28] + "…"
    for x in ("x5c", "x5t", "x5t#S256"):
        k.pop(x, None)
guardar("oidc-jwks", "curl -s …/protocol/openid-connect/certs", json.dumps(j, indent=2))

# --- un token real (redactado): usuario sin MFA
t = o.tokens("ejemplo.usuario", ENV["DEMO_PASSWORD"])
at = t["access_token"]
partes = at.split(".")
import base64  # noqa: E402
dec = lambda p: json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))  # noqa: E731
cab, carga = dec(partes[0]), dec(partes[1])
for k in ("jti", "sid", "sub"):
    if k in carga:
        carga[k] = carga[k][:8] + "…"
carga["scope"] = carga["scope"].split()
guardar("jwt-decodificado", "access token de ejemplo.usuario, decodificado (firma y datos sensibles redactados)",
        "CABECERA\n" + json.dumps(cab, indent=2) + "\n\nCARGA (payload)\n" + json.dumps(carga, indent=2, ensure_ascii=False) +
        f"\n\nFIRMA (RS256)\n{partes[2][:24]}…[redactado]")

# --- eventos de Keycloak y auditoría de la app
guardar("kc-eventos", "GET /admin/realms/proyecto-accesos/events?max=6 (con la cuenta de servicio)",
        sh(f"docker exec blackwall-app-1 php -r 'require \"/var/www/app/vendor/autoload.php\"; echo json_encode(array_slice(Blackwall\\Keycloak::eventos(8),0,6), JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE);'"))

# --- dependencias y código
deps = sh("docker exec blackwall-app-1 php -r 'echo PHP_VERSION, PHP_EOL; foreach (json_decode(file_get_contents(\"/var/www/app/vendor/composer/installed.json\"), true)[\"packages\"] as $p) echo $p[\"name\"], \" \", $p[\"version\"], PHP_EOL;'")
ext = sh("docker exec blackwall-app-1 sh -c \"php -m | grep -i -E '^(ldap|curl|openssl|pdo_sqlite|sodium|mbstring|json)$' | tr '\\n' ' '; echo; apache2 -v | head -1\"")
guardar("php-deps", "versiones y librerías de la aplicación", "PHP " + deps + "\nextensiones: " + ext)
guardar("codigo-lineas", "wc -l (código propio)", sh("wc -l app/src/*.php app/public/index.php app/public/assets/app.js app/public/vista.html keycloak/configurar.py scripts/*.sh pruebas/*.py pruebas/*.cjs docker-compose.yml | sed 's#^ *##'"))
print("listo")
