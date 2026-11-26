"""Componentes comunes de la guía técnica (HTML → PDF con Chromium)."""
import html
import os

AQUI = os.path.dirname(os.path.abspath(__file__))


def esc(t):
    return html.escape(str(t), quote=False)


def term(nombre, titulo=None, max_lineas=None):
    """Bloque estilo terminal con la salida real guardada por recolectar.py."""
    ruta = os.path.join(AQUI, "term", nombre + ".txt")
    lineas = open(ruta).read().rstrip("\n").split("\n")
    if max_lineas:
        lineas = lineas[:max_lineas]
    cuerpo = []
    for l in lineas:
        if l.startswith("$ "):
            cuerpo.append(f'<span class="cmd">{esc(l)}</span>')
        else:
            cuerpo.append(esc(l))
    cab = f'<div class="termtit">{esc(titulo)}</div>' if titulo else ""
    return f'<figure class="term">{cab}<pre>{chr(10).join(cuerpo)}</pre></figure>'


def img(archivo, pie, ancho="100%", carpeta="img", mirar=None):
    """Captura grande con números rojos sobre lo importante (x%, y%, texto) y la lista "Qué mirar" debajo.
    Si x es None, el punto va solo en la lista (sin marca sobre la imagen)."""
    marcas, lista = "", ""
    if mirar:
        for i, (x, y, t) in enumerate(mirar, 1):
            if x is not None:
                marcas += f'<span class="mk" style="left:{x}%;top:{y}%">{i}</span>'
            lista += f'<li><span class="n">{i}</span><span>{t}</span></li>'
        lista = f'<ol class="mirar">{lista}</ol>'
    return (f'<figure class="shot" style="width:{ancho}"><div class="wrap"><img src="{carpeta}/{archivo}" alt="">{marcas}</div>'
            f'<figcaption>{pie}</figcaption>{lista}</figure>')


def img_ev(archivo, pie, mirar=None, ancho="100%"):
    return img(archivo, pie, ancho, carpeta="../../evidencias/capturas", mirar=mirar)


def duo(a, b):
    return f'<div class="duo">{a}{b}</div>'


def tabla(cabeceras, filas, clases="", anchos=None):
    th = "".join(f"<th>{c}</th>" for c in cabeceras)
    cols = ""
    if anchos:
        cols = "<colgroup>" + "".join(f'<col style="width:{a}">' for a in anchos) + "</colgroup>"
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in f) + "</tr>" for f in filas)
    return f'<table class="{clases}">{cols}<thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>'


def nota(texto, tipo="info"):
    return f'<div class="nota {tipo}">{texto}</div>'


def c(t):
    return f"<code>{esc(t)}</code>"


