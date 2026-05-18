"""legacy initial tables marker

Revision ID: a692bd0d976b
Revises:
Create Date: 2026-05-15
"""

from typing import Sequence, Union


revision: str = "a692bd0d976b"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Compatibility marker for databases already stamped with this revision."""
    pass


def downgrade() -> None:
    """No-op because this marker does not create schema objects."""
    pass
