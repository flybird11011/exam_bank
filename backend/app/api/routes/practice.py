from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.practice_service import (
    PracticeSessionQuestionMismatchError,
    create_practice_session,
    get_practice_question,
    list_practice_questions,
    record_practice_attempt,
)


router = APIRouter(prefix="/api/practice")


class PracticeSessionCreate(BaseModel):
    paper_id: str | None = None
    randomized: bool = False
    exclude_mastered: bool = False
    single_choice_count: int = Field(default=8, ge=0)
    fill_blank_count: int = Field(default=8, ge=0)
    short_answer_count: int = Field(default=11, ge=0)


class PracticeAttemptCreate(BaseModel):
    question_id: str
    result: str
    session_id: str | None = None
    answer_payload: dict | list | str | None = None


@router.post("/sessions")
def create_session(payload: PracticeSessionCreate) -> dict:
    try:
        return create_practice_session(payload.model_dump())
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=f"Not found: {exc.args[0]}") from exc


@router.post("/attempts")
def create_attempt(payload: PracticeAttemptCreate) -> dict:
    try:
        return record_practice_attempt(payload.model_dump())
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=f"Not found: {exc.args[0]}") from exc
    except PracticeSessionQuestionMismatchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Unsupported result: {exc.args[0]}") from exc


@router.get("/questions")
def query_questions(
    mastered: bool | None = None,
    min_wrong_count: int | None = None,
    paper_id: str | None = None,
    question_type: str | None = None,
) -> dict:
    return list_practice_questions(
        mastered=mastered,
        min_wrong_count=min_wrong_count,
        paper_id=paper_id,
        question_type=question_type,
    )


@router.get("/questions/{question_id}")
def get_question(question_id: str) -> dict:
    try:
        return get_practice_question(question_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=f"Not found: {exc.args[0]}") from exc
