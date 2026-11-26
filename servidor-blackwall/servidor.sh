#!/usr/bin/env bash
# Servidor Blackwall: pone la aplicación real accesible desde internet y la mantiene encendida.
# Uso:  ./servidor.sh <comando>      (ver "ayuda")
set -uo pipefail

SRV="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BW="$(cd "$SRV/../blackwall-real" && pwd)"
export BW_HOME="${BW_HOME:-$HOME/.local/share/blackwall}"
ENVF="$BW_HOME/blackwall.env"
EST="$BW_HOME/servidor"
CF="$HOME/.local/bin/cloudflared"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT="$UNIT_DIR/blackwall.service"
TSB="$HOME/.local/bin/tailscaled"
TSC="$HOME/.local/bin/tailscale"
TSD="$HOME/.local/share/tailscale"
PUERTO_PROXY=8091
KC_LOCAL="https://localhost:8443/acceso"
mkdir -p "$EST"

dc_publico() { PUBLIC_URL="$1" SRV_DIR="$SRV" docker compose --env-file "$ENVF" -f "$BW/docker-compose.yml" -f "$SRV/docker-compose.publico.yml" "${@:2}"; }
dc_local()   { docker compose --env-file "$ENVF" -f "$BW/docker-compose.yml" "$@"; }
registrar()  { echo "[$(date '+%F %T')] $*"; }

esperar_docker() { until docker info >/dev/null 2>&1; do sleep 3; done; }

esperar_keycloak() {  # $1 = dirección base de Keycloak (con /auth en modo público)
  local i
  for i in $(seq 1 120); do
    curl -s --cacert "$BW_HOME/certs/ca.crt" -o /dev/null -w '%{http_code}' "$1/realms/proyecto-accesos" 2>/dev/null | grep -q 200 && return 0
    sleep 3
  done
  return 1
}

aplicar_urls() {  # $1 = dirección de la app, $2 = dirección con la que este equipo habla con Keycloak
  BW_SOLO_URLS=1 BW_APP_URL="$1" BW_KC_URL="$2" python3 -I "$BW/keycloak/configurar.py" >/dev/null
}

limpiar_cache_app() {
  docker exec -u root blackwall-app-1 sh -c 'rm -f /var/www/datos/discovery.json /var/www/datos/jwks.json /var/www/datos/svc-token.json' >/dev/null 2>&1 || true
}

# ------------------------------------------------------------------ modos
arrancar_local() {
  registrar "Modo LOCAL: https://app.localhost:8444"
  docker rm -f blackwall-proxy-1 >/dev/null 2>&1 || true
  dc_local up -d --build --force-recreate keycloak app >/dev/null 2>&1
  esperar_keycloak "https://localhost:8443" || registrar "AVISO: Keycloak tardó demasiado"
  aplicar_urls "https://app.localhost:8444" "https://localhost:8443"
  limpiar_cache_app
  echo "https://app.localhost:8444 (solo este equipo)" > "$EST/enlace.txt"
  rm -f "$EST/url-aplicada"
}

