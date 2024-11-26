"""

Revision ID: 8a66d18af290
Revises: 004800a3041c
Create Date: 2024-11-16 23:35:50.450285

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a66d18af290'
down_revision: Union[str, None] = '004800a3041c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('files', sa.Column('file_generated_name', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('files', 'file_generated_name')
    # ### end Alembic commands ###