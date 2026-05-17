from app.parser.docx_reader import read_docx_paragraphs
from app.services.import_service import import_paper


def test_sample_paper_import_uses_docx_title():
    fixture = "C:/Users/Admin/Documents/Codex/Exam/backend/tests/fixtures/2025-suzhou-math-exam.docx"
    paragraphs = read_docx_paragraphs(fixture)

    result = import_paper(
        fixture,
        source_file_name="2025-suzhou-math-exam.docx",
        subject="鏁板",
        region="姹熻嫃鐪佽嫃宸炲競",
        exam_year=2025,
        exam_type="涓€冪湡棰?",
    )

    assert result["paper"]["title"] == paragraphs[0].text
    assert result["paper"]["section_count"] == 3
    assert result["paper"]["question_count"] == 27
