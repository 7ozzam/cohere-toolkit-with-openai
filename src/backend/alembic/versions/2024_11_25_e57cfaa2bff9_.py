"""

Revision ID: e57cfaa2bff9
Revises: 8a66d18af290
Create Date: 2024-11-25 10:49:24.401347

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e57cfaa2bff9'
down_revision: Union[str, None] = '8a66d18af290'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('folders',
    sa.Column('user_id', sa.String(), nullable=True),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=False),
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('conversation_folders',
    sa.Column('conversation_id', sa.String(), nullable=False),
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('folder_id', sa.String(), nullable=False),
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['folder_id'], ['folders.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('conversation_id', 'folder_id', name='unique_conversation_folder')
    )
    op.add_column('files', sa.Column('folder_id', sa.String(), nullable=True))
    op.alter_column('files', 'file_name',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.create_foreign_key(None, 'files', 'folders', ['folder_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'files', type_='foreignkey')
    op.alter_column('files', 'file_name',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.drop_column('files', 'folder_id')
    op.drop_table('conversation_folders')
    op.drop_table('folders')
    # ### end Alembic commands ###