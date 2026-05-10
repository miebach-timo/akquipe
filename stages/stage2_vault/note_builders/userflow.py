from stages.stage1_scraper.models import ScrapedData, SitemapNode


def _node_to_mermaid(node: SitemapNode, parent_id: str | None, lines: list[str], ids: dict[str, str]) -> None:
    safe_url = node.url.replace("https://", "").replace("http://", "").replace("/", "_").replace(".", "_").replace("-", "_")[:30]
    node_id = f"n{len(ids)}"
    ids[node.url] = node_id
    label = node.title[:25] if node.title else safe_url
    lines.append(f'  {node_id}["{label}"]')
    if parent_id:
        lines.append(f"  {parent_id} --> {node_id}")
    for child in node.children[:6]:
        _node_to_mermaid(child, node_id, lines, ids)


def build_userflow(data: ScrapedData) -> str:
    mermaid_lines: list[str] = []
    ids: dict[str, str] = {}

    if data.sitemap.root:
        _node_to_mermaid(data.sitemap.root, None, mermaid_lines, ids)

    if not mermaid_lines:
        mermaid_lines = ['  A["Startseite"]']

    # Add CTAs as flow arrows
    cta_lines = []
    root_id = list(ids.values())[0] if ids else "A"
    for cta in data.content.ctas[:5]:
        if cta.href and cta.href in ids:
            target_id = ids[cta.href]
            cta_lines.append(f'  {root_id} -->|"{cta.text[:20]}"| {target_id}')

    mermaid_content = "\n".join(mermaid_lines + cta_lines)

    return f"""---
title: User-Flow
type: client-audit-section
domain: {data.domain}
---

# User Flow — {data.domain}

[[_Overview]] · [[Page-Hierarchy]] · [[Screenshots]]

---

## Navigationsfluss

```mermaid
graph TD
{mermaid_content}
```

---

## Erkannte CTAs (Handlungsaufforderungen)

| Text | Ziel |
|---|---|
{"".join(f"| {c.text} | {c.href} |\n" for c in data.content.ctas[:10])}

---

## UX-Hinweise

> Jede Seite sollte einen klaren primären CTA haben.
> CTAs wie "Klicken Sie hier" oder "Mehr erfahren" sind nicht aussagekräftig (WCAG 2.4.6).
"""
