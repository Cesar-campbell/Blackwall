#!/usr/bin/env bash
# Prepara todo lo que NO va en el repositorio: CA propia, certificados TLS, secretos y LDIF del directorio.
# Es idempotente: si algo ya existe no lo toca (borra $BW_HOME para empezar de cero).
set -euo pipefail

BW_HOME="${BW_HOME:-$HOME/.local/share/blackwall}"
BASE="dc=blackwall,dc=utp"
ENVF="$BW_HOME/blackwall.env"
CERTS="$BW_HOME/certs"
LDIFS="$BW_HOME/ldifs"

mkdir -p "$CERTS" "$LDIFS"
chmod 755 "$BW_HOME" "$CERTS" "$LDIFS"

azar() { openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | head -c "${1:-24}"; }

# ---------------------------------------------------------------- 1. Autoridad certificadora propia
if [[ ! -f "$CERTS/ca.crt" ]]; then
  echo "[+] Creando CA propia (Blackwall Lab CA)"
  openssl genrsa -out "$CERTS/ca.key" 4096 2>/dev/null
  chmod 600 "$CERTS/ca.key"
  openssl req -x509 -new -nodes -key "$CERTS/ca.key" -sha256 -days 825 \
    -subj "/C=PA/O=UTP Blackwall Lab/CN=Blackwall Lab CA" \
    -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign" \
    -addext "subjectKeyIdentifier=hash" -out "$CERTS/ca.crt"
fi

# ---------------------------------------------------------------- 2. Certificados de servidor
# $1 nombre, $2 lista SAN (formato openssl)
cert() {
  local n="$1" san="$2"
  [[ -f "$CERTS/$n.crt" ]] && return
  echo "[+] Certificado TLS para $n"
  openssl genrsa -out "$CERTS/$n.key" 2048 2>/dev/null
  openssl req -new -key "$CERTS/$n.key" -subj "/C=PA/O=UTP Blackwall Lab/CN=$n" -out "$CERTS/$n.csr"
  printf "subjectAltName=%s\nbasicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\nsubjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid,issuer\n" "$san" > "$CERTS/$n.ext"
  openssl x509 -req -in "$CERTS/$n.csr" -CA "$CERTS/ca.crt" -CAkey "$CERTS/ca.key" -CAcreateserial \
    -days 397 -sha256 -extfile "$CERTS/$n.ext" -out "$CERTS/$n.crt" 2>/dev/null
  rm -f "$CERTS/$n.csr" "$CERTS/$n.ext"
  # Los contenedores corren con usuarios sin privilegios: la clave debe ser legible dentro de ellos.
  chmod 644 "$CERTS/$n.key" "$CERTS/$n.crt"
}
cert keycloak "DNS:acceso.localhost,DNS:keycloak,DNS:localhost"
cert app      "DNS:app.localhost,DNS:app,DNS:localhost"
cert ldap     "DNS:ldap,DNS:localhost"
cert db       "DNS:db,DNS:localhost"
chmod 644 "$CERTS/ca.crt"

# ---------------------------------------------------------------- 3. Secretos (fuera del código)
if [[ ! -f "$ENVF" ]]; then
  echo "[+] Generando secretos en $ENVF"
  umask 077
  cat > "$ENVF" <<EOF
BW_HOME=$BW_HOME
LDAP_BASE=$BASE
KC_ADMIN_USER=campbell.cesar
KC_ADMIN_PASSWORD=$(azar 24)
KC_DB_PASSWORD=$(azar 24)
LDAP_ADMIN_PASSWORD=$(azar 24)
LDAP_CONFIG_PASSWORD=$(azar 24)
SVC_LDAP_PASSWORD=$(azar 24)
CLIENT_SECRET=$(azar 32)
SYNC_CLIENT_SECRET=$(azar 32)
DEMO_PASSWORD=Bw-$(azar 14)
EOF
  chmod 600 "$ENVF"
fi
# shellcheck disable=SC1090
source "$ENVF"

