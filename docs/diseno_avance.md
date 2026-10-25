---
title: "Laboratorio 10 — Visualización interactiva"
subtitle: "Documento de diseño · Avance"
author: "Nicolás Concuá — 23197 · Ciencia de Datos (CC3084), Universidad del Valle de Guatemala"
date: "22 de octubre de 2026"
---

# 1. Contexto y usuarios

El tablero forma parte del **observatorio de turismo sostenible de Guatemala**. Usa la base de
**ingreso de visitantes internacionales** (INGUAT / Migración, ene-2009 a jun-2026) y los modelos de
pronóstico del Laboratorio 1. Está dirigido a **directivos del sector turístico** que no necesariamente
conocen estadística: cada vista abre con la pregunta que responde y una instrucción corta de uso.

Repositorio: <https://github.com/nicoCT04/Lab10-DataSicence>

# 2. Preguntas de gestión seleccionadas

| # | Pregunta de gestión | Para qué la usa un directivo | Vistas |
|--|----------------|----------------|------|
| P1 | ¿Cómo evolucionan las llegadas y cuánto se ha recuperado el turismo frente a 2019? | Fijar metas anuales y medir la recuperación pospandemia | KPIs, V1 |
| P2 | ¿En qué meses se concentra la demanda (temporada alta y baja)? | Planificar capacidad, personal y campañas para temporada baja; anticipar la presión estacional sobre los destinos | V2, V7, V8 |
| P3 | ¿Qué mercados de origen aportan más visitantes y cómo cambia su peso? | Priorizar la promoción y medir la dependencia de pocos mercados | V3, V5 |
| P4 | ¿Por qué vías y puntos fronterizos ingresan los visitantes? | Priorizar inversión en infraestructura y servicios de frontera | V1, V6 |
| P5 | ¿Qué tan confiables son las estimaciones de llegadas y qué modelo conviene como referencia? | Decidir cuánto confiar en un pronóstico al presupuestar | V4, V9, tabla de modelos |

# 3. Alcance del tablero

**Incluye**

- Llegadas mensuales de **turistas + excursionistas** (la definición estable de todo el periodo, igual
  que en el Lab 1), por año, mes, vía de ingreso, frontera y mercado de residencia.
- Resultados de **tres modelos sencillos del Laboratorio 1**: ARIMA(1,1,1), Holt-Winters y Seasonal
  Naive, para las series Total, Aérea y Terrestre, con el mismo split 70/30 (entrenamiento hasta mar-2021).
  **No se entrenan modelos nuevos**: `src/models.py` reproduce las mismas especificaciones y obtiene las
  mismas métricas del Lab 1 (p. ej., MAE del ARIMA sobre el Total = 154,494).
- Mínimo **8 visualizaciones interactivas**, con al menos 2 enlazadas y con control del nivel de detalle
  (año → mes, región → país, rango de fechas).

**No incluye / limitaciones**

- Indicadores de gasto, ocupación hotelera, empleo o impacto ambiental: la base solo registra llegadas.
  La concentración estacional se usa como **aproximación** de la presión sobre los destinos.
- Vía marítima: desde 2017 la base no separa turistas y excursionistas por esta vía; solo se muestra
  hasta donde existe ese dato.
- 2026 contiene solo ene-jun; se marca como año parcial.
- Los datos permiten describir **patrones**, no atribuir causas. Los pronósticos se presentan como
  **estimaciones** distinguidas visualmente de lo observado.

# 4. Herramienta seleccionada: Plotly Dash (Python)

| Criterio | Plotly Dash | Streamlit | R Shiny | Voilà / Panel |
|--------|--------|--------|-------|-------|
| Gráficos enlazados por clic | Nativo (`clickData` + callbacks) | Limitado, re-ejecuta todo el script | Sí | Parcial |
| Zoom / nivel de detalle | Nativo en Plotly (zoom, range slider, treemap) | Vía Plotly | Vía plotly/ggiraph | Vía Bokeh/Plotly |
| Reutiliza el código del Lab 1 | Sí (Python, statsmodels) | Sí | No (Lab 1 en Python) | Sí |
| Control del diseño (CSS, paleta) | Total (CSS propio) | Limitado | Alto | Medio |
| Licencia | MIT, gratuita | Apache 2.0 | GPL | BSD |

Se eligió **Dash** porque el requisito central son las **visualizaciones enlazadas**: un callback
conecta el clic en un gráfico con la actualización de otros, sin recargar la página. Además, el modelado
de los Labs 1 y 2 está en Python, por lo que los modelos se reutilizan sin traducirlos, y el CSS propio
permite aplicar la paleta y la tipografía con el mismo significado en todo el tablero.

