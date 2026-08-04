"""Control C4 — textos completos del subconjunto relevante (Paper A).

    python control_textos.py

La limitacion declarada del diseno es que el corpus son titulos: un item
podria enganchar con el regimen europeo en su cuerpo sin decirlo en el
titulo. Este script cierra esa exposicion hasta donde las fuentes lo
permiten:

  1. Recupera el texto completo de los 609 items relevantes por dos rutas
     publicas: la pagina de proyectos de la Camara (textoCompleto.jsp) y el
     PDF del Tramite Parlamentario (www4.hcdn.gob.ar). Los archivos quedan
     cacheados en corpus/textos_full/ y no se re-descargan.
  2. Pasa un screen deterministico de dos niveles sobre los textos:
       tier 1  mencion directa del regimen (EUDR, Reglamento 2023/1115,
               libre de deforestacion, EUTR 995/2010, Pacto Verde,
               diligencia debida UE) MAS un patron de co-ocurrencia
               europa~deforestacion a 250 caracteres.
       tier 2  referencia generica a la UE / mercado de destino, solo para
               lectura experta de consistencia.
  3. Reporta cobertura por dominio y anio, enumera los items sin texto y
     escribe los contextos de cada hit para revision manual.

PROXY declarado: HCDN229905 (0910-D-2019) es "REPRODUCCION DEL EXPEDIENTE
3900-D-17" segun su propio titulo; se le imputa el texto de HCDN202544.

Los items sin texto recuperable se enumeran con su anio de presentacion:
casi todos son anteriores a la propuesta del reglamento (nov-2021) y no
podrian citarlo.

Salidas en paper_A/analisis/: textos_cobertura.csv, textos_screen.csv,
textos_contextos.txt
"""

import csv
import re
import time
import unicodedata
import urllib.request
from collections import Counter
from pathlib import Path

import fitz  # PyMuPDF

BASE = Path(__file__).resolve().parents[1]
HCDN = Path(__file__).resolve().parents[3] / "2026_2_" / "app" / "data" / "raw" / "hcdn"
CACHE = BASE / "corpus" / "textos_full"
OUT = BASE / "analisis"

UA = {"User-Agent": "Mozilla/5.0 (investigacion academica)"}
PROXIES = {"HCDN229905": "HCDN202544"}  # reproduccion del 3900-D-17

TIER1 = {
    "eudr_sigla": r"\beudr\b",
    "reglamento_1115": r"1115[/ ]?2023|2023[/ ]?1115",
    "libre_deforestacion": r"libres? de deforestacion|deforestacion cero|cero deforestacion|deforestation[- ]free",
    "eutr": r"\beutr\b|995[/ ]?2010|2010[/ ]?995",
    "reglamento_madera_ue": r"reglamento.{0,30}madera.{0,30}(union europea|ue\b)",
    "diligencia_debida_ue": r"diligencia debida.{0,80}(union europea|europe|importad)",
    "pacto_verde": r"pacto verde|green deal",
    "coocurrencia_eu_defo": r"(europ|union europea|\bue\b).{0,250}deforestac|deforestac.{0,250}(europ|union europea|\bue\b)",
}
TIER2 = {
    "union_europea": r"union europea|\bue\b|\bu\.e\.\b",
    "europeo_generico": r"europe[oa]s?\b|\beuropa\b|bruselas",
    "mercado_exigencia_ext": r"mercados? (externo|internacional|de destino|de exportacion)|barrera (comercial|paraarancelaria|para-arancelaria)|certificacion (internacional|de exportacion)",
    "mercosur_acuerdo": r"mercosur.{0,60}(union europea|acuerdo de asociacion)|acuerdo.{0,30}mercosur",
}


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type", "")


def try_html(exp, tipo):
    url = f"https://www.hcdn.gob.ar/proyectos/textoCompleto.jsp?exp={exp}&tipo={tipo}"
    try:
        body, _ = fetch(url)
        if "No se encontr" in body.decode("utf-8", errors="replace"):
            return None
        return body
    except Exception:
        return None


def try_pdf(exp):
    anio = exp.split("-")[-1]
    url = (f"https://www4.hcdn.gob.ar/dependencias/dsecretaria/"
           f"Periodo{anio}/PDF{anio}/TP{anio}/{exp}.pdf")
    try:
        body, ctype = fetch(url)
        if "pdf" in ctype.lower() and len(body) > 2000:
            return body
    except Exception:
        pass
    return None


def normalizar(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower())


def texto_html(raw):
    html = None
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            html = raw.decode(enc)
            if "�" not in html:
                break
        except UnicodeDecodeError:
            continue
    html = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", " ", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    for ent, ch in [("&aacute;", "a"), ("&eacute;", "e"), ("&iacute;", "i"),
                    ("&oacute;", "o"), ("&uacute;", "u"), ("&ntilde;", "n"),
                    ("&nbsp;", " "), ("&quot;", '"'), ("&amp;", "&")]:
        html = html.replace(ent, ch)
    return html


def texto_pdf(path):
    return " ".join(page.get_text() for page in fitz.open(path))


def hits(texto, dic):
    return {k: len(re.findall(pat, texto)) for k, pat in dic.items() if re.search(pat, texto)}


def contextos(texto, dic, ancho=160):
    frags = []
    for k, pat in dic.items():
        for m in list(re.finditer(pat, texto))[:5]:
            a, b = max(0, m.start() - ancho), min(len(texto), m.end() + ancho)
            frags.append(f"[{k}] ...{texto[a:b]}...")
    return frags


