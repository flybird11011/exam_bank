"""initial schema

Revision ID: 20260516_0001
Revises:
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260516_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exam_paper",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("subject", sa.String(length=50), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("exam_year", sa.Integer(), nullable=False),
        sa.Column("exam_type", sa.String(length=50), nullable=True),
        sa.Column("source_file_name", sa.Text(), nullable=False),
        sa.Column("source_file_path", sa.Text(), nullable=False),
        sa.Column("total_questions", sa.Integer(), nullable=True),
        sa.Column("total_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("meta_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "paper_section",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("paper_id", sa.String(length=36), sa.ForeignKey("exam_paper.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("section_type", sa.String(length=30), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=True),
        sa.Column("total_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("order_no", sa.Integer(), nullable=False),
        sa.Column("meta_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "question",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("paper_id", sa.String(length=36), sa.ForeignKey("exam_paper.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_id", sa.String(length=36), sa.ForeignKey("paper_section.id", ondelete="SET NULL"), nullable=True),
        sa.Column("question_no", sa.String(length=20), nullable=False),
        sa.Column("order_no", sa.Integer(), nullable=False),
        sa.Column("question_type", sa.String(length=30), nullable=False),
        sa.Column("stem_text", sa.Text(), nullable=True),
        sa.Column("stem_json", sa.Text(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("answer_json", sa.Text(), nullable=False),
        sa.Column("analysis_text", sa.Text(), nullable=True),
        sa.Column("analysis_json", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.Numeric(3, 2), nullable=True),
        sa.Column("source_start_para", sa.Integer(), nullable=True),
        sa.Column("source_end_para", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("meta_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "question_option",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("question_id", sa.String(length=36), sa.ForeignKey("question.id", ondelete="CASCADE"), nullable=False),
        sa.Column("option_label", sa.String(length=10), nullable=False),
        sa.Column("option_text", sa.Text(), nullable=True),
        sa.Column("option_json", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("order_no", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "content_block",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("owner_type", sa.String(length=20), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("block_type", sa.String(length=30), nullable=False),
        sa.Column("order_no", sa.Integer(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("block_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "media_asset",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("owner_type", sa.String(length=20), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("asset_type", sa.String(length=30), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("storage_url", sa.Text(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("extra_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "tag",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tag_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("parent_id", sa.String(length=36), sa.ForeignKey("tag.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tag_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "question_tag",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("question_id", sa.String(length=36), sa.ForeignKey("question.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tag_id", sa.String(length=36), sa.ForeignKey("tag.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "parse_run",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("paper_id", sa.String(length=36), sa.ForeignKey("exam_paper.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_file_path", sa.Text(), nullable=False),
        sa.Column("parser_version", sa.String(length=50), nullable=False),
        sa.Column("parse_status", sa.String(length=20), nullable=False),
        sa.Column("total_questions_found", sa.Integer(), nullable=True),
        sa.Column("total_errors", sa.Integer(), nullable=True),
        sa.Column("run_meta_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "parse_trace",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("parse_run_id", sa.String(length=36), sa.ForeignKey("parse_run.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_type", sa.String(length=20), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("xml_ref", sa.Text(), nullable=True),
        sa.Column("paragraph_range_start", sa.Integer(), nullable=True),
        sa.Column("paragraph_range_end", sa.Integer(), nullable=True),
        sa.Column("raw_snippet", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "parse_warning",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("parse_run_id", sa.String(length=36), sa.ForeignKey("parse_run.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_type", sa.String(length=20), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("warning_code", sa.String(length=80), nullable=False),
        sa.Column("warning_level", sa.String(length=20), nullable=False),
        sa.Column("warning_message", sa.Text(), nullable=False),
        sa.Column("warning_meta_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "review_log",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("target_type", sa.String(length=30), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=False),
        sa.Column("action_type", sa.String(length=30), nullable=False),
        sa.Column("before_json", sa.Text(), nullable=False),
        sa.Column("after_json", sa.Text(), nullable=False),
        sa.Column("reviewer", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("review_log")
    op.drop_table("parse_warning")
    op.drop_table("parse_trace")
    op.drop_table("parse_run")
    op.drop_table("question_tag")
    op.drop_table("tag")
    op.drop_table("media_asset")
    op.drop_table("content_block")
    op.drop_table("question_option")
    op.drop_table("question")
    op.drop_table("paper_section")
    op.drop_table("exam_paper")
