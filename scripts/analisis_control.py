"""Series de control — Paper A (la sustitucion, contra que se compara).

    python analisis_control.py

El cuerpo sostiene que sobre el eje UE-Mercosur el comercio sectorial sale del
registro y la trazabilidad lo reemplaza. Un revisor preguntara si cada mitad de
ese movimiento no es simplemente una tendencia general de la Camara. Este
script construye las dos series de control que responden eso:

  C1 bosque domestico   items cuyo titulo menciona bosque / desmonte /
                        deforestacion / forestal y que NO pertenecen al eje.
                        Si la atencion forestal domestica sube en paralelo al
                        dominio D, parte de lo que el paper atribuye al eje es
                        politica forestal interna.
  C2 comercio exterior  items de comercio exterior sin vinculo con la UE.
                        Si la atencion al comercio exterior cae en general, la
                        desaparicion del dominio B no es especifica del eje.
  C3 destinos no-UE     items que nombran un mercado de destino no europeo Y la
                        exportacion hacia el. Responde la objecion mas peligrosa
                        contra el hallazgo central: si la Camara no tramitara
                        NINGUNA exigencia regulatoria extranjera, la ausencia
                        del regimen europeo hablaria de la Camara y no del
                        regimen. Se reporta ademas el subconjunto que engancha
                        con un requisito o una restriccion del destino, que es
                        el analogo directo del EUDR.

Ambas se miden por screen deterministico sobre los 110.500 titulos, con la
misma normalizacion por volumen anual de la Camara que usa la serie principal.

LIMITACION que hay que declarar: las series de control son de keyword, no de
codificacion humana. Miden titulos que mencionan el tema, no items sobre el
tema. Sirven para comparar TRAYECTORIAS, porque el instrumento es el mismo en
todos los anios, no para medir niveles.

Salidas en paper_A/analisis/: series_control.csv, informe_control.md
"""

import csv
import re
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
HCDN = Path(__file__).resolve().parents[3] / "2026_2_" / "app" / "data" / "raw" / "hcdn"
OUT = BASE / "analisis"

# C1: atencion forestal domestica. Deliberadamente generoso.
FOREST = re.compile(
    r"BOSQUE|DEFORESTA|DESMONTE|FORESTA|MONTE NATIVO|SELVA|YUNGAS"
    r"|ORDENAMIENTO TERRITORIAL DE BOSQUES|LEY 26\.?331"
)
# C2: comercio exterior sin la UE. Se excluyen luego los titulos que nombran
# a la UE o al Mercosur, que son el eje del paper.
COMEX = re.compile(
    r"EXPORTACION|IMPORTACION|COMERCIO EXTERIOR|ARANCEL|ADUANA|ANTIDUMPING"
    r"|DERECHOS? DE EXPORTACION|RETENCIONES|TRATADO DE LIBRE COMERCIO|\bOMC\b"
)
EJE = re.compile(r"MERCOSUR|UNION EUROPEA|COMUNIDAD EUROPEA|\bUE\b|EUROPE")

# C3: mercados de destino no europeos. DESTINO son los compradores efectivos de
# la exportacion argentina fuera de la UE; EXPO exige que el titulo hable de
# exportar hacia ese destino, no de nombrarlo (2.668 titulos lo nombran, casi
# todos por cooperacion, geopolitica o efemerides). REQ marca el subconjunto
# que engancha con una exigencia o una restriccion del destino.
DESTINO = re.compile(
    r"\bCHINA\b|\bCHINO|ESTADOS UNIDOS|\bEE\.?\s?UU\.?\b|\bJAPON\b|JAPONES"
    r"|\bCOREA|\bRUSIA\b|\bRUSA\b|ISRAEL|\bINDIA\b|INDONESIA|TURQUIA|ARABIA"
    r"|EMIRATOS|\bMEXICO\b|CANADA|REINO UNIDO|GRAN BRETA|VIETNAM|MALASIA"
    r"|SUDAFRICA|\bEGIPTO\b|ARGELIA|\bIRAN\b|\bQATAR\b|MARRUECOS|FILIPINAS"
    r"|TAILANDIA|SINGAPUR"
)
EXPO = re.compile(
    r"EXPORTAC|EXPORTAR|EXPORTADOR|ACCESO A(L)? MERCADO|APERTURA DE(L)? MERCADO"
)
REQ = re.compile(
    r"REQUISITO|EXIGENCIA|CERTIFICAC|HABILITACION|BARRERA|TRAZABILIDAD"
    r"|PROTOCOLO SANITARIO|RESTRICCION|SUSPENSION|AUDITORIA|INOCUIDAD"
    r"|ARANCELARI|ANTIDUMPING|SALVAGUARDIA"
)
# Modo de enganche. El punto del control no es cuantos items hay sino COMO
# enganchan: si ninguno trata una exigencia vigente del destino como regla a
# cumplir, la ausencia del regimen europeo no es una rareza europea. El orden
# de evaluacion importa: celebracion primero, porque un beneplacito por una
# autorizacion obtenida menciona la restriccion que se levanto.
CELEBRA = re.compile(r"BENEPLACITO|SATISFACCION|CONGRATUL|RECONOCIMIENTO")
REACCION = re.compile(r"PREOCUPACION|RESTRICCION|SUSPENSION|CIERRE|CONFLICTO"
                      r"|RESTABLECER|IRREGULARIDAD|TRABA")
