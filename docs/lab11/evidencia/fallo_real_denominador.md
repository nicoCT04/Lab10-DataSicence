# Prueba controlada de fallo y recuperación — 2026-10-30T23:39:57

- Datos: **real**. Problema: **denominador** (migración de oct-2025 igual a cero (denominador del factor)).
- Carpeta aislada: `mlops/test_runs/drill-20261030-233922` (no toca `data/raw` ni `mlops/published`).
- Resultado: **todas las comprobaciones se cumplen**.

| Paso | run_id | Estado | current/ | Vigente | Lo que muestra el tablero |
|--|--|--|--|--|--|
| 1. copia de la fuente con problema (denominador) | `20261030-233941-08b3bb` | detenida | sin cambios | `None` | Estimaciones no disponibles |
| 2. copia corregida | `20261030-233950-9ae5b5` | completada | sin cambios | `None` | Estimaciones no disponibles |

## Detalle por paso

**1. copia de la fuente con problema (denominador)**
- Motivo: control crítico fallido, no se reemplazan resultados: Valores y denominadores: denominador de migración igual a cero en: 2025-10
- Publicación: no publicada
- Controles: Columnas y tipos = ok, Fechas y cobertura = advertencia, Unicidad = advertencia, Valores faltantes = advertencia, Valores y denominadores = falla, Regla metodológica = ok
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
