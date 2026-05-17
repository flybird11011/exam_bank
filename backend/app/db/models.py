import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExamPaper(Base):
    __tablename__ = "exam_paper"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(String(50), nullable=False)
    region: Mapped[str | None] = mapped_column(String(100))
    exam_year: Mapped[int] = mapped_column(Integer, nullable=False)
    exam_type: Mapped[str | None] = mapped_column(String(50))
    source_file_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_file_path: Mapped[str] = mapped_column(Text, nullable=False)
    source_file_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    total_questions: Mapped[int | None] = mapped_column(Integer)
    total_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="parsed")
    meta_json: Mapped[dict] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))

    sections: Mapped[list["PaperSection"]] = relationship(back_populates="paper")
    practice_sessions: Mapped[list["PracticeSession"]] = relationship(back_populates="paper")


class PaperSection(Base):
    __tablename__ = "paper_section"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("exam_paper.id", ondelete="CASCADE"), nullable=False)
    section_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    section_type: Mapped[str] = mapped_column(String(30), nullable=False)
    question_count: Mapped[int | None] = mapped_column(Integer)
    total_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    instructions: Mapped[str | None] = mapped_column(Text)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_json: Mapped[dict] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))

    paper: Mapped["ExamPaper"] = relationship(back_populates="sections")
    questions: Mapped[list["Question"]] = relationship(back_populates="section")


class Question(Base):
    __tablename__ = "question"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("exam_paper.id", ondelete="CASCADE"), nullable=False)
    section_id: Mapped[str | None] = mapped_column(ForeignKey("paper_section.id", ondelete="SET NULL"))
    question_no: Mapped[str] = mapped_column(String(20), nullable=False)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
    question_type: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown")
    stem_text: Mapped[str | None] = mapped_column(Text)
    stem_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    answer_text: Mapped[str | None] = mapped_column(Text)
    answer_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    analysis_text: Mapped[str | None] = mapped_column(Text)
    analysis_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    difficulty: Mapped[float | None] = mapped_column(Numeric(3, 2))
    source_start_para: Mapped[int | None] = mapped_column(Integer)
    source_end_para: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="parsed")
    meta_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))

    section: Mapped["PaperSection | None"] = relationship(back_populates="questions")
    options: Mapped[list["QuestionOption"]] = relationship(back_populates="question")
    learning_state: Mapped["QuestionLearningState | None"] = relationship(back_populates="question", uselist=False)
    practice_attempts: Mapped[list["QuestionPracticeAttempt"]] = relationship(back_populates="question")


class QuestionOption(Base):
    __tablename__ = "question_option"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("question.id", ondelete="CASCADE"), nullable=False)
    option_label: Mapped[str] = mapped_column(String(10), nullable=False)
    option_text: Mapped[str | None] = mapped_column(Text)
    option_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))

    question: Mapped["Question"] = relationship(back_populates="options")


class ContentBlock(Base):
    __tablename__ = "content_block"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_type: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    block_type: Mapped[str] = mapped_column(String(30), nullable=False)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str | None] = mapped_column(Text)
    block_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))


class MediaAsset(Base):
    __tablename__ = "media_asset"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_type: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(30), nullable=False)
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    storage_url: Mapped[str] = mapped_column(Text, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    extra_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))


class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tag_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("tag.id", ondelete="SET NULL"))
    tag_path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))


class QuestionTag(Base):
    __tablename__ = "question_tag"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("question.id", ondelete="CASCADE"), nullable=False)
    tag_id: Mapped[str] = mapped_column(ForeignKey("tag.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="auto")
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))


class ParseRun(Base):
    __tablename__ = "parse_run"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("exam_paper.id", ondelete="CASCADE"), nullable=False)
    source_file_path: Mapped[str] = mapped_column(Text, nullable=False)
    parser_version: Mapped[str] = mapped_column(String(50), nullable=False)
    parse_status: Mapped[str] = mapped_column(String(20), nullable=False)
    total_questions_found: Mapped[int | None] = mapped_column(Integer)
    total_errors: Mapped[int | None] = mapped_column(Integer)
    run_meta_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))


class ParseTrace(Base):
    __tablename__ = "parse_trace"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    parse_run_id: Mapped[str] = mapped_column(ForeignKey("parse_run.id", ondelete="CASCADE"), nullable=False)
    owner_type: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    xml_ref: Mapped[str | None] = mapped_column(Text)
    paragraph_range_start: Mapped[int | None] = mapped_column(Integer)
    paragraph_range_end: Mapped[int | None] = mapped_column(Integer)
    raw_snippet: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))


class ParseWarning(Base):
    __tablename__ = "parse_warning"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    parse_run_id: Mapped[str] = mapped_column(ForeignKey("parse_run.id", ondelete="CASCADE"), nullable=False)
    owner_type: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    warning_code: Mapped[str] = mapped_column(String(80), nullable=False)
    warning_level: Mapped[str] = mapped_column(String(20), nullable=False)
    warning_message: Mapped[str] = mapped_column(Text, nullable=False)
    warning_meta_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))


class ReviewLog(Base):
    __tablename__ = "review_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    before_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    after_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    reviewer: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))


class QuestionLearningState(Base):
    __tablename__ = "question_learning_state"

    question_id: Mapped[str] = mapped_column(ForeignKey("question.id", ondelete="CASCADE"), primary_key=True)
    mastered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa.text("0"))
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=sa.text("0"))
    last_result: Mapped[str | None] = mapped_column(String(20))
    last_attempt_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))

    question: Mapped["Question"] = relationship(back_populates="learning_state")


class PracticeSession(Base):
    __tablename__ = "practice_session"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("exam_paper.id", ondelete="CASCADE"), nullable=False)
    mode: Mapped[str] = mapped_column(String(30), nullable=False, default="paper", server_default=sa.text("'paper'"))
    randomized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa.text("0"))
    exclude_mastered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa.text("0"))
    single_choice_count: Mapped[int] = mapped_column(Integer, nullable=False, default=8, server_default=sa.text("8"))
    fill_blank_count: Mapped[int] = mapped_column(Integer, nullable=False, default=8, server_default=sa.text("8"))
    short_answer_count: Mapped[int] = mapped_column(Integer, nullable=False, default=11, server_default=sa.text("11"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running", server_default=sa.text("'running'"))
    meta_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}", server_default=sa.text("'{}'"))
    created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))

    paper: Mapped["ExamPaper"] = relationship(back_populates="practice_sessions")
    attempts: Mapped[list["QuestionPracticeAttempt"]] = relationship(back_populates="session")


class QuestionPracticeAttempt(Base):
    __tablename__ = "question_practice_attempt"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("question.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("practice_session.id", ondelete="SET NULL"))
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    answer_payload: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))

    question: Mapped["Question"] = relationship(back_populates="practice_attempts")
    session: Mapped["PracticeSession | None"] = relationship(back_populates="attempts")
