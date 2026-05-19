from __future__ import annotations

import re
import zipfile
from pathlib import Path
from pathlib import PurePosixPath
from html import unescape
from xml.etree import ElementTree as ET

from app.parser.normalize import normalize_paragraphs
from app.parser.mathtype import extract_mathtype_equation_text
from app.parser.types import DocxContentItem, DocxParagraph


WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
R_EMBED = f"{{{OFFICE_REL_NS}}}embed"
R_ID = f"{{{OFFICE_REL_NS}}}id"
OPTION_PREFIX_RE = re.compile(r"^\s*[A-D][\.。．、]\s*")


def _extract_text(paragraph_xml: str) -> str:
    texts = [unescape(match.group(1)) for match in re.finditer(r"<w:t[^>]*>([\s\S]*?)</w:t>", paragraph_xml)]
    return "".join(texts)


def _extract_paragraph_text(paragraph: ET.Element) -> str:
    text_parts: list[str] = []
    for node in paragraph.iter():
        if node is paragraph:
            continue
        if node.tag.endswith("}t"):
            if node.text:
                text_parts.append(node.text)
        elif node.tag.endswith("}tab"):
            text_parts.append("\t")
        elif node.tag.endswith("}br") or node.tag.endswith("}cr"):
            text_parts.append("\n")
    return "".join(text_parts)


def _read_relationship_targets(archive: zipfile.ZipFile) -> dict[str, str]:
    try:
        rels_xml = archive.read("word/_rels/document.xml.rels").decode("utf-8", errors="ignore")
    except KeyError:
        return {}

    rel_root = ET.fromstring(rels_xml)
    relationships: dict[str, str] = {}
    for relationship in rel_root.findall(f".//{{{REL_NS}}}Relationship"):
        rel_id = relationship.get("Id")
        target = relationship.get("Target")
        if rel_id and target:
            relationships[rel_id] = target
    return relationships


def _document_path_for_target(target: str) -> str:
    normalized = target.lstrip("/")
    if normalized.startswith("word/"):
        return normalized
    return str(PurePosixPath("word") / normalized)


def _asset_ref_for_node(node: ET.Element, relationships: dict[str, str]) -> str | None:
    tag = node.tag
    if tag.endswith("}blip"):
        ref = node.get(R_EMBED)
    elif tag.endswith("}imagedata"):
        ref = node.get(R_ID)
    else:
        return None

    if ref and ref in relationships:
        return ref
    return None


def _extract_mathtype_formula_items(
    archive: zipfile.ZipFile,
    paragraph: ET.Element,
    relationships: dict[str, str],
) -> tuple[dict[str, str], dict[str, str], set[str]]:
    formula_text_by_ref: dict[str, str] = {}
    preview_image_ref_by_formula_ref: dict[str, str] = {}
    preview_image_refs: set[str] = set()

    for object_node in paragraph.iter():
        if not object_node.tag.endswith("}object"):
            continue

        ole_node = next((child for child in object_node.iter() if child.tag.endswith("}OLEObject")), None)
        if ole_node is None or ole_node.get("ProgID") != "Equation.DSMT4":
            continue

        ole_ref = ole_node.get(R_ID)
        if not ole_ref:
            continue

        target = relationships.get(ole_ref)
        if not target:
            continue

        archive_path = _document_path_for_target(target)
        try:
            ole_bytes = archive.read(archive_path)
        except KeyError:
            continue

        formula_text = extract_mathtype_equation_text(ole_bytes)
        if not formula_text:
            continue

        formula_text_by_ref[ole_ref] = formula_text

        image_node = next((child for child in object_node.iter() if child.tag.endswith("}imagedata")), None)
        image_ref = image_node.get(R_ID) if image_node is not None else None
        if image_ref:
            preview_image_ref_by_formula_ref[ole_ref] = image_ref
            preview_image_refs.add(image_ref)

    return formula_text_by_ref, preview_image_ref_by_formula_ref, preview_image_refs


