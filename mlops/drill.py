"""
Prueba controlada de fallo y recuperación (Lab 11, ejercicios 7.4 y 7.5).

    python -m mlops.drill                               # datos sintéticos, denominador cero
    python -m mlops.drill --problem columna             # columna indispensable ausente
    python -m mlops.drill --data real --problem duplicado   # copia de las fuentes institucionales

Todo ocurre en una carpeta aislada (por defecto mlops/test_runs/drill-<fecha>/) con sus propias
fuentes, corridas y versiones publicadas; nunca se modifican data/raw ni mlops/published.

Con datos sintéticos el recorrido completo es:
  1. versión inicial aprobada y publicada (v1);
  2. nueva entrega con el problema: el pipeline se detiene y current/ sigue siendo v1;
  3. entrega corregida: se aprueba, se publica v2 y v1 queda en versions/;
  4. se restaura v1 y el tablero vuelve a leerla.
Con --data real se hacen los pasos 2 y 3 sobre una copia de las fuentes; la versión publicada de
partida es una copia de mlops/published (puede estar vacía) y la corregida solo se publica si la
regla de aceptación la aprueba.
"""
import argparse
import copy
import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

from mlops.config import DEFAULT_CONFIG, ROOT, load_config, resolve
from mlops.pipeline import run
from mlops.publish import current, restore, versions
from src.antigua import load_current

PROBLEMS = {
    "denominador": "migración de oct-2025 igual a cero (denominador del factor)",
    "columna": "falta la columna indispensable «visitantes» en telefonía",
    "duplicado": "una clave destino-fecha-país-segmento repetida en telefonía",
}

# visitantes del polígono por mes (escala de Antigua) y factor constante: la validación es exacta
VISITORS = {"2025-09": 820_000, "2025-10": 835_000, "2025-11": 1_050_000, "2025-12": 1_020_000,
            "2026-03": 1_030_000, "2026-04": 940_000, "2026-05": 925_000, "2026-06": 880_000}
FACTOR = 3.5
GAP_ARRIVALS = {"2026-01": 300_000, "2026-02": 237_000}


