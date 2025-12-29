"""Add performance_thresholds table for early warning detection.

Revision ID: zo_performance_thresholds
Revises: zn_error_pattern_tracking
Create Date: 2025-12-29

Adds:
- performance_thresholds table for runtime-adjustable performance thresholds
- Seeds default thresholds for key metrics
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "zo_performance_thresholds"
down_revision = "zn_error_pattern_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create performance_thresholds table and seed defaults."""
    op.create_table(
        "performance_thresholds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "metric_name",
            sa.String(100),
            nullable=False,
            unique=True,
            comment="Unique metric identifier",
        ),
        sa.Column(
            "warn_value",
            sa.Float(),
            nullable=False,
            comment="Warning threshold value",
        ),
        sa.Column(
            "critical_value",
            sa.Float(),
            nullable=False,
            comment="Critical threshold value",
        ),
        sa.Column(
            "window_minutes",
            sa.Integer(),
            nullable=False,
            server_default="5",
            comment="Time window in minutes for metric aggregation",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Whether threshold is actively monitored",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Human-readable description of the metric",
        ),
        sa.Column(
            "unit",
            sa.String(20),
            nullable=True,
            comment="Unit of measurement (e.g., ms, %, count)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Create index for lookups
    op.create_index(
        "ix_performance_thresholds_enabled",
        "performance_thresholds",
        ["enabled"],
        postgresql_where=sa.text("enabled = true"),
    )

    # Seed default thresholds
    conn = op.get_bind()

    defaults = [
        {
            "metric_name": "api_response_time_ms",
            "warn_value": 2000,
            "critical_value": 5000,
            "description": "API endpoint response time (p95)",
            "unit": "ms",
        },
        {
            "metric_name": "llm_response_time_ms",
            "warn_value": 30000,
            "critical_value": 60000,
            "description": "LLM API response time (p95)",
            "unit": "ms",
        },
        {
            "metric_name": "error_rate_percent",
            "warn_value": 5.0,
            "critical_value": 10.0,
            "description": "Error rate as percentage of requests",
            "unit": "%",
        },
        {
            "metric_name": "queue_depth",
            "warn_value": 100,
            "critical_value": 500,
            "description": "Number of items in processing queue",
            "unit": "count",
        },
        {
            "metric_name": "db_pool_usage_percent",
            "warn_value": 80.0,
            "critical_value": 95.0,
            "description": "Database connection pool utilization",
            "unit": "%",
        },
    ]

    for threshold in defaults:
        conn.execute(
            sa.text("""
                INSERT INTO performance_thresholds
                (metric_name, warn_value, critical_value, description, unit)
                VALUES (:metric_name, :warn_value, :critical_value, :description, :unit)
            """),
            threshold,
        )


def downgrade() -> None:
    """Drop performance_thresholds table."""
    op.drop_index("ix_performance_thresholds_enabled", "performance_thresholds")
    op.drop_table("performance_thresholds")
