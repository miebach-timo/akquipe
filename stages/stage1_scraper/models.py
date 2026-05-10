from typing import Optional
from pydantic import BaseModel, Field


class MetaData(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    robots: Optional[str] = None
    canonical: Optional[str] = None
    viewport: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    schema_types: list[str] = Field(default_factory=list)


class CTA(BaseModel):
    text: str
    href: str
    element: str  # "a", "button"


class ContentData(BaseModel):
    h1_count: int = 0
    h1_texts: list[str] = Field(default_factory=list)
    h2_count: int = 0
    h3_count: int = 0
    images_total: int = 0
    images_missing_alt: int = 0
    images_empty_alt: int = 0
    ctas: list[CTA] = Field(default_factory=list)
    word_count: int = 0
    has_impressum: bool = False
    has_privacy: bool = False
    external_scripts: int = 0
    external_stylesheets: int = 0
    lazy_images: int = 0


class ColorEntry(BaseModel):
    hex: str
    rgb: str
    usage: str
    name: Optional[str] = None


class ContrastPair(BaseModel):
    fg: str
    bg: str
    ratio: float
    passes_aa: bool
    passes_aa_large: bool


class ColorData(BaseModel):
    palette: list[ColorEntry] = Field(default_factory=list)
    contrast_pairs: list[ContrastPair] = Field(default_factory=list)
    css_vars: dict[str, str] = Field(default_factory=dict)


class TypographyData(BaseModel):
    families: list[str] = Field(default_factory=list)
    body_size: Optional[str] = None
    line_height: Optional[str] = None
    weights: list[str] = Field(default_factory=list)
    google_fonts: list[str] = Field(default_factory=list)


class IconData(BaseModel):
    libraries: list[str] = Field(default_factory=list)
    svg_count: int = 0
    svg_files: list[str] = Field(default_factory=list)


class SitemapNode(BaseModel):
    url: str
    title: str
    depth: int
    children: list["SitemapNode"] = Field(default_factory=list)

SitemapNode.model_rebuild()


class SitemapData(BaseModel):
    root: Optional[SitemapNode] = None
    tree_text: str = ""
    all_urls: list[str] = Field(default_factory=list)


class ScrapedData(BaseModel):
    url: str
    domain: str
    scraped_at: str
    pages_crawled: int = 0
    meta: MetaData = Field(default_factory=MetaData)
    content: ContentData = Field(default_factory=ContentData)
    colors: ColorData = Field(default_factory=ColorData)
    typography: TypographyData = Field(default_factory=TypographyData)
    icons: IconData = Field(default_factory=IconData)
    sitemap: SitemapData = Field(default_factory=SitemapData)
    screenshots: list[str] = Field(default_factory=list)
