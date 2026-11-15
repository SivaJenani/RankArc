"""Add image columns missing from the original migration chain, without changing rows."""
from alembic import op
import sqlalchemy as sa
revision = '0004_question_images'
down_revision = '0003_paper_meta_and_sets'
branch_labels = None
depends_on = None

def upgrade():
    inspector = sa.inspect(op.get_bind())
    for table in ('questions', 'options'):
        if 'image_url' not in {c['name'] for c in inspector.get_columns(table)}:
            op.add_column(table, sa.Column('image_url', sa.String(500), nullable=True))

def downgrade():
    for table in ('options', 'questions'):
        op.drop_column(table, 'image_url')
