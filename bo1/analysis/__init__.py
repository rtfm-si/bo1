"""Data Analysis Reimagination module.

Transforms data analysis from statistics dashboards to objective-driven
insight engines that understand business goals.

Modules:
- pipeline: Main DatasetAnalysisPipeline orchestrator
- relevance: assess_relevance() for dataset-objective alignment
- insights: generate_insights() for objective-aligned insights
- story: compile_data_story() for narrative synthesis
- data_requirements: generate_data_requirements() for "What Data Do I Need?"
"""

from bo1.analysis.data_requirements import (
    generate_data_requirements,
    generate_requirements_for_objectives,
)
from bo1.analysis.insights import (
    generate_insights,
    generate_open_exploration_insights,
)
from bo1.analysis.pipeline import DatasetAnalysisPipeline
from bo1.analysis.relevance import (
    assess_relevance,
    determine_analysis_mode,
)
from bo1.analysis.story import compile_data_story

__all__ = [
    # Pipeline
    "DatasetAnalysisPipeline",
    # Relevance
    "assess_relevance",
    "determine_analysis_mode",
    # Insights
    "generate_insights",
    "generate_open_exploration_insights",
    # Story
    "compile_data_story",
    # Data Requirements
    "generate_data_requirements",
    "generate_requirements_for_objectives",
]
