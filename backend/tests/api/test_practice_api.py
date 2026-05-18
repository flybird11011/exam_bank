from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.db.models import ExamPaper, Question, QuestionOption, QuestionTag, Tag
from app.db.session import get_session


def _seed_practice_paper(
    *,
    single_choice_total: int = 8,
    fill_blank_total: int = 8,
    short_answer_total: int = 11,
) -> dict[str, str]:
    paper_id = "paper-practice-1"
    question_ids: dict[str, str] = {}

    with get_session() as session:
        session.add(
            ExamPaper(
                id=paper_id,
                title="练习试卷",
                subject="math",
                region="suzhou",
                exam_year=2025,
                exam_type="exam",
                source_file_name="practice.docx",
                source_file_path="practice.docx",
                status="parsed",
                meta_json="{}",
                created_at=datetime.now(timezone.utc),
            )
        )

        question_counter = 1
        for question_type, total in (
            ("single_choice", single_choice_total),
            ("fill_blank", fill_blank_total),
            ("short_answer", short_answer_total),
        ):
            for index in range(1, total + 1):
                question_id = f"{question_type}-{index}"
                question_ids[f"{question_type}_{index}"] = question_id
                session.add(
                    Question(
                        id=question_id,
                        paper_id=paper_id,
                        section_id=None,
                        question_no=str(question_counter),
                        order_no=question_counter,
                        question_type=question_type,
                        stem_text=f"{question_type} question {index}",
                        stem_json="{}",
                        answer_text=f"answer-{index}",
                        answer_json="{}",
                        analysis_text=f"analysis-{index}",
                        analysis_json="{}",
                        status="parsed",
                        meta_json="{}",
                        created_at=datetime.now(timezone.utc),
                    )
                )
                question_counter += 1

        session.commit()

    question_ids["paper_id"] = paper_id
    return question_ids


def _seed_two_practice_papers_for_all_scope() -> dict[str, str]:
    question_ids: dict[str, str] = {}

    with get_session() as session:
        for paper_id, title, question_no, question_id in (
            ("paper-all-1", "练习试卷一", "1", "paper-all-1-single"),
            ("paper-all-2", "练习试卷二", "2", "paper-all-2-single"),
        ):
            session.add(
                ExamPaper(
                    id=paper_id,
                    title=title,
                    subject="math",
                    region="suzhou",
                    exam_year=2025,
                    exam_type="exam",
                    source_file_name=f"{paper_id}.docx",
                    source_file_path=f"{paper_id}.docx",
                    status="parsed",
                    meta_json="{}",
                    created_at=datetime.now(timezone.utc),
                )
            )
            session.add(
                Question(
                    id=question_id,
                    paper_id=paper_id,
                    section_id=None,
                    question_no=question_no,
                    order_no=int(question_no),
                    question_type="single_choice",
                    stem_text=f"{title} 选择题",
                    stem_json="{}",
                    answer_text="A",
                    answer_json="{}",
                    analysis_text="analysis",
                    analysis_json="{}",
                    status="parsed",
                    meta_json="{}",
                    created_at=datetime.now(timezone.utc),
                )
            )
            question_ids[paper_id] = paper_id
            question_ids[f"{paper_id}_question"] = question_id

        session.commit()

    return question_ids


def test_practice_session_defaults_to_8_8_11_and_returns_matching_questions():
    client = TestClient(app)
    seeded = _seed_practice_paper()

    response = client.post("/api/practice/sessions", json={"paper_id": seeded["paper_id"]})

    assert response.status_code == 200
    body = response.json()
    assert body["session"]["single_choice_count"] == 8
    assert body["session"]["fill_blank_count"] == 8
    assert body["session"]["short_answer_count"] == 11
    assert len(body["questions"]) == 27
    assert [question["question_type"] for question in body["questions"][:8]] == ["single_choice"] * 8
    assert [question["question_type"] for question in body["questions"][8:16]] == ["fill_blank"] * 8
    assert [question["question_type"] for question in body["questions"][16:]] == ["short_answer"] * 11