# 5. Paleta de colores y tipografía

| Rol | Color | Uso y justificación |
|-------|-------|------------------|
| Tinta / Observado | `#1E2A38` | Encabezado, textos y la línea de **datos observados**. Azul casi negro: máximo contraste (AA) sin la dureza del negro puro. |
| Vía Aérea | `#0072B2` | Paleta **Okabe-Ito**, diseñada para ser distinguible con daltonismo. Azul = aire. |
| Vía Terrestre | `#E69F00` | Naranja tierra, opuesto al azul en el círculo cromático (complementario): máxima separación entre las dos vías principales. |
| Vía Marítima | `#009E73` | Verde azulado = mar; tercer color Okabe-Ito. |
| Magnitud sin categoría | `#4A6382` | Azul gris neutro para rankings (mercados), así no se confunde con ninguna vía. |
| Segundo nivel de jerarquía | `#C9D4E2` | El mismo neutro aclarado: países dentro de su región en el treemap (V5). |
| Escala secuencial | `#E8EDF3` → `#7F93AD` → `#1E2A38` | Un solo tono, de claro (poco) a tinta (mucho), para el calendario (V7); no usa ningún color de vía ni de modelo. |
| Estimaciones (modelos) | `#6A3D9A`, `#CC79A7`, `#8C8C8C` | Morado, rosa y gris, tonos que **nunca** se usan para datos observados; además cada modelo tiene su tipo de línea (continua, raya-punto, punteada), así no depende solo del color. |
| Contexto | `#ECEFF3` | Franja gris para periodos especiales (COVID-19, periodo de evaluación). |
| Fondo / tarjetas | `#F5F7FA` / `#FFFFFF` | Fondo claro de baja saturación para que el color se reserve a los datos. |
| Alerta | `#E69F00` borde + `#FFF8EC` | Avisos de limitaciones. |

**Reglas**: (1) un color significa lo mismo en todas las pestañas; (2) la selección se resalta con
opacidad (seleccionado al 100 %, resto al 35 %) en lugar de introducir colores nuevos; (3) las
etiquetas *Observado* y *Estimado* separan hallazgos de estimaciones.

**Tipografía**: *Source Sans 3* (Google Fonts, licencia libre), sans serif humanista de alta
legibilidad en pantalla. Jerarquía: título 24 px, título de gráfico 17 px, cuerpo 15 px, ayudas y ejes
13 px. Los ejes usan sufijos (1M, 250k) para leer cifras grandes de un vistazo.

# 6. Bosquejo de la interfaz y navegación

![Bosquejo de la pestaña Panorama: KPIs, controles y tres gráficos enlazados](img/bosquejo.png){width=92%}

La navegación sigue el orden en que un directivo se hace las preguntas: **de lo general a lo
particular** y de lo observado a lo estimado.

1. **Panorama** (P1, P2, P4): KPIs, controles globales (vías y rango de años) y V1 → V2/V3 enlazadas.
2. **Mercados y fronteras** (P3, P4): treemap región → país (acercar o alejar el nivel de detalle) enlazado
   con las fronteras de ingreso.
3. **Estacionalidad** (P2): mapa de calor año × mes y perfil mensual.
4. **Pronósticos** (P5): observado vs. estimado, error por mes y tabla comparativa de modelos, con el
   aviso de limitaciones.

Cada pestaña sigue la misma plantilla: pregunta → KPIs → controles → gráficos con texto de ayuda.
Cuando un filtro deja un gráfico sin datos, este muestra un mensaje que lo explica en vez de un gráfico vacío.

# 7. Visualizaciones (estado del avance)

| # | Visualización | Tipo y por qué | Interacción | Estado |
|--|------|---------|--------|----|
| V1 | Llegadas anuales por vía | Barras apiladas: compara totales anuales y la composición por vía | Clic en un año (filtra V2 y V3), filtro de vías, rango de años, tooltip | **Funcional** |
| V2 | Detalle mensual del año | Líneas: la secuencia de meses muestra la temporada alta y baja | Enlazada a V1, filtro de vías, zoom | **Funcional** |
| V3 | Principales mercados del año | Barras horizontales ordenadas: ranking con nombres largos legibles | Enlazada a V1, tooltip con % | **Funcional** |
| V4 | Observado vs. estimado | Líneas temporales con franja de evaluación | Serie, modelos visibles, range slider, botones 5 años / todo | **Funcional** |
| V5 | Mercados por región → país | Treemap: jerarquía y proporción; clic para acercar o alejar | Drill-down, enlazada con V6, filtro de vías y años | **Funcional** |
| V6 | Llegadas por frontera | Barras horizontales apiladas por vía: ranking de puntos de ingreso | Enlazada a V5, tooltip con % | **Funcional** |
| V7 | Calendario de llegadas | Mapa de calor año × mes: patrones estacionales de 17 años de un vistazo | Clic en un año (resalta y actualiza V8), llegadas o índice, vías, rango de años | **Funcional** |
| V8 | Perfil estacional | Boxplot por mes: variabilidad de cada mes entre años | Enlazada con V7 en ambos sentidos, excluir pandemia, vías y periodo | **Funcional** |
| V9 | Error de los modelos por mes | Barras agrupadas: cuándo y cuánto falla cada modelo | Enlazada al zoom y a la barra de rango de V4, a la serie y a los modelos | **Funcional** |

