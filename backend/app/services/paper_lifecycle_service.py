from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy import delete, select

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
)
from app.db.session import get_session


MEDIA_ROOT = Path(__file__).resolve().parents[2] / "media"


def hard_delete_paper(paper_id: str) -> dict:
    warnings: list[str] = []

    with get_session() as session:
        paper = session.get(ExamPaper, paper_id)
        if paper is None:
            return {
                "paper_id": paper_id,
                "deleted": False,
                "warnings": [f"paper {paper_id} not found"],
            }

        source_file_path = Path(paper.source_file_path)
        question_ids = session.execute(select(Question.id).where(Question.paper_id == paper_id)).scalars().all()
        section_ids = session.execute(select(PaperSection.id).where(PaperSection.paper_id == paper_id)).scalars().all()
        parse_run_ids = session.execute(select(ParseRun.id).where(ParseRun.paper_id == paper_id)).scalars().all()
        review_target_ids = [paper_id, *section_ids, *question_ids, *parse_run_ids]

        try:
            if review_target_ids:
                session.execute(delete(ReviewLog).where(ReviewLog.target_id.in_(review_target_ids)))

            if question_ids:
                session.execute(
                    delete(ContentBlock).where(
                        ContentBlock.owner_type == "question",
                        ContentBlock.owner_id.in_(question_ids),
                    )
                )
                session.execute(
                    delete(MediaAsset).where(
                        MediaAsset.owner_type == "question",
                        MediaAsset.owner_id.in_(question_ids),
                    )
                )
                session.execute(delete(QuestionPracticeAttempt).where(QuestionPracticeAttempt.question_id.in_(question_ids)))
                session.execute(delete(QuestionLearningState).where(QuestionLearningState.question_id.in_(question_ids)))
                session.execute(delete(QuestionTag).where(QuestionTag.question_id.in_(question_ids)))
                session.execute(delete(QuestionOption).where(QuestionOption.question_id.in_(question_ids)))

            if parse_run_ids:
                session.execute(delete(ParseTrace).where(ParseTrace.parse_run_id.in_(parse_run_ids)))
                session.execute(delete(ParseWarning).where(ParseWarning.parse_run_id.in_(parse_run_ids)))

            session.execute(delete(ParseRun).where(ParseRun.paper_id == paper_id))
            session.execute(delete(PracticeSession).where(PracticeSession.paper_id == paper_id))
            session.execute(delete(Question).where(Question.paper_id == paper_id))
            session.execute(delete(PaperSection).where(PaperSection.paper_id == paper_id))
            session.execute(delete(ExamPaper).where(ExamPaper.id == paper_id))
            session.commit()
        except Exception as exc:  # pragma: no cover - exercised via API warning path
            session.rollback()
            return {
                "paper_id": paper_id,
                "deleted": False,
                "warnings": [f"failed to delete persisted data for {paper_id}: {exc}"],
            }

    media_path = MEDIA_ROOT / paper_id
    if media_path.exists():
        try:
            shutil.rmtree(media_path)
        except Exception as exc:  # pragma: no cover - exercised via tests with monkeypatch
                warnings.append(f"failed to remove media directory {media_path}: {exc}")

    if source_file_path.exists():
        try:
            source_file_path.unlink()
        except Exception as exc:  # pragma: no cover - exercised via tests with monkeypatch
            warnings.append(f"failed to remove source file {source_file_path}: {exc}")

    return {
        "paper_id": paper_id,
        "deleted": True,
        "warnings": warnings,
    }