def test_practice_session_exposes_content_blocks_for_rich_question_rendering():
    client = TestClient(app)
    seeded = _seed_practice_paper(single_choice_total=1, fill_blank_total=0, short_answer_total=0)

    with get_session() as session:
        question = session.get(Question, seeded["single_choice_1"])
        assert question is not None
        question.stem_json = json.dumps(
            {
                "stem_blocks": [
                    {"kind": "text", "text": "已知"},
                    {"kind": "image", "url": "/media/stem.png", "original_file_name": "stem.png"},
                ]
            },
            ensure_ascii=False,
        )
        question.analysis_json = json.dumps(
            {
                "analysis_blocks": [
                    {"kind": "text", "text": "答案"},
                    {"kind": "table", "rows": [["a", "b"], ["1", "2"]]},
                ]
            },
            ensure_ascii=False,
        )
        question.answer_json = json.dumps(
            {
                "option_blocks": [
                    {"kind": "text", "text": "1/2", "source": "formula"},
                ]
            },
            ensure_ascii=False,
        )
        session.add(
            QuestionOption(
                id="option-1",
                question_id=question.id,
                option_label="A",
                option_text="A",
                option_json=json.dumps(
                    {
                        "option_blocks": [
                            {"kind": "text", "text": "1/2", "source": "formula"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                is_correct=False,
                order_no=1,
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

    response = client.post(
        "/api/practice/sessions",
        json={"paper_id": seeded["paper_id"], "single_choice_count": 1, "fill_blank_count": 0, "short_answer_count": 0},
    )

    assert response.status_code == 200
    body = response.json()
    question = body["questions"][0]
    assert question["stem_blocks"][0]["text"] == "已知"
    assert question["stem_blocks"][1]["kind"] == "image"
    assert question["analysis_blocks"][1]["kind"] == "table"
    assert question["options"][0]["option_blocks"][0]["source"] == "formula"


def test_practice_session_exposes_blocks_for_question_detail():
    client = TestClient(app)
    seeded = _seed_practice_paper(single_choice_total=1, fill_blank_total=0, short_answer_total=0)

    with get_session() as session:
        question = session.get(Question, seeded["single_choice_1"])
        assert question is not None
        question.stem_json = json.dumps(
            {
                "stem_blocks": [
                    {"kind": "text", "text": "detail-stem"},
                ]
            },
            ensure_ascii=False,
        )
        question.analysis_json = json.dumps(
            {
                "analysis_blocks": [
                    {"kind": "text", "text": "detail-analysis"},
                ]
            },
            ensure_ascii=False,
        )
        session.commit()

    response = client.get(f"/api/practice/questions/{seeded['single_choice_1']}")

    assert response.status_code == 200
    body = response.json()
    assert body["question"]["stem_blocks"] == [{"kind": "text", "text": "detail-stem"}]
    assert body["question"]["analysis_blocks"] == [{"kind": "text", "text": "detail-analysis"}]


def test_practice_session_reports_actual_selected_counts_when_paper_is_short():
    client = TestClient(app)
    seeded = _seed_practice_paper(single_choice_total=2, fill_blank_total=1, short_answer_total=0)

    response = client.post("/api/practice/sessions", json={"paper_id": seeded["paper_id"]})

    assert response.status_code == 200
    body = response.json()
    assert body["session"]["selected_counts"] == {
        "single_choice": 2,
        "fill_blank": 1,
        "short_answer": 0,
    }
    assert body["session"]["question_ids"] == [
        seeded["single_choice_1"],
        seeded["single_choice_2"],
        seeded["fill_blank_1"],
    ]


def test_practice_session_filters_questions_by_tag_id():
    client = TestClient(app)
    seeded = _seed_practice_paper(single_choice_total=2, fill_blank_total=1, short_answer_total=1)

    with get_session() as session:
        selected_tag = Tag(
            id="tag-practice-difficulty",
            tag_type="difficulty",
            name="较难",
            parent_id=None,
            tag_path="difficulty/较难",
            created_at=datetime.now(timezone.utc),
        )
        session.add(selected_tag)
        session.add(
            QuestionTag(
                id="question-tag-1",
                question_id=seeded["single_choice_1"],
                tag_id=selected_tag.id,
                source="auto",
                confidence=0.72,
                created_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            QuestionTag(
                id="question-tag-2",
                question_id=seeded["fill_blank_1"],
                tag_id=selected_tag.id,
                source="auto",
                confidence=0.72,
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

    response = client.post(
        "/api/practice/sessions",
        json={
            "paper_id": seeded["paper_id"],
            "tag_id": "tag-practice-difficulty",
            "single_choice_count": 8,
            "fill_blank_count": 8,
            "short_answer_count": 11,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session"]["question_ids"] == [seeded["single_choice_1"], seeded["fill_blank_1"]]
    assert body["session"]["available_counts"] == {
        "single_choice": 1,
        "fill_blank": 1,
        "short_answer": 0,
    }
    assert body["session"]["selected_counts"] == {
        "single_choice": 1,
        "fill_blank": 1,
        "short_answer": 0,
    }


def test_practice_session_without_paper_id_draws_from_all_papers():
    client = TestClient(app)
    seeded = _seed_two_practice_papers_for_all_scope()

    response = client.post(
        "/api/practice/sessions",
        json={"single_choice_count": 2, "fill_blank_count": 0, "short_answer_count": 0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session"]["paper_id"] is None
    assert set(body["session"]["question_ids"]) == {
        seeded["paper-all-1_question"],
        seeded["paper-all-2_question"],
    }
    assert len(body["questions"]) == 2

    attempt_response = client.post(
        "/api/practice/attempts",
        json={
            "question_id": seeded["paper-all-2_question"],
            "session_id": body["session"]["id"],
            "result": "correct",
        },
    )

    assert attempt_response.status_code == 200


def test_practice_session_randomized_shuffles_selected_questions(monkeypatch):
    client = TestClient(app)
    seeded = _seed_practice_paper(single_choice_total=1, fill_blank_total=1, short_answer_total=1)

    def reverse_in_place(items):
        items.reverse()

    monkeypatch.setattr("app.services.practice_service.shuffle", reverse_in_place)

    response = client.post(
        "/api/practice/sessions",
        json={"paper_id": seeded["paper_id"], "randomized": True, "single_choice_count": 1, "fill_blank_count": 1, "short_answer_count": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session"]["question_ids"] == [
        seeded["short_answer_1"],
        seeded["fill_blank_1"],
        seeded["single_choice_1"],
    ]


def test_practice_session_excludes_mastered_questions_when_requested():
    client = TestClient(app)
    seeded = _seed_practice_paper()

    client.post("/api/practice/attempts", json={"question_id": seeded["single_choice_1"], "result": "skip"})
    client.post("/api/practice/attempts", json={"question_id": seeded["fill_blank_1"], "result": "correct"})

    response = client.post(
        "/api/practice/sessions",
        json={
            "paper_id": seeded["paper_id"],
            "exclude_mastered": True,
            "single_choice_count": 8,
            "fill_blank_count": 8,
            "short_answer_count": 11,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert seeded["single_choice_1"] not in body["session"]["question_ids"]
    assert seeded["fill_blank_1"] not in body["session"]["question_ids"]
    assert len(body["questions"]) == 25


def test_practice_attempt_skip_marks_question_mastered():
    client = TestClient(app)
    seeded = _seed_practice_paper()

    response = client.post(
        "/api/practice/attempts",
        json={"question_id": seeded["single_choice_1"], "result": "skip"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["learning_state"]["mastered"] is True
    assert body["learning_state"]["wrong_count"] == 0
    assert body["learning_state"]["last_result"] == "skip"


def test_practice_attempt_wrong_clears_mastery_and_increments_wrong_count():
    client = TestClient(app)
    seeded = _seed_practice_paper()

    skip_response = client.post(
        "/api/practice/attempts",
        json={"question_id": seeded["fill_blank_1"], "result": "skip"},
    )
    wrong_response = client.post(
        "/api/practice/attempts",
        json={"question_id": seeded["fill_blank_1"], "result": "wrong"},
    )
    wrong_again_response = client.post(
        "/api/practice/attempts",
        json={"question_id": seeded["fill_blank_1"], "result": "wrong"},
    )

    assert skip_response.status_code == 200
    assert wrong_response.status_code == 200
    assert wrong_again_response.status_code == 200
    assert wrong_response.json()["learning_state"]["mastered"] is False
    assert wrong_response.json()["learning_state"]["wrong_count"] == 1
    assert wrong_again_response.json()["learning_state"]["mastered"] is False
    assert wrong_again_response.json()["learning_state"]["wrong_count"] == 2


def test_practice_wrong_question_filters_by_mastery_and_wrong_count():
    client = TestClient(app)
    seeded = _seed_practice_paper()

    client.post(
        "/api/practice/attempts",
        json={"question_id": seeded["fill_blank_2"], "result": "skip"},
    )
    client.post(
        "/api/practice/attempts",
        json={"question_id": seeded["short_answer_1"], "result": "wrong"},
    )
    client.post(
        "/api/practice/attempts",
        json={"question_id": seeded["short_answer_1"], "result": "wrong"},
    )

    mastered_response = client.get("/api/practice/questions", params={"mastered": True})
    wrong_count_response = client.get("/api/practice/questions", params={"min_wrong_count": 2})

    assert mastered_response.status_code == 200
    assert wrong_count_response.status_code == 200
    assert [item["question_id"] for item in mastered_response.json()["items"]] == [seeded["fill_blank_2"]]
    assert [item["question_id"] for item in wrong_count_response.json()["items"]] == [seeded["short_answer_1"]]


def test_practice_attempt_rejects_question_not_in_session():
    client = TestClient(app)
    seeded = _seed_practice_paper()

    session_response = client.post(
        "/api/practice/sessions",
        json={"paper_id": seeded["paper_id"], "single_choice_count": 1, "fill_blank_count": 1, "short_answer_count": 1},
    )
    session_id = session_response.json()["session"]["id"]

    response = client.post(
        "/api/practice/attempts",
        json={
            "question_id": seeded["single_choice_2"],
            "session_id": session_id,
            "result": "correct",
        },
    )

    assert response.status_code == 400


def test_practice_question_detail_returns_learning_state_and_recent_attempts():
    client = TestClient(app)
    seeded = _seed_practice_paper()

    client.post(
        "/api/practice/attempts",
        json={"question_id": seeded["short_answer_2"], "result": "wrong"},
    )

    response = client.get(f"/api/practice/questions/{seeded['short_answer_2']}")

    assert response.status_code == 200
    body = response.json()
    assert body["question"]["question_id"] == seeded["short_answer_2"]
    assert body["learning_state"]["mastered"] is False
    assert body["learning_state"]["wrong_count"] == 1
    assert len(body["recent_attempts"]) == 1
    assert body["recent_attempts"][0]["result"] == "wrong"


def test_practice_question_detail_limits_recent_attempts_window():
    client = TestClient(app)
    seeded = _seed_practice_paper()

    for _ in range(25):
        client.post(
            "/api/practice/attempts",
            json={"question_id": seeded["short_answer_3"], "result": "wrong"},
        )

    response = client.get(f"/api/practice/questions/{seeded['short_answer_3']}")

    assert response.status_code == 200
    body = response.json()
    assert len(body["recent_attempts"]) == 20
    assert all(attempt["result"] == "wrong" for attempt in body["recent_attempts"])
