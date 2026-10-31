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

Para el Lab 11 se usa **Python 3.14**, separado del entorno anterior del Lab 10.

```bash
python3.14 -m venv .venv-mlops
source .venv-mlops/bin/activate
pip install -r requirements-mlops.txt
python -m mlops.pipeline                 # o --config otra_config.toml
python -m unittest discover -s tests -p 'test_checks.py' -v
python -m unittest discover -s tests -p 'test_evaluation.py' -v
python -m unittest tests.test_publish tests.test_monitoring tests.test_antigua tests.test_drill -v
```

Cada ejecución crea `mlops/runs/<run_id>/` con `config.toml`, `run_log.json` (inicio, fin, etapas,
advertencias, errores y publicación), `quality_report.json/.md`, `series.csv`, `params.json` y
`estimates.csv` y `evaluation.json` (métricas de la validación y decisión de la regla de aceptación). Si falla un control crítico, el flujo se detiene antes de estimar y no toca la
versión publicada.

| Módulo | Etapa |
|--|--|
| `mlops/sources.py` | Lectura y huella SHA-256 de las fuentes |
| `mlops/checks.py` | Seis controles de calidad y reporte |
| `mlops/procedure.py` | Serie destino-mes, factor de reparto y estimación |
| `mlops/evaluation.py` | Validación temporal (ventana expansiva), referencia y regla de aceptación |
| `mlops/pipeline.py` | Orquestación, registro por ejecución y publicación |
| `mlops/tracking.py` | Experimento MLflow, parámetros, métricas, controles y artefactos |
| `mlops/reproduce.py` | Dos corridas sobre las mismas fuentes, comparación y exportación consultable |
| `mlops/monitoring.py` | Alertas de actualización, calidad y resultados frente a la versión vigente |
| `mlops/publish.py` | Publicación de la versión aprobada, listado y restauración de versiones |
| `mlops/drill.py` | Prueba controlada de fallo y recuperación en una carpeta aislada |
| `src/antigua.py` | Lectura de `published/current/` para la pestaña Antigua del tablero |

## Docker: desde un clon limpio

Requisitos: Git, Docker Engine o Docker Desktop activo y Docker Compose v2. Clonar el repositorio
privado con una cuenta autorizada. Colocar la base mensual en `data/raw/` antes de ejecutar.
Las fuentes se montan como solo lectura; **ningún Excel ni `.git` entra en la imagen**.
El tablero conserva los resultados CSV del Lab 10; no los regenera al abrirlo.

```bash
git clone https://github.com/nicoCT04/Lab10-DataSicence.git
cd Lab10-DataSicence
# Colocar BD_moviidad_mensual.xlsx en data/raw/ por el medio institucional.
docker compose --profile pipeline build
export GIT_COMMIT=$(git rev-parse HEAD)
docker compose run --rm pipeline
docker compose up -d tablero mlflow
docker compose logs --tail=100 tablero mlflow
```

En la máquina que ejecuta Docker: tablero `http://127.0.0.1:8050` y MLflow
`http://127.0.0.1:5001` (5000 suele estar ocupado por AirPlay en macOS). Los puertos se vinculan
solo a localhost; no son un despliegue público. El servicio `pipeline` no arranca con `up`:
es una ejecución explícita que termina. Antes de cada corrida, actualizar `GIT_COMMIT` y reconstruir
si cambió el código. No atribuir cambios sin commit a una versión limpia.

**Publicación:** solo una versión aprobada por la regla reemplaza `mlops/published/current/`; la
anterior pasa a `mlops/published/versions/<run_id>/`. Una corrida detenida o rechazada no toca
`current/`. Con las fuentes institucionales actuales la versión candidata se **rechaza** (razón MAE
1.38 > 1.25, ver `evaluacion.md`), así que el tablero muestra «Estimaciones no disponibles». No se
cambian umbrales para aprobarla.

## MLflow y reproducibilidad