CONSULTA = re.compile(r"PEDIDO DE INFORMES|INFORMES AL PODER EJECUTIVO")
EJECUTIVO = re.compile(r"COMUNICACION DEL DECRETO|MENSAJE")


def modo(titulo, tipo):
    """Clasifica como engancha el item con el mercado de destino."""
    if CELEBRA.search(titulo):
        return "celebracion"
    if REACCION.search(titulo):
        return "reaccion"
    if CONSULTA.search(titulo):
        return "consulta"
    if EJECUTIVO.search(titulo) or tipo in ("MENSAJE", "LEY"):
        return "ejecutivo_o_norma"
    return "otro"


def load(path, encoding="utf-8-sig"):
    with open(path, encoding=encoding, newline="") as f:
        return list(csv.DictReader(f))


def tasa(n, base):
    return round(1000 * n / base, 2) if base else 0.0


def main():
    corpus = [r for r in load(HCDN / "proyectos_parlamentarios.csv")
              if r.get("titulo") and r.get("proyecto_id")]
    print(f"Corpus: {len(corpus)}")

    rel = [r for r in load(BASE / "corpus" / "etapa1_screen_final.csv", encoding="utf-8")
           if r["relevante"] == "true"]
    eje_ids = {r["proyecto_id"] for r in rel}
    dominio = {r["proyecto_id"]: r["dominio"] for r in rel}
    print(f"Eje (excluidos de los controles): {len(eje_ids)}")

    total = Counter()
    c1 = Counter()
    c2 = Counter()
    c3 = Counter()
    c3_req = Counter()
    solo_destino = 0
    dom_b = Counter()
    dom_d = Counter()
    c3_items = []
    for r in corpus:
        anio = (r.get("publicacion_fecha") or "")[:4]
        if not anio.isdigit() or not (2008 <= int(anio) <= 2025):
            continue
        a = int(anio)
        total[a] += 1
        pid, tit = r["proyecto_id"], r["titulo"].upper()
        if pid in eje_ids:
            if dominio[pid] == "B":
                dom_b[a] += 1
            elif dominio[pid] == "D":
                dom_d[a] += 1
            continue  # los del eje no entran en los controles
        if FOREST.search(tit):
            c1[a] += 1
        if COMEX.search(tit) and not EJE.search(tit):
            c2[a] += 1
        if DESTINO.search(tit) and not EJE.search(tit):
            solo_destino += 1
        if DESTINO.search(tit) and EXPO.search(tit) and not EJE.search(tit):
            c3[a] += 1
            con_req = bool(REQ.search(tit))
            if con_req:
                c3_req[a] += 1
            c3_items.append({
                "anio": a, "proyecto_id": pid, "tipo": r.get("tipo", ""),
                "requisito": "si" if con_req else "no",
                "modo": modo(tit, r.get("tipo", "")),
                "titulo": r["titulo"],
            })

    with open(OUT / "control_destinos.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(c3_items[0]))
        w.writeheader()
        w.writerows(sorted(c3_items, key=lambda x: (x["anio"], x["proyecto_id"])))

    filas = []
    for a in sorted(total):
        filas.append({
            "anio": a, "total_hcdn": total[a],
            "eje_dom_b": dom_b[a], "eje_dom_b_tasa": tasa(dom_b[a], total[a]),
            "eje_dom_d": dom_d[a], "eje_dom_d_tasa": tasa(dom_d[a], total[a]),
            "c1_bosque": c1[a], "c1_bosque_tasa": tasa(c1[a], total[a]),
            "c2_comex": c2[a], "c2_comex_tasa": tasa(c2[a], total[a]),
            "c3_destinos": c3[a], "c3_destinos_req": c3_req[a],
        })
    with open(OUT / "series_control.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)

    def media(cnt, lo, hi, base=None):
        n = sum(cnt[a] for a in range(lo, hi + 1))
        b = sum((base or total)[a] for a in range(lo, hi + 1))
        return n, tasa(n, b)

    tramos = [("2008-2015", 2008, 2015), ("2016-2019", 2016, 2019),
              ("2020-2025", 2020, 2025)]
    inf = ["# Series de control — la sustitucion contra su contrafactico", "",
           "Screen deterministico sobre los 110.500 titulos, excluidos los 609 del eje.",
           "Tasas por 1.000 items presentados en el ano, que es la normalizacion",
           "de la serie principal.", "",
           "**Limitacion**: los controles son de keyword, no de codificacion humana.",
           "Miden titulos que mencionan el tema. Comparan trayectorias, no niveles.", "",
           "| Tramo | D eje (tasa) | C1 bosque domestico (tasa) | B eje (tasa) | C2 comercio ext. (tasa) |",
           "|---|---|---|---|---|"]
    for nombre, lo, hi in tramos:
        nd, td = media(dom_d, lo, hi)
        n1, t1 = media(c1, lo, hi)
        nb, tb = media(dom_b, lo, hi)
        n2, t2 = media(c2, lo, hi)
        inf.append(f"| {nombre} | {nd} ({td}) | {n1} ({t1}) | {nb} ({tb}) | {n2} ({t2}) |")

    inf += ["", "## Serie anual", "",
            "| Anio | total | D eje | tasa D | C1 bosque | tasa C1 | B eje | tasa B | C2 comex | tasa C2 |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for f_ in filas:
        inf.append("| {anio} | {total_hcdn} | {eje_dom_d} | {eje_dom_d_tasa} | "
                   "{c1_bosque} | {c1_bosque_tasa} | {eje_dom_b} | {eje_dom_b_tasa} | "
                   "{c2_comex} | {c2_comex_tasa} |".format(**f_))

    n3, n3r = sum(c3.values()), sum(c3_req.values())
    modos = Counter(i["modo"] for i in c3_items)
    ETIQ = {"celebracion": "Celebra un envio o una autorizacion obtenida",
            "reaccion": "Reacciona a una restriccion, suspension o conflicto",
            "consulta": "Pide informes sobre volumenes o una apertura",
            "ejecutivo_o_norma": "Comunicacion de decreto o norma domestica",
            "otro": "Otro"}
    inf += ["", "## C3 — mercados de destino no europeos", "",
            f"Titulos que nombran un destino no-UE Y la exportacion hacia el: "
            f"**{n3}** en 18 anios. Nombran un destino no-UE por cualquier",
            f"motivo: {solo_destino} titulos, casi todos cooperacion, diplomacia",
            "o efemerides; por eso el screen exige ademas que el titulo hable de",
            "exportar hacia ese destino.", "",
            "| Modo de enganche | Items |", "|---|---|"]
    for k, v in modos.most_common():
        inf.append(f"| {ETIQ.get(k, k)} | {v} |")
    inf += [f"| **Total** | **{n3}** |", "",
            f"Nombran una restriccion o exigencia en el titulo: **{n3r}**, ambos",
            "reacciones a un mercado que se cierra. Leidos los 18, ninguno trata",
            "una exigencia del destino como regla a cumplir por la produccion",
            "argentina: el modo es celebratorio o reactivo incluso cuando el",
            "objeto es una habilitacion concedida bajo un requisito extranjero.", "",
            "Ubica la ausencia en vez de disolverla: la Camara SI se ocupa de",
            "mercados de exportacion (69 items de comercio sectorial con la UE,",
            "13 proyectos de ley de trazabilidad, respuesta a los hitos de la",
            "negociacion). Lo que no aparece, para ningun destino, es la",
            "exigencia regulatoria vigente como objeto legislativo.",
            "Detalle item por item en control_destinos.csv."]

    (OUT / "informe_control.md").write_text("\n".join(inf) + "\n", encoding="utf-8")
    print(f"-> {OUT / 'series_control.csv'}")
    print(f"-> {OUT / 'control_destinos.csv'}")
    print(f"-> {OUT / 'informe_control.md'}")
    print(f"\nC3 destinos no-UE: {n3} items, {n3r} con requisito/restriccion; "
          + ", ".join(f"{k} {v}" for k, v in modos.most_common()))

    print("\nTramo            D_eje   C1_bosque   B_eje   C2_comex   (tasas por 1.000)")
    for nombre, lo, hi in tramos:
        _, td = media(dom_d, lo, hi)
        _, t1 = media(c1, lo, hi)
        _, tb = media(dom_b, lo, hi)
        _, t2 = media(c2, lo, hi)
        print(f"{nombre:15s} {td:6.2f} {t1:11.2f} {tb:7.2f} {t2:10.2f}")


if __name__ == "__main__":
    main()
