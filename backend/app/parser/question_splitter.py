from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.tagging.rules import generate_paper_tags, generate_question_tags


SECTION_PATTERNS: list[tuple[str, str]] = [
    (r"^一、.*选择题", "single_choice"),
    (r"^二、.*填空题", "fill_blank"),
    (r"^三、.*解答题", "short_answer"),
]

QUESTION_START_RE = re.compile(r"^\s*(\d+)[\.．、]")
ANSWER_MARKERS = ("【答案】",)
ANALYSIS_MARKERS = ("【解析】", "【分析】", "【详解】")
OPTION_RE = re.compile(r"([A-D])[\.．、]\s*")


@dataclass(slots=True)
class QuestionOption:
    option_label: str
    option_text: str


@dataclass(slots=True)
class Question:
    question_no: str
    text_lines: list[str] = field(default_factory=list)
    question_type: str = "unknown"
    stem_text: str = ""
    options: list[QuestionOption] = field(default_factory=list)
    answer_text: str = ""
    analysis_text: str = ""
    tags: list[dict] = field(default_factory=list)


@dataclass(slots=True)
class PaperSection:
    section_type: str
    title: str
    questions: list[Question] = field(default_factory=list)


@dataclass(slots=True)
class Paper:
    sections: list[PaperSection] = field(default_factory=list)
    question_count: int = 0
    tags: list[dict] = field(default_factory=list)


def _section_type_for_title(title: str) -> str:
    for pattern, section_type in SECTION_PATTERNS:
        if re.match(pattern, title):
            return section_type
    return "unknown"


def _is_section_title(text: str) -> bool:
    return any(re.match(pattern, text) for pattern, _ in SECTION_PATTERNS)


def _is_question_start(text: str) -> re.Match[str] | None:
    return QUESTION_START_RE.match(text)


def _visible_and_raw_text(item: Any) -> tuple[str, str]:
    if hasattr(item, "table_rows") and getattr(item, "table_rows"):
        return "", ""

    if hasattr(item, "content_items") and hasattr(item, "text"):
        visible_text = str(getattr(item, "text") or "")
        raw_text = "".join(
            str(content_item.text or "")
            for content_item in getattr(item, "content_items", [])
            if getattr(content_item, "kind", None) == "text"
        )
        return visible_text, raw_text or visible_text

    text = str(item)
    return text, text


def split_sections_and_questions(lines: list[Any]) -> Paper:
    paper = Paper()
    current_section: PaperSection | None = None
    current_question: Question | None = None
    visible_lines: list[str] = []

    def finalize_question() -> None:
        nonlocal current_question, current_section, paper
        if current_question is None or current_section is None:
            return
        current_question.question_type = current_section.section_type
        _parse_question_content(current_question)
        current_question.tags = generate_question_tags(
            question_text=current_question.stem_text or "\n".join(current_question.text_lines),
            question_type=current_question.question_type,
        )
        current_section.questions.append(current_question)
        paper.question_count += 1
        current_question = None

    for raw_item in lines:
        line, raw_line = _visible_and_raw_text(raw_item)
        line = line.strip()
        raw_line = raw_line.strip()
        if not line and not raw_line:
            continue
        visible_lines.append(line or raw_line)

        if _is_section_title(line):
            finalize_question()
            if current_section is not None:
                paper.sections.append(current_section)
            current_section = PaperSection(
                section_type=_section_type_for_title(line),
                title=line,
            )
            continue

        match = _is_question_start(line)
        if match and current_section is not None:
            finalize_question()
            current_question = Question(question_no=match.group(1), text_lines=[raw_line or line])
            continue

        if current_question is not None:
            current_question.text_lines.append(raw_line or line)

    finalize_question()
    if current_section is not None:
        paper.sections.append(current_section)

    paper.tags = generate_paper_tags(visible_lines)
    return paper


def _parse_question_content(question: Question) -> None:
    raw_text = "\n".join(question.text_lines)
    answer_index = raw_text.find("【答案】")
    analysis_marker = next((marker for marker in ANALYSIS_MARKERS if raw_text.find(marker) != -1), None)
    analysis_index = raw_text.find(analysis_marker) if analysis_marker is not None else -1

    stem_block = raw_text
    if answer_index != -1:
        stem_block = raw_text[:answer_index]
        question.answer_text = raw_text[answer_index + len("【答案】"):analysis_index if analysis_index != -1 else len(raw_text)].strip()
    if analysis_index != -1:
        question.analysis_text = raw_text[analysis_index + len(analysis_marker or ""):].strip()
    if question.question_type in {"single_choice", "multiple_choice"}:
        question.stem_text, question.options = _extract_stem_and_options(stem_block)
    else:
        question.stem_text = re.sub(r"\s+", " ", stem_block).strip()
        question.options = []


def _extract_stem_and_options(text: str) -> tuple[str, list[QuestionOption]]:
    normalized = re.sub(r"\s+", " ", text).strip()
    matches = list(OPTION_RE.finditer(normalized))
    if not matches:
        return normalized.strip(), []

    stem = normalized[: matches[0].start()].strip()
    options: list[QuestionOption] = []
    for index, match in enumerate(matches):
        label = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        option_text = normalized[start:end].strip()
        if not option_text:
            option_text = "[图像/对象]"
        options.append(QuestionOption(option_label=label, option_text=option_text))

    return stem, options