def _formula_text_is_weak(text: str) -> bool:
    normalized = re.sub(r"\s+", "", text)
    if not normalized:
        return True
    if "/(=)" in normalized or normalized.endswith("/(=)"):
        return True
    if any(mark in normalized for mark in ("′", "’", "'", "″")):
        return False
    if normalized.isalpha():
        return False
    if any(ch.isdigit() for ch in normalized):
        return False
    if any(ch in normalized for ch in "+-×÷/^"):
        return False
    if not any(ch.isascii() and ch.isalnum() for ch in normalized):
        return False
    return len(normalized) <= 2


def _should_use_formula_preview_image(formula_text: str, paragraph_text: str, allow_preview_fallback: bool) -> bool:
    if not allow_preview_fallback:
        return False

    normalized = re.sub(r"\s+", "", formula_text)
    if not normalized:
        return False

    if normalized.startswith("⊙") and len(normalized) <= 3:
        return False

    return False

    has_inline_option_context = "\t" in paragraph_text or any(label in paragraph_text for label in ("B.", "C.", "D.", "B．", "C．", "D．", "B。", "C。", "D。", "B、", "C、", "D、"))

    if OPTION_PREFIX_RE.match(paragraph_text) and has_inline_option_context and len(normalized) <= 4 and not any(
        ch.isdigit() for ch in normalized
    ):
        return True

    return _formula_text_is_weak(normalized)


def _extract_content_items(
    archive: zipfile.ZipFile,
    element: ET.Element,
    relationships: dict[str, str],
    *,
    allow_preview_fallback: bool = True,
) -> tuple[list[DocxContentItem], list[str]]:
    content_items: list[DocxContentItem] = []
    asset_refs: list[str] = []
    text_buffer: list[str] = []
    paragraph_text = _extract_paragraph_text(element)
    formula_text_by_ref, preview_image_ref_by_formula_ref, preview_image_refs = _extract_mathtype_formula_items(
        archive, element, relationships
    )

    def flush_text() -> None:
        if text_buffer:
            text = "".join(text_buffer)
            if text:
                content_items.append(DocxContentItem(kind="text", text=text))
            text_buffer.clear()

    for node in element.iter():
        if node is element:
            continue

        if node.tag.endswith("}t"):
            if node.text:
                text_buffer.append(node.text)
            continue

        if node.tag.endswith("}tab"):
            text_buffer.append("\t")
            continue

        if node.tag.endswith("}br") or node.tag.endswith("}cr"):
            text_buffer.append("\n")
            continue

        if node.tag.endswith("}OLEObject") and node.get("ProgID") == "Equation.DSMT4":
            ref = node.get(R_ID)
            if ref and ref in formula_text_by_ref:
                formula_text = formula_text_by_ref[ref]
                flush_text()
                content_items.append(DocxContentItem(kind="text", text=formula_text, source="formula"))
            continue

        if node.tag.endswith("}imagedata"):
            ref = node.get(R_ID)
            if ref in preview_image_refs:
                continue

        ref = _asset_ref_for_node(node, relationships)
        if ref:
            flush_text()
            content_items.append(DocxContentItem(kind="asset", asset_ref=ref))
            asset_refs.append(ref)

    flush_text()
    return content_items, asset_refs


def _extract_element_text(
    archive: zipfile.ZipFile,
    element: ET.Element,
    relationships: dict[str, str],
) -> str:
    content_items, _ = _extract_content_items(archive, element, relationships)
    return "".join(item.text or "" for item in content_items if item.kind == "text")


def _has_asset_markers(paragraph: ET.Element, paragraph_xml: str) -> tuple[bool, bool, bool]:
    has_image = any(
        node.tag.endswith("}drawing")
        or node.tag.endswith("}pict")
        or node.tag.endswith("}OLEObject")
        or node.tag.endswith("}inline")
        or node.tag.endswith("}anchor")
        for node in paragraph.iter()
    )
    has_table = any(node.tag.endswith("}tbl") for node in paragraph.iter())
    has_formula = any(node.tag.endswith("}oMath") or node.tag.endswith("}oMathPara") for node in paragraph.iter())
    if not has_formula:
        has_formula = "Equation.DSMT4" in paragraph_xml
    return has_image, has_table, has_formula


