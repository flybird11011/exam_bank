"""add source file sha256 for exam papers

Revision ID: 20260517_0002
Revises: 20260517_0001
Create Date: 2026-05-17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260517_0002"
down_revision = "20260517_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("exam_paper", sa.Column("source_file_sha256", sa.String(length=64), nullable=True))
    op.create_index("ix_exam_paper_source_file_sha256", "exam_paper", ["source_file_sha256"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_exam_paper_source_file_sha256", table_name="exam_paper")
    op.drop_column("exam_paper", "source_file_sha256")
