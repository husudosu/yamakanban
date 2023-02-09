"""CheckListItem: User assignment, due date assignment removed

Revision ID: 9b9f11e39b32
Revises: e56e0ed57e72
Create Date: 2023-02-09 07:59:58.706301

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9b9f11e39b32'
down_revision = 'e56e0ed57e72'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('card_checklist_item', schema=None) as batch_op:
        batch_op.drop_constraint('card_checklist_item_assigned_board_user_id_fkey', type_='foreignkey')
        batch_op.drop_column('assigned_board_user_id')
        batch_op.drop_column('due_date')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('card_checklist_item', schema=None) as batch_op:
        batch_op.add_column(sa.Column('due_date', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('assigned_board_user_id', sa.INTEGER(), autoincrement=False, nullable=True))
        batch_op.create_foreign_key('card_checklist_item_assigned_board_user_id_fkey', 'board_allowed_user', ['assigned_board_user_id'], ['id'], ondelete='CASCADE')

    # ### end Alembic commands ###
