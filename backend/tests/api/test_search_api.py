from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_search_api_returns_imported_paper():
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

    response = client.get("/api/questions/search", params={"subject": "数学", "exam_year": 2025})

    assert response.status_code == 200
    assert response.json()["total"] >= 1
