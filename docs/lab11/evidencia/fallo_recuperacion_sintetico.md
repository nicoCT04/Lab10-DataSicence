# Prueba controlada de fallo y recuperación — 2026-10-30T23:41:16

- Datos: **sinteticos**. Problema: **denominador** (migración de oct-2025 igual a cero (denominador del factor)).
- Carpeta aislada: `mlops/test_runs/evidencia` (no toca `data/raw` ni `mlops/published`).
- Resultado: **todas las comprobaciones se cumplen**.

| Paso | run_id | Estado | current/ | Vigente | Lo que muestra el tablero |
|--|--|--|--|--|--|
| 1. versión inicial | `20261030-234115-c11b1d` | completada | cambió | `20261030-234115-c11b1d` | 2026-01: 1,050,000, 2026-02: 829,500 |
| 2. entrega con problema (denominador) | `20261030-234116-2c1eeb` | detenida | sin cambios | `20261030-234115-c11b1d` | 2026-01: 1,050,000, 2026-02: 829,500 |
| 3. entrega corregida | `20261030-234116-a5faa5` | completada | cambió | `20261030-234116-a5faa5` | 2026-01: 1,134,000, 2026-02: 895,860 |
| restaurar 20261030-234115-c11b1d | `20261030-234115-c11b1d` | restaurada | cambió | `20261030-234115-c11b1d` | 2026-01: 1,050,000, 2026-02: 829,500 |

## Detalle por paso

**1. versión inicial**
- Motivo: aprobada: cumple las cuatro condiciones
- Publicación: publicada en current/ (primera versión aprobada)
- Controles: Columnas y tipos = ok, Fechas y cobertura = ok, Unicidad = ok, Valores faltantes = ok, Valores y denominadores = ok, Regla metodológica = ok
- Monitoreo: Actualización = alerta, Calidad = sin datos, Resultados = ok

**2. entrega con problema (denominador)**
- Motivo: control crítico fallido, no se reemplazan resultados: Valores y denominadores: denominador de migración igual a cero en: 2025-10
- Publicación: no publicada
- Controles: Columnas y tipos = ok, Fechas y cobertura = ok, Unicidad = ok, Valores faltantes = ok, Valores y denominadores = falla, Regla metodológica = ok
- Monitoreo: Actualización = ok, Calidad = ok, Resultados = sin datos

**3. entrega corregida**
- Motivo: aprobada: cumple las cuatro condiciones
- Publicación: publicada en current/; la anterior (20261030-234115-c11b1d) quedó en versions/
- Controles: Columnas y tipos = ok, Fechas y cobertura = ok, Unicidad = ok, Valores faltantes = ok, Valores y denominadores = ok, Regla metodológica = ok
- Monitoreo: Actualización = ok, Calidad = ok, Resultados = ok

**restaurar 20261030-234115-c11b1d**

Comprobaciones:

- [x] la versión inicial se publica
- [x] el problema detiene el pipeline
- [x] con el problema current/ no cambia y sigue la versión inicial
- [x] el tablero sigue mostrando la versión inicial
- [x] la entrega corregida se publica
- [x] la versión inicial vuelve a estar vigente
- [x] el tablero lee de nuevo la versión inicial
