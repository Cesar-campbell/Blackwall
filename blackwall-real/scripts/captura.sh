#!/usr/bin/env bash
# CP-10: captura de red (tcpdump en el espacio de red de Keycloak) durante un login real y análisis del contenido.
# Los .pcap se abren con Wireshark. Incluye un experimento de control sin TLS para mostrar qué se vería en texto plano.
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
export BW_HOME="${BW_HOME:-$HOME/.local/share/blackwall}"
# shellcheck disable=SC1091
source "$BW_HOME/blackwall.env"
EV="$RAIZ/evidencias"; mkdir -p "$EV"
IMG=bw-captura

if ! docker image inspect "$IMG" >/dev/null 2>&1; then
  echo "[+] Construyendo imagen de captura (tcpdump + tshark)" >&2
  docker build -q -t "$IMG" - >/dev/null <<'DF'
FROM debian:trixie
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update >/dev/null && apt-get install -y --no-install-recommends tcpdump tshark curl python3 >/dev/null && rm -rf /var/lib/apt/lists/*
DF
fi
UIDG="$(id -u):$(id -g)"

# ---------- 1) Captura del login real por HTTPS
docker rm -f bw-cap >/dev/null 2>&1 || true
docker run -d --name bw-cap --net container:blackwall-keycloak-1 --cap-add NET_RAW --cap-add NET_ADMIN -v "$EV:/cap" "$IMG" \
  sh -c "tcpdump -i eth0 -U -w /cap/login-https.pcap 'tcp port 8443'; chown $UIDG /cap/login-https.pcap" >/dev/null
sleep 3
python3 -I - <<PY
import sys; sys.path.insert(0, "$RAIZ/pruebas")
import oidc_cliente as o
r = o.login("ejemplo.usuario", o.ENV["DEMO_PASSWORD"], app=True)
assert r["ok"], r.get("error")
st, ses = o.sesion_app(r)
r["nav"].pedir(o.APP + "/auth/logout", {}, {"X-CSRF-Token": ses["csrf"]})
PY
sleep 2
docker stop -t 5 bw-cap >/dev/null; docker rm bw-cap >/dev/null

# ---------- 2) Control: el mismo tipo de envío SIN TLS (HTTP plano) para contrastar
docker run --rm --cap-add NET_RAW --cap-add NET_ADMIN -v "$EV:/cap" "$IMG" sh -c '
  python3 -m http.server 8099 --bind 127.0.0.1 >/dev/null 2>&1 &
  sleep 1
  tcpdump -i lo -U -w /cap/control-http.pcap "tcp port 8099" 2>/dev/null &
  sleep 1
  curl -s -o /dev/null -d "username=ejemplo.usuario&password=CLAVE-DE-EJEMPLO-123" -H "Authorization: Bearer eyJhbGciOiJSUzI1NiJ9.ejemplo.firma" http://127.0.0.1:8099/login
  sleep 1; kill %2 2>/dev/null; sleep 1; chown '"$UIDG"' /cap/control-http.pcap' >/dev/null 2>&1 || true

# ---------- 3) Análisis
cuenta() { grep -a -c -F -- "$2" "$1" || true; }
SALIDA="$EV/captura-login.txt"
P1=$(cuenta "$EV/login-https.pcap" "$DEMO_PASSWORD"); P2=$(cuenta "$EV/login-https.pcap" "eyJ")
P3=$(cuenta "$EV/login-https.pcap" "$CLIENT_SECRET"); P4=$(cuenta "$EV/login-https.pcap" "code_verifier")
P5=$(cuenta "$EV/login-https.pcap" "password=")
C1=$(cuenta "$EV/control-http.pcap" "CLAVE-DE-EJEMPLO-123"); C2=$(cuenta "$EV/control-http.pcap" "eyJhbGci")
{
  echo "Captura del login por HTTPS: $EV/login-https.pcap  ($(stat -c %s "$EV/login-https.pcap") bytes)"
  docker run --rm -v "$EV:/cap:ro" "$IMG" sh -c '
    echo "Paquetes: $(tshark -r /cap/login-https.pcap 2>/dev/null | wc -l)"
    echo "Protocolo de aplicación observado: $(tshark -r /cap/login-https.pcap -T fields -e _ws.col.Protocol 2>/dev/null | sort | uniq -c | sort -rn | tr "\n" " ")"
    echo "Versión TLS negociada: $(tshark -r /cap/login-https.pcap -Y "tls.handshake.type==2" -T fields -e tls.handshake.version 2>/dev/null | sort -u | tr "\n" " ")"
    echo "Suite de cifrado: $(tshark -r /cap/login-https.pcap -Y "tls.handshake.type==2" -T fields -e tls.handshake.ciphersuite 2>/dev/null | sort -u | tr "\n" " ")"'
  echo
  echo "Búsqueda de datos sensibles en texto plano dentro del .pcap (HTTPS):"
  echo "  - contraseña del usuario ............ $P1 coincidencias"
  echo "  - tokens JWT (prefijo eyJ) .......... $P2 coincidencias"
  echo "  - secreto del cliente ............... $P3 coincidencias"
  echo "  - code_verifier (PKCE) .............. $P4 coincidencias"
  echo "  - campo password= ................... $P5 coincidencias"
  echo
  echo "Control sin TLS (HTTP plano, $EV/control-http.pcap):"
  echo "  - contraseña en claro ............... $C1 coincidencias"
  echo "  - token en claro .................... $C2 coincidencias"
} | tee "$SALIDA" >&2

if [[ "$P1$P2$P3$P4$P5" == "00000" && "${C1:-0}" -gt 0 && "${C2:-0}" -gt 0 ]]; then
  echo "OK: con HTTPS no hay contraseñas ni tokens visibles (0 coincidencias); sin TLS sí (control: $C1/$C2)"
else
  echo "FALLO: revisar $SALIDA"; exit 1
fi
