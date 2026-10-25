"""Exporta el documento integrado sin servicios externos. Requiere requirements-dev.txt y Chromium."""
from html import escape
from pathlib import Path
import re
import tempfile

from markdown_it import MarkdownIt
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / "docs/diseno_final.md"
    _, metadata, body = source.read_text(encoding="utf-8").split("---", 2)
    fields = dict(re.findall(r'^(\w+): "(.*)"$', metadata, re.MULTILINE))
    body = re.sub(r"\{width=\d+%\}", "", body)
    rendered = MarkdownIt("commonmark").enable("table").render(body)
    cover = "".join(f"<p>{escape(fields[key])}</p>" for key in ["title", "subtitle", "author", "date"])
    html = f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
    <base href="{source.parent.as_uri()}/"><title>{escape(fields['title'])}</title>
    <style>
    @page {{ size:A4; margin:18mm 16mm 18mm; }}
    body {{ font:10.5pt/1.45 Arial,sans-serif; color:#1E2A38; }}
    .cover {{ padding-top:55mm; break-after:page; text-align:center; }}
    .cover p:first-child {{ font-size:24pt; font-weight:bold; }}
    .cover p:nth-child(2) {{ font-size:18pt; color:#4A6382; }}
    h1 {{ font-size:17pt; margin:22pt 0 9pt; }}
    h2 {{ font-size:13pt; color:#4A6382; margin:16pt 0 7pt; }}
    h1,h2,h3 {{ break-after:avoid; }}
    p {{ orphans:3; widows:3; }}
    table {{ border-collapse:collapse; width:100%; font-size:9pt; margin:10pt 0; }}
    th,td {{ border:1px solid #D7DDE5; padding:5pt; text-align:left; vertical-align:top; overflow-wrap:anywhere; }}
    th {{ background:#ECEFF3; }} tr {{ break-inside:avoid; }} thead {{ display:table-header-group; }}
    img {{ display:block; max-width:100%; max-height:210mm; margin:8pt auto; object-fit:contain; }}
    code {{ font-size:9pt; overflow-wrap:anywhere; }} a {{ color:#305D7C; overflow-wrap:anywhere; }}
    </style></head><body><header class="cover">{cover}</header>{rendered}</body></html>"""
    with tempfile.TemporaryDirectory() as directory, sync_playwright() as playwright:
        page_path = Path(directory) / "document.html"
        page_path.write_text(html, encoding="utf-8")
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(page_path.as_uri(), wait_until="networkidle")
        page.pdf(path=str(ROOT / "docs/Diseno_Final_Lab10.pdf"), print_background=True,
                 display_header_footer=True, header_template="<span></span>",
                 footer_template='<div style="font:9px Arial;width:100%;text-align:center;color:#5B6675">'
                                 'CC3084 · Documento de diseño · <span class="pageNumber"></span>'
                                 ' / <span class="totalPages"></span></div>')
        browser.close()
    print("Generado: docs/Diseno_Final_Lab10.pdf")


if __name__ == "__main__":
    main()
