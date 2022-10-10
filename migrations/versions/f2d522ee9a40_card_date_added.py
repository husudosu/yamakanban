"""Card date added

Revision ID: f2d522ee9a40
Revises: 0d360a490bee
Create Date: 2022-10-10 08:32:17.982564

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2d522ee9a40'
down_revision = '0d360a490bee'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('card_date',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('card_id', sa.Integer(), nullable=True),
    sa.Column('board_id', sa.Integer(), nullable=True),
    sa.Column('is_due_date', sa.Boolean(), nullable=True),
    sa.Column('dt_from', sa.DateTime(), nullable=False),
    sa.Column('dt_to', sa.DateTime(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['board_id'], ['board.id'], ),
    sa.ForeignKeyConstraint(['card_id'], ['card.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('card_date')
    # ### end Alembic commands ###