Las tarjetas KPI, los controles, los textos y la tabla de métricas son complementarios y no se cuentan
como visualizaciones.

![Pestaña Panorama funcional: el año seleccionado (2025) se resalta en V1 y actualiza V2 y V3](img/panorama.png){width=92%}

**Lectura de ejemplo (observado)**: en 2025 llegaron 3.35 M de visitantes, el 81 % del nivel de 2019;
El Salvador es el principal mercado y la vía terrestre concentra cerca de dos tercios de las llegadas.
**Estimación**: los tres modelos subestiman 2022-2026 porque se entrenaron con datos que terminan en plena
pandemia; el ARIMA(1,1,1) es el de menor error (MAPE 59 % en el Total) y se presenta solo como referencia.

# 8. Pestaña Pronósticos: V4, V9 y comparación de modelos

Esta pestaña responde la pregunta P5, qué tan confiables son las estimaciones de llegadas y qué modelo
conviene como referencia. Usa las predicciones de los tres modelos sencillos del Laboratorio 1,
ARIMA(1,1,1), Holt-Winters y Seasonal Naive, entrenados hasta marzo de 2021 y evaluados con los 63 meses
de abril de 2021 a junio de 2026 que no vieron. No se entrena ningún modelo nuevo, `src/models.py`
reproduce las predicciones y las funciones de error las resumen, y sobre el periodo completo dan
exactamente las mismas métricas que `outputs/metrics.csv`.

## V4. Observado frente a estimado

El dato es una serie de tiempo mensual, así que el gráfico adecuado es el de líneas, donde la pendiente
se lee como crecimiento y la distancia entre dos líneas como error. Lo observado va en el azul casi negro
de la paleta y cada modelo en un color que nunca se usa para datos observados, con un tipo de línea
distinto, de modo que la comparación no dependa solo del color. Una franja gris marca el periodo de
evaluación, donde los modelos estiman sin haber visto los datos. La barra de rango inferior y los botones
de cinco años o todo el periodo permiten acercar o alejar el nivel de detalle. Al prender o apagar
modelos el gráfico conserva el zoom, y solo se reinicia al cambiar de serie.

## V9. Error de los modelos por mes

V4 muestra que los modelos fallan, pero no cuándo. V9 responde esa segunda pregunta con el error
promedio de cada modelo según el mes del año. Es una variable cuantitativa sobre dos categorías, mes y
modelo, por eso usamos barras agrupadas, que comparan longitudes desde una base común, la forma más
precisa de comparar magnitudes. Los meses van en su orden natural de enero a diciembre para que se lea
la temporada, y cada modelo conserva su color de V4 y además una trama distinta en sus barras, para que
se distinga sin depender del color. Al pasar el cursor sobre una barra se ve si el modelo se quedó corto
o se pasó, y cuántos meses entran en el promedio.

V9 está enlazada con V4. Al acercar V4 o mover su barra de rango, V9 y la tabla de errores se
recalculan solo con los meses visibles, y un rótulo indica el periodo analizado. Es la forma de
aumentar o disminuir el nivel de detalle de la comparación, desde los 63 meses completos hasta un
solo año. Si el periodo elegido no contiene meses de evaluación, o si no hay modelos seleccionados, el
gráfico muestra un mensaje que explica qué hacer en lugar de quedar vacío.

## Comparación de modelos

La tabla de errores acompaña a V9 y no cuenta como visualización. Ordena los modelos de menor a mayor
error y muestra tres métricas con una explicación en lenguaje llano. El MAE es cuántos visitantes se
equivoca en promedio cada mes, el RMSE es parecido pero castiga más los errores grandes y el MAPE es el
error como porcentaje de lo observado. También indica cuántos meses de evaluación entran en el periodo,
porque un error calculado con pocos meses es menos confiable.

