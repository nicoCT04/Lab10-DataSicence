"""Publicación controlada y restauración sobre carpetas temporales; no toca mlops/published."""
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from mlops.publish import PublishError, current, main, publish, restore, versions


def fake_run(root: Path, run_id: str, value: float) -> tuple[Path, dict]:
    """Corrida mínima con los archivos que se publican y metadatos de una versión aprobada."""
    d = root / "runs" / run_id
    d.mkdir(parents=True)
    pd.DataFrame({"destino": "Antigua Guatemala", "periodo": ["2026-01", "2026-02"], "valor": [value, value],
                  "unidad": "visitantes únicos del mes", "tipo": "Estimación", "run_id": run_id,
                  "fecha_generacion": "2026-10-30T15:00:00", "version_procedimiento": "factor-reparto-1.0"}
                 ).to_csv(d / "estimates.csv", index=False)
    pd.DataFrame({"periodo": ["2025-12", "2026-01"], "visitantes_obs": [1.0, None]}).to_csv(
        d / "series.csv", index=False)
    (d / "evaluation.json").write_text("{}")
    meta = {"run_id": run_id, "generated": "2026-10-30T15:00:00",
            "acceptance": {"approved": True, "reason": "aprobada"}}
    return d, meta


def files(folder: Path) -> dict:
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}


class Publication(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.pub = self.root / "published"

    def tearDown(self):
        self.tmp.cleanup()

    def test_without_versions_nothing_is_current(self):
        self.assertIsNone(current(self.pub))
        self.assertEqual(versions(self.pub), [])

    def test_first_and_second_publication_keep_previous(self):
        d1, m1 = fake_run(self.root, "r1", 100.0)
        self.assertIsNone(publish(d1, self.pub, m1)["previous"])
        d2, m2 = fake_run(self.root, "r2", 200.0)
        self.assertEqual(publish(d2, self.pub, m2)["previous"], "r1")
        self.assertEqual(current(self.pub)["run_id"], "r2")
        self.assertEqual(current(self.pub)["previous"], "r1")
        self.assertTrue((self.pub / "versions" / "r1" / "estimates.csv").exists())
        est = pd.read_csv(self.pub / "current" / "estimates.csv")
        self.assertEqual(est["valor"].tolist(), [200.0, 200.0])
        self.assertEqual([v["run_id"] for v in versions(self.pub)], ["r2", "r1"])
        history = [json.loads(line) for line in (self.pub / "history.jsonl").read_text().splitlines()]
        self.assertEqual([h["action"] for h in history], ["publicar", "publicar"])

    def test_rejected_version_does_not_touch_current(self):
        d1, m1 = fake_run(self.root, "r1", 100.0)
        publish(d1, self.pub, m1)
        before = files(self.pub / "current")
        d2, m2 = fake_run(self.root, "r2", 200.0)
        m2["acceptance"]["approved"] = False
        with self.assertRaises(PublishError):
            publish(d2, self.pub, m2)
        self.assertEqual(files(self.pub / "current"), before)
        self.assertFalse((self.pub / "versions").exists() and any((self.pub / "versions").iterdir()))

    def test_incomplete_run_is_not_published(self):
        d1, m1 = fake_run(self.root, "r1", 100.0)
        (d1 / "estimates.csv").unlink()
        with self.assertRaises(PublishError):
            publish(d1, self.pub, m1)
        self.assertIsNone(current(self.pub))

    def test_restore_previous_and_back(self):
        for run_id, value in (("r1", 100.0), ("r2", 200.0)):
            d, m = fake_run(self.root, run_id, value)
            publish(d, self.pub, m)
        self.assertEqual(restore(self.pub, "r1")["previous"], "r2")
        self.assertEqual(current(self.pub)["run_id"], "r1")
        self.assertEqual(pd.read_csv(self.pub / "current" / "estimates.csv")["valor"].iloc[0], 100.0)
        self.assertTrue((self.pub / "versions" / "r2").is_dir())
        self.assertFalse((self.pub / "versions" / "r1").exists())
        restore(self.pub, "r2")
        self.assertEqual(current(self.pub)["run_id"], "r2")

    def test_restore_unknown_version_fails_without_changes(self):
        d1, m1 = fake_run(self.root, "r1", 100.0)
        publish(d1, self.pub, m1)
        before = files(self.pub)
        with self.assertRaises(PublishError):
            restore(self.pub, "no-existe")
        self.assertEqual(files(self.pub), before)

    def test_cli_list_and_restore(self):
        for run_id in ("r1", "r2"):
            d, m = fake_run(self.root, run_id, 1.0)
            publish(d, self.pub, m)
        main(["--published", str(self.pub), "restore", "r1"])
        self.assertEqual(current(self.pub)["run_id"], "r1")
        with self.assertRaises(SystemExit):
            main(["--published", str(self.pub), "restore", "r9"])


if __name__ == "__main__":
    unittest.main()
