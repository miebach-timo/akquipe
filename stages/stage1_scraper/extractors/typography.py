from playwright.async_api import Page
from stages.stage1_scraper.models import TypographyData


async def extract_typography(page: Page) -> TypographyData:
    data = await page.evaluate("""
    () => {
        const families = new Set();
        const weights = new Set();

        // Check Google Fonts links
        const googleFonts = [];
        for (const link of document.querySelectorAll('link[href*="fonts.googleapis.com"]')) {
            googleFonts.push(link.href);
            const match = link.href.match(/family=([^&:]+)/);
            if (match) {
                const family = decodeURIComponent(match[1]).replace(/[+]/g, ' ').split(':')[0];
                families.add(family);
            }
        }

        // Computed styles on key elements
        const bodyStyle = getComputedStyle(document.body);
        const bodySize = bodyStyle.fontSize;
        const lineHeight = bodyStyle.lineHeight;

        const targets = [document.body, ...document.querySelectorAll('h1,h2,h3,p,a,button,li')].slice(0, 50);
        for (const el of targets) {
            const s = getComputedStyle(el);
            const family = s.fontFamily;
            if (family) {
                // Take first font in stack
                const first = family.split(',')[0].trim().replace(/["']/g, '');
                if (first && first !== 'inherit' && first !== 'initial') {
                    families.add(first);
                }
            }
            if (s.fontWeight) weights.add(s.fontWeight);
        }

        return {
            families: [...families].slice(0, 8),
            body_size: bodySize,
            line_height: lineHeight,
            weights: [...weights].sort(),
            google_fonts: googleFonts,
        };
    }
    """)

    return TypographyData(
        families=data["families"],
        body_size=data.get("body_size"),
        line_height=data.get("line_height"),
        weights=data["weights"],
        google_fonts=data["google_fonts"],
    )
