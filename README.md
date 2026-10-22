# Laboratorio 10 — Visualización interactiva (CC3084 Data Science, UVG, Sem. II 2026)

Tablero interactivo del **observatorio de turismo sostenible** para Guatemala, dirigido a
directivos del sector turístico. Usa la base de **ingreso de viajeros internacionales**
(ene-2009 a jun-2026) y reutiliza los modelos de pronóstico del Laboratorio 1.

## Estructura

```text
.
├── app.py                 # tablero (Plotly Dash)
├── assets/style.css       # estilos y paleta
├── src/
│   ├── data.py            # carga y agregaciones de la base
│   └── models.py          # predicciones de los modelos del Lab 1
├── data/raw/              # Base_Migracion_2009-2026jun.xlsx
├── outputs/               # predicciones y métricas (csv)
└── docs/                  # documento de diseño
```

## Cómo ejecutar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.models      # genera outputs/predictions.csv y outputs/metrics.csv
python app.py             # http://127.0.0.1:8050
```

## Estado

- [x] Avance: preguntas de gestión, alcance, paleta, planificación, bosquejo y herramienta (`docs/`)
- [ ] Tablero completo (8 visualizaciones) — entrega final 25-oct-2026
