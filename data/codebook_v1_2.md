# Taxonomía de anotación — Paper A (v1.0)

**Estado**: **v1.2 CONGELADA** (1-ago-2026), tras piloto de 3 iteraciones sobre 497 títulos (ver `pilot/informe_piloto_etapa1.md`). Decisión del usuario: título-only estricto en el filtro principal + barrido sectorial de robustez por separado (opción A+C). Cambios posteriores requieren nueva versión y re-validación.
**Unidad de análisis**: el título del proyecto parlamentario (HCDN, 2008-2025, *N* = 110.501). La anotación se basa exclusivamente en el título; los títulos HCDN son largos y descriptivos (funcionan como sumario), limitación declarada en Data and Methods.
**Arquitectura**: dos etapas. Etapa 1 = filtro binario de relevancia (alto recall, Haiku 4.5). Etapa 2 = clasificación fina sobre los positivos (Sonnet 5). Prompts congelados en `prompts/`.

---

## Etapa 1 — Relevancia (binaria)

**Pregunta operativa**: ¿el proyecto toca el eje comercio UE-Mercosur y su ecosistema regulatorio?

Un proyecto es **relevante** si su título toca al menos uno de estos cuatro dominios:

| Dominio | Definición | Ejemplos reales del corpus |
|---|---|---|
| **A. Acuerdo UE-Mercosur** | Negociación, firma, ratificación, contenido o seguimiento parlamentario del acuerdo de asociación birregional | "PEDIDO DE INFORMES AL PODER EJECUTIVO SOBRE DIVERSAS CUESTIONES RELACIONADAS CON EL ACUERDO ENTRE MERCADO COMUN DEL SUR (MERCOSUR) Y LA UNION EUROPEA (UE)" (5554-D-2024); "COMISION BICAMERAL ESPECIAL PARA EL SEGUIMIENTO Y RATIFICACION DEL ACUERDO DE ASOCIACION ESTRATEGICA MERCOSUR - UNION EUROPEA" (0945-D-2021) |
| **B. Comercio exterior con la UE** | Exportaciones/importaciones, aranceles, cuotas (Hilton, 481), barreras sanitarias o técnicas, disputas o acuerdos comerciales con la UE o con estados miembros | "EXPRESAR PREOCUPACION POR EL INCUMPLIMIENTO DE LA CUOTA HILTON" (5283-D-2014); proyectos sobre biodiesel-UE, limones, acero |
| **C. Mercosur** | Institucionalidad del bloque (cumbres, Parlasur, arancel externo común), comercio intra-Mercosur, negociaciones comerciales externas del bloque con cualquier contraparte | "EXPRESAR BENEPLACITO POR LA SUSCRIPCION DEL ACUERDO... EN LA 63 EDICION DE LA CUMBRE DE JEFES DE ESTADO DEL MERCOSUR" (4837-D-2023) |
| **D. Trazabilidad / deforestación / regulación forestal ligada a cadenas productivas o de exportación** | Trazabilidad de ganado o productos agropecuarios/forestales, certificación de origen o libre-deforestación, reglamento europeo de deforestación (EUDR), política de bosques nativos vinculada a producción o comercio | "PEDIDO DE INFORMES... TRAZABILIDAD INDIVIDUAL ELECTRONICA PARA GANADO BOVINO, BUBALINO Y CERVIDO" (6175-D-2024) |

**No relevante** (exclusiones, con las trampas reales del corpus):

1. **Trazabilidad doméstica de otros rubros**: medicamentos ("REGIMEN DE TRAZABILIDAD UNITARIA Y DIGITAL DE MEDICAMENTOS DE ALTO RIESGO", 5913-D-2025), GNC ("SISTEMA NACIONAL DE TRAZABILIDAD DE OBLEAS DE CARGA DE GNC", 5476-D-2025), dispositivos médicos, ciberfraudes, evolución patrimonial de funcionarios, salud pública. El grep de "TRAZABILIDAD" muestra que la mayoría de los hits son de este tipo — la palabra sola no alcanza.
2. **UE / países europeos sin contenido comercial-regulatorio**: cooperación cultural o educativa, derechos humanos, política exterior general.
3. **Política agropecuaria o industrial doméstica** sin conexión con la UE, el Mercosur o requisitos de exportación/trazabilidad.
4. **Referencia a la Nomenclatura Común del Mercosur (NCM) como mero nomenclador** *(agregada en v1.1 tras el piloto)*: medidas tributarias/aduaneras domésticas que citan posiciones arancelarias de la NCM (derechos de exportación a la soja, reintegros, IVA). 131 títulos en el corpus; el piloto v1 los incluía como dominio C.
5. **Comercio exterior general sin contraparte europea identificable** *(precisión de B en v1.1)*: OMC, retenciones, disputas con países no europeos. La Cuota Hilton cuenta como UE implícita.
6. **Eventos y honores con nombre Mercosur** *(agregada en v1.1)*: declaraciones de interés por festivales, encuentros culturales, expos y congresos "del Mercosur", y actos honoríficos ("ciudadano ilustre del Mercosur"). Cumbres y órganos del bloque sí son dominio C.

