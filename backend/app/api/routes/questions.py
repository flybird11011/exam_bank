from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.review_service import update_question
from app.services.search_service import search_questions


router = APIRouter(prefix="/api/questions")


class QuestionPatch(BaseModel):
    status: str | None = None
    question_type: str | None = None
    stem_text: str | None = None
    answer_text: str | None = None
    analysis_text: str | None = None
    options: list[dict] | None = None


@router.patch("/{question_id}")
def patch_question(question_id: str, payload: QuestionPatch) -> dict:
    return update_question(question_id, payload.model_dump(exclude_none=True))


@router.get("/search")
def search(subject: str | None = None, exam_year: int | None = None) -> dict:
    return search_questions(subject=subject, exam_year=exam_year)
