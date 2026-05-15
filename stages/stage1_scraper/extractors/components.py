"""Extractor: component inventory — buttons, forms, cards, navigation type, modals."""


async def extract_components(page) -> dict:
    result = await page.evaluate("""() => {
        // Buttons
        const buttonEls = [...document.querySelectorAll('button, a[class*="btn"], a[class*="button"], [role="button"]')];
        const buttons = buttonEls.slice(0, 20).map(el => ({
            text: (el.textContent || '').trim().substring(0, 50),
            tag: el.tagName.toLowerCase(),
            classes: el.className.substring(0, 100),
            type: el.getAttribute('type') || null,
        }));

        // Forms
        const formEls = [...document.querySelectorAll('form')];
        const forms = formEls.slice(0, 5).map(form => {
            const inputs = [...form.querySelectorAll('input, textarea, select')];
            return {
                input_types: [...new Set(inputs.map(i => i.type || i.tagName.toLowerCase()))],
                input_count: inputs.length,
                has_labels: form.querySelectorAll('label').length > 0,
                required_count: form.querySelectorAll('[required]').length,
            };
        });

        // Navigation type detection
        const nav = document.querySelector('nav, [role="navigation"]');
        let navType = 'none';
        let isSticky = false;
        let hasHamburger = false;
        if (nav) {
            const cs = window.getComputedStyle(nav);
            isSticky = cs.position === 'sticky' || cs.position === 'fixed';
            const megaMenu = nav.querySelectorAll('ul ul').length > 2;
            hasHamburger = !!(document.querySelector('[class*="hamburger"], [class*="menu-toggle"], [aria-label*="menu"]'));
            navType = megaMenu ? 'mega-menu' : (isSticky ? 'sticky' : 'standard');
        }

        // Modal/overlay detection
        const hasModal = !!(document.querySelector('[role="dialog"], .modal, [class*="modal"], [class*="overlay"], [class*="popup"]'));

        // Card patterns — repeated structural blocks
        const cardCandidates = [...document.querySelectorAll('[class*="card"], [class*="tile"], [class*="item"]')];
        const hasCards = cardCandidates.length >= 2;

        // Hero section detection
        const hero = document.querySelector('[class*="hero"], [class*="banner"], section:first-of-type, header + *');
        const hasHero = !!hero;

        return {
            buttons,
            forms,
            nav_type: navType,
            nav_is_sticky: isSticky,
            nav_has_hamburger: hasHamburger,
            has_modal: hasModal,
            has_cards: hasCards,
            has_hero: hasHero,
            button_count: buttonEls.length,
            form_count: formEls.length,
        };
    }""")

    return result or {}
