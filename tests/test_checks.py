"""Controles de calidad con datos sintéticos: cada caso introduce un problema y verifica que se detecta."""
import copy
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from mlops.checks import FAIL, OK, SKIP, WARN, run_checks
from mlops.config import load_config
from mlops.pipeline import run

CFG = load_config()
FIT = CFG["periods"]["fit"]
TARGET = CFG["periods"]["estimate"]


def synthetic():
    """Telefonía del polígono y un subdestino en los meses de ajuste; migración en ajuste + estimación."""
    rows = []
    for m in FIT:
        d = pd.Timestamp(m + "-01")
        for dest in ("Antigua Guatemala", "Jocotenango"):
            for country, seg, v in (("Guatemala", "mayor a 1 dia", 600.0), ("Usa", "menor a 1 dia", 400.0)):
                rows.append(dict(destino=dest, anio=d.year, mes=d.month, fecha=d, pais=country,
                                 es_consecutivo=seg, visitantes=v, dias_persona=v * 2, permanencia_prom=2.0))
    mob = pd.DataFrame(rows)
    mig = pd.DataFrame([dict(**{"Año": p.year, "Mes cod": p.month}, Vía="Aérea", Frontera="Aeropuerto",
                             País="Usa", **{"Tipo de Viajero": "Turista"}, Viajero=300.0)
                        for p in pd.period_range(min(FIT + TARGET), max(FIT + TARGET), freq="M")])
    return mob, mig


def status(report, name):
    return next(r["status"] for r in report if r["control"] == name)


class QualityChecks(unittest.TestCase):
    def test_clean_data_passes(self):
        report = run_checks(*synthetic(), CFG)
        self.assertTrue(all(r["status"] == OK for r in report), report)

    def test_missing_column_stops_and_skips_rest(self):
        mob, mig = synthetic()
        report = run_checks(mob.drop(columns="visitantes"), mig, CFG)
        self.assertEqual(status(report, "Columnas y tipos"), FAIL)
        self.assertTrue(all(r["status"] == SKIP for r in report[1:]))

    def test_incompatible_type(self):
        mob, mig = synthetic()
        report = run_checks(mob.assign(visitantes=mob["visitantes"].astype(str)), mig, CFG)
        self.assertEqual(status(report, "Columnas y tipos"), FAIL)

    def test_fit_month_without_coverage(self):
        mob, mig = synthetic()
        mob = mob[mob["fecha"] != pd.Timestamp(FIT[0] + "-01")]
        self.assertEqual(status(run_checks(mob, mig, CFG), "Fechas y cobertura"), FAIL)

    def test_target_month_without_migration(self):
        mob, mig = synthetic()
        mig = mig[~((mig["Año"] == 2026) & (mig["Mes cod"] == 1))]
        self.assertEqual(status(run_checks(mob, mig, CFG), "Fechas y cobertura"), FAIL)

    def test_inconsistent_year_month(self):
        mob, mig = synthetic()
        mob.loc[0, "mes"] = 12 if mob.loc[0, "mes"] != 12 else 1
        self.assertEqual(status(run_checks(mob, mig, CFG), "Fechas y cobertura"), FAIL)

    def test_duplicated_key(self):
        mob, mig = synthetic()
        mob = pd.concat([mob, mob.iloc[[0]].assign(visitantes=1.0)])
        self.assertEqual(status(run_checks(mob, mig, CFG), "Unicidad"), FAIL)

    def test_migration_key_repeated_is_warning(self):
        mob, mig = synthetic()
        mig = pd.concat([mig, mig.iloc[[0]].assign(Viajero=5.0)])
        self.assertEqual(status(run_checks(mob, mig, CFG), "Unicidad"), WARN)

    def test_missing_allowed_vs_blocking(self):
        mob, mig = synthetic()
        allowed = mob.copy()
        allowed.loc[0, "pais"] = None
        self.assertEqual(status(run_checks(allowed, mig, CFG), "Valores faltantes"), WARN)
        blocking = mob.copy()
        blocking.loc[0, "visitantes"] = np.nan
        self.assertEqual(status(run_checks(blocking, mig, CFG), "Valores faltantes"), FAIL)

    def test_negative_and_nonfinite(self):
        mob, mig = synthetic()
        neg = mob.copy()
        neg.loc[0, "visitantes"] = -5
        self.assertEqual(status(run_checks(neg, mig, CFG), "Valores y denominadores"), FAIL)
        inf = mob.copy()
        inf.loc[0, "visitantes"] = np.inf
        self.assertEqual(status(run_checks(inf, mig, CFG), "Valores y denominadores"), FAIL)

    def test_zero_denominator(self):
        mob, mig = synthetic()
        mig.loc[(mig["Año"] == 2026) & (mig["Mes cod"] == 2), "Viajero"] = 0.0
        self.assertEqual(status(run_checks(mob, mig, CFG), "Valores y denominadores"), FAIL)

    def test_daily_source_breaks_method_rule(self):
        mob, mig = synthetic()
        daily = mob.assign(fecha=mob["fecha"] + pd.Timedelta(days=4))
        self.assertEqual(status(run_checks(daily, mig, CFG), "Regla metodológica"), FAIL)
        with_daily_cols = mob.assign(idfecha=mob["fecha"])
        self.assertEqual(status(run_checks(with_daily_cols, mig, CFG), "Regla metodológica"), FAIL)

    def test_polygon_absent(self):
        mob, mig = synthetic()
        mob = mob[mob["destino"] != "Antigua Guatemala"]
        self.assertEqual(status(run_checks(mob, mig, CFG), "Regla metodológica"), FAIL)


class PipelineStops(unittest.TestCase):
    """Corrida completa sobre archivos sintéticos: con un denominador cero se detiene antes de estimar."""

    def run_with(self, mob, mig):
        tmp = Path(self.tmp.name)
        mob.to_excel(tmp / "mob.xlsx", sheet_name="Antigua", index=False)
        mig.to_excel(tmp / "mig.xlsx", sheet_name="Datos", index=False)
        cfg = copy.deepcopy(CFG)
        cfg["paths"].update(mobility=str(tmp / "mob.xlsx"), migration=str(tmp / "mig.xlsx"),
                            runs=str(tmp / "runs"), published=str(tmp / "published"))
        return run(cfg)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_stops_then_recovers(self):
        mob, mig = synthetic()
        broken = mig.copy()
        broken.loc[broken["Mes cod"] == 9, "Viajero"] = 0.0
        res = self.run_with(mob, broken)
        self.assertEqual(res["status"], "detenida")
        self.assertFalse((Path(res["run_dir"]) / "estimates.csv").exists())

        res = self.run_with(mob, mig)
        self.assertEqual(res["status"], "completada")
        # factor sintético = 1000 / 300 en todos los meses
        self.assertAlmostEqual(res["factor"], 1000 / 300)
        self.assertTrue(np.allclose(res["estimates"]["valor"], 1000.0))


if __name__ == "__main__":
    unittest.main()
