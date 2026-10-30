"""
Validación temporal del factor de reparto y regla de aceptación de la versión candidata.

Ventana expansiva: cada mes de periods.evaluation se oculta y se estima solo con
los meses observados anteriores a él, igual que se estimarían ene-feb 2026 con lo
que había disponible. La referencia (procedure.baseline) se evalúa en los mismos
meses y con la misma restricción temporal.
"""
import numpy as np
import pandas as pd

from mlops.checks import failed
from mlops.config import months


def _observed(series: pd.DataFrame) -> pd.DataFrame:
    return series.dropna(subset=["visitantes_obs", "factor"]).sort_values("periodo")


def candidate(series: pd.DataFrame, target, method: str = "mean") -> dict:
    """Factor de reparto con los meses observados anteriores a target y V̂ = f̂ · M_target."""
    prev = _observed(series)
    prev = prev[prev["periodo"] < target]
    if prev.empty:
        raise ValueError(f"no hay meses observados antes de {target} para calcular el factor")
    agg = np.median if method == "median" else np.mean
    factor = float(agg(prev["factor"]))
    migration = float(series.loc[series["periodo"] == target, "migracion"].iloc[0])
    return {"estimate": factor * migration, "factor": factor,
            "months_used": [str(p) for p in prev["periodo"]]}


def baseline(series: pd.DataFrame, target, kind: str = "last_value") -> dict:
    """Referencia sencilla: último valor observado antes de target, o promedio histórico previo."""
    prev = _observed(series)
    prev = prev[prev["periodo"] < target]
    if prev.empty:
        raise ValueError(f"no hay meses observados antes de {target} para la referencia")
    if kind == "last_value":
        return {"estimate": float(prev["visitantes_obs"].iloc[-1]), "from": str(prev["periodo"].iloc[-1])}
    if kind == "mean":
        return {"estimate": float(prev["visitantes_obs"].mean()), "from": "promedio de meses previos"}
    raise ValueError(f"referencia desconocida: {kind}")


def metrics(observed, predicted) -> dict:
    """
    MAE y RMSE en visitantes; MAPE en %. El MAPE divide entre el observado, así que
    los meses con observado igual a cero se excluyen de su cálculo y se reportan
    en mape_excluded; si todos son cero el MAPE queda en None (no calculable).
    """
    y, p = np.asarray(observed, float), np.asarray(predicted, float)
    err = y - p
    nonzero = y != 0
    return {
        "MAE": float(np.mean(np.abs(err))),
        "RMSE": float(np.sqrt(np.mean(err ** 2))),
        "MAPE": float(np.mean(np.abs(err[nonzero] / y[nonzero])) * 100) if nonzero.any() else None,
        "mape_excluded": int((~nonzero).sum()),
        "n": int(len(y)),
    }


TOL = 1e-6  # visitantes; absorbe el residuo de punto flotante cuando el error es nulo


def mae_ratio(candidate_mae: float, reference_mae: float) -> float:
    """MAE del procedimiento / MAE de la referencia; si la referencia no se equivoca, 1 o infinito."""
    if reference_mae <= TOL:
        return 1.0 if candidate_mae <= TOL else float("inf")
    return candidate_mae / reference_mae


def evaluate(series: pd.DataFrame, cfg: dict) -> dict:
    """Errores mes a mes y métricas del procedimiento y de la referencia en los mismos meses."""
    proc = cfg["procedure"]
    rows = []
    for target in months(cfg["periods"]["evaluation"]):
        obs = series.loc[series["periodo"] == target, "visitantes_obs"]
        if obs.empty or obs.isna().all():
            # no se calcula error para meses sin valor observado comparable (p. ej. ene-feb 2026)
            raise ValueError(f"el mes de evaluación {target} no tiene valor observado")
        cand = candidate(series, target, proc["factor"])
        base = baseline(series, target, proc["baseline"])
        rows.append({"periodo": str(target), "observado": float(obs.iloc[0]),
                     "candidato": cand["estimate"], "factor_usado": cand["factor"],
                     "meses_ajuste": cand["months_used"],
                     "referencia": base["estimate"], "referencia_desde": base["from"]})
    table = pd.DataFrame(rows)
    cand_m = metrics(table["observado"], table["candidato"])
    base_m = metrics(table["observado"], table["referencia"])
    return {
        "scheme": "ventana expansiva, un mes oculto a la vez",
        "evaluated_months": table["periodo"].tolist(),
        "baseline": proc["baseline"],
        "candidate": cand_m,
        "reference": base_m,
        "ratio_mae_vs_reference": mae_ratio(cand_m["MAE"], base_m["MAE"]),
        "monthly": table.to_dict("records"),
    }


def accept(report: list[dict], estimates: pd.DataFrame, evaluation: dict, cfg: dict) -> dict:
    """
    Regla verificable para aprobar la versión candidata. Se aprueba solo si se
    cumplen las cuatro condiciones; los umbrales vienen de [acceptance] y no se
    ajustan después de ver el resultado.

      1. Calidad: ningún control con falla (ni sin ejecutar).
      2. Salidas completas: un valor por cada mes de periods.estimate, finito y >= 0.
      3. Error del procedimiento: MAPE de la validación <= max_mape.
      4. Comparación: MAE del procedimiento / MAE de la referencia <= max_ratio_vs_baseline.
    """
    acc = cfg["acceptance"]
    checks = []

    bad = failed(report)
    checks.append({"rule": "Controles de calidad", "passed": not bad,
                   "detail": "sin fallas" if not bad else
                   "controles con falla: " + ", ".join(r["control"] for r in bad)})

    expected = sorted(cfg["periods"]["estimate"])
    got = sorted(estimates["periodo"].astype(str)) if len(estimates) else []
    values = pd.to_numeric(estimates["valor"], errors="coerce") if len(estimates) else pd.Series(dtype=float)
    complete = got == expected and bool(np.isfinite(values).all()) and bool((values >= 0).all())
    checks.append({"rule": "Salidas completas", "passed": complete,
                   "detail": f"{len(got)} de {len(expected)} meses, finitos y no negativos" if complete else
                   f"se esperaban {expected} con valores finitos y >= 0; se obtuvo {got} "
                   f"con valores {values.round(0).tolist()}"})

    mape = evaluation["candidate"]["MAPE"]
    ok_mape = mape is not None and mape <= acc["max_mape"]
    checks.append({"rule": "Error del procedimiento", "passed": ok_mape,
                   "detail": "MAPE no calculable" if mape is None else
                   f"MAPE {mape:.1f} % (umbral {acc['max_mape']} %)"})

    ratio = evaluation["ratio_mae_vs_reference"]
    ok_ratio = ratio is not None and ratio <= acc["max_ratio_vs_baseline"]
    checks.append({"rule": "Comparación con la referencia", "passed": ok_ratio,
                   "detail": "razón no calculable" if ratio is None else
                   f"MAE {evaluation['candidate']['MAE']:,.0f} frente a {evaluation['reference']['MAE']:,.0f} "
                   f"de la referencia, razón {ratio:.2f} (umbral {acc['max_ratio_vs_baseline']})"})

    approved = all(c["passed"] for c in checks)
    reason = ("aprobada: cumple las cuatro condiciones" if approved else
              "rechazada: " + "; ".join(f"{c['rule']} ({c['detail']})" for c in checks if not c["passed"]))
    return {"approved": approved, "reason": reason, "checks": checks,
            "thresholds": {k: acc[k] for k in ("max_mape", "max_ratio_vs_baseline")}}
