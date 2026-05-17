from __future__ import annotations

import json
import hashlib
import mimetypes
import re
import zipfile
from io import BytesIO
from xml.etree import ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone
from pathlib import PurePosixPath
from uuid import uuid4

from PIL import Image, UnidentifiedImageError
from sqlalchemy import desc, select

from app.db.models import ContentBlock, ExamPaper, MediaAsset, PaperSection, Question, QuestionOption, ParseRun, QuestionTag
from app.db.session import get_session
from app.parser.types import DocxParagraph
from app.parser.docx_reader import read_docx_paragraphs
from app.parser.question_splitter import split_sections_and_questions, _is_section_title
from app.parser.small_image_ocr import recognize_small_numeric_image, recognize_small_text_image
from app.services.tag_service import get_or_create_tag


MEDIA_ROOT = Path(__file__).resolve().parents[2] / "media"
QUESTION_START_RE = re.compile(r"^\s*(\d+)[\.。．、]")
OPTION_START_RE = re.compile(r"^[A-D][\.。．、]")
OPTION_LABEL_RE = re.compile(r"([A-D])[\.。．、]\s*")
STEM_END_PREFIXES = ("答案", "【答案】", "解析", "【解析】", "详解", "【详解】")
ANALYSIS_START_PREFIXES = ("解析", "【解析】", "分析", "【分析】", "详解", "【详解】")
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
BROWSER_FRIENDLY_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}
NUMERIC_OCR_HINTS = ("同比", "环比", "增长", "百分", "比例", "占比", "率", "金额", "数据", "统计")


def calculate_sha256_for_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def calculate_sha256_for_file(file_path: str) -> str:
    return calculate_sha256_for_bytes(Path(file_path).read_bytes())


def find_existing_paper_by_source_sha256(source_file_sha256: str) -> ExamPaper | None:
    with get_session() as session:
        return (
            session.execute(
                select(ExamPaper)
                .where(ExamPaper.source_file_sha256 == source_file_sha256)
                .order_by(desc(ExamPaper.created_at), desc(ExamPaper.id))
            )
            .scalars()
            .first()
        )


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


def _is_browser_friendly_image(file_name: str) -> bool:
    return Path(file_name).suffix.lower() in BROWSER_FRIENDLY_IMAGE_EXTENSIONS


def _write_png_derivative(storage_dir: Path, file_name: str, payload: bytes) -> str | None:
    derivative_name = f"{Path(file_name).stem}.png"
    derivative_path = storage_dir / derivative_name

    try:
        with Image.open(BytesIO(payload)) as image:
            image.convert("RGBA").save(derivative_path, format="PNG")
    except (UnidentifiedImageError, OSError, ValueError):
        return None

    return derivative_name


def _extract_question_spans(paragraphs: list[DocxParagraph]) -> list[list[DocxParagraph]]:
    spans: list[list[DocxParagraph]] = []
    current: list[DocxParagraph] = []
    for paragraph in paragraphs:
        if QUESTION_START_RE.match(paragraph.text.strip()):
            if current:
                spans.append(current)
            current = [paragraph]
            continue
        if current:
            current.append(paragraph)

    if current:
        spans.append(current)
    return spans


def _normalize_for_match(text: str) -> str:
    return re.sub(r"[\s\u200b]+", "", text)


def _matchable_paragraph_text(paragraph: DocxParagraph) -> str:
    visible_parts: list[str] = []
    for item in paragraph.content_items:
        if item.kind != "text":
            continue
        if item.text:
            visible_parts.append(item.text)

    if visible_parts:
        return "".join(visible_parts)

    return paragraph.text


