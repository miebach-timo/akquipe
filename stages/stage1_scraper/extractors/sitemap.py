from collections import deque
from urllib.parse import urljoin, urlparse

from playwright.async_api import Browser, BrowserContext
from stages.stage1_scraper.models import SitemapData, SitemapNode


def _same_domain(base: str, link: str) -> bool:
    base_parsed = urlparse(base)
    link_parsed = urlparse(link)
    if not link_parsed.scheme:
        return True
    return link_parsed.netloc.removeprefix("www.") == base_parsed.netloc.removeprefix("www.")


def _normalize(url: str, base: str) -> str | None:
    if url.startswith(("mailto:", "tel:", "javascript:", "#")):
        return None
    parsed = urlparse(urljoin(base, url))
    # Remove fragment
    clean = parsed._replace(fragment="").geturl()
    return clean


def _build_tree_text(node: SitemapNode, indent: int = 0) -> str:
    prefix = "  " * indent + ("└─ " if indent > 0 else "")
    lines = [f"{prefix}{node.title or node.url}"]
    for child in node.children:
        lines.append(_build_tree_text(child, indent + 1))
    return "\n".join(lines)


async def extract_sitemap(
    context: BrowserContext,
    start_url: str,
    max_pages: int = 30,
    max_depth: int = 3,
    timeout: int = 15000,
) -> SitemapData:
    visited: dict[str, SitemapNode] = {}
    queue: deque[tuple[str, int, str | None]] = deque()  # (url, depth, parent_url)
    queue.append((start_url, 0, None))

    root_node: SitemapNode | None = None

    while queue and len(visited) < max_pages:
        url, depth, parent_url = queue.popleft()

        if url in visited or depth > max_depth:
            continue

        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            title = await page.title()

            node = SitemapNode(url=url, title=title or url, depth=depth)
            visited[url] = node

            if parent_url and parent_url in visited:
                visited[parent_url].children.append(node)
            elif root_node is None:
                root_node = node

            if depth < max_depth:
                links = await page.evaluate("""
                () => [...document.querySelectorAll('a[href]')]
                    .map(a => a.href)
                    .filter(h => h && !h.startsWith('mailto:') && !h.startsWith('tel:') && !h.startsWith('javascript:'))
                """)
                for link in links:
                    norm = _normalize(link, url)
                    if norm and _same_domain(start_url, norm) and norm not in visited:
                        queue.append((norm, depth + 1, url))

        except Exception:
            pass
        finally:
            await page.close()

    if root_node is None and visited:
        root_node = next(iter(visited.values()))

    tree_text = _build_tree_text(root_node) if root_node else ""

    return SitemapData(
        root=root_node,
        tree_text=tree_text,
        all_urls=list(visited.keys()),
    )
