#!/usr/bin/env bash
# Atajo para operar Blackwall (versión real). Uso: scripts/bw.sh <comando>
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
export BW_HOME="${BW_HOME:-$HOME/.local/share/blackwall}"
ENVF="$BW_HOME/blackwall.env"
dc() { docker compose --env-file "$ENVF" -f "$RAIZ/docker-compose.yml" "$@"; }

case "${1:-ayuda}" in
  preparar)    "$RAIZ/scripts/preparar.sh" ;;
  infra)       "$RAIZ/scripts/preparar.sh"; dc up -d ldap ldap-init db keycloak ;;
  configurar)  python3 "$RAIZ/keycloak/configurar.py" ;;
  app)         dc up -d --build app ;;
  arriba)      "$RAIZ/scripts/preparar.sh"; dc up -d --build; python3 "$RAIZ/keycloak/configurar.py" ;;
  abajo)       dc down ;;
  limpiar)     dc down -v; echo "Datos borrados. Para regenerar secretos y certificados: rm -rf $BW_HOME" ;;
  logs)        shift; dc logs -f "${@:-}" ;;
  estado)      dc ps ;;
  credenciales)
    # shellcheck disable=SC1090
    source "$ENVF"
    echo "Contraseña de las cuentas de demostración: $DEMO_PASSWORD"
    echo "Admin de Keycloak: $KC_ADMIN_USER / $KC_ADMIN_PASSWORD   (https://acceso.localhost:8443)" ;;
  pruebas)     shift; python3 "$RAIZ/pruebas/casos_prueba.py" "$@" ;;
  *) sed -n '2,3p' "$0"; echo "Comandos: preparar infra configurar app arriba abajo limpiar logs estado credenciales pruebas" ;;
esac
