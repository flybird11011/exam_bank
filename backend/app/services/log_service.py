from __future__ import annotations

from app.db.models import ParseWarning, ReviewLog
from app.db.session import get_session


def list_review_logs() -> list[dict]:
    with get_session() as session:
        logs = session.query(ReviewLog).order_by(ReviewLog.created_at.desc()).all()
        return [
            {
                "id": log.id,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "action_type": log.action_type,
                "before_json": log.before_json,
                "after_json": log.after_json,
                "reviewer": log.reviewer,
            }
            for log in logs
        ]


def list_parse_warnings(parse_run_id: str) -> list[dict]:
    with get_session() as session:
        warnings = (
            session.query(ParseWarning)
            .filter(ParseWarning.parse_run_id == parse_run_id)
            .order_by(ParseWarning.created_at.asc())
            .all()
        )
        return [
            {
                "id": warning.id,
                "warning_code": warning.warning_code,
                "warning_level": warning.warning_level,
                "warning_message": warning.warning_message,
                "warning_meta_json": warning.warning_meta_json,
            }
            for warning in warnings
        ]

