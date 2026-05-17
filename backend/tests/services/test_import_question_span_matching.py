from pathlib import Path

from app.parser.docx_reader import read_docx_paragraphs
from app.parser.question_splitter import split_sections_and_questions
from app.services.import_service import _extract_question_spans_from_draft


def test_extract_question_spans_keeps_formula_rich_question_seven():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"
    paragraphs = read_docx_paragraphs(str(fixture))
    paper_draft = split_sections_and_questions(paragraphs)

    spans = _extract_question_spans_from_draft(paragraphs, paper_draft)
    flat_questions = [question for section in paper_draft.sections for question in section.questions]
    question_seven_index = next(index for index, question in enumerate(flat_questions) if question.question_no == "7")

    question_seven_span = spans[question_seven_index]

    assert question_seven_span, "question 7 should still map to its original paragraph span"
    assert question_seven_span[0].index == 71
    assert question_seven_span[-1].index >= 74
