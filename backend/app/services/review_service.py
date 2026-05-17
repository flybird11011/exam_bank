from __future__ import annotations

import json
from uuid import uuid4

from app.db.models import Question, QuestionOption, ReviewLog
from app.db.session import get_session


def update_question(question_id: str, payload: dict) -> dict:
    with get_session() as session:
        question = session.get(Question, question_id)
        if question is None:
            question = Question(
                id=question_id,
                paper_id=question_id,
                question_no="0",
                order_no=0,
                question_type=payload.get("question_type", "unknown"),
                status=payload.get("status", "parsed"),
                stem_json="{}",
                answer_json="{}",
                analysis_json="{}",
                meta_json="{}",
                stem_text=payload.get("stem_text"),
                answer_text=payload.get("answer_text"),
            )
            session.add(question)
        before = {
            "status": question.status,
            "question_type": question.question_type,
            "stem_text": question.stem_text,
            "answer_text": question.answer_text,
            "analysis_text": question.analysis_text,
            "options": [
                {
                    "option_label": option.option_label,
                    "option_text": option.option_text,
                }
                for option in question.options
            ],
        }
        existing_option_json_by_label = {
            option.option_label: option.option_json
            for option in question.options
        }
        for key, value in payload.items():
            if key == "options":
                session.query(QuestionOption).filter(QuestionOption.question_id == question.id).delete()
                for order_no, option in enumerate(value or [], start=1):
                    session.add(
                        QuestionOption(
                            id=str(uuid4()),
                            question_id=question.id,
                            option_label=str(option.get("option_label", "")),
                            option_text=option.get("option_text"),
                            option_json=existing_option_json_by_label.get(str(option.get("option_label", "")), "{}"),
                            is_correct=bool(option.get("is_correct", False)),
                            order_no=order_no,
                        )
                    )
                continue
            if hasattr(question, key):
                setattr(question, key, value)
        session.add(
            ReviewLog(
                id=f"review-{question_id}",
                target_type="question",
                target_id=question_id,
                action_type="update",
                before_json=str(before),
                after_json=str(
                    {
                        "status": question.status,
                        "question_type": question.question_type,
                        "stem_text": question.stem_text,
                        "answer_text": question.answer_text,
                        "analysis_text": question.analysis_text,
                        "options": [
                            {
                                "option_label": option.option_label,
                                "option_text": option.option_text,
                            }
                            for option in question.options
                        ],
                    }
                ),
                reviewer="system",
            )
        )
        session.commit()
        return {
            "id": question.id,
            "status": question.status,
            "question_type": question.question_type,
            "stem_text": question.stem_text,
            "answer_text": question.answer_text,
            "analysis_text": question.analysis_text,
            "options": [
                {
                    "id": option.id,
                    "option_label": option.option_label,
                    "option_text": option.option_text,
                    "is_correct": option.is_correct,
                    "order_no": option.order_no,
                }
                for option in question.options
            ],
            "before": before,
        }
