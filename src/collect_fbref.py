from playwright.sync_api import sync_playwright


def fetch_page(url: str) -> str:
    """Load a webpage and return its HTML."""

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)

        try:
            page = browser.new_page()

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30_000,
            )

            html = page.content()

            return html

        finally:
            browser.close()

if __name__ == "__main__":
    url = "https://fbref.com/en/comps/Big5/stats/players/Big-5-European-Leagues-Stats"

    html = fetch_page(url)

    print(len(html))
    print(html[:500])