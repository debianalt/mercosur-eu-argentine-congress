# Marco de referencia: externo vs domestico

Dos capas sobre los 609 relevantes: regla lexica en todo el corpus, y codificacion manual del autor sobre los 152 del dominio D (`gold/marco_D_manual.csv`). El codigo final es el manual en D y el de la regla en el resto.

**Acuerdo regla-manual en D: 147/152 (96.7%), kappa de Cohen = 0.878.**

## Desacuerdos, con su razon

- **HCDN213062** (2018, LEY): externo -> **domestico**. Recoded externo -> domestico. Minimum-standards environmental bill (presupuestos minimos) on agrochemical traceability: environmental-control instrument with no external-market referent. The lexical rule fired on TRAZABILIDAD.
- **HCDN240918** (2020, LEY): externo -> **domestico**. Recoded externo -> domestico. Same instrument as HCDN213062.
- **HCDN273811** (2024, RESOLUCION): domestico -> **externo**. Recoded domestico -> externo. Requests an import ban on pork produced with ractopamine: explicit external-trade referent (ingreso a la Republica Argentina). The lexical rule has no pattern for INGRESO.
- **HCDN279302** (2024, DECLARACION): eudr -> **ue_otro**. Recoded eudr -> ue_otro. The register of establishments supplying cattle for slaughter for export to the EU is sanitary-traceability apparatus created by SENASA Resolution 370/1997 and re-established by Resolution 53/2017, twenty-six years before Regulation 2023/1115; it also appears as established framework in the recitals of SAGyP Resolution 71/2024 (B.O. 17-10-2024). Title names the EU but not the deforestation regime.
- **HCDN283348** (2025, RESOLUCION): eudr -> **externo**. Recoded eudr -> externo. The individual electronic traceability system was created by SAGyP Resolution 71/2024, whose recitals invoke global consumer demands and sanitary management and do not mention Regulation 2023/1115 or deforestation; Resolution 19/2025 postponed it on device-supply grounds. Multi-market instrument, not EU-specific.

## Segunda codificacion ciega

LLM en sesion fresca (3-ago-2026, cuatro tandas), solo titulos y definiciones del instrumento. **Acuerdo con los codigos manuales: 149/152 (98.0%), kappa de Cohen = 0.926.** Desacuerdos que tocan el marco eudr: 0.

- **HCDN179703**: manual domestico vs ciego externo (duda del ciego: FAO es referente internacional no comercial). El codigo manual queda: protocolo declarado antes de la segunda pasada.
- **HCDN180275**: manual externo vs ciego domestico (duda del ciego: menciona trazabilidad animal dentro de auditoria domestica). El codigo manual queda: protocolo declarado antes de la segunda pasada.
- **HCDN279193**: manual domestico vs ciego externo (duda del ciego: esquema REDD+ internacional pero programa provincial). El codigo manual queda: protocolo declarado antes de la segunda pasada.

## Marco por dominio (codigo final)

| Dominio | eudr | ue_otro | externo | domestico | total |
|---|---|---|---|---|---|
| A — explicit agreement | 0 (0%) | 28 (100%) | 0 (0%) | 0 (0%) | 28 |
| B — sectoral trade with the EU | 0 (0%) | 23 (33%) | 46 (67%) | 0 (0%) | 69 |
| C — Mercosur as an institution | 0 (0%) | 4 (1%) | 354 (98%) | 2 (1%) | 360 |
| D — traceability and forest regulation | 3 (2%) | 1 (1%) | 19 (12%) | 129 (85%) | 152 |
| **Total** | **3** (0%) | **56** (9%) | **419** (69%) | **131** (22%) | **609** |

## El dominio D, que es donde se juega el argumento

- Total: 152
- Con algun marco externo: 23 (15%)
- Puramente domestico: 129 (85%)
- Que enganchan con el regimen europeo de deforestacion: 3

## Serie anual: items que nombran el regimen europeo

| Anio | eudr | ue_otro | externo | domestico | total |
|---|---|---|---|---|---|
| 2008 | 0 | 3 | 22 | 6 | 31 |
| 2009 | 0 | 0 | 23 | 7 | 30 |
| 2010 | 0 | 5 | 51 | 9 | 65 |
| 2011 | 0 | 1 | 30 | 6 | 37 |
| 2012 | 0 | 7 | 49 | 7 | 63 |
| 2013 | 0 | 3 | 24 | 15 | 42 |
| 2014 | 0 | 4 | 47 | 9 | 60 |
| 2015 | 0 | 5 | 21 | 9 | 35 |
| 2016 | 0 | 3 | 23 | 8 | 34 |
| 2017 | 0 | 1 | 13 | 5 | 19 |
| 2018 | 0 | 2 | 9 | 8 | 19 |
| 2019 | 0 | 10 | 13 | 4 | 27 |
| 2020 | 0 | 2 | 23 | 13 | 38 |
| 2021 | 0 | 1 | 19 | 5 | 25 |
| 2022 | 0 | 0 | 17 | 4 | 21 |
| 2023 | 0 | 1 | 5 | 2 | 8 |
| 2024 | 2 | 4 | 18 | 12 | 36 |
| 2025 | 1 | 4 | 12 | 2 | 19 |

## Todos los items que enganchan con el regimen europeo de deforestacion

- [2024 · D · RESOLUCION] EXPRESAR APOYO A LAS GESTIONES DEL PODER EJECUTIVO NACIONAL PARA POSTERGAR LA ENTRADA EN VIGENCIA DEL REGLAMENTO N° 2023/1115 DE LA UNION EUROPEA, QUE ESTABLECE RESTRICCIONES AL COMERCIO.
- [2024 · D · RESOLUCION] PEDIDO DE INFORMES AL PODER EJECUTIVO SOBRE LAS ACCIONES QUE ESTA IMPLEMENTANDO EL GOBIERNO NACIONAL EN POS DEL CUMPLIMIENTO DEL REGLAMENTO RELATIVO A LA COMERCIALIZACION Y EXPORTACION DE PRODUCTOS ASOCIADOS A LA DEFORESTACION Y LA DEGRADACION FORESTAL EN EL MERCADO DE LA UNION EUROPEA.
- [2025 · D · RESOLUCION] INSTAR AL PODER EJECUTIVO RETOME LAS NEGOCIACIONES CON LOS ORGANISMOS INTERNACIONALES CORRESPONDIENTES PARA GARANTIZAR LA CONTINUIDAD DE LAS EXPORTACIONES ARGENTINAS MIENTRAS DURE LA SUSPENSION DE LA REGULACION 2023/1115 DE LA UNION EUROPEA.