def _extract_table_cell_content(
    archive: zipfile.ZipFile,
    cell: ET.Element,
    relationships: dict[str, str],
) -> list[DocxContentItem]:
    cell_content: list[DocxContentItem] = []
    for paragraph in cell.findall("./w:p", WORD_NS):
        content_items, _ = _extract_content_items(archive, paragraph, relationships, allow_preview_fallback=False)
        cell_content.extend(content_items)
    return cell_content


def _extract_table_rows(
    archive: zipfile.ZipFile,
    table: ET.Element,
    relationships: dict[str, str],
) -> tuple[list[list[str]], list[list[list[DocxContentItem]]]]:
    rows: list[list[str]] = []
    table_cells: list[list[list[DocxContentItem]]] = []
    for row in table.findall(".//w:tr", WORD_NS):
        row_text_cells: list[str] = []
        row_cells: list[list[DocxContentItem]] = []
        for cell in row.findall("./w:tc", WORD_NS):
            cell_content = _extract_table_cell_content(archive, cell, relationships)
            row_cells.append(cell_content)
            cell_text_parts = [item.text or "" for item in cell_content if item.kind == "text"]
            row_text_cells.append("\n".join(part for part in cell_text_parts if part))
        if row_text_cells:
            rows.append(row_text_cells)
            table_cells.append(row_cells)
    return rows, table_cells


def _flatten_table_rows(rows: list[list[str]]) -> str:
    return "\n".join("\t".join(cell for cell in row) for row in rows)


def _iter_document_blocks(node: ET.Element):
    for child in list(node):
        if child.tag.endswith("}p"):
            yield "paragraph", child
        elif child.tag.endswith("}tbl"):
            yield "table", child
        else:
            yield from _iter_document_blocks(child)


def read_docx_paragraphs(docx_path: str) -> list[DocxParagraph]:
    path = Path(docx_path)
    if not path.exists():
        raise FileNotFoundError(path)

    with zipfile.ZipFile(path) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
        relationships = _read_relationship_targets(archive)

        raw_paragraphs = []
        root = ET.fromstring(document_xml)
        body = root.find("w:body", WORD_NS)
        if body is None:
            return []

        for index, (kind, node) in enumerate(_iter_document_blocks(body), start=0):
            paragraph_xml = ET.tostring(node, encoding="unicode")
            if kind == "table":
                table_rows, table_cells = _extract_table_rows(archive, node, relationships)
                text = _flatten_table_rows(table_rows)
                content_items = [DocxContentItem(kind="text", text=text)] if text else []
                asset_refs: list[str] = []
                has_image, has_table, has_formula = _has_asset_markers(node, paragraph_xml)
                raw_paragraphs.append(
                    DocxParagraph(
                        index=index,
                        text=text,
                        raw_xml=paragraph_xml,
                        has_image=has_image,
                        has_table=True,
                        has_formula=has_formula,
                        table_rows=table_rows,
                        table_cells=table_cells,
                        asset_refs=asset_refs,
                        content_items=content_items,
                    )
                )
                continue

            paragraph = node
            text = _extract_paragraph_text(paragraph)
            if not text:
                text = _extract_text(paragraph_xml)
            has_image, has_table, has_formula = _has_asset_markers(paragraph, paragraph_xml)
            content_items, asset_refs = _extract_content_items(archive, paragraph, relationships)
            raw_paragraphs.append(
                DocxParagraph(
                    index=index,
                    text=text,
                    raw_xml=paragraph_xml,
                    has_image=has_image,
                    has_table=has_table,
                    has_formula=has_formula,
                    table_rows=None,
                    table_cells=None,
                    asset_refs=asset_refs,
                    content_items=content_items,
                )
            )

        return normalize_paragraphs(raw_paragraphs)
