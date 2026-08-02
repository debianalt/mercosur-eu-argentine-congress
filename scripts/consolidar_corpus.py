"""Consolidacion final — Paper A: corpus anotado + acuerdo post-hoc vs anotador Haiku.

    python consolidar_corpus.py

Salidas en paper_A/corpus/:
  etapa1_screen_final.csv   corpus anotado (candidatos del screen con etiqueta final)
  acuerdo_haiku.csv         desacuerdos codificador-vs-Haiku sobre el segmento compartido
"""

import csv
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA = Path(__file__).resolve().parents[3] / "2026_2_" / "app" / "data" / "raw" / "hcdn" / "proyectos_parlamentarios.csv"
CORPUS = BASE / "corpus"

CAMPOS = ["proyecto_id", "titulo", "publicacion_fecha", "anio", "tipo", "autor",
          "relevante", "dominio", "tema", "orientacion", "saliencia",
          "fuente_etiqueta", "flag_revision", "notas"]


def load(path, key="proyecto_id"):
    with open(path, encoding="utf-8", newline="") as f:
        return {r[key]: r for r in csv.DictReader(f)}


def kappa(pares):
    n = len(pares)
    ac = sum(a == b for a, b in pares) / n
    ca, cb = Counter(a for a, _ in pares), Counter(b for _, b in pares)
    esp = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return (ac - esp) / (1 - esp), ac


def main():
    with open(DATA, encoding="utf-8-sig", newline="") as f:
        meta = {r["proyecto_id"]: r for r in csv.DictReader(f) if r.get("proyecto_id")}

    worklist = load(CORPUS / "worklist_screen.csv")
    codigos = load(CORPUS / "corpus_codigos_claude.csv")
    gold = load(BASE / "gold" / "gold_codigos_claude.csv")

    filas = []
    for pid in list(worklist) + [p for p in gold if p not in worklist]:
        m = meta.get(pid)
        if not m:
            continue
        if pid in codigos:
            c, fuente = codigos[pid], "corpus"
            rel, dom = c["relevante"], c["dominio"]
            tema, ori, sal = c["tema"], c["orientacion"], c["saliencia"]
            flag, notas = c["flag_revision"], c["notas"]
        else:
            g = gold[pid]
            fuente = "gold_adjudicado"
            rel = "true" if g["relevante_manual"] == "true" else "false"
            dom, tema = g["dominio_manual"], g["tema_manual"]
            ori, sal = g["orientacion_manual"], g["saliencia_manual"]
            flag, notas = g["flag_revision"], g["notas"]
        filas.append({"proyecto_id": pid, "titulo": m["titulo"],
                      "publicacion_fecha": m["publicacion_fecha"],
                      "anio": (m.get("publicacion_fecha") or "")[:4],
                      "tipo": m["tipo"], "autor": m["autor"],
                      "relevante": rel, "dominio": dom, "tema": tema,
                      "orientacion": ori, "saliencia": sal,
                      "fuente_etiqueta": fuente, "flag_revision": flag, "notas": notas})

    out = CORPUS / "etapa1_screen_final.csv"
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(filas)

    pos = [r for r in filas if r["relevante"] == "true"]
    print(f"Corpus anotado: {len(filas)} titulos -> {out}")
    print(f"  Fuente: {Counter(r['fuente_etiqueta'] for r in filas)}")
    print(f"  RELEVANTES: {len(pos)} ({100 * len(pos) / len(filas):.1f}% de los candidatos)")
    print(f"  Dominio: {Counter(r['dominio'] for r in pos)}")
    print(f"  Tema: {Counter(r['tema'] for r in pos)}")
    print(f"  Orientacion: {Counter(r['orientacion'] for r in pos)}")
    print(f"  Saliencia: {Counter(r['saliencia'] for r in pos)}")
    print(f"  Tipo (positivos): {Counter(r['tipo'] for r in pos)}")
    print(f"  Flags de revision: {sum(r['flag_revision'] == 'si' for r in filas)}")

    print("\n  Positivos por anio:")
    por_anio = Counter(r["anio"] for r in pos)
    cand_anio = Counter(r["anio"] for r in filas)
    for a in sorted(por_anio):
        print(f"    {a}: {por_anio[a]:3d} relevantes / {cand_anio[a]:3d} candidatos")

    # --- acuerdo post-hoc vs Haiku v1.2 ---
    haiku = load(CORPUS / "haiku_labels_screen.csv")
    pares, desac = [], []
    for r in filas:
        h = haiku.get(r["proyecto_id"])
        if not h:
            continue
        a = r["relevante"] == "true"
        b = str(h["relevante"]) == "True"
        pares.append((a, b))
        if a != b:
            desac.append((r, h))
    if pares:
        k, ac = kappa(pares)
        vp = sum(a and b for a, b in pares)
        fn = sum(a and not b for a, b in pares)
        fp = sum(b and not a for a, b in pares)
        rec = vp / (vp + fn) if vp + fn else 0
        pre = vp / (vp + fp) if vp + fp else 0
        f1 = 2 * rec * pre / (rec + pre) if rec + pre else 0
        print(f"\nAcuerdo post-hoc vs anotador Haiku v1.2 (N = {len(pares)} compartidos):")
        print(f"  acuerdo {100 * ac:.1f}% | kappa {k:.3f} | recall {100 * rec:.1f}% | "
              f"precision {100 * pre:.1f}% | F1 {f1:.3f}")
        with open(CORPUS / "acuerdo_haiku.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["proyecto_id", "titulo", "codificador", "dominio_cod",
                        "haiku", "dominio_haiku", "confianza_haiku", "fuente_haiku", "notas"])
            for r, h in desac:
                w.writerow([r["proyecto_id"], r["titulo"], r["relevante"], r["dominio"],
                            h["relevante"], h["dominio"], h["confianza"], h["fuente"], r["notas"]])
        print(f"  {len(desac)} desacuerdos -> {CORPUS / 'acuerdo_haiku.csv'}")


if __name__ == "__main__":
    main()