Experimento: **observatorio-antigua**. Cada run tiene ID propio y el ID del pipeline como nombre/tag.
En la interfaz de MLflow seleccionar **Model training → Experiments → observatorio-antigua**;
la vista inicial GenAI/Traces no muestra estas ejecuciones de estimación.
Registra fecha, commit, huellas SHA-256, períodos, parámetros, controles, métricas reales y artefactos.
`environment.json` conserva versiones instaladas. Una ejecución detenida figura como `FAILED`, con
su causa y sin métricas si no llegó a evaluación. Una candidata rechazada puede ser `FINISHED`:
terminar el cálculo no equivale a autorizar su publicación.

```bash
export GIT_COMMIT=$(git rev-parse HEAD)
docker compose run --rm pipeline python -m mlops.reproduce --output mlops/runs/reproducibility
docker compose run --rm pipeline mlflow experiments search
# Usar el ID que corresponda a observatorio-antigua (1 en un almacén nuevo).
docker compose run --rm pipeline mlflow runs list --experiment-id 1
```

`comparison.json` comprueba fuentes/configuración/código, parámetros y evaluación, además de valores
y métricas con `rtol=1e-12`, `atol=1e-8`. Solo excluye ID y fecha de generación de la tabla comparada.
`runs_export.json` exporta la consulta completa de esos dos runs. Un error de comparación devuelve
código 1. **No confundir equivalencia con precisión o aprobación.**

La comprobación técnica inicial usa datos sintéticos y está identificada como tal en
[el informe](docs/lab11/informe.md). Falta repetir el comando con la base mensual institucional,
ausente en este equipo. Las pruebas unitarias usan almacenes temporales, no contaminan el experimento
de trabajo. La ejecución local sin Docker usa SQLite en `mlruns/mlflow.db`; para consultar ese
almacén desde el mismo entorno:

```bash
mlflow ui --backend-store-uri "sqlite:///$PWD/mlruns/mlflow.db" --host 127.0.0.1 --port 5001
```

No mezclar un almacén local con uno creado en Docker: los URI de artefactos contienen rutas absolutas
(`/app/mlruns/artifacts` dentro del contenedor). Conservar cada almacén con su entorno de consulta.

## Persistencia, entrega y recuperación

| Ruta del host (bind mount) | Contenido |
|--|--|
| `data/` | Fuentes institucionales, solo lectura para los contenedores |
| `mlruns/` | SQLite y artefactos de MLflow |
| `mlops/runs/` | Logs, controles, parámetros, evaluación, candidatos y exportaciones |
| `mlops/published/` | `current/` (versión que lee el tablero), `versions/` (anteriores) e `history.jsonl` |

```bash
docker compose down
docker compose up -d tablero mlflow
```

Eliminar contenedores no elimina estas carpetas. No borrarlas para «reiniciar» el tablero.
Para entregar los registros, detener primero los servicios y copiar **juntas** `mlruns/` y
`mlops/runs/` por Canvas/OneDrive autorizado; incluir `mlops/published/` cuando existan versiones.
Las capturas y JSON del informe complementan, pero no sustituyen, la base y sus artefactos.
No subir fuentes ni registros institucionales a servicios públicos.

**Restauración de resultados:** ver la sección siguiente. Para regresar el **código** a una versión
conocida, detener servicios, usar `git switch --detach <commit_verificado>`, reconstruir y conservar
los volúmenes. Regresar el código no restaura las estimaciones; para eso se usa `mlops.publish restore`.

## Tablero, monitoreo y recuperación

**Pestaña «Antigua Guatemala».** Lee solo `mlops/published/current/` (`estimates.csv`, `series.csv` y
`metadata.json`); no lee los Excel ni ejecuta el pipeline. Muestra lo observado con línea continua y
las estimaciones con rombos morados; ene–feb 2026 quedan como hueco en la línea observada, nunca como
cero. Incluye fecha de actualización, margen de error de la validación (meses evaluados) y una
advertencia de limitaciones. Los detalles de ejecuciones quedan en MLflow. La versión vigente se relee
al abrir la pestaña: una publicación o restauración se ve sin reiniciar el tablero. El filtro de
periodo solo recorta los datos ya cargados. `PUBLISHED_DIR=<carpeta>` muestra otra carpeta de versiones.