**Regla de duda (alto recall)**: si el título es ambiguo pero plausiblemente toca un dominio, marcar relevante. La etapa 2 descarta los falsos positivos. Casos límite que se incluyen: REDD+/créditos de carbono en provincias forestales (dominio D débil), acuerdos del Mercosur con terceros no-UE (dominio C), trazabilidad bovina aunque el título no mencione exportación (dominio D — el régimen SENASA responde a mercados de destino).

**Output etapa 1** (JSON): `relevante` (bool), `dominio` (A/B/C/D/ninguno — el dominio principal que dispara la inclusión), `confianza` (alta/media/baja).

---

## Etapa 2 — Clasificación fina (sobre positivos de etapa 1)

Tres dimensiones independientes por proyecto.

### 2.1 Tema (excluyente; ante empate, la categoría más específica gana: 1 > 3 > 2 > 4)

| Código | Definición | Regla de decisión |
|---|---|---|
| `acuerdo_ue_mercosur` | El acuerdo birregional en sí: negociación, firma, ratificación, contenido, comisiones de seguimiento | Menciona el acuerdo (con cualquier denominación: "acuerdo de asociación", "acuerdo Mercosur-UE", "acuerdo birregional") |
| `comercio_ue_sectorial` | Comercio con la UE o estados miembros por sector, sin referirse al acuerdo: carne (Hilton, 481), biodiesel, limones, acero, barreras sanitarias | UE o país miembro como mercado/contraparte + sector, sin el acuerdo |
| `eudr_trazabilidad_forestal` | EUDR, trazabilidad agropecuaria/forestal, certificación de origen o libre-deforestación, bosques nativos ligados a producción | El objeto es el régimen de trazabilidad/deforestación, aun sin mención de la UE |
| `mercosur_institucional` | Mercosur sin eje UE: cumbres, Parlasur, arancel externo común, comercio intra-bloque, otras negociaciones externas | Mercosur presente, UE ausente |
| `otro_descartar` | Falso positivo de etapa 1 | No encaja en ninguna de las anteriores |

### 2.2 Orientación

| Código | Definición | Indicadores en el título |
|---|---|---|
| `pro_liberalizacion` | Apoyo al acuerdo o a la apertura comercial | "beneplácito" por firma/avance, urgir ratificación, pedir acceso a mercado o aumento de cupo |
| `proteccionista_defensiva` | Rechazo o alerta por daño a sectores domésticos | "rechazo", "preocupación por el perjuicio", pedido de exclusión de sectores, suspensión de negociaciones |
| `condicionada` | Apoyo con salvaguardas o exigencias — la negociación de los términos de legibilidad (Scott §5 del plan) | Apoyo + reclamo de compensaciones, gradualidad, protección de sectores específicos, reciprocidad |
| `administrativa_neutra` | Sin toma de posición discernible | Pedidos de informes sin valencia, expresiones protocolares, creación de comisiones de seguimiento |

**Reglas de decisión**:
- Un pedido de informes es `administrativa_neutra` salvo que el propio título cargue valencia ("...ante el perjuicio que ocasionará..." → `proteccionista_defensiva`).
- "Preocupación" por incumplimiento de un cupo de exportación (Hilton) es `pro_liberalizacion` (reclama *más* comercio), no defensiva. La valencia se juzga respecto de la liberalización comercial, no del gobierno de turno.
- Si la orientación no es discernible desde el título → `administrativa_neutra` + confianza baja. Nunca adivinar por el autor o el bloque.
- Si `tema = otro_descartar` → orientación y saliencia = `no_aplica`.

### 2.3 Saliencia

| Código | Definición |
|---|---|
| `explicita` | El título menciona explícitamente el acuerdo UE-Mercosur o el reglamento EUDR |
| `relacionada` | Tema del eje sin mención explícita del acuerdo/EUDR |

### Output etapa 2 (JSON)

`tema`, `orientacion`, `saliencia`, `justificacion` (≤ 20 palabras, cita el fragmento del título que decide), `confianza` (alta/media/baja).

---

## Reglas transversales

- **Confianza**: `alta` = el título decide sin ambigüedad; `media` = requiere la regla de duda o una inferencia corta; `baja` = decisión por descarte o título insuficiente. Sirve para estratificar el gold standard (sobremuestrear `baja`).
- **Base de juicio**: solo el título. No inferir por autor, bloque, provincia ni fecha.
- **Idioma**: prompts y categorías en español; el manuscrito traduce las etiquetas al inglés (labels estables: p. ej. `condicionada` → *conditional support*).

