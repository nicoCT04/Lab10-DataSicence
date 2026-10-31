"""La prueba controlada completa con cada tipo de problema, en carpetas temporales."""
import json
import tempfile
import unittest
from pathlib import Path

from mlops.drill import PROBLEMS, main


class ControlledFailure(unittest.TestCase):
    def test_each_problem_stops_keeps_version_and_restores(self):
        for problem in PROBLEMS:
            with self.subTest(problem=problem), tempfile.TemporaryDirectory() as tmp:
                main(["--problem", problem, "--output", tmp])  # SystemExit si falla una comprobación
                report = json.loads((Path(tmp) / "drill_report.json").read_text())
                self.assertEqual(report["fallas"], [])
                broken = report["pasos"][1]
                self.assertEqual(broken["estado"], "detenida")
                self.assertFalse(broken["current_cambio"])
                self.assertEqual(report["pasos"][-1]["vigente"], report["pasos"][0]["run_id"])


if __name__ == "__main__":
    unittest.main()
