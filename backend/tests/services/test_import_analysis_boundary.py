from pathlib import Path

from app.parser.docx_reader import read_docx_paragraphs
from app.parser.question_splitter import split_sections_and_questions
from app.services.import_service import _analysis_paragraphs, _extract_question_spans_from_draft


def test_analysis_paragraphs_stop_before_next_section_title_for_question_sixteen():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"
    paragraphs = read_docx_paragraphs(str(fixture))
    paper_draft = split_sections_and_questions(paragraphs)
    spans = _extract_question_spans_from_draft(paragraphs, paper_draft)
    flat_questions = [question for section in paper_draft.sections for question in section.questions]
    question_sixteen_index = next(index for index, question in enumerate(flat_questions) if question.question_no == "16")

    analysis_paragraphs = _analysis_paragraphs(spans[question_sixteen_index])

    assert analysis_paragraphs
    assert analysis_paragraphs[-1].text.strip() != "三、解答题：本大题共11小题，共82分．把解答过程写在答题卡相对应的位置上，解答时应写出必要的计算过程、推演步骤或文字说明．作图时用2B铅笔或黑色墨水签字笔．"
    assert all(not paragraph.text.strip().startswith("三、解答题") for paragraph in analysis_paragraphs)
