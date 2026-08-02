"""Validacion y acuerdo del gold standard — Paper A.

    python gold_kappa.py validar   # chequea la codificacion (cobertura, vocabulario, coherencia)
    python gold_kappa.py kappa     # Cohen's kappa codificador vs anotador (correr DESPUES de commitear los codigos)

El kappa de relevancia compara gold_codigos_claude.csv (codificador experto,
ciego) contra gold_clave_modelo.csv (anotador Haiku v1.2). Tema/orientacion/
saliencia no tienen contraparte hasta que corra la etapa 2.
"""

import csv
import sys
from collections import Counter
from pathlib import Path

GOLD = Path(__file__).resolve().parents[1] / "gold"

TEMAS = {"acuerdo_ue_mercosur", "comercio_ue_sectorial", "eudr_trazabilidad_forestal",
         "mercosur_institucional", "otro_descartar", ""}
ORIS = {"pro_liberalizacion", "proteccionista_defensiva", "condicionada",
        "administrativa_neutra", "no_aplica", ""}
SALS = {"explicita", "relacionada", "no_aplica", ""}
DOMS = {"A", "B", "C", "D", "ninguno"}


def load(name):
    with open(GOLD / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def cmd_validar():
    hoja = {r["proyecto_id"]: r for r in load("gold_para_codificar.csv")}
    codigos = load("gold_codigos_claude.csv")
    errores = []
    if len(codigos) != 400:
        errores.append(f"filas: {len(codigos)} != 400")
    vistos = set()
    for r in codigos:
        pid, orden = r["proyecto_id"], r["orden"]
        if pid in vistos:
            errores.append(f"duplicado {pid}")
        vistos.add(pid)
        if pid not in hoja:
            errores.append(f"orden {orden}: {pid} no esta en la hoja")
        elif hoja[pid]["orden"] != orden:
            errores.append(f"orden {orden}: {pid} tiene orden {hoja[pid]['orden']} en la hoja")
        rel = r["relevante_manual"]
        if rel not in ("true", "false"):
            errores.append(f"orden {orden}: relevante '{rel}'")
        if r["dominio_manual"] not in DOMS:
            errores.append(f"orden {orden}: dominio '{r['dominio_manual']}'")
        if r["tema_manual"] not in TEMAS or r["orientacion_manual"] not in ORIS or r["saliencia_manual"] not in SALS:
            errores.append(f"orden {orden}: vocabulario etapa 2 invalido")
        if rel == "true" and (r["dominio_manual"] == "ninguno" or not r["tema_manual"]
                              or not r["orientacion_manual"] or not r["saliencia_manual"]):
            errores.append(f"orden {orden}: positivo incompleto")
        if rel == "false" and (r["dominio_manual"] != "ninguno" or r["tema_manual"]
                               or r["orientacion_manual"] or r["saliencia_manual"]):
            errores.append(f"orden {orden}: negativo con campos de positivo")
    pos = sum(r["relevante_manual"] == "true" for r in codigos)
    flags = sum(r["flag_revision"] == "si" for r in codigos)
    print(f"Codigos: {len(codigos)} filas | positivos {pos} | flags de revision {flags}")
    print(f"Dominios (positivos): {Counter(r['dominio_manual'] for r in codigos if r['relevante_manual'] == 'true')}")
    print(f"Orientacion (positivos): {Counter(r['orientacion_manual'] for r in codigos if r['relevante_manual'] == 'true')}")
    if errores:
        print("\nERRORES:")
        for e in errores:
            print(f"  {e}")
        sys.exit(1)
    print("Validacion OK")


def kappa_cohen(pares):
    n = len(pares)
    acuerdo = sum(a == b for a, b in pares) / n
    ca, cb = Counter(a for a, _ in pares), Counter(b for _, b in pares)
    esperado = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return (acuerdo - esperado) / (1 - esperado), acuerdo


def cmd_kappa():
    codigos = {r["proyecto_id"]: r for r in load("gold_codigos_claude.csv")}
    clave = {r["proyecto_id"]: r for r in load("gold_clave_modelo.csv")}
    pares, detalle = [], []
    for pid, c in codigos.items():
        k = clave.get(pid)
        if not k:
            continue
        a = c["relevante_manual"] == "true"
        b = str(k["relevante"]) == "True"
        pares.append((a, b))
        if a != b:
            detalle.append((pid, c, k))
    kap, acuerdo = kappa_cohen(pares)
    print(f"Relevancia — N = {len(pares)}, acuerdo {100 * acuerdo:.1f}%, Cohen's kappa = {kap:.3f}")
    print(f"Umbral del plan: kappa >= 0,75 -> {'CUMPLE' if kap >= 0.75 else 'NO CUMPLE'}")

    # kappa de dominio sobre los acuerdos positivos
    dom_pares = [(codigos[p]["dominio_manual"], clave[p]["dominio"]) for p in codigos
                 if p in clave and codigos[p]["relevante_manual"] == "true"
                 and str(clave[p]["relevante"]) == "True"]
    if dom_pares:
        kd, ad = kappa_cohen(dom_pares)
        print(f"Dominio (sobre {len(dom_pares)} positivos compartidos) — acuerdo {100 * ad:.1f}%, kappa = {kd:.3f}")

    print(f"\nDesacuerdos de relevancia: {len(detalle)}")
    solo_cod = [(p, c, k) for p, c, k in detalle if c["relevante_manual"] == "true"]
    solo_mod = [(p, c, k) for p, c, k in detalle if c["relevante_manual"] == "false"]
    print(f"  Codificador SI / anotador NO (recall del anotador): {len(solo_cod)}")
    print(f"  Codificador NO / anotador SI (precision del anotador): {len(solo_mod)}")

    hoja = {r["proyecto_id"]: r for r in load("gold_para_codificar.csv")}
    out = GOLD / "gold_desacuerdos.csv"
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["proyecto_id", "titulo", "codificador", "dominio_codificador",
                    "anotador", "dominio_anotador", "confianza_anotador", "flag_revision", "notas"])
        for p, c, k in detalle:
            w.writerow([p, hoja[p]["titulo"], c["relevante_manual"], c["dominio_manual"],
                        k["relevante"], k["dominio"], k["confianza"], c["flag_revision"], c["notas"]])
    print(f"Listado -> {out}")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("validar", "kappa"):
        print(__doc__)
        sys.exit(2)
    (cmd_validar if sys.argv[1] == "validar" else cmd_kappa)()


if __name__ == "__main__":
    main()
