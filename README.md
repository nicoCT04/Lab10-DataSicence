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
│   ├── figures.py         # V1–V9 y mensajes sin datos
│   ├── theme.py           # significado de colores y formato común
│   └── models.py          # predicciones del Lab 1 y cálculo de errores
├── data/raw/              # Base_Migracion_2009-2026jun.xlsx
├── outputs/               # predicciones y métricas (csv)
├── tests/test_dashboard.py # recorridos de uso en navegador
├── scripts/export_design.py # exporta el documento final a PDF
└── docs/                  # diseño final editable, PDF y avance histórico
```

## Cómo ejecutar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py             # http://127.0.0.1:8050
```

Las predicciones y métricas ya están versionadas: **no hay que entrenar modelos para ejecutar el
tablero**. `python -m src.models` es un paso opcional de reproducción de las especificaciones del
Lab 1, no parte de la navegación ni un modelo nuevo. La primera ejecución lee el Excel y crea
`outputs/arrivals.parquet` (caché ignorada por Git); si se reemplaza la base, borrar esa caché antes
de ejecutar. Se requiere Python 3.11 o posterior. Se verificó con Python 3.11.2, Dash 4.4.1,
Plotly 6.3.0 y Chromium. Source Sans 3 se solicita a Google Fonts; sin conexión se utiliza la
fuente sans serif local de respaldo.

## Guía rápida

| Pestaña | Visualizaciones | Cómo explorar |
|--|--|--|
| Panorama | V1 anual, V2 mensual, V3 mercados | Elegir vías y años; clic en una barra de V1 cambia V2 y V3. Si se cambia el rango, el detalle permanece dentro de él. Las tarjetas de cabecera son la referencia fija de 2025. |
| Mercados y fronteras | V5 treemap, V6 puntos de ingreso | Entrar en región/país; V6 muestra las fronteras de esa selección. La barra superior permite volver. |
| Estacionalidad | V7 calendario, V8 cajas mensuales | Elegir llegadas o índice; clic en el calendario selecciona el año del perfil y clic en un punto del perfil resalta el año. Se pueden excluir 2020–2021 de las cajas. |
| Pronósticos | V4 observado/estimado, V9 error por mes | Elegir serie y modelos; usar zoom, barra de rango o «5 años»/«Todo». V9 y la tabla se recalculan con los meses visibles. |

Hay **nueve gráficos interactivos**, sin contar KPIs, controles ni tabla de métricas. Los filtros
vacíos muestran instrucciones y una combinación sin registros se distingue de una selección
sin vías. En los campos numéricos del rango, salir del campo (Tab) confirma el valor.

## Pruebas de uso

```bash
pip install -r requirements-dev.txt
python -m playwright install chromium
python -m unittest discover -s tests -v
```

Las pruebas abren su propio servidor en el puerto **8051**, que debe estar libre, y lo cierran al
terminar. Ejecutan clics y filtros reales en las cuatro pestañas: rango anual y detalles enlazados,
selección vacía y vía sin registros, región → fronteras, calendario → perfil, índice de un año
incompleto, zoom de pronósticos y modelos desmarcados. Comprueban errores del navegador y
respuestas HTTP 5xx. También revisan el ancho de 600 px y la separación entre leyenda y botones.
No sustituyen un estudio de usabilidad con directivos ni garantizan todos los dispositivos.

Para guardar capturas locales durante las pruebas, establecer `LAB10_SCREENSHOTS` con una carpeta
de artefactos; no es necesario versionarlas. Las correcciones finales mantienen el año de detalle
dentro del rango, distinguen el mensaje sin registros en V1 y separan leyenda y botones en V4.

## Documento y entregables

- [Documento de diseño final en PDF](docs/Diseno_Final_Lab10.pdf).
- [Fuente integrada editable](docs/diseno_final.md): preguntas, alcance, herramienta, bosquejo,
  paleta, justificación de V1–V9, planificación con responsables y contraste con el enunciado.
- [Avance original en PDF](docs/Diseno_Avance_Lab10.pdf), conservado como registro histórico;
  la fuente Markdown se integró en `diseno_final.md` y su versión anterior permanece en Git.
- Código y repositorio: https://github.com/nicoCT04/Lab10-DataSicence.

Para regenerar el PDF, después de instalar las dependencias de desarrollo y Chromium:

```bash
python scripts/export_design.py
```

La exportación utiliza Markdown y Chromium localmente, sin enviar los datos a un servicio externo.
La portada identifica al equipo de proyecto, sin firma personal.

## Interpretación y límites

Fuente: **Base de Migración 2009–2026, INGUAT / Migración**. Total = turistas + excursionistas;
no es una medida de ingresos económicos ni de sostenibilidad ambiental. 2026 solo incluye
enero–junio. La vía marítima deja de tener esa separación desde 2017: ausencia de registros no
equivale a cero visitantes. Las series describen patrones, no prueban sus causas.