CSS = """
@font-face{font-family:"Inter";font-weight:400;src:url(../../app/public/assets/fonts/inter-latin-400-normal.woff2) format("woff2")}
@font-face{font-family:"Inter";font-weight:500;src:url(../../app/public/assets/fonts/inter-latin-500-normal.woff2) format("woff2")}
@font-face{font-family:"Inter";font-weight:600;src:url(../../app/public/assets/fonts/inter-latin-600-normal.woff2) format("woff2")}
@font-face{font-family:"Inter";font-weight:700;src:url(../../app/public/assets/fonts/inter-latin-700-normal.woff2) format("woff2")}
@font-face{font-family:"Inter";font-weight:800;src:url(../../app/public/assets/fonts/inter-latin-800-normal.woff2) format("woff2")}
@font-face{font-family:"JetBrains Mono";font-weight:400;src:url(../../app/public/assets/fonts/jetbrains-mono-latin-400-normal.woff2) format("woff2")}
@font-face{font-family:"JetBrains Mono";font-weight:600;src:url(../../app/public/assets/fonts/jetbrains-mono-latin-600-normal.woff2) format("woff2")}
:root{--azul:#003366;--azul2:#0a4d8c;--soft:#e8f0f9;--ink:#18222e;--mut:#5d6878;--line:#dbe2ea;--ok:#16803c;--okc:#e6f6ec;--no:#c62828;--noc:#fdecec;--al:#b45309;--alc:#fff4e2;
 --mono:"JetBrains Mono",ui-monospace,monospace}
@page{size:A4;margin:17mm 15mm 19mm 15mm;@bottom-left{content:"Blackwall · Guía técnica";font:500 8pt Inter;color:#8793a3}@bottom-right{content:counter(page);font:600 8pt Inter;color:#003366}}
@page :first{margin:0;@bottom-left{content:none}@bottom-right{content:none}}
*{box-sizing:border-box}
html{font:9.6pt/1.5 Inter,sans-serif;color:var(--ink)}
body{margin:0}
h1{font-size:20pt;letter-spacing:-.02em;color:var(--azul);margin:0 0 .3em;padding-bottom:.25em;border-bottom:3px solid var(--azul2)}
h2{font-size:12.5pt;color:var(--azul);margin:1.3em 0 .35em;break-after:avoid}
h3{font-size:10.3pt;color:var(--azul2);margin:1.1em 0 .25em;break-after:avoid}
p{margin:.45em 0}
ul,ol{margin:.4em 0;padding-left:1.25em}li{margin:.15em 0}
code{font:400 .88em var(--mono);background:var(--soft);padding:.05em .3em;border-radius:3px;color:#0a3a6b}
section.sec{break-before:page}
.lead{font-size:10.6pt;color:#33425a}
table{width:100%;border-collapse:collapse;margin:.6em 0;font-size:8.3pt;break-inside:auto}
th,td{border:1px solid var(--line);padding:.32em .5em;text-align:left;vertical-align:top}
th{background:var(--azul);color:#fff;font-weight:600;font-size:7.8pt;letter-spacing:.03em}
tbody tr:nth-child(even){background:#f6f9fc}
tr{break-inside:avoid}
td code{font-size:.9em}
figure{margin:.7em 0;break-inside:avoid}
figure.shot img{width:100%;display:block;border:1px solid var(--line);border-radius:5px}
figcaption{font-size:8.6pt;font-weight:600;color:var(--azul);margin-top:.3em;text-align:left}
.wrap{position:relative}
.mk{position:absolute;width:6mm;height:6mm;margin:-3mm 0 0 -3mm;border-radius:50%;background:#c62828;color:#fff;font:700 9pt/6mm Inter;text-align:center;border:1.6px solid #fff;box-shadow:0 1px 4px #0007}
ol.mirar{list-style:none;margin:.35em 0 0;padding:0;display:grid;grid-template-columns:1fr 1fr;gap:.2em 4mm;font-size:8.6pt}
ol.mirar li{display:flex;gap:2mm;align-items:flex-start;margin:0}
ol.mirar .n{flex:0 0 5mm;height:5mm;border-radius:50%;background:#c62828;color:#fff;font:700 8pt/5mm Inter;text-align:center;margin-top:.1mm}
.duo{display:grid;grid-template-columns:1fr 1fr;gap:3mm}.duo figure{width:100%!important}
figure.term{background:#0b1622;border-radius:6px;overflow:hidden}
.termtit{background:#16263a;color:#9db4cf;font:600 7.2pt Inter;padding:.35em .8em;letter-spacing:.04em}
figure.term pre{margin:0;padding:.6em .8em;color:#cfe0f2;font:400 6.9pt/1.45 var(--mono);white-space:pre-wrap;word-break:break-all}
.cmd{color:#7fd1ff;font-weight:600}
.nota{border-left:4px solid var(--azul2);background:var(--soft);padding:.5em .8em;margin:.7em 0;border-radius:0 5px 5px 0;font-size:9pt;break-inside:avoid}
.nota.ok{border-color:var(--ok);background:var(--okc)}.nota.al{border-color:var(--al);background:var(--alc)}.nota.no{border-color:var(--no);background:var(--noc)}
.pill{display:inline-block;padding:.02em .5em;border-radius:99px;font-size:7.6pt;font-weight:600;white-space:nowrap}
.pill.ok{background:var(--okc);color:var(--ok)}.pill.no{background:var(--noc);color:var(--no)}.pill.al{background:var(--alc);color:var(--al)}.pill.mut{background:var(--soft);color:var(--azul2)}
.cover{height:297mm;background:linear-gradient(160deg,#002a55,#0a4d8c);color:#fff;padding:26mm 22mm;display:flex;flex-direction:column;justify-content:space-between;position:relative;overflow:hidden;break-after:page}
.cover::before{content:"";position:absolute;inset:0;background:linear-gradient(#ffffff0d 1px,transparent 1px) 0 0/100% 12mm,linear-gradient(90deg,#ffffff0d 1px,transparent 1px) 0 0/12mm 100%;mask:linear-gradient(120deg,#000,transparent 80%)}
.cover>*{position:relative}
.cover .lg{display:flex;align-items:center;gap:4mm;font-weight:800;font-size:17pt;letter-spacing:.14em}
.cover .eslo{font-size:9pt;font-weight:600;letter-spacing:.16em;text-transform:uppercase;opacity:.75;margin-bottom:6mm}
.cover h1{color:#fff;border:0;font-size:34pt;line-height:1.05;letter-spacing:-.03em;font-weight:800;max-width:150mm}
.cover p{opacity:.85;max-width:130mm;font-size:11.5pt}
.cover .foot{font-size:9pt;opacity:.8;line-height:1.6}
.toc{margin-top:4mm}.toc .row{display:flex;gap:2mm;align-items:baseline;padding:1.1mm 0;border-bottom:1px dotted var(--line);font-size:10pt}
.toc .row b{color:var(--azul);min-width:8mm}.toc .row .t{flex:1}.toc .row .p{font-weight:700;color:var(--azul)}
.toc .row.sub{padding-left:8mm;font-size:8.8pt;color:var(--mut)}
.small{font-size:8pt;color:var(--mut)}
svg text{font-family:Inter,sans-serif}
"""
