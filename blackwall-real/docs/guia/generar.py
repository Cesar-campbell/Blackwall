#!/usr/bin/env python3
"""Arma la guía técnica (HTML) y la convierte a PDF con Chromium. Dos pasadas: la segunda lleva los números de página al índice.
Uso: python3 docs/guia/generar.py"""
import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import s1  # noqa: E402
import s2  # noqa: E402
import s3  # noqa: E402
from base import CSS  # noqa: E402

DOCS = os.path.dirname(AQUI)
HTML = os.path.join(AQUI, "guia.html")
PDF = os.path.join(DOCS, "Guia-Tecnica-Blackwall.pdf")

LOGO = '<svg width="54" height="54" viewBox="0 0 64 64"><circle cx="32" cy="32" r="26" fill="none" stroke="#e8f0f9" stroke-width="5" stroke-dasharray="42 12.45" transform="rotate(-80 32 32)"/><circle cx="32" cy="32" r="16" fill="#0a4d8c"/><path d="M26.5 31v-3.5a5.5 5.5 0 0 1 11 0V31" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round"/><rect x="23.5" y="30.5" width="17" height="13" rx="2.5" fill="#fff"/><circle cx="32" cy="36" r="2" fill="#0a4d8c"/><rect x="31.2" y="37" width="1.6" height="3.6" rx=".6" fill="#0a4d8c"/></svg>'

secciones = s1.secciones() + s2.secciones() + s3.secciones()


def etiqueta(n):
    return n.rstrip("b")


def construir(paginas):
    toc = []
    for n, titulo, _ in secciones:
        if n.endswith("b"):
            continue
        p = paginas.get(n, "")
        toc.append(f'<div class="row"><b>{n}</b><span class="t">{titulo}</span><span class="p">{p}</span></div>')
    cuerpo = []
    for n, titulo, h in secciones:
        t = titulo if not n.endswith("b") else titulo
        cuerpo.append(f'<section class="sec"><h1>{etiqueta(n)}. {t}</h1>{h}</section>')
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Blackwall · Guía técnica</title><style>{CSS}</style></head><body>
<div class="cover">
  <div class="lg">{LOGO}BLACKWALL</div>
  <div><div class="eslo">Nadie cruza sin ser verificado</div><h1>Guía técnica de la aplicación</h1>
  <p>Cómo funciona cada pieza: herramientas, protocolos, funciones, pruebas y evidencias. Para que todo el grupo pueda explicar y defender el proyecto.</p></div>
  <div class="foot">Proyecto final · Seguridad en accesos: identificación, autenticación y autorización<br>Universidad Tecnológica de Panamá · FISC · Ciberseguridad II<br>Facilitadora: Mildred Echezano</div>
</div>
<section><h1>Contenido</h1>
<p class="small">Cómo leer esta guía: cada sección explica un tema <b>en palabras simples</b>, muestra una <b>captura real</b> y dice <b>dónde está en el código</b>. Al final hay un glosario.</p>
<div class="toc">{''.join(toc)}</div></section>
{''.join(cuerpo)}
</body></html>"""


def a_pdf():
    r = subprocess.run(["chromium-browser", "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={PDF}", "--virtual-time-budget=20000", "file://" + HTML], capture_output=True, text=True, timeout=300)
    if not os.path.exists(PDF):
        sys.exit("No se generó el PDF: " + r.stderr[-400:])


def paginas_de_secciones():
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", PDF], capture_output=True, text=True).stdout).group(1))
    res = {}
    textos = {p: subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), "-layout", PDF, "-"], capture_output=True, text=True).stdout for p in range(3, n + 1)}
    for num, titulo, _ in secciones:
        if num.endswith("b"):
            continue
        plano = re.sub(r"<[^>]+>", "", titulo)[:30]
        for p in range(3, n + 1):
            if re.search(rf"^\s*{re.escape(etiqueta(num))}\.\s+{re.escape(plano)}", textos[p], re.M):
                res[num] = p
                break
    return res, n


open(HTML, "w").write(construir({}))
a_pdf()
pags, total = paginas_de_secciones()
open(HTML, "w").write(construir(pags))
a_pdf()
print("páginas:", total, "· secciones localizadas:", len(pags), "de", sum(1 for s in secciones if not s[0].endswith("b")))
print(PDF)
