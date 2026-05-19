from pathlib import Path

from app.parser.docx_reader import read_docx_paragraphs
from app.parser.types import DocxContentItem, DocxParagraph
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


def test_split_sections_and_questions_ignores_table_option_labels():
    paragraphs = [
        DocxParagraph(
            index=0,
            text="一、选择题（本题共1小题）",
            raw_xml="<w:p/>",
        ),
        DocxParagraph(
            index=1,
            text="4. 如图所示是苏州园林中的景象，由光的折射形成的是（ ）",
            raw_xml="<w:p/>",
        ),
        DocxParagraph(
            index=2,
            text="A. 图 A\tB. 图 B\tC. 图 C\tD. 图 D",
            raw_xml="<w:tbl/>",
            has_table=True,
            table_rows=[["A. 图 A", "B. 图 B", "C. 图 C", "D. 图 D"]],
            content_items=[DocxContentItem(kind="text", text="A. 图 A\tB. 图 B\tC. 图 C\tD. 图 D")],
        ),
        DocxParagraph(
            index=3,
            text="A. 亭台在水中的“倒影”A\tB. 碧水中变浅的“池底”B\tC. 漏窗在墙壁上的“影子”C\tD. 夕阳下水中的“太阳”D",
            raw_xml="<w:p/>",
            content_items=[
                DocxContentItem(kind="text", text="A. 亭台在水中的“倒影”A\tB. 碧水中变浅的“池底”B\tC. 漏窗在墙壁上的“影子”C\tD. 夕阳下水中的“太阳”D")
            ],
        ),
    ]

    paper = split_sections_and_questions(paragraphs)

    question = paper.sections[0].questions[0]
    assert [option.option_label for option in question.options] == ["A", "B", "C", "D"]
    assert [option.option_text for option in question.options] == [
        "亭台在水中的“倒影”A",
        "碧水中变浅的“池底”B",
        "漏窗在墙壁上的“影子”C",
        "夕阳下水中的“太阳”D",
    ]
