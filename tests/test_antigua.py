"""Pestaña de Antigua: lee solo la versión publicada y nunca dibuja ene-feb 2026 como cero."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.antigua import frames, load_current
from src.figures import antigua_lines

PERIODS = [str(p) for p in pd.period_range("2025-09", "2026-06", freq="M")]


def write_version(folder: Path, run_id="r1", jan=1_000_000.0, feb=800_000.0):
    cur = folder / "current"
    cur.mkdir(parents=True)
    pd.DataFrame({"destino": "Antigua Guatemala", "periodo": ["2026-01", "2026-02"], "valor": [jan, feb],
                  "unidad": "visitantes únicos del mes", "tipo": "Estimación", "run_id": run_id,
                  "fecha_generacion": "2026-10-30T15:00:00", "version_procedimiento": "factor-reparto-1.0"}
                 ).to_csv(cur / "estimates.csv", index=False)
    obs = [np.nan if p in ("2026-01", "2026-02") else 900_000.0 for p in PERIODS]
    pd.DataFrame({"periodo": PERIODS, "visitantes_obs": obs}).to_csv(cur / "series.csv", index=False)
    (cur / "metadata.json").write_text(json.dumps({
        "run_id": run_id, "generated": "2026-10-30T15:00:00", "published_at": "2026-10-30T15:01:00",
        "procedure_version": "factor-reparto-1.0",
        "evaluation": {"months": ["2026-04", "2026-05", "2026-06"], "candidate": {"MAE": 50_000.0, "MAPE": 5.5}}}))


class AntiguaTab(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pub = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_without_approved_version_is_unavailable(self):
        self.assertIsNone(load_current(self.pub))

    def test_incomplete_estimates_are_not_shown(self):
        write_version(self.pub)
        est = pd.read_csv(self.pub / "current" / "estimates.csv").drop(columns="run_id")
        est.to_csv(self.pub / "current" / "estimates.csv", index=False)
        self.assertIsNone(load_current(self.pub))

    def test_reads_published_version(self):
        write_version(self.pub)
        data = load_current(self.pub)
        self.assertEqual([r["valor"] for r in data["estimates"]], [1_000_000.0, 800_000.0])
        self.assertEqual(data["meta"]["evaluation"]["candidate"]["MAE"], 50_000.0)

    def test_months_without_coverage_are_gaps_not_zero(self):
        write_version(self.pub)
        obs, est = frames(load_current(self.pub))
        fig = antigua_lines(obs, est)
        observed = next(t for t in fig.data if t.name == "Observado")
        estimated = next(t for t in fig.data if t.name == "Estimación")
        jan = list(pd.to_datetime(observed.x)).index(pd.Timestamp("2026-01-01"))
        self.assertTrue(np.isnan(observed.y[jan]))
        self.assertFalse(observed.connectgaps)
        self.assertNotIn(0, list(observed.y))
        self.assertEqual(list(estimated.y), [1_000_000.0, 800_000.0])
        self.assertNotEqual(observed.line.color, estimated.marker.color)

    def test_window_filter_only_trims_published_data(self):
        write_version(self.pub)
        obs, est = frames(load_current(self.pub), "2026")
        self.assertEqual(obs["fecha"].dt.year.unique().tolist(), [2026])
        self.assertEqual(len(est), 2)


class AntiguaCallback(unittest.TestCase):
    """El callback del tablero, sin navegador: textos de directivo y estado sin versión aprobada."""

    @classmethod
    def setUpClass(cls):
        import app
        cls.app = app

    def test_unavailable_message(self):
        cards, fig, note, warning = self.app.update_antigua(None, "all")
        self.assertIn("Estimaciones no disponibles", str(cards))
        self.assertEqual(fig.layout.annotations[0].text, "Estimaciones no disponibles")
        self.assertIn("Limitaciones", warning)

    def test_available_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_version(Path(tmp))
            data = load_current(Path(tmp))
        cards, fig, note, warning = self.app.update_antigua(data, "all")
        text = str(cards)
        self.assertIn("1,000,000", text)
        self.assertIn("± 5.5 %", text)
        self.assertIn("30 oct 2026", text)
        self.assertIn("abr 2026, may 2026, jun 2026", note)
        self.assertNotIn("r1", text + note + warning)  # sin detalles técnicos de la ejecución


if __name__ == "__main__":
    unittest.main()
