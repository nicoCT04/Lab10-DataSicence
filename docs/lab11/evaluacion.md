# Lab 11 — Validación temporal y regla de aceptación

Observatorio de Inteligencia Turística · Grupo 1 · La Antigua Guatemala. Sección a cargo de
Fernando Rueda. Código en [`mlops/evaluation.py`](../../mlops/evaluation.py), pruebas en
[`tests/test_evaluation.py`](../../tests/test_evaluation.py) y umbrales en
[`mlops/config.toml`](../../mlops/config.toml).

## 1. Esquema de validación

El objetivo es saber qué tan bien estimaría el factor de reparto un mes que no tiene telefonía,
como enero y febrero de 2026. Para medirlo ocultamos meses que sí tienen dato observado y los
estimamos como si no existieran.

Usamos una ventana expansiva sobre los meses de `periods.evaluation`, abril, mayo y junio de 2026.
Para cada mes evaluado, el factor se calcula solo con los meses observados anteriores a él y se
multiplica por la migración de ese mes. Así nunca se usa información posterior al mes que se
estima, y cada mes evaluado incorpora un mes más de historia que el anterior.

| Mes evaluado | Meses usados para el factor | Factor | Estimado | Observado |
|--|--|--|--|--|
| abr 2026 | sep–dic 2025 y mar 2026 (5) | 3.345 | 872,959 | 939,242 |
| may 2026 | los anteriores y abr 2026 (6) | 3.388 | 817,478 | 926,444 |
| jun 2026 | los anteriores y may 2026 (7) | 3.452 | 848,148 | 878,775 |

Enero y febrero de 2026 nunca entran a la evaluación, porque no tienen valor observado
comparable. Si la configuración pidiera evaluar un mes sin telefonía, `evaluate` se detiene con
un error en lugar de calcular un error contra un vacío.

La prueba `test_future_months_do_not_change_the_estimate` comprueba de forma automática que no
hay fuga de información: cambia por completo los factores de mayo y junio y verifica que la
estimación de abril no se mueve.

## 2. Referencia sencilla

Comparamos con el último valor observado (`procedure.baseline = "last_value"`), que estima cada
mes con los visitantes del mes observado inmediatamente anterior. Se evalúa en los mismos tres
meses y con la misma restricción temporal, así que ninguno de los dos procedimientos ve el futuro.

## 3. Métricas

| Métrica | Factor de reparto | Último valor | Qué significa |
|--|--|--|--|
| MAE | 68,625 | 49,604 | Visitantes de diferencia promedio por mes |
| RMSE | 75,730 | 58,426 | Parecido al MAE, pero castiga más los errores grandes |
| MAPE | 7.4 % | 5.4 % | El error como porcentaje de lo observado |

El MAE es la métrica principal porque está en la misma unidad que la variable y se lee sin
esfuerzo. El MAPE divide entre el valor observado, así que no está definido cuando el observado es
cero. En esta serie no hay ceros, porque Antigua recibe entre 0.82 y 1.05 millones de visitantes
cada mes, pero el código lo trata de forma explícita, excluye del MAPE los meses con observado
igual a cero, reporta cuántos excluyó en `mape_excluded` y, si todos fueran cero, deja el MAPE
como no calculable, lo que hace fallar la regla.

## 4. Regla de aceptación

Una versión candidata se aprueba solo si cumple las cuatro condiciones, y se verifica en código
con `accept` en la etapa de publicación del pipeline.

| # | Condición | Se cumple si |
|--|--|--|
| 1 | Calidad | Ningún control de calidad terminó con falla o sin ejecutarse |
| 2 | Salidas completas | Hay un valor para cada mes de `periods.estimate` (ene y feb 2026), finito y mayor o igual a cero |
| 3 | Error del procedimiento | MAPE de la validación menor o igual a `max_mape` (15 %) |
| 4 | Comparación con la referencia | MAE del factor dividido entre MAE de la referencia menor o igual a `max_ratio_vs_baseline` (1.25) |

