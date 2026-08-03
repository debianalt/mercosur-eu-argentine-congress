# The Argentine Congress and the European Union deforestation regime, 2008–2025

Annotated corpus and replication materials for a study of how the European Union–Mercosur agreement and the European Union Deforestation Regulation register in the legislative record of a commodity-exporting country.

## What this is

The complete record of parliamentary initiatives tabled in the Argentine Chamber of Deputies between 2008 and 2025 comprises 110,500 items. This repository contains the subset that was screened and annotated to identify those engaging the European Union–Mercosur axis, the coding instrument used, the validation materials, and the scripts that produce every figure and table in the article.

**Headline counts.** 110,500 titles screened → 1,677 candidates (1.52 per cent) → 1,856 labelled titles once the gold standard is merged → 614 coded as relevant → 609 after expert review.

## Contents

```
data/
  corpus_annotated.csv      1,856 labelled titles. The analysed dataset.
  codebook_v1_2.md          Coding instrument, frozen before production coding,
                            with both appendices of adjudication rules.
  expert_review_log.csv     Before/after record of every correction made during
                            the expert review of relevant items.
  screen_worklist.csv       The 1,456 screened candidates sent for coding.
gold/
  gold_sample.csv           400-title validation sample (150 positives,
                            250 negatives with sectoral probes).
  gold_coder_labels.csv     Primary coder labels, recorded blind.
  gold_adjudication.csv     The 15 disagreements, adjudicated case by case,
                            with the rule each one established.
  gold_disagreements.csv    Full disagreement detail.
  marco_D_manual.csv        Hand-coding of the frame for all 152 forest-domain
                            items, with the lexical rule's code, the final hand
                            code and a per-item adjudication note.
prompts/                    Frozen prompts, model identifiers, output schemas
                            and run parameters. See prompts/README.md.
analysis/                   Derived tables and complete model output.
scripts/                    Python scripts that produce everything in analysis/.
```

## Column reference for `corpus_annotated.csv`

| Column | Meaning |
|---|---|
| `proyecto_id` | Chamber file identifier |
| `titulo` | Title as published by the Chamber |
| `publicacion_fecha`, `anio` | Date and year of tabling |
| `tipo` | Item type: bill, resolution, declaration, executive message |
| `autor` | Authoring legislator or body |
| `relevante` | Whether the item engages the axis |
| `dominio` | A explicit agreement · B sectoral trade with the EU · C Mercosur as an institution · D traceability and forest regulation |
| `tema` | Finer topic, including the symbolic subcategory within domain C |
| `orientacion` | pro-liberalisation · protectionist-defensive · conditional support · administrative-neutral |
| `saliencia` | Whether the agreement is named explicitly |
| `fuente_etiqueta` | Whether the label comes from the screened corpus or the adjudicated gold standard |
| `flag_revision`, `notas` | Review flag and coder notes |

Labels are in Spanish because the coding instrument is in Spanish and the source titles are in Spanish. The codebook gives the English gloss for every value.

## How the annotation was produced and validated

Coding combined a large language model working under a frozen codebook with human adjudication. Reliability was measured on the 400-title gold standard: Cohen's κ = 0.921 on relevance, recall 93.5 per cent, precision 96.7 per cent, *F*₁ = 0.951, and κ = 0.984 on domain among shared positives. The 15 disagreements were adjudicated individually and all 15 resolved in favour of the primary coder; each is recorded in `gold/gold_adjudication.csv` together with the rule it established.

The recall of the keyword screen was measured rather than assumed. Of 8,229 titles carrying no screen keyword and already annotated in earlier runs, three were flagged and all three adjudicated as not relevant, placing the upper bound of the 95 per cent confidence interval at approximately 0.036 per cent of the corpus.

Every relevant item was then reviewed by the author, working in tiers ordered by risk. Forty items carried at least one correction, 6.5 per cent of those reviewed.

The frame classification that separates the European deforestation regime from other external references and from domestic instruments has two layers. A documented lexical rule assigns a frame to every relevant item, and the author hand-coded all 152 forest-domain items against the frame definitions. Agreement between rule and coder is 147 of 152, 96.7 per cent, with Cohen's κ = 0.878; the hand codes are final. Each disagreement carries a written reason in `gold/marco_D_manual.csv`, documented against public administrative records (Boletín Oficial and the SENASA normative digest).

## Reproducing the analysis

```
python scripts/analisis_seccion4.py      # descriptive tables and the join
python scripts/analisis_seccion45.py     # panel and count models
python scripts/analisis_marco.py         # frame layer: lexical rule + hand codes
python scripts/analisis_comisiones.py    # committee referral profiles
python scripts/analisis_control.py       # the two control series
python scripts/analisis_robustez.py      # robustness of the count models
python scripts/fig1_attention_series.py  # Figure 1
python scripts/analisis_bosque_atencion.py   # forest comparison
```

Run the first two in that order: the second consumes the output of the first, and the frame and figure scripts consume outputs of both. The scripts expect the Chamber source files, which are redistributed by their publisher rather than here, and the forest script expects the external land-cover layers described below.

## External data sources

Forest loss is taken from Global Forest Change (Hansen et al. 2013, doi:10.1126/science.1244693), native cover from MapBiomas Argentina Collection 2 (https://argentina.mapbiomas.org), and planted area from the Inventario Nacional de Plantaciones Forestales of the Dirección Nacional de Desarrollo Foresto Industrial, Secretaría de Agricultura, Ganadería y Pesca (version of 23 April 2026). None of the three is redistributed here; each is available from its publisher under its own terms.

## Limitations that bear on reuse

The Chamber publishes titles and metadata but not full texts, so classification operates on summaries. The register covers the lower chamber; Senate items appear only when transmitted to it. Reliability was established independently for relevance and not for the finer dimensions, and the expert review was conducted with the assigned codes visible, which does not correct for anchoring toward the proposed label. The hand-coding of the frame was likewise conducted with the rule's assignments visible, and its agreement with the lexical rule is a consistency check, not an independent reliability estimate. The category of conditional support returns no cases, which is a finding rather than a coding gap, but users building on the scheme should be aware of it.

## Licence

Data and documentation are released under the Creative Commons Attribution 4.0 International licence. Code is released under the MIT licence.
