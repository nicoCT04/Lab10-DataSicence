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

- [x] **Avance (22-oct)**: preguntas de gestión, alcance, paleta, herramienta, bosquejo y planificación
      → `docs/Diseno_Avance_Lab10.pdf` (fuente en `docs/diseno_avance.md`)
- [x] Panorama: V1 llegadas anuales por vía, **enlazada** con V2 detalle mensual y V3 mercados del año
- [x] Pronósticos: V4 observado vs. estimado (ARIMA(1,1,1), Holt-Winters, Seasonal Naive) + tabla de errores
- [x] Pronósticos: V9 error de los modelos por mes, enlazada al zoom de V4 junto con la tabla de errores
- [ ] Mercados y fronteras (V5 treemap región → país, V6 fronteras), Estacionalidad (V7, V8)
- [ ] Documento de diseño final — entrega 25-oct-2026
