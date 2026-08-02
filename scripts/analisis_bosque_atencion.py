# -*- coding: utf-8 -*-
"""Atencion legislativa vs perdida real de bosque, por provincia.

    python analisis_bosque_atencion.py

Escribe analisis/bosque_atencion.csv. En el CUERPO del paper entra solo el
contraste Santiago del Estero / Misiones (~110 palabras en la seccion de las
dos periferias); la tabla completa va al suplementario S10. Decision del
2-ago-2026: el argumento central no depende de este dato, que entra como
corroboracion externa y no como segunda linea argumental.

Fuentes:
  nealab/neahub/pipeline/output/eudr/hires/eudr_ar_res7.parquet
      189.105 hexagonos H3 res-7, 10 provincias forestales argentinas.
      Hansen GFC v1.13 (2001-2025) + MapBiomas AR Col.2. Perdida post-2020,
      que es la fecha de corte de la EUDR.
  .../eudr_plantation_res7.parquet
      Cobertura nativo / plantacion / sabana en 2020 y actual. Solo 4 provincias
      (Chaco, Corrientes, Formosa, Misiones), pero son las que permiten separar
      cosecha de plantacion de deforestacion de nativo.
  paper_A/analisis/geografia.csv y panel_legislador_anio.csv

Nota metodologica central: la perdida Hansen NO es deforestacion. En Misiones
el 94% de la perdida post-2020 es rotacion de plantacion; solo el 5,7%
corresponde a retroceso de bosque nativo. Usar Hansen crudo invertiria el
sentido del hallazgo.
"""

import csv
from pathlib import Path

import pandas as pd

import os

# Capas forestales externas, no redistribuidas aqui. Ver el README,
# seccion "External data sources". Apuntar EUDR_DIR al directorio que las
# contiene, o dejarlas en ./external/eudr.
EUDR = Path(os.environ.get("EUDR_DIR", "./external/eudr"))
BASE = Path(__file__).resolve().parent
HEX_KM2 = 5.1613  # area media del hexagono H3 res-7

NOMBRE = {"ar_salta": "SALTA", "ar_santiago_del_estero": "SANTIAGO DEL ESTERO",
          "ar_chaco": "CHACO", "ar_catamarca": "CATAMARCA", "ar_corrientes": "CORRIENTES",
          "ar_entre_ríos": "ENTRE RIOS", "ar_formosa": "FORMOSA", "ar_jujuy": "JUJUY",
          "ar_misiones": "MISIONES", "ar_tucumán": "TUCUMAN"}


def atencion(paper_a: Path):
    """relevantes, dominio D y banca-anios por distrito (incluye los de cero)."""
    geo = {r["unidad"]: r for r in csv.DictReader(
        open(paper_a / "analisis" / "geografia.csv", encoding="utf-8"))
        if r["nivel"] == "distrito"}
    panel = pd.read_csv(paper_a / "analisis" / "panel_legislador_anio.csv")
    ba = panel.groupby("distrito")["exposure"].sum()
    return geo, ba


def main(paper_a: Path):
    geo, ba = atencion(paper_a)

    loss = pd.read_parquet(EUDR / "eudr_ar_res7.parquet",
                           columns=["h3index", "province", "loss_post_2020_pct",
                                    "forest_cover_2020"])
    loss["hansen_km2"] = loss["loss_post_2020_pct"] / 100 * HEX_KM2

    pl = pd.read_parquet(EUDR / "eudr_plantation_res7.parquet")
    m = loss.merge(pl.drop(columns=["province"]), on="h3index", how="left")
    for col, src in [("nat2020", "native_2020_pct"), ("nat_now", "native_forest_pct"),
                     ("pl2020", "plantation_2020_pct"), ("pl_now", "plantation_pct")]:
        m[col + "_km2"] = m[src] / 100 * HEX_KM2

    r = m.groupby("province").agg(
        hansen=("hansen_km2", "sum"),
        nat2020=("nat2020_km2", "sum"), nat_now=("nat_now_km2", "sum"),
        pl2020=("pl2020_km2", "sum"), pl_now=("pl_now_km2", "sum")).reset_index()
    r["distrito"] = r["province"].map(NOMBRE)
    r["nativo_perdido_km2"] = r["nat2020"] - r["nat_now"]
    r["pct_nativo_perdido"] = 100 * r["nativo_perdido_km2"] / r["nat2020"]
    r["nativo_sobre_hansen"] = 100 * r["nativo_perdido_km2"] / r["hansen"]
    # la capa de plantacion cubre solo 4 provincias: el resto queda NaN a proposito
    r.loc[r["nat2020"] < 100, ["nativo_perdido_km2", "pct_nativo_perdido",
                               "nativo_sobre_hansen"]] = pd.NA

    r["relevantes"] = r["distrito"].map(lambda d: int(geo[d]["relevantes"]) if d in geo else 0)
    r["dom_D"] = r["distrito"].map(lambda d: int(geo[d]["dom_D"]) if d in geo else 0)
    r["banca_anios"] = r["distrito"].map(lambda d: ba.get(d, float("nan")))
    r["rel_100ba"] = 100 * r["relevantes"] / r["banca_anios"]
    r["D_100ba"] = 100 * r["dom_D"] / r["banca_anios"]

    cols = ["distrito", "hansen", "nativo_perdido_km2", "pct_nativo_perdido",
            "nativo_sobre_hansen", "banca_anios", "relevantes", "dom_D",
            "rel_100ba", "D_100ba"]
    out = r.sort_values("hansen", ascending=False)[cols]
    pd.set_option("display.width", 200)
    print(out.to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
    destino = paper_a / "analisis" / "bosque_atencion.csv"
    out.to_csv(destino, index=False, float_format="%.2f")
    print(f"\n-> {destino}")

    print("\nSpearman sobre las 10 provincias forestales (descriptivo, n=10):")
    for v in ["relevantes", "dom_D", "rel_100ba", "D_100ba"]:
        print(f"  perdida Hansen post-2020 vs {v:11}: "
              f"rho = {r['hansen'].corr(r[v], method='spearman'):+.3f}")
    sub = r.dropna(subset=["nativo_perdido_km2"])
    print(f"\nSolo las 4 provincias con separacion nativo/plantacion (n={len(sub)}):")
    for v in ["relevantes", "dom_D", "rel_100ba", "D_100ba"]:
        print(f"  perdida de NATIVO vs {v:11}: "
              f"rho = {sub['nativo_perdido_km2'].corr(sub[v], method='spearman'):+.3f}")
    return out


if __name__ == "__main__":
    main(Path(__file__).resolve().parents[1])