Se reutilizan ARIMA(1,1,1), Holt-Winters y Seasonal Naive del Lab 1 para Total, Aérea y Terrestre.
El entrenamiento termina en marzo de 2021 y la prueba comprende abril de 2021–junio de 2026
(63 meses). V4 es una evaluación retrospectiva, no una proyección posterior a junio de 2026.
MAE resume el error absoluto medio; RMSE penaliza más los errores grandes; MAPE expresa el error
porcentual. Menor es mejor. La selección de períodos cortos cambia estas métricas y el ranking;
no debe interpretarse como evidencia de mejora frente a otro horizonte.

## Revisión de la rúbrica

| Criterio | Evidencia |
|--|--|
| Diseño intuitivo, color y legibilidad (30 puntos) | Cuatro pestañas por pregunta de gestión; significado estable de colores; ayudas y estados vacíos; revisión a 1440 y 600 px |
| Exploración y visualización (50 puntos) | V1–V9, tres modelos, enlaces independientes entre gráficos y niveles de detalle por año, región, fecha y medida |
| Funcionamiento e interacción (20 puntos) | Recorridos de navegador reproducibles y revisión visual; sin cambios en las predicciones ni métricas originales |

Este contraste no asigna una nota. El equipo debe comprobar inscripción en Canvas, entrega completa
del avance del 22-oct a las 17:20, permisos del docente para revisar el historial y entrega final
del 25-oct-2026. Los commits locales no demuestran una entrega en Canvas. La base se usa con fines
académicos; no se publica ni despliega el tablero sin autorización.

## Estado

- [x] **Avance (22-oct)**: preguntas de gestión, alcance, paleta, herramienta, bosquejo y planificación
      → `docs/Diseno_Avance_Lab10.pdf` (fuente integrada en `docs/diseno_final.md`)
- [x] Panorama: V1 llegadas anuales por vía, **enlazada** con V2 detalle mensual y V3 mercados del año
- [x] Pronósticos: V4 observado vs. estimado (ARIMA(1,1,1), Holt-Winters, Seasonal Naive) + tabla de errores
- [x] Pronósticos: V9 error de los modelos por mes, enlazada al zoom de V4 junto con la tabla de errores
- [x] Mercados y fronteras (V5 treemap región → país, V6 fronteras), Estacionalidad (V7, V8)
- [x] Pruebas de uso, estados sin datos y pulido de legibilidad
- [x] Documento de diseño final, PDF y README — entrega prevista 25-oct-2026

---

# Laboratorio 11 — MLOps del observatorio (Grupo 1, La Antigua Guatemala)

Flujo reproducible que estima los **visitantes únicos mensuales del polígono Antigua Guatemala**
para ene–feb 2026 (sin cobertura de telefonía) con el factor de reparto sobre la migración.
Alcance, fórmulas, períodos y diagrama: [docs/lab11/alcance.md](docs/lab11/alcance.md).

## Datos

Los datos institucionales **no se versionan ni se copian a imágenes**. Colocar en `data/raw/`:

- `BD_moviidad_mensual.xlsx` (carpeta compartida del proyecto; ignorado por Git)
- `Base_Migracion_2009-2026jun.xlsx` (ya incluido)

Las rutas se pueden cambiar en [mlops/config.toml](mlops/config.toml).

## Ejecutar el pipeline

```bash
source .venv/bin/activate
pip install -r requirements-mlops.txt
python -m mlops.pipeline                 # o --config otra_config.toml
python -m unittest tests.test_checks -v  # controles con datos sintéticos
```

Cada ejecución crea `mlops/runs/<run_id>/` con `config.toml`, `run_log.json` (inicio, fin, etapas,
advertencias, errores y publicación), `quality_report.json/.md`, `series.csv`, `params.json` y
`estimates.csv`. Si falla un control crítico, el flujo se detiene antes de estimar y no toca la
versión publicada.

| Módulo | Etapa |
|--|--|
| `mlops/sources.py` | Lectura y huella SHA-256 de las fuentes |
| `mlops/checks.py` | Seis controles de calidad y reporte |
| `mlops/procedure.py` | Serie destino-mes, factor de reparto y estimación |
| `mlops/pipeline.py` | Orquestación, registro por ejecución y publicación |

## Estado

- [x] **Avance (29-oct)**: alcance, diagrama, configuración, pipeline inicial y seis controles de calidad con pruebas
- [ ] Registro en MLflow y dos ejecuciones reproducibles
- [ ] Validación temporal (ventana expansiva), referencia y regla de aceptación
- [ ] Publicación de la versión aprobada e integración con el tablero
- [ ] Monitoreo, prueba controlada de fallo y restauración de versión
- [ ] Docker Compose (tablero + pipeline + MLflow) y documentación final
- [ ] Informe técnico en PDF — entrega 1-nov-2026
