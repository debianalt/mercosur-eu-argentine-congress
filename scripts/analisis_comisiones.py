"""Analisis de giro a comisiones — Paper A (desplazamiento institucional).

    python analisis_comisiones.py

El cuerpo del paper muestra que el OBJETO de la atencion cambia (comercio
sectorial -> trazabilidad). Este script pregunta si ademas cambia el LUGAR de
la Camara donde ese objeto se procesa: a que comisiones se giran los proyectos
de cada dominio, y si el perfil de giro se desplaza entre la primera y la
segunda mitad del periodo.

Es una segunda medicion, independiente de la codificacion tematica, del mismo
fenomeno: si los items de trazabilidad se giran a comisiones distintas de las
que recibian los de comercio sectorial, el desplazamiento es institucional y no
solo tematico.

Salidas en paper_A/analisis/:
  comisiones_dominio.csv   comision x dominio (giro primero y todos los giros)
  comisiones_periodo.csv   comision x periodo (2008-2015 / 2016-2025)
  informe_comisiones.md    sintesis legible con los numeros que cita el paper
"""

import csv
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
HCDN = Path(__file__).resolve().parents[3] / "2026_2_" / "app" / "data" / "raw" / "hcdn"
OUT = BASE / "analisis"

DOMINIOS = {"A": "acuerdo explicito", "B": "comercio sectorial",
            "C": "Mercosur institucional", "D": "trazabilidad y forestal"}

# agrupamiento tematico de comisiones, para leer el desplazamiento sin ruido de
# nomenclatura. Se aplica por coincidencia de subcadena sobre el nombre normalizado.
GRUPOS = [
    ("Relaciones exteriores y Mercosur", ["RELACIONES EXTERIORES", "MERCOSUR"]),
    ("Agricultura y ganaderia", ["AGRICULTURA", "GANADERIA"]),
    ("Recursos naturales y ambiente", ["RECURSOS NATURALES", "AMBIENTE", "ECOLOGIA"]),
    ("Comercio e industria", ["COMERCIO", "INDUSTRIA", "PYME", "PEQUENAS Y MEDIANAS"]),
    ("Presupuesto y hacienda", ["PRESUPUESTO", "HACIENDA", "FINANZAS"]),
    ("Economia y trabajo", ["ECONOMIA", "TRABAJO", "OBRAS PUBLICAS", "TRANSPORTE",
                            "ENERGIA", "COMBUSTIBLES", "INFRAESTRUCTURA"]),
]


def load(path, encoding="utf-8-sig"):
    with open(path, encoding=encoding, newline="") as f:
        return list(csv.DictReader(f))


def grupo(comision):
    c = (comision or "").upper()
    for nombre, claves in GRUPOS:
        if any(k in c for k in claves):
            return nombre
    return "Otras"


def tabla(contador, total):
    filas = []
    for k, n in contador.most_common():
        filas.append({"clave": k, "n": n,
                      "pct": round(100 * n / total, 1) if total else 0.0})
    return filas


