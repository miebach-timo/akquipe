from pathlib import Path
from stages.stage1_scraper.models import ScrapedData


def build_screenshots(data: ScrapedData, assets_screenshots_dir: Path) -> str:
    labels = {
        "01_fullpage": "Gesamte Seite (Full Page)",
        "02_above_fold": "Above the Fold (Viewport)",
        "03_header": "Header / Navigation",
        "04_main": "Hauptinhalt",
        "05_footer": "Footer",
    }

    gallery_lines = []
    for screenshot_path in data.screenshots:
        fname = Path(screenshot_path).stem
        label = labels.get(fname, fname)
        gallery_lines.append(f"### {label}\n![[assets/screenshots/{Path(screenshot_path).name}]]")

    gallery = "\n\n".join(gallery_lines) or "Keine Screenshots vorhanden."

    return f"""---
title: Screenshots
type: client-audit-section
domain: {data.domain}
screenshot_count: {len(data.screenshots)}
---

# Screenshots — {data.domain}

[[_Overview]] · [[Page-Hierarchy]] · [[User-Flow]]

---

{gallery}
"""
