"""Datasets API endpoints for data management.

Provides:
- GET /api/v1/datasets - List user's datasets
- POST /api/v1/datasets/upload - Upload CSV file
- POST /api/v1/datasets/import-sheets - Import Google Sheet
- GET /api/v1/datasets/{id} - Get dataset with profile
- DELETE /api/v1/datasets/{id} - Delete dataset and Spaces file
- POST /api/v1/datasets/{id}/ask - Q&A with SSE streaming
- GET /api/v1/datasets/{id}/conversations - List conversations
- GET /api/v1/datasets/{id}/conversations/{conv_id} - Get conversation
"""

import json
import logging
import re
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from backend.api.middleware.auth import get_current_user
from backend.api.models import (
    AskRequest,
    ChartResultResponse,
    ChartSpec,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationMessage,
    ConversationResponse,
    DatasetAnalysisListResponse,
    DatasetAnalysisResponse,
    DatasetDetailResponse,
    DatasetListResponse,
    DatasetProfileResponse,
    DatasetResponse,
    ImportSheetsRequest,
    QueryResultResponse,
    QuerySpec,
)
from backend.api.utils.errors import handle_api_errors
from backend.services.chart_generator import ChartError, generate_chart_json, generate_chart_png
from backend.services.conversation_repo import ConversationRepository
from backend.services.csv_utils import CSVValidationError, validate_csv_structure
from backend.services.dataframe_loader import DataFrameLoadError, load_dataframe
from backend.services.profiler import ProfileError, profile_dataset, save_profile
from backend.services.query_engine import QueryError, execute_query
from backend.services.spaces import SpacesError, get_spaces_client
from backend.services.summary_generator import generate_dataset_summary, invalidate_summary_cache
from bo1.llm.client import ClaudeClient
from bo1.prompts.data_analyst import (
    DATA_ANALYST_SYSTEM,
    build_analyst_prompt,
    format_clarifications_context,
    format_conversation_history,
    format_dataset_context,
)
from bo1.state.repositories.dataset_repository import DatasetRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/datasets", tags=["datasets"])

# Upload constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = [
    "text/csv",
    "application/csv",
    "text/plain",  # Some systems send CSV as text/plain
    "application/vnd.ms-excel",  # Excel sometimes sends CSV this way
]

# Singleton repository instances
dataset_repository = DatasetRepository()
conversation_repository = ConversationRepository()


def _format_dataset_response(dataset: dict[str, Any]) -> DatasetResponse:
    """Format dataset dict for API response."""
    return DatasetResponse(
        id=dataset["id"],
        user_id=dataset["user_id"],
        name=dataset["name"],
        description=dataset.get("description"),
        source_type=dataset["source_type"],
        source_uri=dataset.get("source_uri"),
        file_key=dataset.get("file_key"),
        row_count=dataset.get("row_count"),
        column_count=dataset.get("column_count"),
        file_size_bytes=dataset.get("file_size_bytes"),
        created_at=dataset["created_at"],
        updated_at=dataset["updated_at"],
    )


def _format_profile_response(profile: dict[str, Any]) -> DatasetProfileResponse:
    """Format profile dict for API response."""
    return DatasetProfileResponse(
        id=profile["id"],
        column_name=profile["column_name"],
        data_type=profile["data_type"],
        null_count=profile.get("null_count"),
        unique_count=profile.get("unique_count"),
        min_value=profile.get("min_value"),
        max_value=profile.get("max_value"),
        mean_value=profile.get("mean_value"),
        sample_values=profile.get("sample_values"),
    )