## Validación prevista (del plan §3)

Gold standard ~400 títulos codificados a mano, muestreo estratificado (período × tipo × resultado del filtro, incluyendo negativos para medir recall). Umbrales: κ ≥ 0,75 en relevancia; si orientación < 0,70, colapsar categorías (candidato: `condicionada` → `pro_liberalizacion` con flag) y reportarlo.

## Anexo — Reglas de adjudicación (fijadas por el autor, 1-ago-2026)

Doctrina establecida al adjudicar los 15 desacuerdos del gold standard (los 15 fallos confirmaron al primer codificador; detalle en `gold/gold_adjudicacion.csv`). Estas reglas gobiernan la codificación humana; **no** modifican el prompt v1.2 congelado del anotador — sus desvíos respecto de estas reglas se reportan como error de anotación en Limitations:

1. Los órganos, programas e instrumentos formales del bloque son dominio C **sin restricción de materia** (educativo, DDHH, cooperativo incluidos). Ejemplos: IPPDH, protocolo educativo, Mercosur Educativo.
2. La trazabilidad agroalimentaria de cadenas productivas es dominio D **sin importar el rubro** (ganado, fruta, pesca, insumos agroquímicos).
3. Las declaraciones de interés por eventos de terceros quedan **excluidas aunque el tema sea del eje** (jornadas de trazabilidad, mesas redondas sobre órganos, congresos con actos accesorios de órganos).
4. Los topónimos "Ruta/Corredor del Mercosur" **no hacen relevancia** (análogo de la trampa NCM).
5. Operar el DIE/AEC (excepciones, reducciones) **es instrumento del bloque** (C), a diferencia de las medidas domésticas que solo citan posiciones NCM.
6. Disputas económicas con la UE o sus miembros entran por regla de duda **aunque el objeto sea inversión** y no comercio (YPF-Repsol).

## Anexo — Adenda de la revisión experta (fijada por el autor, 2-ago-2026)

Establecida durante la revisión experta completa del corpus (`corpus/README_revision_experta.md`). Igual que la doctrina de adjudicación, gobierna la codificación humana sin modificar el prompt v1.2 congelado:

7. **Categoría nueva `mercosur_simbolico`** (dominio C): proyectos cuyo objeto es una ocurrencia celebratoria, conmemorativa o cultural *del bloque mismo* — aniversarios del Tratado de Asunción y de la ley 23981, "Día del Mercosur" (adhesiones e institución del día), certámenes y ediciones de programas culturales oficiales (Mercosur Educativo "Manos Jóvenes"), papelería y leyendas conmemorativas. Criterio de deslinde con `mercosur_institucional`: **acto o decisión institucional del bloque → institucional; ocurrencia celebratoria → simbólico**, sin importar el vehículo legislativo (beneplácito, declaración de interés, ley). Cumbres, reuniones de órganos, firmas, membresías y presidencias siguen siendo `mercosur_institucional`. El "Día del Mercosur Ciudadano" (elección directa de parlamentarios, Protocolo Constitutivo del Parlasur) es institucional, no simbólico. La categoría alcanza también la **legislación permanente de símbolos del bloque** (izamiento de la bandera del Mercosur): decide el contenido litúrgico, no el vehículo ni la permanencia. Los programas y campañas oficiales *como políticas* son institucionales; sus ediciones, certámenes, jornadas y seminarios son simbólicos.
8. La regla 3 (eventos de terceros) **se reafirma y prevalece**: jornadas, seminarios o proyectos de terceros sobre temas del eje se descartan, no se recodifican como simbólicos (casos: jornada de difusión EUDR, proyecto binacional de conservación).

En el análisis, dominio C se reporta desagregado (institucional / simbólico) y la robustez de §4/§4.5 se corre con y sin `mercosur_simbolico`.

## Registro de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-08-01 | Versión inicial para piloto de 500 títulos |
| 1.1 | 2026-08-01 | Tras piloto v1 (497 títulos, 2,0% positivos en estrato aleatorio): exclusión NCM-como-nomenclador, dominio B restringido a contraparte europea identificable, exclusión de eventos/honores protocolares "del Mercosur". Prompt: `etapa1_system_v1_1.txt`. Ver `pilot/informe_piloto_etapa1.md` |
| 1.2 | 2026-08-01 | v1.1 sobre-corrigió (8 verdaderos positivos perdidos de 31 flips). Carve-outs: AEC ≠ NCM-nomenclador; OMC excluida solo sin la UE como parte; órganos oficiales y símbolos del bloque = C; trazabilidad agroalimentaria = D aunque sanitaria; C explicita adhesión de miembros e intra-Mercosur. Prompt: `etapa1_system_v1_2.txt`. **CONGELADA 1-ago-2026** (criterio de aceptación cumplido; decisión A+C del usuario) |
