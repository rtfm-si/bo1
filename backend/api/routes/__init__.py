"""API routes package for new endpoint modules.

This package contains route modules for new features that are organized
separately from the monolithic datasets.py.
"""

from backend.api.routes.dataset_folders import router as dataset_folders_router
from backend.api.routes.dataset_objective_analysis import (
    router as dataset_objective_analysis_router,
)
from backend.api.routes.objective_data_requirements import (
    router as objective_data_requirements_router,
)

__all__ = [
    "dataset_folders_router",
    "dataset_objective_analysis_router",
    "objective_data_requirements_router",
]