@router.get(
    "",
    response_model=DatasetListResponse,
    summary="List datasets",
    description="List all datasets for the current user",
)
@handle_api_errors("list datasets")
async def list_datasets(
    limit: int = Query(50, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
    user: dict = Depends(get_current_user),
) -> DatasetListResponse:
    """List all datasets for the current user."""
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    datasets, total = dataset_repository.list_by_user(
        user_id=user_id,
        limit=limit,
        offset=offset,
    )

    return DatasetListResponse(
        datasets=[_format_dataset_response(d) for d in datasets],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/upload",
    response_model=DatasetResponse,
    status_code=201,
    summary="Upload CSV dataset",
    description="Upload a CSV file to create a new dataset",
)
@handle_api_errors("upload dataset")
async def upload_dataset(
    file: UploadFile = File(..., description="CSV file to upload"),
    name: str = Form(..., min_length=1, max_length=255, description="Dataset name"),
    description: str | None = Form(None, max_length=5000, description="Dataset description"),
    user: dict = Depends(get_current_user),
) -> DatasetResponse:
    """Upload a CSV file to create a new dataset."""
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    # Validate content type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        # Check file extension as fallback
        filename = file.filename or ""
        if not filename.lower().endswith(".csv"):
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type: {content_type}. Please upload a CSV file.",
            )

    # Read file content with size check
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise HTTPException(status_code=422, detail="Empty file")

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({file_size / 1024 / 1024:.1f}MB). Maximum size is {MAX_FILE_SIZE / 1024 / 1024:.0f}MB.",
        )

    # Validate CSV structure
    try:
        csv_metadata = validate_csv_structure(content)
    except CSVValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None

    # Generate Spaces key
    dataset_id = str(uuid.uuid4())
    file_key = f"datasets/{user_id}/{dataset_id}.csv"

    # Upload to Spaces
    try:
        spaces_client = get_spaces_client()
        spaces_client.upload_file(
            key=file_key,
            data=content,
            content_type="text/csv",
            metadata={
                "user_id": user_id,
                "original_filename": file.filename or "upload.csv",
            },
        )
        logger.info(f"Uploaded CSV to Spaces: {file_key} ({file_size} bytes)")
    except SpacesError as e:
        logger.error(f"Failed to upload to Spaces: {e}")
        raise HTTPException(status_code=502, detail="Failed to upload file to storage") from None

    # Create dataset record
    try:
        dataset = dataset_repository.create(
            user_id=user_id,
            name=name,
            source_type="csv",
            description=description,
            file_key=file_key,
            row_count=csv_metadata.row_count,
            column_count=csv_metadata.column_count,
            file_size_bytes=file_size,
        )
    except Exception as e:
        # Cleanup Spaces file on database error
        logger.error(f"Failed to create dataset record: {e}")
        try:
            spaces_client.delete_file(file_key)
        except SpacesError:
            logger.warning(f"Failed to cleanup Spaces file after DB error: {file_key}")
        raise HTTPException(status_code=500, detail="Failed to create dataset") from None

    logger.info(f"Created dataset {dataset['id']} for user {user_id}")
    return _format_dataset_response(dataset)


