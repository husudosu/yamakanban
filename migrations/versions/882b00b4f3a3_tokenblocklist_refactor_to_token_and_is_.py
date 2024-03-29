"""TokenBlockList refactor to Token and is_revoked column created

Revision ID: 882b00b4f3a3
Revises: 4838bec095df
Create Date: 2022-12-22 07:47:13.169288

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '882b00b4f3a3'
down_revision = '4838bec095df'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('token',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('jti', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('type', sa.String(length=16), server_default='access_token', nullable=False),
    sa.Column('revoked', sa.Boolean(), server_default='0', nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('token', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_token_jti'), ['jti'], unique=False)

    with op.batch_alter_table('token_blocklist', schema=None) as batch_op:
        batch_op.drop_index('ix_token_blocklist_jti')

    op.drop_table('token_blocklist')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('token_blocklist',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('jti', sa.VARCHAR(length=36), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('type', sa.VARCHAR(length=16), server_default=sa.text("'access_token'::character varying"), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name='token_blocklist_user_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='token_blocklist_pkey')
    )
    with op.batch_alter_table('token_blocklist', schema=None) as batch_op:
        batch_op.create_index('ix_token_blocklist_jti', ['jti'], unique=False)

    with op.batch_alter_table('token', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_token_jti'))

    op.drop_table('token')
    # ### end Alembic commands ###
