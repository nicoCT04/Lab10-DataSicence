"""Trazabilidad local: SQLite y artefactos persistentes, sin subir las fuentes originales."""
import json
import math
import os
import platform
from importlib.metadata import distributions
from pathlib import Path

from mlflow import MlflowClient

from mlops.config import ROOT

EXPERIMENT = "observatorio-antigua"


def start(cfg: dict, log: dict):
    storage = Path(os.environ.get("MLFLOW_STORAGE", ROOT / "mlruns")).resolve()
    storage.mkdir(parents=True, exist_ok=True)
    client = MlflowClient(tracking_uri=os.environ.get(
        "MLFLOW_TRACKING_URI", f"sqlite:///{storage / 'mlflow.db'}"))
    experiment = client.get_experiment_by_name(EXPERIMENT)
    experiment_id = experiment.experiment_id if experiment else client.create_experiment(
        EXPERIMENT, artifact_location=(storage / "artifacts").as_uri())
    run = client.create_run(experiment_id, tags={
        "mlflow.runName": log["run_id"], "pipeline.run_id": log["run_id"],
        "pipeline.start": log["start"], "mlflow.source.git.commit": log["code"]["commit"],
        "code.dirty": str(log["code"]["dirty"]),
        "destination": cfg["destination"], "procedure_version": cfg["procedure_version"],
    })
    run_id = run.info.run_id
    try:
        for key in ("destination", "procedure_version", "unit", "seed"):
            client.log_param(run_id, key, cfg[key])
        for section in ("periods", "procedure", "acceptance", "paths"):
            for key, value in cfg[section].items():
                client.log_param(run_id, f"{section}.{key}",
                                 json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value)
        client.log_dict(run_id, {"python": platform.python_version(),
                                "packages": {d.metadata["Name"]: d.version for d in distributions()}},
                        "environment.json")
    except Exception as error:
        client.set_tag(run_id, "failure.reason", str(error)[:5000])
        client.set_terminated(run_id, status="FAILED")
        raise
    return client, run_id


def finish(client, run_id: str, log: dict, directory: Path):
    """Registra únicamente resultados producidos; una detención no tiene métricas ficticias."""
    for key in ("status", "end", "publication"):
        client.set_tag(run_id, f"pipeline.{key}", log[key])
    for source, info in log.get("sources", {}).items():
        for key, value in info.items():
            client.log_param(run_id, f"sources.{source}.{key}", value)
    for control, status in log.get("quality", {}).items():
        client.set_tag(run_id, f"quality.{control}", status)
    if log.get("errors"):
        client.set_tag(run_id, "failure.reason", json.dumps(log["errors"], ensure_ascii=False)[:5000])
    if "acceptance" in log:
        client.set_tag(run_id, "acceptance.approved", str(log["acceptance"]["approved"]))
        client.set_tag(run_id, "acceptance.reason", log["acceptance"]["reason"])
    params = directory / "params.json"
    if params.exists():
        fit = json.loads(params.read_text())
        for key, value in fit.items():
            client.log_param(run_id, f"fit.{key}", json.dumps(value, ensure_ascii=False))
    evaluation = log.get("evaluation", {})
    for kind in ("candidate", "reference"):
        for key, value in evaluation.get(kind, {}).items():
            if value is not None and math.isfinite(value):
                client.log_metric(run_id, f"{kind}.{key}", value)
    ratio = evaluation.get("ratio_mae_vs_reference")
    if ratio is not None and math.isfinite(ratio):
        client.log_metric(run_id, "ratio_mae_vs_reference", ratio)
    # Los JSON originales conservan también valores no calculables/no finitos y su contexto.
    for artifact in directory.iterdir():
        if artifact.is_file():
            client.log_artifact(run_id, str(artifact))
    client.set_terminated(run_id, status="FINISHED" if log["status"] == "completada" else "FAILED")
