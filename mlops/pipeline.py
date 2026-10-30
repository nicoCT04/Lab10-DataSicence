"""
Pipeline del Lab 11. Uso:

    python -m mlops.pipeline [--config mlops/config.toml]

Cada ejecución crea mlops/runs/<run_id>/ con la configuración usada, el log,
la serie preparada, los parámetros y las estimaciones candidatas.
"""
import argparse
import json
import os
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

from mlops.checks import WARN, failed, run_checks, write_report
from mlops.config import DEFAULT_CONFIG, ROOT, load_config, resolve
from mlops.evaluation import accept, evaluate
from mlops.procedure import estimate, fit_factor, prepare
from mlops.publish import publish
from mlops.sources import read_sources
from mlops import tracking


class StopPipeline(Exception):
    """Falla controlada: se detiene el flujo sin tocar la versión publicada."""


def git_commit() -> dict:
    if os.environ.get("GIT_COMMIT"):
        return {"commit": os.environ["GIT_COMMIT"], "dirty": None}
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


def version_metadata(log: dict, cfg: dict) -> dict:
    """Lo que acompaña a una versión publicada: identifica datos, código, evaluación y decisión."""
    return {"run_id": log["run_id"], "generated": log["start"], "destination": cfg["destination"],
            "unit": cfg["unit"], "procedure_version": cfg["procedure_version"],
            "periods": cfg["periods"], "code": log.get("code"), "sources": log.get("sources"),
            "mlflow_run_id": log.get("mlflow_run_id"), "quality": log.get("quality"),
            "evaluation": log.get("evaluation"), "acceptance": log.get("acceptance")}


def run(cfg: dict) -> dict:
    np.random.seed(cfg.get("seed", 0))
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    run_dir = resolve(cfg, "runs") / run_id
    run_dir.mkdir(parents=True)
    shutil.copy(cfg["_path"], run_dir / "config.toml")
    log = RunLog(run_id, run_dir)
    log.data["code"] = git_commit()
    result = {"run_id": run_id, "run_dir": str(run_dir)}
    tracked = None
    try:
        with log.stage("tracking"):
            tracked = tracking.start(cfg, log.data)
            log.data["mlflow_run_id"] = tracked[1]
            result["mlflow_run_id"] = tracked[1]
        with log.stage("lectura"):
            mob, mig, sources = read_sources(cfg)
            log.data["sources"] = sources

        with log.stage("validación"):
            report = run_checks(mob, mig, cfg)
            write_report(report, run_dir)
            log.data["quality"] = {r["control"]: r["status"] for r in report}
            for r in report:
                print(f"  {r['status']:<12} {r['control']}")
                if r["status"] == WARN:
                    log.warn("validación", f"{r['control']}: {r['detail']}")
        if failed(report):
            msg = " | ".join(f"{r['control']}: {r['detail']}" for r in failed(report))
            log.data["errors"].append({"stage": "validación", "error": msg})
            raise StopPipeline(f"control crítico fallido, no se reemplazan resultados: {msg}")

        with log.stage("preparación"):
            series = prepare(mob, mig, cfg)
            series.assign(periodo=series["periodo"].astype(str)).to_csv(run_dir / "series.csv", index=False)

        with log.stage("ajuste"):
            fit = fit_factor(series, cfg["periods"]["fit"], cfg["procedure"]["factor"])
            (run_dir / "params.json").write_text(json.dumps(fit, indent=2))
            print(f"  factor de reparto = {fit['factor']:.4f} ({fit['n_months']} meses)")

        with log.stage("evaluación"):
            evaluation = evaluate(series, cfg)
            (run_dir / "evaluation.json").write_text(json.dumps(evaluation, indent=2, ensure_ascii=False))
            c, r = evaluation["candidate"], evaluation["reference"]
            log.data["evaluation"] = {"months": evaluation["evaluated_months"],
                                      "candidate": c, "reference": r,
                                      "ratio_mae_vs_reference": evaluation["ratio_mae_vs_reference"]}
            print(f"  meses evaluados: {', '.join(evaluation['evaluated_months'])}")
            print(f"  factor de reparto: MAE {c['MAE']:,.0f}  RMSE {c['RMSE']:,.0f}  MAPE {c['MAPE']:.1f} %")
            print(f"  referencia ({evaluation['baseline']}): MAE {r['MAE']:,.0f}  RMSE {r['RMSE']:,.0f}  "
                  f"MAPE {r['MAPE']:.1f} %")

        with log.stage("estimación"):
            est = estimates_table(estimate(series, fit, cfg["periods"]["estimate"]),
                                  cfg, run_id, log.data["start"])

        with log.stage("almacenamiento"):
            est.to_csv(run_dir / "estimates.csv", index=False)

        with log.stage("publicación"):
            decision = accept(report, est, evaluation, cfg)
            evaluation["decision"] = decision
            (run_dir / "evaluation.json").write_text(json.dumps(evaluation, indent=2, ensure_ascii=False))
            log.data["acceptance"] = {"approved": decision["approved"], "reason": decision["reason"]}
            for c in decision["checks"]:
                print(f"  {'cumple' if c['passed'] else 'NO cumple':<10} {c['rule']}: {c['detail']}")
            if decision["approved"]:
                pub = publish(run_dir, resolve(cfg, "published"), version_metadata(log.data, cfg))
                log.data["publication"] = (f"publicada en current/; la anterior ({pub['previous']}) "
                                           "quedó en versions/" if pub["previous"] else
                                           "publicada en current/ (primera versión aprobada)")
                print(f"  {log.data['publication']}")
            else:
                log.data["publication"] = "no publicada: " + decision["reason"]
                log.warn("publicación", "versión rechazada; se conserva la última versión aprobada")

        log.close("completada")
        result.update(status="completada", factor=fit["factor"], estimates=est,
                      approved=decision["approved"], reason=decision["reason"])
    except StopPipeline as e:
        log.close("detenida")
        result.update(status="detenida", reason=str(e))
    except Exception:
        log.data["errors"].append({"stage": "-", "error": traceback.format_exc(limit=3)})
        log.close("fallida")
        result.update(status="fallida")
    finally:
        if tracked:
            try:
                tracking.finish(*tracked, log.data, run_dir)
            except Exception:
                log.data["errors"].append({"stage": "tracking", "error": traceback.format_exc(limit=3)})
                log.close("fallida")
                result.update(status="fallida", reason="No se pudo completar el registro en MLflow; ver run_log.json")
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    args = ap.parse_args(argv)
    res = run(load_config(args.config))
    print(f"\nrun {res['run_id']}: {res['status']}  ->  {res['run_dir']}")
    if "estimates" in res:
        print(res["estimates"][["periodo", "valor", "tipo"]].round(0).to_string(index=False))
        print(f"\nversión candidata {res['reason']}")
    if res["status"] != "completada":
        print(res.get("reason", "ver run_log.json"))
        sys.exit(1)


if __name__ == "__main__":
    main()
