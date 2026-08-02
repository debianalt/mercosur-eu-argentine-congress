# Prompts congelados — Paper A

Los archivos `*_system_v1.txt` son los prompts de sistema **verbatim** que consumen los scripts. No editarlos sin subir la versión (crear `_v2.txt`, nunca sobreescribir) y registrar el cambio en `taxonomia_v1.md` → Registro de versiones. Reproducibilidad (plan §3): el manuscrito reporta versión de prompt, modelo exacto y fecha de corrida.

## Etapa 1 — filtro de relevancia

| Parámetro | Valor |
|---|---|
| Prompt | `etapa1_system_v1_2.txt` (**CONGELADA 1-ago-2026**; `v1`/`v1_1` conservadas — cambios en `taxonomia_v1.md` → Registro de versiones) |
| Modelo | `claude-haiku-4-5` |
| Vía | Message Batches API (50% de descuento) |
| `max_tokens` | 500 |
| `temperature` | 0 |
| Salida | Structured outputs (`output_config.format`, JSON Schema estricto) |

Mensaje de usuario (template): `Título: "{titulo}"`

JSON Schema de salida:

```json
{
  "type": "object",
  "properties": {
    "relevante": {"type": "boolean"},
    "dominio": {"type": "string", "enum": ["A", "B", "C", "D", "ninguno"]},
    "confianza": {"type": "string", "enum": ["alta", "media", "baja"]}
  },
  "required": ["relevante", "dominio", "confianza"],
  "additionalProperties": false
}
```

## Etapa 2 — clasificación fina

| Parámetro | Valor |
|---|---|
| Prompt | `etapa2_system_v1.txt` |
| Modelo | `claude-sonnet-5` |
| Vía | Message Batches API |
| `max_tokens` | 2000 (thinking adaptativo activo por defecto en Sonnet 5; el tope cubre thinking + respuesta) |
| `output_config.effort` | `medium` |
| Sampling | Sin `temperature`/`top_p` (Sonnet 5 los rechaza; no aplican) |
| Salida | Structured outputs (JSON Schema estricto) |

Mensaje de usuario (template): `Título: "{titulo}"`

JSON Schema de salida:

```json
{
  "type": "object",
  "properties": {
    "tema": {"type": "string", "enum": ["acuerdo_ue_mercosur", "comercio_ue_sectorial", "eudr_trazabilidad_forestal", "mercosur_institucional", "otro_descartar"]},
    "orientacion": {"type": "string", "enum": ["pro_liberalizacion", "proteccionista_defensiva", "condicionada", "administrativa_neutra", "no_aplica"]},
    "saliencia": {"type": "string", "enum": ["explicita", "relacionada", "no_aplica"]},
    "justificacion": {"type": "string"},
    "confianza": {"type": "string", "enum": ["alta", "media", "baja"]}
  },
  "required": ["tema", "orientacion", "saliencia", "justificacion", "confianza"],
  "additionalProperties": false
}
```

## Pendientes de la fase de validación

- Corridas duplicadas sobre una submuestra para reportar estabilidad test-retest del anotador (plan §3).
- Congelar `_v1` → definitivo (o subir a `_v2`) tras el piloto de 500 títulos y antes del gold standard.