@router.post(
    "/import-sheets",
    response_model=DatasetResponse,
    status_code=201,
    summary="Import Google Sheet",
    description="Import a Google Sheet as a dataset (public or private with OAuth)",
)
@handle_api_errors("import sheets")
async def import_sheets(
    request: ImportSheetsRequest,
    user: dict = Depends(get_current_user),
) -> DatasetResponse:
    """Import a Google Sheet as a dataset.

    - If user has Google Sheets connected: uses OAuth (can access private sheets)
    - Otherwise: uses API key (public sheets only)
    """
    from backend.services.sheets import SheetsError, get_oauth_sheets_client, get_sheets_client

    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    # Try OAuth client first (for private sheets), fall back to API key (public only)
    oauth_client = get_oauth_sheets_client(user_id)
    if oauth_client:
        sheets_client = oauth_client
        logger.info(f"Using OAuth client for sheets import (user {user_id})")
    else:
        try:
            sheets_client = get_sheets_client()
            logger.info(f"Using API key client for sheets import (user {user_id})")
        except SheetsError as e:
            raise HTTPException(status_code=503, detail=str(e)) from None

    # Parse URL to get spreadsheet ID
    try:
        spreadsheet_id = sheets_client.parse_sheets_url(request.url)
    except SheetsError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None

    # Fetch sheet data as CSV
    try:
        csv_content, metadata = sheets_client.fetch_as_csv(spreadsheet_id)
    except SheetsError as e:
        # Provide better error for private sheets without OAuth
        error_msg = str(e)
        if "Access denied" in error_msg and not oauth_client:
            error_msg = (
                "Access denied. This sheet may be private. "
                "Connect Google Sheets to import private spreadsheets."
            )
        raise HTTPException(status_code=422, detail=error_msg) from None

    file_size = len(csv_content)

    # Use provided name or sheet title
    name = request.name or f"{metadata.title} - {metadata.sheet_name}"

    # Generate Spaces key
    dataset_id = str(uuid.uuid4())
    file_key = f"datasets/{user_id}/{dataset_id}.csv"

    # Upload to Spaces
    try:
        spaces_client = get_spaces_client()
        spaces_client.upload_file(
            key=file_key,
            data=csv_content,
            content_type="text/csv",
            metadata={
                "user_id": user_id,
                "source": "google_sheets",
                "spreadsheet_id": spreadsheet_id,
            },
        )
        logger.info(f"Uploaded sheets import to Spaces: {file_key} ({file_size} bytes)")
    except SpacesError as e:
        logger.error(f"Failed to upload to Spaces: {e}")
        raise HTTPException(status_code=502, detail="Failed to upload file to storage") from None

    # Create dataset record
    try:
        dataset = dataset_repository.create(
            user_id=user_id,
            name=name,
            source_type="sheets",
            source_uri=request.url,
            description=request.description,
            file_key=file_key,
            row_count=metadata.row_count,
            column_count=metadata.column_count,
            file_size_bytes=file_size,
        )
    except Exception as e:
        # Cleanup Spaces file on database error
        logger.error(f"Failed to create dataset record: {e}")
        try:
            spaces_client.delete_file(file_key)
        except SpacesError:
            logger.warning(f"Failed to cleanup Spaces file after DB error: {file_key}")
        raise HTTPException(status_code=500, detail="Failed to create dataset") from None

    logger.info(f"Created sheets dataset {dataset['id']} for user {user_id} from {request.url}")
    return _format_dataset_response(dataset)


@router.get(
    "/{dataset_id}",
    response_model=DatasetDetailResponse,
    summary="Get dataset",
    description="Get dataset details with column profiles",
)
@handle_api_errors("get dataset")
async def get_dataset(
    dataset_id: str,
    user: dict = Depends(get_current_user),
) -> DatasetDetailResponse:
    """Get dataset details with column profiles."""
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Get column profiles
    profiles = dataset_repository.get_profiles(dataset_id)

    return DatasetDetailResponse(
        id=dataset["id"],
        user_id=dataset["user_id"],
        name=dataset["name"],
        description=dataset.get("description"),
        source_type=dataset["source_type"],
        source_uri=dataset.get("source_uri"),
        file_key=dataset.get("file_key"),
        row_count=dataset.get("row_count"),
        column_count=dataset.get("column_count"),
        file_size_bytes=dataset.get("file_size_bytes"),
        created_at=dataset["created_at"],
        updated_at=dataset["updated_at"],
        profiles=[_format_profile_response(p) for p in profiles],
        summary=dataset.get("summary"),
    )


