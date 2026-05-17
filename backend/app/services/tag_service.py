from __future__ import annotations

from uuid import uuid4

from sqlalchemy import delete, select

from app.db.models import QuestionTag, Tag
from app.db.session import get_session


def get_or_create_tag(session, tag_type: str, name: str) -> Tag:
    existing = session.query(Tag).filter(Tag.tag_type == tag_type, Tag.name == name).first()
    if existing is not None:
        return existing

    tag = Tag(
        id=str(uuid4()),
        tag_type=tag_type,
        name=name,
        parent_id=None,
        tag_path=f"{tag_type}/{name}",
        created_at=None,
    )
    session.add(tag)
    session.flush()
    return tag


def list_tags(tag_type: str | None = None, keyword: str | None = None) -> list[dict]:
    with get_session() as session:
        stmt = select(Tag)
        if tag_type:
            stmt = stmt.where(Tag.tag_type == tag_type)
        if keyword:
            stmt = stmt.where(Tag.name.contains(keyword))
        tags = session.execute(stmt).scalars().all()
        return [
            {
                "id": tag.id,
                "tag_type": tag.tag_type,
                "name": tag.name,
                "parent_id": tag.parent_id,
                "tag_path": tag.tag_path,
            }
            for tag in tags
        ]


def add_question_tag(question_id: str, tag_type: str, name: str, source: str = "manual", confidence: float = 1.0) -> dict:
    with get_session() as session:
        tag = get_or_create_tag(session, tag_type=tag_type, name=name)
        existing = (
            session.query(QuestionTag)
            .filter(QuestionTag.question_id == question_id, QuestionTag.tag_id == tag.id, QuestionTag.source == source)
            .first()
        )
        if existing is None:
            session.add(
                QuestionTag(
                    id=str(uuid4()),
                    question_id=question_id,
                    tag_id=tag.id,
                    source=source,
                    confidence=confidence,
                )
            )
            session.commit()
        return {
            "question_id": question_id,
            "tag_id": tag.id,
            "tag_type": tag.tag_type,
            "name": tag.name,
            "source": source,
            "confidence": confidence,
        }


def remove_question_tag(question_id: str, tag_id: str, source: str | None = None) -> None:
    with get_session() as session:
        stmt = delete(QuestionTag).where(QuestionTag.question_id == question_id, QuestionTag.tag_id == tag_id)
        if source is not None:
            stmt = stmt.where(QuestionTag.source == source)
        session.execute(stmt)
        session.commit()


def list_question_tags(question_id: str) -> list[dict]:
    with get_session() as session:
        rows = (
            session.query(QuestionTag, Tag)
            .join(Tag, QuestionTag.tag_id == Tag.id)
            .filter(QuestionTag.question_id == question_id)
            .all()
        )
        return [
            {
                "question_id": question_id,
                "tag_id": tag.id,
                "tag_type": tag.tag_type,
                "name": tag.name,
                "source": question_tag.source,
                "confidence": float(question_tag.confidence) if question_tag.confidence is not None else None,
            }
            for question_tag, tag in rows
        ]

