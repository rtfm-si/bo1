"""Chart generation for insights following Stephen Few's principles.

Generates Plotly figure_json specs with:
- Minimal chart junk (no 3D, no gratuitous decorations)
- High data-ink ratio
- Appropriate chart type for data
- Clean, readable defaults
- Hover interactions for detail-on-demand
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Stephen Few-inspired color palette (muted, professional)
CHART_COLORS = [
    "#4A90A4",  # Blue-gray
    "#E07B39",  # Muted orange
    "#5B8C5A",  # Sage green
    "#8E6C88",  # Muted purple
    "#C4A35A",  # Gold
    "#6B8E9B",  # Steel blue
]

# Minimal layout defaults following Stephen Few principles
# Axis defaults for reuse (typed for mypy)
_XAXIS_DEFAULTS: dict[str, Any] = {
    "showgrid": False,
    "showline": True,
    "linecolor": "#E5E7EB",
    "tickfont": {"size": 11},
    "title": {"font": {"size": 12, "color": "#6B7280"}},
}
_YAXIS_DEFAULTS: dict[str, Any] = {
    "showgrid": True,
    "gridcolor": "#F3F4F6",
    "showline": False,
    "tickfont": {"size": 11},
    "title": {"font": {"size": 12, "color": "#6B7280"}},
}

BASE_LAYOUT: dict[str, Any] = {
    "font": {"family": "Inter, system-ui, sans-serif", "size": 12, "color": "#374151"},
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "margin": {"l": 50, "r": 20, "t": 40, "b": 50, "pad": 4},
    "hovermode": "closest",
    "showlegend": False,
    "xaxis": _XAXIS_DEFAULTS,
    "yaxis": _YAXIS_DEFAULTS,
}


def generate_chart_from_insight(
    visualization_config: dict[str, Any],
    supporting_data: dict[str, Any],
    title: str | None = None,
) -> dict[str, Any] | None:
    """Generate Plotly figure_json from insight visualization config.

    Args:
        visualization_config: Dict with type, x_axis, y_axis, group_by, title
        supporting_data: Data to visualize (stats, values, etc.)
        title: Optional override title for the chart

    Returns:
        Plotly figure_json dict or None if insufficient data
    """
    if not visualization_config or not supporting_data:
        return None

    chart_type = visualization_config.get("type", "bar")
    x_axis = visualization_config.get("x_axis")
    y_axis = visualization_config.get("y_axis")
    chart_title = title or visualization_config.get("title", "")

    # Extract data from supporting_data
    data = _extract_chart_data(supporting_data, x_axis, y_axis)
    if not data:
        return None

    # Generate appropriate chart
    try:
        if chart_type == "bar":
            return _generate_bar_chart(data, chart_title, x_axis, y_axis)
        elif chart_type == "line":
            return _generate_line_chart(data, chart_title, x_axis, y_axis)
        elif chart_type == "scatter":
            return _generate_scatter_chart(data, chart_title, x_axis, y_axis)
        elif chart_type == "pie":
            return _generate_pie_chart(data, chart_title)
        else:
            # Default to bar
            return _generate_bar_chart(data, chart_title, x_axis, y_axis)
    except Exception as e:
        logger.warning(f"Failed to generate {chart_type} chart: {e}")
        return None


def _extract_chart_data(
    supporting_data: dict[str, Any],
    x_axis: str | None,
    y_axis: str | None,
) -> dict[str, Any] | None:
    """Extract x/y data from supporting_data structure.

    Handles various data formats from LLM responses.
    """
    # Check for chart_data nested structure (from updated prompt)
    chart_data = supporting_data.get("chart_data", {})
    if chart_data and isinstance(chart_data, dict):
        x_data = chart_data.get("x", [])
        y_data = chart_data.get("y", [])
        if x_data and y_data:
            return {
                "x": x_data,
                "y": y_data,
                "unit": chart_data.get("unit", ""),
            }
        # Stats format for distributions
        stats = chart_data.get("stats", {})
        if stats:
            return {"stats": stats, "unit": chart_data.get("unit", "")}

    # Direct data array
    if "data" in supporting_data and isinstance(supporting_data["data"], list):
        return {"values": supporting_data["data"]}

    # X/Y arrays at root level
    x_data = supporting_data.get("x", supporting_data.get("labels", []))
    y_data = supporting_data.get("y", supporting_data.get("values", []))

    if x_data and y_data:
        return {"x": x_data, "y": y_data}

    # Stats-based (for numeric distributions)
    stats = supporting_data.get("stats", {})
    if stats:
        return {"stats": stats}

    # Categories with counts
    categories = supporting_data.get("categories", {})
    if categories and isinstance(categories, dict):
        return {
            "x": list(categories.keys()),
            "y": list(categories.values()),
        }

    # Top values list
    top_values = supporting_data.get("top_values", [])
    if top_values:
        if isinstance(top_values[0], dict):
            return {
                "x": [v.get("label", v.get("name", str(i))) for i, v in enumerate(top_values)],
                "y": [v.get("value", v.get("count", 0)) for v in top_values],
            }
        return {"values": top_values}

    # Trend data
    trend = supporting_data.get("trend", [])
    if trend:
        return {"values": trend}

    # Comparison data
    comparison = supporting_data.get("comparison", {})
    if comparison:
        return {
            "x": list(comparison.keys()),
            "y": list(comparison.values()),
        }

    return None


def _generate_bar_chart(
    data: dict[str, Any],
    title: str,
    x_label: str | None,
    y_label: str | None,
) -> dict[str, Any]:
    """Generate horizontal bar chart (better for labels)."""
    x = data.get("x", [])
    y = data.get("y", [])
    unit = data.get("unit", "")

    if not x or not y:
        # Generate from stats
        stats = data.get("stats", {})
        if stats:
            x = ["Min", "Median", "Mean", "Max"]
            y = [
                stats.get("min", 0),
                stats.get("median", stats.get("p50", 0)),
                stats.get("mean", 0),
                stats.get("max", 0),
            ]

    # Limit to top 10 for readability (Stephen Few: don't overwhelm)
    if len(x) > 10:
        # Sort and take top 10
        pairs = sorted(zip(x, y, strict=False), key=lambda p: p[1], reverse=True)[:10]
        x = [p[0] for p in pairs]
        y = [p[1] for p in pairs]

    # Calculate customdata for enhanced hover (%, rank)
    total = sum(y) if y else 1
    n = len(y)
    # Sort indices by value descending to get ranks
    sorted_indices = sorted(range(n), key=lambda i: y[i], reverse=True)
    ranks = [0] * n
    for rank, idx in enumerate(sorted_indices, 1):
        ranks[idx] = rank
    customdata = [[round(v / total * 100, 1), ranks[i], n] for i, v in enumerate(y)]

    # Build hover template with unit
    unit_suffix = f" {unit}" if unit and unit not in ["%", "$"] else unit
    hover_template = (
        "<b>%{y}</b><br>"
        f"Value: %{{x:,.1f}}{unit_suffix}<br>"
        "Share: %{customdata[0]:.1f}%<br>"
        "Rank: %{customdata[1]} of %{customdata[2]}"
        "<extra></extra>"
    )

    return {
        "data": [
            {
                "type": "bar",
                "x": y,  # Horizontal bar
                "y": x,
                "orientation": "h",
                "marker": {
                    "color": CHART_COLORS[0],
                    "line": {"width": 0},
                },
                "customdata": customdata,
                "hovertemplate": hover_template,
            }
        ],
        "layout": {
            **BASE_LAYOUT,
            "title": {"text": title, "font": {"size": 14, "color": "#111827"}, "x": 0},
            "xaxis": {
                **_XAXIS_DEFAULTS,
                "title": {"text": y_label or "", "font": {"size": 12, "color": "#6B7280"}},
            },
            "yaxis": {
                **_YAXIS_DEFAULTS,
                "title": {"text": "", "font": {"size": 12, "color": "#6B7280"}},
                "automargin": True,
            },
            "bargap": 0.3,
        },
    }


def _generate_line_chart(
    data: dict[str, Any],
    title: str,
    x_label: str | None,
    y_label: str | None,
) -> dict[str, Any]:
    """Generate line chart for trends."""
    x = data.get("x", [])
    y = data.get("y", data.get("values", []))

    if not x and y:
        x = list(range(len(y)))

    return {
        "data": [
            {
                "type": "scatter",
                "mode": "lines+markers",
                "x": x,
                "y": y,
                "line": {"color": CHART_COLORS[0], "width": 2},
                "marker": {"size": 6, "color": CHART_COLORS[0]},
                "hovertemplate": "<b>%{x}</b><br>%{y:,.2f}<extra></extra>",
            }
        ],
        "layout": {
            **BASE_LAYOUT,
            "title": {"text": title, "font": {"size": 14, "color": "#111827"}, "x": 0},
            "xaxis": {
                **_XAXIS_DEFAULTS,
                "title": {"text": x_label or "", "font": {"size": 12, "color": "#6B7280"}},
            },
            "yaxis": {
                **_YAXIS_DEFAULTS,
                "title": {"text": y_label or "", "font": {"size": 12, "color": "#6B7280"}},
            },
        },
    }


def _generate_scatter_chart(
    data: dict[str, Any],
    title: str,
    x_label: str | None,
    y_label: str | None,
) -> dict[str, Any]:
    """Generate scatter chart for correlations."""
    x = data.get("x", [])
    y = data.get("y", [])

    return {
        "data": [
            {
                "type": "scatter",
                "mode": "markers",
                "x": x,
                "y": y,
                "marker": {
                    "size": 8,
                    "color": CHART_COLORS[0],
                    "opacity": 0.7,
                    "line": {"width": 1, "color": "#ffffff"},
                },
                "hovertemplate": "%{x:,.2f}, %{y:,.2f}<extra></extra>",
            }
        ],
        "layout": {
            **BASE_LAYOUT,
            "title": {"text": title, "font": {"size": 14, "color": "#111827"}, "x": 0},
            "xaxis": {
                **_XAXIS_DEFAULTS,
                "title": {"text": x_label or "", "font": {"size": 12, "color": "#6B7280"}},
            },
            "yaxis": {
                **_YAXIS_DEFAULTS,
                "title": {"text": y_label or "", "font": {"size": 12, "color": "#6B7280"}},
            },
        },
    }


def _generate_pie_chart(
    data: dict[str, Any],
    title: str,
) -> dict[str, Any]:
    """Generate pie/donut chart for proportions.

    Uses donut style (Stephen Few: easier to compare arc lengths).
    """
    labels = data.get("x", [])
    values = data.get("y", data.get("values", []))
    unit = data.get("unit", "")

    # Limit to 6 segments (Stephen Few: too many segments are hard to read)
    if len(labels) > 6:
        pairs = sorted(zip(labels, values, strict=False), key=lambda p: p[1], reverse=True)
        top = pairs[:5]
        other_sum = sum(p[1] for p in pairs[5:])
        labels = [p[0] for p in top] + ["Other"]
        values = [p[1] for p in top] + [other_sum]

    # Calculate ranks for customdata
    n = len(values)
    sorted_indices = sorted(range(n), key=lambda i: values[i], reverse=True)
    ranks = [0] * n
    for rank, idx in enumerate(sorted_indices, 1):
        ranks[idx] = rank
    customdata = [[ranks[i], n] for i in range(n)]

    # Build hover template with rank
    unit_suffix = f" {unit}" if unit and unit not in ["%", "$"] else unit
    hover_template = (
        "<b>%{label}</b><br>"
        f"Value: %{{value:,.0f}}{unit_suffix}<br>"
        "Share: %{percent}<br>"
        "Rank: %{customdata[0]} of %{customdata[1]}"
        "<extra></extra>"
    )

    return {
        "data": [
            {
                "type": "pie",
                "labels": labels,
                "values": values,
                "hole": 0.4,  # Donut style
                "marker": {"colors": CHART_COLORS[: len(labels)]},
                "textinfo": "percent",
                "textposition": "outside",
                "customdata": customdata,
                "hovertemplate": hover_template,
            }
        ],
        "layout": {
            **BASE_LAYOUT,
            "title": {"text": title, "font": {"size": 14, "color": "#111827"}, "x": 0.5},
            "showlegend": True,
            "legend": {
                "orientation": "h",
                "yanchor": "top",
                "y": -0.1,
                "xanchor": "center",
                "x": 0.5,
            },
        },
    }


def generate_benchmark_chart(
    your_value: float,
    industry_median: float | None,
    industry_top_quartile: float | None,
    metric_name: str,
    unit: str = "",
) -> dict[str, Any]:
    """Generate benchmark comparison chart.

    Shows your value vs industry benchmarks in a horizontal bullet-style chart.
    """
    categories = ["Your Value"]
    values = [your_value]

    if industry_median is not None:
        categories.append("Industry Median")
        values.append(industry_median)

    if industry_top_quartile is not None:
        categories.append("Top Quartile")
        values.append(industry_top_quartile)

    colors = [CHART_COLORS[0], "#9CA3AF", "#10B981"]

    return {
        "data": [
            {
                "type": "bar",
                "x": values,
                "y": categories,
                "orientation": "h",
                "marker": {"color": colors[: len(values)]},
                "text": [f"{v:,.1f}{unit}" for v in values],
                "textposition": "outside",
                "hovertemplate": "<b>%{y}</b><br>%{x:,.2f}" + unit + "<extra></extra>",
            }
        ],
        "layout": {
            **BASE_LAYOUT,
            "title": {
                "text": f"{metric_name} Comparison",
                "font": {"size": 14, "color": "#111827"},
                "x": 0,
            },
            "xaxis": {
                **_XAXIS_DEFAULTS,
                "title": {"text": unit, "font": {"size": 12, "color": "#6B7280"}},
            },
            "yaxis": {
                **_YAXIS_DEFAULTS,
                "automargin": True,
            },
            "bargap": 0.4,
        },
    }
