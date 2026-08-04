"""Figure 1 del manuscrito — serie de atencion (Paper A, seccion 4.1).

    python fig1_attention_series.py

Lee analisis/serie_atencion.csv, escribe manuscript/figures/Figure_1.png.

Version de manuscrito de figura_serie_atencion.py (que queda como exploratoria
en espanol). Diferencias: etiquetas en ingles, sin titulo embebido (el caption
vive en el .md), 300 dpi.

ESTANDAR TIPOGRAFICO DE LAS FIGURAS DEL ARTICULO — toda figura nueva lo respeta
(el style guide exige tamanos y nombres de categoria identicos entre figuras):
    etiquetas de eje 10 pt · ticks 9 pt · leyenda 9 pt · anotaciones 8 pt
    tinta #444444 · grilla #e6e6e6 · sin spines superior ni derecho
    nombres de dominio: los de ETIQUETAS, sin abreviar ni reordenar

PALETA — validada, no elegida a ojo. `validate_palette.js --mode light` sobre
#1f5c99,#c25e1e,#3f8f5f,#c9a227 devuelve ALL CHECKS PASS (banda de luminosidad,
piso de croma, separacion CVD 8,0 deutan, piso de vision normal 19,5). Dos
salvedades que obligan a encoding secundario, y por eso van las TRAMAS:
  (1) la separacion CVD 8,0 cae en la banda piso 6-8, legal solo con encoding
      secundario;
  (2) en ESCALA DE GRISES los dominios B y C quedan en luminancia 0,191 y
      0,204, practicamente indistinguibles — y la revista cobra GBP 300 por
      figura a color impresa, asi que la version en grises es la probable.
La trama resuelve ambas. El WARN de contraste de #c9a227 (2,36) queda cubierto
por las etiquetas directas sobre las barras.
"""

import csv
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parents[1]
SERIE = BASE / "analisis" / "serie_atencion.csv"
MARCO = BASE / "analisis" / "marco_items.csv"
DESTINO = BASE / "manuscript" / "figures" / "Figure_1.png"

COLORES = {"A": "#1f5c99", "B": "#c25e1e", "C": "#3f8f5f", "D": "#c9a227"}
TRAMAS = {"A": "", "B": "///", "C": "...", "D": "xxx"}
ETIQUETAS = {"A": "A  Explicit agreement", "B": "B  Sectoral trade with the EU",
             "C": "C  Mercosur as an institution",
             "D": "D  Forest and traceability regulation"}
TINTA = "#444444"
HITOS = {2010: "Madrid summit", 2016: "exchange of offers",
         2019: "political agreement", 2024: "close of negotiations"}
DESTACAR = {2010, 2012, 2014, 2023, 2024}

PT_EJE, PT_TICK, PT_LEYENDA, PT_ANOT = 10, 9, 9, 8


