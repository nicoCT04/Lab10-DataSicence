"""
Publicación controlada de la versión aprobada y restauración de versiones anteriores.

    python -m mlops.publish list
    python -m mlops.publish restore <run_id>
    python -m mlops.publish --published otra/carpeta list

Estructura de mlops/published/:

    current/              versión que lee el tablero (estimates.csv, series.csv, metadata.json, ...)
    versions/<run_id>/    versiones aprobadas anteriores, completas
    history.jsonl         una línea por publicación o restauración

Solo se publica una corrida aprobada por la regla de aceptación. La nueva versión se arma
primero en una carpeta temporal; current/ se reemplaza al final con dos renombres, así que
una falla a mitad de camino no deja al tablero sin la versión anterior.
"""
import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from mlops.config import DEFAULT_CONFIG, load_config, resolve

CURRENT, VERSIONS, HISTORY, META = "current", "versions", "history.jsonl", "metadata.json"
# archivos de la corrida que forman una versión publicada; los dos primeros son obligatorios
FILES = ["estimates.csv", "series.csv", "evaluation.json", "quality_report.json", "config.toml"]
REQUIRED = FILES[:2]


class PublishError(Exception):
    """La versión no se puede publicar o restaurar; current/ queda como estaba."""


def read_meta(version_dir: Path) -> dict | None:
    path = version_dir / META
    return json.loads(path.read_text()) if path.exists() else None


def current(published: Path) -> dict | None:
    """Metadatos de la versión vigente o None si todavía no hay una versión aprobada."""
    return read_meta(published / CURRENT)


def _log(published: Path, **entry):
    entry = {"at": datetime.now().isoformat(timespec="seconds"), **entry}
    with open(published / HISTORY, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _swap_in(published: Path, new_dir: Path) -> str | None:
    """Mueve current/ a versions/<run_id>/ y pone new_dir como current/. Devuelve el run_id anterior."""
    cur, previous = published / CURRENT, None
    (published / VERSIONS).mkdir(parents=True, exist_ok=True)
    if cur.exists():
        meta = read_meta(cur)
        previous = meta["run_id"] if meta else "sin-metadatos-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        archived = published / VERSIONS / previous
        if archived.exists():
            raise PublishError(f"ya existe versions/{previous}; no se sobrescribe una versión archivada")
        cur.rename(archived)
    try:
        new_dir.rename(cur)
    except OSError:
        if previous:  # deja todo como estaba
            (published / VERSIONS / previous).rename(cur)
        raise
    return previous


def publish(run_dir: Path, published: Path, metadata: dict) -> dict:
    """
    Publica la corrida run_dir como versión vigente. metadata debe venir de una corrida
    aprobada (metadata["acceptance"]["approved"] es True); si no, no se toca nada.
    """
    run_dir, published = Path(run_dir), Path(published)
    if not metadata.get("acceptance", {}).get("approved"):
        raise PublishError("la versión no fue aprobada por la regla de aceptación")
    missing = [f for f in REQUIRED if not (run_dir / f).exists()]
    if missing:
        raise PublishError(f"faltan archivos de la corrida: {missing}")

    published.mkdir(parents=True, exist_ok=True)
    staging = published / f".staging-{metadata['run_id']}"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    for name in FILES:
        if (run_dir / name).exists():
            shutil.copy2(run_dir / name, staging / name)
    meta = {**metadata, "published_at": datetime.now().isoformat(timespec="seconds")}
    try:
        previous = _swap_in(published, staging)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    meta["previous"] = previous
    (published / CURRENT / META).write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    _log(published, action="publicar", run_id=meta["run_id"], previous=previous)
    return {"run_id": meta["run_id"], "previous": previous}


def versions(published: Path) -> list[dict]:
    """Versión vigente y anteriores, de la más reciente a la más antigua."""
    published, out = Path(published), []
    meta = current(published)
    if meta:
        out.append({"run_id": meta["run_id"], "state": "vigente", "generated": meta.get("generated"),
                    "published_at": meta.get("published_at")})
    folder = published / VERSIONS
    for d in sorted(folder.iterdir(), reverse=True) if folder.exists() else []:
        m = read_meta(d)
        if d.is_dir() and m:
            out.append({"run_id": m["run_id"], "state": "anterior", "generated": m.get("generated"),
                        "published_at": m.get("published_at")})
    return out


def restore(published: Path, run_id: str) -> dict:
    """Vuelve a poner versions/<run_id>/ como vigente; la vigente pasa a versions/."""
    published = Path(published)
    source = published / VERSIONS / run_id
    meta = read_meta(source) if source.is_dir() else None
    if not meta:
        available = [v["run_id"] for v in versions(published) if v["state"] == "anterior"]
        raise PublishError(f"no existe la versión anterior {run_id}; disponibles: {available or 'ninguna'}")
    if not meta.get("acceptance", {}).get("approved") or not (source / "estimates.csv").exists():
        raise PublishError(f"versions/{run_id} no es una versión aprobada completa")
    # se mueve fuera de versions/ antes del cambio para que no choque con el archivo de la vigente
    staging = published / f".staging-{run_id}"
    source.rename(staging)
    try:
        previous = _swap_in(published, staging)
    except Exception:
        staging.rename(source)
        raise
    _log(published, action="restaurar", run_id=run_id, previous=previous)
    return {"run_id": run_id, "previous": previous}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    ap.add_argument("--published", help="carpeta de versiones (por defecto paths.published de la config)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="versión vigente y anteriores")
    r = sub.add_parser("restore", help="volver a una versión aprobada anterior")
    r.add_argument("run_id")
    args = ap.parse_args(argv)
    published = Path(args.published) if args.published else resolve(load_config(args.config), "published")

    if args.cmd == "list":
        rows = versions(published)
        if not rows:
            print("sin versiones aprobadas: el tablero muestra «Estimaciones no disponibles»")
        for v in rows:
            print(f"{v['state']:<9} {v['run_id']}  generada {v['generated']}  publicada {v['published_at']}")
        return
    try:
        res = restore(published, args.run_id)
    except PublishError as e:
        print(f"no se restauró: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"vigente: {res['run_id']} (la anterior {res['previous']} quedó en {VERSIONS}/)")


if __name__ == "__main__":
    main()
