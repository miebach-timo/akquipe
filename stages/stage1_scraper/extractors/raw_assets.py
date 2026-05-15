"""Extractor: raw HTML dump, inline styles/scripts, framework detection, external asset URLs."""
from pathlib import Path


async def extract_raw_assets(page, scraped_dir: Path) -> dict:
    html = await page.content()
    (scraped_dir / "page.html").write_text(html, encoding="utf-8")

    result = await page.evaluate("""() => {
        const inlineStyles = [...document.querySelectorAll('style')]
            .map(s => s.textContent || '').join('\\n\\n');
        const inlineScripts = [...document.querySelectorAll('script:not([src])')]
            .map(s => s.textContent || '').filter(t => t.trim().length > 0).join('\\n\\n');

        const externalStylesheets = [...document.querySelectorAll('link[rel="stylesheet"][href]')]
            .map(l => l.href);
        const externalScripts = [...document.querySelectorAll('script[src]')]
            .map(s => s.src);

        // Framework detection
        const frameworks = [];
        if (window.React || document.querySelector('[data-reactroot]')) frameworks.push('React');
        if (window.Vue) frameworks.push('Vue');
        if (window.angular) frameworks.push('Angular');
        if (window.__NEXT_DATA__) frameworks.push('Next.js');
        if (window.nuxt) frameworks.push('Nuxt.js');
        if (window.Astro) frameworks.push('Astro');
        if (window.svelte) frameworks.push('Svelte');
        if (window.wp || window.wpApiSettings) frameworks.push('WordPress');
        if (window.Shopify) frameworks.push('Shopify');

        // CDN detection
        const cdnPatterns = ['jquery', 'bootstrap', 'tailwind', 'fontawesome', 'googleapis', 'cloudflare'];
        const cdnsDetected = cdnPatterns.filter(cdn =>
            externalScripts.some(s => s.includes(cdn)) ||
            externalStylesheets.some(s => s.includes(cdn))
        );

        return {
            inline_styles: inlineStyles,
            inline_scripts: inlineScripts.substring(0, 10000),  // cap to 10KB
            external_stylesheets: externalStylesheets.slice(0, 20),
            external_scripts: externalScripts.slice(0, 20),
            frameworks_detected: frameworks,
            cdns_detected: cdnsDetected,
        };
    }""")

    if result.get("inline_styles"):
        (scraped_dir / "styles_inline.css").write_text(result["inline_styles"], encoding="utf-8")
    if result.get("inline_scripts"):
        (scraped_dir / "scripts_inline.js").write_text(result["inline_scripts"], encoding="utf-8")

    return {
        "external_stylesheets": result.get("external_stylesheets", []),
        "external_scripts": result.get("external_scripts", []),
        "frameworks_detected": result.get("frameworks_detected", []),
        "cdns_detected": result.get("cdns_detected", []),
    }
