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
    dom_b = Counter()
    dom_d = Counter()
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

    filas = []
    for a in sorted(total):
        filas.append({
            "anio": a, "total_hcdn": total[a],
            "eje_dom_b": dom_b[a], "eje_dom_b_tasa": tasa(dom_b[a], total[a]),
            "eje_dom_d": dom_d[a], "eje_dom_d_tasa": tasa(dom_d[a], total[a]),
            "c1_bosque": c1[a], "c1_bosque_tasa": tasa(c1[a], total[a]),
            "c2_comex": c2[a], "c2_comex_tasa": tasa(c2[a], total[a]),
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

    (OUT / "informe_control.md").write_text("\n".join(inf) + "\n", encoding="utf-8")
    print(f"-> {OUT / 'series_control.csv'}")
    print(f"-> {OUT / 'informe_control.md'}")

    print("\nTramo            D_eje   C1_bosque   B_eje   C2_comex   (tasas por 1.000)")
    for nombre, lo, hi in tramos:
        _, td = media(dom_d, lo, hi)
        _, t1 = media(c1, lo, hi)
        _, tb = media(dom_b, lo, hi)
        _, t2 = media(c2, lo, hi)
        print(f"{nombre:15s} {td:6.2f} {t1:11.2f} {tb:7.2f} {t2:10.2f}")


if __name__ == "__main__":
    main()
