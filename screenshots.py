"""Take screenshots of each chart from the HTML report for README."""
from playwright.sync_api import sync_playwright
import os

HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "reading_report.html")
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1200, "height": 900})
    page.goto(f"file://{HTML_PATH}", wait_until="networkidle")
    page.wait_for_timeout(3000)  # Wait for plotly charts to render

    chart_ids = [
        ("chart_0", "rank"),
        ("chart_1", "timeline"),
        ("chart_2", "distribution"),
        ("chart_3", "shelf"),
        ("chart_4", "heatmap"),
    ]

    for div_id, name in chart_ids:
        element = page.locator(f"#{div_id}")
        if element.count() > 0:
            path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
            element.screenshot(path=path)
            print(f"Saved: {path}")

    browser.close()
    print("Done.")
