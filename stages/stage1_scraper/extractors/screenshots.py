from pathlib import Path
from playwright.async_api import Page


async def take_screenshots(page: Page, screenshots_dir: Path, domain: str) -> list[str]:
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []

    # Full-page screenshot
    full_path = screenshots_dir / "01_fullpage.png"
    await page.screenshot(path=str(full_path), full_page=True)
    saved.append(str(full_path))

    # Viewport screenshot (above the fold)
    fold_path = screenshots_dir / "02_above_fold.png"
    await page.screenshot(path=str(fold_path), full_page=False)
    saved.append(str(fold_path))

    # Section screenshots: hero, nav, footer
    sections = [
        ("nav, header, [role=banner]", "03_header"),
        ("main, [role=main], article, .content, .main", "04_main"),
        ("footer, [role=contentinfo]", "05_footer"),
    ]

    for selector, name in sections:
        try:
            el = page.locator(selector).first
            if await el.count() > 0:
                path = screenshots_dir / f"{name}.png"
                await el.screenshot(path=str(path))
                saved.append(str(path))
        except Exception:
            pass

    return saved