@router.delete(
    "/{dataset_id}",
    status_code=204,
    summary="Delete dataset",
    description="Delete a dataset and its Spaces file",
)
@handle_api_errors("delete dataset")
async def delete_dataset(
    dataset_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    """Delete a dataset and its Spaces file."""
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    # Get dataset to retrieve file_key
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Delete file from Spaces if exists
    file_key = dataset.get("file_key")
    if file_key:
        try:
            spaces_client = get_spaces_client()
            spaces_client.delete_file(file_key)
            logger.info(f"Deleted Spaces file {file_key} for dataset {dataset_id}")
        except SpacesError as e:
            # Log but don't fail - file may already be deleted
            logger.warning(f"Failed to delete Spaces file {file_key}: {e}")

    # Soft delete dataset
    deleted = dataset_repository.delete(dataset_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")

    logger.info(f"Deleted dataset {dataset_id} for user {user_id}")


@router.post(
    "/{dataset_id}/profile",
    response_model=DatasetDetailResponse,
    summary="Profile dataset",
    description="Trigger profiling for a dataset (infer types, compute statistics)",
)
@handle_api_errors("profile dataset")
async def trigger_profile(
    dataset_id: str,
    user: dict = Depends(get_current_user),
) -> DatasetDetailResponse:
    """Trigger profiling for a dataset."""
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    # Verify ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Profile the dataset
    try:
        profile = profile_dataset(dataset_id, user_id, dataset_repository)
        save_profile(profile, dataset_repository)
    except ProfileError as e:
        logger.error(f"Failed to profile dataset {dataset_id}: {e}")
        raise HTTPException(status_code=422, detail=str(e)) from None

    # Generate summary (invalidate cache first since profile changed)
    invalidate_summary_cache(dataset_id)
    try:
        summary = await generate_dataset_summary(
            profile.to_dict(),
            dataset_name=dataset["name"],
        )
        dataset_repository.update_summary(dataset_id, user_id, summary)
    except Exception as e:
        logger.warning(f"Failed to generate summary for {dataset_id}: {e}")
        summary = None

    # Return updated dataset with profiles
    profiles = dataset_repository.get_profiles(dataset_id)

    return DatasetDetailResponse(
        id=dataset["id"],
        user_id=dataset["user_id"],
        name=dataset["name"],
        description=dataset.get("description"),
        source_type=dataset["source_type"],
        source_uri=dataset.get("source_uri"),
        file_key=dataset.get("file_key"),
        row_count=profile.row_count,
        column_count=profile.column_count,
        file_size_bytes=dataset.get("file_size_bytes"),
        created_at=dataset["created_at"],
        updated_at=dataset["updated_at"],
        profiles=[_format_profile_response(p) for p in profiles],
        summary=summary,
    )


@router.post(
    "/{dataset_id}/query",
    response_model=QueryResultResponse,
    summary="Execute query",
    description="Execute a structured query against a dataset",
)
@handle_api_errors("execute query")
async def execute_dataset_query(
    dataset_id: str,
    query: QuerySpec,
    user: dict = Depends(get_current_user),
) -> QueryResultResponse:
    """Execute a structured query against a dataset."""
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    # Verify ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Get file key
    file_key = dataset.get("file_key")
    if not file_key:
        raise HTTPException(status_code=422, detail="Dataset has no associated file")

    # Load DataFrame (no row limit for queries)
    try:
        df = load_dataframe(file_key, max_rows=None)
    except DataFrameLoadError as e:
        logger.error(f"Failed to load dataset {dataset_id}: {e}")
        raise HTTPException(status_code=502, detail="Failed to load dataset") from None

    # Execute query
    try:
        result = execute_query(df, query, dataset_id=dataset_id)
    except QueryError as e:
        logger.warning(f"Query error for dataset {dataset_id}: {e}")
        raise HTTPException(status_code=422, detail=str(e)) from None

    return QueryResultResponse(
        rows=result.rows,
        columns=result.columns,
        total_count=result.total_count,
        has_more=result.has_more,
        query_type=result.query_type,
    )


@router.post(
    "/{dataset_id}/chart",
    response_model=ChartResultResponse,
    summary="Generate chart",
    description="Generate a chart from dataset data",
)
@handle_api_errors("generate chart")
async def generate_dataset_chart(
    dataset_id: str,
    chart: ChartSpec,
    user: dict = Depends(get_current_user),
) -> ChartResultResponse:
    """Generate a chart from dataset data."""
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    # Verify ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Get file key
    file_key = dataset.get("file_key")
    if not file_key:
        raise HTTPException(status_code=422, detail="Dataset has no associated file")

    # Load DataFrame
    try:
        df = load_dataframe(file_key, max_rows=None)
    except DataFrameLoadError as e:
        logger.error(f"Failed to load dataset {dataset_id}: {e}")
        raise HTTPException(status_code=502, detail="Failed to load dataset") from None

    # Generate chart JSON
    try:
        result = generate_chart_json(df, chart)
    except ChartError as e:
        logger.warning(f"Chart error for dataset {dataset_id}: {e}")
        raise HTTPException(status_code=422, detail=str(e)) from None

    # Generate PNG and upload to Spaces
    analysis_id = None
    try:
        png_bytes = generate_chart_png(df, chart)
        chart_key = f"charts/{user_id}/{dataset_id}/{uuid.uuid4()}.png"

        spaces_client = get_spaces_client()
        spaces_client.upload_file(
            key=chart_key,
            data=png_bytes,
            content_type="image/png",
            metadata={"dataset_id": dataset_id, "user_id": user_id},
        )
        logger.info(f"Uploaded chart to Spaces: {chart_key}")

        # Save analysis record
        analysis = dataset_repository.create_analysis(
            dataset_id=dataset_id,
            user_id=user_id,
            chart_spec=chart.model_dump(),
            chart_key=chart_key,
            title=chart.title,
        )
        analysis_id = analysis.get("id")
        logger.info(f"Created analysis {analysis_id} for dataset {dataset_id}")

    except (SpacesError, ChartError) as e:
        # Log but don't fail - chart generation succeeded
        logger.warning(f"Failed to persist chart for {dataset_id}: {e}")

    return ChartResultResponse(
        figure_json=result["figure_json"],
        chart_type=result["chart_type"],
        width=result["width"],
        height=result["height"],
        row_count=result["row_count"],
        analysis_id=analysis_id,
    )


@router.get(
    "/{dataset_id}/analyses",
    response_model=DatasetAnalysisListResponse,
    summary="List analyses",
    description="List recent analyses (charts/queries) for a dataset",
)
@handle_api_errors("list analyses")
async def list_analyses(
    dataset_id: str,
    limit: int = Query(20, ge=1, le=100, description="Max analyses to return"),
    user: dict = Depends(get_current_user),
) -> DatasetAnalysisListResponse:
    """List recent analyses for a dataset."""
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    analyses = dataset_repository.list_analyses(dataset_id, user_id, limit)

    # Generate presigned URLs for chart images
    spaces_client = get_spaces_client()
    response_analyses = []
    for a in analyses:
        chart_url = None
        if a.get("chart_key"):
            try:
                chart_url = spaces_client.generate_presigned_url(
                    a["chart_key"],
                    expires_in=3600,  # 1 hour
                )
            except SpacesError:
                logger.warning(f"Failed to generate presigned URL for {a['chart_key']}")

        response_analyses.append(
            DatasetAnalysisResponse(
                id=a["id"],
                dataset_id=a["dataset_id"],
                query_spec=a.get("query_spec"),
                chart_spec=a.get("chart_spec"),
                chart_url=chart_url,
                title=a.get("title"),
                created_at=a["created_at"],
            )
        )

    return DatasetAnalysisListResponse(
        analyses=response_analyses,
        total=len(response_analyses),
    )


# =============================================================================
# Dataset Q&A Endpoints (EPIC 5)
# =============================================================================


def _parse_spec_from_response(response: str, tag: str) -> dict[str, Any] | None:
    """Extract JSON spec from XML-tagged section of LLM response.

    Args:
        response: Full LLM response text
        tag: XML tag name (e.g., "query_spec" or "chart_spec")

    Returns:
        Parsed dict or None if not found
    """
    pattern = rf"<{tag}>\s*([\s\S]*?)\s*</{tag}>"
    match = re.search(pattern, response)
    if not match:
        return None

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse {tag} JSON from response")
        return None


def _strip_specs_from_response(response: str) -> str:
    """Remove XML spec blocks from response, keeping only prose."""
    response = re.sub(r"<query_spec>[\s\S]*?</query_spec>", "", response)
    response = re.sub(r"<chart_spec>[\s\S]*?</chart_spec>", "", response)
    return response.strip()


def _extract_clarification_from_conversation(
    messages: list[dict[str, Any]],
    current_question: str,
) -> tuple[str, str] | None:
    """Extract clarification Q&A if the user is answering a prior assistant question.

    Looks at the last assistant message to see if it contained a question.
    If so, treats the current user message as the answer.

    Args:
        messages: Conversation history
        current_question: User's current message

    Returns:
        Tuple of (question_asked, user_answer) or None if not a clarification
    """
    if len(messages) < 1:
        return None

    # Get last assistant message
    last_assistant = None
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            last_assistant = msg
            break

    if not last_assistant:
        return None

    content = last_assistant.get("content", "")

    # Look for question patterns in assistant's response
    # Common patterns: ends with "?", contains "Could you", "What is", "Can you tell me", etc.
    question_patterns = [
        r"[?]\s*$",  # Ends with question mark
        r"\b(could you|can you|what is|what are|which|how many|how much|please clarify|please specify)\b",
    ]

    has_question = any(re.search(pattern, content, re.IGNORECASE) for pattern in question_patterns)

    if not has_question:
        return None

    # Extract the question (last sentence ending with ?)
    sentences = re.split(r"(?<=[.!?])\s+", content)
    question_asked = None
    for sentence in reversed(sentences):
        if "?" in sentence:
            question_asked = sentence.strip()
            break

    if question_asked:
        return (question_asked, current_question)

    return None


async def _stream_ask_response(
    dataset_id: str,
    user_id: str,
    question: str,
    conversation_id: str | None,
) -> AsyncGenerator[str, None]:
    """Stream the ask response as SSE events.

    Events:
    - thinking: Processing started
    - analysis: LLM response text
    - query: Query spec if generated
    - query_result: Query execution result
    - chart: Chart spec if generated
    - done: Processing complete with conversation_id
    - error: Error occurred
    """
    try:
        # Verify dataset ownership and get profile
        dataset = dataset_repository.get_by_id(dataset_id, user_id)
        if not dataset:
            yield f"event: error\ndata: {json.dumps({'error': 'Dataset not found'})}\n\n"
            return

        yield f"event: thinking\ndata: {json.dumps({'status': 'loading_context'})}\n\n"

        # Get or create conversation
        if conversation_id:
            conversation = conversation_repository.get(conversation_id, user_id)
            if not conversation or conversation.get("dataset_id") != dataset_id:
                yield f"event: error\ndata: {json.dumps({'error': 'Conversation not found'})}\n\n"
                return
        else:
            conversation = conversation_repository.create(dataset_id, user_id)
            conversation_id = conversation["id"]

        # Build profile context from profiles
        profiles = dataset_repository.get_profiles(dataset_id)
        profile_dict = {
            "dataset_id": dataset_id,
            "row_count": dataset.get("row_count", 0),
            "column_count": dataset.get("column_count", 0),
            "columns": [
                {
                    "name": p.get("column_name", ""),
                    "inferred_type": p.get("data_type", "unknown"),
                    "stats": {
                        "null_count": p.get("null_count"),
                        "unique_count": p.get("unique_count"),
                        "min_value": p.get("min_value"),
                        "max_value": p.get("max_value"),
                        "mean_value": p.get("mean_value"),
                    },
                }
                for p in profiles
            ],
        }

        # Format context
        dataset_context = format_dataset_context(
            profile_dict,
            dataset["name"],
            dataset.get("summary"),
        )
        conv_history = format_conversation_history(conversation.get("messages", []))

        # Load prior clarifications for context persistence
        clarifications = dataset_repository.get_clarifications(dataset_id, user_id)
        clarifications_ctx = format_clarifications_context(clarifications)

        # Build prompt
        user_prompt = build_analyst_prompt(
            question, dataset_context, conv_history, clarifications_ctx
        )

        yield f"event: thinking\ndata: {json.dumps({'status': 'calling_llm'})}\n\n"

        # Check if user is answering a clarifying question from prior message
        # If so, persist this Q&A pair for future context
        messages = conversation.get("messages", [])
        clarification_pair = _extract_clarification_from_conversation(messages, question)
        if clarification_pair:
            q_asked, user_answer = clarification_pair
            dataset_repository.add_clarification(dataset_id, user_id, q_asked, user_answer)
            logger.info(f"Saved clarification for dataset {dataset_id}: {q_asked[:50]}...")

        # Add user message to conversation
        conversation_repository.append_message(conversation_id, "user", question)

        # Call LLM
        client = ClaudeClient()
        response, usage = await client.call(
            model="sonnet",
            system=DATA_ANALYST_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=2000,
            temperature=0.3,
        )

        # Parse specs from response
        query_spec = _parse_spec_from_response(response, "query_spec")
        chart_spec = _parse_spec_from_response(response, "chart_spec")
        analysis_text = _strip_specs_from_response(response)

        # Stream analysis
        yield f"event: analysis\ndata: {json.dumps({'content': analysis_text})}\n\n"

        # Execute query if spec provided
        query_result = None
        if query_spec:
            yield f"event: query\ndata: {json.dumps({'spec': query_spec})}\n\n"

            try:
                file_key = dataset.get("file_key")
                if file_key:
                    df = load_dataframe(file_key, max_rows=None)
                    # Convert spec to QuerySpec model
                    query_model = QuerySpec(**query_spec)
                    result = execute_query(df, query_model, dataset_id=dataset_id)
                    query_result = {
                        "rows": result.rows[:10],  # Limit for context
                        "columns": result.columns,
                        "total_count": result.total_count,
                    }
                    yield f"event: query_result\ndata: {json.dumps(query_result)}\n\n"
            except (DataFrameLoadError, QueryError) as e:
                logger.warning(f"Query execution failed: {e}")
                yield f"event: query_result\ndata: {json.dumps({'error': str(e)})}\n\n"

        # Return chart spec if provided
        if chart_spec:
            yield f"event: chart\ndata: {json.dumps({'spec': chart_spec})}\n\n"

        # Save assistant response to conversation
        conversation_repository.append_message(
            conversation_id,
            "assistant",
            analysis_text,
            query_spec=query_spec,
            chart_spec=chart_spec,
            query_result=query_result,
        )

        # Done event with conversation ID
        yield f"event: done\ndata: {json.dumps({'conversation_id': conversation_id, 'tokens': usage.total_tokens})}\n\n"

    except Exception as e:
        logger.error(f"Error in ask stream for dataset {dataset_id}: {e}")
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


@router.post(
    "/{dataset_id}/ask",
    summary="Ask a question about the dataset",
    description="Natural language Q&A with SSE streaming",
    responses={
        200: {
            "description": "SSE event stream",
            "content": {
                "text/event-stream": {"example": 'event: analysis\ndata: {"content": "..."}\n\n'}
            },
        },
    },
)
async def ask_dataset(
    dataset_id: str,
    request: AskRequest,
    user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Ask a natural language question about the dataset.

    Returns SSE events: thinking, analysis, query, query_result, chart, done, error.
    """
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    return StreamingResponse(
        _stream_ask_response(
            dataset_id,
            user_id,
            request.question,
            request.conversation_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/{dataset_id}/conversations",
    response_model=ConversationListResponse,
    summary="List conversations",
    description="List recent Q&A conversations for a dataset",
)
@handle_api_errors("list conversations")
async def list_conversations(
    dataset_id: str,
    limit: int = Query(20, ge=1, le=100, description="Max conversations to return"),
    user: dict = Depends(get_current_user),
) -> ConversationListResponse:
    """List recent Q&A conversations for a dataset."""
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    conversations = conversation_repository.list_by_dataset(dataset_id, user_id, limit)

    return ConversationListResponse(
        conversations=[
            ConversationResponse(
                id=c["id"],
                dataset_id=c["dataset_id"],
                created_at=c["created_at"],
                updated_at=c["updated_at"],
                message_count=c["message_count"],
            )
            for c in conversations
        ],
        total=len(conversations),
    )


@router.get(
    "/{dataset_id}/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get conversation",
    description="Get a conversation with full message history",
)
@handle_api_errors("get conversation")
async def get_conversation(
    dataset_id: str,
    conversation_id: str,
    user: dict = Depends(get_current_user),
) -> ConversationDetailResponse:
    """Get a conversation with full message history."""
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    conversation = conversation_repository.get(conversation_id, user_id)
    if not conversation or conversation.get("dataset_id") != dataset_id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationDetailResponse(
        id=conversation["id"],
        dataset_id=conversation["dataset_id"],
        created_at=conversation["created_at"],
        updated_at=conversation["updated_at"],
        message_count=len(conversation.get("messages", [])),
        messages=[
            ConversationMessage(
                role=m["role"],
                content=m["content"],
                timestamp=m["timestamp"],
                query_spec=m.get("query_spec"),
                chart_spec=m.get("chart_spec"),
                query_result=m.get("query_result"),
            )
            for m in conversation.get("messages", [])
        ],
    )


@router.delete(
    "/{dataset_id}/conversations/{conversation_id}",
    status_code=204,
    summary="Delete conversation",
    description="Delete a Q&A conversation",
)
@handle_api_errors("delete conversation")
async def delete_conversation(
    dataset_id: str,
    conversation_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    """Delete a Q&A conversation."""
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    deleted = conversation_repository.delete(conversation_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
