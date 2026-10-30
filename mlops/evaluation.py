"""
Validación temporal del factor de reparto y regla de aceptación de la versión candidata.

Ventana expansiva: cada mes de periods.evaluation se oculta y se estima solo con
los meses observados anteriores a él, igual que se estimarían ene-feb 2026 con lo
que había disponible. La referencia (procedure.baseline) se evalúa en los mismos
meses y con la misma restricción temporal.
"""
import numpy as np
import pandas as pd

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
        "ratio_mae_vs_reference": cand_m["MAE"] / base_m["MAE"] if base_m["MAE"] else None,
        "monthly": table.to_dict("records"),
    }
