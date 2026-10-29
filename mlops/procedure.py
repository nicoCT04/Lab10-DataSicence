"""Preparación de la serie destino-mes, factor de reparto y estimación."""
import numpy as np
import pandas as pd

from mlops.config import months


def prepare(mob: pd.DataFrame, mig: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    Serie mensual del polígono y del ingreso al país. Los meses sin telefonía
    quedan en NaN: la ausencia de dato no es cero.
    """
    polygon = mob[mob["destino"].str.strip() == cfg["sources"]["polygon"]]
    visitors = polygon.groupby(pd.to_datetime(polygon["fecha"]).dt.to_period("M"))["visitantes"].sum()

    arrivals = mig[mig["Tipo de Viajero"].isin(cfg["sources"]["traveler_types"])]
    period = pd.PeriodIndex.from_fields(year=arrivals["Año"], month=arrivals["Mes cod"], freq="M")
    arrivals = arrivals.groupby(period)["Viajero"].sum()

    p = cfg["periods"]
    needed = months(p["fit"]).union(months(p["estimate"]))
    span = pd.period_range(needed.min(), needed.max(), freq="M")
    out = pd.DataFrame({"periodo": span})
    out["visitantes_obs"] = visitors.reindex(span).values
    out["migracion"] = arrivals.reindex(span).values
    out["factor"] = out["visitantes_obs"] / out["migracion"]
    return out


def fit_factor(series: pd.DataFrame, fit_months: list[str], method: str = "mean") -> dict:
    """Factor de reparto f̂ = promedio (o mediana) de V_t / M_t en los meses de ajuste."""
    sub = series[series["periodo"].isin(months(fit_months))].dropna(subset=["factor"])
    if sub.empty:
        raise ValueError("No hay meses observados para calcular el factor de reparto")
    agg = np.median if method == "median" else np.mean
    return {
        "method": method,
        "factor": float(agg(sub["factor"])),
        "n_months": int(len(sub)),
        "monthly": {str(p): float(f) for p, f in zip(sub["periodo"], sub["factor"])},
    }


def estimate(series: pd.DataFrame, fit: dict, target_months: list[str]) -> pd.DataFrame:
    """V̂_t = f̂ · M_t para los meses sin cobertura."""
    sub = series[series["periodo"].isin(months(target_months))]
    return pd.DataFrame({"periodo": sub["periodo"].astype(str).values,
                         "valor": fit["factor"] * sub["migracion"].values})
