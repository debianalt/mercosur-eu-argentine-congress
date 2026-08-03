"""Marco de referencia externo vs domestico — Paper A (reencuadre 3-ago-2026).

    python analisis_marco.py

El paper pasa a sostener una AUSENCIA: el regimen europeo de deforestacion casi
no aparece en el registro legislativo argentino, mientras la agenda forestal de
la Camara corre por motores domesticos. Esa afirmacion necesita una medicion,
y esta es.

Sobre los 609 relevantes se aplica una clasificacion determinista de marco:

  eudr       engancha con el regimen europeo de deforestacion: nombra el
             Reglamento 2023/1115, la exigencia de producto libre de
             deforestacion, o el aparato de cumplimiento para exportar a la UE
  ue_otro    nombra la UE o el acuerdo por otra via (cuota Hilton, biodiesel,
             disputas comerciales), sin ser del regimen de deforestacion
  externo    engancha con mercado externo, exportacion, trazabilidad con
             destino comercial o el bloque, sin nombrar la UE
  domestico  sin referente externo alguno: instrumentos argentinos
             (Ley 26.331, OTBN, Fondo Fiduciario, desmontes, incendios)

La clasificacion tiene dos capas. La regla lexica corre sobre los 609 y es
auditable. Sobre el dominio D, que es el que carga la afirmacion central, los
152 items fueron ademas codificados a mano contra la definicion conceptual de
cada marco (gold/marco_D_manual.csv, con nota de adjudicacion por item donde
la lectura difiere). El codigo final es el humano en D y el de la regla en el
resto; el informe reporta el acuerdo entre ambas capas (porcentaje y kappa de
Cohen) y la lista completa de desacuerdos con su razon.

Resultado de la codificacion manual (3-ago-2026): los items que enganchan con
el regimen europeo son TRES, no cinco. Los dos que la regla asignaba por
aparato caen con evidencia documental: el registro de establecimientos
proveedores de la UE es anterior al regimen (ue_otro), y la trazabilidad
individual electronica (Res. SAGyP 71/2024) se fundo en demandas de
consumidores globales y sanidad, sin mencion del Reglamento 2023/1115
(externo). El informe emite la lista completa de los items `eudr`.

Salidas en paper_A/analisis/:
  marco_items.csv        los 609 con su marco final y el de la regla
  marco_externos.csv     solo explicitos y externos, para revision del autor
  informe_marco.md       las cifras que cita el paper
"""

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "analisis"

# NUCLEO DE LA AFIRMACION DE AUSENCIA: items que enganchan con el regimen
# europeo de deforestacion. Deliberadamente estrecho y auditable a ojo: el
# informe emite la lista completa, que cabe en media pagina.
EUDR = re.compile(
    r"2023/1115|EUDR"
    r"|REGLAMENTO.{0,80}DEFORESTACION|DEFORESTACION.{0,80}(UNION EUROPEA|MERCADO DE LA UNION)"
    r"|LIBRE DE DEFORESTACION|DEFORESTACION IMPORTADA"
    r"|REGISTRO DE ESTABLECIMIENTOS RURALES.{0,140}UNION EUROPEA"
    r"|TRAZABILIDAD INDIVIDUAL ELECTRONICA"
)
# nombra la UE o el acuerdo, sin ser del regimen de deforestacion
REGIMEN = re.compile(
    r"UNION EUROPEA|COMUNIDAD EUROPEA|\bUE\b|EUROPE"
    r"|ACUERDO .{0,25}MERCOSUR.{0,25}(UNION EUROPEA|UE)\b"
)
# engancha con lo externo sin nombrar el regimen
EXTERNO = re.compile(
    r"MERCOSUR|EXPORTA|IMPORTA|COMERCIO EXTERIOR|ARANCEL|ADUANA|CUOTA HILTON"
    r"|CUOTA 481|ANTIDUMPING|OMC|ORGANIZACION MUNDIAL DE COMERCIO|MERCADO EXTERNO"
    r"|TRAZABILIDAD|CERTIFICACION|BIODIESEL|BIOCOMBUSTIBLE"
)
# marcadores inequivocos de instrumento domestico
DOMESTICO = re.compile(
    r"LEY 26\.?331|ORDENAMIENTO TERRITORIAL DE BOSQUES|\bOTBN\b|DESMONTE"
    r"|PRESUPUESTOS MINIMOS|FONDO FIDUCIARIO|FONDO NACIONAL|INCENDIO"
    r"|REGIMEN SANCIONATORIO|REGIMEN PENAL"
)

