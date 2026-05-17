from pathlib import Path

from fastapi.testclient import TestClient

from app.db.models import ExamPaper, PracticeSession, Question
from app.db.session import get_session
from app.main import app


def test_paper_detail_api_returns_sections_and_questions():
    client = TestClient(app)
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"

    with fixture.open("rb") as f:
        result = client.post(
            "/api/papers/import",
            files={
                "file": (
                    "2025-suzhou-math-exam.docx",
                    f,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
            data={
                "subject": "数学",
                "region": "江苏省苏州市",
                "exam_year": 2025,
                "exam_type": "中考真题",
            },
        ).json()

    paper_id = result["paper"]["paper_id"]
    paper = client.get(f"/api/papers/{paper_id}").json()

    assert paper["paper_id"] == paper_id
    assert len(paper["sections"]) == 3
    first_question = paper["sections"][0]["questions"][0]
    assert first_question["question_no"] == "1"
    assert [option["option_label"] for option in first_question["options"]] == ["A", "B", "C", "D"]
    assert "stem_blocks" in first_question
    assert any(
        block["kind"] == "image"
        for section in paper["sections"]
        for question in section["questions"]
        for block in question["stem_blocks"]
    )


def test_paper_list_api_returns_latest_paper():
    client = TestClient(app)
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"

    with fixture.open("rb") as f:
        client.post(
            "/api/papers/import",
            files={
                "file": (
                    "2025-suzhou-math-exam.docx",
                    f,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
            data={
                "subject": "数学",
                "region": "江苏省苏州市",
                "exam_year": 2025,
                "exam_type": "中考真题",
            },
        )

    papers = client.get("/api/papers").json()
    assert papers[0]["subject"] == "数学"
    assert papers[0]["question_count"] == 27


def test_delete_paper_api_removes_paper_and_associated_rows():
    client = TestClient(app)
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"

    with fixture.open("rb") as f:
        result = client.post(
            "/api/papers/import",
            files={
                "file": (
                    "2025-suzhou-math-exam.docx",
                    f,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
            data={
                "subject": "数学",
                "region": "江苏省苏州市",
                "exam_year": 2025,
                "exam_type": "中考真题",
            },
        ).json()

    paper_id = result["paper"]["paper_id"]
    response = client.delete(f"/api/papers/{paper_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["paper_id"] == paper_id
    assert body["deleted"] is True
    assert body["warnings"] == []

    with get_session() as session:
        assert session.get(ExamPaper, paper_id) is None
        assert session.query(Question).filter(Question.paper_id == paper_id).count() == 0
        assert session.query(PracticeSession).filter(PracticeSession.paper_id == paper_id).count() == 0
