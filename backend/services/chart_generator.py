"""Chart generation service using Plotly.

Generates line, bar, pie, and scatter charts from DataFrames.
Returns JSON specs for frontend rendering, with optional PNG export for PDFs.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from backend.api.models import ChartSpec, FilterSpec
from backend.services.query_engine import _apply_filters

logger = logging.getLogger(__name__)

# Maximum rows to chart (prevent memory issues)
MAX_CHART_ROWS = 10000


class ChartError(Exception):
    """Error during chart generation."""

    pass


@dataclass
class ChartResult:
    """Result of chart generation."""

    figure_json: dict[str, Any]  # Plotly figure as JSON for frontend
    chart_type: str
    width: int
    height: int
    row_count: int


def _validate_fields(df: pd.DataFrame, spec: ChartSpec) -> None:
    """Validate that required fields exist in DataFrame."""
    if spec.x_field not in df.columns:
        raise ChartError(f"Column '{spec.x_field}' not found in dataset")
    if spec.y_field not in df.columns:
        raise ChartError(f"Column '{spec.y_field}' not found in dataset")
    if spec.group_field and spec.group_field not in df.columns:
        raise ChartError(f"Group column '{spec.group_field}' not found in dataset")


def _apply_chart_filters(df: pd.DataFrame, filters: list[FilterSpec] | None) -> pd.DataFrame:
    """Apply filters to DataFrame before charting."""
    if not filters:
        return df
    return _apply_filters(df, filters)


def _generate_line_chart(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    """Generate a line chart."""
    fig = px.line(
        df,
        x=spec.x_field,
        y=spec.y_field,
        color=spec.group_field,
        title=spec.title,
    )
    return fig


def _generate_bar_chart(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    """Generate a bar chart."""
    fig = px.bar(
        df,
        x=spec.x_field,
        y=spec.y_field,
        color=spec.group_field,
        title=spec.title,
    )
    return fig


def _generate_pie_chart(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    """Generate a pie chart."""
    fig = px.pie(
        df,
        names=spec.x_field,
        values=spec.y_field,
        title=spec.title,
    )
    return fig


def _generate_scatter_chart(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    """Generate a scatter chart."""
    fig = px.scatter(
        df,
        x=spec.x_field,
        y=spec.y_field,
        color=spec.group_field,
        title=spec.title,
    )
    return fig


def _build_figure(df: pd.DataFrame, spec: ChartSpec) -> tuple[go.Figure, int]:
    """Build a Plotly figure from DataFrame and spec.

    Returns:
        Tuple of (figure, row_count)
    """
    if df.empty:
        raise ChartError("Cannot generate chart from empty DataFrame")

    # Apply filters
    df = _apply_chart_filters(df, spec.filters)
    if df.empty:
        raise ChartError("No data remaining after applying filters")

    # Validate fields
    _validate_fields(df, spec)

    # Limit rows for performance
    if len(df) > MAX_CHART_ROWS:
        logger.warning(f"Truncating DataFrame from {len(df)} to {MAX_CHART_ROWS} rows for chart")
        df = df.head(MAX_CHART_ROWS)

    row_count = len(df)

    # Generate chart by type
    if spec.chart_type == "line":
        fig = _generate_line_chart(df, spec)
    elif spec.chart_type == "bar":
        fig = _generate_bar_chart(df, spec)
    elif spec.chart_type == "pie":
        fig = _generate_pie_chart(df, spec)
    elif spec.chart_type == "scatter":
        fig = _generate_scatter_chart(df, spec)
    else:
        raise ChartError(f"Unknown chart type: {spec.chart_type}")

    # Apply consistent styling
    fig.update_layout(
        template="plotly_white",
        font={"family": "Inter, sans-serif", "size": 12},
        margin={"l": 50, "r": 50, "t": 60, "b": 50},
        width=spec.width,
        height=spec.height,
    )

    return fig, row_count


def generate_chart(df: pd.DataFrame, spec: ChartSpec) -> ChartResult:
    """Generate a chart from DataFrame.

    Args:
        df: Input DataFrame
        spec: Chart specification

    Returns:
        ChartResult with Plotly JSON spec for frontend rendering

    Raises:
        ChartError: If chart generation fails
    """
    fig, row_count = _build_figure(df, spec)

    # Convert to JSON for frontend rendering
    figure_json = json.loads(fig.to_json())

    logger.info(
        f"Generated {spec.chart_type} chart: {row_count} data points, {spec.width}x{spec.height}"
    )

    return ChartResult(
        figure_json=figure_json,
        chart_type=spec.chart_type,
        width=spec.width,
        height=spec.height,
        row_count=row_count,
    )


def generate_chart_json(df: pd.DataFrame, spec: ChartSpec) -> dict:
    """Generate chart and return as JSON response for API.

    Args:
        df: Input DataFrame
        spec: Chart specification

    Returns:
        Dict with figure_json and metadata
    """
    result = generate_chart(df, spec)
    return {
        "figure_json": result.figure_json,
        "chart_type": result.chart_type,
        "width": result.width,
        "height": result.height,
        "row_count": result.row_count,
    }


def generate_chart_png(df: pd.DataFrame, spec: ChartSpec) -> bytes:
    """Generate chart as PNG bytes for PDF embedding.

    Uses matplotlib backend to render charts as PNG (no Chromium/kaleido required).

    Args:
        df: Input DataFrame
        spec: Chart specification

    Returns:
        PNG image bytes

    Raises:
        ChartError: If chart generation or PNG export fails
    """
    import io

    import matplotlib

    matplotlib.use("Agg")  # Non-GUI backend
    import matplotlib.pyplot as plt

    fig_mpl, row_count = _build_matplotlib_figure(df, spec)

    try:
        # Export to PNG
        buffer = io.BytesIO()
        fig_mpl.savefig(
            buffer,
            format="png",
            dpi=200,  # 2x for retina
            bbox_inches="tight",
            facecolor="white",
        )
        buffer.seek(0)
        png_bytes = buffer.getvalue()
        plt.close(fig_mpl)
    except Exception as e:
        plt.close(fig_mpl)
        raise ChartError(f"Failed to export chart image: {e}") from e

    logger.info(f"Exported {spec.chart_type} chart to PNG: {row_count} data points")

    return png_bytes


def _build_matplotlib_figure(df: pd.DataFrame, spec: ChartSpec):
    """Build a matplotlib figure for PNG export.

    Returns:
        Tuple of (matplotlib figure, row_count)
    """
    import matplotlib.pyplot as plt

    if df.empty:
        raise ChartError("Cannot generate chart from empty DataFrame")

    # Apply filters
    df = _apply_chart_filters(df, spec.filters)
    if df.empty:
        raise ChartError("No data remaining after applying filters")

    # Validate fields
    _validate_fields(df, spec)

    # Limit rows
    if len(df) > MAX_CHART_ROWS:
        df = df.head(MAX_CHART_ROWS)

    row_count = len(df)

    # Create figure with specified size (convert pixels to inches at 100 dpi base)
    fig, ax = plt.subplots(figsize=(spec.width / 100, spec.height / 100))

    # Generate chart by type
    if spec.chart_type == "line":
        if spec.group_field:
            for name, group in df.groupby(spec.group_field):
                ax.plot(group[spec.x_field], group[spec.y_field], label=name, marker="o")
            ax.legend()
        else:
            ax.plot(df[spec.x_field], df[spec.y_field], marker="o")

    elif spec.chart_type == "bar":
        if spec.group_field:
            # Grouped bar chart
            groups = df[spec.group_field].unique()
            x_vals = df[spec.x_field].unique()
            width = 0.8 / len(groups)
            for i, group in enumerate(groups):
                group_data = df[df[spec.group_field] == group]
                positions = [list(x_vals).index(x) + i * width for x in group_data[spec.x_field]]
                ax.bar(positions, group_data[spec.y_field], width=width, label=group)
            ax.set_xticks([i + width * (len(groups) - 1) / 2 for i in range(len(x_vals))])
            ax.set_xticklabels(x_vals)
            ax.legend()
        else:
            ax.bar(df[spec.x_field], df[spec.y_field])

    elif spec.chart_type == "pie":
        ax.pie(df[spec.y_field], labels=df[spec.x_field], autopct="%1.1f%%")

    elif spec.chart_type == "scatter":
        if spec.group_field:
            for name, group in df.groupby(spec.group_field):
                ax.scatter(group[spec.x_field], group[spec.y_field], label=name)
            ax.legend()
        else:
            ax.scatter(df[spec.x_field], df[spec.y_field])

    else:
        raise ChartError(f"Unknown chart type: {spec.chart_type}")

    # Apply title and labels
    if spec.title:
        ax.set_title(spec.title)
    if spec.chart_type != "pie":
        ax.set_xlabel(spec.x_field)
        ax.set_ylabel(spec.y_field)

    # Style
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()

    return fig, row_count
