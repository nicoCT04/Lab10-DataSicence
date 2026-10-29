import tomllib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "mlops" / "config.toml"


def load_config(path=DEFAULT_CONFIG) -> dict:
    with open(path, "rb") as f:
        cfg = tomllib.load(f)
    cfg["_path"] = str(Path(path).resolve())
    return cfg


def resolve(cfg: dict, key: str) -> Path:
    """Ruta de [paths]; las relativas se toman desde la raíz del repositorio."""
    p = Path(cfg["paths"][key])
    return p if p.is_absolute() else ROOT / p


def months(values: list[str]) -> pd.PeriodIndex:
    return pd.PeriodIndex(values, freq="M")
