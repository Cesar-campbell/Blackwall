#!/usr/bin/env python3
"""Escaneo con OWASP ZAP (Automation Framework, en Docker) contra la app real.

Uso:  python3 pruebas/zap_escaneo.py <etiqueta>      (p. ej. antes / despues)

- Autentica como ejemplo.usuario (mínimo privilegio, sin tocar datos de otros) y también prueba sin sesión.
- Alarga la vida del token a 15 min durante el escaneo y la restaura al terminar.
- Guarda en evidencias/: zap-<etiqueta>.html, zap-<etiqueta>.json y zap-<etiqueta>-resumen.md
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import casos_prueba as c  # noqa: E402
import oidc_cliente as o  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(RAIZ, "evidencias")
etiqueta = sys.argv[1] if len(sys.argv) > 1 else "antes"
URL = o.APP

kc = c.KcAdmin()
realm = kc.call("GET", "")[1]
original = realm["accessTokenLifespan"]
trabajo = tempfile.mkdtemp(prefix="zap-")
os.chmod(trabajo, 0o777)
try:
    kc.call("PUT", "", {**realm, "accessTokenLifespan": 900})
    t = c.token_de("ejemplo.usuario")[0]["access_token"]
    plan = textwrap.dedent(f"""\
    env:
      contexts:
        - name: blackwall
          urls: ["{URL}"]
          includePaths: ["{URL}/.*"]
          excludePaths: ["{URL}/auth/logout.*", "{URL}/auth/login.*"]
      parameters: {{failOnError: false, failOnWarning: false, progressToStdout: true}}
    jobs:
      - type: replacer
        rules:
          - description: bearer
            matchType: req_header
            matchString: Authorization
            matchRegex: false
            replacementString: "Bearer {t}"
            initiators: []
      - type: requestor
        requests:
          - {{url: "{URL}/", method: GET}}
          - {{url: "{URL}/api/yo", method: GET}}
          - {{url: "{URL}/api/casos", method: GET}}
          - {{url: "{URL}/api/casos/INC-001", method: GET}}
          - {{url: "{URL}/api/estadisticas", method: GET}}
          - {{url: "{URL}/api/usuarios", method: GET}}
          - {{url: "{URL}/api/auditoria", method: GET}}
          - {{url: "{URL}/api/config", method: GET}}
          - {{url: "{URL}/api/casos", method: POST, data: '{{"titulo":"zap","descripcion":"zap","severidad":"baja"}}', headers: ["Content-Type: application/json"]}}
      - type: spider
        parameters: {{context: blackwall, maxDuration: 2}}
      - type: passiveScan-wait
        parameters: {{maxDuration: 3}}
      - type: activeScan
        parameters: {{context: blackwall, maxRuleDurationInMins: 1, maxScanDurationInMins: 7}}
      - type: report
        parameters: {{template: traditional-json, reportDir: /zap/wrk, reportFile: zap-{etiqueta}, reportTitle: "Blackwall - {etiqueta}"}}
      - type: report
        parameters: {{template: traditional-html, reportDir: /zap/wrk, reportFile: zap-{etiqueta}, reportTitle: "Blackwall - {etiqueta}"}}
    """)
    with open(os.path.join(trabajo, "plan.yaml"), "w") as f:
        f.write(plan)
    print("[+] Ejecutando ZAP (unos 8–10 minutos)…", flush=True)
    r = subprocess.run(["docker", "run", "--rm", "--network", "host", "--add-host", "app.localhost:127.0.0.1",
                        "-v", f"{trabajo}:/zap/wrk:rw", "zaproxy/zap-stable", "zap.sh", "-cmd", "-silent", "-port", "8089",
                        "-config", "connection.sslAcceptAll=true", "-autorun", "/zap/wrk/plan.yaml"],
                       capture_output=True, text=True)
    open(os.path.join(trabajo, "zap.log"), "w").write(r.stdout + r.stderr)
    print((r.stdout + r.stderr)[-1500:])
finally:
    kc.call("PUT", "", {**kc.call("GET", "")[1], "accessTokenLifespan": original})

os.makedirs(EV, exist_ok=True)
for ext in ("html", "json"):
    src = os.path.join(trabajo, f"zap-{etiqueta}.{ext}")
    if os.path.exists(src):
        shutil.copy(src, os.path.join(EV, f"zap-{etiqueta}.{ext}"))
import re  # noqa: E402
# La guía pide no incluir tokens completos en las evidencias: se redactan en el log
with open(os.path.join(EV, f"zap-{etiqueta}.log"), "w") as f:
    f.write(re.sub(r"eyJ[A-Za-z0-9_.-]+", "eyJ…[redactado]", open(os.path.join(trabajo, "zap.log")).read()))

rep = json.load(open(os.path.join(EV, f"zap-{etiqueta}.json")))
alertas = []
for sitio in rep.get("site", []):
    for a in sitio.get("alerts", []):
        alertas.append({"riesgo": a["riskdesc"].split(" ")[0], "nombre": a["name"], "cwe": a.get("cweid", ""), "n": a.get("count", "")})
orden = {"High": 0, "Medium": 1, "Low": 2, "Informational": 3}
alertas.sort(key=lambda a: (orden.get(a["riesgo"], 9), a["nombre"]))
with open(os.path.join(EV, f"zap-{etiqueta}-resumen.md"), "w") as f:
    f.write(f"# Resumen del escaneo ZAP · {etiqueta}\n\n| Riesgo | Alerta | CWE | Instancias |\n|---|---|---|---|\n")
    for a in alertas:
        f.write(f"| {a['riesgo']} | {a['nombre']} | {a['cwe']} | {a['n']} |\n")
    conteo = {k: sum(1 for a in alertas if a["riesgo"] == k) for k in orden}
    f.write(f"\nTotales: {conteo}\n")
print(open(os.path.join(EV, f"zap-{etiqueta}-resumen.md")).read())
shutil.rmtree(trabajo, ignore_errors=True)
