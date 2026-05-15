import json
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

from shared import logger
from shared.run_state import RunState, Status
from stages.stage1_scraper.extractors.colors import extract_colors
from stages.stage1_scraper.extractors.components import extract_components
from stages.stage1_scraper.extractors.content import extract_content, extract_meta
from stages.stage1_scraper.extractors.icons import extract_icons
from stages.stage1_scraper.extractors.motion import extract_motion_tokens
from stages.stage1_scraper.extractors.raw_assets import extract_raw_assets
from stages.stage1_scraper.extractors.screenshots import take_screenshots
from stages.stage1_scraper.extractors.sitemap import extract_sitemap
from stages.stage1_scraper.extractors.spacing import extract_spacing_tokens
from stages.stage1_scraper.extractors.typography import extract_typography
from stages.stage1_scraper.models import (
    ComponentInventory, MetaData, MotionTokens, RawAssets, ScrapedData, SpacingTokens,
)


async def run_scraper(state: RunState, settings) -> RunState:
    state.scraper.status = Status.RUNNING

    run_dir = state.run_dir(settings.output_dir)
    scraped_dir = run_dir / "scraped"
    screenshots_dir = scraped_dir / "screenshots"
    assets_dir = scraped_dir / "assets"
    scraped_dir.mkdir(parents=True, exist_ok=True)

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            page = await context.new_page()

            logger.info(f"Lade Startseite: {state.url}")
            await page.goto(state.url, wait_until="networkidle", timeout=settings.scraper_timeout)

            # Wait for JS to settle
            await page.wait_for_timeout(2000)

            logger.dim("  → Extrahiere Metadaten...")
            meta_raw = await extract_meta(page)
            meta = MetaData(**meta_raw)

            logger.dim("  → Extrahiere Inhalte & CTAs...")
            content = await extract_content(page)

            logger.dim("  → Extrahiere Farben & Kontrast...")
            colors = await extract_colors(page)

            logger.dim("  → Extrahiere Typografie...")
            typography = await extract_typography(page)

            logger.dim("  → Erkenne Icons & SVGs...")
            icons = await extract_icons(page, assets_dir)

            logger.dim("  → Erstelle Screenshots (Desktop)...")
            screenshot_paths = await take_screenshots(page, screenshots_dir, state.domain)

            logger.dim("  → Mobile + Tablet Screenshots...")
            mobile_path = None
            tablet_path = None
            try:
                await page.set_viewport_size({"width": 375, "height": 812})
                await page.wait_for_timeout(500)
                mobile_file = screenshots_dir / f"{state.domain}_mobile.png"
                await page.screenshot(path=str(mobile_file), full_page=False)
                mobile_path = str(mobile_file)

                await page.set_viewport_size({"width": 768, "height": 1024})
                await page.wait_for_timeout(500)
                tablet_file = screenshots_dir / f"{state.domain}_tablet.png"
                await page.screenshot(path=str(tablet_file), full_page=False)
                tablet_path = str(tablet_file)

                await page.set_viewport_size({"width": 1440, "height": 900})
            except Exception as e:
                logger.dim(f"    Multi-Viewport Screenshots fehlgeschlagen: {e}")

            logger.dim("  → Extrahiere Raw-Assets + Framework-Detection...")
            raw_assets_dict = await extract_raw_assets(page, scraped_dir)

            logger.dim("  → Extrahiere Spacing-Tokens...")
            spacing_dict = await extract_spacing_tokens(page)

            logger.dim("  → Extrahiere Motion-Tokens...")
            motion_dict = await extract_motion_tokens(page)

            logger.dim("  → Extrahiere Komponenten-Inventar...")
            components_dict = await extract_components(page)

            logger.dim("  → Crawle Seitenhierarchie...")
            sitemap = await extract_sitemap(
                context,
                state.url,
                max_pages=settings.scraper_max_pages,
                max_depth=settings.scraper_max_depth,
                timeout=settings.scraper_timeout,
            )

            await browser.close()

        scraped = ScrapedData(
            url=state.url,
            domain=state.domain,
            scraped_at=datetime.now().isoformat(),
            pages_crawled=len(sitemap.all_urls),
            meta=meta,
            content=content,
            colors=colors,
            typography=typography,
            icons=icons,
            sitemap=sitemap,
            screenshots=[str(p) for p in screenshot_paths],
            mobile_screenshot_path=mobile_path,
            tablet_screenshot_path=tablet_path,
            raw_assets=RawAssets(**raw_assets_dict),
            spacing_tokens=SpacingTokens(**spacing_dict),
            motion_tokens=MotionTokens(**motion_dict),
            components=ComponentInventory(**components_dict),
        )

        data_path = scraped_dir / "data.json"
        data_path.write_text(scraped.model_dump_json(indent=2), encoding="utf-8")

        state.scraper.status = Status.DONE
        state.scraper.data_path = str(data_path)
        state.scraper.screenshots_dir = str(screenshots_dir)
        state.scraper.pages_crawled = scraped.pages_crawled

        logger.success(f"Scraping abgeschlossen — {scraped.pages_crawled} Seiten, {len(colors.palette)} Farben, {len(screenshot_paths)} Screenshots")

    except Exception as e:
        state.scraper.status = Status.FAILED
        state.scraper.error = str(e)
        logger.error(f"Scraping fehlgeschlagen: {e}")
        raise

    return state


def load_scraped_data(state: RunState, output_dir: Path) -> ScrapedData:
    if not state.scraper.data_path:
        raise ValueError("Kein Scraper-Output vorhanden — zuerst Stage 1 ausführen.")
    path = Path(state.scraper.data_path)
    from stages.stage1_scraper.models import ScrapedData
    return ScrapedData.model_validate_json(path.read_text(encoding="utf-8"))