| Serie | Mejor modelo | MAE | MAPE |
|---|---|---|---|
| Total | ARIMA(1,1,1) | 154,494 | 59.2 % |
| Aérea | ARIMA(1,1,1) | 33,226 | 33.3 % |
| Terrestre | ARIMA(1,1,1) | 123,363 | 75.5 % |

## Lo que el directivo puede leer, y sus límites

Lo observado en la pestaña es que los tres modelos subestiman las llegadas en el 90 % al 100 % de los
meses y que su mayor error cae en diciembre, el pico de la temporada, salvo en la vía aérea, donde el
Holt-Winters y el Seasonal Naive fallan más en julio. También se observa que el error crece con el
horizonte. Con el total, el ARIMA se equivoca en un 31 % durante el primer año después del
entrenamiento y en un 66 % entre 2024 y 2026.

La interpretación, que no es un hallazgo directo de los datos, es que los modelos aprendieron con una
serie que termina en plena pandemia y proyectan ese nivel deprimido, por eso no anticipan la
recuperación y se quedan más cortos en los meses de mayor demanda. El ARIMA(1,1,1) es el de menor error
en las tres series, pero se presenta solo como referencia para comparar modelos y no como cifra oficial.
Para planificar, un directivo debería usar estos pronósticos a corto plazo y reentrenarlos con datos
recientes, y tratar con cautela cualquier estimación de diciembre. El aviso de limitaciones al pie de la
pestaña lo dice de forma explícita.

# 9. Pestañas Mercados y fronteras y Estacionalidad: V5 a V8

Estas dos pestañas responden las preguntas P2, P3 y P4: de dónde vienen los visitantes, por dónde entran
y en qué meses se concentra la demanda. Todo lo que muestran es **observado**, por eso cada gráfico lleva
la etiqueta *Observado* y ninguno usa los colores reservados a las estimaciones.

## V5. Visitantes por región y país de residencia

El dato es jerárquico, región que contiene países, y lo que interesa al directivo es el **peso** de cada
mercado dentro del total. El treemap representa las dos cosas a la vez: el área de cada rectángulo es
proporcional a sus visitantes y los países quedan dentro del rectángulo de su región. Frente a un gráfico
de pastel, el treemap admite decenas de países sin volverse ilegible, y frente a unas barras conserva la
jerarquía. Es también la forma de **aumentar o disminuir el nivel de detalle**: al inicio solo se ven
las regiones; un clic en una región la abre y muestra sus países, y un clic en la barra superior vuelve
al nivel anterior. Para que los rectángulos pequeños no saturen la vista, en cada región se muestran los
diez países más grandes y el resto se agrupa en «Otros países». Se excluyen los guatemaltecos residentes
en el exterior, igual que en V3, y la región sin código de la base se rotula «Sin región».

El color no codifica una categoría nueva, para no competir con los colores de las vías: las regiones
usan el azul gris neutro de la paleta y los países el mismo tono aclarado, de modo que el color solo
indica el nivel de la jerarquía. Cada rectángulo muestra su nombre, sus visitantes y su porcentaje del
total, y el tooltip agrega el porcentaje dentro de su región.

## V6. Puntos de ingreso de la selección

V6 responde «¿por dónde entran?» para lo que el usuario eligió en V5. Son 21 puntos con nombres largos,
por eso usamos barras horizontales ordenadas de mayor a menor, que dejan leer cada nombre y comparar
longitudes desde una base común. Aquí el color sí tiene significado y es el mismo de todo el tablero:
azul aérea, naranja terrestre y verde marítima, así que se ve de inmediato qué puntos son aeropuertos y
cuáles pasos terrestres.

V5 y V6 están **enlazadas**: al hacer clic en una región o en un país de V5, V6 se recalcula solo con
esos visitantes y su título lo indica (por ejemplo, «Puntos de ingreso de visitantes de El Salvador
(América Del Centro), 2025»). Al volver a la raíz, V6 muestra de nuevo a todos los visitantes. Las
tarjetas de la pestaña acompañan la lectura: visitantes extranjeros del periodo, mercado principal, peso
de los tres mayores mercados (una medida simple de dependencia) y principal punto de ingreso de la
selección. Si no hay vías seleccionadas, o si la combinación de vías y años no tiene registros, ambos
gráficos muestran un mensaje que lo explica.

**Lectura de ejemplo (2025, observado)**: América del Centro aporta el 64 % de los visitantes extranjeros
y América del Norte el 25 %; El Salvador por sí solo representa el 47 % y los tres mayores mercados el
75 %, una concentración alta. Los centroamericanos entran sobre todo por tierra (Valle Nuevo, 31 %),
mientras que el 85 % de los norteamericanos y el 70 % de los europeos entran por La Aurora. Para un
directivo esto separa dos públicos con infraestructuras distintas: servicios fronterizos para el mercado
regional y conectividad aérea para los mercados de larga distancia. Los datos muestran por dónde entran
los visitantes, no por qué eligen esa vía.

