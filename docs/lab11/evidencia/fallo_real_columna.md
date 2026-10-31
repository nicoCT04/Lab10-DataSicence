# Prueba controlada de fallo y recuperación — 2026-10-30T23:39:14

- Datos: **real**. Problema: **columna** (falta la columna indispensable «visitantes» en telefonía).
- Carpeta aislada: `mlops/test_runs/drill-20261030-233857` (no toca `data/raw` ni `mlops/published`).
- Resultado: **todas las comprobaciones se cumplen**.

| Paso | run_id | Estado | current/ | Vigente | Lo que muestra el tablero |
|--|--|--|--|--|--|
| 1. copia de la fuente con problema (columna) | `20261030-233858-50525a` | detenida | sin cambios | `None` | Estimaciones no disponibles |
| 2. copia corregida | `20261030-233906-7b98a8` | completada | sin cambios | `None` | Estimaciones no disponibles |

## Detalle por paso

**1. copia de la fuente con problema (columna)**
- Motivo: control crítico fallido, no se reemplazan resultados: Columnas y tipos: telefonía: falta «visitantes» | Fechas y cobertura: no ejecutado: faltan columnas indispensables | Unicidad: no ejecutado: faltan columnas indispensables | Valores faltantes: no ejecutado: faltan columnas indispensables | Valores y denominadores: no ejecutado: faltan columnas indispensables | Regla metodológica: no ejecutado: faltan columnas indispensables
- Publicación: no publicada
- Controles: Columnas y tipos = falla, Fechas y cobertura = no ejecutado, Unicidad = no ejecutado, Valores faltantes = no ejecutado, Valores y denominadores = no ejecutado, Regla metodológica = no ejecutado
- Monitoreo: Actualización = alerta, Calidad = sin datos, Resultados = sin datos

**2. copia corregida**
- Motivo: rechazada: Comparación con la referencia (MAE 68,625 frente a 49,604 de la referencia, razón 1.38 (umbral 1.25))
- Publicación: no publicada: rechazada: Comparación con la referencia (MAE 68,625 frente a 49,604 de la referencia, razón 1.38 (umbral 1.25))
- Controles: Columnas y tipos = ok, Fechas y cobertura = advertencia, Unicidad = advertencia, Valores faltantes = advertencia, Valores y denominadores = ok, Regla metodológica = ok
- Monitoreo: Actualización = alerta, Calidad = sin datos, Resultados = ok

Comprobaciones:

- [x] el problema detiene el pipeline
- [x] con el problema la versión publicada no cambia
- [x] la copia corregida completa el flujo
- [x] current/ solo cambia si la regla aprueba la versión corregida
