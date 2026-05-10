from pathlib import Path
from playwright.async_api import Page
from stages.stage1_scraper.models import IconData


_LIBRARY_PATTERNS = [
    ("Font Awesome", ["fontawesome", "font-awesome", "fa-", "fas ", "far ", "fab "]),
    ("Material Icons", ["material-icons", "material-symbols", "fonts.googleapis.com/icon"]),
    ("Bootstrap Icons", ["bootstrap-icons", "bi bi-", "bi-"]),
    ("Heroicons", ["heroicons"]),
    ("Lucide", ["lucide"]),
    ("Phosphor", ["phosphor"]),
    ("Feather", ["feather-icons", "feather icon"]),
    ("Ionicons", ["ionicons"]),
    ("Tabler Icons", ["tabler-icons"]),
]


async def extract_icons(page: Page, assets_dir: Path | None = None) -> IconData:
    data = await page.evaluate("""
    () => {
        const sources = [];

        // Link tags (CDN stylesheets)
        for (const link of document.querySelectorAll('link[href]')) {
            sources.push(link.href || '');
        }
        // Script tags
        for (const script of document.querySelectorAll('script[src]')) {
            sources.push(script.src || '');
        }
        // Class names from elements (sample)
        const classNames = [];
        for (const el of [...document.querySelectorAll('[class]')].slice(0, 200)) {
            classNames.push(el.className);
        }

        // Inline SVGs
        const svgs = [...document.querySelectorAll('svg')];
        const svgData = svgs.slice(0, 30).map(svg => svg.outerHTML);

        return { sources, classNames: classNames.join(' '), svg_count: svgs.length, svgData };
    }
    """)

    libraries: list[str] = []
    all_text = " ".join(data["sources"]) + " " + data["classNames"]

    for lib_name, patterns in _LIBRARY_PATTERNS:
        if any(p.lower() in all_text.lower() for p in patterns):
            libraries.append(lib_name)

    svg_files: list[str] = []
    if assets_dir and data["svgData"]:
        icons_dir = assets_dir / "icons"
        icons_dir.mkdir(parents=True, exist_ok=True)
        for i, svg_html in enumerate(data["svgData"]):
            if len(svg_html) > 50:
                fname = f"icon_{i+1:03d}.svg"
                (icons_dir / fname).write_text(svg_html, encoding="utf-8")
                svg_files.append(str(icons_dir / fname))

    return IconData(
        libraries=libraries,
        svg_count=data["svg_count"],
        svg_files=svg_files,
    )