def _extract_question_spans_from_draft(
    paragraphs: list[DocxParagraph],
    paper_draft,
) -> list[list[DocxParagraph]]:
    start_indices: list[int | None] = []
    paragraph_index = 0

    for section in paper_draft.sections:
        for question in section.questions:
            first_line = next((line.strip() for line in question.text_lines if line.strip()), "")
            if not first_line:
                start_indices.append(None)
                continue

            normalized_first_line = _normalize_for_match(first_line)
            start_index = None

            for index in range(paragraph_index, len(paragraphs)):
                paragraph_text = _matchable_paragraph_text(paragraphs[index]).strip()
                if not paragraph_text:
                    continue

                normalized_paragraph = _normalize_for_match(paragraph_text)
                if normalized_paragraph.startswith(normalized_first_line) or normalized_first_line.startswith(normalized_paragraph):
                    start_index = index
                    paragraph_index = index + 1
                    break

            start_indices.append(start_index)

    expanded_spans: list[list[DocxParagraph]] = []
    matched_starts = [index for index in start_indices if index is not None]
    matched_position = 0

    for start_index in start_indices:
        if start_index is None:
            expanded_spans.append([])
            continue

        end_index = matched_starts[matched_position + 1] if matched_position + 1 < len(matched_starts) else len(paragraphs)
        expanded_spans.append([paragraph for paragraph in paragraphs if start_index <= paragraph.index < end_index])
        matched_position += 1

    return expanded_spans


def _stem_paragraphs(question_paragraphs: list[DocxParagraph]) -> list[DocxParagraph]:
    stem_paragraphs: list[DocxParagraph] = []
    for paragraph in question_paragraphs:
        stripped = paragraph.text.strip()
        if stripped and (OPTION_START_RE.match(stripped) or any(stripped.startswith(prefix) for prefix in STEM_END_PREFIXES)):
            break
        stem_paragraphs.append(paragraph)
    return stem_paragraphs


def _option_paragraphs(question_paragraphs: list[DocxParagraph]) -> list[DocxParagraph]:
    option_paragraphs: list[DocxParagraph] = []
    started = False
    for paragraph in question_paragraphs:
        stripped = paragraph.text.strip()
        if not started and stripped and OPTION_START_RE.match(stripped):
            started = True
        if not started:
            continue
        if stripped and any(stripped.startswith(prefix) for prefix in STEM_END_PREFIXES):
            break
        option_paragraphs.append(paragraph)
    return option_paragraphs


def _build_option_blocks(
    session,
    archive: zipfile.ZipFile,
    relationships: dict[str, str],
    paper_id: str,
    question_id: str,
    question_paragraphs: list[DocxParagraph],
) -> dict[str, list[dict]]:
    blocks_by_label: dict[str, list[dict]] = {label: [] for label in "ABCD"}
    current_label: str | None = None
    media_cache: dict[str, dict] = {}

    def append_text(label: str, text: str, source: str | None = None) -> None:
        normalized_text = text.strip()
        if not normalized_text:
            return
        block = {"kind": "text", "text": normalized_text}
        if source:
            block["source"] = source
        blocks_by_label[label].append(block)

    for paragraph in _option_paragraphs(question_paragraphs):
        for item in paragraph.content_items:
            if item.kind == "text":
                text = item.text or ""
                matches = list(OPTION_LABEL_RE.finditer(text))
                if matches:
                    if current_label is not None and matches[0].start() > 0:
                        append_text(current_label, text[: matches[0].start()], item.source)
                    for match_index, match in enumerate(matches):
                        current_label = match.group(1)
                        start = match.end()
                        end = matches[match_index + 1].start() if match_index + 1 < len(matches) else len(text)
                        append_text(current_label, text[start:end], item.source)
                    continue

                if current_label is not None:
                    append_text(current_label, text, item.source)
                continue

            if item.kind == "asset" and item.asset_ref and current_label is not None:
                asset = _store_media_asset(
                    session=session,
                    archive=archive,
                    relationships=relationships,
                    paper_id=paper_id,
                    question_id=question_id,
                    asset_ref=item.asset_ref,
                    media_cache=media_cache,
                )
                block = {"kind": "image", "asset_ref": item.asset_ref}
                if asset is not None:
                    block.update(
                        {
                            "media_asset_id": asset["id"],
                            "url": asset["storage_url"],
                            "file_name": asset["file_name"],
                            "original_file_name": asset["original_file_name"],
                        }
                    )
                blocks_by_label[current_label].append(block)
                session.add(
                    ContentBlock(
                        id=str(uuid4()),
                        owner_type="question",
                        owner_id=question_id,
                        block_type="option_image",
                        order_no=sum(len(blocks) for blocks in blocks_by_label.values()),
                        text_content=None,
                        block_json=json.dumps(block, ensure_ascii=False),
                        created_at=datetime.now(timezone.utc),
                    )
                )

    return blocks_by_label


