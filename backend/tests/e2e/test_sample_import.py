from app.services.import_service import build_paper_title, import_paper


def test_sample_paper_import_uses_structured_title_first():
    fixture = "C:/Users/Admin/Documents/Codex/Exam/backend/tests/fixtures/2025-suzhou-math-exam.docx"

    result = import_paper(
        fixture,
        source_file_name="2025-suzhou-math-exam.docx",
        subject="physics",
        region="Suzhou",
        exam_year=2025,
        exam_type="midterm",
    )

    assert result["paper"]["title"] == build_paper_title("physics", "Suzhou", 2025, "midterm")
    assert result["paper"]["section_count"] == 3
    assert result["paper"]["question_count"] == 27
