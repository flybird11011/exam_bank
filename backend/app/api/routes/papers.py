import json

from fastapi import APIRouter, HTTPException
from sqlalchemy import desc, select

from app.db.models import ExamPaper, PaperSection, ParseRun, Question, QuestionOption
from app.db.session import get_session
from app.services.paper_lifecycle_service import hard_delete_paper

router = APIRouter(prefix="/api/papers")


def _load_stem_blocks(stem_json: str | None) -> list[dict]:
    if not stem_json:
        return []

    try:
        payload = json.loads(stem_json)
    except json.JSONDecodeError:
        return []

    stem_blocks = payload.get("stem_blocks")
    return stem_blocks if isinstance(stem_blocks, list) else []


def _load_option_blocks(option_json: str | None) -> list[dict]:
    if not option_json:
        return []

    try:
        payload = json.loads(option_json)
    except json.JSONDecodeError:
        return []

    option_blocks = payload.get("option_blocks")
    return option_blocks if isinstance(option_blocks, list) else []


def _load_analysis_blocks(analysis_json: str | None) -> list[dict]:
    if not analysis_json:
        return []

    try:
        payload = json.loads(analysis_json)
    except json.JSONDecodeError:
        return []

    analysis_blocks = payload.get("analysis_blocks")
    return analysis_blocks if isinstance(analysis_blocks, list) else []


@router.get("")
def list_papers() -> list[dict]:
    with get_session() as session:
        papers = session.execute(select(ExamPaper).order_by(desc(ExamPaper.created_at))).scalars().all()
        payload: list[dict] = []
        for paper in papers:
            parse_run = (
                session.execute(
                    select(ParseRun).where(ParseRun.paper_id == paper.id).order_by(desc(ParseRun.created_at))
                )
                .scalars()
                .first()
            )
            sections = session.execute(select(PaperSection).where(PaperSection.paper_id == paper.id)).scalars().all()
            question_count = (
                session.execute(select(Question).where(Question.paper_id == paper.id)).scalars().all()
            )
            payload.append(
                {
                    "paper_id": paper.id,
                    "parse_run_id": parse_run.id if parse_run else None,
                    "title": paper.title,
                    "subject": paper.subject,
                    "region": paper.region,
                    "exam_year": paper.exam_year,
                    "exam_type": paper.exam_type,
                    "section_count": len(sections),
                    "question_count": len(question_count),
                    "status": paper.status,
                }
            )
        return payload


@router.get("/{paper_id}")
def get_paper(paper_id: str) -> dict:
    with get_session() as session:
        paper = session.get(ExamPaper, paper_id)
        if paper is None:
            return {"paper_id": paper_id, "sections": []}

        parse_run = (
            session.execute(
                select(ParseRun).where(ParseRun.paper_id == paper_id).order_by(desc(ParseRun.created_at))
            )
            .scalars()
            .first()
        )

        sections_payload: list[dict] = []
        sections = (
            session.execute(
                select(PaperSection).where(PaperSection.paper_id == paper_id).order_by(PaperSection.order_no)
            )
            .scalars()
            .all()
        )
        for section in sections:
            questions = (
                session.execute(
                    select(Question)
                    .where(Question.section_id == section.id)
                    .order_by(Question.order_no)
                )
                .scalars()
                .all()
            )
            sections_payload.append(
                {
                    "id": section.id,
                    "title": section.title,
                    "section_type": section.section_type,
                    "order_no": section.order_no,
                    "questions": [
                        {
                            "id": question.id,
                            "question_no": question.question_no,
                            "question_type": question.question_type,
                            "stem_text": question.stem_text,
                            "stem_blocks": _load_stem_blocks(question.stem_json),
                            "answer_text": question.answer_text,
                            "analysis_text": question.analysis_text,
                            "analysis_blocks": _load_analysis_blocks(question.analysis_json),
                            "confidence": float(question.confidence) if question.confidence is not None else None,
                            "status": question.status,
                            "options": [
                                {
                                    "id": option.id,
                                    "option_label": option.option_label,
                                    "option_text": option.option_text,
                                    "option_blocks": _load_option_blocks(option.option_json),
                                    "is_correct": option.is_correct,
                                    "order_no": option.order_no,
                                }
                                for option in (
                                    session.execute(
                                        select(QuestionOption)
                                        .where(QuestionOption.question_id == question.id)
                                        .order_by(QuestionOption.order_no)
                                    )
                                    .scalars()
                                    .all()
                                )
                            ],
                        }
                        for question in questions
                    ],
                }
            )

        return {
            "paper_id": paper.id,
            "title": paper.title,
            "subject": paper.subject,
            "region": paper.region,
            "exam_year": paper.exam_year,
            "exam_type": paper.exam_type,
            "parse_run_id": parse_run.id if parse_run else None,
            "sections": sections_payload,
        }


@router.delete("/{paper_id}")
def delete_paper(paper_id: str) -> dict:
    result = hard_delete_paper(paper_id)
    if not result.get("deleted"):
        raise HTTPException(status_code=404, detail=f"Not found: {paper_id}")
    return result
