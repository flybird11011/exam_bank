from app.db.base import Base
from app.db import models  # noqa: F401


def test_metadata_contains_core_tables():
    table_names = set(Base.metadata.tables.keys())
    assert {
        "exam_paper",
        "paper_section",
        "question",
        "question_option",
        "content_block",
        "media_asset",
        "tag",
        "question_tag",
        "parse_run",
        "parse_trace",
        "parse_warning",
        "review_log",
        "question_learning_state",
        "question_practice_attempt",
        "practice_session",
    }.issubset(table_names)