DOMINIOS = {"A": "explicit agreement", "B": "sectoral trade with the EU",
            "C": "Mercosur as an institution", "D": "traceability and forest regulation"}


def marco(titulo):
    t = titulo.upper()
    if EUDR.search(t):
        return "eudr"
    if REGIMEN.search(t):
        return "ue_otro"
    if EXTERNO.search(t):
        return "externo"
    return "domestico"


def kappa_cohen(pares):
    """Kappa de Cohen sin ponderar sobre pares (codigo_a, codigo_b)."""
    n = len(pares)
    cats = sorted({c for par in pares for c in par})
    po = sum(1 for a, b in pares if a == b) / n
    ma = Counter(a for a, _ in pares)
    mb = Counter(b for _, b in pares)
    pe = sum(ma[c] * mb[c] for c in cats) / (n * n)
    return (po - pe) / (1 - pe)


def main():
    rel = [r for r in csv.DictReader(
        open(BASE / "corpus" / "etapa1_screen_final.csv", encoding="utf-8"))
        if r["relevante"] == "true"]
    print(f"Relevantes: {len(rel)}")

    for r in rel:
        r["marco_regla"] = marco(r["titulo"])
        r["anio"] = int(r["publicacion_fecha"][:4])

    # ---------- capa manual sobre el dominio D ----------
    manual = {r["proyecto_id"]: r for r in csv.DictReader(
        open(BASE / "gold" / "marco_D_manual.csv", encoding="utf-8"))}
    ids_D = {r["proyecto_id"] for r in rel if r["dominio"] == "D"}
    assert ids_D == set(manual), (
        f"gold/marco_D_manual.csv no cubre exactamente el dominio D: "
        f"faltan {ids_D - set(manual)}, sobran {set(manual) - ids_D}")
    for pid, m in manual.items():
        assert m["marco_regla"] == next(
            r["marco_regla"] for r in rel if r["proyecto_id"] == pid), \
            f"{pid}: el codigo de regla registrado no coincide con la regex vigente"

    for r in rel:
        r["marco"] = (manual[r["proyecto_id"]]["marco_manual"]
                      if r["dominio"] == "D" else r["marco_regla"])

    pares = [(manual[p]["marco_regla"], manual[p]["marco_manual"]) for p in sorted(ids_D)]
    acuerdo = sum(1 for a, b in pares if a == b)
    kappa = kappa_cohen(pares)
    desacuerdos = [manual[p] for p in sorted(ids_D)
                   if manual[p]["marco_regla"] != manual[p]["marco_manual"]]

    with open(OUT / "marco_items.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["proyecto_id", "anio", "tipo", "dominio",
                                          "saliencia", "marco", "marco_regla",
                                          "titulo"],
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(rel, key=lambda r: (r["anio"], r["dominio"])))

    externos = [r for r in rel if r["marco"] != "domestico"]
    with open(OUT / "marco_externos.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["proyecto_id", "anio", "tipo", "dominio",
                                          "marco", "titulo"], extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(externos, key=lambda r: (r["anio"],)))

    # ---------- cifras ----------
    cruz = defaultdict(Counter)
    for r in rel:
        cruz[r["dominio"]][r["marco"]] += 1
    marcos = ["eudr", "ue_otro", "externo", "domestico"]

    inf = ["# Marco de referencia: externo vs domestico", "",
           f"Dos capas sobre los {len(rel)} relevantes: regla lexica en todo el "
           "corpus, y codificacion manual del autor sobre los 152 del dominio D "
           "(`gold/marco_D_manual.csv`). El codigo final es el manual en D y el "
           "de la regla en el resto.", "",
           f"**Acuerdo regla-manual en D: {acuerdo}/{len(pares)} "
           f"({100*acuerdo/len(pares):.1f}%), kappa de Cohen = {kappa:.3f}.**", "",
           "## Desacuerdos, con su razon", ""]
    for d in desacuerdos:
        inf.append(f"- **{d['proyecto_id']}** ({d['anio']}, {d['tipo']}): "
                   f"{d['marco_regla']} -> **{d['marco_manual']}**. {d['nota']}")
    inf += ["", "## Marco por dominio (codigo final)", "",
           "| Dominio | " + " | ".join(marcos) + " | total |", "|" + "---|" * (len(marcos) + 2)]
    for d in sorted(cruz):
        tot = sum(cruz[d].values())
        celdas = " | ".join(f"{cruz[d][m]} ({100*cruz[d][m]/tot:.0f}%)" for m in marcos)
        inf.append(f"| {d} — {DOMINIOS[d]} | {celdas} | {tot} |")
    tot_g = Counter()
    for d in cruz:
        tot_g.update(cruz[d])
    inf.append("| **Total** | " + " | ".join(
        f"**{tot_g[m]}** ({100*tot_g[m]/len(rel):.0f}%)" for m in marcos)
        + f" | **{len(rel)}** |")

    # el dominio D es el que decide el argumento
    D = [r for r in rel if r["dominio"] == "D"]
    d_ext = [r for r in D if r["marco"] != "domestico"]
    inf += ["", "## El dominio D, que es donde se juega el argumento", "",
            f"- Total: {len(D)}",
            f"- Con algun marco externo: {len(d_ext)} ({100*len(d_ext)/len(D):.0f}%)",
            f"- Puramente domestico: {len(D)-len(d_ext)} "
            f"({100*(len(D)-len(d_ext))/len(D):.0f}%)",
            f"- Que enganchan con el regimen europeo de deforestacion: "
            f"{sum(1 for r in D if r['marco']=='eudr')}", ""]

    # serie anual del enganche real con el regimen
    inf += ["## Serie anual: items que nombran el regimen europeo", "",
            "| Anio | " + " | ".join(marcos) + " | total |",
            "|" + "---|" * (len(marcos) + 2)]
    por_anio = defaultdict(Counter)
    for r in rel:
        por_anio[r["anio"]][r["marco"]] += 1
    for a in sorted(por_anio):
        c = por_anio[a]
        inf.append(f"| {a} | " + " | ".join(str(c[m]) for m in marcos)
                   + f" | {sum(c.values())} |")

    inf += ["", "## Todos los items que enganchan con el regimen europeo de deforestacion", ""]
    for r in sorted((r for r in rel if r["marco"] == "eudr"),
                    key=lambda r: r["anio"]):
        inf.append(f"- [{r['anio']} · {r['dominio']} · {r['tipo']}] {r['titulo']}")

    (OUT / "informe_marco.md").write_text("\n".join(inf) + "\n", encoding="utf-8")
    print(f"-> {OUT / 'marco_items.csv'}")
    print(f"-> {OUT / 'marco_externos.csv'}")
    print(f"-> {OUT / 'informe_marco.md'}")

    print("\nMarco por dominio:")
    for d in sorted(cruz):
        tot = sum(cruz[d].values())
        print(f"  {d}: " + ", ".join(f"{m} {cruz[d][m]} ({100*cruz[d][m]/tot:.0f}%)"
                                     for m in marcos))
    print(f"\nTotal: " + ", ".join(f"{m} {tot_g[m]}" for m in marcos))


if __name__ == "__main__":
    main()
