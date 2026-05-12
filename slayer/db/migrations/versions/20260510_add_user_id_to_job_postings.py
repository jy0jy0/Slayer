"""add user_id to job_postings

Revision ID: 20260510_add_user_id_to_job_postings
Revises: 4981296b4b69
Create Date: 2026-05-10

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20260510_add_user_id_to_job_postings"
down_revision: Union[str, None] = "4981296b4b69"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_postings",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_job_postings_user_id", "job_postings", ["user_id"])
    op.create_foreign_key(
        "fk_job_postings_user_id_users",
        "job_postings",
        "users",
        ["user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_job_postings_user_id_users", "job_postings", type_="foreignkey")
    op.drop_index("ix_job_postings_user_id", table_name="job_postings")
    op.drop_column("job_postings", "user_id")
