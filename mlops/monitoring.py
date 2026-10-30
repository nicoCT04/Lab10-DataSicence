"""
Monitoreo por ejecución: actualización, calidad y resultados.

Cada verificación devuelve ok, alerta o sin datos. Una alerta pide revisión: no detiene el
flujo ni cambia la decisión de publicar, que depende solo de los controles de calidad y de la
regla de aceptación. La referencia para comparar es la versión vigente (la última aprobada).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd


OK, ALERT, NODATA = "ok", "alerta", "sin datos"


def quality_stats(mob: pd.DataFrame, mig: pd.DataFrame, cfg: dict) -> dict:
    """Faltantes, duplicados y cobertura de las fuentes; se guardan con cada versión publicada."""
    q, polygon = cfg["quality"], cfg["sources"]["polygon"]
    missing = {f"telefonía.{c}": int(mob[c].isna().sum())
               for c in [*q["mobility_columns"], *q["allowed_missing"]] if c in mob.columns}
    missing |= {f"migración.{c}": int(mig[c].isna().sum()) for c in q["migration_columns"] if c in mig.columns}
    dups = {}
    if set(q["mobility_key"]) <= set(mob.columns):
        dups["telefonía"] = int(mob.duplicated(q["mobility_key"]).sum())
    mig_key = [c for c in q["migration_key"] if c in mig.columns]
    if mig_key:
        dups["migración"] = int(mig.duplicated(mig_key).sum())

    coverage = {"telefonia": [], "migracion": []}
    if {"destino", "fecha"} <= set(mob.columns):
        sub = mob[mob["destino"].astype(str).str.strip() == polygon]
        fecha = pd.to_datetime(sub["fecha"], errors="coerce").dropna()
        coverage["telefonia"] = sorted({str(p) for p in fecha.dt.to_period("M")})
    if {"Año", "Mes cod", "Tipo de Viajero"} <= set(mig.columns):
        sub = mig[mig["Tipo de Viajero"].isin(cfg["sources"]["traveler_types"]) & mig["Mes cod"].between(1, 12)]
        coverage["migracion"] = sorted({f"{int(y):04d}-{int(m):02d}" for y, m in zip(sub["Año"], sub["Mes cod"])})
    return {"rows": {"telefonía": len(mob), "migración": len(mig)},
            "missing": missing, "duplicates": dups, "coverage": coverage}


def check(name: str, status: str, detail: str, **extra) -> dict:
    return {"check": name, "status": status, "detail": detail, **extra}


def freshness(stats: dict, est: pd.DataFrame | None, cfg: dict, published: dict | None) -> dict:
    """¿Llegan las fuentes al último mes que pide la configuración y cubren los resultados lo esperado?"""
    p = cfg["periods"]
    expected = {"telefonia": max(p["fit"]), "migracion": max(p["fit"] + p["estimate"])}
    problems, notes = [], []
    for source, last_needed in expected.items():
        have = stats["coverage"][source]
        last = have[-1] if have else None
        if last is None or last < last_needed:
            problems.append(f"{source} llega hasta {last or 'sin datos'}; se esperaba {last_needed}")
        else:
            notes.append(f"{source} hasta {last} (se necesita {last_needed})")
    if est is not None:
        missing = sorted(set(p["estimate"]) - set(est["periodo"].astype(str)))
        if missing:
            problems.append("resultados sin los meses " + ", ".join(missing))
        else:
            notes.append("resultados para " + ", ".join(p["estimate"]))
    if published is None:
        problems.append("no hay versión aprobada publicada: el tablero indica que las estimaciones no están "
                        "disponibles")
    else:
        notes.append(f"versión vigente generada {published.get('generated')}")
    status = ALERT if problems else OK
    return check("Actualización", status, "; ".join(problems + notes), expected=expected)


def _grew(new: int, old: int, cfg: dict) -> bool:
    m = cfg["monitoring"]
    return new - old >= m["min_rows_change"] and new > old * (1 + m["max_relative_change"])


def quality_change(stats: dict, published: dict | None, cfg: dict) -> dict:
    """Compara faltantes, duplicados y cobertura con los de la versión vigente."""
    base = (published or {}).get("quality_stats")
    if not base:
        return check("Calidad", NODATA, "no hay una versión aprobada con qué comparar; esta ejecución "
                                        "servirá de referencia si se aprueba")
    alerts = []
    for kind, label in (("missing", "faltantes"), ("duplicates", "duplicados")):
        for key, new in stats[kind].items():
            old = base[kind].get(key, 0)
            if _grew(new, old, cfg):
                alerts.append(f"{label} en {key}: {old} → {new}")
        for key in set(base[kind]) - set(stats[kind]):
            alerts.append(f"{label}: ya no se puede medir {key} (columna ausente)")
    for source, have in stats["coverage"].items():
        lost = sorted(set(base["coverage"].get(source, [])) - set(have))
        if lost:
            alerts.append(f"cobertura de {source}: faltan meses que antes tenía ({', '.join(lost)})")
    ref = published.get("run_id")
    if alerts:
        return check("Calidad", ALERT, f"frente a la versión vigente {ref}: " + "; ".join(alerts))
    return check("Calidad", OK, f"sin cambios relevantes en faltantes, duplicados ni cobertura frente a {ref}")


def results(series: pd.DataFrame | None, est: pd.DataFrame | None, cfg: dict,
            published_est: pd.DataFrame | None) -> dict:
    """Estimaciones negativas o no finitas y variaciones mensuales que exceden el umbral."""
    if est is None or series is None:
        return check("Resultados", NODATA, "la ejecución no generó estimaciones; no hay resultados que revisar")
    limit = cfg["acceptance"]["max_monthly_change"]
    alerts, notes = [], []
    values = pd.to_numeric(est["valor"], errors="coerce")
    bad = est.loc[~np.isfinite(values) | (values < 0), "periodo"].astype(str).tolist()
    if bad:
        alerts.append("estimaciones negativas o no finitas en " + ", ".join(bad))

    # serie que ve el tablero: observados y, en su lugar, las estimaciones
    s = series.assign(periodo=series["periodo"].astype(str)).set_index("periodo")["visitantes_obs"].copy()
    est_values = dict(zip(est["periodo"].astype(str), values))
    for period, v in est_values.items():
        if period in s.index and pd.isna(s[period]):
            s[period] = v
    s = s.dropna()
    s = s[s > 0]
    change = s.pct_change().dropna()
    jumps = change[change.abs() > limit]
    for period, c in jumps.items():
        alerts.append(f"variación de {c:+.0%} en {period} frente al mes anterior (umbral ±{limit:.0%})")
    notes.append(f"mayor variación mensual {change.abs().max():.0%}" if len(change) else "")

    if published_est is not None:
        old = dict(zip(published_est["periodo"].astype(str), published_est["valor"]))
        for period, v in est_values.items():
            if period in old and old[period] > 0 and abs(v / old[period] - 1) > limit:
                alerts.append(f"{period} cambia {v / old[period] - 1:+.0%} frente a la versión vigente")

    # 7.3: el error predictivo se actualiza solo si ya existe el observado del mes estimado
    comparable = {p: (float(series.loc[series["periodo"].astype(str) == p, "visitantes_obs"].iloc[0]), v)
                  for p, v in est_values.items()
                  if (series["periodo"].astype(str) == p).any()
                  and series.loc[series["periodo"].astype(str) == p, "visitantes_obs"].notna().any()}
    if comparable:
        errs = {p: abs(o - v) for p, (o, v) in comparable.items()}
        notes.append("error con observados nuevos: " + ", ".join(f"{p} {e:,.0f}" for p, e in errs.items()))
    else:
        notes.append("sin observaciones comparables para " + ", ".join(est_values)
                     + "; el error predictivo no se actualiza")
    detail = "; ".join(x for x in alerts + notes if x)
    if alerts:
        detail += ". Requiere revisión; una variación alta no demuestra por sí sola pérdida de precisión"
    return check("Resultados", ALERT if alerts else OK, detail,
                 comparable={p: list(v) for p, v in comparable.items()})


def run_monitoring(stats: dict, series, est, cfg: dict, published_dir: Path) -> list[dict]:
    published_dir = Path(published_dir)
    meta_path = published_dir / "current" / "metadata.json"
    published = json.loads(meta_path.read_text()) if meta_path.exists() else None
    est_path = published_dir / "current" / "estimates.csv"
    published_est = pd.read_csv(est_path) if published and est_path.exists() else None
    return [freshness(stats, est, cfg, published),
            quality_change(stats, published, cfg),
            results(series, est, cfg, published_est)]


def write_report(checks: list[dict], run_dir: Path) -> None:
    (Path(run_dir) / "monitoring.json").write_text(json.dumps(checks, indent=2, ensure_ascii=False))