def _store_media_asset(
    session,
    archive: zipfile.ZipFile,
    relationships: dict[str, str],
    paper_id: str,
    question_id: str,
    asset_ref: str,
    media_cache: dict[str, dict],
) -> dict | None:
    cached = media_cache.get(asset_ref)
    if cached is not None:
        return cached

    target = relationships.get(asset_ref)
    if not target:
        return None

    archive_path = _document_path_for_target(target)
    try:
        payload = archive.read(archive_path)
    except KeyError:
        return None

    file_name = Path(target).name or f"{asset_ref}.bin"
    storage_dir = MEDIA_ROOT / paper_id / question_id
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_path = storage_dir / file_name
    storage_path.write_bytes(payload)

    asset_id = str(uuid4())
    storage_url = f"/media/{paper_id}/{question_id}/{file_name}"
    media_file_name = file_name
    mime_type = mimetypes.guess_type(file_name)[0]
    extra_json: dict[str, str] = {"asset_ref": asset_ref, "original_file_name": file_name}

    if not _is_browser_friendly_image(file_name):
        derivative_name = _write_png_derivative(storage_dir, file_name, payload)
        if derivative_name is not None:
            media_file_name = derivative_name
            storage_url = f"/media/{paper_id}/{question_id}/{derivative_name}"
            mime_type = "image/png"
            extra_json["derivative_file_name"] = derivative_name

    asset = {
        "id": asset_id,
        "file_name": media_file_name,
        "storage_url": storage_url,
        "original_file_name": file_name,
    }
    session.add(
        MediaAsset(
            id=asset_id,
            owner_type="question",
            owner_id=question_id,
            asset_type="stem_image",
            file_name=media_file_name,
            mime_type=mime_type,
            storage_url=storage_url,
            extra_json=json.dumps(extra_json, ensure_ascii=False),
            created_at=datetime.now(timezone.utc),
        )
    )
    media_cache[asset_ref] = asset
    return asset


def _build_stem_blocks(
    session,
    archive: zipfile.ZipFile,
    relationships: dict[str, str],
    paper_id: str,
    question_id: str,
    question_paragraphs: list[DocxParagraph],
) -> list[dict]:
    blocks: list[dict] = []
    media_cache: dict[str, dict] = {}

    for paragraph in _stem_paragraphs(question_paragraphs):
        if paragraph.table_rows:
            table_block = {"kind": "table", "rows": [list(row) for row in paragraph.table_rows]}
            blocks.append(table_block)
            session.add(
                ContentBlock(
                    id=str(uuid4()),
                    owner_type="question",
                    owner_id=question_id,
                    block_type="table",
                    order_no=len(blocks),
                    text_content=paragraph.text or None,
                    block_json=json.dumps(table_block, ensure_ascii=False),
                    created_at=datetime.now(timezone.utc),
                )
            )
            continue

        paragraph_text = paragraph.text or ""
        should_try_numeric_ocr = any(hint in paragraph_text for hint in NUMERIC_OCR_HINTS) and any(
            ch.isdigit() for ch in paragraph_text
        )
        for item in paragraph.content_items:
            if item.kind == "text":
                text = item.text or ""
                if not text:
                    continue
                block = {"kind": "text", "text": text}
                if item.source:
                    block["source"] = item.source
                blocks.append(block)
                session.add(
                    ContentBlock(
                        id=str(uuid4()),
                        owner_type="question",
                        owner_id=question_id,
                        block_type="text",
                        order_no=len(blocks),
                        text_content=text,
                        block_json=json.dumps(block, ensure_ascii=False),
                        created_at=datetime.now(timezone.utc),
                    )
                )
                continue

            if item.kind == "asset" and item.asset_ref:
                asset = _store_media_asset(
                    session=session,
                    archive=archive,
                    relationships=relationships,
                    paper_id=paper_id,
                    question_id=question_id,
                    asset_ref=item.asset_ref,
                    media_cache=media_cache,
                )
                ocr_text = None
                if asset is not None:
                    asset_path = MEDIA_ROOT / paper_id / question_id / asset["file_name"]
                    if should_try_numeric_ocr:
                        ocr_text = recognize_small_numeric_image(asset_path)

                if ocr_text:
                    if blocks and blocks[-1].get("kind") == "text":
                        blocks[-1]["text"] = f"{blocks[-1].get('text', '')}{ocr_text}"
                        continue
                    block = {"kind": "text", "text": ocr_text, "source": "ocr"}
                else:
                    block = {"kind": "image", "asset_ref": item.asset_ref}
                    if asset is not None:
                        block.update(
                            {
                                "media_asset_id": asset["id"],
                                "url": asset["storage_url"],
                                "file_name": asset["file_name"],
                                "original_file_name": asset["original_file_name"],
                            }
                        )
                blocks.append(block)
                session.add(
                    ContentBlock(
                        id=str(uuid4()),
                        owner_type="question",
                        owner_id=question_id,
                        block_type="text" if ocr_text else "image",
                        order_no=len(blocks),
                        text_content=ocr_text,
                        block_json=json.dumps(block, ensure_ascii=False),
                        created_at=datetime.now(timezone.utc),
                    )
                )

    return blocks


