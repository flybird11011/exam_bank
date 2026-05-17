from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_tags_api_lists_auto_and_manual_tags():
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

    tags = client.get("/api/tags", params={"tag_type": "subject"}).json()
    assert any(tag["name"] == "数学" for tag in tags)

    question_id = result["paper"]["sections"][0]["questions"][0]["id"]
    created = client.post(
        f"/api/questions/{question_id}/tags",
        json={"tag_type": "knowledge_point", "name": "实数大小比较", "source": "manual", "confidence": 1.0},
    ).json()
    assert created["name"] == "实数大小比较"

    question_tags = client.get(f"/api/questions/{question_id}/tags").json()
    assert any(tag["name"] == "实数大小比较" for tag in question_tags)

    delete_result = client.delete(f"/api/questions/{question_id}/tags/{created['tag_id']}")
    assert delete_result.status_code == 200
    assert delete_result.json()["status"] == "deleted"
