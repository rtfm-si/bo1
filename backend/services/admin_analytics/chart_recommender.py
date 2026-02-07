"""Heuristic chart type recommendation from query result shape.

Generates Plotly figure_json using Stephen Few principles
(same palette/layout as bo1/analysis/charts.py).
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Stephen Few-inspired palette (matches bo1/analysis/charts.py)
CHART_COLORS = [
    "#4A90A4",
    "#E07B39",
    "#5B8C5A",
    "#8E6C88",
    "#C4A35A",
    "#6B8E9B",
    "#7B9EA8",
    "#D4845A",
]

BASE_LAYOUT: dict[str, Any] = {
    "font": {"family": "Inter, system-ui, sans-serif", "size": 12, "color": "#374151"},
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "margin": {"l": 50, "r": 20, "t": 40, "b": 50, "pad": 4},
    "hovermode": "closest",
    "showlegend": False,
    "xaxis": {
        "showgrid": False,
        "showline": True,
        "linecolor": "#E5E7EB",
        "tickfont": {"size": 11},
    },
    "yaxis": {
        "showgrid": True,
        "gridcolor": "#F3F4F6",
        "showline": False,
        "tickfont": {"size": 11},
    },
}


def recommend_chart(
    columns: list[str],
    rows: list[dict[str, Any]],
    step_description: str = "",
) -> dict[str, Any] | None:
    """Recommend chart type and build Plotly figure_json from result data.

    Args:
        columns: Column names from query result
        rows: List of row dicts
        step_description: Optional step description for title

    Returns:
        Plotly figure_json dict or None if data not chartable
    """
    if not rows or not columns:
        return None

    row_count = len(rows)

    # Classify columns
    numeric_cols = _find_numeric_columns(columns, rows)
    date_cols = _find_date_columns(columns)
    text_cols = [c for c in columns if c not in numeric_cols and c not in date_cols]

    # Single numeric value — just a stat, no chart
    if row_count == 1 and len(numeric_cols) == 1 and not text_cols:
        return None

    # Time series: date column + numeric columns → line chart
    if date_cols and numeric_cols:
        return _build_time_series(date_cols[0], numeric_cols, rows, step_description)

    # Category + single numeric → bar chart (or pie if few categories)
    if text_cols and numeric_cols:
        if row_count <= 8 and len(numeric_cols) == 1:
            return _build_pie_chart(text_cols[0], numeric_cols[0], rows, step_description)
        return _build_bar_chart(text_cols[0], numeric_cols, rows, step_description)

    # Multiple numeric columns, no categories → table only
    if numeric_cols and not text_cols and not date_cols:
        if row_count > 1:
            # Use first column as x-axis
            return _build_bar_chart(
                columns[0], numeric_cols[1:] or numeric_cols, rows, step_description
            )

    return None


def _find_numeric_columns(columns: list[str], rows: list[dict]) -> list[str]:
    """Identify numeric columns from actual data."""
    numeric = []
    for col in columns:
        for row in rows[:5]:  # Sample first 5 rows
            val = row.get(col)
            if val is not None:
                if isinstance(val, (int, float)):
                    numeric.append(col)
                elif isinstance(val, str):
                    try:
                        float(val)
                        numeric.append(col)
                    except (ValueError, TypeError):
                        pass
                break
    return numeric


def _find_date_columns(columns: list[str]) -> list[str]:
    """Identify date/time columns by name heuristics."""
    date_keywords = (
        "date",
        "day",
        "month",
        "week",
        "year",
        "time",
        "created_at",
        "updated_at",
        "period",
        "timestamp",
    )
    return [c for c in columns if any(k in c.lower() for k in date_keywords)]


def _build_time_series(
    date_col: str, numeric_cols: list[str], rows: list[dict], title: str
) -> dict[str, Any]:
    """Build line chart for time series data."""
    x_vals = [r[date_col] for r in rows]
    traces = []
    for i, col in enumerate(numeric_cols[:4]):  # Max 4 series
        traces.append(
            {
                "type": "scatter",
                "mode": "lines+markers",
                "x": x_vals,
                "y": [_to_num(r.get(col, 0)) for r in rows],
                "name": _humanize(col),
                "line": {"color": CHART_COLORS[i % len(CHART_COLORS)], "width": 2},
                "marker": {"size": 4},
            }
        )

    layout = {**BASE_LAYOUT, "title": {"text": title, "font": {"size": 14}}}
    if len(numeric_cols) > 1:
        layout["showlegend"] = True
        layout["legend"] = {"orientation": "h", "y": -0.15}
    layout["xaxis"] = {**BASE_LAYOUT["xaxis"], "title": {"text": _humanize(date_col)}}
    layout["yaxis"] = {**BASE_LAYOUT["yaxis"], "title": {"text": _humanize(numeric_cols[0])}}

    return {"data": traces, "layout": layout}


def _build_bar_chart(
    category_col: str, numeric_cols: list[str], rows: list[dict], title: str
) -> dict[str, Any]:
    """Build bar chart for categorical data."""
    x_vals = [str(r.get(category_col, "")) for r in rows]
    traces = []
    for i, col in enumerate(numeric_cols[:4]):
        traces.append(
            {
                "type": "bar",
                "x": x_vals,
                "y": [_to_num(r.get(col, 0)) for r in rows],
                "name": _humanize(col),
                "marker": {"color": CHART_COLORS[i % len(CHART_COLORS)]},
            }
        )

    layout = {**BASE_LAYOUT, "title": {"text": title, "font": {"size": 14}}}
    if len(numeric_cols) > 1:
        layout["showlegend"] = True
        layout["barmode"] = "group"
    layout["xaxis"] = {**BASE_LAYOUT["xaxis"], "title": {"text": _humanize(category_col)}}

    return {"data": traces, "layout": layout}


def _build_pie_chart(
    label_col: str, value_col: str, rows: list[dict], title: str
) -> dict[str, Any]:
    """Build donut/pie chart for proportion data."""
    labels = [str(r.get(label_col, "")) for r in rows]
    values = [_to_num(r.get(value_col, 0)) for r in rows]

    trace = {
        "type": "pie",
        "labels": labels,
        "values": values,
        "hole": 0.4,
        "marker": {"colors": CHART_COLORS[: len(labels)]},
        "textinfo": "label+percent",
        "hoverinfo": "label+value+percent",
    }

    layout = {
        **BASE_LAYOUT,
        "title": {"text": title, "font": {"size": 14}},
        "showlegend": True,
        "legend": {"orientation": "h", "y": -0.1},
    }
    # Remove axis config for pie
    layout.pop("xaxis", None)
    layout.pop("yaxis", None)

    return {"data": [trace], "layout": layout}


def _to_num(val: Any) -> float:
    """Safely convert value to float."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _humanize(col_name: str) -> str:
    """Convert column_name to Human Name."""
    return col_name.replace("_", " ").title()
