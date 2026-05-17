from __future__ import annotations

from sqlalchemy import select

from app.db.models import ExamPaper, Question
from app.db.session import get_session


def search_questions(subject: str | None = None, exam_year: int | None = None) -> dict:
    items: list[dict] = []
    with get_session() as session:
        stmt = select(Question, ExamPaper).join(ExamPaper, Question.paper_id == ExamPaper.id)
        if subject:
            stmt = stmt.where(ExamPaper.subject == subject)
        if exam_year:
            stmt = stmt.where(ExamPaper.exam_year == exam_year)
        for question, paper in session.execute(stmt).all():
            items.append(
                {
                    "paper_id": paper.id,
                    "question_id": question.id,
                    "question_no": question.question_no,
                    "stem_text": question.stem_text,
                    "question_type": question.question_type,
                    "status": question.status,
                }
            )
    return {"items": items, "total": len(items)}
