"""Add paper metadata and question paper_set columns."""
from alembic import op
import sqlalchemy as sa

revision = '0003_paper_meta_and_sets'
down_revision = '0002_mock_test_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('papers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('meta', sa.Text(), nullable=True))

    with op.batch_alter_table('questions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('paper_set', sa.String(length=100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('questions', schema=None) as batch_op:
        batch_op.drop_column('paper_set')

    with op.batch_alter_table('papers', schema=None) as batch_op:
        batch_op.drop_column('meta')

