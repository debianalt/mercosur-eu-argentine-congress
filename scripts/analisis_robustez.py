"""Robustez de los modelos de conteo — Paper A.

    python analisis_robustez.py

El estimador de Misiones en el dominio D (IRR 3,42; IC95 [1,04 - 11,26];
p = 0,043) descansa en 30 items y su intervalo roza el 1. Este script somete
ese resultado, y el de Patagonia, a las especificaciones alternativas que un
revisor va a pedir:

  R1  excluir DECLARACION (el tipo mas barato de presentar)
  R2  efectos fijos de anio (absorbe el ciclo negociador y el calendario
      electoral sin imponerles forma funcional)
  R3  binomial negativa (la dispersion no la exige, pero es el reflejo del
      revisor ante un modelo de conteo)
  R4  errores estandar cluster por distrito en vez de por diputado (la
      variacion de interes es provincial)

Salida: paper_A/analisis/robustez_seccion45.txt
"""

import csv
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "analisis"

BASE_FORMULA = ("{y} ~ C(fase, Treatment('f1_impasse')) + electoral + "
                "C(familia, Treatment('kirchnerismo')) + {geo} + gobierno")

# la familia partidaria ya entra en BASE_FORMULA; el termino de izquierda
# progresista es el mayor del modelo forestal y el cuerpo lo reporta, asi que
# tiene que pasar por la misma bateria que el resto de las estimaciones.
TERM_IZQ = "C(familia, Treatment('kirchnerismo'))[T.izquierda_progresista]"


def irr(res, termino):
    if termino not in res.params.index:
        return None
    lo, hi = res.conf_int().loc[termino]
    return (float(np.exp(res.params[termino])), float(np.exp(lo)),
            float(np.exp(hi)), float(res.pvalues[termino]))


def fmt(v):
    if v is None:
        return "     —                              "
    e, lo, hi, p = v
    return f"IRR {e:5.2f}  IC95 [{lo:5.2f}, {hi:6.2f}]  p = {p:.3f}"


def ajustar(panel, y, geo, familia, cluster="diputado_id", extra=""):
    f = BASE_FORMULA.format(y=y, geo=geo) + extra
    return smf.glm(f, data=panel, family=familia,
                   offset=np.log(panel["exposure"])).fit(
        cov_type="cluster", cov_kwds={"groups": panel[cluster]})


def main():
    panel = pd.read_csv(OUT / "panel_legislador_anio.csv")
    panel["misiones"] = (panel["distrito"] == "MISIONES").astype(int)
    panel["patagonia"] = (panel["region"] == "PATAGONIA").astype(int)

    # conteos sin DECLARACION: se recomputan desde el join de autores
    join = list(csv.DictReader(open(OUT / "autores_join.csv", encoding="utf-8")))
    dip = [r for r in join if r["categoria"] == "diputado"]
    sin_decl = {}
    for r in dip:
        if r["tipo"] == "DECLARACION":
            continue
        k = (r["diputado_id"], int(r["fecha"][:4]))
        sin_decl[k] = sin_decl.get(k, 0) + (1 if r["dominio"] == "D" else 0)
    panel["n_rel_d_sin_decl"] = [
        sin_decl.get((str(d), int(a)), 0)
        for d, a in zip(panel["diputado_id"], panel["anio"])]

    poisson = sm.families.Poisson()
    negbin = sm.families.NegativeBinomial(alpha=1.0)
    geo_reg = "C(region, Treatment('PAMPEANA'))"

    lineas = ["=" * 78,
              "ROBUSTEZ — dominio D (trazabilidad y regulacion forestal)",
              "=" * 78, "",
              f"Panel: {len(panel)} legislador-anios; "
              f"items D = {int(panel['n_rel_d'].sum())}; "
              f"sin DECLARACION = {int(panel['n_rel_d_sin_decl'].sum())}", ""]

    especificaciones = [
        ("Base (la del cuerpo)", "n_rel_d", poisson, "", "diputado_id"),
        ("R1 sin DECLARACION", "n_rel_d_sin_decl", poisson, "", "diputado_id"),
        ("R2 efectos fijos de anio", "n_rel_d", poisson, " + C(anio)", "diputado_id"),
        ("R3 binomial negativa", "n_rel_d", negbin, "", "diputado_id"),
        ("R4 cluster por distrito", "n_rel_d", poisson, "", "distrito"),
    ]

    for etiqueta, y, fam, extra, cluster in especificaciones:
        # Misiones entra como dummy que reemplaza al termino regional; Patagonia
        # se lee de la especificacion regional. Son dos modelos por fila.
        nota = ""
        try:
            m_mis = ajustar(panel, y, "misiones", fam, cluster, extra)
            v_mis = irr(m_mis, "misiones")
        except Exception as e:                                   # noqa: BLE001
            v_mis = None
            nota = (f"  [Misiones no estimable: {e} — con efectos fijos de anio "
                    f"y un evento raro, los anios sin items D quedan sin "
                    f"variacion y el ajuste no converge]")
        try:
            m_reg = ajustar(panel, y, geo_reg, fam, cluster, extra)
            v_pat = irr(m_reg, "C(region, Treatment('PAMPEANA'))[T.PATAGONIA]")
            v_nea = irr(m_reg, "C(region, Treatment('PAMPEANA'))[T.NEA]")
            v_izq = irr(m_reg, TERM_IZQ)
        except Exception as e:                                   # noqa: BLE001
            v_pat = v_nea = v_izq = None
            nota += f"\n  [region no estimable: {e}]"
        lineas += [f"--- {etiqueta} ---",
                   f"  Misiones   {fmt(v_mis)}",
                   f"  Patagonia  {fmt(v_pat)}",
                   f"  NEA        {fmt(v_nea)}",
                   f"  Izq.progr. {fmt(v_izq)}"]
        if nota:
            lineas.append(nota)
        lineas.append("")

    # el efecto electoral del modelo de todos los dominios, misma bateria
    lineas += ["=" * 78,
               "ROBUSTEZ — ano electoral (todos los dominios, M1)",
               "=" * 78, ""]
    for etiqueta, fam, extra, cluster in [
            ("Base (la del cuerpo)", poisson, "", "diputado_id"),
            ("R3 binomial negativa", negbin, "", "diputado_id"),
            ("R4 cluster por distrito", poisson, "", "distrito")]:
        m = ajustar(panel, "n_rel", geo_reg, fam, cluster, extra)
        lineas.append(f"  {etiqueta:28s} electoral  {fmt(irr(m, 'electoral'))}")
        lineas.append(f"  {'':28s} gobierno   {fmt(irr(m, 'gobierno'))}")
        lineas.append(f"  {'':28s} izq.progr. {fmt(irr(m, TERM_IZQ))}")

    texto = "\n".join(lineas) + "\n"
    (OUT / "robustez_seccion45.txt").write_text(texto, encoding="utf-8")
    print(texto)
    print(f"-> {OUT / 'robustez_seccion45.txt'}")


if __name__ == "__main__":
    main()
