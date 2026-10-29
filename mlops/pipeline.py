"""
Pipeline del Lab 11. Uso:

    python -m mlops.pipeline [--config mlops/config.toml]

Cada ejecución crea mlops/runs/<run_id>/ con la configuración usada, el log,
la serie preparada, los parámetros y las estimaciones candidatas.
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
import traceback
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import numpy as np

from mlops.config import DEFAULT_CONFIG, ROOT, load_config, resolve
from mlops.procedure import estimate, fit_factor, prepare
from mlops.sources import read_sources


class StopPipeline(Exception):
    """Falla controlada: se detiene el flujo sin tocar la versión publicada."""


def git_commit() -> dict:
    def git(*args):
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    try:
        return {"commit": git("rev-parse", "HEAD") or "desconocido",
                "dirty": bool(git("status", "--porcelain", "--untracked-files=no"))}
    except FileNotFoundError:
        return {"commit": "desconocido", "dirty": None}


class RunLog:
    def __init__(self, run_id: str, run_dir: Path):
        self.path = run_dir / "run_log.json"
        self.data = {"run_id": run_id, "start": datetime.now().isoformat(timespec="seconds"),
                     "end": None, "status": "en curso", "stages": [], "warnings": [],
                     "errors": [], "publication": "no publicada"}

    @contextmanager
    def stage(self, name: str):
        t0 = time.perf_counter()
        print(f"[{name}] ...", flush=True)
        try:
            yield
        except Exception as e:
            self.data["stages"].append({"stage": name, "status": "fallida",
                                        "seconds": round(time.perf_counter() - t0, 2)})
            self.data["errors"].append({"stage": name, "error": f"{type(e).__name__}: {e}"})
            raise
        self.data["stages"].append({"stage": name, "status": "completada",
                                    "seconds": round(time.perf_counter() - t0, 2)})

    def warn(self, stage: str, msg: str):
        print(f"  ADVERTENCIA ({stage}): {msg}")
        self.data["warnings"].append({"stage": stage, "message": msg})

    def close(self, status: str):
        self.data["end"] = datetime.now().isoformat(timespec="seconds")
        self.data["status"] = status
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False))


def estimates_table(est, cfg: dict, run_id: str, generated: str):
    """Formato que consume el tablero: una fila por mes estimado."""
    return est.assign(destino=cfg["destination"], unidad=cfg["unit"], tipo="Estimación",
                      run_id=run_id, fecha_generacion=generated,
                      version_procedimiento=cfg["procedure_version"])[
        ["destino", "periodo", "valor", "unidad", "tipo", "run_id", "fecha_generacion",
         "version_procedimiento"]]


def run(cfg: dict) -> dict:
    np.random.seed(cfg.get("seed", 0))
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    run_dir = resolve(cfg, "runs") / run_id
    run_dir.mkdir(parents=True)
    shutil.copy(cfg["_path"], run_dir / "config.toml")
    log = RunLog(run_id, run_dir)
    log.data["code"] = git_commit()
    result = {"run_id": run_id, "run_dir": str(run_dir)}
    try:
        with log.stage("lectura"):
            mob, mig, sources = read_sources(cfg)
            log.data["sources"] = sources

        with log.stage("preparación"):
            series = prepare(mob, mig, cfg)
            series.assign(periodo=series["periodo"].astype(str)).to_csv(run_dir / "series.csv", index=False)

        with log.stage("ajuste"):
            fit = fit_factor(series, cfg["periods"]["fit"], cfg["procedure"]["factor"])
            (run_dir / "params.json").write_text(json.dumps(fit, indent=2))
            print(f"  factor de reparto = {fit['factor']:.4f} ({fit['n_months']} meses)")

        with log.stage("evaluación"):
            # pendiente: validación temporal con ventana expansiva y referencia
            log.warn("evaluación", "evaluación temporal no implementada; no hay métricas")

        with log.stage("estimación"):
            est = estimates_table(estimate(series, fit, cfg["periods"]["estimate"]),
                                  cfg, run_id, log.data["start"])

        with log.stage("almacenamiento"):
            est.to_csv(run_dir / "estimates.csv", index=False)

        with log.stage("publicación"):
            # pendiente: regla de aceptación y reemplazo controlado de published/current
            log.data["publication"] = "no publicada: regla de aceptación pendiente"
            log.warn("publicación", "la versión queda como candidata")

        log.close("completada")
        result.update(status="completada", factor=fit["factor"], estimates=est)
    except StopPipeline as e:
        log.close("detenida")
        result.update(status="detenida", reason=str(e))
    except Exception:
        log.data["errors"].append({"stage": "-", "error": traceback.format_exc(limit=3)})
        log.close("fallida")
        result.update(status="fallida")
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    args = ap.parse_args(argv)
    res = run(load_config(args.config))
    print(f"\nrun {res['run_id']}: {res['status']}  ->  {res['run_dir']}")
    if "estimates" in res:
        print(res["estimates"][["periodo", "valor", "tipo"]].round(0).to_string(index=False))
    if res["status"] != "completada":
        print(res.get("reason", "ver run_log.json"))
        sys.exit(1)


if __name__ == "__main__":
    main()
