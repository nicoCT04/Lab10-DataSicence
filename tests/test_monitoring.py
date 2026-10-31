"""Verificaciones de monitoreo con datos sintéticos: cada caso provoca una alerta concreta."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from mlops.config import load_config
from mlops.monitoring import ALERT, NODATA, OK, quality_stats, run_monitoring
from tests.test_checks import synthetic

CFG = load_config()


def series_and_estimates(jan=1000.0, feb=1000.0):
    """Serie como la de prepare(): observados de 1000 y ene-feb sin telefonía."""
    periods = pd.period_range("2025-09", "2026-06", freq="M")
    obs = [np.nan if str(p) in ("2026-01", "2026-02") else 1000.0 for p in periods]
    series = pd.DataFrame({"periodo": periods, "visitantes_obs": obs, "migracion": 300.0})
    est = pd.DataFrame({"periodo": ["2026-01", "2026-02"], "valor": [jan, feb]})
    return series, est


class Monitoring(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pub = Path(self.tmp.name)
        self.mob, self.mig = synthetic()
        self.stats = quality_stats(self.mob, self.mig, CFG)

    def tearDown(self):
        self.tmp.cleanup()

    def publish_baseline(self, stats=None, est=None):
        """Simula una versión vigente con sus estadísticas de calidad."""
        cur = self.pub / "current"
        cur.mkdir()
        (cur / "metadata.json").write_text(json.dumps({"run_id": "base", "generated": "2026-10-30T15:00:00",
                                                       "quality_stats": stats or self.stats}))
        (est if est is not None else series_and_estimates()[1]).to_csv(cur / "estimates.csv", index=False)

    def by_name(self, checks):
        return {c["check"]: c for c in checks}

    def test_clean_run_against_baseline_is_ok(self):
        self.publish_baseline()
        checks = self.by_name(run_monitoring(self.stats, *series_and_estimates(), CFG, self.pub))
        self.assertEqual({k: c["status"] for k, c in checks.items()},
                         {"Actualización": OK, "Calidad": OK, "Resultados": OK})
        self.assertIn("el error predictivo no se actualiza", checks["Resultados"]["detail"])

    def test_without_published_version(self):
        checks = self.by_name(run_monitoring(self.stats, *series_and_estimates(), CFG, self.pub))
        self.assertEqual(checks["Actualización"]["status"], ALERT)
        self.assertIn("no hay versión aprobada", checks["Actualización"]["detail"])
        self.assertEqual(checks["Calidad"]["status"], NODATA)

    def test_stale_migration_is_flagged(self):
        mig = self.mig[~((self.mig["Año"] == 2026) & (self.mig["Mes cod"] == 6))]
        checks = self.by_name(run_monitoring(quality_stats(self.mob, mig, CFG), None, None, CFG, self.pub))
        self.assertEqual(checks["Actualización"]["status"], ALERT)
        self.assertIn("migracion llega hasta 2026-05", checks["Actualización"]["detail"])
        self.assertEqual(checks["Resultados"]["status"], NODATA)

    def test_more_missing_and_duplicates_than_baseline(self):
        self.publish_baseline()
        mob = self.mob.copy()
        mob.loc[:9, "permanencia_prom"] = np.nan
        mob = pd.concat([mob, mob.iloc[:6]])
        checks = self.by_name(run_monitoring(quality_stats(mob, self.mig, CFG), None, None, CFG, self.pub))
        detail = checks["Calidad"]["detail"]
        self.assertEqual(checks["Calidad"]["status"], ALERT)
        self.assertIn("faltantes en telefonía.permanencia_prom: 0 → 16", detail)
        self.assertIn("duplicados en telefonía: 0 → 6", detail)

    def test_small_change_is_not_an_alert(self):
        self.publish_baseline()
        mob = self.mob.copy()
        mob.loc[:1, "permanencia_prom"] = np.nan  # 2 filas: por debajo de min_rows_change
        checks = self.by_name(run_monitoring(quality_stats(mob, self.mig, CFG), None, None, CFG, self.pub))
        self.assertEqual(checks["Calidad"]["status"], OK)

    def test_lost_coverage(self):
        self.publish_baseline()
        mob = self.mob[self.mob["fecha"] != pd.Timestamp("2025-09-01")]
        checks = self.by_name(run_monitoring(quality_stats(mob, self.mig, CFG), None, None, CFG, self.pub))
        self.assertEqual(checks["Calidad"]["status"], ALERT)
        self.assertIn("2025-09", checks["Calidad"]["detail"])

    def test_negative_and_nonfinite_estimates(self):
        series, _ = series_and_estimates()
        est = pd.DataFrame({"periodo": ["2026-01", "2026-02"], "valor": [-5.0, np.inf]})
        checks = self.by_name(run_monitoring(self.stats, series, est, CFG, self.pub))
        self.assertEqual(checks["Resultados"]["status"], ALERT)
        self.assertIn("negativas o no finitas en 2026-01, 2026-02", checks["Resultados"]["detail"])

    def test_large_monthly_change_is_alert_for_review(self):
        checks = self.by_name(run_monitoring(self.stats, *series_and_estimates(jan=1500.0), CFG, self.pub))
        detail = checks["Resultados"]["detail"]
        self.assertEqual(checks["Resultados"]["status"], ALERT)
        self.assertIn("+50% en 2026-01", detail)
        self.assertIn("no demuestra por sí sola pérdida de precisión", detail)

    def test_change_against_published_estimate(self):
        # la serie nueva es suave; lo que cambia es la estimación de feb frente a la versión vigente
        old = pd.DataFrame({"periodo": ["2026-01", "2026-02"], "valor": [1000.0, 500.0]})
        self.publish_baseline(est=old)
        checks = self.by_name(run_monitoring(self.stats, *series_and_estimates(), CFG, self.pub))
        detail = checks["Resultados"]["detail"]
        self.assertIn("2026-02 cambia +100% frente a la versión vigente", detail)
        self.assertNotIn("2026-01 cambia", detail)

    def test_error_updates_only_with_comparable_observations(self):
        series, est = series_and_estimates()
        series.loc[series["periodo"] == pd.Period("2026-01", "M"), "visitantes_obs"] = 1100.0
        checks = self.by_name(run_monitoring(self.stats, series, est, CFG, self.pub))
        self.assertEqual(checks["Resultados"]["comparable"], {"2026-01": [1100.0, 1000.0]})
        self.assertIn("2026-01 100", checks["Resultados"]["detail"])

    def test_stats_survive_missing_columns(self):
        stats = quality_stats(self.mob.drop(columns=["visitantes", "fecha"]), self.mig, CFG)
        self.assertEqual(stats["coverage"]["telefonia"], [])
        self.assertNotIn("telefonía.visitantes", stats["missing"])


if __name__ == "__main__":
    unittest.main()
