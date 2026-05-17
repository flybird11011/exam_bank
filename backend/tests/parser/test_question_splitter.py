from pathlib import Path

from app.parser.docx_reader import read_docx_paragraphs
from app.parser.question_splitter import split_sections_and_questions


def test_split_sample_math_exam_into_three_sections_and_twenty_seven_questions():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"
    paragraphs = read_docx_paragraphs(str(fixture))
    paper = split_sections_and_questions([paragraph.text for paragraph in paragraphs])

    assert [section.section_type for section in paper.sections] == [
        "single_choice",
        "fill_blank",
        "short_answer",
    ]
    assert paper.question_count == 27
    first_question = paper.sections[0].questions[0]
    assert [option.option_label for option in first_question.options] == ["A", "B", "C", "D"]
    assert first_question.options[0].option_text == "5"


def test_split_short_answer_question_does_not_infer_choice_options():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"
    paragraphs = read_docx_paragraphs(str(fixture))
    paper = split_sections_and_questions(paragraphs)

    flat_questions = [question for section in paper.sections for question in section.questions]
    question_twenty_three = next(question for question in flat_questions if question.question_no == "23")

    assert question_twenty_three.question_type == "short_answer"
    assert question_twenty_three.options == []
