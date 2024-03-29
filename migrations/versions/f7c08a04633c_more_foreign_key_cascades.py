"""More foreign key cascades

Revision ID: f7c08a04633c
Revises: a6dcf7bd5c58
Create Date: 2022-12-03 18:07:58.548165

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f7c08a04633c'
down_revision = 'a6dcf7bd5c58'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('card', schema=None) as batch_op:
        batch_op.drop_constraint('card_board_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(None, 'board', ['board_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('list', schema=None) as batch_op:
        batch_op.drop_constraint('list_board_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(None, 'board', ['board_id'], ['id'], ondelete='CASCADE')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('list', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key('list_board_id_fkey', 'board', ['board_id'], ['id'])

    with op.batch_alter_table('card', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key('card_board_id_fkey', 'board', ['board_id'], ['id'])

    # ### end Alembic commands ###
