from app.services.import_service import import_paper
from app.services.search_service import search_questions


def test_sample_import_can_be_found_by_search():
    import_paper(
        "C:/Users/Admin/Documents/Codex/Exam/backend/tests/fixtures/2025-suzhou-math-exam.docx",
        source_file_name="2025-suzhou-math-exam.docx",
        subject="数学",
        region="江苏省苏州市",
        exam_year=2025,
        exam_type="中考真题",
    )

    result = search_questions(subject="数学", exam_year=2025)

    assert result["total"] == 27
