from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.import_service import import_paper
from app.db.models import QuestionOption
from app.db.models import Question
from app.db.session import get_session


def test_review_api_can_update_question_text_fields():
    client = TestClient(app)

    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"
    imported = import_paper(
        file_path=str(fixture),
        source_file_name="2025-suzhou-math-exam.docx",
        subject="数学",
        region="江苏省苏州市",
        exam_year=2025,
        exam_type="中考真题",
    )
    question_id = imported["paper"]["sections"][0]["questions"][0]["id"]

    response = client.patch(
        f"/api/questions/{question_id}",
        json={
            "status": "confirmed",
            "question_type": "single_choice",
            "stem_text": "修改后的题干",
            "answer_text": "D",
            "analysis_text": "修改后的解析",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"
    assert response.json()["analysis_text"] == "修改后的解析"

    with get_session() as session:
        question = session.get(Question, question_id)
        assert question is not None
        assert question.analysis_text == "修改后的解析"


def test_review_api_can_update_question_options():
    client = TestClient(app)

    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"
    imported = import_paper(
        file_path=str(fixture),
        source_file_name="2025-suzhou-math-exam.docx",
        subject="数学",
        region="江苏省苏州市",
        exam_year=2025,
        exam_type="中考真题",
    )
    question_id = imported["paper"]["sections"][0]["questions"][0]["id"]

    response = client.patch(
        f"/api/questions/{question_id}",
        json={
            "options": [
                {"option_label": "A", "option_text": "10"},
                {"option_label": "B", "option_text": "8"},
                {"option_label": "C", "option_text": "6"},
                {"option_label": "D", "option_text": "4"},
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["options"][0]["option_text"] == "10"

    with get_session() as session:
        options = session.query(QuestionOption).filter(QuestionOption.question_id == question_id).order_by(QuestionOption.order_no).all()
        assert [option.option_text for option in options] == ["10", "8", "6", "4"]
