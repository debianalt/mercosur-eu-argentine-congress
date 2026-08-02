"""Analisis seccion 4 — Paper A (bloques descriptivos 4.1-4.4).

    python analisis_seccion4.py

Salidas en paper_A/analisis/:
  serie_atencion.csv            anio x conteos, indice ponderado, tasa por 1.000, hitos
  serie_atencion_trimestral.csv trimestre x relevantes (localizacion fina de picos)
  autores_join.csv              relevantes x (categoria autor, bloque, familia, distrito, region)
  orientacion_bloque.csv        familia x presidencia (orientacion) + familia x dominio
  geografia.csv                 distrito y region x conteos + tasa por 100 banca-anios
  avance.csv                    dictamen / aprobado / ley por segmento vs universo HCDN

Entradas versionadas en analisis/: bloques_familias.csv (bloque -> familia
politica, manual) y diputados_supl_2005_2009.csv (cohorte 2005-2009 ausente de
diputados.csv, reconstruida por build_suplemento_2005_2009.py; completa el join
de autores 2008-09 y los denominadores de banca-anios).
"""

import csv
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
HCDN = Path(__file__).resolve().parents[3] / "2026_2_" / "app" / "data" / "raw" / "hcdn"
OUT = BASE / "analisis"

PESO_TIPO = {"LEY": 3, "MENSAJE Y PROYECTO DE LEY": 3, "RESOLUCION": 2,
             "DECLARACION": 1, "MENSAJE": 1}

PRESIDENCIAS = [  # (clave, desde, hasta) sobre publicacion_fecha ISO
    ("cfk_2008_2015", "2008-01-01", "2015-12-09"),
    ("macri_2015_2019", "2015-12-10", "2019-12-09"),
    ("fernandez_2019_2023", "2019-12-10", "2023-12-09"),
    ("milei_2023_2025", "2023-12-10", "2025-12-31"),
]
GOBIERNO = {"cfk_2008_2015": {"kirchnerismo"},
            "macri_2015_2019": {"pro", "ucr", "cc_ari"},
            "fernandez_2019_2023": {"kirchnerismo"},
            "milei_2023_2025": {"lla"}}

REGIONES = {
    "NEA": {"MISIONES", "CORRIENTES", "CHACO", "FORMOSA"},
    "NOA": {"JUJUY", "SALTA", "TUCUMAN", "CATAMARCA", "SANTIAGO DEL ESTERO", "LA RIOJA"},
    "CUYO": {"MENDOZA", "SAN JUAN", "SAN LUIS"},
    "PAMPEANA": {"BUENOS AIRES", "CORDOBA", "SANTA FE", "ENTRE RIOS", "LA PAMPA"},
    "PATAGONIA": {"NEUQUEN", "RIO NEGRO", "CHUBUT", "SANTA CRUZ", "TIERRA DEL FUEGO"},
    "CABA": {"CIUDAD DE BUENOS AIRES"},
}
DISTRITO_REGION = {d: r for r, ds in REGIONES.items() for d in ds}

ANIOS_ELECTORALES = {2009, 2011, 2013, 2015, 2017, 2019, 2021, 2023, 2025}
HITOS_ANIO = {2010: "relanzamiento Madrid (may)", 2016: "intercambio de ofertas (may)",
              2019: "acuerdo politico (jun)", 2024: "cierre negociacion (dic)"}
HITOS_TRIM = {"2010Q2": "Madrid", "2016Q2": "ofertas", "2019Q2": "acuerdo politico",
              "2024Q4": "cierre"}


def norm(s):
    s = unicodedata.normalize("NFD", (s or "").upper().strip())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", s)


def presidencia(fecha):
    for clave, desde, hasta in PRESIDENCIAS:
        if desde <= fecha <= hasta:
            return clave
    return ""


class IndiceDiputados:
    """Match autor ('APELLIDO, NOMBRE') -> mandato vigente en la fecha.

    Fallback: apellido + primer nombre, solo si apunta a una unica persona.
    """

    def __init__(self, filas):
        self.exacto = defaultdict(list)
        self.fb_exacto = defaultdict(list)
        for d in filas:
            full = norm(d["apellido"] + ", " + d["nombre"])
            corto = norm(d["apellido"]) + "/" + (norm(d["nombre"]).split(" ") or [""])[0]
            self.exacto[full].append(d)
            self.fb_exacto[corto].append(d)

    def _vigente(self, cands, fecha):
        for d in cands:
            if d["bloque_inicio"][:10] <= fecha <= d["bloque_fin"][:10]:
                return d, "vigente"
        if cands:  # autor con mandato pero fecha fuera de la ventana de bloque
            mejor = min(cands, key=lambda d: abs_dias(d["bloque_inicio"][:10], fecha))
            return mejor, "fuera_ventana"
        return None, ""

    def match(self, autor, fecha):
        a = norm(autor)
        exacto = self.exacto.get(a, [])
        if exacto:
            d, det = self._vigente(exacto, fecha)
            if det == "vigente":
                return d, "exacto_vigente"
        partes = a.split(", ")
        if len(partes) == 2:
            corto = partes[0] + "/" + partes[1].split(" ")[0]
            filas = self.fb_exacto.get(corto, [])
            if filas and len({d["id"] for d in filas}) == 1:
                d, det = self._vigente(filas, fecha)
                if det == "vigente":
                    return d, "fallback_vigente"
        if exacto:  # sin estadia vigente en ningun pool: la mas cercana
            d, det = self._vigente(exacto, fecha)
            return d, "exacto_" + det
        return None, ""


