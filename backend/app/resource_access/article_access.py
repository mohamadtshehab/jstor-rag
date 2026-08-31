from __future__ import annotations

import asyncio
import json
import random
from pathlib import Path

from playwright.async_api import BrowserContext, BrowserType, Cookie, Page, Playwright, ViewportSize, async_playwright
from playwright_stealth import Stealth

from ..contracts.dtos import ArticleData, DocumentMetadata
from ..contracts.interfaces import IArticleAccess, IConfigUtility

_JSTOR_HOSTNAME = "jstor.org"
_JSTOR_HOME = "https://www.jstor.org"

# Selectors that indicate a CAPTCHA or bot-challenge page is active
_CAPTCHA_SELECTORS = [
    "iframe[src*='challenges.cloudflare.com']",  # Cloudflare Turnstile iframe
    "iframe[src*='hcaptcha.com']",               # hCaptcha
    "iframe[src*='recaptcha']",                  # reCAPTCHA v2
    "#challenge-form",                           # Cloudflare JS challenge form
    "div.cf-turnstile",                          # Cloudflare Turnstile widget div
    "div#px-captcha",                            # PerimeterX CAPTCHA
]

# How long to wait for the user to solve a CAPTCHA (5 minutes)
_CAPTCHA_SOLVE_TIMEOUT_MS = 5 * 60 * 1000

# Realistic viewport — most common desktop resolution
_VIEWPORT: ViewportSize = {"width": 1920, "height": 1080}