def main():
    with open(SERIE, encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    anios = [int(r["anio"]) for r in filas]

    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(9, 6.5),
                                   height_ratios=[2, 1])
    fig.subplots_adjust(hspace=0.12)

    plt.rcParams["hatch.linewidth"] = 0.6
    base = [0] * len(filas)
    for dom in "ABCD":
        vals = [int(r[f"dom_{dom}"]) for r in filas]
        # el borde blanco es el separador de 2 px entre segmentos apilados
        ax1.bar(anios, vals, bottom=base, width=0.75, color=COLORES[dom],
                edgecolor="white", linewidth=1.4, hatch=TRAMAS[dom],
                label=ETIQUETAS[dom])
        base = [b + v for b, v in zip(base, vals)]
    for a, total in zip(anios, base):
        if a in DESTACAR:
            # 2010 y 2024 caen sobre una linea de hito y la etiqueta queda
            # partida al medio: se corren a la izquierda de la linea.
            dx = -9 if a in HITOS else 0
            ax1.annotate(str(total), (a, total), textcoords="offset points",
                         xytext=(dx, 3), ha="center", fontsize=PT_ANOT, color=TINTA)

    # Panel inferior: cuanto del dominio D engancha realmente con el regimen
    # europeo. Es el panel que sostiene el argumento de ausencia.
    marco = defaultdict(Counter)
    with open(MARCO, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["dominio"] == "D":
                marco[int(r["anio"])][r["marco"]] += 1
    # Tres estratos, no dos: mostrar solo "regimen vs resto" ensena la ausencia
    # pero esconde la otra mitad del argumento, que el resto es domestico.
    # Gris #8a8a8a para el estrato externo: en grises queda en luminancia
    # intermedia entre el oro (claro) y el borgona (oscuro), y no toca la
    # paleta categorica validada del panel superior.
    dom_dom = [marco[a]["domestico"] for a in anios]
    dom_ext = [marco[a]["externo"] + marco[a]["ue_otro"] for a in anios]
    dom_eudr = [marco[a]["eudr"] for a in anios]

    ax2.bar(anios, dom_dom, width=0.75, color=COLORES["D"], edgecolor="white",
            linewidth=1.4, hatch=TRAMAS["D"],
            label="No external referent (domestic instruments)")
    ax2.bar(anios, dom_ext, bottom=dom_dom, width=0.75, color="#8a8a8a",
            edgecolor="white", linewidth=1.4, hatch="\\\\\\",
            label="External referent, not the European regime")
    base_eudr = [d + e for d, e in zip(dom_dom, dom_ext)]
    ax2.bar(anios, dom_eudr, bottom=base_eudr, width=0.75, color="#8c1d1d",
            edgecolor="white", linewidth=1.4,
            label="Engaging the EU deforestation regime")
    for a, b, e in zip(anios, base_eudr, dom_eudr):
        if e:
            ax2.annotate(str(e), (a, b + e), textcoords="offset points",
                         xytext=(0, 3), ha="center", fontsize=PT_ANOT,
                         color="#8c1d1d", fontweight="bold")
    ax2.set_ylabel("Domain D items", fontsize=PT_EJE, color=TINTA)
    ax2.legend(fontsize=PT_LEYENDA, frameon=False, loc="upper left",
               labelcolor=TINTA)
    ax2.margins(y=0.30)

    for ax in (ax1, ax2):
        for a in HITOS:
            ax.axvline(a, color="#999999", linestyle="--", linewidth=0.8, zorder=0)
        ax.grid(axis="y", color="#e6e6e6", linewidth=0.6, zorder=0)
        ax.set_axisbelow(True)
        for lado in ("top", "right"):
            ax.spines[lado].set_visible(False)
        ax.tick_params(colors=TINTA, labelsize=PT_TICK)
    # 2016 y 2019 estan a tres anios: las etiquetas se pisan en una sola linea
    for i, (a, txt) in enumerate(sorted(HITOS.items())):
        ax1.annotate(txt, (a, 1.0), xycoords=("data", "axes fraction"),
                     xytext=(0, 4 + 12 * (i % 2)), textcoords="offset points",
                     ha="center", va="bottom", fontsize=PT_ANOT, color="#777777")

    # Los anios electorales iban con triangulos grises sin relleno sobre la
    # linea del eje: se pisaban con las etiquetas rotadas y desaparecian en
    # impresion. Van en la propia etiqueta de anio, en negrita, que sobrevive
    # la escala de grises y no agrega un elemento que colisione.
    electorales = {a for a in anios if a % 2 == 1}

    ax1.set_ylabel("Relevant items", fontsize=PT_EJE, color=TINTA)
    ax1.legend(fontsize=PT_LEYENDA, frameon=False, loc="upper right",
               labelcolor=TINTA)
    ax1.margins(y=0.18)  # aire para las anotaciones de hito
    ax2.set_xticks(anios)
    ax2.set_xticklabels(anios, rotation=45)
    for etiqueta, a in zip(ax2.get_xticklabels(), anios):
        if a in electorales:
            etiqueta.set_fontweight("bold")
            etiqueta.set_color("#111111")

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(DESTINO, dpi=300, bbox_inches="tight", facecolor="white")
    print(f"-> {DESTINO}")


if __name__ == "__main__":
    main()
