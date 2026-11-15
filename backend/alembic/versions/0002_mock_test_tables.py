"""Add mock test tables: questions, options, attempts, attempt_answers.

Also adds hashed_password to users and filename/file_path to papers.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_mock_test_tables"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users: add hashed_password ---
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("hashed_password", sa.String(200), nullable=True))

    # --- papers: add filename, file_path; make exam_id/year nullable ---
    with op.batch_alter_table("papers") as batch_op:
        batch_op.add_column(sa.Column("filename", sa.String(260), nullable=True))
        batch_op.add_column(sa.Column("file_path", sa.String(500), nullable=True))
        batch_op.alter_column("exam_id", nullable=True)
        batch_op.alter_column("year", nullable=True)

    # --- questions ---
    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id"), nullable=False),
        sa.Column("question_number", sa.Integer(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(20), nullable=False, server_default="mcq"),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("correct_option_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_questions_paper_id", "questions", ["paper_id"])

    # --- options ---
    op.create_table(
        "options",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("label", sa.String(1), nullable=False),
        sa.Column("option_text", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_options_question_id", "options", ["question_id"])

    # --- attempts ---
    op.create_table(
        "attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("total_questions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="in_progress"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_attempts_user_id", "attempts", ["user_id"])
    op.create_index("ix_attempts_paper_id", "attempts", ["paper_id"])

    # --- attempt_answers ---
    op.create_table(
        "attempt_answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attempt_id", sa.Integer(), sa.ForeignKey("attempts.id"), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column(
            "selected_option_id", sa.Integer(), sa.ForeignKey("options.id"), nullable=True
        ),
        sa.Column("is_correct", sa.Integer(), nullable=True),
        sa.Column("time_spent_seconds", sa.Integer(), nullable=True),
    )
    op.create_index("ix_attempt_answers_attempt_id", "attempt_answers", ["attempt_id"])
    op.create_index("ix_attempt_answers_question_id", "attempt_answers", ["question_id"])


def downgrade() -> None:
    op.drop_index("ix_attempt_answers_question_id", table_name="attempt_answers")
    op.drop_index("ix_attempt_answers_attempt_id", table_name="attempt_answers")
    op.drop_table("attempt_answers")

    op.drop_index("ix_attempts_paper_id", table_name="attempts")
    op.drop_index("ix_attempts_user_id", table_name="attempts")
    op.drop_table("attempts")

    op.drop_index("ix_options_question_id", table_name="options")
    op.drop_table("options")

    op.drop_index("ix_questions_paper_id", table_name="questions")
    op.drop_table("questions")

    with op.batch_alter_table("papers") as batch_op:
        batch_op.drop_column("file_path")
        batch_op.drop_column("filename")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("hashed_password")
