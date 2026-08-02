"""Analisis seccion 4.5 — Paper A (modelos de conteo sobre panel legislador-anio).

    python analisis_seccion45.py

Formaliza los tres hallazgos descriptivos de la seccion 4:
  M1  conteo de proyectos relevantes ~ fase del ciclo + anio electoral +
      familia + region + gobierno  (Poisson, offset log(exposure), SE cluster
      por diputado; NB como robustez si hay sobredispersion)
  M2  mismo modelo restringido al dominio D (trazabilidad/forestal)
  M3  logit a nivel proyecto: P(orientacion no-neutra) ~ gobierno + familia +
      fase  (SE cluster por diputado)

Salidas en paper_A/analisis/: panel_legislador_anio.csv, modelos_seccion45.txt.
Lenguaje: asociacion; registro observacional, sin identificacion causal.
"""

import csv
import unicodedata
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

BASE = Path(__file__).resolve().parents[1]
HCDN = Path(__file__).resolve().parents[3] / "2026_2_" / "app" / "data" / "raw" / "hcdn"
OUT = BASE / "analisis"

FASES = {**{a: "f1_impasse" for a in range(2008, 2010)},
         **{a: "f2_relanzamiento" for a in range(2010, 2016)},
         **{a: "f3_reactivacion" for a in range(2016, 2020)},
         **{a: "f4_paralisis" for a in range(2020, 2024)},
         **{a: "f5_cierre" for a in range(2024, 2026)}}
PRESIDENCIA_ANIO = {**{a: "cfk" for a in range(2008, 2016)},
                    **{a: "macri" for a in range(2016, 2020)},
                    **{a: "fernandez" for a in range(2020, 2024)},
                    **{a: "milei" for a in range(2024, 2026)}}
GOBIERNO = {"cfk": {"kirchnerismo"}, "macri": {"pro", "ucr", "cc_ari"},
            "fernandez": {"kirchnerismo"}, "milei": {"lla"}}
REGIONES = {
    "NEA": {"MISIONES", "CORRIENTES", "CHACO", "FORMOSA"},
    "NOA": {"JUJUY", "SALTA", "TUCUMAN", "CATAMARCA", "SANTIAGO DEL ESTERO", "LA RIOJA"},
    "CUYO": {"MENDOZA", "SAN JUAN", "SAN LUIS"},
    "PAMPEANA": {"BUENOS AIRES", "CORDOBA", "SANTA FE", "ENTRE RIOS", "LA PAMPA"},
    "PATAGONIA": {"NEUQUEN", "RIO NEGRO", "CHUBUT", "SANTA CRUZ", "TIERRA DEL FUEGO"},
    "CABA": {"CIUDAD DE BUENOS AIRES"},
}
DISTRITO_REGION = {d: r for r, ds in REGIONES.items() for d in ds}
FAMILIAS_M3 = {"kirchnerismo", "ucr", "pro", "peronismo_federal"}  # resto -> otras


def norm(s):
    s = unicodedata.normalize("NFD", (s or "").upper().strip())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", s)


def solape_dias(ini, fin, a, b):
    lo, hi = max(ini, a), min(fin, b)
    return max(0.0, (pd.Timestamp(hi) - pd.Timestamp(lo)).days + 1)


def fecha_valida(v):
    v = (v or "")[:10]
    return v if v and v[0].isdigit() else ""