arrancar_publico() {
  [[ -s "$EST/tailscale-url" ]] || [[ -x "$CF" ]] || { registrar "ERROR: falta cloudflared ($CF) o la configuración de Tailscale"; return 1; }
  # Servicios base y proxy (con una dirección provisional; se corrige abajo si cambia)
  local previa=""; [[ -f "$EST/url-aplicada" ]] && previa="$(cat "$EST/url-aplicada")"
  dc_publico "${previa:-https://pendiente.invalid}" up -d ldap db >/dev/null 2>&1
  dc_publico "${previa:-https://pendiente.invalid}" up -d --force-recreate --no-deps proxy >/dev/null 2>&1
  # Túnel: dirección fija si existe, si no una temporal de Cloudflare
  local url="" log="$EST/tunel.log"
  : > "$log"
  if [[ -s "$EST/tailscale-url" && -x "$TSB" ]]; then
    # Dirección FIJA y gratuita con Tailscale Funnel (sin dominio propio)
    url="$(cat "$EST/tailscale-url")"
    pkill -x tailscaled 2>/dev/null || true; sleep 1
    "$TSB" --tun=userspace-networking --state="$TSD/estado" --socket="$TSD/ts.sock" >"$log" 2>&1 &
    local j
    for j in $(seq 1 30); do "$TSC" --socket="$TSD/ts.sock" status --json 2>/dev/null | grep -q '"Running"' && break; sleep 2; done
    "$TSC" --socket="$TSD/ts.sock" funnel --bg "$PUERTO_PROXY" >>"$log" 2>&1
  elif [[ -s "$SRV/tunel-fijo.env" ]]; then
    # shellcheck disable=SC1091
    source "$SRV/tunel-fijo.env"   # define TUNEL_TOKEN y URL_FIJA (túnel con nombre, dominio propio)
    "$CF" tunnel --no-autoupdate run --token "$TUNEL_TOKEN" >"$log" 2>&1 &
    url="$URL_FIJA"
  else
    "$CF" tunnel --no-autoupdate --url "http://127.0.0.1:$PUERTO_PROXY" >"$log" 2>&1 &
  fi
  CF_PID=$!
  trap 'kill $CF_PID 2>/dev/null' EXIT TERM INT
  if [[ -z "$url" ]]; then
    local i
    for i in $(seq 1 60); do
      url="$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$log" | head -1)"
      [[ -n "$url" ]] && break
      kill -0 $CF_PID 2>/dev/null || { registrar "El túnel se cerró: $(tail -2 "$log")"; return 1; }
      sleep 1
    done
  fi
  [[ -n "$url" ]] || { registrar "No se obtuvo la dirección pública"; return 1; }
  registrar "Dirección pública: $url"
  # Si cambió la dirección, Keycloak y la app se reconfiguran con la nueva
  if [[ "$url" != "$previa" ]]; then
    registrar "Aplicando la nueva dirección (tarda ~1 minuto)…"
    dc_publico "$url" up -d --build --force-recreate keycloak app >/dev/null 2>&1
  else
    dc_publico "$url" up -d --build keycloak app >/dev/null 2>&1
  fi
  esperar_keycloak "$KC_LOCAL" || registrar "AVISO: Keycloak tardó demasiado"
  aplicar_urls "$url" "$KC_LOCAL"
  limpiar_cache_app
  echo "$url" > "$EST/url-aplicada"
  echo "$url" > "$EST/enlace.txt"
  registrar "LISTO. Comparte este enlace: $url"
  wait $CF_PID   # si el túnel se cae, el script termina y systemd lo vuelve a levantar
}

servicio() {
  esperar_docker
  [[ -f "$EST/modo" ]] || echo publico > "$EST/modo"
  if [[ "$(cat "$EST/modo")" == "local" ]]; then
    arrancar_local
    sleep infinity
  else
    arrancar_publico
  fi
}

# ------------------------------------------------------------------ comandos
instalar() {
  command -v docker >/dev/null || { echo "Falta Docker"; exit 1; }
  [[ -x "$CF" ]] || { echo "Falta $CF (túnel de Cloudflare). Descárgalo de github.com/cloudflare/cloudflared/releases"; exit 1; }
  "$BW/scripts/preparar.sh" >/dev/null
  docker pull -q caddy:2-alpine >/dev/null
  mkdir -p "$UNIT_DIR"
  local inhibir=""
  systemd-inhibit --what=sleep --who=Blackwall --why=prueba --mode=block true >/dev/null 2>&1 && \
    inhibir="/usr/bin/systemd-inhibit --what=sleep:handle-lid-switch --who=Blackwall --why=\"Servidor Blackwall en ejecución\" --mode=block "
  cat > "$UNIT" <<EOF
[Unit]
Description=Servidor Blackwall (aplicación real accesible desde internet)
After=network-online.target

[Service]
Type=simple
ExecStart=${inhibir}$SRV/servidor.sh servicio
Restart=always
RestartSec=20
TimeoutStopSec=30

[Install]
WantedBy=default.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable --now blackwall.service
  loginctl enable-linger "$USER" 2>/dev/null || true
  echo "Instalado. Arranca solo al encender el equipo. Para ver el enlace: $0 enlace"
}

enlace() {
  if [[ -f "$EST/enlace.txt" ]]; then cat "$EST/enlace.txt"; else echo "Aún no hay enlace (el servicio está arrancando; revisa en 1–2 minutos)"; fi
}

