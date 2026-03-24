"""Add worklog, time entry and remittance tables

Revision ID: 6e24f9a4c2e1
Revises: 1a31ce608336
Create Date: 2026-03-24 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = "6e24f9a4c2e1"
down_revision = "1a31ce608336"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "remittance",
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=False,
        ),
        sa.Column("total_amount", sa.Float(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_remittance_created_at"), "remittance", ["created_at"], unique=False)
    op.create_index(op.f("ix_remittance_owner_id"), "remittance", ["owner_id"], unique=False)

    op.create_table(
        "worklog",
        sa.Column(
            "task_name",
            sqlmodel.sql.sqltypes.AutoString(length=255),
            nullable=False,
        ),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("is_adjusted", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("remittance_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["remittance_id"], ["remittance.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_worklog_created_at"), "worklog", ["created_at"], unique=False)
    op.create_index(op.f("ix_worklog_owner_id"), "worklog", ["owner_id"], unique=False)
    op.create_index(op.f("ix_worklog_remittance_id"), "worklog", ["remittance_id"], unique=False)

    op.create_table(
        "timeentry",
        sa.Column(
            "description",
            sqlmodel.sql.sqltypes.AutoString(length=255),
            nullable=True,
        ),
        sa.Column("hours", sa.Float(), nullable=False),
        sa.Column("hourly_rate", sa.Float(), nullable=False),
        sa.Column("is_disputed", sa.Boolean(), nullable=False),
        sa.Column("is_removed", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("worklog_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["worklog_id"], ["worklog.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_timeentry_created_at"), "timeentry", ["created_at"], unique=False)
    op.create_index(op.f("ix_timeentry_worklog_id"), "timeentry", ["worklog_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_timeentry_worklog_id"), table_name="timeentry")
    op.drop_index(op.f("ix_timeentry_created_at"), table_name="timeentry")
    op.drop_table("timeentry")

    op.drop_index(op.f("ix_worklog_remittance_id"), table_name="worklog")
    op.drop_index(op.f("ix_worklog_owner_id"), table_name="worklog")
    op.drop_index(op.f("ix_worklog_created_at"), table_name="worklog")
    op.drop_table("worklog")

    op.drop_index(op.f("ix_remittance_owner_id"), table_name="remittance")
    op.drop_index(op.f("ix_remittance_created_at"), table_name="remittance")
    op.drop_table("remittance")