def worklist():
    """Los 609 relevantes con expediente, dominio y marco (para el D)."""
    marco = {r["proyecto_id"]: r["marco_manual"]
             for r in csv.DictReader(open(BASE / "gold" / "marco_D_manual.csv", encoding="utf-8"))}
    screen = [r for r in csv.DictReader(open(BASE / "corpus" / "etapa1_screen_final.csv", encoding="utf-8"))
              if r["relevante"].lower() == "true"]
    ids = {r["proyecto_id"] for r in screen}
    meta = {}
    with open(HCDN / "proyectos_parlamentarios.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["proyecto_id"] in ids:
                meta[r["proyecto_id"]] = r
    rows = []
    for r in screen:
        m = meta.get(r["proyecto_id"], {})
        rows.append({
            "proyecto_id": r["proyecto_id"], "anio": r["anio"], "tipo": r["tipo"],
            "dominio": r["dominio"], "marco": marco.get(r["proyecto_id"], ""),
            "exp": m.get("exp_diputados", ""),
        })
    return rows


def recuperar(rows):
    CACHE.mkdir(exist_ok=True)
    out = []
    for i, r in enumerate(rows):
        pid, exp, tipo = r["proyecto_id"], r["exp"], r["tipo"]
        html_f, pdf_f = CACHE / f"{pid}.html", CACHE / f"{pid}.pdf"
        ruta = "ninguna"
        if html_f.exists():
            ruta = "html"
        elif pdf_f.exists():
            ruta = "pdf"
        elif exp and exp != "NA":
            body = try_html(exp, tipo if tipo in ("LEY", "RESOLUCION", "DECLARACION") else "LEY")
            if body:
                html_f.write_bytes(body)
                ruta = "html"
            else:
                time.sleep(0.4)
                body = try_pdf(exp)
                if body:
                    pdf_f.write_bytes(body)
                    ruta = "pdf"
            time.sleep(0.4)
        if ruta == "ninguna" and pid in PROXIES:
            ruta = "reproduccion"
        out.append({**r, "ruta": ruta})
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(rows)}", flush=True)
    return out


def cargar_texto(pid, ruta):
    if ruta == "reproduccion":
        pid = PROXIES[pid]
        ruta = "html" if (CACHE / f"{pid}.html").exists() else "pdf"
    f = CACHE / f"{pid}.{'html' if ruta == 'html' else 'pdf'}"
    if not f.exists():
        return None
    return texto_html(f.read_bytes()) if ruta == "html" else texto_pdf(f)


def main():
    rows = worklist()
    print(f"worklist: {len(rows)} items relevantes")
    rows = recuperar(rows)

    res, ctx = [], []
    for r in rows:
        texto = cargar_texto(r["proyecto_id"], r["ruta"]) if r["ruta"] != "ninguna" else None
        if texto is None:
            res.append({**r, "chars": 0, "tier1": "", "tier2": ""})
            continue
        t = normalizar(texto)
        h1, h2 = hits(t, TIER1), hits(t, TIER2)
        res.append({**r, "chars": len(t),
                    "tier1": ";".join(f"{k}:{v}" for k, v in h1.items()),
                    "tier2": ";".join(f"{k}:{v}" for k, v in h2.items())})
        if h1:
            ctx.append(f"\n{'=' * 80}\n{r['proyecto_id']} {r['exp']} {r['tipo']} {r['anio']} "
                       f"dominio={r['dominio']} marco={r['marco']} ruta={r['ruta']}")
            ctx += contextos(t, {k: TIER1[k] for k in h1})

    OUT.mkdir(exist_ok=True)
    with open(OUT / "textos_cobertura.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["proyecto_id", "anio", "tipo", "dominio", "marco", "exp", "ruta", "chars"])
        w.writeheader()
        w.writerows([{k: r[k] for k in w.fieldnames} for r in res])
    with open(OUT / "textos_screen.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(res[0].keys()))
        w.writeheader()
        w.writerows(res)
    (OUT / "textos_contextos.txt").write_text("\n".join(ctx), encoding="utf-8")

    con_texto = [r for r in res if r["chars"]]
    print(f"\ncobertura: {len(con_texto)}/{len(res)} "
          f"({100 * len(con_texto) / len(res):.1f}%)  rutas: {Counter(r['ruta'] for r in res)}")
    for dom in "DABC":
        sub = [r for r in res if r["dominio"] == dom]
        ok = sum(1 for r in sub if r["chars"])
        print(f"  dominio {dom}: {ok}/{len(sub)}")

    t1 = [r for r in con_texto if r["tier1"]]
    print(f"\ntier 1 ({len(t1)} items):")
    for r in t1:
        print(f"  {r['proyecto_id']} {r['exp']} dominio={r['dominio']} marco={r['marco']} -> {r['tier1']}")
    dom_d_t2 = [r for r in con_texto if r["dominio"] == "D" and r["marco"] == "domestico" and r["tier2"] and not r["tier1"]]
    print(f"\ndomesticos con tier 2 y sin tier 1: {len(dom_d_t2)}")

    sin = [r for r in res if not r["chars"]]
    print(f"\nsin texto: {len(sin)}")
    for r in sorted(sin, key=lambda x: (x["dominio"], x["anio"])):
        print(f"  {r['proyecto_id']} {r['exp']} {r['tipo']} {r['anio']} dominio={r['dominio']} marco={r['marco']}")


if __name__ == "__main__":
    main()