def abs_dias(a, b):
    from datetime import date
    da = date(*map(int, a.split("-")))
    db = date(*map(int, b.split("-")))
    return abs((da - db).days)


def fecha_valida(v):
    v = (v or "")[:10]
    return v if v and v[0].isdigit() else ""


def load(path, encoding="utf-8-sig"):
    with open(path, encoding=encoding, newline="") as f:
        return list(csv.DictReader(f))


def escribir(path, filas, campos):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)
    print(f"  -> {path.name} ({len(filas)} filas)")


def main():
    OUT.mkdir(exist_ok=True)
    corpus = load(BASE / "corpus" / "etapa1_screen_final.csv", encoding="utf-8")
    rel = [r for r in corpus if r["relevante"] == "true"]
    meta = {r["proyecto_id"]: r for r in load(HCDN / "proyectos_parlamentarios.csv")
            if r.get("proyecto_id")}
    dips = load(HCDN / "diputados.csv")
    for s in load(OUT / "diputados_supl_2005_2009.csv", encoding="utf-8"):
        dips.append({"id": s["id"], "apellido": s["apellido"], "nombre": s["nombre"],
                     "distrito": s["distrito"], "bloque": s["bloque"],
                     "inicio": s["inicio"], "fin": s["fin"],
                     "bloque_inicio": s["inicio"], "bloque_fin": s["fin"],
                     "suplemento": "si"})
    idx = IndiceDiputados(dips)

    familias = {}
    for r in load(OUT / "bloques_familias.csv", encoding="utf-8"):
        familias[norm(r["bloque"])] = r["familia"]
    # bloques mixtos: integrantes con partido propio inequivoco (PS, GEN)
    # se asignan a su familia partidaria por diputado_id
    overrides = {r["diputado_id"]: r["familia"]
                 for r in load(OUT / "familia_overrides.csv", encoding="utf-8")}

    # ---------- 4.1 serie de atencion ----------
    total_anio = Counter(m["publicacion_fecha"][:4] for m in meta.values())
    cand_anio = Counter(r["anio"] for r in corpus)
    filas_serie = []
    for anio in map(str, range(2008, 2026)):
        de_anio = [r for r in rel if r["anio"] == anio]
        dom = Counter(r["dominio"] for r in de_anio)
        tip = Counter(r["tipo"] for r in de_anio)
        indice = sum(PESO_TIPO.get(r["tipo"], 1) for r in de_anio)
        filas_serie.append({
            "anio": anio, "total_hcdn": total_anio[anio], "candidatos": cand_anio[anio],
            "relevantes": len(de_anio),
            "dom_A": dom["A"], "dom_B": dom["B"], "dom_C": dom["C"], "dom_D": dom["D"],
            "ley": tip["LEY"], "resolucion": tip["RESOLUCION"],
            "declaracion": tip["DECLARACION"],
            "mensaje_ley": tip["MENSAJE Y PROYECTO DE LEY"], "mensaje": tip["MENSAJE"],
            "indice_ponderado": indice,
            "tasa_1000": round(1000 * len(de_anio) / total_anio[anio], 2)
            if total_anio[anio] else "",
            "electoral": "si" if int(anio) in ANIOS_ELECTORALES else "no",
            "hito": HITOS_ANIO.get(int(anio), ""),
        })
    escribir(OUT / "serie_atencion.csv", filas_serie, list(filas_serie[0]))

    trims = Counter()
    for r in rel:
        f = r["publicacion_fecha"]
        trims[f[:4] + "Q" + str((int(f[5:7]) - 1) // 3 + 1)] += 1
    filas_trim = [{"trimestre": t, "relevantes": trims[t], "hito": HITOS_TRIM.get(t, "")}
                  for t in sorted(trims)]
    escribir(OUT / "serie_atencion_trimestral.csv", filas_trim, list(filas_trim[0]))

    # ---------- join autor -> diputado ----------
    filas_join = []
    for r in rel:
        m = meta.get(r["proyecto_id"], {})
        exp = (m.get("exp_diputados") or "") + " " + (m.get("exp_senado") or "")
        fecha = r["publicacion_fecha"][:10]
        cat, metodo, bloque, familia, distrito, did, fm = "", "", "", "", "", "", ""
        if "-PE-" in exp or "-JGM-" in exp or r["tipo"].startswith("MENSAJE"):
            cat = "ejecutivo"
        elif "," not in r["autor"]:
            cat = "organo"
        elif m.get("camara_origen") == "Senado":
            cat = "senado"
        else:
            d, metodo = idx.match(r["autor"], fecha)
            if d:
                cat = "diputado"
                bloque = d["bloque"]
                familia = overrides.get(d["id"]) or familias.get(norm(bloque), "SIN_MAPEAR")
                distrito = d["distrito"]
                did = d["id"]
                fm = "suplemento" if d.get("suplemento") else "hcdn"
            else:
                cat = "sin_match"
        pres = presidencia(fecha)
        filas_join.append({
            "proyecto_id": r["proyecto_id"], "fecha": fecha, "autor": r["autor"],
            "categoria": cat, "metodo_match": metodo, "diputado_id": did,
            "fuente_mandato": fm, "bloque": bloque,
            "familia": familia, "distrito": distrito,
            "region": DISTRITO_REGION.get(distrito, ""),
            "presidencia": pres,
            "gobierno": ("si" if familia and familia in GOBIERNO.get(pres, set())
                         else ("no" if familia else "")),
            "tipo": r["tipo"], "dominio": r["dominio"],
            "orientacion": r["orientacion"], "saliencia": r["saliencia"],
        })
    escribir(OUT / "autores_join.csv", filas_join, list(filas_join[0]))

    cats = Counter(f["categoria"] for f in filas_join)
    print(f"  categorias de autor: {dict(cats)}  (suma {sum(cats.values())} = {len(rel)})")
    print(f"  metodos de match: {Counter(f['metodo_match'] for f in filas_join if f['metodo_match'])}")
    print(f"  fuente del mandato: {Counter(f['fuente_mandato'] for f in filas_join if f['fuente_mandato'])}")
    sin_mapear = Counter(f["bloque"] for f in filas_join if f["familia"] == "SIN_MAPEAR")
    if sin_mapear:
        print(f"  BLOQUES SIN MAPEAR: {dict(sin_mapear)}")
    sm = [f for f in filas_join if f["categoria"] == "sin_match"]
    if sm:
        print(f"  sin match ({len(sm)}): {Counter(f['autor'] for f in sm)}")
        print(f"  sin match por anio: {sorted(Counter(f['fecha'][:4] for f in sm).items())}")

    # ---------- 4.2 orientacion por familia x presidencia ----------
    dip_join = [f for f in filas_join if f["categoria"] == "diputado"]
    filas_ori = []
    for (fam, pres), grupo in sorted(agrupar(dip_join, ("familia", "presidencia")).items()):
        ori = Counter(g["orientacion"] for g in grupo)
        dom = Counter(g["dominio"] for g in grupo)
        n = len(grupo)
        filas_ori.append({
            "familia": fam, "presidencia": pres,
            "gobierno": grupo[0]["gobierno"], "n": n,
            "neutra": ori["administrativa_neutra"],
            "pro_liberalizacion": ori["pro_liberalizacion"],
            "defensiva": ori["proteccionista_defensiva"],
            "condicionada": ori["condicionada"],
            "pct_no_neutra": round(100 * (n - ori["administrativa_neutra"]) / n, 1),
            "dom_A": dom["A"], "dom_B": dom["B"], "dom_C": dom["C"], "dom_D": dom["D"],
        })
    escribir(OUT / "orientacion_bloque.csv", filas_ori, list(filas_ori[0]))

    # ---------- 4.3 geografia ----------
    # servicio efectivo: reemplazos juran tarde (juramento > inicio) y las
    # renuncias cesan antes (cese < fin); usar fechas nominales doble-contaria
    banca_anios = Counter()
    vistos = set()
    for d in dips:  # mandato-anios en 2008-2025 (filas por estadia de bloque: dedup por mandato)
        clave = (d["id"], d["inicio"], d["fin"])
        if clave in vistos:
            continue
        vistos.add(clave)
        jura = fecha_valida(d.get("juramento"))
        cese = fecha_valida(d.get("cese"))
        ini = max(d["inicio"][:10], jura or "2008-01-01", "2008-01-01")
        fin = min(d["fin"][:10], cese or "2025-12-31", "2025-12-31")
        if ini < fin:
            banca_anios[d["distrito"]] += abs_dias(ini, fin) / 365.25

    filas_geo = []
    por_distrito = agrupar(dip_join, ("distrito",))
    for (dist,), grupo in sorted(por_distrito.items()):
        dom = Counter(g["dominio"] for g in grupo)
        ba = banca_anios[dist]
        filas_geo.append({
            "unidad": dist, "nivel": "distrito",
            "region": DISTRITO_REGION.get(dist, ""), "relevantes": len(grupo),
            "dom_B": dom["B"], "dom_D": dom["D"], "banca_anios": round(ba, 1),
            "tasa_100ba": round(100 * len(grupo) / ba, 2) if ba else "",
        })
    for reg, dists in REGIONES.items():
        grupo = [g for g in dip_join if g["region"] == reg]
        dom = Counter(g["dominio"] for g in grupo)
        ba = sum(banca_anios[d] for d in dists)
        filas_geo.append({
            "unidad": reg, "nivel": "region", "region": reg, "relevantes": len(grupo),
            "dom_B": dom["B"], "dom_D": dom["D"], "banca_anios": round(ba, 1),
            "tasa_100ba": round(100 * len(grupo) / ba, 2) if ba else "",
        })
    escribir(OUT / "geografia.csv", filas_geo, list(filas_geo[0]))

    # ---------- 4.4 tasa de avance ----------
    # resultado_proyectos lista ~todo el universo; dictamen_tipo NA = nunca dictaminado
    con_dictamen, aprobados = set(), set()
    for r in load(HCDN / "resultado_proyectos.csv"):
        if r.get("dictamen_tipo") not in ("", "NA"):
            con_dictamen.add(r["expediente_id"])
        if r.get("resultado") in ("APROBADO", "MEDIA SANCION", "SANCIONADO"):
            aprobados.add(r["expediente_id"])
    sancionados = {r["proyecto_id"] for r in load(HCDN / "leyes_sancionadas.csv")}
    giros = Counter()
    for r in load(HCDN / "giro_comisiones.csv"):
        giros[r["proyecto_id"]] += 1

    def avance(ids, grupo, subgrupo, tipo):
        n = len(ids)
        if not n:
            return None
        gg = [giros[i] for i in ids if giros[i]]
        return {"grupo": grupo, "subgrupo": subgrupo, "tipo": tipo, "n": n,
                "pct_dictamen": round(100 * sum(i in con_dictamen for i in ids) / n, 1),
                "pct_aprobado": round(100 * sum(i in aprobados for i in ids) / n, 1),
                "pct_ley": round(100 * sum(i in sancionados for i in ids) / n, 1),
                "mediana_giros": statistics.median(gg) if gg else ""}

    filas_av = []
    tipos = sorted({r["tipo"] for r in rel})
    for tipo in tipos:
        filas_av.append(avance([r["proyecto_id"] for r in rel if r["tipo"] == tipo],
                               "corpus", "todos", tipo))
        filas_av.append(avance([p for p, m in meta.items() if m["tipo"] == tipo],
                               "universo_hcdn", "todos", tipo))
    for dom in "ABCD":
        filas_av.append(avance([r["proyecto_id"] for r in rel if r["dominio"] == dom],
                               "corpus", f"dominio_{dom}", "todos"))
    for ori in ("administrativa_neutra", "pro_liberalizacion", "proteccionista_defensiva"):
        filas_av.append(avance([r["proyecto_id"] for r in rel if r["orientacion"] == ori],
                               "corpus", f"orientacion_{ori}", "todos"))
    filas_av = [f for f in filas_av if f]
    escribir(OUT / "avance.csv", filas_av, list(filas_av[0]))

    # ---------- resumen consola ----------
    print("\nSerie de atencion (relevantes/anio):")
    for f in filas_serie:
        barra = "#" * f["relevantes"]
        print(f"  {f['anio']}  {f['relevantes']:3d}  tasa {f['tasa_1000']:>5}  {barra}"
              f"{'  <-- ' + f['hito'] if f['hito'] else ''}")
    print("\nFamilia x presidencia (n >= 10):")
    for f in filas_ori:
        if f["n"] >= 10:
            print(f"  {f['familia']:22s} {f['presidencia']:20s} gob={f['gobierno']} "
                  f"n={f['n']:3d}  no-neutra {f['pct_no_neutra']}%")
    print("\nRegiones (tasa por 100 banca-anios):")
    for f in filas_geo:
        if f["nivel"] == "region":
            print(f"  {f['unidad']:10s} rel={f['relevantes']:3d}  tasa={f['tasa_100ba']}"
                  f"  B={f['dom_B']} D={f['dom_D']}")


def agrupar(filas, claves):
    grupos = defaultdict(list)
    for f in filas:
        grupos[tuple(f[k] for k in claves)].append(f)
    return grupos


if __name__ == "__main__":
    main()
