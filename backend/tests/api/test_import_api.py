from pathlib import Path

from fastapi.testclient import TestClient

from app.db.models import ContentBlock, ExamPaper, MediaAsset, ParseRun, Question
from app.db.session import get_session
from app.main import MEDIA_ROOT, app


def _post_import(client: TestClient, fixture: Path, duplicate_policy: str | None = None):
    with fixture.open("rb") as f:
        payload = {
            "subject": "math",
            "region": "suzhou",
            "exam_year": 2025,
            "exam_type": "exam",
        }
        if duplicate_policy is not None:
            payload["duplicate_policy"] = duplicate_policy
        return client.post(
            "/api/papers/import",
            files={
                "file": (
                    "2025-suzhou-math-exam.docx",
                    f,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
            data=payload,
        )


def test_import_returns_parse_run_id():
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

    assert response.status_code == 200
    body = response.json()
    assert "parse_run_id" in body
    assert body["status"] == "parsed"

    with get_session() as session:
        paper = session.query(ExamPaper).one()
        assert paper.source_file_sha256


def test_import_exposes_stem_blocks_with_image_content():
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

    assert response.status_code == 200
    body = response.json()
    first_question = body["paper"]["sections"][0]["questions"][0]

    assert "stem_blocks" in first_question
    image_block = next(
        block
        for section in body["paper"]["sections"]
        for question in section["questions"]
        for block in question["stem_blocks"]
        if block["kind"] == "image"
    )

    assert image_block["url"].endswith(".png")
    assert image_block["original_file_name"]
    assert MEDIA_ROOT.joinpath(image_block["url"].split("/media/", 1)[1]).exists()


def test_import_aligns_stem_blocks_with_their_matching_question():
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

    body = response.json()
    second_question = body["paper"]["sections"][0]["questions"][1]

    assert second_question["stem_blocks"][0]["text"].startswith("2.")
    assert any(block["kind"] == "image" for block in second_question["stem_blocks"])
    assert all(not (block["kind"] == "text" and block["text"].strip().startswith(("A.", "B.", "C.", "D."))) for block in second_question["stem_blocks"])


def test_import_recognizes_small_numeric_inline_images_in_the_stem():
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

    body = response.json()
    third_question = body["paper"]["sections"][0]["questions"][2]

    assert any(block["kind"] == "text" and "11.5%" in block["text"] for block in third_question["stem_blocks"])


def test_import_converts_mathtype_option_to_text_blocks_in_paper_detail():
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

    first_question = detail["sections"][0]["questions"][0]
    option_d = next(option for option in first_question["options"] if option["option_label"] == "D")

    assert option_d["option_text"] == "\u22121"
    assert option_d["option_blocks"] == [{"kind": "text", "text": "\u22121", "source": "formula"}]


def test_import_extracts_formula_text_blocks_for_option_a_and_b():
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

    question_eight = detail["sections"][0]["questions"][7]
    option_a = next(option for option in question_eight["options"] if option["option_label"] == "A")
    option_b = next(option for option in question_eight["options"] if option["option_label"] == "B")

    assert option_a["option_blocks"][0]["kind"] == "text"
    assert option_a["option_blocks"][0]["source"] == "formula"
    assert option_b["option_blocks"][0]["kind"] == "text"
    assert option_b["option_blocks"][0]["source"] == "formula"


def test_import_preserves_text_after_formula_in_option_c():
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

    question_eight = detail["sections"][0]["questions"][7]
    option_c = next(option for option in question_eight["options"] if option["option_label"] == "C")

    assert option_c["option_text"] == "△A′CD的面积=△A′DE的面积"
    assert option_c["option_blocks"] == [
        {"kind": "text", "text": "△A′CD", "source": "formula"},
        {"kind": "text", "text": "的面积"},
        {"kind": "text", "text": "=△A′DE", "source": "formula"},
        {"kind": "text", "text": "的面积"},
    ]

def test_import_keeps_regular_images_in_question_two_as_image_blocks():
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

    second_question = detail["sections"][0]["questions"][1]
    stem_image_blocks = [block for block in second_question["stem_blocks"] if block["kind"] == "image"]
    option_d = next(option for option in second_question["options"] if option["option_label"] == "D")

    assert stem_image_blocks
    assert option_d["option_blocks"]
    assert option_d["option_blocks"][0]["kind"] == "image"
    assert all(block["kind"] != "text" for block in option_d["option_blocks"])


def test_import_exposes_analysis_blocks_for_question_five():
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

    fifth_question = detail["sections"][0]["questions"][4]
    analysis_blocks = fifth_question["analysis_blocks"]

    assert any(block["kind"] == "image" for block in analysis_blocks)
    assert any(block["kind"] == "text" and "70\u00b0+\u03b1=180\u00b0" in block["text"] for block in analysis_blocks)


def test_import_duplicate_policy_ask_returns_duplicate_payload_and_skips_second_import():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"

    with TestClient(app) as client:
        first_response = _post_import(client, fixture)
        duplicate_response = _post_import(client, fixture)

    assert first_response.status_code == 200
    assert duplicate_response.status_code == 409
    duplicate_body = duplicate_response.json()["detail"]
    first_body = first_response.json()
    assert duplicate_body["code"] == "DUPLICATE_PAPER"
    assert duplicate_body["duplicate_found"] is True
    assert duplicate_body["duplicate_policy"] == "ask"
    assert duplicate_body["existing_paper"]["paper_id"] == first_body["paper"]["paper_id"]
    assert duplicate_body["source_file_sha256"]

    with get_session() as session:
        assert session.query(ExamPaper).count() == 1
        assert session.query(ParseRun).count() == 1


def test_import_duplicate_policy_keep_both_imports_second_copy_with_same_fingerprint():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"

    with TestClient(app) as client:
        first_response = _post_import(client, fixture)
        second_response = _post_import(client, fixture, duplicate_policy="keep_both")

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    with get_session() as session:
        papers = session.query(ExamPaper).all()
        assert len(papers) == 2
        hashes = {paper.source_file_sha256 for paper in papers}
        assert len(hashes) == 1
        assert None not in hashes


def test_import_duplicate_policy_replace_deletes_old_paper_rows_and_media_tree():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"

    with TestClient(app) as client:
        first_response = _post_import(client, fixture)
        old_paper_id = first_response.json()["paper"]["paper_id"]
        with get_session() as session:
            old_source_file_path = session.get(ExamPaper, old_paper_id).source_file_path
        old_media_dir = MEDIA_ROOT / old_paper_id
        assert old_media_dir.exists()

        replace_response = _post_import(client, fixture, duplicate_policy="replace")

    assert replace_response.status_code == 200
    replace_body = replace_response.json()
    new_paper_id = replace_body["paper"]["paper_id"]
    assert new_paper_id != old_paper_id
    assert not old_media_dir.exists()
    assert not Path(old_source_file_path).exists()

    with get_session() as session:
        assert session.get(ExamPaper, old_paper_id) is None
        assert session.query(ExamPaper).count() == 1
        assert session.query(Question).filter(Question.paper_id == old_paper_id).count() == 0
        assert session.query(ContentBlock).filter(ContentBlock.owner_type == "question").count() > 0
        assert session.query(MediaAsset).filter(MediaAsset.owner_type == "question").count() > 0


def test_import_replace_reports_cleanup_warning_when_old_paper_cleanup_fails(monkeypatch):
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "2025-suzhou-math-exam.docx"

    with TestClient(app) as client:
        first_response = _post_import(client, fixture)
        old_paper_id = first_response.json()["paper"]["paper_id"]

        from app.api.routes import imports as imports_route

        def _failing_cleanup(_paper_id: str):
            return {
                "paper_id": old_paper_id,
                "deleted": False,
                "warnings": ["simulated cleanup failure"],
            }

        monkeypatch.setattr(imports_route, "hard_delete_paper", _failing_cleanup)
        replace_response = _post_import(client, fixture, duplicate_policy="replace")

    assert replace_response.status_code == 200
    replace_body = replace_response.json()
    assert replace_body["paper"]["paper_id"] != old_paper_id
    assert replace_body["cleanup_warnings"] == ["simulated cleanup failure"]

    with get_session() as session:
        assert session.query(ExamPaper).count() == 2




