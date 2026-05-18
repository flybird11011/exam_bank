from __future__ import annotations

import json
from datetime import datetime, timezone
from random import shuffle
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import select

from app.db.models import (
    ExamPaper,
    PracticeSession,
    Question,
    QuestionLearningState,
    QuestionOption,
    QuestionPracticeAttempt,
    QuestionTag,
    Tag,
)
from app.db.session import get_session


QUESTION_TYPE_ORDER = ("single_choice", "fill_blank", "short_answer")
RECENT_ATTEMPTS_LIMIT = 20


class PracticeSessionQuestionMismatchError(Exception):
    pass


def _default_state_payload() -> dict:
    return {
        "mastered": False,
        "wrong_count": 0,
        "last_result": None,
        "last_attempt_at": None,
    }


def _state_payload(state: QuestionLearningState | None) -> dict:
    if state is None:
        return _default_state_payload()
    return {
        "mastered": bool(state.mastered),
        "wrong_count": int(state.wrong_count or 0),
        "last_result": state.last_result,
        "last_attempt_at": state.last_attempt_at.isoformat() if state.last_attempt_at else None,
    }


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


def _question_payload(session, question: Question, state: QuestionLearningState | None = None) -> dict:
    options = (
        session.execute(
            select(QuestionOption).where(QuestionOption.question_id == question.id).order_by(QuestionOption.order_no)
        )
        .scalars()
        .all()
    )

    state_payload = _state_payload(state)
    return {
        "question_id": question.id,
        "paper_id": question.paper_id,
        "question_no": question.question_no,
        "order_no": question.order_no,
        "question_type": question.question_type,
        "stem_text": question.stem_text,
        "stem_blocks": _load_stem_blocks(question.stem_json),
        "answer_text": question.answer_text,
        "analysis_text": question.analysis_text,
        "analysis_blocks": _load_analysis_blocks(question.analysis_json),
        "options": [
            {
                "id": option.id,
                "option_label": option.option_label,
                "option_text": option.option_text,
                "option_blocks": _load_option_blocks(option.option_json),
                "is_correct": option.is_correct,
                "order_no": option.order_no,
            }
            for option in options
        ],
        **state_payload,
    }


def _get_question_state(session, question_id: str) -> QuestionLearningState | None:
    return session.get(QuestionLearningState, question_id)


def _ensure_question_exists(session, question_id: str) -> Question:
    question = session.get(Question, question_id)
    if question is None:
        raise LookupError(question_id)
    return question


def _serialize_attempt(attempt: QuestionPracticeAttempt) -> dict:
    payload = attempt.answer_payload
    parsed_payload: object | None = None
    if payload is not None:
        try:
            parsed_payload = json.loads(payload)
        except json.JSONDecodeError:
            parsed_payload = payload

    return {
        "id": attempt.id,
        "question_id": attempt.question_id,
        "session_id": attempt.session_id,
        "result": attempt.result,
        "answer_payload": parsed_payload,
        "created_at": attempt.created_at.isoformat() if attempt.created_at else None,
    }


def _load_questions_by_type(
    session,
    paper_id: str | None,
    question_type: str,
    tag_id: str | None = None,
) -> list[tuple[Question, QuestionLearningState | None]]:
    stmt = (
        select(Question, QuestionLearningState)
        .outerjoin(QuestionLearningState, QuestionLearningState.question_id == Question.id)
        .order_by(Question.order_no)
    )
    if paper_id is not None:
        stmt = stmt.where(Question.paper_id == paper_id)
    stmt = stmt.where(Question.question_type == question_type)
    if tag_id is not None:
        tagged_question_ids = select(QuestionTag.question_id).where(QuestionTag.tag_id == tag_id)
        stmt = stmt.where(Question.id.in_(tagged_question_ids))
    return list(session.execute(stmt).all())


def create_practice_session(payload: dict) -> dict:
    paper_id = payload.get("paper_id")
    tag_id = payload.get("tag_id")
    randomized = bool(payload.get("randomized", False))
    exclude_mastered = bool(payload.get("exclude_mastered", False))
    single_choice_count = int(payload.get("single_choice_count", 8))
    fill_blank_count = int(payload.get("fill_blank_count", 8))
    short_answer_count = int(payload.get("short_answer_count", 11))

    with get_session() as session:
        scope = "all_papers" if paper_id in (None, "") else "paper"
        if scope == "paper":
            paper = session.get(ExamPaper, paper_id)
            if paper is None:
                raise LookupError(paper_id)
            storage_paper_id = paper_id
        else:
            storage_paper_id = session.execute(select(ExamPaper.id).order_by(ExamPaper.created_at, ExamPaper.id)).scalars().first()
            if storage_paper_id is None:
                raise LookupError("exam_paper")

        if tag_id not in (None, "") and session.get(Tag, tag_id) is None:
            raise LookupError(tag_id)

        requested_counts = {
            "single_choice": single_choice_count,
            "fill_blank": fill_blank_count,
            "short_answer": short_answer_count,
        }
        available_counts: dict[str, int] = {}
        selected_counts: dict[str, int] = {}
        selected_entries: list[dict] = []

        for question_type in QUESTION_TYPE_ORDER:
            rows = _load_questions_by_type(session, paper_id, question_type, tag_id=tag_id if tag_id not in (None, "") else None)
            if exclude_mastered:
                rows = [row for row in rows if not row[1] or not row[1].mastered]
            available_counts[question_type] = len(rows)
            chosen_rows = rows[: requested_counts[question_type]]
            selected_counts[question_type] = len(chosen_rows)
            selected_entries.extend(
                {
                    "question_id": question.id,
                    "question": _question_payload(session, question, state),
                }
                for question, state in chosen_rows
            )

        if randomized:
            shuffle(selected_entries)

        selected_questions = [entry["question"] for entry in selected_entries]
        selected_question_ids = [entry["question_id"] for entry in selected_entries]

        practice_session = PracticeSession(
            id=str(uuid4()),
            paper_id=storage_paper_id,
            mode=scope,
            randomized=randomized,
            exclude_mastered=exclude_mastered,
            single_choice_count=single_choice_count,
            fill_blank_count=fill_blank_count,
            short_answer_count=short_answer_count,
            status="running",
            meta_json=json.dumps(
                {
                    "scope": scope,
                    "paper_id": paper_id,
                    "tag_id": tag_id if tag_id not in (None, "") else None,
                    "question_ids": selected_question_ids,
                    "question_counts": requested_counts,
                    "selected_counts": selected_counts,
                    "available_counts": available_counts,
                },
                ensure_ascii=False,
            ),
            created_at=datetime.now(timezone.utc),
        )
        session.add(practice_session)
        session.commit()

        return {
            "session": {
                "id": practice_session.id,
                "paper_id": None if scope == "all_papers" else practice_session.paper_id,
                "tag_id": tag_id if tag_id not in (None, "") else None,
                "mode": practice_session.mode,
                "randomized": practice_session.randomized,
                "exclude_mastered": practice_session.exclude_mastered,
                "single_choice_count": practice_session.single_choice_count,
                "fill_blank_count": practice_session.fill_blank_count,
                "short_answer_count": practice_session.short_answer_count,
                "status": practice_session.status,
                "created_at": practice_session.created_at.isoformat() if practice_session.created_at else None,
                "question_ids": selected_question_ids,
                "selected_counts": selected_counts,
                "available_counts": available_counts,
            },
            "questions": selected_questions,
        }


