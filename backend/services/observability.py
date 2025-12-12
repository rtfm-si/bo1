"""Observability links service for admin dashboard.

Provides access to external monitoring and observability tool URLs.
"""

from pydantic import BaseModel, Field

from bo1.config import get_settings


class ObservabilityLinks(BaseModel):
    """External observability tool links for admin access.

    Attributes:
        grafana_url: Grafana dashboard URL (optional)
        prometheus_url: Prometheus dashboard URL (optional)
        sentry_url: Sentry error tracking URL (optional)
    """

    grafana_url: str | None = Field(None, description="Grafana dashboard URL")
    prometheus_url: str | None = Field(None, description="Prometheus dashboard URL")
    sentry_url: str | None = Field(None, description="Sentry error tracking URL")


def get_observability_links() -> ObservabilityLinks:
    """Get configured observability links from environment.

    Missing URLs are set to None (buttons will be hidden in UI).

    Returns:
        ObservabilityLinks with configured URLs or None for missing ones
    """
    settings = get_settings()

    return ObservabilityLinks(
        grafana_url=settings.grafana_url or None,
        prometheus_url=settings.prometheus_url or None,
        sentry_url=settings.sentry_url or None,
    )