La decisión se guarda en `mlops/runs/<run_id>/evaluation.json` junto con las métricas, y el
pipeline devuelve `approved` y `reason`, que es lo que usan la publicación y el registro en MLflow.
Si la versión se rechaza, no se toca la versión publicada.

### Justificación de los umbrales

Los dos umbrales se fijaron en el avance del 29 de octubre (commit `3ae4055`), antes de que
existiera la evaluación, y no se modificaron al ver el resultado.

El umbral del MAPE parte de la escala de la variable. Los visitantes observados de Antigua van de
0.82 a 1.05 millones por mes, unos 12 % por encima y por debajo de su promedio de 0.94 millones.
Un error mayor al 15 %, unos 140 mil visitantes, sería más grande que la diferencia natural entre
un mes y otro, y la estimación no aportaría más que decir que enero fue un mes típico.

El umbral de comparación tolera que el factor sea hasta 25 % peor que la referencia. Con solo tres
meses evaluados el MAE es ruidoso y un margen evita rechazar por azar, pero un procedimiento que
se equivoca claramente más que una regla trivial no debería publicarse.

## 5. Resultado y decisión

| Condición | Resultado |
|--|--|
| Calidad | Cumple, ningún control con falla (tres advertencias permitidas) |
| Salidas completas | Cumple, enero 1,042,620 y febrero 821,310, finitos y no negativos |
| Error del procedimiento | Cumple, MAPE 7.4 % frente al umbral de 15 % |
| Comparación con la referencia | No cumple, razón 1.38 frente al umbral de 1.25 |

La versión candidata se rechaza. El factor de reparto tiene un error moderado, 7.4 %, pero la
referencia del último valor se equivoca menos en los tres meses evaluados. El enunciado no exige
superar a la referencia, pero sí aplicar la regla tal como se definió, así que la aplicamos sin
cambiarla.

La tabla mensual explica por qué pasa. El factor subestimó los tres meses, porque se apoya en los
factores de fin de 2025, que fueron más bajos, sobre todo diciembre con 2.79, mientras que en la
primavera de 2026 el factor subió a 3.5 y 3.8. Además el factor hereda la estacionalidad de la
migración, que cae 7.5 % de abril a mayo, cuando los visitantes de Antigua apenas bajaron 1.4 %.
La referencia, en cambio, aprovecha que la telefonía de Antigua cambia poco de un mes al siguiente.

Esa ventaja de la referencia no se trasladaría completa a la tarea real. Para estimar febrero de
2026, el último valor observado sería el de diciembre de 2025, dos meses antes y en plena temporada
alta, no el mes inmediatamente anterior como en la validación. La regla no se ajusta por esto, pero
conviene tenerlo presente al interpretar el resultado.

Mientras no exista una versión aprobada, el tablero debe indicar que las estimaciones no están
disponibles. Si el grupo propone una nueva versión del procedimiento, debe registrarse con otra
`procedure_version` y evaluarse con esta misma regla y estos mismos umbrales.

## 6. Limitaciones para reproducir enero y febrero de 2026

- No hay telefonía de enero ni de febrero en ningún año, así que no se puede validar el factor en
  esos meses ni saber si su relación con la migración se parece a la de los meses evaluados.
- No hay comparación interanual, porque la telefonía cubre de septiembre de 2025 a agosto de 2026
  y ningún mes se repite.
- La migración tiene una ruptura metodológica entre 2022 y 2023, por eso solo se usan 2025 y 2026 y
  no se puede alargar la historia para calcular el factor.
- Abril a junio no se parecen a enero y febrero, que siguen a la temporada alta de fin de año, así
  que el error de la validación es solo una aproximación del error real de esos meses.
- Con tres meses evaluados las métricas son poco estables, un solo mes cambia mucho el promedio.
- El procedimiento supone un factor constante, aunque los factores mensuales van de 2.79 a 3.84.

## 7. Cómo reproducirlo

```bash
python -m mlops.pipeline                            # imprime métricas y la decisión
python -m unittest tests.test_evaluation -v         # 18 pruebas de la evaluación y la regla
```