def synthetic(update: float = 1.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Telefonía del polígono y un subdestino; migración con ene-feb multiplicados por update."""
    rows = []
    for month, total in VISITORS.items():
        d = pd.Timestamp(month + "-01")
        for dest, share in (("Antigua Guatemala", 1.0), ("Jocotenango", 0.2)):
            for country, seg, part in (("Guatemala", "mayor a 1 dia", 0.45), ("Guatemala", "menor a 1 dia", 0.2),
                                       ("Usa", "mayor a 1 dia", 0.25), ("Usa", "menor a 1 dia", 0.1)):
                v = total * share * part
                rows.append(dict(destino=dest, anio=d.year, mes=d.month, fecha=d, pais=country,
                                 es_consecutivo=seg, visitantes=v, dias_persona=v * 2, permanencia_prom=2.0))
    arrivals = {m: v / FACTOR for m, v in VISITORS.items()} | {m: v * update for m, v in GAP_ARRIVALS.items()}
    mig = []
    for month, total in sorted(arrivals.items()):
        p = pd.Period(month, "M")
        for kind, part in (("Turista", 0.7), ("Excursionista", 0.3)):
            mig.append({"Año": p.year, "Mes cod": p.month, "Vía": "Aérea", "Frontera": "Aeropuerto La Aurora",
                        "País": "Usa", "Tipo de Viajero": kind, "Viajero": total * part})
    return pd.DataFrame(rows), pd.DataFrame(mig)


def inject(problem: str, mob: pd.DataFrame, mig: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    mob, mig = mob.copy(), mig.copy()
    if problem == "denominador":
        mig.loc[(mig["Año"] == 2025) & (mig["Mes cod"] == 10), "Viajero"] = 0
    elif problem == "columna":
        mob = mob.drop(columns="visitantes")
    elif problem == "duplicado":
        mob = pd.concat([mob, mob.iloc[[0]].assign(visitantes=mob["visitantes"].iloc[0] + 1)], ignore_index=True)
    return mob, mig


def tree_hash(folder: Path) -> str | None:
    """Huella del contenido de current/ para comprobar que no cambió."""
    if not folder.exists():
        return None
    h = hashlib.sha256()
    for p in sorted(folder.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(folder).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


class Drill:
    def __init__(self, cfg: dict, box: Path):
        self.box, self.steps = box, []
        self.published = box / "published"
        self.cfg = copy.deepcopy(cfg)
        self.cfg["paths"].update(runs=str(box / "runs"), published=str(self.published))

    def write(self, name: str, mob: pd.DataFrame | None, mig: pd.DataFrame | None, base: dict | None = None):
        """Escribe una entrega; si un DataFrame es None se copia el archivo de base sin reescribirlo."""
        folder = self.box / "entregas" / name
        folder.mkdir(parents=True)
        paths = {}
        for key, df, sheet in (("mobility", mob, self.cfg["paths"]["mobility_sheet"]),
                               ("migration", mig, self.cfg["paths"]["migration_sheet"])):
            target = folder / f"{key}.xlsx"
            if df is None:
                shutil.copy2(base[key], target)
            else:
                df.to_excel(target, sheet_name=sheet, index=False)
            paths[key] = str(target)
        return paths

    def run(self, step: str, sources: dict) -> dict:
        cfg = copy.deepcopy(self.cfg)
        cfg["paths"].update(sources)
        before = tree_hash(self.published / "current")
        res = run(cfg)
        log = json.loads((Path(res["run_dir"]) / "run_log.json").read_text())
        shown = load_current(self.published)
        record = {
            "paso": step, "run_id": res["run_id"], "estado": res["status"],
            "motivo": res.get("reason"), "publicacion": log["publication"],
            "controles": log.get("quality", {}),
            "monitoreo": {c["check"]: c["status"] for c in log.get("monitoring", [])},
            "current_cambio": before != tree_hash(self.published / "current"),
            "vigente": (current(self.published) or {}).get("run_id"),
            "tablero": [{"periodo": r["periodo"], "valor": round(r["valor"])} for r in shown["estimates"]]
            if shown else "Estimaciones no disponibles",
        }
        self.steps.append(record)
        print(f"\n>>> {step}: {record['estado']} · vigente {record['vigente']} · "
              f"current {'cambió' if record['current_cambio'] else 'sin cambios'}")
        return record

    def restore(self, run_id: str) -> dict:
        before = tree_hash(self.published / "current")
        restore(self.published, run_id)
        shown = load_current(self.published)
        record = {"paso": f"restaurar {run_id}", "run_id": run_id, "estado": "restaurada",
                  "current_cambio": before != tree_hash(self.published / "current"),
                  "vigente": current(self.published)["run_id"],
                  "tablero": [{"periodo": r["periodo"], "valor": round(r["valor"])} for r in shown["estimates"]]}
        self.steps.append(record)
        print(f"\n>>> restaurar: vigente {record['vigente']}")
        return record


def run_synthetic(d: Drill, problem: str) -> list[str]:
    """Recorrido completo; devuelve las comprobaciones que no se cumplieron."""
    v1 = d.run("1. versión inicial", d.write("1-inicial", *synthetic()))
    bad_mob, bad_mig = inject(problem, *synthetic(update=1.08))
    broken = d.run(f"2. entrega con problema ({problem})", d.write("2-con-problema", bad_mob, bad_mig))
    fixed = d.run("3. entrega corregida", d.write("3-corregida", *synthetic(update=1.08)))
    restored = d.restore(v1["run_id"])
    expect = [
        (v1["estado"] == "completada" and v1["vigente"] == v1["run_id"], "la versión inicial se publica"),
        (broken["estado"] == "detenida", "el problema detiene el pipeline"),
        (not broken["current_cambio"] and broken["vigente"] == v1["run_id"],
         "con el problema current/ no cambia y sigue la versión inicial"),
        (broken["tablero"] == v1["tablero"], "el tablero sigue mostrando la versión inicial"),
        (fixed["vigente"] == fixed["run_id"], "la entrega corregida se publica"),
        (v1["run_id"] in [v["run_id"] for v in versions(d.published) if v["state"] == "vigente"],
         "la versión inicial vuelve a estar vigente"),
        (restored["tablero"] == v1["tablero"] != fixed["tablero"], "el tablero lee de nuevo la versión inicial"),
    ]
    return [msg for ok, msg in expect if not ok]


def run_real(d: Drill, problem: str, cfg: dict) -> list[str]:
    real = resolve(cfg, "published")
    if real.exists():
        shutil.copytree(real, d.published)
    base = {"mobility": resolve(cfg, "mobility"), "migration": resolve(cfg, "migration")}
    mob = pd.read_excel(base["mobility"], sheet_name=cfg["paths"]["mobility_sheet"])
    # solo se reescribe la fuente afectada; la otra se copia tal cual
    if problem == "denominador":
        mig = pd.read_excel(base["migration"], sheet_name=cfg["paths"]["migration_sheet"])
        bad_mob, bad_mig = None, inject(problem, mob, mig)[1]
    else:
        bad_mob, bad_mig = inject(problem, mob, pd.DataFrame())[0], None
    broken = d.run(f"1. copia de la fuente con problema ({problem})", d.write("1-con-problema", bad_mob, bad_mig, base))
    fixed = d.run("2. copia corregida", d.write("2-corregida", None, None, base))
    approved = fixed["vigente"] == fixed["run_id"]
    expect = [
        (broken["estado"] == "detenida", "el problema detiene el pipeline"),
        (not broken["current_cambio"], "con el problema la versión publicada no cambia"),
        (fixed["estado"] == "completada", "la copia corregida completa el flujo"),
        (fixed["current_cambio"] == approved, "current/ solo cambia si la regla aprueba la versión corregida"),
    ]
    return [msg for ok, msg in expect if not ok]


def report_md(summary: dict) -> str:
    lines = [f"# Prueba controlada de fallo y recuperación — {summary['fecha']}", "",
             f"- Datos: **{summary['datos']}**. Problema: **{summary['problema']}** ({PROBLEMS[summary['problema']]}).",
             f"- Carpeta aislada: `{summary['carpeta']}` (no toca `data/raw` ni `mlops/published`).",
             f"- Resultado: **{'todas las comprobaciones se cumplen' if not summary['fallas'] else 'FALLAS: ' + '; '.join(summary['fallas'])}**.",
             "", "| Paso | run_id | Estado | current/ | Vigente | Lo que muestra el tablero |", "|--|--|--|--|--|--|"]
    for s in summary["pasos"]:
        shown = s["tablero"] if isinstance(s["tablero"], str) else ", ".join(
            f"{r['periodo']}: {r['valor']:,}" for r in s["tablero"])
        lines.append(f"| {s['paso']} | `{s['run_id']}` | {s['estado']} | "
                     f"{'cambió' if s['current_cambio'] else 'sin cambios'} | `{s['vigente']}` | {shown} |")
    lines += ["", "## Detalle por paso", ""]
    for s in summary["pasos"]:
        lines.append(f"**{s['paso']}**")
        if s.get("motivo"):
            lines.append(f"- Motivo: {s['motivo']}")
        if s.get("publicacion"):
            lines.append(f"- Publicación: {s['publicacion']}")
        if s.get("controles"):
            lines.append("- Controles: " + ", ".join(f"{k} = {v}" for k, v in s["controles"].items()))
        if s.get("monitoreo"):
            lines.append("- Monitoreo: " + ", ".join(f"{k} = {v}" for k, v in s["monitoreo"].items()))
        lines.append("")
    lines += ["Comprobaciones:", ""] + [f"- [x] {c}" for c in summary["comprobaciones"]
                                        if c not in summary["fallas"]] + [f"- [ ] {c}" for c in summary["fallas"]]
    return "\n".join(lines) + "\n"


CHECKS_SYNTHETIC = ["la versión inicial se publica", "el problema detiene el pipeline",
                    "con el problema current/ no cambia y sigue la versión inicial",
                    "el tablero sigue mostrando la versión inicial", "la entrega corregida se publica",
                    "la versión inicial vuelve a estar vigente", "el tablero lee de nuevo la versión inicial"]
CHECKS_REAL = ["el problema detiene el pipeline", "con el problema la versión publicada no cambia",
               "la copia corregida completa el flujo",
               "current/ solo cambia si la regla aprueba la versión corregida"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    ap.add_argument("--problem", choices=list(PROBLEMS), default="denominador")
    ap.add_argument("--data", choices=["sinteticos", "real"], default="sinteticos")
    ap.add_argument("--output", help="carpeta aislada (por defecto mlops/test_runs/drill-<fecha>)")
    ap.add_argument("--mlflow-principal", action="store_true",
                    help="registrar las corridas en el almacén MLflow de trabajo en vez del de la carpeta aislada")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    box = Path(args.output) if args.output else ROOT / "mlops" / "test_runs" / f"drill-{stamp}"
    if box.exists() and any(box.iterdir()):
        raise SystemExit(f"{box} no está vacía; use otra carpeta")
    box.mkdir(parents=True, exist_ok=True)
    saved = {k: os.environ.get(k) for k in ("MLFLOW_STORAGE", "MLFLOW_TRACKING_URI")}
    if not args.mlflow_principal:
        os.environ["MLFLOW_STORAGE"] = str(box / "mlruns")
        os.environ["MLFLOW_TRACKING_URI"] = f"sqlite:///{box / 'mlruns' / 'mlflow.db'}"

    d = Drill(cfg, box)
    try:
        if args.data == "real":
            failures, checks = run_real(d, args.problem, cfg), CHECKS_REAL
        else:
            failures, checks = run_synthetic(d, args.problem), CHECKS_SYNTHETIC
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    summary = {"fecha": datetime.now().isoformat(timespec="seconds"), "datos": args.data,
               "problema": args.problem, "carpeta": str(box.relative_to(ROOT) if box.is_relative_to(ROOT) else box), "pasos": d.steps,
               "comprobaciones": checks, "fallas": failures}
    (box / "drill_report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    (box / "drill_report.md").write_text(report_md(summary))
    print(f"\nreporte: {box / 'drill_report.md'}")
    print("todas las comprobaciones se cumplen" if not failures else "FALLAS: " + "; ".join(failures))
    print(f"para verlo en el tablero: PUBLISHED_DIR={box / 'published'} python app.py")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
