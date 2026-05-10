import re
from playwright.async_api import Page
from stages.stage1_scraper.models import ContentData, CTA


async def extract_content(page: Page) -> ContentData:
    data = await page.evaluate("""
    () => {
        const h1s = [...document.querySelectorAll('h1')];
        const h2s = [...document.querySelectorAll('h2')];
        const h3s = [...document.querySelectorAll('h3')];
        const imgs = [...document.querySelectorAll('img')];

        const ctas = [];
        const seen = new Set();
        for (const el of document.querySelectorAll('a[href], button')) {
            const text = el.textContent.trim().replace(/\\s+/g, ' ');
            const href = el.href || '';
            if (text && text.length < 60 && !seen.has(text)) {
                const style = getComputedStyle(el);
                const isBtn = el.tagName === 'BUTTON' ||
                    style.display === 'inline-block' ||
                    el.classList.toString().match(/btn|button|cta|action/i);
                if (isBtn || (href && !href.includes('#') && text.length < 30)) {
                    ctas.push({ text, href, element: el.tagName.toLowerCase() });
                    seen.add(text);
                }
            }
        }

        const bodyText = document.body?.innerText || '';
        const wordCount = bodyText.trim().split(/\\s+/).filter(w => w.length > 0).length;

        const allLinks = [...document.querySelectorAll('a[href]')].map(a => a.textContent.trim().toLowerCase() + '|' + (a.href || '').toLowerCase());
        const hasImpressum = allLinks.some(l => l.includes('impressum') || l.includes('imprint') || l.includes('legal'));
        const hasPrivacy = allLinks.some(l => l.includes('datenschutz') || l.includes('privacy') || l.includes('dsgvo'));

        const scripts = [...document.querySelectorAll('script[src]')].filter(s => !s.src.includes(location.hostname));
        const styles = [...document.querySelectorAll('link[rel=stylesheet]')].filter(l => !l.href.includes(location.hostname));
        const lazyImgs = [...document.querySelectorAll('img[loading=lazy]')];

        return {
            h1_count: h1s.length,
            h1_texts: h1s.map(h => h.textContent.trim().replace(/\\s+/g, ' ')).filter(t => t),
            h2_count: h2s.length,
            h3_count: h3s.length,
            images_total: imgs.length,
            images_missing_alt: imgs.filter(i => !i.hasAttribute('alt')).length,
            images_empty_alt: imgs.filter(i => i.hasAttribute('alt') && i.alt === '').length,
            ctas: ctas.slice(0, 20),
            word_count: wordCount,
            has_impressum: hasImpressum,
            has_privacy: hasPrivacy,
            external_scripts: scripts.length,
            external_stylesheets: styles.length,
            lazy_images: lazyImgs.length,
        };
    }
    """)

    return ContentData(
        h1_count=data["h1_count"],
        h1_texts=data["h1_texts"],
        h2_count=data["h2_count"],
        h3_count=data["h3_count"],
        images_total=data["images_total"],
        images_missing_alt=data["images_missing_alt"],
        images_empty_alt=data["images_empty_alt"],
        ctas=[CTA(**c) for c in data["ctas"]],
        word_count=data["word_count"],
        has_impressum=data["has_impressum"],
        has_privacy=data["has_privacy"],
        external_scripts=data["external_scripts"],
        external_stylesheets=data["external_stylesheets"],
        lazy_images=data["lazy_images"],
    )


async def extract_meta(page: Page):
    """Returns raw dict for MetaData."""
    return await page.evaluate("""
    () => {
        const g = (sel) => document.querySelector(sel)?.content || null;
        const schemaScripts = [...document.querySelectorAll('script[type="application/ld+json"]')];
        const schemaTypes = [];
        for (const s of schemaScripts) {
            try {
                const obj = JSON.parse(s.textContent);
                if (obj['@type']) schemaTypes.push(obj['@type']);
            } catch(e) {}
        }
        return {
            title: document.title || null,
            description: g('meta[name="description"]'),
            robots: g('meta[name="robots"]'),
            canonical: document.querySelector('link[rel="canonical"]')?.href || null,
            viewport: g('meta[name="viewport"]'),
            og_title: g('meta[property="og:title"]'),
            og_description: g('meta[property="og:description"]'),
            og_image: g('meta[property="og:image"]'),
            schema_types: schemaTypes,
        };
    }
    """)
