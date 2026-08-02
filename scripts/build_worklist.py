"""Diseno sin API — Paper A: screen deterministico + lista de trabajo del codificador.

1. Aplica el screen de keywords (eje + sectoriales, generoso) sobre los 110.500.
2. Cota empirica del recall del screen: positivos en titulos SIN keyword ya
   anotados por Haiku v1.2 (piloto + pool del gold + cola del corpus).
3. Emite la worklist para codificacion experta en sesion (sin etiquetas previas,
   para no anclar) y un archivo aparte con las etiquetas Haiku existentes
   (para acuerdo inter-anotador post-hoc).

    python build_worklist.py
"""

import csv
import re
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA = Path(__file__).resolve().parents[3] / "2026_2_" / "app" / "data" / "raw" / "hcdn" / "proyectos_parlamentarios.csv"
OUT = BASE / "corpus"

SCREEN = re.compile(
    r"MERCOSUR|UNION EUROPEA|CUOTA HILTON|CUOTA 481|BIODIESEL|BIOCOMBUSTIBLE"
    r"|TRAZABILIDAD|DEFORESTACION|EUDR|ARANCEL|ANTIDUMPING|UNION ADUANERA"
    r"|LIBRE COMERCIO|\bOMC\b|ORGANIZACION MUNDIAL DE COMERCIO|ORGANIZACION MUNDIAL DEL COMERCIO"
    r"|BOSQUES? NATIVOS?|\bAFTOSA\b|FITOSANITARI|CITRIC[OA]|\bCARNE|\bLIMON(ES)?\b|\bACERO\b"
)


def load(path, key="proyecto_id"):
    if not path.exists():
        return {}
    with open(path, encoding="utf-8", newline="") as f:
        return {r[key]: r for r in csv.DictReader(f)}


def main():
    with open(DATA, encoding="utf-8-sig", newline="") as f:
        corpus = [r for r in csv.DictReader(f) if r.get("titulo") and r.get("proyecto_id")]

    candidatos = [r for r in corpus if SCREEN.search(r["titulo"])]
    print(f"Corpus: {len(corpus)} | Candidatos del screen: {len(candidatos)} "
          f"({100 * len(candidatos) / len(corpus):.2f}%)")

    # --- etiquetas Haiku v1.2 existentes (todas las corridas) ---
    fuentes = {
        "corpus_tail": load(OUT / "etapa1_corpus_results.csv"),
        "gold_pool": load(BASE / "gold" / "gold_pool_results.csv"),
        "piloto_v1_2": load(BASE / "pilot" / "etapa1_results_v1_2.csv"),
        "sectorial": load(BASE / "pilot" / "filtro_sectorial_cruce.csv"),
    }
    haiku = {}
    for fuente, rows in fuentes.items():
        for pid, r in rows.items():
            rel = r.get("relevante") or r.get("filtro_relevante") or ""
            estado = r.get("estado", "ok")
            if str(estado) != "ok" and fuente != "sectorial":
                continue
            if pid not in haiku and str(rel) in ("True", "False"):
                haiku[pid] = {"relevante": str(rel), "dominio": r.get("dominio") or r.get("filtro_dominio", ""),
                              "confianza": r.get("confianza") or r.get("filtro_confianza", ""), "fuente": fuente}
    print(f"Etiquetas Haiku v1.2 disponibles: {len(haiku)}")

    # --- cota del recall del screen: titulos SIN keyword ya anotados ---
    sin_kw_anotados = [(pid, h) for pid, h in haiku.items()]
    corpus_idx = {r["proyecto_id"]: r for r in corpus}
    sin_kw = [(pid, h) for pid, h in sin_kw_anotados
              if pid in corpus_idx and not SCREEN.search(corpus_idx[pid]["titulo"])]
    pos_sin_kw = [(pid, h) for pid, h in sin_kw if h["relevante"] == "True"]
    print(f"Control del screen: {len(sin_kw)} titulos sin keyword con etiqueta Haiku; "
          f"positivos = {len(pos_sin_kw)}")
    for pid, h in pos_sin_kw[:20]:
        print(f"  MISS del screen: [{h['dominio']}/{h['confianza']}] {corpus_idx[pid]['titulo'][:120]}")
    n = len(sin_kw)
    if n and not pos_sin_kw:
        # cota superior 95% (regla de 3) sobre la fraccion de positivos en no-keyword
        cota = 3.0 / n
        restantes = len(corpus) - len(candidatos)
        print(f"Cota superior 95% del miss: {100 * cota:.3f}% de los {restantes} sin keyword "
              f"= ~{cota * restantes:.0f} titulos en todo el corpus")

    # --- worklist: candidatos sin etiqueta adjudicada (gold) ---
    gold = load(BASE / "gold" / "gold_codigos_claude.csv")
    pendientes = [r for r in candidatos if r["proyecto_id"] not in gold]
    ya_gold = len(candidatos) - len(pendientes)
    pendientes.sort(key=lambda r: (r.get("publicacion_fecha") or "", r["proyecto_id"]))
    print(f"Candidatos ya adjudicados en gold: {ya_gold} | Worklist a codificar: {len(pendientes)}")
    print(f"Worklist por anio: {dict(sorted(Counter((r.get('publicacion_fecha') or '')[:4] for r in pendientes).items()))}")

    OUT.mkdir(exist_ok=True)
    with open(OUT / "worklist_screen.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["proyecto_id", "titulo", "publicacion_fecha", "tipo", "autor"],
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(pendientes)
    with open(OUT / "haiku_labels_screen.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["proyecto_id", "relevante", "dominio", "confianza", "fuente"])
        for pid, h in haiku.items():
            w.writerow([pid, h["relevante"], h["dominio"], h["confianza"], h["fuente"]])
    print(f"-> {OUT / 'worklist_screen.csv'} (para codificar, sin etiquetas previas)")
    print(f"-> {OUT / 'haiku_labels_screen.csv'} (acuerdo post-hoc; no mirar al codificar)")


if __name__ == "__main__":
    main()
