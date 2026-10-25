"""Recorridos de uso reales en Chromium. No ajustan ni regeneran modelos."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.log = tempfile.TemporaryFile()
        cls.server = subprocess.Popen(
            [sys.executable, "-c", "from app import app; app.run(port=8051, debug=False)"],
            cwd=ROOT, stdout=cls.log, stderr=subprocess.STDOUT)
        for _ in range(120):
            try:
                with urlopen("http://127.0.0.1:8051", timeout=1):
                    break
            except OSError:
                if cls.server.poll() is not None:
                    cls.log.seek(0)
                    raise RuntimeError(cls.log.read().decode())
                time.sleep(0.5)
        else:
            cls.server.terminate()
            raise RuntimeError("El servidor de prueba no inició en el puerto 8051")
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.terminate()
        cls.server.wait(timeout=10)
        cls.log.close()

    def setUp(self):
        self.page = self.browser.new_page(viewport={"width": 1440, "height": 1100})
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.on("response", lambda response: self.errors.append(f"HTTP {response.status}: {response.url}")
                     if response.status >= 500 else None)
        self.page.goto("http://127.0.0.1:8051")
        self.page.wait_for_selector("#yearly-bars .main-svg")

    def tearDown(self):
        self.page.close()
        self.assertEqual(self.errors, [])

    def capture(self, name, selector=None):
        directory = os.environ.get("LAB10_SCREENSHOTS")
        if directory:
            Path(directory).mkdir(parents=True, exist_ok=True)
            target = self.page.locator(selector) if selector else self.page
            target.screenshot(path=str(Path(directory) / f"{name}.png"))

    def tab(self, name, graph):
        self.page.get_by_text(name, exact=True).click()
        self.page.wait_for_selector(f"#{graph} .main-svg")
        self.page.wait_for_timeout(600)  # permite completar montaje y ajuste de tamaño de Plotly

    def test_panorama_filters_and_empty_states(self):
        page = self.page
        expect(page.locator("#monthly-title")).to_have_text("Detalle mensual de 2025")
        self.capture("panorama", "#yearly-bars")
        upper = page.locator("#year-range input[type=number]").nth(1)
        upper.fill("2010")
        upper.press("Tab")
        expect(page.locator("#monthly-title")).to_have_text("Detalle mensual de 2010")
        expect(page.locator("#markets-title")).to_have_text("Principales mercados de 2010")
        bar = page.locator("#yearly-bars .trace.bars .point path").first
        bar.scroll_into_view_if_needed()
        bounds = bar.bounding_box()
        # Plotly recibe los clics a través de su capa de arrastre sobre las barras.
        page.mouse.click(bounds["x"] + bounds["width"] / 2, bounds["y"] + bounds["height"] / 2)
        expect(page.locator("#monthly-title")).to_have_text("Detalle mensual de 2009")
        for checkbox in page.locator("#via-filter input").all():
            checkbox.uncheck()
        expect(page.locator("#yearly-bars .annotation-text")).to_contain_text("Seleccione al menos una vía")
        page.locator("#via-filter label").filter(has_text="Marítima").locator("input").check()
        # Con vía elegida, pero sin registros: mensaje diferente de «no eligió vía».
        upper.fill("2026")
        upper.press("Tab")
        lower = page.locator("#year-range input[type=number]").first
        lower.fill("2025")
        lower.press("Tab")
        expect(page.locator("#monthly-title")).to_have_text("Detalle mensual de 2025")
        expect(page.locator("#yearly-bars .annotation-text")).to_contain_text("No hay registros")
        self.capture("sin_datos", "#yearly-bars")

    def test_linked_markets_and_season(self):
        page = self.page
        self.tab("Mercados y fronteras", "market-tree")
        page.locator("#market-tree g.slice").filter(has_text="América Del Centro").locator("path.surface").first.click()
        expect(page.locator("#borders-title")).to_contain_text("América Del Centro")
        self.capture("mercados")
        for checkbox in page.locator("#mk-vias input").all():
            checkbox.uncheck()
        expect(page.locator("#border-bars .annotation-text")).to_contain_text("Seleccione al menos una vía")
        self.tab("Estacionalidad", "season-heatmap")
        image = page.locator("#season-heatmap .heatmaplayer image")
        bounds = image.bounding_box()
        page.mouse.click(bounds["x"] + bounds["width"] / 24, bounds["y"] + bounds["height"] / 36)
        expect(page.locator("#profile-title")).to_contain_text("2009")
        self.capture("estacionalidad")
        # 2026 parcial: no tiene índice anual; no debe dibujar un perfil inventado.
        for index in [0, 1]:
            field = page.locator("#ss-years input[type=number]").nth(index)
            field.fill("2026")
            field.press("Tab")
        expect(page.locator("#season-heatmap .annotation-text")).to_contain_text("No hay años completos")
        expect(page.locator("#season-boxes .annotation-text")).to_contain_text("No hay años completos")
        page.locator("#ss-measure label").filter(has_text="Llegadas").locator("input").check()
        page.wait_for_selector("#season-heatmap .heatmaplayer image")

    def test_forecasts_and_narrow_layout(self):
        page = self.page
        self.tab("Pronósticos", "forecast-lines")
        expect(page.locator("#window-label")).to_contain_text("63 meses")
        self.assertEqual(page.locator("#metrics-table td.dash-cell").count(), 15)
        self.capture("pronosticos", "#forecast-lines")
        page.locator("#forecast-lines .rangeselector .button").filter(has_text="5 años").click()
        expect(page.locator("#window-label")).to_have_text(
            "Periodo analizado: jun 2021 a jun 2026 (61 meses de evaluación)")
        page.locator("#forecast-lines .rangeselector .button").filter(has_text="Todo").click()
        expect(page.locator("#window-label")).to_contain_text("63 meses")
        page.set_viewport_size({"width": 600, "height": 1000})
        page.wait_for_timeout(600)  # espera el redimensionamiento de Plotly
        self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 600)
        legend = page.locator("#forecast-lines .legend").bounding_box()
        buttons = page.locator("#forecast-lines .rangeselector").bounding_box()
        self.assertLessEqual(legend["y"] + legend["height"], buttons["y"])
        self.capture("pronosticos_600", "#forecast-lines")
        for checkbox in page.locator("#model-filter input").all():
            checkbox.uncheck()
        expect(page.locator("#error-by-month .annotation-text")).to_contain_text("Seleccione al menos un modelo")
        self.assertEqual(page.locator("#metrics-table td.dash-cell").count(), 0)


if __name__ == "__main__":
    unittest.main()
