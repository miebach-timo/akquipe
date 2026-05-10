from stages.stage1_scraper.models import ScrapedData


def build_hierarchy(data: ScrapedData) -> str:
    all_urls = "\n".join(f"- {url}" for url in data.sitemap.all_urls) or "- nur Startseite"

    return f"""---
title: Page-Hierarchy
type: client-audit-section
domain: {data.domain}
pages_found: {len(data.sitemap.all_urls)}
---

# Seitenhierarchie — {data.domain}

[[_Overview]] · [[User-Flow]] · [[Screenshots]]

---

## Seitenbaum

```
{data.sitemap.tree_text}
```

---

## Alle gecrawlten URLs ({len(data.sitemap.all_urls)})

{all_urls}
"""
