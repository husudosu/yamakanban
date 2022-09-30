"""removed owner_id from card

Revision ID: 0d360a490bee
Revises: e144d6633b00
Create Date: 2022-09-30 08:06:28.422061

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0d360a490bee'
down_revision = 'e144d6633b00'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('card', schema=None) as batch_op:
        batch_op.drop_constraint('card_owner_id_fkey', type_='foreignkey')
        batch_op.drop_column('owner_id')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('card', schema=None) as batch_op:
        batch_op.add_column(sa.Column('owner_id', sa.INTEGER(), autoincrement=False, nullable=False))
        batch_op.create_foreign_key('card_owner_id_fkey', 'board_allowed_user', ['owner_id'], ['id'])

    # ### end Alembic commands ###
