"""Create M0 foundation tables."""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("email", sa.String(320), nullable=False), sa.Column("name", sa.String(120), nullable=False), sa.Column("avatar", sa.String(500)), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("exams", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("code", sa.String(40), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("default_duration", sa.Integer(), nullable=False), sa.Column("active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_index("ix_exams_name", "exams", ["name"], unique=True)
    op.create_index("ix_exams_code", "exams", ["code"], unique=True)
    op.create_table("papers", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("exam_id", sa.Integer(), sa.ForeignKey("exams.id"), nullable=False), sa.Column("year", sa.Integer(), nullable=False), sa.Column("title", sa.String(200), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("file_url", sa.String(500)), sa.Column("answer_key_url", sa.String(500)), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_index("ix_papers_exam_id", "papers", ["exam_id"])
    op.create_table("marking_schemes", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("exam_id", sa.Integer(), sa.ForeignKey("exams.id"), nullable=False), sa.Column("section", sa.String(80), nullable=False), sa.Column("question_type", sa.String(40), nullable=False), sa.Column("correct", sa.Float(), nullable=False), sa.Column("wrong", sa.Float(), nullable=False), sa.Column("unattempted", sa.Float(), nullable=False), sa.Column("attempt_limit", sa.Integer()), sa.Column("partial_marking_rules", sa.JSON()), sa.Column("source", sa.String(40), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_index("ix_marking_schemes_exam_id", "marking_schemes", ["exam_id"])

def downgrade() -> None:
    op.drop_index("ix_marking_schemes_exam_id", table_name="marking_schemes")
    op.drop_table("marking_schemes")
    op.drop_index("ix_papers_exam_id", table_name="papers")
    op.drop_table("papers")
    op.drop_index("ix_exams_code", table_name="exams")
    op.drop_index("ix_exams_name", table_name="exams")
    op.drop_table("exams")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

