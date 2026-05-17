from dataclasses import dataclass, field


@dataclass(slots=True)
class DocxContentItem:
    kind: str
    text: str | None = None
    asset_ref: str | None = None
    source: str | None = None


@dataclass(slots=True)
class DocxParagraph:
    index: int
    text: str
    raw_xml: str
    has_image: bool = False
    has_table: bool = False
    has_formula: bool = False
    table_rows: list[list[str]] | None = None
    asset_refs: list[str] = field(default_factory=list)
    content_items: list[DocxContentItem] = field(default_factory=list)
