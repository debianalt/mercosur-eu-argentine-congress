# -*- coding: utf-8 -*-
"""Aplica la revision experta al corpus final (in place; git = provenance).

Correr cuando corpus/revision_experta.csv (y opcionalmente
revision_negativos_flag.csv) esten revisados. Convencion: columna *_corr
vacia = confirmado; con valor = correccion.

- tema_corr = otro_descartar -> la fila pasa a relevante=false (dominio
  ninguno, resto vacio).
- relevante_corr = si en la hoja de negativos -> promocion a relevante
  (exige tema_corr/orientacion_corr/saliencia_corr completos; el dominio
  se deriva del tema).

Outputs: etapa1_screen_final.csv actualizado, corpus/log_revision_experta.csv
(antes/despues por fila cambiada) y analisis/revision_experta_metricas.md
(tasa de correccion global, por variable y por tier -> Data and Methods).
Tras correr, re-ejecutar analisis_seccion4.py / analisis_seccion45.py si
hubo correcciones.
"""
import csv
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
CORPUS = BASE / "corpus" / "etapa1_screen_final.csv"
REV_REL = BASE / "corpus" / "revision_experta.csv"
REV_NEG = BASE / "corpus" / "revision_negativos_flag.csv"
OUT_LOG = BASE / "corpus" / "log_revision_experta.csv"
OUT_MD = BASE / "analisis" / "revision_experta_metricas.md"

TEMA_A_DOMINIO = {"acuerdo_ue_mercosur": "A", "comercio_ue_sectorial": "B",
                  "mercosur_institucional": "C", "eudr_trazabilidad_forestal": "D",
                  "mercosur_simbolico": "C"}
VALID = {
    "tema_corr": set(TEMA_A_DOMINIO) | {"otro_descartar"},
    "orientacion_corr": {"pro_liberalizacion", "proteccionista_defensiva",
                         "condicionada", "administrativa_neutra"},
    "saliencia_corr": {"explicita", "relacionada"},
}


def leer(path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def validar(r, cols):
    for c in cols:
        v = r.get(c, "").strip().lower()
        if v and v not in VALID[c]:
            raise SystemExit(f"valor invalido '{v}' en {c}, orden {r['orden']}")


def main():
    with open(CORPUS, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        corpus = {r["proyecto_id"]: r for r in reader}

    rev_rel, rev_neg = leer(REV_REL), leer(REV_NEG)
    if not rev_rel:
        raise SystemExit(f"no existe {REV_REL}; correr build_revision_experta.py")

    log, cambios_var, cambios_tier = [], Counter(), Counter()
    revisadas_rel = len(rev_rel)

    def registrar(pid, campo, antes, despues, origen, nota):
        log.append({"proyecto_id": pid, "campo": campo, "antes": antes,
                    "despues": despues, "origen": origen, "nota": nota})

    for r in rev_rel:
        validar(r, ["tema_corr", "orientacion_corr", "saliencia_corr"])
        pid = r["proyecto_id"]
        c = corpus[pid]
        nota = r.get("nota_revision", "").strip()
        tema_c = r["tema_corr"].strip().lower()
        fila_cambio = False

        if tema_c == "otro_descartar":
            registrar(pid, "relevante", "true", "false", "revision_experta", nota)
            c.update({"relevante": "false", "dominio": "ninguno", "tema": "",
                      "orientacion": "", "saliencia": ""})
            cambios_var["descartado"] += 1
            cambios_tier[r["tier"]] += 1
            continue

        for campo, corr in [("tema", tema_c),
                            ("orientacion", r["orientacion_corr"].strip().lower()),
                            ("saliencia", r["saliencia_corr"].strip().lower())]:
            if corr and corr != c[campo]:
                registrar(pid, campo, c[campo], corr, "revision_experta", nota)
                c[campo] = corr
                if campo == "tema":
                    c["dominio"] = TEMA_A_DOMINIO[corr]
                cambios_var[campo] += 1
                fila_cambio = True
        if fila_cambio:
            cambios_tier[r["tier"]] += 1

    promovidos = 0
    for r in rev_neg:
        if r["relevante_corr"].strip().lower() not in {"si", "sí", "true"}:
            continue
        validar(r, ["tema_corr", "orientacion_corr", "saliencia_corr"])
        pid = r["proyecto_id"]
        tema_c = r["tema_corr"].strip().lower()
        ori_c = r["orientacion_corr"].strip().lower()
        sal_c = r["saliencia_corr"].strip().lower()
        if not (tema_c and ori_c and sal_c) or tema_c == "otro_descartar":
            raise SystemExit(f"promocion incompleta en negativos, orden {r['orden']}")
        c = corpus[pid]
        registrar(pid, "relevante", "false", "true", "revision_negativos",
                  r.get("nota_revision", "").strip())
        c.update({"relevante": "true", "dominio": TEMA_A_DOMINIO[tema_c],
                  "tema": tema_c, "orientacion": ori_c, "saliencia": sal_c})
        promovidos += 1

    with open(CORPUS, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(corpus.values())

    with open(OUT_LOG, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["proyecto_id", "campo", "antes",
                                          "despues", "origen", "nota"])
        w.writeheader()
        w.writerows(log)

    n_final = sum(1 for c in corpus.values() if c["relevante"] == "true")
    filas_corregidas = len({e["proyecto_id"] for e in log})
    lines = [
        "# Revision experta del corpus — metricas",
        "",
        f"Filas relevantes revisadas: {revisadas_rel}. Hoja de negativos con "
        f"flag: {len(rev_neg)} filas (promovidos: {promovidos}).",
        # denominador canonico = relevantes revisados (la hoja de negativos no
        # aporta correcciones por construccion: solo puede promover)
        f"Filas con al menos una correccion: {filas_corregidas} "
        f"({filas_corregidas / revisadas_rel:.1%} de los {revisadas_rel} "
        f"relevantes revisados; {filas_corregidas / (revisadas_rel + len(rev_neg)):.1%} "
        f"si el denominador incluye la hoja de negativos).",
        "",
        "| Correccion | n |",
        "|---|---|",
    ]
    for k in ["tema", "orientacion", "saliencia", "descartado"]:
        lines.append(f"| {k} | {cambios_var[k]} |")
    lines.append(f"| promovido (negativo->relevante) | {promovidos} |")
    lines += ["", "| Tier | filas corregidas |", "|---|---|"]
    for t in sorted(cambios_tier):
        lines.append(f"| {t} | {cambios_tier[t]} |")
    lines += ["", f"*N* relevantes final: {n_final} (antes: 614).",
              "", "Detalle antes/despues en `corpus/log_revision_experta.csv`."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nescritos:\n  {CORPUS} (in place)\n  {OUT_LOG}\n  {OUT_MD}")


if __name__ == "__main__":
    main()