def record_practice_attempt(payload: dict) -> dict:
    question_id = payload["question_id"]
    result = payload["result"]
    session_id = payload.get("session_id")
    answer_payload = payload.get("answer_payload")

    with get_session() as session:
        question = _ensure_question_exists(session, question_id)
        if session_id is not None:
            practice_session = session.get(PracticeSession, session_id)
            if practice_session is None:
                raise LookupError(session_id)

            try:
                session_meta = json.loads(practice_session.meta_json or "{}")
            except json.JSONDecodeError:
                session_meta = {}
            selected_question_ids = set(session_meta.get("question_ids") or [])
            scope = session_meta.get("scope", "paper")
            if scope == "all_papers":
                if question_id not in selected_question_ids:
                    raise PracticeSessionQuestionMismatchError(
                        f"{question_id} not in session {session_id}"
                    )
            elif question.paper_id != practice_session.paper_id or question_id not in selected_question_ids:
                raise PracticeSessionQuestionMismatchError(
                    f"{question_id} not in session {session_id}"
                )

        state = _get_question_state(session, question_id)
        now = datetime.now(timezone.utc)
        if state is None:
            state = QuestionLearningState(
                question_id=question_id,
                mastered=False,
                wrong_count=0,
                last_result=None,
                last_attempt_at=None,
                updated_at=now,
            )
            session.add(state)

        if result == "correct" or result == "skip":
            state.mastered = True
        elif result == "wrong":
            state.mastered = False
            state.wrong_count = int(state.wrong_count or 0) + 1
        else:
            raise ValueError(result)

        state.last_result = result
        state.last_attempt_at = now
        state.updated_at = now

        if answer_payload is None:
            serialized_answer_payload = "{}"
        else:
            serialized_answer_payload = answer_payload if isinstance(answer_payload, str) else json.dumps(
                answer_payload,
                ensure_ascii=False,
            )

        session.add(
            QuestionPracticeAttempt(
                id=str(uuid4()),
                question_id=question.id,
                session_id=session_id,
                result=result,
                answer_payload=serialized_answer_payload,
                created_at=now,
            )
        )
        session.commit()

        return {"learning_state": _state_payload(state)}


def list_practice_questions(
    *,
    mastered: bool | None = None,
    min_wrong_count: int | None = None,
    paper_id: str | None = None,
    question_type: str | None = None,
) -> dict:
    with get_session() as session:
        stmt = (
            select(Question, QuestionLearningState)
            .outerjoin(QuestionLearningState, QuestionLearningState.question_id == Question.id)
            .order_by(Question.order_no)
        )
        if paper_id is not None:
            stmt = stmt.where(Question.paper_id == paper_id)
        if question_type is not None:
            stmt = stmt.where(Question.question_type == question_type)

        items: list[dict] = []
        for question, state in session.execute(stmt).all():
            state_payload = _state_payload(state)
            if mastered is not None and state_payload["mastered"] != mastered:
                continue
            if min_wrong_count is not None and state_payload["wrong_count"] < min_wrong_count:
                continue
            items.append(
                _question_payload(session, question, state),
            )

        return {"items": items, "total": len(items)}


def get_practice_question(question_id: str) -> dict:
    with get_session() as session:
        question = _ensure_question_exists(session, question_id)
        state = _get_question_state(session, question_id)
        attempts = (
            session.execute(
                select(QuestionPracticeAttempt)
                .where(QuestionPracticeAttempt.question_id == question_id)
                .order_by(sa.desc(QuestionPracticeAttempt.created_at), sa.desc(QuestionPracticeAttempt.id))
                .limit(RECENT_ATTEMPTS_LIMIT)
            )
            .scalars()
            .all()
        )
        return {
            "question": _question_payload(session, question, state),
            "learning_state": _state_payload(state),
            "recent_attempts": [_serialize_attempt(attempt) for attempt in attempts],
        }