def main():
    corpus = load(BASE / "corpus" / "etapa1_screen_final.csv", encoding="utf-8")
    rel = [r for r in corpus if r["relevante"] == "true"]
    dominio = {r["proyecto_id"]: r["dominio"] for r in rel}
    anio = {r["proyecto_id"]: int(r["publicacion_fecha"][:4]) for r in rel}
    tipo = {r["proyecto_id"]: r["tipo"] for r in rel}
    print(f"Relevantes: {len(rel)}")

    giros = defaultdict(list)
    for r in load(HCDN / "giro_comisiones.csv"):
        giros[r["proyecto_id"]].append((int(r["orden"]), r["comision"]))
    for pid in giros:
        giros[pid].sort()

    # cobertura: no todo item se gira (las DECLARACION sobre tablas, p. ej.)
    con_giro = [p for p in dominio if giros.get(p)]
    print(f"Con al menos un giro: {len(con_giro)} ({100*len(con_giro)/len(rel):.1f}%)")
    por_tipo = Counter(tipo[p] for p in dominio if not giros.get(p))
    print(f"Sin giro, por tipo: {dict(por_tipo)}")

    # ---------- comision de primer giro, por dominio ----------
    primero_dom = defaultdict(Counter)
    todos_dom = defaultdict(Counter)
    grupo_dom = defaultdict(Counter)
    n_dom = Counter()
    for pid in con_giro:
        d = dominio[pid]
        n_dom[d] += 1
        primero_dom[d][giros[pid][0][1]] += 1
        grupo_dom[d][grupo(giros[pid][0][1])] += 1
        for _, c in giros[pid]:
            todos_dom[d][c] += 1

    filas = []
    for d in sorted(primero_dom):
        for f in tabla(primero_dom[d], n_dom[d]):
            filas.append({"dominio": d, "etiqueta": DOMINIOS.get(d, d),
                          "nivel": "comision_primer_giro", "clave": f["clave"],
                          "n": f["n"], "pct": f["pct"], "base": n_dom[d]})
        for f in tabla(grupo_dom[d], n_dom[d]):
            filas.append({"dominio": d, "etiqueta": DOMINIOS.get(d, d),
                          "nivel": "grupo_primer_giro", "clave": f["clave"],
                          "n": f["n"], "pct": f["pct"], "base": n_dom[d]})
    with open(OUT / "comisiones_dominio.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["dominio", "etiqueta", "nivel", "clave",
                                          "n", "pct", "base"])
        w.writeheader()
        w.writerows(filas)

    # ---------- perfil de giro por periodo ----------
    cortes = [("2008-2015", 2008, 2015), ("2016-2025", 2016, 2025)]
    filas_p = []
    for nombre, a0, a1 in cortes:
        ids = [p for p in con_giro if a0 <= anio[p] <= a1]
        cnt = Counter(grupo(giros[p][0][1]) for p in ids)
        for f in tabla(cnt, len(ids)):
            filas_p.append({"periodo": nombre, "clave": f["clave"], "n": f["n"],
                            "pct": f["pct"], "base": len(ids)})
    with open(OUT / "comisiones_periodo.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["periodo", "clave", "n", "pct", "base"])
        w.writeheader()
        w.writerows(filas_p)

    # ---------- informe ----------
    inf = ["# Giro a comisiones — desplazamiento institucional", "",
           f"Relevantes: {len(rel)}. Con al menos un giro registrado: {len(con_giro)} "
           f"({100*len(con_giro)/len(rel):.1f}%).", "",
           "Los items sin giro son mayoritariamente DECLARACION tratadas sobre tablas "
           "y MENSAJE del ejecutivo.", "",
           "## Grupo de comision del primer giro, por dominio", ""]
    grupos_orden = [g for g, _ in GRUPOS] + ["Otras"]
    encabezado = "| Grupo de comision | " + " | ".join(
        f"{d} ({n_dom[d]})" for d in sorted(n_dom)) + " |"
    inf.append(encabezado)
    inf.append("|" + "---|" * (len(n_dom) + 1))
    for g in grupos_orden:
        celdas = []
        for d in sorted(n_dom):
            n = grupo_dom[d][g]
            celdas.append(f"{n} ({100*n/n_dom[d]:.0f}%)" if n_dom[d] else "0")
        inf.append(f"| {g} | " + " | ".join(celdas) + " |")

    inf += ["", "## Comisiones concretas mas frecuentes (primer giro)", ""]
    for d in sorted(primero_dom):
        top = ", ".join(f"{c} ({n})" for c, n in primero_dom[d].most_common(4))
        inf.append(f"- **{d} — {DOMINIOS.get(d, d)}** (n = {n_dom[d]}): {top}")

    inf += ["", "## Perfil de primer giro por periodo", "",
            "| Grupo | 2008-2015 | 2016-2025 |", "|---|---|---|"]
    p1 = {f["clave"]: f for f in filas_p if f["periodo"] == "2008-2015"}
    p2 = {f["clave"]: f for f in filas_p if f["periodo"] == "2016-2025"}
    b1 = p1[next(iter(p1))]["base"] if p1 else 0
    b2 = p2[next(iter(p2))]["base"] if p2 else 0
    for g in grupos_orden:
        a = p1.get(g, {"n": 0, "pct": 0.0})
        b = p2.get(g, {"n": 0, "pct": 0.0})
        inf.append(f"| {g} | {a['n']} ({a['pct']}%) | {b['n']} ({b['pct']}%) |")
    inf.append(f"| **Base** | **{b1}** | **{b2}** |")

    # El perfil agregado esta dominado por C (institucional), que va casi
    # siempre a Relaciones Exteriores en los dos periodos. El desplazamiento se
    # lee limpio restringiendo a los dominios sustantivos B y D.
    inf += ["", "## Perfil de primer giro, solo dominios B y D", "",
            "El agregado esta dominado por C, que va a Relaciones Exteriores en "
            "los dos periodos. Restringido a los dominios sustantivos:", "",
            "| Grupo | 2008-2015 | 2016-2025 |", "|---|---|---|"]
    bd = [p for p in con_giro if dominio[p] in ("B", "D")]
    c1 = Counter(grupo(giros[p][0][1]) for p in bd if anio[p] <= 2015)
    c2 = Counter(grupo(giros[p][0][1]) for p in bd if anio[p] >= 2016)
    t1, t2 = sum(c1.values()), sum(c2.values())
    for g in grupos_orden:
        a1v = f"{c1[g]} ({100*c1[g]/t1:.1f}%)" if t1 else "0"
        a2v = f"{c2[g]} ({100*c2[g]/t2:.1f}%)" if t2 else "0"
        inf.append(f"| {g} | {a1v} | {a2v} |")
    inf.append(f"| **Base** | **{t1}** | **{t2}** |")

    # composicion B/D por periodo, que es lo que mueve el perfil
    for nombre, lo, hi in [("2008-2015", 2008, 2015), ("2016-2025", 2016, 2025)]:
        nb = sum(1 for p in bd if lo <= anio[p] <= hi and dominio[p] == "B")
        nd = sum(1 for p in bd if lo <= anio[p] <= hi and dominio[p] == "D")
        inf.append(f"\n{nombre}: B = {nb}, D = {nd}")

    # numero de giros por dominio (complejidad institucional del item)
    inf += ["", "## Cantidad de comisiones por item", ""]
    for d in sorted(n_dom):
        ng = [len(giros[p]) for p in con_giro if dominio[p] == d]
        inf.append(f"- **{d}**: media {sum(ng)/len(ng):.2f} comisiones por item "
                   f"(max {max(ng)})")

    (OUT / "informe_comisiones.md").write_text("\n".join(inf) + "\n", encoding="utf-8")
    print(f"-> {OUT / 'comisiones_dominio.csv'}")
    print(f"-> {OUT / 'comisiones_periodo.csv'}")
    print(f"-> {OUT / 'informe_comisiones.md'}")

    print("\nGrupo de primer giro por dominio (%):")
    for d in sorted(n_dom):
        print(f"  {d} (n={n_dom[d]}): " + ", ".join(
            f"{g} {100*grupo_dom[d][g]/n_dom[d]:.0f}%"
            for g in grupos_orden if grupo_dom[d][g]))


if __name__ == "__main__":
    main()
