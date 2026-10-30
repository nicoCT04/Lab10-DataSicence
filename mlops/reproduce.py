"""Dos corridas y exportación verificable: python -m mlops.reproduce --output carpeta [--config archivo]."""
import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from mlflow import MlflowClient

from mlops.config import DEFAULT_CONFIG, ROOT, load_config
from mlops.pipeline import run
from mlops.sources import fingerprint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    config_hash = fingerprint(Path(args.config))
    results = [run(load_config(args.config)) for _ in range(2)]
    logs = [json.loads((Path(r["run_dir"]) / "run_log.json").read_text()) for r in results]
    # El URI efectivo queda en el entorno o se deriva de MLFLOW_STORAGE, igual que en tracking.
    storage = Path(os.environ.get("MLFLOW_STORAGE", ROOT / "mlruns")).resolve()
    client = MlflowClient(tracking_uri=os.environ.get("MLFLOW_TRACKING_URI", f"sqlite:///{storage / 'mlflow.db'}"))
    exported = []
    for result in results:
        if "mlflow_run_id" in result:
            record = client.get_run(result["mlflow_run_id"])
            exported.append({"info": dict(record.info), "data": dict(record.data)})
    (output / "runs_export.json").write_text(json.dumps(exported, indent=2, ensure_ascii=False, default=str))
    comparison = {"run_ids": [r["run_id"] for r in results], "config_sha256": config_hash,
                  "rtol": 1e-12, "atol": 1e-8, "equivalent": False}
    try:
        assert all(r["status"] == "completada" for r in results), "Una corrida no terminó"
        assert fingerprint(Path(args.config)) == config_hash, "Cambió la configuración"
        assert logs[0]["sources"] == logs[1]["sources"], "Cambiaron las fuentes"
        assert logs[0]["code"] == logs[1]["code"], "Cambió el código"
        for filename in ("params.json", "evaluation.json"):
            contents = [json.loads((Path(r["run_dir"]) / filename).read_text()) for r in results]
            assert contents[0] == contents[1], f"Diferencias en {filename}"
        frames = [pd.read_csv(Path(r["run_dir"]) / "estimates.csv").drop(
            columns=["run_id", "fecha_generacion"]) for r in results]
        pd.testing.assert_frame_equal(*frames, rtol=1e-12, atol=1e-8)
        a, b = [row["data"]["metrics"] for row in exported]
        assert a.keys() == b.keys(), "Métricas distintas"
        np.testing.assert_allclose(list(a.values()), [b[k] for k in a], rtol=1e-12, atol=1e-8)
        comparison.update(equivalent=True, max_estimate_difference=float(
            (frames[0]["valor"] - frames[1]["valor"]).abs().max()),
            note="IDs y fechas cambian; parámetros y evaluación idénticos; estimaciones y métricas dentro de tolerancia.")
    except AssertionError as error:
        comparison["reason"] = str(error)
    (output / "comparison.json").write_text(json.dumps(comparison, indent=2, ensure_ascii=False))
    print(json.dumps(comparison, indent=2, ensure_ascii=False))
    if not comparison["equivalent"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
