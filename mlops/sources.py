"""Lectura de las fuentes sin transformar, con su huella digital."""
import hashlib
import warnings
from pathlib import Path

import pandas as pd

from mlops.config import resolve

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")


def fingerprint(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_sources(cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    mob_path, mig_path = resolve(cfg, "mobility"), resolve(cfg, "migration")
    for p in (mob_path, mig_path):
        if not p.exists():
            raise FileNotFoundError(f"No se encontró la fuente {p}")
    mob = pd.read_excel(mob_path, sheet_name=cfg["paths"]["mobility_sheet"])
    mig = pd.read_excel(mig_path, sheet_name=cfg["paths"]["migration_sheet"])
    info = {
        "mobility": {"file": mob_path.name, "sheet": cfg["paths"]["mobility_sheet"],
                     "sha256": fingerprint(mob_path), "rows": len(mob)},
        "migration": {"file": mig_path.name, "sheet": cfg["paths"]["migration_sheet"],
                      "sha256": fingerprint(mig_path), "rows": len(mig)},
    }
    return mob, mig, info