estado() {
  echo "Servicio: $(systemctl --user is-active blackwall.service 2>&1) · arranque automático: $(systemctl --user is-enabled blackwall.service 2>&1) · modo: $(cat "$EST/modo" 2>/dev/null || echo '-')"
  echo "Enlace:   $(enlace)"
  docker ps --filter name=blackwall --format 'table {{.Names}}\t{{.Status}}'
  local u; u="$(cat "$EST/url-aplicada" 2>/dev/null || true)"
  [[ -n "$u" ]] && echo "Respuesta pública: HTTP $(curl -s -o /dev/null -m 15 -w '%{http_code}' "$u/acceso/realms/proyecto-accesos" 2>/dev/null) (200 = Keycloak responde desde internet)"
  echo "Memoria de los contenedores:"; docker stats --no-stream --format '  {{.Name}}  {{.MemUsage}}' $(docker ps -q --filter name=blackwall) 2>/dev/null
}

detener() {
  systemctl --user stop blackwall.service 2>/dev/null || true
  docker compose --env-file "$ENVF" -f "$BW/docker-compose.yml" -f "$SRV/docker-compose.publico.yml" stop 2>/dev/null || true
  echo "Detenido (los datos se conservan). Para volver a encender: $0 iniciar"
}

iniciar() { systemctl --user start blackwall.service; echo "Iniciando… el enlace aparece en 1–2 minutos: $0 enlace"; }

cambiar_modo() { echo "$1" > "$EST/modo"; systemctl --user restart blackwall.service; echo "Modo $1: reiniciando (1–2 minutos)"; }

eliminar() {
  if [[ "${1:-}" != "--si" ]]; then
    cat <<EOF
Esto APAGA y BORRA todo lo de Blackwall en este equipo:
  - el servicio de arranque automático y el túnel
  - los contenedores, volúmenes (usuarios, casos, auditoría) y la imagen de la app
  - los secretos y certificados en $BW_HOME
  - los programas del túnel (cloudflared y tailscale) y la sesión de Tailscale
(El código del proyecto y los PDF NO se borran.)
Para confirmar: $0 eliminar --si
EOF
    return 0
  fi
  systemctl --user disable --now blackwall.service 2>/dev/null || true
  rm -f -- "$UNIT"
  systemctl --user daemon-reload
  docker compose --env-file "$ENVF" -f "$BW/docker-compose.yml" -f "$SRV/docker-compose.publico.yml" down -v --rmi local 2>/dev/null || true
  docker rm -f blackwall-proxy-1 >/dev/null 2>&1 || true
  docker rmi caddy:2-alpine >/dev/null 2>&1 || true
  docker network rm blackwall_bw >/dev/null 2>&1 || true
  if [[ -n "$BW_HOME" && "$BW_HOME" == "$HOME/.local/share/blackwall" ]]; then rm -rf -- "$BW_HOME"; fi
  rm -f -- "$CF"
  pkill -x tailscaled 2>/dev/null || true
  if [[ "$TSD" == "$HOME/.local/share/tailscale" ]]; then rm -rf -- "$TSD" "$HOME/.local/share/tailscale-pkg"; fi
  rm -f -- "$TSB" "$TSC"
  loginctl disable-linger "$USER" 2>/dev/null || true
  echo "Todo lo de Blackwall fue apagado y eliminado de este equipo."
}

case "${1:-ayuda}" in
  servicio) servicio ;;
  instalar) instalar ;;
  enlace) enlace ;;
  estado) estado ;;
  iniciar) iniciar ;;
  detener) detener ;;
  local) cambiar_modo local ;;
  publico) cambiar_modo publico ;;
  logs) journalctl --user -u blackwall.service -f -n 40 ;;
  eliminar) shift; eliminar "${1:-}" ;;
  *) cat <<EOF
Servidor Blackwall — comandos:
  instalar    Deja todo configurado y arranca solo al encender el equipo
  enlace      Muestra la dirección pública para compartir
  estado      Servicios, enlace y memoria
  iniciar     Enciende el servidor     detener   Lo apaga (conserva los datos)
  local       Modo sin internet (solo este equipo: https://app.localhost:8444)
  publico     Modo con dirección pública (el normal)
  logs        Ver lo que está haciendo
  eliminar    Apaga y borra TODO lo de Blackwall (pide confirmación)
EOF
  ;;
esac
