#!/usr/bin/env -S uv run python
"""Test article fetch in a visible browser window.

Usage:
    uv run python scripts/test_article_fetch.py [JSTOR_URL] [--login]

Example:
    uv run python scripts/test_article_fetch.py "https://www.jstor.org/stable/12345678"
    uv run python scripts/test_article_fetch.py "https://www.jstor.org/stable/12345678" --login

With --login: Opens jstor.org, clicks Log in, waits for dialog, then pauses for
manual login. Session is cached to data/jstor_auth_state.json. Subsequent runs
with --login use the cache and skip the wait.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add backend root to path so we can import app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.resource_access.article_access import ArticleAccess
from app.utilities.config_utility import ConfigUtility


async def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    url = args[0] if args else "https://www.jstor.org/"
    do_login = "--login" in flags

    # Set env before ConfigUtility() — it reads at init
    os.environ["JSTOR_RAG_PLAYWRIGHT_HEADLESS"] = "true"
    os.environ["JSTOR_RAG_PLAYWRIGHT_DO_LOGIN_FLOW"] = "true" if do_login else "false"

    config = ConfigUtility()
    access = ArticleAccess(config=config)
    print(f"Fetching: {url}")
    if do_login:
        print("Login flow: will open jstor.org, click Log in, fill credentials.\n")
    else:
        print("Headless mode.\n")
    result = await access.fetch_article(url)
    print("--- Metadata ---")
    print(f"Title: {result.metadata.title}")
    print(f"Authors: {result.metadata.authors}")
    print(f"DOI: {result.metadata.doi}")
    print(f"\n--- Content ({len(result.text)} chars) ---")
    print(result.text[:2000] + result.text[-2000:] + ("..." if len(result.text) > 2000 else ""))


if __name__ == "__main__":
    asyncio.run(main())
