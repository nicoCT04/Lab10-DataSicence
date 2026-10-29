"""
Seis controles de calidad. Cada uno devuelve ok, advertencia o falla; una falla
detiene el pipeline antes de tocar la versión publicada.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from mlops.config import months

OK, WARN, FAIL, SKIP = "ok", "advertencia", "falla", "no ejecutado"


def result(name: str, status: str, detail: str, **extra) -> dict:
    return {"control": name, "status": status, "detail": detail, **extra}


def type_ok(s: pd.Series, kind: str) -> bool:
    if kind == "int":
        return pd.api.types.is_integer_dtype(s)
    if kind == "number":
        return pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)
    if kind == "date":
        return pd.api.types.is_datetime64_any_dtype(s)
    return pd.api.types.is_string_dtype(s) or pd.api.types.is_object_dtype(s)


def check_columns(mob, mig, cfg) -> dict:
    q, problems = cfg["quality"], []
    for label, df, spec in (("telefonía", mob, q["mobility_columns"]), ("migración", mig, q["migration_columns"])):
        for col, kind in spec.items():
            if col not in df.columns:
                problems.append(f"{label}: falta «{col}»")
            elif not type_ok(df[col], kind):
                problems.append(f"{label}: «{col}» es {df[col].dtype}, se esperaba {kind}")
    if problems:
        return result("Columnas y tipos", FAIL, "; ".join(problems))
    return result("Columnas y tipos", OK, "columnas indispensables presentes con tipo compatible")


def mobility_periods(mob, polygon) -> pd.PeriodIndex:
    sub = mob[mob["destino"].str.strip() == polygon]
    return pd.PeriodIndex(pd.to_datetime(sub["fecha"]).dt.to_period("M").unique()).sort_values()


def migration_totals(mig, cfg) -> pd.Series:
    sub = mig[mig["Tipo de Viajero"].isin(cfg["sources"]["traveler_types"])]
    period = pd.PeriodIndex.from_fields(year=sub["Año"], month=sub["Mes cod"], freq="M")
    return sub.groupby(period)["Viajero"].sum()


def check_dates(mob, mig, cfg) -> dict:
    fails, warns = [], []
    fecha = pd.to_datetime(mob["fecha"], errors="coerce")
    if fecha.isna().any():
        fails.append(f"{int(fecha.isna().sum())} fechas inválidas en telefonía")
    bad_ym = (fecha.dt.year != mob["anio"]) | (fecha.dt.month != mob["mes"])
    if bad_ym[fecha.notna()].any():
        fails.append(f"{int(bad_ym[fecha.notna()].sum())} filas con anio/mes distintos de fecha")
    bad_month = ~mig["Mes cod"].between(1, 12)
    if bad_month.any():
        fails.append(f"{int(bad_month.sum())} filas de migración con mes fuera de 1-12")

    p = cfg["periods"]
    fit, target = months(p["fit"]), months(p["estimate"])
    have_mob = mobility_periods(mob[fecha.notna()], cfg["sources"]["polygon"])
    have_mig = migration_totals(mig[~bad_month], cfg).index
    miss_mob = fit.difference(have_mob)
    miss_mig = fit.union(target).difference(have_mig)
    if len(miss_mob):
        fails.append("meses de ajuste sin telefonía: " + ", ".join(map(str, miss_mob)))
    if len(miss_mig):
        fails.append("meses sin migración: " + ", ".join(map(str, miss_mig)))
    overlap = target.intersection(have_mob)
    if len(overlap):
        warns.append("hay telefonía en meses marcados para estimar: " + ", ".join(map(str, overlap)))
    extra = have_mob.difference(fit.union(target))
    if len(extra):
        warns.append("meses con telefonía fuera del ajuste (no se usan): " + ", ".join(map(str, extra)))

    coverage = {"telefonia": [str(x) for x in have_mob],
                "migracion": f"{have_mig.min()} a {have_mig.max()}" if len(have_mig) else "sin datos"}
    if fails:
        return result("Fechas y cobertura", FAIL, "; ".join(fails + warns), coverage=coverage)
    if warns:
        return result("Fechas y cobertura", WARN, "; ".join(warns), coverage=coverage)
    return result("Fechas y cobertura", OK, "fechas válidas y meses necesarios cubiertos", coverage=coverage)


def check_unique(mob, mig, cfg) -> dict:
    q = cfg["quality"]
    dup_mob = int(mob.duplicated(q["mobility_key"]).sum())
    dup_rows = int(mig.duplicated().sum())
    key = [c for c in q["migration_key"] if c in mig.columns]
    dup_key = int(mig.duplicated(key).sum())
    if dup_mob or dup_rows:
        return result("Unicidad", FAIL,
                      f"{dup_mob} claves repetidas en telefonía ({', '.join(q['mobility_key'])}); "
                      f"{dup_rows} filas idénticas en migración")
    if dup_key:
        return result("Unicidad", WARN,
                      f"{dup_key} claves repetidas en migración con otros atributos distintos; se suman al agregar el mes")
    return result("Unicidad", OK, "sin duplicados según la clave")


def check_missing(mob, mig, cfg) -> dict:
    allowed = set(cfg["quality"]["allowed_missing"])
    needed_mob = [c for c in cfg["quality"]["mobility_columns"] if c not in allowed]
    blocking = {f"telefonía.{c}": int(mob[c].isna().sum()) for c in needed_mob}
    blocking |= {f"migración.{c}": int(mig[c].isna().sum()) for c in cfg["quality"]["migration_columns"]}
    blocking = {k: v for k, v in blocking.items() if v}
    permitted = {c: int(mob[c].isna().sum()) for c in allowed if c in mob.columns and mob[c].isna().any()}
    if blocking:
        return result("Valores faltantes", FAIL, f"faltantes que impiden estimar: {blocking}")
    if permitted:
        return result("Valores faltantes", WARN,
                      f"faltantes permitidos: {permitted} (pais vacío se agrupa como «No identificado»)")
    return result("Valores faltantes", OK, "sin faltantes")


def check_values(mob, mig, cfg) -> dict:
    problems = []
    for label, s in (("telefonía.visitantes", mob["visitantes"]), ("migración.Viajero", mig["Viajero"])):
        v = pd.to_numeric(s, errors="coerce")
        if (v < 0).any():
            problems.append(f"{int((v < 0).sum())} conteos negativos en {label}")
        nonfinite = ~np.isfinite(v.dropna())
        if nonfinite.any():
            problems.append(f"{int(nonfinite.sum())} valores no finitos en {label}")
    p = cfg["periods"]
    totals = migration_totals(mig, cfg).reindex(months(p["fit"]).union(months(p["estimate"])))
    zero = totals[totals == 0]
    if len(zero):
        problems.append("denominador de migración igual a cero en: " + ", ".join(map(str, zero.index)))
    if problems:
        return result("Valores y denominadores", FAIL, "; ".join(problems))
    return result("Valores y denominadores", OK, "conteos no negativos y finitos; denominadores mayores que cero")


def check_method(mob, mig, cfg) -> dict:
    """La serie debe salir de la base mensual del polígono, no de sumar presencias diarias ni subdestinos."""
    problems, polygon = [], cfg["sources"]["polygon"]
    daily = [c for c in cfg["quality"]["daily_columns"] if c in mob.columns]
    if daily:
        problems.append(f"la fuente tiene columnas de la base diaria: {daily}")
    fecha = pd.to_datetime(mob["fecha"], errors="coerce").dropna()
    if (fecha.dt.day != 1).any():
        problems.append(f"{int((fecha.dt.day != 1).sum())} fechas que no son día 1 (registro diario)")
    per_month = fecha.groupby(fecha.dt.to_period("M")).nunique()
    if (per_month > 1).any():
        problems.append("más de una fecha por mes: " + ", ".join(map(str, per_month[per_month > 1].index)))
    names = mob["destino"].str.strip().unique()
    if polygon not in names:
        problems.append(f"no existe el polígono «{polygon}»")
    if problems:
        return result("Regla metodológica", FAIL, "; ".join(problems))
    others = sorted(n for n in names if n != polygon)
    return result("Regla metodológica", OK,
                  f"serie mensual de la base mensual; solo «{polygon}», sin sumar {others}")


CHECKS = [check_columns, check_dates, check_unique, check_missing, check_values, check_method]
NAMES = ["Columnas y tipos", "Fechas y cobertura", "Unicidad", "Valores faltantes",
         "Valores y denominadores", "Regla metodológica"]


def run_checks(mob: pd.DataFrame, mig: pd.DataFrame, cfg: dict) -> list[dict]:
    """Si fallan columnas y tipos, el resto no se puede evaluar con seguridad."""
    out = [check_columns(mob, mig, cfg)]
    for check, name in zip(CHECKS[1:], NAMES[1:]):
        if out[0]["status"] == FAIL:
            out.append(result(name, SKIP, "no ejecutado: faltan columnas indispensables"))
            continue
        try:
            out.append(check(mob, mig, cfg))
        except Exception as e:
            out.append(result(name, FAIL, f"error al evaluar: {type(e).__name__}: {e}"))
    return out


def failed(report: list[dict]) -> list[dict]:
    return [r for r in report if r["status"] in (FAIL, SKIP)]


def write_report(report: list[dict], run_dir: Path) -> None:
    (run_dir / "quality_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    lines = ["# Reporte de calidad", "", "| Control | Resultado | Detalle |", "|--|--|--|"]
    lines += [f"| {r['control']} | {r['status']} | {r['detail']} |" for r in report]
    verdict = "DETENIDO: falla crítica" if failed(report) else "Aprobado para continuar"
    lines += ["", f"**{verdict}**", ""]
    (run_dir / "quality_report.md").write_text("\n".join(lines))