def _analysis_paragraphs(question_paragraphs: list[DocxParagraph]) -> list[DocxParagraph]:
    analysis_paragraphs: list[DocxParagraph] = []
    started = False

    for paragraph in question_paragraphs:
        stripped = paragraph.text.strip()
        if not started and stripped and any(stripped.startswith(prefix) for prefix in ANALYSIS_START_PREFIXES):
            started = True

        if started:
            if stripped and _is_section_title(stripped):
                break
            analysis_paragraphs.append(paragraph)

    return analysis_paragraphs


def _build_analysis_blocks(
    session,
    archive: zipfile.ZipFile,
    relationships: dict[str, str],
    paper_id: str,
    question_id: str,
    question_paragraphs: list[DocxParagraph],
) -> list[dict]:
    blocks: list[dict] = []
    media_cache: dict[str, dict] = {}

    def _append_text_block(text: str, source: str | None = None) -> None:
        block = {"kind": "text", "text": text}
        if source:
            block["source"] = source
        blocks.append(block)
        session.add(
            ContentBlock(
                id=str(uuid4()),
                owner_type="question",
                owner_id=question_id,
                block_type="analysis_text",
                order_no=len(blocks),
                text_content=text,
                block_json=json.dumps(block, ensure_ascii=False),
                created_at=datetime.now(timezone.utc),
            )
        )

    for paragraph in _analysis_paragraphs(question_paragraphs):
        stripped = paragraph.text.strip()
        content_items = list(paragraph.content_items)
        for item_index, item in enumerate(content_items):
            if item.kind == "text":
                text = item.text or ""
                if not text:
                    continue
                if stripped.startswith(text) and any(stripped.startswith(prefix) for prefix in ANALYSIS_START_PREFIXES):
                    for prefix in ANALYSIS_START_PREFIXES:
                        if stripped.startswith(prefix) and text.startswith(prefix):
                            text = text[len(prefix) :].lstrip()
                            break
                if not text:
                    continue
                _append_text_block(text, item.source)
                continue

            if item.kind == "asset" and item.asset_ref:
                asset = _store_media_asset(
                    session=session,
                    archive=archive,
                    relationships=relationships,
                    paper_id=paper_id,
                    question_id=question_id,
                    asset_ref=item.asset_ref,
                    media_cache=media_cache,
                )
                block = {"kind": "image", "asset_ref": item.asset_ref}
                if asset is not None:
                    block.update(
                        {
                            "media_asset_id": asset["id"],
                            "url": asset["storage_url"],
                            "file_name": asset["file_name"],
                            "original_file_name": asset["original_file_name"],
                        }
                    )
                    asset_path = MEDIA_ROOT / paper_id / question_id / asset["file_name"]
                    ocr_text = recognize_small_text_image(asset_path)
                    previous_text = ""
                    next_text = ""
                    if item_index > 0 and content_items[item_index - 1].kind == "text":
                        previous_text = content_items[item_index - 1].text or ""
                    if item_index + 1 < len(content_items) and content_items[item_index + 1].kind == "text":
                        next_text = content_items[item_index + 1].text or ""
                    if ocr_text == "-" and previous_text and next_text:
                        previous_tail = previous_text[-1]
                        next_head = next_text[:1]
                        if "\u4e00" <= previous_tail <= "\u9fff" and "\u4e00" <= next_head <= "\u9fff":
                            ocr_text = "的"
                    if ocr_text and any(ch.isalnum() for ch in ocr_text):
                        if blocks and blocks[-1].get("kind") == "text":
                            blocks[-1]["text"] = f"{blocks[-1].get('text', '')}{ocr_text}"
                        else:
                            _append_text_block(ocr_text, "ocr")
                        continue
                blocks.append(block)
                session.add(
                    ContentBlock(
                        id=str(uuid4()),
                        owner_type="question",
                        owner_id=question_id,
                        block_type="analysis_image",
                        order_no=len(blocks),
                        text_content=None,
                        block_json=json.dumps(block, ensure_ascii=False),
                        created_at=datetime.now(timezone.utc),
                    )
                )

    return blocks


