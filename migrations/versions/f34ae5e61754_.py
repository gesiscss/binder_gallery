"""empty message

Revision ID: f34ae5e61754
Revises: 95ebbf30bba6
Create Date: 2019-01-31 17:30:14.748252

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f34ae5e61754'
down_revision = '95ebbf30bba6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('binder_launch', 'repo_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('binder_launch', 'repo_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    # ### end Alembic commands ###