from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.db.models import (
    ContentBlock,
    ExamPaper,
    MediaAsset,
    PaperSection,
    ParseRun,
    ParseTrace,
    ParseWarning,
    PracticeSession,
    Question,
    QuestionLearningState,
    QuestionOption,
    QuestionPracticeAttempt,
    QuestionTag,
    ReviewLog,
    Tag,
)
from app.db.session import get_session
from app.services.paper_lifecycle_service import MEDIA_ROOT, hard_delete_paper


def _seed_paper_tree(paper_id: str = "paper-delete-1") -> dict[str, str]:
    section_id = "section-delete-1"
    question_id = "question-delete-1"
    parse_run_id = "parse-run-delete-1"
    tag_id = "tag-delete-1"
    option_id = "option-delete-1"
    session_id = "practice-session-delete-1"

    with get_session() as session:
        session.add(
            ExamPaper(
                id=paper_id,
                title="Delete Me",
                subject="math",
                region="suzhou",
                exam_year=2025,
                exam_type="exam",
                source_file_name="delete.docx",
                source_file_path="delete.docx",
                source_file_sha256="a" * 64,
                status="parsed",
                meta_json="{}",
                created_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            PaperSection(
                id=section_id,
                paper_id=paper_id,
                section_no=1,
                title="Section 1",
                section_type="single_choice",
                order_no=1,
                meta_json="{}",
            )
        )
        session.add(
            Question(
                id=question_id,
                paper_id=paper_id,
                section_id=section_id,
                question_no="1",
                order_no=1,
                question_type="single_choice",
                stem_text="stem",
                stem_json="{}",
                answer_text="A",
                answer_json="{}",
                analysis_text="analysis",
                analysis_json="{}",
                status="parsed",
                meta_json="{}",
            )
        )
        session.add(
            QuestionOption(
                id=option_id,
                question_id=question_id,
                option_label="A",
                option_text="A",
                option_json="{}",
                is_correct=False,
                order_no=1,
            )
        )
        session.add(
            ParseRun(
                id=parse_run_id,
                paper_id=paper_id,
                source_file_path="delete.docx",
                parser_version="v1",
                parse_status="parsed",
                total_questions_found=1,
                total_errors=0,
                run_meta_json="{}",
                created_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            ParseTrace(
                id="parse-trace-delete-1",
                parse_run_id=parse_run_id,
                owner_type="question",
                owner_id=question_id,
                raw_snippet="snippet",
                created_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            ParseWarning(
                id="parse-warning-delete-1",
                parse_run_id=parse_run_id,
                owner_type="question",
                owner_id=question_id,
                warning_code="W1",
                warning_level="warn",
                warning_message="warning",
                warning_meta_json="{}",
                created_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            ContentBlock(
                id="content-delete-1",
                owner_type="question",
                owner_id=question_id,
                block_type="text",
                order_no=1,
                text_content="text",
                block_json="{}",
                created_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            MediaAsset(
                id="media-delete-1",
                owner_type="question",
                owner_id=question_id,
                asset_type="stem_image",
                file_name="image.png",
                mime_type="image/png",
                storage_url=f"/media/{paper_id}/{question_id}/image.png",
                extra_json="{}",
                created_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            Tag(
                id=tag_id,
                tag_type="knowledge",
                name="tag",
                tag_path="knowledge/tag",
                created_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            QuestionTag(
                id="question-tag-delete-1",
                question_id=question_id,
                tag_id=tag_id,
                source="auto",
                confidence=1,
                created_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            QuestionLearningState(
                question_id=question_id,
                mastered=False,
                wrong_count=0,
                last_result=None,
                updated_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            PracticeSession(
                id=session_id,
                paper_id=paper_id,
                mode="paper",
                randomized=False,
                exclude_mastered=False,
                single_choice_count=1,
                fill_blank_count=0,
                short_answer_count=0,
                status="running",
                meta_json="{}",
                created_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            QuestionPracticeAttempt(
                id="question-attempt-delete-1",
                question_id=question_id,
                session_id=session_id,
                result="wrong",
                answer_payload="{}",
                created_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            ReviewLog(
                id="review-log-delete-1",
                target_type="question",
                target_id=question_id,
                action_type="edit",
                before_json="{}",
                after_json="{}",
                reviewer="tester",
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

    media_dir = MEDIA_ROOT / paper_id / question_id
    media_dir.mkdir(parents=True, exist_ok=True)
    (media_dir / "image.png").write_bytes(b"image")

    return {
        "paper_id": paper_id,
        "question_id": question_id,
        "parse_run_id": parse_run_id,
        "session_id": session_id,
    }


def test_hard_delete_paper_removes_associated_rows_and_media_tree():
    seeded = _seed_paper_tree()
    paper_id = seeded["paper_id"]
    media_root_for_paper = MEDIA_ROOT / paper_id
    assert media_root_for_paper.exists()

    result = hard_delete_paper(paper_id)

    assert result["deleted"] is True
    assert result["warnings"] == []
    assert not media_root_for_paper.exists()

    with get_session() as session:
        assert session.get(ExamPaper, paper_id) is None
        assert session.query(PaperSection).filter(PaperSection.paper_id == paper_id).count() == 0
        assert session.query(Question).filter(Question.paper_id == paper_id).count() == 0
        assert session.query(QuestionOption).count() == 0
        assert session.query(ParseRun).filter(ParseRun.paper_id == paper_id).count() == 0
        assert session.query(ParseTrace).count() == 0
        assert session.query(ParseWarning).count() == 0
        assert session.query(ContentBlock).count() == 0
        assert session.query(MediaAsset).count() == 0
        assert session.query(QuestionTag).count() == 0
        assert session.query(QuestionLearningState).count() == 0
        assert session.query(PracticeSession).filter(PracticeSession.paper_id == paper_id).count() == 0
        assert session.query(QuestionPracticeAttempt).count() == 0
        assert session.query(ReviewLog).count() == 0


def test_hard_delete_paper_returns_warning_when_media_cleanup_fails(monkeypatch):
    seeded = _seed_paper_tree(paper_id="paper-delete-2")

    from app.services import paper_lifecycle_service

    def _raise_rmtree(_path: Path):
        raise OSError("simulated rmtree failure")

    monkeypatch.setattr(paper_lifecycle_service.shutil, "rmtree", _raise_rmtree)
    result = hard_delete_paper(seeded["paper_id"])

    assert result["deleted"] is True
    assert result["warnings"]
    assert "simulated rmtree failure" in result["warnings"][0]

    with get_session() as session:
        assert session.get(ExamPaper, seeded["paper_id"]) is None