## V7. Calendario de llegadas: año por mes

Para ver la estacionalidad de 17 años de un vistazo, el mapa de calor año × mes es el gráfico más
compacto: cada fila es un año, cada columna un mes y la intensidad del color es el número de llegadas.
Las columnas que se oscurecen año tras año son la temporada alta y las filas claras muestran caídas como
la de 2020. Al ser una magnitud ordenada, usamos una **escala secuencial de un solo tono** que va del gris
azulado claro (pocas llegadas) a la tinta (muchas), derivada del neutro de la paleta para no confundirse
con ninguna vía. Los meses sin datos (julio a diciembre de 2026) se marcan con ✕ en lugar de quedar en
blanco, y el año elegido se enmarca con un recuadro.

El control **Medida** cambia entre llegadas e **índice estacional**, que compara cada mes con el mes
promedio de su propio año (100). El índice quita el efecto del crecimiento o la caída entre años y deja
solo la forma de la temporada; se calcula únicamente para años completos. Su escala de color se fija
entre 60 y 140 porque los primeros meses de 2020, comparados con un año hundido por la pandemia, llegan
a 400 y apagarían el resto del calendario; el tooltip sigue mostrando el valor real.

## V8. Perfil estacional

V7 muestra cada mes de cada año; V8 resume cuál es el mes **típico** y qué tan estable es ese patrón.
Por eso usamos un diagrama de caja por mes: la línea central es la mediana de los años y la caja abarca
la mitad central, así que una caja corta significa un mes estable y una larga, un mes que varía mucho
entre años. Encima se dibujan los años como puntos y, con la tinta de lo observado, la línea del año
elegido, para comparar un año concreto con el patrón típico. Por defecto se excluyen 2020-2021 de las
cajas, porque la pandemia deformaría el patrón, aunque se pueden incluir desmarcando la casilla.

V7 y V8 están **enlazadas en ambos sentidos**: un clic en una fila del calendario dibuja ese año en V8,
y un clic en un punto de V8 enmarca su año en V7. Las tarjetas resumen el perfil con el índice, que es
comparable entre años: mes más fuerte y más débil, diferencia entre pico y valle, y cuántos años
completos entran en el cálculo. Si el año elegido queda fuera del rango o no tiene un año completo de
datos, una nota bajo el gráfico lo explica.

**Lectura de ejemplo (aérea y terrestre, 2009-2026 sin 2020-2021, observado)**: diciembre es el mes más
fuerte (índice 135, un 35 % más que un mes promedio) y febrero el más débil (81); el pico supera al valle
en un 66 %. Septiembre (85) y mayo (88) también son meses bajos. La vía aérea tiene un segundo pico en
julio (116), mientras que la terrestre concentra más su temporada en diciembre (140) y varía más entre
años. Para planificar, esto sugiere reforzar capacidad y personal en diciembre y julio, y dirigir las
campañas a febrero, mayo y septiembre. Como la base solo registra llegadas, la concentración estacional
es una **aproximación** de la presión sobre los destinos, no una medida de ella.

# 10. Planificación de tareas

Responsable de todas las tareas: **Nicolás Concuá (23197)**.

| # | Tarea | Fecha de terminación | Estado |
|--|------------------|------|----|
| 1 | Preguntas de gestión, alcance y elección de herramienta | 22-oct-2026 | Hecho |
| 2 | Paleta, tipografía, bosquejo y navegación | 22-oct-2026 | Hecho |
| 3 | Preparación de datos y predicciones del Lab 1 (`src/`) | 22-oct-2026 | Hecho |
| 4 | Pestaña Panorama: KPIs, V1-V3 enlazadas | 22-oct-2026 | Hecho |
| 5 | Pestaña Pronósticos: V4 y tabla de modelos | 22-oct-2026 | Hecho |
| 6 | Pestaña Mercados y fronteras: V5-V6 enlazadas | 24-oct-2026 | Hecho |
| 7 | Pestaña Estacionalidad: V7-V8 | 24-oct-2026 | Hecho |
| 8 | V9 (error por mes) y comparación de modelos | 23-oct-2026 | Hecho |
| 9 | Pruebas de uso, mensajes vacíos, legibilidad y corrección de errores | 24-oct-2026 | Pendiente |
| 10 | Documento de diseño final (PDF) y README | 25-oct-2026 | Pendiente |