def main():
    familias = {norm(r["bloque"]): r["familia"]
                for r in csv.DictReader(open(OUT / "bloques_familias.csv", encoding="utf-8"))}
    # bloques mixtos: integrantes con partido propio inequivoco (PS, GEN)
    # se asignan a su familia partidaria por diputado_id
    overrides = {r["diputado_id"]: r["familia"]
                 for r in csv.DictReader(open(OUT / "familia_overrides.csv", encoding="utf-8"))}

    with open(HCDN / "diputados.csv", encoding="utf-8-sig", newline="") as f:
        estadias = list(csv.DictReader(f))
    for s in csv.DictReader(open(OUT / "diputados_supl_2005_2009.csv", encoding="utf-8")):
        estadias.append({"id": s["id"], "apellido": s["apellido"], "nombre": s["nombre"],
                         "distrito": s["distrito"], "inicio": s["inicio"], "fin": s["fin"],
                         "bloque": s["bloque"], "bloque_inicio": s["inicio"],
                         "bloque_fin": s["fin"]})

    por_id = defaultdict(list)
    for e in estadias:
        por_id[e["id"]].append(e)

    join = list(csv.DictReader(open(OUT / "autores_join.csv", encoding="utf-8")))
    dip_join = [r for r in join if r["categoria"] == "diputado"]
    conteo = defaultdict(int)
    conteo_d = defaultdict(int)
    for r in dip_join:
        clave = (r["diputado_id"], int(r["fecha"][:4]))
        conteo[clave] += 1
        if r["dominio"] == "D":
            conteo_d[clave] += 1

    # ---------- panel legislador-anio ----------
    filas = []
    sin_familia = set()
    for did, es in por_id.items():
        # servicio efectivo por mandato nominal: reemplazos juran tarde, las
        # renuncias cesan antes (dedup por (inicio, fin))
        mandatos = {}
        for e in es:
            k = (e["inicio"][:10], e["fin"][:10])
            jura = fecha_valida(e.get("juramento"))
            cese = fecha_valida(e.get("cese"))
            mandatos[k] = (max(k[0], jura or k[0]), min(k[1], cese or k[1]))
        for anio in range(2008, 2026):
            a0, a1 = f"{anio}-01-01", f"{anio}-12-31"
            dias = sum(solape_dias(i, f, a0, a1) for i, f in mandatos.values())
            if dias <= 0:
                continue
            # estadia de bloque con mayor solape en el anio
            mejor = max(es, key=lambda e: solape_dias(e["bloque_inicio"][:10],
                                                      e["bloque_fin"][:10], a0, a1))
            familia = overrides.get(did) or familias.get(norm(mejor["bloque"]), "")
            if not familia:  # micro-bloques sin mapear caen a 'otros'
                sin_familia.add(mejor["bloque"])
                familia = "otros"
            pres = PRESIDENCIA_ANIO[anio]
            filas.append({
                "diputado_id": did, "anio": anio,
                "exposure": round(dias / 365.25, 4),
                "familia": familia, "distrito": mejor["distrito"],
                "region": DISTRITO_REGION.get(mejor["distrito"], ""),
                "fase": FASES[anio], "electoral": int(anio % 2 == 1),
                "gobierno": int(familia in GOBIERNO[pres]),
                "n_rel": conteo.get((did, anio), 0),
                "n_rel_d": conteo_d.get((did, anio), 0),
            })
    if sin_familia:
        print(f"AVISO bloques sin mapear (caen a 'otros'): {len(sin_familia)}")
    panel = pd.DataFrame(filas)
    panel.to_csv(OUT / "panel_legislador_anio.csv", index=False)
    print(f"Panel: {len(panel)} legislador-anios, {panel['diputado_id'].nunique()} diputados, "
          f"{panel['exposure'].sum():.0f} banca-anios, {panel['n_rel'].sum()} proyectos")
    asignados = sum(conteo.values())
    print(f"  proyectos en panel vs join: {panel['n_rel'].sum()} / {asignados}")
    en_panel = {(r["diputado_id"], r["anio"]) for r in filas}
    perdidos = {k: v for k, v in conteo.items() if k not in en_panel}
    if perdidos:
        print(f"  AVISO conteos sin fila de panel (proyecto fuera de la ventana "
              f"de servicio del autor): {perdidos}")

    informe = []

    def registrar(titulo, res, irr=True):
        informe.append("=" * 78)
        informe.append(titulo)
        informe.append(str(res.summary()))
        if irr:
            tabla = pd.DataFrame({"IRR": np.exp(res.params),
                                  "IC95_lo": np.exp(res.conf_int()[0]),
                                  "IC95_hi": np.exp(res.conf_int()[1]),
                                  "p": res.pvalues}).round(3)
            informe.append("IRR (exp(beta)) con IC95:\n" + tabla.to_string())

    # ---------- M1: conteo total ----------
    formula = ("n_rel ~ C(fase, Treatment('f1_impasse')) + electoral + "
               "C(familia, Treatment('kirchnerismo')) + "
               "C(region, Treatment('PAMPEANA')) + gobierno")
    m1 = smf.glm(formula, data=panel, family=sm.families.Poisson(),
                 offset=np.log(panel["exposure"])).fit(
        cov_type="cluster", cov_kwds={"groups": panel["diputado_id"]})
    disp = m1.pearson_chi2 / m1.df_resid
    registrar(f"M1 Poisson conteo total (dispersion Pearson/gl = {disp:.2f})", m1)

    # robustez NB si hay sobredispersion
    if disp > 1.5:
        m1nb = smf.glm(formula, data=panel,
                       family=sm.families.NegativeBinomial(alpha=1.0),
                       offset=np.log(panel["exposure"])).fit(
            cov_type="cluster", cov_kwds={"groups": panel["diputado_id"]})
        registrar("M1b Binomial Negativa (robustez, alpha=1)", m1nb)

    # ---------- M2: dominio D ----------
    m2 = smf.glm(formula.replace("n_rel", "n_rel_d"), data=panel,
                 family=sm.families.Poisson(),
                 offset=np.log(panel["exposure"])).fit(
        cov_type="cluster", cov_kwds={"groups": panel["diputado_id"]})
    registrar(f"M2 Poisson dominio D (dispersion = {m2.pearson_chi2 / m2.df_resid:.2f})", m2)

    # M2b: el caso extremo descriptivo (Misiones) como dummy de distrito
    panel["misiones"] = (panel["distrito"] == "MISIONES").astype(int)
    m2b = smf.glm(formula.replace("n_rel", "n_rel_d")
                  .replace("C(region, Treatment('PAMPEANA'))", "misiones"),
                  data=panel, family=sm.families.Poisson(),
                  offset=np.log(panel["exposure"])).fit(
        cov_type="cluster", cov_kwds={"groups": panel["diputado_id"]})
    registrar("M2b Poisson dominio D con dummy Misiones (en vez de region)", m2b)

    # ---------- M3: logit no-neutra a nivel proyecto ----------
    proy = pd.DataFrame(dip_join)
    proy["no_neutra"] = (proy["orientacion"] != "administrativa_neutra").astype(int)
    proy["fase"] = proy["fecha"].str[:4].astype(int).map(FASES)
    proy["gobierno_num"] = (proy["gobierno"] == "si").astype(int)
    proy["familia_m3"] = proy["familia"].where(proy["familia"].isin(FAMILIAS_M3), "otras")
    m3 = smf.glm("no_neutra ~ gobierno_num + C(familia_m3, Treatment('kirchnerismo')) + "
                 "C(fase, Treatment('f2_relanzamiento'))",
                 data=proy, family=sm.families.Binomial()).fit(
        cov_type="cluster", cov_kwds={"groups": proy["diputado_id"]})
    registrar(f"M3 logit no-neutra a nivel proyecto (N = {len(proy)}, "
              f"no-neutras = {proy['no_neutra'].sum()}) — coef en OR", m3)

    (OUT / "modelos_seccion45.txt").write_text("\n".join(informe), encoding="utf-8")
    print(f"-> {OUT / 'modelos_seccion45.txt'}")

    # sintesis rapida en consola
    print("\nM1 - IRR de fases (ref: impasse 2008-09) y electoral:")
    for k in m1.params.index:
        if "fase" in k or k == "electoral":
            print(f"  {k:55s} IRR {np.exp(m1.params[k]):5.2f}  p={m1.pvalues[k]:.3f}")
    print("\nM2 (dominio D) - IRR de regiones (ref: PAMPEANA) y M2b Misiones:")
    for k in m2.params.index:
        if "region" in k:
            print(f"  {k:55s} IRR {np.exp(m2.params[k]):5.2f}  p={m2.pvalues[k]:.3f}")
    print(f"  {'misiones (M2b)':55s} IRR {np.exp(m2b.params['misiones']):5.2f}"
          f"  p={m2b.pvalues['misiones']:.3f}")
    print("\nM3 - OR de gobierno y familias (ref: kirchnerismo):")
    for k in m3.params.index:
        if k != "Intercept" and "fase" not in k:
            print(f"  {k:55s} OR {np.exp(m3.params[k]):5.2f}  p={m3.pvalues[k]:.3f}")


if __name__ == "__main__":
    main()
