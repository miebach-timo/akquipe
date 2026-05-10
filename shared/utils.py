from datetime import datetime
from urllib.parse import urlparse

from slugify import slugify


def domain_from_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.removeprefix("www.")


def run_id_from_url(url: str) -> str:
    domain = domain_from_url(url)
    slug = slugify(domain, separator="_")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{slug}_{ts}"


def safe_filename(name: str) -> str:
    return slugify(name, separator="_")
