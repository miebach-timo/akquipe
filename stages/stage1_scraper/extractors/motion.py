"""Extractor: CSS animations, transitions, motion preferences, animation library detection."""


async def extract_motion_tokens(page) -> dict:
    result = await page.evaluate("""() => {
        const elements = [...document.querySelectorAll('*')].slice(0, 200);
        const transitions = new Set(), animations = new Set();

        elements.forEach(el => {
            const cs = window.getComputedStyle(el);
            const tr = cs.transition;
            if (tr && tr !== 'all 0s ease 0s' && tr !== 'none') transitions.add(tr);
            const an = cs.animationName;
            if (an && an !== 'none') animations.add(an);
        });

        // Check for prefers-reduced-motion support
        const sheets = [...document.styleSheets];
        let hasReducedMotion = false;
        try {
            sheets.forEach(sheet => {
                try {
                    const rules = [...sheet.cssRules || []];
                    rules.forEach(rule => {
                        if (rule.conditionText && rule.conditionText.includes('prefers-reduced-motion')) {
                            hasReducedMotion = true;
                        }
                    });
                } catch(e) {}
            });
        } catch(e) {}

        // Detect animation libraries from scripts
        const scripts = [...document.scripts].map(s => s.src);
        const libs = [];
        if (scripts.some(s => s.includes('gsap') || s.includes('TweenMax'))) libs.push('GSAP');
        if (scripts.some(s => s.includes('aos'))) libs.push('AOS');
        if (scripts.some(s => s.includes('scrollreveal'))) libs.push('ScrollReveal');
        if (scripts.some(s => s.includes('lottie'))) libs.push('Lottie');
        if (scripts.some(s => s.includes('framer-motion') || s.includes('framer'))) libs.push('Framer Motion');
        if (scripts.some(s => s.includes('anime'))) libs.push('Anime.js');
        if (typeof AOS !== 'undefined') libs.push('AOS');
        if (typeof gsap !== 'undefined') libs.push('GSAP');

        return {
            transitions: [...transitions].slice(0, 10),
            animation_names: [...animations].slice(0, 10),
            has_reduced_motion_support: hasReducedMotion,
            animation_libraries: [...new Set(libs)],
        };
    }""")

    return result or {}