# Common desktop user agent (kept in sync with Chrome stable)
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class ArticleAccess(IArticleAccess):
    """Fetches JSTOR article content via Playwright.

    Encapsulates Academic Resource Locality: JSTOR DOM structure, selectors,
    and extraction rules. All volatility for "how we get article data" lives here.

    Bot-evasion strategy (in order of impact):
    1. System Chrome via `playwright_channel = "chrome"` — avoids missing DRM/API signals.
    2. playwright-stealth applied to every context — patches navigator.webdriver, WebGL, etc.
    3. Persistent user data directory — builds real browsing history over time.
    4. Cached session state — reuses authenticated cookies across runs.
    5. Natural navigation pattern — lands on jstor.org homepage before deep-linking.
    6. Human-like timing — random delays before interaction and before extraction.

    CAPTCHA handling:
    - If a CAPTCHA is detected in headed mode, the browser is already visible; the
      user is prompted to solve it and the script waits for the challenge to clear.
    - If a CAPTCHA is detected in headless mode, the context is closed and relaunched
      as visible so the user can solve it. Once cleared, state is saved, and the
      context is relaunched headless for the actual content extraction.
    """

    _JSTOR_SELECTORS = {
        "content_spans": [
            "span.markedContent > span[role='presentation']",
            "div.textLayer > span[role='presentation']",
            "span[role=\"presentation\"]",
        ],
        "login_dialog": "mfe-access-workflow-pharos-modal[name='AccessWorkflowModal']",
        "paywall": ".paywall, .restricted-access, [data-testid='paywall']",
    }

    def __init__(self, config: IConfigUtility | None = None) -> None:
        self._config = config

    # ── Public interface ──────────────────────────────────────────────────────

    def validate_url(self, url: str) -> bool:
        return _JSTOR_HOSTNAME in url

    async def fetch_article(self, url: str) -> ArticleData:
        scraper_cfg = self._config.read_scraper_config() if self._config else None
        channel = (scraper_cfg.playwright_channel if scraper_cfg else "") or "chrome"
        user_data_dir = (
            scraper_cfg.playwright_user_data_dir if scraper_cfg else "./data/playwright_user"
        )
        headless = scraper_cfg.headless if scraper_cfg else True
        do_login_flow = scraper_cfg.do_login_flow if scraper_cfg else False
        login_dialog_wait_seconds = (
            scraper_cfg.login_dialog_wait_seconds if scraper_cfg else 0.0
        )
        state_path = self._get_state_path()

        async with async_playwright() as pw:
            context, page = await self._open_context(
                pw, headless, channel, user_data_dir, state_path
            )
            try:
                if do_login_flow:
                    await self._do_login_flow(
                        page, context, login_dialog_wait_seconds, state_path
                    )

                await self._warm_up_navigation(page, url)
                await self._handle_turnaway(page)

                captcha = await self._detect_captcha(page)
                if captcha:
                    if headless:
                        # Can't show a headless window — close and reopen visibly.
                        await context.close()
                        context, page = await self._open_context(
                            pw, False, channel, user_data_dir, state_path
                        )
                        await page.goto(url, wait_until="domcontentloaded", timeout=60_000)

                    print(
                        f"\n[jstor-rag] CAPTCHA detected ({captcha}).\n"
                        "Please solve it in the browser window. Waiting up to 5 minutes..."
                    )
                    await self._wait_for_captcha_solve(page)
                    print("[jstor-rag] CAPTCHA solved. Continuing...")

                    state_path.parent.mkdir(parents=True, exist_ok=True)
                    await context.storage_state(path=str(state_path))

                    if headless:
                        # Relaunch headless now that session has valid cookies.
                        await context.close()
                        context, page = await self._open_context(
                            pw, True, channel, user_data_dir, state_path
                        )
                        await self._warm_up_navigation(page, url)
                        await self._handle_turnaway(page)

                # Wait for the JS viewer to finish rendering in all paths.
                # domcontentloaded fires before JSTOR's viewer mounts, so
                # scrollHeight would be 0 and _scroll_viewer_to_end would be a no-op
                # without this gate. If the viewer doesn't appear it may be because
                # the site redirected to a login/paywall flow; try a login fallback
                # and then retry waiting for the viewer before failing.
                try:
                    await self._wait_for_viewer(page)
                except Exception as first_exc:
                    # If viewer didn't appear, attempt interactive/login flow
                    if not do_login_flow:
                        try:
                            await self._do_login_flow(page, context, login_dialog_wait_seconds, state_path)
                            # reload the article and wait again for the viewer
                            await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                            await self._wait_for_viewer(page, timeout=60_000)
                        except Exception:
                            # If fallback also fails, re-raise the original error for visibility
                            raise first_exc
                    else:
                        # Already configured to run login flow; re-raise
                        raise

                if not do_login_flow and not await self._is_logged_in(page):
                    await self._do_login_flow(page, context, 0.0, state_path)
                    await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                    await self._wait_for_viewer(page)
                    await self._human_pause(2.0, 4.0)

                await self._scroll_viewer_to_end(page)
                await self._human_pause(1.0, 2.5)

                text = await self._extract_content(page)

                state_path.parent.mkdir(parents=True, exist_ok=True)
                await context.storage_state(path=str(state_path))

            finally:
                await context.close()

        return ArticleData(
            text=text,
            metadata=DocumentMetadata(url=url),
        )

    async def fetch_metadata(self, url: str) -> DocumentMetadata:
        """Fetch title, authors, and DOI — not yet implemented."""
        raise NotImplementedError

    # ── Context management ────────────────────────────────────────────────────

    async def _open_context(
        self,
        pw: Playwright,
        headless: bool,
        channel: str,
        user_data_dir: str,
        state_path: Path,
    ) -> tuple[BrowserContext, Page]:
        """Launch a persistent context, apply stealth, restore cookies, and open a page."""
        browser_type: BrowserType = getattr(pw, "chromium")
        context = await browser_type.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel=channel,
            headless=headless,
            viewport=_VIEWPORT,
            user_agent=_USER_AGENT,
            locale="en-US",
            timezone_id="America/New_York",
            args=["--disable-blink-features=AutomationControlled"],
        )
        stealth = Stealth()
        await stealth.apply_stealth_async(context)
        if state_path.exists():
            await context.add_cookies(
                _load_cookies_from_state(state_path)  # type: ignore[arg-type]
            )
        page = await context.new_page()
        return context, page

    # ── Navigation helpers ────────────────────────────────────────────────────

    async def _warm_up_navigation(self, page: Page, article_url: str) -> None:
        """Navigate via jstor.org homepage before deep-linking to avoid cold-start bot signals."""
        await page.goto(_JSTOR_HOME, wait_until="domcontentloaded", timeout=60_000)
        await self._human_pause(2.0, 4.5)
        await page.mouse.move(
            random.randint(300, 1200), random.randint(200, 700)
        )
        await self._human_pause(0.5, 1.5)
        await page.goto(article_url, wait_until="domcontentloaded", timeout=60_000)
        await self._human_pause(1.0, 2.0)

    async def _handle_turnaway(self, page: Page) -> bool:
        """Detect and bypass JSTOR turnaway (free-view click-through) pages.

        If present, extracts the read-now href from the access button and
        navigates directly to it, avoiding Shadow DOM interaction.
        Returns True if a turnaway was detected and handled.
        """
        try:
            btn = page.locator('[data-qa="turnaway-read-online"]')
            if await btn.count() == 0:
                return False
            href = await btn.get_attribute("href")
            if href:
                target = href if href.startswith("http") else f"{_JSTOR_HOME}{href}"
                await page.goto(target, wait_until="domcontentloaded", timeout=60_000)
            else:
                await btn.click()
            await self._human_pause(1.0, 2.0)
            return True
        except Exception:
            return False

    async def _detect_captcha(self, page: Page) -> str | None:
        """Return the first matched CAPTCHA selector, or None if no challenge is present."""
        for selector in _CAPTCHA_SELECTORS:
            try:
                if await page.locator(selector).count() > 0:
                    return selector
            except Exception:
                continue
        return None

    async def _wait_for_captcha_solve(self, page: Page) -> None:
        """Block until the article content appears, indicating the CAPTCHA was solved."""
        await self._wait_for_viewer(page, timeout=_CAPTCHA_SOLVE_TIMEOUT_MS)

    async def _is_logged_in(self, page: Page) -> bool:
        """Heuristic: check for the presence of the login button to detect logged-out state."""
        try:
            login_btn = page.get_by_test_id("access-workflow-button").get_by_text(
                "Log in", exact=True
            )
            await login_btn.wait_for(state="visible", timeout=3000)
            return False
        except Exception:
            return True

    async def _scroll_viewer_to_end(self, page: Page) -> None:
        """Scroll div.viewer-wrapper > div.viewer incrementally to the end.

        JSTOR lazy-loads span.markedContent nodes as the viewer scrolls, so
        a full incremental scroll is required to ensure all text spans are
        present in the DOM before extraction.
        """
        _VIEWER = "div.viewer-wrapper > div.viewer"
        _STEP = 600

        scroll_height: int = await page.evaluate(
            f"document.querySelector('{_VIEWER}')?.scrollHeight ?? 0"
        )
        current = 0
        while current < scroll_height:
            current = min(current + _STEP, scroll_height)
            await page.evaluate(
                f"document.querySelector('{_VIEWER}')?.scrollTo(0, {current})"
            )
            await self._human_pause(0.2, 0.6)
            scroll_height = await page.evaluate(
                f"document.querySelector('{_VIEWER}')?.scrollHeight ?? {scroll_height}"
            )

    @staticmethod
    async def _human_pause(lo: float, hi: float) -> None:
        await asyncio.sleep(random.uniform(lo, hi))

    # ── Login flow ────────────────────────────────────────────────────────────

    async def _do_login_flow(
        self,
        page: Page,
        context: BrowserContext,
        login_dialog_wait_seconds: float,
        state_path: Path,
    ) -> None:
        """Open jstor.org, click Log in, fill credentials, save session state."""
        await page.goto(_JSTOR_HOME, wait_until="load", timeout=60_000)
        await self._human_pause(2.0, 5.0)

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
            return  # Already logged in via persistent profile

        dialog = page.locator(self._JSTOR_SELECTORS["login_dialog"])
        try:
            await dialog.wait_for(state="visible", timeout=5000)
        except Exception:
            return  # No dialog = already authenticated

        await self._human_pause(1.0, 3.0)

        scraper_cfg = self._config.read_scraper_config() if self._config else None
        email = scraper_cfg.login_email if scraper_cfg else ""
        password = scraper_cfg.login_password if scraper_cfg else ""
        if email and password:
            await dialog.locator('mfe-access-workflow-pharos-text-input[name="email"] >> input').fill(email)
            await self._human_pause(0.3, 0.8)
            await dialog.locator('mfe-access-workflow-pharos-text-input[name="password"] >> input').fill(password)
            await self._human_pause(0.5, 1.5)
            submit_btn = (
                dialog.locator('mfe-access-workflow-pharos-button[type="submit"]')
                .filter(visible=True)
                .first
            )
            await submit_btn.click(delay=random.randint(50, 150))
            await page.wait_for_load_state("networkidle", timeout=15_000)
        elif login_dialog_wait_seconds > 0:
            await page.wait_for_timeout(int(login_dialog_wait_seconds * 1000))

        state_path.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(state_path))

    # ── Content extraction ────────────────────────────────────────────────────

    async def _extract_content(self, page: Page) -> str:
        for selector in self._JSTOR_SELECTORS["content_spans"]:
            spans = page.locator(selector)
            if await spans.count() > 0:
                texts = await spans.all_text_contents()
                return "\n".join(t.strip() for t in texts if t.strip())

        raise ValueError("No content spans found")

    async def _extract_title(self, page: Page) -> str:
        raise NotImplementedError

    async def _extract_authors(self, page: Page) -> list[str]:
        raise NotImplementedError

    async def _extract_doi(self, page: Page) -> str:
        raise NotImplementedError

    async def _wait_for_viewer(self, page: Page, timeout: int = 30_000) -> None:
        """Wait until any known viewer layer has attached to the DOM."""
        errors: list[Exception] = []
        for selector in self._JSTOR_SELECTORS["content_spans"]:
            try:
                await page.wait_for_selector(selector, state="attached", timeout=timeout)
                return
            except Exception as exc:
                errors.append(exc)
        raise errors[0]

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_state_path(self) -> Path:
        if self._config:
            path = Path(self._config.read_scraper_config().playwright_state_path)
        else:
            path = Path("./data/jstor_auth_state.json")
        return path.resolve()


def _load_cookies_from_state(state_path: Path) -> list[Cookie]:
    """Parse cookies from a Playwright storage_state JSON file."""
    try:
        data = json.loads(state_path.read_text())
        return data.get("cookies", [])  # type: ignore[return-value]
    except Exception:
        return []
