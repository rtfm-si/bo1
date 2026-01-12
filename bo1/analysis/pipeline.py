"""Dataset analysis pipeline orchestrator.

Main orchestration class for the objective-aligned analysis flow,
coordinating relevance assessment, insight generation, and story synthesis.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from bo1.analysis.insights import generate_insights
from bo1.analysis.relevance import assess_relevance, determine_analysis_mode
from bo1.analysis.story import compile_data_story
from bo1.models.dataset_objective_analysis import (
    AnalysisMode,
    DatasetObjectiveAnalysis,
    RelevanceAssessment,
)
from bo1.state.database import db_session
from bo1.state.repositories import user_repository
from bo1.state.repositories.dataset_repository import DatasetRepository

logger = logging.getLogger(__name__)


class DatasetAnalysisPipeline:
    """Orchestrates the full objective-aligned analysis flow.

    This pipeline:
    1. Fetches business context from user profile
    2. Loads and profiles the dataset
    3. Assesses relevance to objectives
    4. Determines analysis mode (objective-focused vs open exploration)
    5. Generates insights aligned to objectives or patterns
    6. Compiles a data story narrative
    7. Saves and returns the result
    """

    def __init__(self) -> None:
        """Initialize the pipeline with repository access."""
        self._dataset_repo = DatasetRepository()

    async def analyze(
        self,
        dataset_id: str,
        user_id: str,
        selected_objective_id: str | None = None,
        force_mode: str | None = None,
    ) -> DatasetObjectiveAnalysis:
        """Run full analysis pipeline.

        Args:
            dataset_id: UUID of the dataset to analyze
            user_id: UUID of the user requesting analysis
            selected_objective_id: Optional pre-selected objective from
                "What Data Do I Need?" flow
            force_mode: Optional forced mode:
                - 'objective_focused': Always use objective-focused mode
                - 'open_exploration': Always use open exploration mode
                - None: Auto-detect based on relevance score

        Returns:
            DatasetObjectiveAnalysis with full analysis results

        Raises:
            ValueError: If dataset not found or not accessible
        """
        analysis_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        logger.info(
            f"Starting analysis pipeline for dataset {dataset_id[:8]}... user {user_id[:8]}..."
        )

        # 1. Fetch business context
        context = await self._fetch_business_context(user_id)
        objectives = self._extract_objectives(context, selected_objective_id)
        has_objectives = len(objectives) > 0

        # 2. Load and profile dataset
        profile = await self._load_dataset_profile(dataset_id, user_id)
        investigation = await self._load_investigation(dataset_id, user_id)

        # 3. Assess relevance to objectives
        relevance: RelevanceAssessment | None = None
        if has_objectives:
            relevance = await assess_relevance(
                profile=profile,
                objectives=objectives,
                north_star=context.get("north_star_goal") if context else None,
                industry=context.get("industry") if context else None,
                business_model=context.get("business_model") if context else None,
                dataset_name=profile.get("name"),
            )
            logger.info(f"Relevance score: {relevance.relevance_score}")
        else:
            logger.info("No objectives defined, using open exploration mode")

        # 4. Determine analysis mode
        relevance_score = relevance.relevance_score if relevance else 0
        analysis_mode = determine_analysis_mode(
            relevance_score=relevance_score,
            force_mode=force_mode,
            has_objectives=has_objectives,
        )
        logger.info(f"Analysis mode: {analysis_mode}")

        # 5. Generate insights
        insights = await generate_insights(
            profile=profile,
            context=context,
            relevance=relevance,
            investigation=investigation,
        )
        logger.info(f"Generated {len(insights)} insights")

        # 6. Compile data story
        data_quality = investigation.get("data_quality") if investigation else None
        columns = profile.get("column_profiles", profile.get("columns", []))
        data_story = await compile_data_story(
            insights=insights,
            relevance=relevance,
            data_quality=data_quality,
            context=context,
            columns=columns,
        )
        logger.info("Compiled data story")

        # 7. Build and save result
        result = DatasetObjectiveAnalysis(
            id=analysis_id,
            dataset_id=dataset_id,
            user_id=user_id,
            analysis_mode=AnalysisMode(analysis_mode),
            relevance_score=relevance_score if relevance else None,
            relevance_assessment=relevance,
            data_story=data_story,
            insights=insights,
            context_snapshot=self._create_context_snapshot(context, objectives),
            selected_objective_id=selected_objective_id,
            created_at=now,
            updated_at=now,
        )

        # Save to database
        await self._save_analysis(result)

        return result

    async def _fetch_business_context(self, user_id: str) -> dict[str, Any] | None:
        """Fetch user's business context from the database.

        Args:
            user_id: User UUID

        Returns:
            Business context dict or None if not set up
        """
        try:
            context = user_repository.get_context(user_id)
            if context:
                logger.debug(f"Loaded business context for user {user_id[:8]}...")
            else:
                logger.info(f"No business context found for user {user_id[:8]}...")
            return context
        except Exception as e:
            logger.warning(f"Error fetching business context: {e}")
            return None

    def _extract_objectives(
        self,
        context: dict[str, Any] | None,
        selected_objective_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Extract objectives from business context.

        Args:
            context: Business context dict
            selected_objective_id: Optional pre-selected objective to prioritize

        Returns:
            List of objective dicts with id, name, description, target, current
        """
        if not context:
            return []

        objectives: list[dict[str, Any]] = []

        # Extract from strategic_objectives
        strategic_objectives = context.get("strategic_objectives", [])
        if isinstance(strategic_objectives, list):
            for obj in strategic_objectives:
                if isinstance(obj, dict):
                    obj_id = obj.get("id", str(uuid.uuid4()))
                    objectives.append(
                        {
                            "id": obj_id,
                            "name": obj.get("name", obj.get("objective", "")),
                            "description": obj.get("description", ""),
                            "target": obj.get("target", obj.get("target_value", "")),
                            "current": obj.get("current", obj.get("current_value", "")),
                        }
                    )

        # Add north star as an objective if present
        north_star = context.get("north_star_goal")
        if north_star:
            objectives.insert(
                0,
                {
                    "id": "north_star",
                    "name": north_star,
                    "description": "Primary business goal",
                    "target": "",
                    "current": "",
                },
            )

        # If selected_objective_id provided, move it to front
        if selected_objective_id:
            for i, obj in enumerate(objectives):
                if obj.get("id") == selected_objective_id:
                    objectives.insert(0, objectives.pop(i))
                    break

        return objectives

    async def _load_dataset_profile(
        self,
        dataset_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Load dataset metadata and column profiles.

        Args:
            dataset_id: Dataset UUID
            user_id: User UUID for access check

        Returns:
            Profile dict with columns, sample_rows, row_count, etc.

        Raises:
            ValueError: If dataset not found or not accessible
        """
        # Get dataset metadata
        dataset = self._dataset_repo.get_by_id(dataset_id, user_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found or not accessible")

        # Get column profiles
        column_profiles = self._dataset_repo.get_profiles(dataset_id)

        # Build profile dict
        profile = {
            "name": dataset.get("name", "Unnamed"),
            "description": dataset.get("description"),
            "row_count": dataset.get("row_count", 0),
            "column_count": dataset.get("column_count", 0),
            "columns": [
                {
                    "name": col.get("column_name", ""),
                    "type": col.get("data_type", "unknown"),
                }
                for col in column_profiles
            ],
            "column_profiles": column_profiles,
            "sample_rows": self._extract_sample_rows(column_profiles),
        }

        return profile

    def _extract_sample_rows(self, column_profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract sample rows from column profiles.

        Args:
            column_profiles: List of column profile dicts with sample_values

        Returns:
            List of sample row dicts (max 5 rows)
        """
        if not column_profiles:
            return []

        # Build rows from sample values
        max_samples = 5
        rows: list[dict[str, Any]] = [{} for _ in range(max_samples)]

        for col in column_profiles:
            col_name = col.get("column_name", "")
            samples = col.get("sample_values", [])
            if isinstance(samples, list):
                for i, val in enumerate(samples[:max_samples]):
                    if i < len(rows):
                        rows[i][col_name] = val

        # Filter out empty rows
        return [r for r in rows if r]

    async def _load_investigation(
        self,
        dataset_id: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        """Load pre-computed investigation (deterministic analysis).

        Args:
            dataset_id: Dataset UUID
            user_id: User UUID for access check

        Returns:
            Investigation dict or None if not computed
        """
        try:
            investigation = self._dataset_repo.get_investigation(dataset_id, user_id)
            if investigation:
                logger.debug(f"Loaded investigation for dataset {dataset_id[:8]}...")
            return investigation
        except Exception as e:
            logger.warning(f"Error loading investigation: {e}")
            return None

    def _create_context_snapshot(
        self,
        context: dict[str, Any] | None,
        objectives: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create a snapshot of context at analysis time.

        Args:
            context: Full business context
            objectives: Extracted objectives

        Returns:
            Snapshot dict with relevant context fields
        """
        if not context:
            return {"objectives": objectives}

        return {
            "north_star_goal": context.get("north_star_goal"),
            "industry": context.get("industry"),
            "business_model": context.get("business_model"),
            "objectives": objectives,
        }

    async def _save_analysis(self, analysis: DatasetObjectiveAnalysis) -> None:
        """Save analysis result to database.

        Args:
            analysis: Complete analysis result to save
        """
        import json

        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    # Serialize models to JSON-compatible dicts
                    relevance_json = None
                    if analysis.relevance_assessment:
                        relevance_json = analysis.relevance_assessment.model_dump(mode="json")

                    data_story_json = None
                    if analysis.data_story:
                        data_story_json = analysis.data_story.model_dump(mode="json")

                    insights_json = [
                        insight.model_dump(mode="json") for insight in analysis.insights
                    ]

                    cur.execute(
                        """
                        INSERT INTO dataset_objective_analyses (
                            id, dataset_id, user_id, analysis_mode,
                            relevance_score, relevance_assessment,
                            data_story, insights, context_snapshot,
                            selected_objective_id, created_at, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            analysis_mode = EXCLUDED.analysis_mode,
                            relevance_score = EXCLUDED.relevance_score,
                            relevance_assessment = EXCLUDED.relevance_assessment,
                            data_story = EXCLUDED.data_story,
                            insights = EXCLUDED.insights,
                            context_snapshot = EXCLUDED.context_snapshot,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (
                            analysis.id,
                            analysis.dataset_id,
                            analysis.user_id,
                            analysis.analysis_mode.value,
                            analysis.relevance_score,
                            json.dumps(relevance_json) if relevance_json else None,
                            json.dumps(data_story_json) if data_story_json else None,
                            json.dumps(insights_json),
                            json.dumps(analysis.context_snapshot)
                            if analysis.context_snapshot
                            else None,
                            analysis.selected_objective_id,
                            analysis.created_at,
                            analysis.updated_at,
                        ),
                    )
                    conn.commit()

            logger.info(
                f"Saved analysis {analysis.id[:8]}... for dataset {analysis.dataset_id[:8]}..."
            )

        except Exception as e:
            logger.error(f"Error saving analysis: {e}")
            # Don't raise - analysis result is still valid even if save fails

    async def get_analysis(
        self,
        dataset_id: str,
        user_id: str,
    ) -> DatasetObjectiveAnalysis | None:
        """Retrieve existing analysis for a dataset.

        Args:
            dataset_id: Dataset UUID
            user_id: User UUID for access check

        Returns:
            DatasetObjectiveAnalysis or None if not found
        """
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, dataset_id, user_id, analysis_mode,
                               relevance_score, relevance_assessment,
                               data_story, insights, context_snapshot,
                               selected_objective_id, created_at, updated_at
                        FROM dataset_objective_analyses
                        WHERE dataset_id = %s AND user_id = %s
                        ORDER BY created_at DESC
                        LIMIT 1
                        """,
                        (dataset_id, user_id),
                    )
                    row = cur.fetchone()

            if row:
                return DatasetObjectiveAnalysis.from_db_row(dict(row))
            return None

        except Exception as e:
            logger.error(f"Error retrieving analysis: {e}")
            return None
