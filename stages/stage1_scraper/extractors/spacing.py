"""Extractor: spacing tokens, border-radius, box-shadows from computed styles."""
from collections import Counter


async def extract_spacing_tokens(page) -> dict:
    result = await page.evaluate("""() => {
        const elements = [...document.querySelectorAll('*')].slice(0, 200);
        const paddings = [], margins = [], gaps = [], radii = [], shadows = [];

        elements.forEach(el => {
            const cs = window.getComputedStyle(el);

            // Padding/Margin — only non-zero
            ['paddingTop','paddingBottom','paddingLeft','paddingRight'].forEach(p => {
                const v = cs[p]; if (v && v !== '0px') paddings.push(v);
            });
            ['marginTop','marginBottom','marginLeft','marginRight'].forEach(p => {
                const v = cs[p]; if (v && v !== '0px') margins.push(v);
            });
            const gap = cs.gap; if (gap && gap !== 'normal' && gap !== '0px') gaps.push(gap);

            // Border radius
            const br = cs.borderRadius; if (br && br !== '0px') radii.push(br);

            // Box shadow
            const bs = cs.boxShadow; if (bs && bs !== 'none') shadows.push(bs);
        });

        function topN(arr, n) {
            const counts = {};
            arr.forEach(v => counts[v] = (counts[v] || 0) + 1);
            return Object.entries(counts)
                .sort((a, b) => b[1] - a[1])
                .slice(0, n)
                .map(e => e[0]);
        }

        return {
            common_paddings: topN(paddings, 8),
            common_margins: topN(margins, 8),
            common_gaps: topN(gaps, 5),
            common_radii: topN(radii, 5),
            common_shadows: topN(shadows, 3),
        };
    }""")

    return result or {}
