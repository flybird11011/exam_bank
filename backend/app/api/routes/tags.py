from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.tag_service import add_question_tag, list_question_tags, list_tags, remove_question_tag


router = APIRouter()


class TagCreateRequest(BaseModel):
    tag_type: str
    name: str
    source: str = "manual"
    confidence: float = 1.0


@router.get("/api/tags")
def get_tags(tag_type: str | None = None, keyword: str | None = None) -> list[dict]:
    return list_tags(tag_type=tag_type, keyword=keyword)


@router.get("/api/questions/{question_id}/tags")
def get_question_tags(question_id: str) -> list[dict]:
    return list_question_tags(question_id)


@router.post("/api/questions/{question_id}/tags")
def create_question_tag(question_id: str, payload: TagCreateRequest) -> dict:
    return add_question_tag(
        question_id=question_id,
        tag_type=payload.tag_type,
        name=payload.name,
        source=payload.source,
        confidence=payload.confidence,
    )


@router.delete("/api/questions/{question_id}/tags/{tag_id}")
def delete_question_tag(question_id: str, tag_id: str, source: str | None = None) -> dict[str, str]:
    remove_question_tag(question_id, tag_id, source=source)
    return {"status": "deleted"}