def build_paper_title(subject: str, region: str, exam_year: int, exam_type: str) -> str:
    region_part = region.strip()
    subject_part = subject.strip()
    exam_type_part = exam_type.strip()
    if region_part:
        return f"{exam_year}年{region_part}{exam_type_part}{subject_part}试卷"
    return f"{exam_year}年{exam_type_part}{subject_part}试卷"


def _derive_paper_title(paragraphs: list[DocxParagraph], subject: str, region: str, exam_year: int, exam_type: str) -> str:
    for paragraph in paragraphs[:8]:
        title_candidate = paragraph.text.strip()
        if title_candidate and "试卷" in title_candidate:
            return title_candidate

    return build_paper_title(subject, region, exam_year, exam_type)


def import_paper(
    file_path: str,
    source_file_name: str,
    subject: str,
    region: str,
    exam_year: int,
    exam_type: str,
    source_file_sha256: str | None = None,
    ) -> dict:
    source_file_sha256 = source_file_sha256 or calculate_sha256_for_file(file_path)
    paragraphs = read_docx_paragraphs(file_path)
    paper_draft = split_sections_and_questions(paragraphs)
    question_spans = _extract_question_spans_from_draft(paragraphs, paper_draft)

    parse_run_id = str(uuid4())
    paper_id = str(uuid4())
    paper_title = _derive_paper_title(paragraphs, subject, region, exam_year, exam_type)
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(file_path) as archive, get_session() as session:
        relationships = _read_relationship_targets(archive)
        paper = ExamPaper(
            id=paper_id,
            title=paper_title,
            subject=subject,
            region=region,
            exam_year=exam_year,
            exam_type=exam_type,
            source_file_name=source_file_name,
            source_file_path=str(Path(file_path)),
            source_file_sha256=source_file_sha256,
            total_questions=paper_draft.question_count,
            status="parsed",
            meta_json="{}",
            created_at=datetime.now(timezone.utc),
        )
        session.add(paper)
        session.flush()

        parse_run = ParseRun(
            id=parse_run_id,
            paper_id=paper_id,
            source_file_path=str(Path(file_path)),
            parser_version="v1",
            parse_status="parsed",
            total_questions_found=paper_draft.question_count,
            total_errors=0,
            run_meta_json="{}",
            created_at=datetime.now(timezone.utc),
        )
        session.add(parse_run)

        paper_payload = {
            "paper_id": paper_id,
            "title": paper.title,
            "subject": subject,
            "region": region,
            "exam_year": exam_year,
            "exam_type": exam_type,
            "section_count": len(paper_draft.sections),
            "question_count": paper_draft.question_count,
            "sections": [],
        }

        question_counter = 1
        question_span_index = 0
        for section_index, section in enumerate(paper_draft.sections, start=1):
            section_id = str(uuid4())
            section_row = PaperSection(
                id=section_id,
                paper_id=paper_id,
                section_no=section_index,
                title=section.title,
                section_type=section.section_type,
                question_count=len(section.questions),
                order_no=section_index,
                meta_json="{}",
            )
            session.add(section_row)

            section_payload = {
                "id": section_id,
                "section_type": section.section_type,
                "title": section.title,
                "order_no": section_index,
                "questions": [],
            }

            for question in section.questions:
                question_id = str(uuid4())
                question_paragraphs = question_spans[question_span_index] if question_span_index < len(question_spans) else []
                stem_blocks = _build_stem_blocks(
                    session=session,
                    archive=archive,
                    relationships=relationships,
                    paper_id=paper_id,
                    question_id=question_id,
                    question_paragraphs=question_paragraphs,
                )
                stem_json = json.dumps({"stem_blocks": stem_blocks}, ensure_ascii=False)
                option_blocks_by_label = _build_option_blocks(
                    session=session,
                    archive=archive,
                    relationships=relationships,
                    paper_id=paper_id,
                    question_id=question_id,
                    question_paragraphs=question_paragraphs,
                )
                analysis_blocks = _build_analysis_blocks(
                    session=session,
                    archive=archive,
                    relationships=relationships,
                    paper_id=paper_id,
                    question_id=question_id,
                    question_paragraphs=question_paragraphs,
                )
                question_row = Question(
                    id=question_id,
                    paper_id=paper_id,
                    section_id=section_id,
                    question_no=question.question_no,
                    order_no=question_counter,
                    question_type=question.question_type,
                    stem_text=question.stem_text or "\n".join(question.text_lines),
                    stem_json=stem_json,
                    answer_text=question.answer_text or None,
                    answer_json="{}",
                    analysis_text=question.analysis_text or None,
                    analysis_json=json.dumps({"analysis_blocks": analysis_blocks}, ensure_ascii=False),
                    status="parsed",
                    meta_json="{}",
                )
                session.add(question_row)

                for label_index, option in enumerate(question.options or [], start=1):
                    option_blocks = option_blocks_by_label.get(option.option_label, [])
                    option_text = option.option_text
                    if option_blocks:
                        text_parts = [block["text"] for block in option_blocks if block["kind"] == "text" and block.get("text")]
                        if text_parts:
                            option_text = "".join(text_parts)
                    session.add(
                        QuestionOption(
                            id=str(uuid4()),
                            question_id=question_id,
                            option_label=option.option_label,
                            option_text=option_text,
                            option_json=json.dumps({"option_blocks": option_blocks}, ensure_ascii=False),
                            is_correct=False,
                            order_no=label_index,
                        )
                    )

                for tag_payload in question.tags:
                    tag = get_or_create_tag(
                        session,
                        tag_type=tag_payload["tag_type"],
                        name=tag_payload["name"],
                    )
                    session.add(
                        QuestionTag(
                            id=str(uuid4()),
                            question_id=question_id,
                            tag_id=tag.id,
                            source=tag_payload["source"],
                            confidence=tag_payload["confidence"],
                        )
                    )

                section_payload["questions"].append(
                    {
                    "id": question_id,
                    "question_no": question.question_no,
                    "order_no": question_counter,
                    "question_type": question.question_type,
                    "stem_text": question.stem_text or "\n".join(question.text_lines),
                    "stem_blocks": stem_blocks,
                    "answer_text": question.answer_text or None,
                    "analysis_text": question.analysis_text or None,
                    "analysis_blocks": analysis_blocks,
                        "options": [
                            {
                                "option_label": option.option_label,
                                "option_text": option_text,
                                "option_blocks": option_blocks_by_label.get(option.option_label, []),
                            }
                            for option in question.options
                        ],
                        "status": "parsed",
                    }
                )
                question_counter += 1
                question_span_index += 1

            paper_payload["sections"].append(section_payload)

        for tag_payload in paper_draft.tags:
            get_or_create_tag(
                session,
                tag_type=tag_payload["tag_type"],
                name=tag_payload["name"],
            )

        session.commit()

    return {
        "parse_run_id": parse_run_id,
        "status": "parsed",
        "paper": paper_payload,
    }