**Monitoreo.** Cada corrida escribe `monitoring.json` y la sección `monitoring` de `run_log.json`, y
registra `monitoring.<verificación>` en MLflow. Las alertas piden revisión; no deciden la publicación.

| Verificación | Alerta cuando |
|--|--|
| Actualización | Telefonía no llega al último mes de ajuste, migración no llega al último mes de ajuste o estimación, faltan meses en los resultados o no hay versión aprobada publicada |
| Calidad | Faltantes o duplicados crecen frente a la versión vigente en ≥ 5 filas y > 20 %, o se pierden meses de cobertura (`[monitoring]` en la config) |
| Resultados | Estimaciones negativas o no finitas, variación entre meses consecutivos o frente a la versión vigente > 40 % (`acceptance.max_monthly_change`). El error predictivo solo se recalcula si aparece el observado de un mes estimado |

**Versiones y restauración.**

```bash
python -m mlops.publish list                       # vigente y anteriores
python -m mlops.publish restore <run_id>           # vuelve a poner una versión anterior aprobada
# en Docker (published está montado con escritura en el servicio pipeline):
docker compose run --rm pipeline python -m mlops.publish restore <run_id>
```

`restore` solo acepta versiones aprobadas completas de `versions/`; la vigente pasa a `versions/` y
queda en `history.jsonl`. Recargar la pestaña Antigua para ver la versión restaurada.

**Prueba controlada de fallo y recuperación.**

```bash
python -m mlops.drill                                   # sintético: denominador cero
python -m mlops.drill --problem columna                 # o duplicado
python -m mlops.drill --data real --problem denominador # copia de las fuentes institucionales
PUBLISHED_DIR=mlops/test_runs/<carpeta>/published python app.py   # ver el resultado en el tablero
# en Docker, guardar la carpeta en un volumen montado:
docker compose run --rm pipeline python -m mlops.drill --output mlops/runs/drill
```

Todo ocurre en una carpeta aislada (`mlops/test_runs/drill-<fecha>/` por defecto) con sus propias
fuentes, corridas, versiones y almacén MLflow; nunca toca `data/raw` ni `mlops/published`. Con datos
sintéticos: publica una versión inicial, introduce el problema (el pipeline se detiene y `current/` no
cambia), publica la entrega corregida y restaura la versión inicial. Con `--data real` hace los pasos
de fallo y corrección sobre una copia de las fuentes. Resultados en
[docs/lab11/evidencia/](docs/lab11/evidencia/).

## Informe integrado

[PDF](docs/lab11/Informe_Lab11.pdf) y [fuente editable](docs/lab11/informe.md). Integra el alcance
y la evaluación ya escritos con trazabilidad/Docker; identifica las evidencias aún pendientes.
Para regenerarlo usando las dependencias de desarrollo del Lab 10:

```bash
python scripts/export_design.py --source docs/lab11/informe.md --output docs/lab11/Informe_Lab11.pdf
```

## Estado

- [x] **Avance (29-oct)**: alcance, diagrama, configuración, pipeline inicial y seis controles de calidad con pruebas
- [x] Registro en MLflow y comprobación reproducible sintética
- [ ] Repetir y entregar registros con las fuentes institucionales completas
- [x] Validación temporal (ventana expansiva), referencia y regla de aceptación → [docs/lab11/evaluacion.md](docs/lab11/evaluacion.md)
- [x] Publicación de la versión aprobada e integración con el tablero (pestaña Antigua)
- [x] Monitoreo, prueba controlada de fallo y restauración de versión
- [x] Docker Compose (tablero + pipeline + MLflow) y documentación
- [x] PDF integrado del estado disponible, sin firma personal
- [ ] Incorporar al PDF la publicación, monitoreo y recuperación verificados — entrega 1-nov-2026
