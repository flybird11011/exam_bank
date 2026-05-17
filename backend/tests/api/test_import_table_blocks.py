from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_import_exposes_table_blocks_for_question_seven():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"

    with TestClient(app) as client:
        with fixture.open("rb") as f:
            response = client.post(
                "/api/papers/import",
                files={
                    "file": (
                        "2025-suzhou-math-exam.docx",
                        f,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
                data={
                    "subject": "math",
                    "region": "suzhou",
                    "exam_year": 2025,
                    "exam_type": "exam",
                },
            )
        paper_id = response.json()["paper"]["paper_id"]
        detail = client.get(f"/api/papers/{paper_id}").json()

    seventh_question = detail["sections"][0]["questions"][6]
    stem_blocks = seventh_question["stem_blocks"]

    table_block = next(block for block in stem_blocks if block["kind"] == "table")
    assert table_block["rows"] == [["温度t(°C)", "−10", "0", "10", "30"], ["声音传播的速度v(m/s)", "324", "330", "336", "348"]]
