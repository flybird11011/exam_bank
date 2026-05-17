"""practice state tables

Revision ID: 20260517_0001
Revises: 20260516_0001
Create Date: 2026-05-17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260517_0001"
down_revision = "20260516_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "practice_session",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("paper_id", sa.String(length=36), sa.ForeignKey("exam_paper.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mode", sa.String(length=30), nullable=False, server_default=sa.text("'paper'")),
        sa.Column("randomized", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("exclude_mastered", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("single_choice_count", sa.Integer(), nullable=False, server_default=sa.text("8")),
        sa.Column("fill_blank_count", sa.Integer(), nullable=False, server_default=sa.text("8")),
        sa.Column("short_answer_count", sa.Integer(), nullable=False, server_default=sa.text("11")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'running'")),
        sa.Column("meta_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "question_learning_state",
        sa.Column("question_id", sa.String(length=36), sa.ForeignKey("question.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("mastered", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("wrong_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_result", sa.String(length=20), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "question_practice_attempt",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("question_id", sa.String(length=36), sa.ForeignKey("question.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("practice_session.id", ondelete="SET NULL"), nullable=True),
        sa.Column("result", sa.String(length=20), nullable=False),
        sa.Column("answer_payload", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("question_practice_attempt")
    op.drop_table("question_learning_state")
    op.drop_table("practice_session")
