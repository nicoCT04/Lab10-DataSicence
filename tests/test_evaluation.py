"""Validación temporal y regla de aceptación con series sintéticas de resultado conocido."""
import copy
import unittest

import numpy as np
import pandas as pd

from mlops.checks import FAIL, OK
from mlops.config import load_config
from mlops.evaluation import accept, baseline, candidate, evaluate, mae_ratio, metrics

CFG = load_config()


def series(factors: dict, migration: float = 100.0) -> pd.DataFrame:
    """Serie destino-mes con un factor dado por mes; ene-feb 2026 sin telefonía."""
    span = pd.period_range("2025-09", "2026-06", freq="M")
    rows = []
    for p in span:
        f = factors.get(str(p))
        rows.append({"periodo": p, "migracion": migration,
                     "visitantes_obs": f * migration if f is not None else np.nan,
                     "factor": f if f is not None else np.nan})
    return pd.DataFrame(rows)


FACTORS = {"2025-09": 3.0, "2025-10": 3.0, "2025-11": 3.0, "2025-12": 3.0,
           "2026-03": 3.0, "2026-04": 4.0, "2026-05": 5.0, "2026-06": 6.0}
REPORT_OK = [{"control": "Columnas y tipos", "status": OK}]
ESTIMATES_OK = pd.DataFrame({"periodo": ["2026-01", "2026-02"], "valor": [1000.0, 900.0]})


def evaluation(mape: float, ratio: float) -> dict:
    return {"candidate": {"MAE": 100.0 * ratio, "MAPE": mape},
            "reference": {"MAE": 100.0}, "ratio_mae_vs_reference": ratio}


class TemporalValidation(unittest.TestCase):
    def test_factor_uses_only_previous_months(self):
        c = candidate(series(FACTORS), pd.Period("2026-05", "M"))
        self.assertEqual(c["months_used"], ["2025-09", "2025-10", "2025-11", "2025-12", "2026-03", "2026-04"])
        self.assertAlmostEqual(c["factor"], (3.0 * 5 + 4.0) / 6)

    def test_future_months_do_not_change_the_estimate(self):
        target = pd.Period("2026-04", "M")
        changed = dict(FACTORS, **{"2026-05": 50.0, "2026-06": 99.0})
        self.assertEqual(candidate(series(FACTORS), target), candidate(series(changed), target))

    def test_months_without_mobility_are_not_used(self):
        c = candidate(series(FACTORS), pd.Period("2026-04", "M"))
        self.assertNotIn("2026-01", c["months_used"])
        self.assertNotIn("2026-02", c["months_used"])

    def test_baseline_is_last_observed_value_before_target(self):
        b = baseline(series(FACTORS), pd.Period("2026-03", "M"))
        self.assertEqual(b["from"], "2025-12")  # ene-feb no tienen dato observado
        self.assertEqual(b["estimate"], 300.0)

    def test_both_procedures_evaluated_on_the_same_months(self):
        ev = evaluate(series(FACTORS), CFG)
        self.assertEqual(ev["evaluated_months"], CFG["periods"]["evaluation"])
        self.assertEqual(ev["candidate"]["n"], ev["reference"]["n"])

    def test_evaluation_month_without_observed_value_stops(self):
        cfg = copy.deepcopy(CFG)
        cfg["periods"]["evaluation"] = ["2026-01"]
        with self.assertRaises(ValueError):
            evaluate(series(FACTORS), cfg)

    def test_metrics_on_known_values(self):
        m = metrics([100, 200], [90, 230])
        self.assertAlmostEqual(m["MAE"], 20.0)
        self.assertAlmostEqual(m["RMSE"], np.sqrt((100 + 900) / 2))
        self.assertAlmostEqual(m["MAPE"], (10 + 15) / 2)

    def test_mape_excludes_zero_observations(self):
        m = metrics([0, 100], [10, 90])
        self.assertEqual(m["mape_excluded"], 1)
        self.assertAlmostEqual(m["MAPE"], 10.0)
        self.assertIsNone(metrics([0, 0], [1, 2])["MAPE"])


class ReferenceRatio(unittest.TestCase):
    def test_perfect_reference_and_candidate_count_as_equal(self):
        self.assertEqual(mae_ratio(0.0, 0.0), 1.0)

    def test_floating_point_residue_counts_as_zero(self):
        self.assertEqual(mae_ratio(1e-10, 0.0), 1.0)

    def test_perfect_reference_makes_any_error_infinitely_worse(self):
        self.assertEqual(mae_ratio(5.0, 0.0), float("inf"))


class AcceptanceRule(unittest.TestCase):
    def test_approves_when_all_conditions_hold(self):
        d = accept(REPORT_OK, ESTIMATES_OK, evaluation(5.0, 1.0), CFG)
        self.assertTrue(d["approved"], d["reason"])

    def test_rejects_failed_quality_control(self):
        report = REPORT_OK + [{"control": "Unicidad", "status": FAIL}]
        self.assertFalse(accept(report, ESTIMATES_OK, evaluation(5.0, 1.0), CFG)["approved"])

    def test_rejects_missing_month(self):
        self.assertFalse(accept(REPORT_OK, ESTIMATES_OK.iloc[:1], evaluation(5.0, 1.0), CFG)["approved"])

    def test_rejects_negative_or_non_finite_estimates(self):
        for bad in (-1.0, np.nan, np.inf):
            est = ESTIMATES_OK.assign(valor=[1000.0, bad])
            self.assertFalse(accept(REPORT_OK, est, evaluation(5.0, 1.0), CFG)["approved"], bad)

    def test_rejects_mape_above_threshold(self):
        d = accept(REPORT_OK, ESTIMATES_OK, evaluation(CFG["acceptance"]["max_mape"] + 0.1, 1.0), CFG)
        self.assertFalse(d["approved"])
        self.assertIn("Error del procedimiento", d["reason"])

    def test_rejects_when_much_worse_than_reference(self):
        d = accept(REPORT_OK, ESTIMATES_OK,
                   evaluation(5.0, CFG["acceptance"]["max_ratio_vs_baseline"] + 0.01), CFG)
        self.assertFalse(d["approved"])
        self.assertIn("Comparación con la referencia", d["reason"])

    def test_thresholds_are_inclusive(self):
        acc = CFG["acceptance"]
        d = accept(REPORT_OK, ESTIMATES_OK, evaluation(acc["max_mape"], acc["max_ratio_vs_baseline"]), CFG)
        self.assertTrue(d["approved"], d["reason"])


if __name__ == "__main__":
    unittest.main()