# ---------------------------------------------------------------- 4. LDIF del directorio
# Se regeneran siempre (solo se cargan la primera vez que arranca OpenLDAP).
rm -f "$LDIFS"/*.ldif
cat > "$LDIFS/01-estructura.ldif" <<EOF
dn: $BASE
objectClass: top
objectClass: dcObject
objectClass: organization
o: Blackwall UTP
dc: blackwall

# Una unidad organizativa por área (guía, fase 2)
dn: ou=ti,$BASE
objectClass: organizationalUnit
ou: ti
description: Tecnologia e infraestructura

dn: ou=soc,$BASE
objectClass: organizationalUnit
ou: soc
description: Centro de operaciones de seguridad

dn: ou=cum,$BASE
objectClass: organizationalUnit
ou: cum
description: Cumplimiento y auditoria

dn: ou=usr,$BASE
objectClass: organizationalUnit
ou: usr
description: Usuarios que reportan incidentes

dn: ou=pub,$BASE
objectClass: organizationalUnit
ou: pub
description: Acceso publico

dn: ou=servicio,$BASE
objectClass: organizationalUnit
ou: servicio
description: Cuentas de servicio (sin inicio de sesion interactivo)

dn: ou=politicas,$BASE
objectClass: organizationalUnit
ou: politicas
EOF

# Política de contraseñas (NIST SP 800-63B, guía 7.2): 12+ caracteres, historial de 5, bloqueo tras 5 fallos
cat > "$LDIFS/02-politica.ldif" <<EOF
dn: cn=default,ou=politicas,$BASE
objectClass: device
objectClass: pwdPolicy
cn: default
pwdAttribute: userPassword
pwdMinLength: 12
pwdCheckQuality: 1
pwdInHistory: 5
pwdMaxFailure: 5
pwdLockout: TRUE
pwdLockoutDuration: 60
pwdFailureCountInterval: 0
pwdMustChange: FALSE
pwdAllowUserChange: TRUE
pwdSafeModify: FALSE
EOF

# Cuenta de servicio: sin inetOrgPerson, así Keycloak nunca la importa como usuario que inicia sesión
cat > "$LDIFS/03-servicio.ldif" <<EOF
dn: uid=svc-blackwall-sync,ou=servicio,$BASE
objectClass: account
objectClass: simpleSecurityObject
uid: svc-blackwall-sync
description: Cuenta de servicio Blackwall (sincronizacion Keycloak y administracion de usuarios)
userPassword: $SVC_LDAP_PASSWORD
EOF

# Usuarios: apellido.nombre, uno por rol como mínimo (guía, sección 6 y fase 2)
usuario() { # uid ou nombre apellido
  cat <<EOF
dn: uid=$1,ou=$2,$BASE
objectClass: inetOrgPerson
uid: $1
cn: $3 $4
givenName: $3
sn: $4
mail: $1@blackwall.utp
userPassword: $DEMO_PASSWORD

EOF
}
grupo() { # ou nombre-grupo miembro...
  local ou="$1" cn="$2"; shift 2
  echo "dn: cn=$cn,ou=$ou,$BASE"
  echo "objectClass: groupOfNames"
  echo "cn: $cn"
  for m in "$@"; do echo "member: uid=$m,ou=$ou,$BASE"; done
  echo
}
{
  usuario campbell.cesar  ti  Cesar  Campbell
  usuario cruz.irvin      soc Irvin  Cruz
  usuario pinto.nicole    soc Nicole Pinto
  usuario galvez.angel    cum Angel  Galvez
  usuario ejemplo.usuario  usr Usuario Ejemplo
  usuario ejemplo.usuario2 usr Usuario "Ejemplo Dos"
  usuario cordero.moises  pub Moises Cordero
} > "$LDIFS/04-usuarios.ldif"
{
  grupo ti  GRP_TI_ADMIN      campbell.cesar
  grupo soc GRP_SOC_ANALISTA  cruz.irvin pinto.nicole
  grupo cum GRP_CUM_AUDITOR   galvez.angel
  grupo usr GRP_USR_USUARIO   ejemplo.usuario ejemplo.usuario2
  grupo pub GRP_PUB_INVITADO  cordero.moises
} > "$LDIFS/05-grupos.ldif"
chmod 644 "$LDIFS"/*.ldif

echo "[ok] Todo listo en $BW_HOME"
