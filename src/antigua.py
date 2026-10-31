"""
Lectura de la versión publicada de Antigua para el tablero. Solo lee mlops/published/current/:
no ejecuta el pipeline ni recalcula el factor de reparto.
"""
import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.data import MONTHS, ROOT

# en Docker se monta en /app/mlops/published; PUBLISHED_DIR permite mostrar otra carpeta de versiones
PUBLISHED = Path(os.environ.get("PUBLISHED_DIR") or ROOT / "mlops" / "published")
ESTIMATE_COLUMNS = ["destino", "periodo", "valor", "unidad", "run_id", "fecha_generacion",
                    "version_procedimiento"]


def load_current(published: Path = PUBLISHED) -> dict | None:
    """Versión vigente o None si no hay una aprobada completa (el tablero no inventa valores)."""
    cur = Path(published) / "current"
    try:
        est = pd.read_csv(cur / "estimates.csv")
        series = pd.read_csv(cur / "series.csv")
        meta = json.loads((cur / "metadata.json").read_text())
    except (OSError, ValueError):
        return None
    if not set(ESTIMATE_COLUMNS) <= set(est.columns) or est.empty:
        return None
    if not {"periodo", "visitantes_obs"} <= set(series.columns):
        return None
    return {"estimates": est[ESTIMATE_COLUMNS].to_dict("records"),
            "observed": series[["periodo", "visitantes_obs"]].to_dict("records"),
            "meta": {k: meta.get(k) for k in ("generated", "published_at", "evaluation", "procedure_version")}}


def month_label(period: str) -> str:
    """'2026-01' -> 'ene 2026'."""
    year, month = period.split("-")
    return f"{MONTHS[int(month) - 1].lower()} {year}"


def date_label(iso: str | None) -> str:
    if not iso:
        return "—"
    d = datetime.fromisoformat(iso)
    return f"{d.day} {MONTHS[d.month - 1].lower()} {d.year}"


def frames(data: dict, window: str = "all") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Observados (con huecos) y estimaciones, recortados a la ventana elegida."""
    obs = pd.DataFrame(data["observed"])
    est = pd.DataFrame(data["estimates"])
    for df in (obs, est):
        df["fecha"] = pd.PeriodIndex(df["periodo"].astype(str), freq="M").to_timestamp()
    if window == "2026":
        obs, est = obs[obs["fecha"].dt.year == 2026], est[est["fecha"].dt.year == 2026]
    return obs.sort_values("fecha"), est.sort_values("fecha")
