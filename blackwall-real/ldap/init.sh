#!/bin/bash
# Configuración "en caliente" de OpenLDAP (cn=config). Se ejecuta una vez tras arrancar el directorio:
#  1) política de contraseñas por defecto  2) permisos (ACL) mínimos para la cuenta de servicio
set -euo pipefail
export LDAPTLS_CACERT=/certs/ca.crt
URI="ldaps://ldap:1636"
CFG=(-x -H "$URI" -D "cn=admin,cn=config" -w "$LDAP_CONFIG_ADMIN_PASSWORD")
SVC="uid=svc-blackwall-sync,ou=servicio,$LDAP_ROOT"

for i in $(seq 1 60); do
  ldapsearch "${CFG[@]}" -b cn=config -s base dn >/dev/null 2>&1 && break
  sleep 2
done

# 1) La política "cn=default" se aplica a todo usuario que no tenga una propia
ldapmodify "${CFG[@]}" >/dev/null <<LDIF
dn: olcOverlay={0}ppolicy,olcDatabase={2}mdb,cn=config
changetype: modify
replace: olcPPolicyDefault
olcPPolicyDefault: cn=default,ou=politicas,$LDAP_ROOT
LDIF

# 2) ACL: solo la cuenta de servicio escribe; cada persona se ve a sí misma; nadie anónimo lee nada.
#    (el administrador raíz del directorio no pasa por ACL)
ldapmodify "${CFG[@]}" >/dev/null <<LDIF
dn: olcDatabase={2}mdb,cn=config
changetype: modify
replace: olcAccess
olcAccess: {0}to attrs=userPassword by dn.exact="$SVC" write by self write by anonymous auth by * none
olcAccess: {1}to dn.subtree="$LDAP_ROOT" by dn.exact="$SVC" write by self read by * none
LDIF
echo "[ldap-init] política de contraseñas y ACL aplicadas"
