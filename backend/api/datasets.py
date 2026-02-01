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

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rate_limit import UPLOAD_RATE_LIMIT, limiter
from backend.api.middleware.tier_limits import record_dataset_usage, require_dataset_limit
from backend.api.models import (
    AllReportItem,
    AllReportsListResponse,
    AskRequest,
    ChartResultResponse,
    ChartSpec,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationMessage,
    ConversationResponse,
    DatasetAnalysisListResponse,
    DatasetAnalysisResponse,
    DatasetBusinessContextCreate,
    DatasetBusinessContextResponse,
    DatasetComparisonCreate,
    DatasetComparisonListResponse,
    DatasetComparisonResponse,
    DatasetDetailResponse,
    DatasetFavouriteCreate,
    DatasetFavouriteListResponse,
    DatasetFavouriteResponse,
    DatasetFavouriteUpdate,
    DatasetFixRequest,
    DatasetFixResponse,
    DatasetInsightsResponse,
    DatasetInvestigationResponse,
    DatasetListResponse,
    DatasetProfileResponse,
    DatasetReportCreate,
    DatasetReportListResponse,
    DatasetReportResponse,
    DatasetResponse,
    DatasetUpdate,
    FavouriteType,
    ImportSheetsRequest,
    MultiDatasetAnalysisCreate,
    MultiDatasetAnalysisListResponse,
    MultiDatasetAnalysisResponse,
    MultiDatasetAnomaly,
    MultiDatasetCommonSchema,
    MultiDatasetSummary,
    PiiWarning,
    QueryResultResponse,
    QuerySpec,
    ReportSection,
    SimilarDatasetItem,
    SimilarDatasetsResponse,
    UpdateColumnDescriptionRequest,
)
from backend.api.utils import RATE_LIMIT_RESPONSE
from backend.api.utils.errors import handle_api_errors, http_error
from backend.api.utils.pagination import make_pagination_fields
from backend.services.antivirus import ClamAVError, ScanStatus, scan_upload
from backend.services.chart_generator import ChartError, generate_chart_json, generate_chart_png
from backend.services.conversation_repo import ConversationRepository
from backend.services.csv_utils import CSVValidationError, validate_csv_structure
from backend.services.dataframe_loader import DataFrameLoadError, load_dataframe
from backend.services.dataset_comparator import compare_datasets
from backend.services.deterministic_analyzer import run_investigation
from backend.services.insight_generator import (
    generate_dataset_insights,
    generate_enhanced_insights,
    invalidate_insight_cache,
)
from backend.services.multi_dataset_analyzer import analyze_multiple_datasets
from backend.services.pii_detector import PiiWarning as PiiWarningData
from backend.services.pii_detector import detect_pii_in_csv
from backend.services.profiler import ProfileError, profile_dataset, save_profile
from backend.services.query_engine import QueryError, execute_query
from backend.services.spaces import SpacesConfigurationError, SpacesError, get_spaces_client
from backend.services.summary_generator import generate_dataset_summary, invalidate_summary_cache
from backend.services.usage_tracking import UsageResult
from bo1.datasets.cleaning import (
    CleaningError,
    fill_nulls,
    remove_duplicates,
    remove_null_rows,
    trim_whitespace,
)
from bo1.llm.client import ClaudeClient
from bo1.logging.errors import ErrorCode, log_error
from bo1.prompts.data_analyst import (
    DATA_ANALYST_SYSTEM,
    build_analyst_prompt,
    format_business_context,
    format_clarifications_context,
    format_conversation_history,
    format_dataset_context,
)
from bo1.security import sanitize_for_prompt
from bo1.state.repositories.dataset_repository import DatasetRepository
from bo1.state.repositories.user_repository import UserRepository

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
user_repository = UserRepository()


def _format_pii_warnings(pii_warnings: list[PiiWarningData] | None) -> list[PiiWarning] | None:
    """Convert PII detection warnings to API response format."""
    if not pii_warnings:
        return None
    return [
        PiiWarning(
            column_name=w.column_name,
            pii_type=w.pii_type.value,
            confidence=w.confidence,
            sample_values=w.sample_values,
            match_count=w.match_count,
        )
        for w in pii_warnings
    ]


def _format_dataset_response(
    dataset: dict[str, Any],
    warnings: list[str] | None = None,
    pii_warnings: list[PiiWarningData] | None = None,
) -> DatasetResponse:
    """Format dataset dict for API response."""
    return DatasetResponse(
        id=dataset["id"],
        user_id=dataset["user_id"],
        name=dataset["name"],
        description=dataset.get("description"),
        source_type=dataset["source_type"],
        source_uri=dataset.get("source_uri"),
        file_key=dataset.get("file_key"),
        storage_path=dataset.get("storage_path"),
        row_count=dataset.get("row_count"),
        column_count=dataset.get("column_count"),
        file_size_bytes=dataset.get("file_size_bytes"),
        created_at=dataset["created_at"],
        updated_at=dataset["updated_at"],
        warnings=warnings,
        pii_warnings=_format_pii_warnings(pii_warnings),
        pii_acknowledged_at=dataset.get("pii_acknowledged_at"),
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
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    datasets, total = dataset_repository.list_by_user(
        user_id=user_id,
        limit=limit,
        offset=offset,
    )

    return DatasetListResponse(
        datasets=[_format_dataset_response(d) for d in datasets],
        **make_pagination_fields(total, limit, offset),
    )


@router.get(
    "/reports",
    response_model=AllReportsListResponse,
    summary="List all data reports",
    description="List all data analysis reports for the current user across all datasets",
)
@handle_api_errors("list all reports")
async def list_all_reports(
    limit: int = Query(50, ge=1, le=100, description="Page size"),
    user: dict = Depends(get_current_user),
) -> AllReportsListResponse:
    """List all data analysis reports across all datasets."""
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    reports = dataset_repository.list_all_reports(user_id=user_id, limit=limit)

    return AllReportsListResponse(
        reports=[
            AllReportItem(
                id=r["id"],
                dataset_id=r.get("dataset_id"),  # Can be None if dataset deleted
                dataset_name=r.get("dataset_name"),  # Can be None if dataset deleted
                title=r["title"],
                executive_summary=r.get("executive_summary"),
                created_at=r["created_at"],
            )
            for r in reports
        ],
        total=len(reports),
    )


@router.get(
    "/reports/{report_id}",
    response_model=DatasetReportResponse,
    summary="Get report by ID",
    description="Get a specific report by ID. Supports orphaned reports where dataset was deleted.",
)
@handle_api_errors("get report by id")
async def get_report_by_id(
    report_id: str,
    user: dict = Depends(get_current_user),
) -> DatasetReportResponse:
    """Get a report by ID without requiring dataset_id.

    Supports orphaned reports where the dataset has been deleted.
    """
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    report = dataset_repository.get_report(report_id, user_id)
    if not report:
        raise http_error(ErrorCode.API_NOT_FOUND, "Report not found", status=404)

    # Get favourites for rendering charts (may be empty if dataset deleted)
    favourites = dataset_repository.get_favourites_by_ids(report["favourite_ids"], user_id)

    return DatasetReportResponse(
        id=report["id"],
        dataset_id=report.get("dataset_id"),
        title=report["title"],
        executive_summary=report.get("executive_summary"),
        sections=[ReportSection(**s) for s in report["report_content"].get("sections", [])],
        favourite_ids=report["favourite_ids"],
        favourites=[
            DatasetFavouriteResponse(
                id=f["id"],
                dataset_id=f["dataset_id"],
                favourite_type=FavouriteType(f["favourite_type"]),
                analysis_id=f.get("analysis_id"),
                message_id=f.get("message_id"),
                insight_data=f.get("insight_data"),
                title=f.get("title"),
                content=f.get("content"),
                chart_spec=f.get("chart_spec"),
                figure_json=f.get("figure_json"),
                user_note=f.get("user_note"),
                sort_order=f.get("sort_order", 0),
                created_at=f["created_at"],
            )
            for f in favourites
        ],
        model_used=report.get("model_used"),
        tokens_used=report.get("tokens_used"),
        created_at=report["created_at"],
    )


@router.post(
    "/upload",
    response_model=DatasetResponse,
    status_code=201,
    summary="Upload CSV dataset",
    description="Upload a CSV file to create a new dataset. Rate limited to 10 uploads per hour per IP.",
    responses={429: RATE_LIMIT_RESPONSE},
)
@limiter.limit(UPLOAD_RATE_LIMIT)
@handle_api_errors("upload dataset")
async def upload_dataset(
    request: Request,
    file: UploadFile = File(..., description="CSV file to upload"),
    name: str = Form(..., min_length=1, max_length=255, description="Dataset name"),
    description: str | None = Form(None, max_length=5000, description="Dataset description"),
    user: dict = Depends(get_current_user),
    tier_usage: UsageResult = Depends(require_dataset_limit),
) -> DatasetResponse:
    """Upload a CSV file to create a new dataset."""
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Validate content type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        # Check file extension as fallback
        filename = file.filename or ""
        if not filename.lower().endswith(".csv"):
            raise http_error(
                ErrorCode.VALIDATION_ERROR,
                f"Unsupported file type: {content_type}. Please upload a CSV file.",
                status=415,
            )

    # Read file content with size check
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise http_error(ErrorCode.VALIDATION_ERROR, "Empty file", status=422)

    if file_size > MAX_FILE_SIZE:
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            f"File too large ({file_size / 1024 / 1024:.1f}MB). Maximum size is {MAX_FILE_SIZE / 1024 / 1024:.0f}MB.",
            status=413,
        )

    # Validate CSV structure
    try:
        csv_metadata = validate_csv_structure(content)
    except CSVValidationError as e:
        raise http_error(ErrorCode.VALIDATION_ERROR, str(e), status=422) from None

    # Detect potential PII in the CSV (non-blocking - returns warnings)
    pii_warnings = detect_pii_in_csv(content)
    if pii_warnings:
        logger.info(
            f"PII detection found {len(pii_warnings)} potential PII columns in upload from user {user_id}"
        )

    # Generate Spaces key with user_id prefix for organization (needed for pending scan tracking)
    dataset_id = str(uuid.uuid4())
    storage_prefix = f"datasets/{user_id}"
    storage_filename = f"{dataset_id}.csv"
    file_key = f"{storage_prefix}/{storage_filename}"

    # Scan for malware before storage
    try:
        scan_result = await scan_upload(
            content,
            file.filename or "upload.csv",
            user_id=user_id,
            content_type=content_type,
            source_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            file_key=file_key,  # For pending scan tracking if ClamAV unavailable
        )
        if scan_result.status == ScanStatus.INFECTED:
            logger.warning(
                f"Malware detected in upload from user {user_id}: {scan_result.threat_name}"
            )
            raise http_error(
                ErrorCode.VALIDATION_ERROR,
                "File rejected: malware detected",
                status=400,
                threat_name=scan_result.threat_name,
            )
        # PENDING status means ClamAV was unavailable - file will be scanned later
        if scan_result.status == ScanStatus.PENDING:
            logger.info(f"File {file_key} queued for pending scan (ClamAV unavailable)")
    except ClamAVError as e:
        # ClamAV required but unavailable - block upload
        log_error(
            logger,
            ErrorCode.SERVICE_UNAVAILABLE,
            f"ClamAV scan failed: {e}",
            user_id=user_id,
            filename=file.filename,
        )
        raise http_error(
            ErrorCode.SERVICE_UNAVAILABLE,
            "File scanning service unavailable. Please try again later.",
            status=503,
        ) from None

    # Upload to Spaces using new put_file method
    try:
        spaces_client = get_spaces_client()
        spaces_client.put_file(
            prefix=storage_prefix,
            filename=storage_filename,
            data=content,
            content_type="text/csv",
            metadata={
                "user_id": user_id,
                "original_filename": file.filename or "upload.csv",
            },
        )
        logger.info(f"Uploaded CSV to Spaces: {file_key} ({file_size} bytes)")
    except SpacesConfigurationError as e:
        # Credentials not configured - admin issue
        log_error(
            logger,
            ErrorCode.CONFIG_ERROR,
            f"Spaces not configured: {e}",
            user_id=user_id,
        )
        raise http_error(
            ErrorCode.CONFIG_ERROR,
            "File storage service is not configured. Please contact support.",
            status=503,
        ) from None
    except SpacesError as e:
        log_error(
            logger,
            ErrorCode.EXT_SPACES_ERROR,
            f"Failed to upload to Spaces: {e}",
            user_id=user_id,
            file_key=file_key,
        )
        raise http_error(
            ErrorCode.EXT_SPACES_ERROR, "Failed to upload file to storage", status=502
        ) from None

    # Create dataset record with storage_path for future hierarchical access
    try:
        dataset = dataset_repository.create(
            user_id=user_id,
            name=name,
            source_type="csv",
            description=description,
            file_key=file_key,
            storage_path=storage_prefix,
            row_count=csv_metadata.row_count,
            column_count=csv_metadata.column_count,
            file_size_bytes=file_size,
        )
    except Exception as e:
        # Cleanup Spaces file on database error
        log_error(
            logger,
            ErrorCode.DB_WRITE_ERROR,
            f"Failed to create dataset record: {e}",
            user_id=user_id,
            file_key=file_key,
        )
        try:
            spaces_client.delete_file(file_key)
        except SpacesError:
            logger.warning(f"Failed to cleanup Spaces file after DB error: {file_key}")
        raise http_error(ErrorCode.DB_WRITE_ERROR, "Failed to create dataset", status=500) from None

    logger.info(f"Created dataset {dataset['id']} for user {user_id}")

    # Record dataset usage for tier tracking
    try:
        record_dataset_usage(user_id)
    except Exception as e:
        # Non-blocking - log and continue
        logger.debug(f"Usage tracking failed (non-blocking): {e}")

    return _format_dataset_response(
        dataset, warnings=csv_metadata.warnings, pii_warnings=pii_warnings
    )


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
    from backend.services.sheets import SheetsError, get_oauth_sheets_client

    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Require OAuth - user must connect Google Drive first
    sheets_client = get_oauth_sheets_client(user_id)
    if not sheets_client:
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            "Please connect Google Drive first to import spreadsheets.",
            status=400,
        )

    # Parse URL to get spreadsheet ID
    try:
        spreadsheet_id = sheets_client.parse_sheets_url(request.url)
    except SheetsError as e:
        raise http_error(ErrorCode.VALIDATION_ERROR, str(e), status=422) from None

    # Fetch sheet data as CSV
    try:
        csv_content, metadata = sheets_client.fetch_as_csv(spreadsheet_id)
    except SheetsError as e:
        raise http_error(ErrorCode.VALIDATION_ERROR, str(e), status=422) from None

    file_size = len(csv_content)

    # Use provided name or sheet title
    name = request.name or f"{metadata.title} - {metadata.sheet_name}"

    # Generate Spaces key with user_id prefix
    dataset_id = str(uuid.uuid4())
    storage_prefix = f"datasets/{user_id}"
    filename = f"{dataset_id}.csv"
    file_key = f"{storage_prefix}/{filename}"

    # Upload to Spaces using new put_file method
    try:
        spaces_client = get_spaces_client()
        spaces_client.put_file(
            prefix=storage_prefix,
            filename=filename,
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
        log_error(
            logger,
            ErrorCode.EXT_SPACES_ERROR,
            f"Failed to upload to Spaces: {e}",
            user_id=user_id,
            file_key=file_key,
        )
        raise http_error(
            ErrorCode.EXT_SPACES_ERROR, "Failed to upload file to storage", status=502
        ) from None

    # Create dataset record with storage_path
    try:
        dataset = dataset_repository.create(
            user_id=user_id,
            name=name,
            source_type="sheets",
            source_uri=request.url,
            description=request.description,
            file_key=file_key,
            storage_path=storage_prefix,
            row_count=metadata.row_count,
            column_count=metadata.column_count,
            file_size_bytes=file_size,
        )
    except Exception as e:
        # Cleanup Spaces file on database error
        log_error(
            logger,
            ErrorCode.DB_WRITE_ERROR,
            f"Failed to create dataset record: {e}",
            user_id=user_id,
            file_key=file_key,
        )
        try:
            spaces_client.delete_file(file_key)
        except SpacesError:
            logger.warning(f"Failed to cleanup Spaces file after DB error: {file_key}")
        raise http_error(ErrorCode.DB_WRITE_ERROR, "Failed to create dataset", status=500) from None

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
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

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


@router.patch(
    "/{dataset_id}",
    response_model=DatasetResponse,
    summary="Update dataset",
    description="Update dataset name and/or description",
)
@handle_api_errors("update dataset")
async def update_dataset(
    dataset_id: str,
    body: DatasetUpdate,
    user: dict = Depends(get_current_user),
) -> DatasetResponse:
    """Update dataset metadata (name, description)."""
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Check if at least one field is provided
    if body.name is None and body.description is None:
        raise http_error(
            ErrorCode.API_INVALID_REQUEST,
            "At least one of 'name' or 'description' must be provided",
            status=400,
        )

    # Update dataset
    updated = dataset_repository.update_dataset(
        dataset_id=dataset_id,
        user_id=user_id,
        name=body.name,
        description=body.description,
    )

    if not updated:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    return DatasetResponse(
        id=updated["id"],
        user_id=updated["user_id"],
        name=updated["name"],
        description=updated.get("description"),
        source_type=updated["source_type"],
        source_uri=updated.get("source_uri"),
        file_key=updated.get("file_key"),
        row_count=updated.get("row_count"),
        column_count=updated.get("column_count"),
        file_size_bytes=updated.get("file_size_bytes"),
        created_at=updated["created_at"],
        updated_at=updated["updated_at"],
    )


@router.post(
    "/{dataset_id}/acknowledge-pii",
    response_model=DatasetResponse,
    summary="Acknowledge PII warning",
    description="Acknowledge that the dataset has been reviewed for PII",
)
@handle_api_errors("acknowledge PII")
async def acknowledge_pii(
    dataset_id: str,
    user: dict = Depends(get_current_user),
) -> DatasetResponse:
    """Acknowledge PII warning for a dataset.

    Users must acknowledge they have reviewed the data for PII
    before the dataset can be used for analysis.
    """
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Update dataset with acknowledgment timestamp
    updated = dataset_repository.acknowledge_pii(dataset_id=dataset_id, user_id=user_id)

    if not updated:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    return _format_dataset_response(updated)


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
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Get dataset to retrieve file_key
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

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
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

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
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    # Profile the dataset
    try:
        profile = profile_dataset(dataset_id, user_id, dataset_repository)
        save_profile(profile, dataset_repository)
    except ProfileError as e:
        log_error(
            logger,
            ErrorCode.SERVICE_ANALYSIS_ERROR,
            f"Failed to profile dataset {dataset_id}: {e}",
            dataset_id=dataset_id,
            user_id=user_id,
        )
        raise http_error(ErrorCode.SERVICE_ANALYSIS_ERROR, str(e), status=422) from None

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

    # Auto-trigger investigation after successful profiling
    file_key = dataset.get("file_key")
    if file_key:
        try:
            df = load_dataframe(file_key)
            investigation = run_investigation(df)
            investigation_dict = investigation.to_dict()
            dataset_repository.save_investigation(dataset_id, user_id, investigation_dict)
            logger.info(f"Auto-investigation completed for dataset {dataset_id}")
        except Exception as e:
            # Don't fail profiling if investigation fails
            logger.warning(f"Auto-investigation failed for {dataset_id}: {e}")

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
    "/{dataset_id}/fix",
    response_model=DatasetFixResponse,
    summary="Fix data quality issues",
    description="""
    Apply a data cleaning action to fix quality issues in a dataset.

    Available actions:
    - **remove_duplicates**: Remove duplicate rows. Config: {keep: 'first'|'last', subset: ['col1']}
    - **fill_nulls**: Fill null values in a column. Config: {column: 'col', strategy: 'mean'|'median'|'mode'|'zero'|'value', fill_value: 'x'}
    - **remove_nulls**: Remove rows with null values. Config: {columns: ['col1'], how: 'any'|'all'}
    - **trim_whitespace**: Trim whitespace from string columns. No config needed.

    After applying a fix, the dataset file is updated and re-profiled automatically.
    The response indicates whether re-analysis is recommended.
    """,
)
@handle_api_errors("fix dataset")
async def fix_dataset(
    dataset_id: str,
    body: DatasetFixRequest,
    user: dict = Depends(get_current_user),
) -> DatasetFixResponse:
    """Apply data cleaning action to fix quality issues."""
    import io

    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    file_key = dataset.get("file_key")
    if not file_key:
        raise http_error(
            ErrorCode.API_INVALID_REQUEST,
            "Dataset has no file to modify",
            status=400,
        )

    # Load dataset
    try:
        df = load_dataframe(file_key, max_rows=None, sanitize=False)
    except DataFrameLoadError as e:
        log_error(
            logger,
            ErrorCode.SERVICE_ANALYSIS_ERROR,
            f"Failed to load dataset for fixing: {e}",
            dataset_id=dataset_id,
            user_id=user_id,
        )
        raise http_error(
            ErrorCode.SERVICE_ANALYSIS_ERROR, f"Failed to load dataset: {e}", status=422
        ) from None

    original_row_count = len(df)
    config = body.config or {}

    # Apply the requested action
    try:
        if body.action.value == "remove_duplicates":
            df_clean, stats = remove_duplicates(
                df,
                keep=config.get("keep", "first"),
                subset=config.get("subset"),
            )
            rows_affected = stats["rows_removed"]
            message = f"Removed {rows_affected} duplicate rows"

        elif body.action.value == "fill_nulls":
            column = config.get("column")
            if not column:
                raise http_error(
                    ErrorCode.API_INVALID_REQUEST,
                    "fill_nulls requires 'column' in config",
                    status=400,
                )
            df_clean, stats = fill_nulls(
                df,
                column=column,
                strategy=config.get("strategy", "mean"),
                fill_value=config.get("fill_value"),
            )
            rows_affected = stats["nulls_filled"]
            message = f"Filled {rows_affected} null values in '{column}' using {stats['strategy']}"

        elif body.action.value == "remove_nulls":
            df_clean, stats = remove_null_rows(
                df,
                columns=config.get("columns"),
                how=config.get("how", "any"),
            )
            rows_affected = stats["rows_removed"]
            message = f"Removed {rows_affected} rows with null values"

        elif body.action.value == "trim_whitespace":
            df_clean, stats = trim_whitespace(df)
            rows_affected = stats["cells_trimmed"]
            message = f"Trimmed whitespace in {rows_affected} cells across {len(stats['columns_affected'])} columns"

        else:
            raise http_error(
                ErrorCode.API_INVALID_REQUEST,
                f"Unknown action: {body.action.value}",
                status=400,
            )

    except CleaningError as e:
        log_error(
            logger,
            ErrorCode.SERVICE_ANALYSIS_ERROR,
            f"Cleaning error: {e}",
            dataset_id=dataset_id,
            user_id=user_id,
            action=body.action.value,
        )
        raise http_error(ErrorCode.SERVICE_ANALYSIS_ERROR, str(e), status=422) from None

    new_row_count = len(df_clean)

    # If no changes were made, return early
    if rows_affected == 0:
        return DatasetFixResponse(
            success=True,
            rows_affected=0,
            new_row_count=new_row_count,
            reanalysis_required=False,
            message="No changes needed - data already clean",
            stats=stats,
        )

    # Save updated file to Spaces
    try:
        csv_buffer = io.BytesIO()
        df_clean.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue()

        spaces_client = get_spaces_client()
        # Overwrite existing file
        spaces_client._client.put_object(
            Bucket=spaces_client.bucket,
            Key=file_key,
            Body=csv_content,
            ContentType="text/csv",
            Metadata={
                "user_id": user_id,
                "action_applied": body.action.value,
            },
        )
        logger.info(f"Updated dataset file {file_key} after {body.action.value}")
    except SpacesError as e:
        log_error(
            logger,
            ErrorCode.EXT_SPACES_ERROR,
            f"Failed to save fixed dataset: {e}",
            dataset_id=dataset_id,
            user_id=user_id,
        )
        raise http_error(
            ErrorCode.EXT_SPACES_ERROR,
            "Failed to save updated dataset",
            status=502,
        ) from None

    # Update row count in database
    dataset_repository.update_row_count(dataset_id, user_id, new_row_count)

    # Invalidate caches since data changed
    invalidate_summary_cache(dataset_id)
    invalidate_insight_cache(dataset_id)

    # Re-run profiling
    try:
        profile = profile_dataset(dataset_id, user_id, dataset_repository)
        save_profile(profile, dataset_repository)
        logger.info(f"Re-profiled dataset {dataset_id} after fix")
    except ProfileError as e:
        logger.warning(f"Failed to re-profile after fix: {e}")

    # Re-run investigation
    try:
        investigation = run_investigation(df_clean)
        investigation_dict = investigation.to_dict()
        dataset_repository.save_investigation(dataset_id, user_id, investigation_dict)
        logger.info(f"Re-investigated dataset {dataset_id} after fix")
    except Exception as e:
        logger.warning(f"Failed to re-investigate after fix: {e}")

    logger.info(
        f"Fixed dataset {dataset_id}: {body.action.value} affected {rows_affected} rows "
        f"({original_row_count} -> {new_row_count})"
    )

    return DatasetFixResponse(
        success=True,
        rows_affected=rows_affected,
        new_row_count=new_row_count,
        reanalysis_required=True,
        message=message,
        stats=stats,
    )


@router.get(
    "/{dataset_id}/insights",
    response_model=DatasetInsightsResponse,
    summary="Get dataset insights",
    description="Get structured business intelligence for a dataset",
)
@handle_api_errors("get dataset insights")
async def get_dataset_insights(
    dataset_id: str,
    regenerate: bool = Query(False, description="Force regeneration (bypass cache)"),
    user: dict = Depends(get_current_user),
) -> DatasetInsightsResponse:
    """Get structured business intelligence for a dataset.

    Returns actionable insights including:
    - Data identity (what this data represents)
    - Headline metrics (key numbers at a glance)
    - Business insights (trends, patterns, risks)
    - Data quality assessment
    - Suggested questions to explore
    - Column-level semantic understanding
    """
    from datetime import UTC, datetime

    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    # Get profiles
    profiles = dataset_repository.get_profiles(dataset_id)
    if not profiles:
        # Return empty response with message instead of error
        return DatasetInsightsResponse(
            insights=None,
            generated_at=datetime.now(UTC).isoformat(),
            model_used="none",
            tokens_used=0,
            cached=False,
            message="Dataset not profiled yet. Click 'Generate Profile' to analyze this dataset first.",
        )

    # Build profile dict for insight generator
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
                    "sample_values": p.get("sample_values", []),
                },
            }
            for p in profiles
        ],
    }

    # Invalidate cache if regenerating
    if regenerate:
        invalidate_insight_cache(dataset_id)

    # Generate insights
    try:
        insights, metadata = await generate_dataset_insights(
            profile_dict,
            dataset_name=dataset["name"],
            use_cache=not regenerate,
        )
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_ANALYSIS_ERROR,
            f"Failed to generate insights for {dataset_id}: {e}",
            dataset_id=dataset_id,
            user_id=user_id,
        )
        raise http_error(
            ErrorCode.SERVICE_ANALYSIS_ERROR,
            "Failed to generate insights",
            status=500,
        ) from None

    return DatasetInsightsResponse(
        insights=insights,
        generated_at=datetime.now(UTC).isoformat(),
        model_used=metadata.get("model_used", "sonnet"),
        tokens_used=metadata.get("tokens_used", 0),
        cached=metadata.get("cached", False),
    )


@router.get(
    "/{dataset_id}/enhanced-insights",
    response_model=DatasetInsightsResponse,
    summary="Get enhanced insights",
    description="Get insights enhanced with investigation findings and business context",
)
@handle_api_errors("get enhanced insights")
async def get_enhanced_insights(
    dataset_id: str,
    regenerate: bool = Query(False, description="Force regeneration (bypass cache)"),
    user: dict = Depends(get_current_user),
) -> DatasetInsightsResponse:
    """Get enhanced insights using investigation data and business context.

    This endpoint generates richer insights by combining:
    - Dataset profile (column types, statistics)
    - Investigation findings (column roles, outliers, correlations, data quality)
    - Business context (user's goals, KPIs, objectives)
    """
    from datetime import UTC, datetime

    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    # Get profiles
    profiles = dataset_repository.get_profiles(dataset_id)
    if not profiles:
        return DatasetInsightsResponse(
            insights=None,
            generated_at=datetime.now(UTC).isoformat(),
            model_used="none",
            tokens_used=0,
            cached=False,
            message="Dataset not profiled yet. Generate a profile first.",
        )

    # Build profile dict
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
                    "sample_values": p.get("sample_values", []),
                },
            }
            for p in profiles
        ],
    }

    # Get investigation (may be None)
    investigation_data = dataset_repository.get_investigation(dataset_id, user_id)
    investigation = None
    if investigation_data:
        investigation = {
            "column_roles": investigation_data.get("column_roles"),
            "missingness": investigation_data.get("missingness"),
            "descriptive_stats": investigation_data.get("descriptive_stats"),
            "outliers": investigation_data.get("outliers"),
            "correlations": investigation_data.get("correlations"),
            "time_series_readiness": investigation_data.get("time_series_readiness"),
            "segmentation_builder": investigation_data.get("segmentation_builder"),
            "data_quality": investigation_data.get("data_quality"),
        }

    # Get business context (may be None)
    context_data = dataset_repository.get_business_context(dataset_id, user_id)
    business_context = None
    if context_data:
        business_context = {
            "business_goal": context_data.get("business_goal"),
            "key_metrics": context_data.get("key_metrics"),
            "kpis": context_data.get("kpis"),
            "objectives": context_data.get("objectives"),
            "industry": context_data.get("industry"),
            "additional_context": context_data.get("additional_context"),
        }

    # Invalidate cache if regenerating
    if regenerate:
        invalidate_insight_cache(dataset_id)

    # Generate enhanced insights
    try:
        insights, metadata = await generate_enhanced_insights(
            profile_dict,
            dataset_name=dataset["name"],
            investigation=investigation,
            business_context=business_context,
            use_cache=not regenerate,
        )
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_ANALYSIS_ERROR,
            f"Failed to generate enhanced insights for {dataset_id}: {e}",
            dataset_id=dataset_id,
            user_id=user_id,
        )
        raise http_error(
            ErrorCode.SERVICE_ANALYSIS_ERROR,
            "Failed to generate insights. Please try again.",
            status=500,
        ) from None

    return DatasetInsightsResponse(
        insights=insights,
        generated_at=datetime.now(UTC).isoformat(),
        model_used=metadata.get("model_used", "sonnet"),
        tokens_used=metadata.get("tokens_used", 0),
        cached=metadata.get("cached", False),
    )


@router.get(
    "/{dataset_id}/similar",
    response_model=SimilarDatasetsResponse,
    summary="Find similar datasets",
    description="Find datasets semantically similar to this one based on metadata and columns",
)
@handle_api_errors("find similar datasets")
async def get_similar_datasets(
    dataset_id: str,
    threshold: float = Query(
        0.6,
        ge=0.4,
        le=0.9,
        description="Minimum similarity threshold (0.4-0.9)",
    ),
    limit: int = Query(5, ge=1, le=10, description="Maximum results to return"),
    user: dict = Depends(get_current_user),
) -> SimilarDatasetsResponse:
    """Find datasets semantically similar to the given dataset.

    Uses embedding-based similarity to find datasets with similar:
    - Names and descriptions
    - Column structures
    - Business context/insights
    """
    from backend.services.dataset_similarity import get_similarity_service

    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset exists and user owns it
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    # Find similar datasets
    service = get_similarity_service()
    similar = service.find_similar_datasets(
        user_id=user_id,
        dataset_id=dataset_id,
        threshold=threshold,
        limit=limit,
    )

    return SimilarDatasetsResponse(
        similar=[
            SimilarDatasetItem(
                dataset_id=s.dataset_id,
                name=s.name,
                similarity=s.similarity,
                shared_columns=s.shared_columns,
                insight_preview=s.insight_preview,
            )
            for s in similar
        ],
        query_dataset_id=dataset_id,
        threshold=threshold,
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
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    # Get file key
    file_key = dataset.get("file_key")
    if not file_key:
        raise http_error(ErrorCode.VALIDATION_ERROR, "Dataset has no associated file", status=422)

    # Load DataFrame (no row limit for queries)
    try:
        df = load_dataframe(file_key, max_rows=None)
    except DataFrameLoadError as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to load dataset {dataset_id}: {e}",
            dataset_id=dataset_id,
            user_id=user_id,
            file_key=file_key,
        )
        raise http_error(ErrorCode.EXT_SPACES_ERROR, "Failed to load dataset", status=502) from None

    # Execute query
    try:
        result = execute_query(df, query, dataset_id=dataset_id)
    except QueryError as e:
        logger.warning(f"Query error for dataset {dataset_id}: {e}")
        raise http_error(ErrorCode.VALIDATION_ERROR, str(e), status=422) from None

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
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    # Get file key
    file_key = dataset.get("file_key")
    if not file_key:
        raise http_error(ErrorCode.VALIDATION_ERROR, "Dataset has no associated file", status=422)

    # Load DataFrame
    try:
        df = load_dataframe(file_key, max_rows=None)
    except DataFrameLoadError as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to load dataset {dataset_id}: {e}",
            dataset_id=dataset_id,
            user_id=user_id,
            file_key=file_key,
        )
        raise http_error(ErrorCode.EXT_SPACES_ERROR, "Failed to load dataset", status=502) from None

    # Generate chart JSON
    try:
        result = generate_chart_json(df, chart)
    except ChartError as e:
        logger.warning(f"Chart error for dataset {dataset_id}: {e}")
        raise http_error(ErrorCode.VALIDATION_ERROR, str(e), status=422) from None

    # Generate PNG and upload to Spaces using same prefix as dataset
    analysis_id = None
    try:
        png_bytes = generate_chart_png(df, chart)
        chart_prefix = f"charts/{user_id}/{dataset_id}"
        chart_filename = f"{uuid.uuid4()}.png"
        chart_key = f"{chart_prefix}/{chart_filename}"

        spaces_client = get_spaces_client()
        spaces_client.put_file(
            prefix=chart_prefix,
            filename=chart_filename,
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


@router.post(
    "/{dataset_id}/preview-chart",
    response_model=ChartResultResponse,
    summary="Preview chart",
    description="Generate a chart preview without persistence (lighter weight than /chart)",
)
@handle_api_errors("preview chart")
async def preview_dataset_chart(
    dataset_id: str,
    chart: ChartSpec,
    user: dict = Depends(get_current_user),
) -> ChartResultResponse:
    """Generate a chart preview without saving to storage.

    Lighter weight than /chart endpoint - no PNG generation, no Spaces upload,
    no analysis record created. Use for quick chart previews from suggestions.
    """
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    # Get file key
    file_key = dataset.get("file_key")
    if not file_key:
        raise http_error(ErrorCode.VALIDATION_ERROR, "Dataset has no associated file", status=422)

    # Load DataFrame
    try:
        df = load_dataframe(file_key, max_rows=None)
    except DataFrameLoadError as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to load dataset {dataset_id}: {e}",
            dataset_id=dataset_id,
            user_id=user_id,
            file_key=file_key,
        )
        raise http_error(ErrorCode.EXT_SPACES_ERROR, "Failed to load dataset", status=502) from None

    # Generate chart JSON only (no PNG, no persistence)
    try:
        result = generate_chart_json(df, chart)
    except ChartError as e:
        logger.warning(f"Chart preview error for dataset {dataset_id}: {e}")
        raise http_error(ErrorCode.VALIDATION_ERROR, str(e), status=422) from None

    return ChartResultResponse(
        figure_json=result["figure_json"],
        chart_type=result["chart_type"],
        width=result["width"],
        height=result["height"],
        row_count=result["row_count"],
        analysis_id=None,  # Not persisted
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
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

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

        # Load business context if available
        business_ctx = ""
        try:
            user_context = user_repository.get_context(user_id)
            if user_context:
                business_ctx = format_business_context(user_context)
                if business_ctx:
                    logger.info(f"Injecting business context for dataset Q&A (user {user_id})")
        except Exception as e:
            logger.warning(f"Failed to load business context for {user_id}: {e}")

        # Sanitize user question to prevent prompt injection
        safe_question = sanitize_for_prompt(question)

        # Build prompt
        user_prompt = build_analyst_prompt(
            safe_question, dataset_context, conv_history, clarifications_ctx, business_ctx
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

        # Return chart spec if provided and save to analysis gallery
        analysis_id = None
        if chart_spec:
            yield f"event: chart\ndata: {json.dumps({'spec': chart_spec})}\n\n"

            # Save chart to analysis gallery for persistence
            try:
                # Generate title from chart spec
                chart_type = chart_spec.get("chart_type", "chart")
                columns = chart_spec.get("columns", [])
                if columns:
                    col_names = ", ".join(columns[:2])
                    title = f"{chart_type.replace('_', ' ').title()} - {col_names}"
                else:
                    title = f"{chart_type.replace('_', ' ').title()}"

                analysis = dataset_repository.create_analysis(
                    dataset_id=dataset_id,
                    user_id=user_id,
                    chart_spec=chart_spec,
                    title=title,
                )
                analysis_id = analysis.get("id")
                logger.info(f"Saved Q&A chart to analysis gallery: {analysis_id}")
            except Exception as e:
                logger.warning(f"Failed to save chart to analysis gallery: {e}")

        # Save assistant response to conversation
        conversation_repository.append_message(
            conversation_id,
            "assistant",
            analysis_text,
            query_spec=query_spec,
            chart_spec=chart_spec,
            query_result=query_result,
        )

        # Done event with conversation ID and optional analysis_id
        done_payload = {"conversation_id": conversation_id, "tokens": usage.total_tokens}
        if analysis_id:
            done_payload["analysis_id"] = str(analysis_id)
        yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"

    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Error in ask stream for dataset {dataset_id}: {e}",
            dataset_id=dataset_id,
            user_id=user_id,
        )
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
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

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
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

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
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    conversation = conversation_repository.get(conversation_id, user_id)
    if not conversation or conversation.get("dataset_id") != dataset_id:
        raise http_error(ErrorCode.API_NOT_FOUND, "Conversation not found", status=404)

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
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    deleted = conversation_repository.delete(conversation_id, user_id)
    if not deleted:
        raise http_error(ErrorCode.API_NOT_FOUND, "Conversation not found", status=404)


# =========================================================================
# Column Descriptions
# =========================================================================


@router.patch(
    "/{dataset_id}/columns/{column_name}/description",
    status_code=200,
    summary="Update column description",
    description="Update user-defined description for a specific column",
)
@handle_api_errors("update column description")
async def update_column_description(
    dataset_id: str,
    column_name: str,
    body: UpdateColumnDescriptionRequest,
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    """Update user-defined description for a column."""
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    # Update description
    updated = dataset_repository.update_column_description(
        dataset_id, user_id, column_name, body.description
    )
    if not updated:
        raise http_error(ErrorCode.API_NOT_FOUND, "Failed to update description", status=404)

    return {"column_name": column_name, "description": body.description}


@router.get(
    "/{dataset_id}/columns/descriptions",
    response_model=dict[str, str],
    summary="Get column descriptions",
    description="Get all user-defined column descriptions for a dataset",
)
@handle_api_errors("get column descriptions")
async def get_column_descriptions(
    dataset_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    """Get all user-defined column descriptions."""
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    return dataset_repository.get_column_descriptions(dataset_id, user_id)


# =========================================================================
# Favourites
# =========================================================================


@router.post(
    "/{dataset_id}/favourites",
    response_model=DatasetFavouriteResponse,
    status_code=201,
    summary="Create favourite",
    description="Add a chart, insight, or message to favourites",
)
@handle_api_errors("create favourite")
async def create_favourite(
    dataset_id: str,
    body: DatasetFavouriteCreate,
    user: dict = Depends(get_current_user),
) -> DatasetFavouriteResponse:
    """Create a favourite for a dataset item."""
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    favourite = dataset_repository.create_favourite(
        user_id=user_id,
        dataset_id=dataset_id,
        favourite_type=body.favourite_type.value,
        analysis_id=body.analysis_id,
        message_id=body.message_id,
        insight_data=body.insight_data,
        title=body.title,
        content=body.content,
        chart_spec=body.chart_spec,
        figure_json=body.figure_json,
        user_note=body.user_note,
    )

    if not favourite:
        raise http_error(ErrorCode.API_CONFLICT, "Item already favourited", status=409)

    return DatasetFavouriteResponse(
        id=favourite["id"],
        dataset_id=favourite["dataset_id"],
        favourite_type=FavouriteType(favourite["favourite_type"]),
        analysis_id=favourite.get("analysis_id"),
        message_id=favourite.get("message_id"),
        insight_data=favourite.get("insight_data"),
        title=favourite.get("title"),
        content=favourite.get("content"),
        chart_spec=favourite.get("chart_spec"),
        figure_json=favourite.get("figure_json"),
        user_note=favourite.get("user_note"),
        sort_order=favourite.get("sort_order", 0),
        created_at=favourite["created_at"],
    )


@router.get(
    "/{dataset_id}/favourites",
    response_model=DatasetFavouriteListResponse,
    summary="List favourites",
    description="List all favourites for a dataset",
)
@handle_api_errors("list favourites")
async def list_favourites(
    dataset_id: str,
    user: dict = Depends(get_current_user),
) -> DatasetFavouriteListResponse:
    """List favourites for a dataset."""
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    favourites = dataset_repository.list_favourites(dataset_id, user_id)

    return DatasetFavouriteListResponse(
        favourites=[
            DatasetFavouriteResponse(
                id=f["id"],
                dataset_id=f["dataset_id"],
                favourite_type=FavouriteType(f["favourite_type"]),
                analysis_id=f.get("analysis_id"),
                message_id=f.get("message_id"),
                insight_data=f.get("insight_data"),
                title=f.get("title"),
                content=f.get("content"),
                chart_spec=f.get("chart_spec"),
                figure_json=f.get("figure_json"),
                user_note=f.get("user_note"),
                sort_order=f.get("sort_order", 0),
                created_at=f["created_at"],
            )
            for f in favourites
        ],
        total=len(favourites),
    )


@router.patch(
    "/{dataset_id}/favourites/{favourite_id}",
    response_model=DatasetFavouriteResponse,
    summary="Update favourite",
    description="Update a favourite (note or sort order)",
)
@handle_api_errors("update favourite")
async def update_favourite(
    dataset_id: str,
    favourite_id: str,
    body: DatasetFavouriteUpdate,
    user: dict = Depends(get_current_user),
) -> DatasetFavouriteResponse:
    """Update a favourite."""
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    favourite = dataset_repository.update_favourite(
        favourite_id=favourite_id,
        user_id=user_id,
        user_note=body.user_note,
        sort_order=body.sort_order,
    )

    if not favourite:
        raise http_error(ErrorCode.API_NOT_FOUND, "Favourite not found", status=404)

    return DatasetFavouriteResponse(
        id=favourite["id"],
        dataset_id=favourite["dataset_id"],
        favourite_type=FavouriteType(favourite["favourite_type"]),
        analysis_id=favourite.get("analysis_id"),
        message_id=favourite.get("message_id"),
        insight_data=favourite.get("insight_data"),
        title=favourite.get("title"),
        content=favourite.get("content"),
        chart_spec=favourite.get("chart_spec"),
        figure_json=favourite.get("figure_json"),
        user_note=favourite.get("user_note"),
        sort_order=favourite.get("sort_order", 0),
        created_at=favourite["created_at"],
    )


@router.delete(
    "/{dataset_id}/favourites/{favourite_id}",
    status_code=204,
    summary="Delete favourite",
    description="Remove an item from favourites",
)
@handle_api_errors("delete favourite")
async def delete_favourite(
    dataset_id: str,
    favourite_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    """Delete a favourite."""
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    deleted = dataset_repository.delete_favourite(favourite_id, user_id)
    if not deleted:
        raise http_error(ErrorCode.API_NOT_FOUND, "Favourite not found", status=404)


# =========================================================================
# Reports
# =========================================================================


@router.post(
    "/{dataset_id}/reports",
    response_model=DatasetReportResponse,
    status_code=201,
    summary="Generate report",
    description="Generate a report from favourited items",
)
@handle_api_errors("generate report")
async def generate_report(
    dataset_id: str,
    body: DatasetReportCreate,
    user: dict = Depends(get_current_user),
) -> DatasetReportResponse:
    """Generate a report from favourites."""
    from backend.services.dataset_report_generator import generate_dataset_report

    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    # Get favourites to include
    if body.favourite_ids:
        favourites = dataset_repository.get_favourites_by_ids(body.favourite_ids, user_id)
    else:
        favourites = dataset_repository.list_favourites(dataset_id, user_id)

    if not favourites:
        raise http_error(
            ErrorCode.API_VALIDATION_ERROR, "No favourites to include in report", status=400
        )

    # Generate report via LLM
    report_data, metadata = await generate_dataset_report(
        dataset=dataset,
        favourites=favourites,
        title=body.title,
    )

    # Persist report
    report = dataset_repository.create_report(
        user_id=user_id,
        dataset_id=dataset_id,
        title=report_data["title"],
        report_content={"sections": report_data["sections"]},
        favourite_ids=[f["id"] for f in favourites],
        executive_summary=report_data.get("executive_summary"),
        model_used=metadata.get("model"),
        tokens_used=metadata.get("tokens"),
    )

    return DatasetReportResponse(
        id=report["id"],
        dataset_id=report["dataset_id"],
        title=report["title"],
        executive_summary=report.get("executive_summary"),
        sections=[ReportSection(**s) for s in report["report_content"].get("sections", [])],
        favourite_ids=report["favourite_ids"],
        favourites=[
            DatasetFavouriteResponse(
                id=f["id"],
                dataset_id=f["dataset_id"],
                favourite_type=FavouriteType(f["favourite_type"]),
                analysis_id=f.get("analysis_id"),
                message_id=f.get("message_id"),
                insight_data=f.get("insight_data"),
                title=f.get("title"),
                content=f.get("content"),
                chart_spec=f.get("chart_spec"),
                figure_json=f.get("figure_json"),
                user_note=f.get("user_note"),
                sort_order=f.get("sort_order", 0),
                created_at=f["created_at"],
            )
            for f in favourites
        ],
        model_used=report.get("model_used"),
        tokens_used=report.get("tokens_used"),
        created_at=report["created_at"],
    )


@router.get(
    "/{dataset_id}/reports",
    response_model=DatasetReportListResponse,
    summary="List reports",
    description="List all reports for a dataset",
)
@handle_api_errors("list reports")
async def list_reports(
    dataset_id: str,
    user: dict = Depends(get_current_user),
) -> DatasetReportListResponse:
    """List reports for a dataset."""
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    reports = dataset_repository.list_reports(dataset_id, user_id)

    return DatasetReportListResponse(
        reports=[
            DatasetReportResponse(
                id=r["id"],
                dataset_id=r["dataset_id"],
                title=r["title"],
                executive_summary=r.get("executive_summary"),
                sections=[ReportSection(**s) for s in r["report_content"].get("sections", [])],
                favourite_ids=r["favourite_ids"],
                model_used=r.get("model_used"),
                tokens_used=r.get("tokens_used"),
                created_at=r["created_at"],
            )
            for r in reports
        ],
        total=len(reports),
    )


@router.get(
    "/{dataset_id}/reports/{report_id}",
    response_model=DatasetReportResponse,
    summary="Get report",
    description="Get a specific report with full content",
)
@handle_api_errors("get report")
async def get_report(
    dataset_id: str,
    report_id: str,
    user: dict = Depends(get_current_user),
) -> DatasetReportResponse:
    """Get a report by ID."""
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    report = dataset_repository.get_report(report_id, user_id)
    if not report:
        raise http_error(ErrorCode.API_NOT_FOUND, "Report not found", status=404)

    # Get favourites for rendering charts
    favourites = dataset_repository.get_favourites_by_ids(report["favourite_ids"], user_id)

    return DatasetReportResponse(
        id=report["id"],
        dataset_id=report["dataset_id"],
        title=report["title"],
        executive_summary=report.get("executive_summary"),
        sections=[ReportSection(**s) for s in report["report_content"].get("sections", [])],
        favourite_ids=report["favourite_ids"],
        favourites=[
            DatasetFavouriteResponse(
                id=f["id"],
                dataset_id=f["dataset_id"],
                favourite_type=FavouriteType(f["favourite_type"]),
                analysis_id=f.get("analysis_id"),
                message_id=f.get("message_id"),
                insight_data=f.get("insight_data"),
                title=f.get("title"),
                content=f.get("content"),
                chart_spec=f.get("chart_spec"),
                figure_json=f.get("figure_json"),
                user_note=f.get("user_note"),
                sort_order=f.get("sort_order", 0),
                created_at=f["created_at"],
            )
            for f in favourites
        ],
        model_used=report.get("model_used"),
        tokens_used=report.get("tokens_used"),
        created_at=report["created_at"],
    )


@router.delete(
    "/{dataset_id}/reports/{report_id}",
    status_code=204,
    summary="Delete report",
    description="Delete a report",
)
@handle_api_errors("delete report")
async def delete_report(
    dataset_id: str,
    report_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    """Delete a report."""
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    deleted = dataset_repository.delete_report(report_id, user_id)
    if not deleted:
        raise http_error(ErrorCode.API_NOT_FOUND, "Report not found", status=404)


class ReportSummaryResponse(BaseModel):
    """Response for executive summary regeneration."""

    summary: str = Field(..., description="Regenerated executive summary")
    model_used: str | None = Field(None, description="LLM model used")
    tokens_used: int | None = Field(None, description="Tokens consumed")


@router.post(
    "/{dataset_id}/reports/{report_id}/summary",
    response_model=ReportSummaryResponse,
    summary="Regenerate executive summary",
    description="Regenerate the executive summary for a report using LLM",
)
@handle_api_errors("regenerate report summary")
async def regenerate_report_summary(
    dataset_id: str,
    report_id: str,
    user: dict = Depends(get_current_user),
) -> ReportSummaryResponse:
    """Regenerate the executive summary for a report."""
    from backend.services.dataset_report_generator import regenerate_executive_summary

    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    # Get report
    report = dataset_repository.get_report(report_id, user_id)
    if not report:
        raise http_error(ErrorCode.API_NOT_FOUND, "Report not found", status=404)

    # Regenerate summary
    summary, metadata = await regenerate_executive_summary(report)

    # Update report with new summary
    dataset_repository.update_report_summary(report_id, user_id, summary)

    return ReportSummaryResponse(
        summary=summary,
        model_used=metadata.get("model"),
        tokens_used=metadata.get("tokens"),
    )


@router.get(
    "/{dataset_id}/reports/{report_id}/export",
    summary="Export report",
    description="Export report in specified format (markdown or pdf)",
)
@handle_api_errors("export report")
async def export_report(
    dataset_id: str,
    report_id: str,
    format: str = Query("markdown", description="Export format: markdown or pdf"),
    user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Export a report as markdown or PDF."""
    from backend.services.dataset_report_generator import export_report_to_markdown

    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    # Get report
    report = dataset_repository.get_report(report_id, user_id)
    if not report:
        raise http_error(ErrorCode.API_NOT_FOUND, "Report not found", status=404)

    # Get favourites for chart references
    favourites = dataset_repository.get_favourites_by_ids(report["favourite_ids"], user_id)

    if format == "markdown":
        markdown_content = export_report_to_markdown(
            report=report,
            dataset_name=dataset.get("name", "Dataset"),
            favourites=favourites,
        )
        return StreamingResponse(
            iter([markdown_content.encode("utf-8")]),
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename={report.get('title', 'report').replace(' ', '_')}.md"
            },
        )

    elif format == "pdf":
        # Generate markdown first, then convert to simple PDF
        markdown_content = export_report_to_markdown(
            report=report,
            dataset_name=dataset.get("name", "Dataset"),
            favourites=favourites,
        )

        # For MVP, we'll provide HTML that can be printed to PDF
        # A proper PDF would need reportlab or weasyprint
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{report.get("title", "Report")}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; }}
        h1 {{ color: #1a1a2e; border-bottom: 2px solid #4f46e5; padding-bottom: 10px; }}
        h2 {{ color: #374151; margin-top: 30px; }}
        blockquote {{ border-left: 4px solid #4f46e5; margin: 20px 0; padding: 10px 20px; background: #f3f4f6; }}
        hr {{ border: none; border-top: 1px solid #e5e7eb; margin: 30px 0; }}
        .meta {{ color: #6b7280; font-size: 14px; }}
        @media print {{ body {{ margin: 0; padding: 20px; }} }}
    </style>
</head>
<body>
    <h1>{report.get("title", "Data Analysis Report")}</h1>
    <p class="meta"><strong>Dataset:</strong> {dataset.get("name", "Dataset")}</p>
    <hr>
"""
        # Convert markdown sections to HTML
        if report.get("executive_summary"):
            html_content += f"<h2>Executive Summary</h2><p>{report['executive_summary']}</p>"

        report_content = report.get("report_content", {})
        for section in report_content.get("sections", []):
            html_content += f"<h2>{section.get('title', 'Section')}</h2>"
            # Basic markdown to HTML conversion
            content = section.get("content", "")
            content = content.replace("\n\n", "</p><p>").replace("\n", "<br>")
            html_content += f"<p>{content}</p>"

        html_content += """
    <hr>
    <p class="meta"><em>Generated by Board of One Data Analysis</em></p>
</body>
</html>"""

        return StreamingResponse(
            iter([html_content.encode("utf-8")]),
            media_type="text/html",
            headers={
                "Content-Disposition": f"attachment; filename={report.get('title', 'report').replace(' ', '_')}.html"
            },
        )

    else:
        raise http_error(
            ErrorCode.API_VALIDATION_ERROR,
            f"Unsupported format: {format}. Use 'markdown' or 'pdf'",
            status=400,
        )


# =============================================================================
# Investigation Endpoints (8 Deterministic Analyses)
# =============================================================================


@router.post(
    "/{dataset_id}/investigate",
    response_model=DatasetInvestigationResponse,
    summary="Run dataset investigation",
    description="Run 8 deterministic analyses on a dataset",
)
@handle_api_errors("run investigation")
async def run_dataset_investigation(
    dataset_id: str,
    user: dict = Depends(get_current_user),
) -> DatasetInvestigationResponse:
    """Run 8 deterministic analyses on a dataset.

    Analyses:
    1. Column role inference (id, timestamp, metric, dimension)
    2. Missingness + uniqueness + cardinality
    3. Descriptive stats + heavy hitters
    4. Outlier detection (IQR-based)
    5. Correlation matrix + leakage hints
    6. Time-series readiness
    7. Segmentation suggestions
    8. Data quality assessment

    Results are cached in the database.
    """
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    file_key = dataset.get("file_key")
    if not file_key:
        raise http_error(ErrorCode.SERVICE_ANALYSIS_ERROR, "Dataset has no file", status=422)

    # Load DataFrame
    try:
        df = load_dataframe(file_key)
    except DataFrameLoadError as e:
        raise http_error(
            ErrorCode.SERVICE_ANALYSIS_ERROR, f"Failed to load dataset: {e}", status=422
        ) from e

    # Run investigation
    investigation = run_investigation(df)
    investigation_dict = investigation.to_dict()

    # Save to database
    saved = dataset_repository.save_investigation(dataset_id, user_id, investigation_dict)

    return DatasetInvestigationResponse(**saved)


@router.get(
    "/{dataset_id}/investigation",
    response_model=DatasetInvestigationResponse,
    summary="Get dataset investigation",
    description="Get cached investigation results for a dataset",
)
@handle_api_errors("get investigation")
async def get_dataset_investigation(
    dataset_id: str,
    user: dict = Depends(get_current_user),
) -> DatasetInvestigationResponse:
    """Get cached investigation results for a dataset."""
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    # Get cached investigation
    investigation = dataset_repository.get_investigation(dataset_id, user_id)
    if not investigation:
        raise http_error(
            ErrorCode.API_NOT_FOUND,
            "No investigation found. Run POST /investigate first.",
            status=404,
        )

    return DatasetInvestigationResponse(**investigation)


class ColumnRoleUpdate(BaseModel):
    """Request body for updating a column's role."""

    column_name: str = Field(description="Column name to update")
    role: str = Field(description="New role: metric, dimension, id, timestamp, or unknown")


@router.patch(
    "/{dataset_id}/column-role",
    response_model=DatasetInvestigationResponse,
    summary="Update column role",
    description="Update a column's role classification (metric, dimension, id, timestamp, unknown)",
)
@handle_api_errors("update column role")
async def update_column_role(
    dataset_id: str,
    body: ColumnRoleUpdate,
    user: dict = Depends(get_current_user),
) -> DatasetInvestigationResponse:
    """Update a column's role in the investigation.

    Allows users to correct misclassified columns (e.g., setting 'Returns' from 'unknown' to 'metric').
    """
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Validate role
    valid_roles = {"metric", "dimension", "id", "timestamp", "unknown"}
    if body.role not in valid_roles:
        raise http_error(
            ErrorCode.API_VALIDATION_ERROR,
            f"Invalid role. Must be one of: {', '.join(valid_roles)}",
            status=400,
        )

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    # Update the column role
    investigation = dataset_repository.update_column_role(
        dataset_id, user_id, body.column_name, body.role
    )
    if not investigation:
        raise http_error(
            ErrorCode.API_NOT_FOUND,
            "Column not found in investigation or no investigation exists",
            status=404,
        )

    return DatasetInvestigationResponse(**investigation)


# =============================================================================
# Business Context Endpoints
# =============================================================================


@router.post(
    "/{dataset_id}/business-context",
    response_model=DatasetBusinessContextResponse,
    summary="Set business context",
    description="Set or update business context for a dataset",
)
@handle_api_errors("set business context")
async def set_business_context(
    dataset_id: str,
    context: DatasetBusinessContextCreate,
    user: dict = Depends(get_current_user),
) -> DatasetBusinessContextResponse:
    """Set or update business context for a dataset.

    Business context includes goals, metrics, KPIs, objectives, and industry.
    This context is used to enhance LLM-generated suggestions.
    """
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    # Save business context
    saved = dataset_repository.save_business_context(
        dataset_id=dataset_id,
        user_id=user_id,
        business_goal=context.business_goal,
        key_metrics=context.key_metrics,
        kpis=context.kpis,
        objectives=context.objectives,
        industry=context.industry,
        additional_context=context.additional_context,
    )

    return DatasetBusinessContextResponse(**saved)


@router.get(
    "/{dataset_id}/business-context",
    response_model=DatasetBusinessContextResponse,
    summary="Get business context",
    description="Get business context for a dataset",
)
@handle_api_errors("get business context")
async def get_business_context(
    dataset_id: str,
    user: dict = Depends(get_current_user),
) -> DatasetBusinessContextResponse:
    """Get business context for a dataset.

    First checks for dataset-specific business context.
    Falls back to user's global business context if none exists.
    """
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    # Get dataset-specific business context
    context = dataset_repository.get_business_context(dataset_id, user_id)
    if context:
        return DatasetBusinessContextResponse(**context)

    # Fallback to user's global business context
    user_context = user_repository.get_context(user_id)
    if user_context:
        # Map user context to dataset business context format
        return DatasetBusinessContextResponse(
            id=None,
            dataset_id=dataset_id,
            business_goal=user_context.get("primary_objective"),
            key_metrics=None,
            kpis=user_context.get("context_kpis") if user_context.get("context_kpis") else None,
            objectives=user_context.get("main_value_proposition"),
            industry=user_context.get("industry"),
            additional_context=f"Company: {user_context.get('company_name', 'N/A')}. "
            f"Target market: {user_context.get('target_market', 'N/A')}. "
            f"Business model: {user_context.get('business_model', 'N/A')}."
            if user_context.get("company_name") or user_context.get("target_market")
            else None,
            created_at=None,
            updated_at=None,
        )

    raise http_error(
        ErrorCode.API_NOT_FOUND,
        "No business context found. Set up your business context in Settings first.",
        status=404,
    )


# =============================================================================
# Dataset Comparison Endpoints
# =============================================================================


@router.post(
    "/{dataset_id}/compare/{other_dataset_id}",
    response_model=DatasetComparisonResponse,
    status_code=201,
    summary="Compare two datasets",
    description="Compare this dataset with another dataset (schema, statistics, key metrics)",
)
@handle_api_errors("compare datasets")
async def compare_two_datasets(
    dataset_id: str,
    other_dataset_id: str,
    body: DatasetComparisonCreate | None = None,
    user: dict = Depends(get_current_user),
) -> DatasetComparisonResponse:
    """Compare two datasets.

    Compares:
    - Schema: common columns, columns only in A/B, type mismatches
    - Statistics: per-column stat deltas (mean, null count, unique count, etc.)
    - Key metrics: percentage changes in aggregate metrics

    Results are cached in the database.
    """
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify ownership of both datasets
    dataset_a = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset_a:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset A not found", status=404)

    dataset_b = dataset_repository.get_by_id(other_dataset_id, user_id)
    if not dataset_b:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset B not found", status=404)

    # Ensure both datasets have files
    file_key_a = dataset_a.get("file_key")
    file_key_b = dataset_b.get("file_key")
    if not file_key_a or not file_key_b:
        raise http_error(
            ErrorCode.SERVICE_ANALYSIS_ERROR, "Both datasets must have files", status=422
        )

    # Load DataFrames
    try:
        df_a = load_dataframe(file_key_a)
        df_b = load_dataframe(file_key_b)
    except DataFrameLoadError as e:
        raise http_error(
            ErrorCode.SERVICE_ANALYSIS_ERROR, f"Failed to load dataset: {e}", status=422
        ) from e

    # Run comparison
    comparison_name = body.name if body else None
    result = compare_datasets(
        df_a=df_a,
        df_b=df_b,
        name_a=dataset_a["name"],
        name_b=dataset_b["name"],
    )

    # Save to database
    saved = dataset_repository.save_comparison(
        user_id=user_id,
        dataset_a_id=dataset_id,
        dataset_b_id=other_dataset_id,
        schema_comparison=result.schema_comparison.to_dict(),
        statistics_comparison=result.statistics_comparison.to_dict(),
        key_metrics_comparison=result.key_metrics_comparison.to_dict(),
        insights=result.insights,
        name=comparison_name,
    )

    return DatasetComparisonResponse(
        id=saved["id"],
        dataset_a_id=saved["dataset_a_id"],
        dataset_b_id=saved["dataset_b_id"],
        dataset_a_name=dataset_a["name"],
        dataset_b_name=dataset_b["name"],
        name=saved.get("name"),
        schema_comparison=saved["schema_comparison"],
        statistics_comparison=saved["statistics_comparison"],
        key_metrics_comparison=saved["key_metrics_comparison"],
        insights=saved["insights"] or [],
        created_at=saved["created_at"],
    )


@router.get(
    "/{dataset_id}/comparisons",
    response_model=DatasetComparisonListResponse,
    summary="List dataset comparisons",
    description="List all comparisons involving this dataset",
)
@handle_api_errors("list comparisons")
async def list_dataset_comparisons(
    dataset_id: str,
    limit: int = Query(10, ge=1, le=50, description="Max comparisons to return"),
    user: dict = Depends(get_current_user),
) -> DatasetComparisonListResponse:
    """List comparisons involving this dataset (as either A or B)."""
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    comparisons = dataset_repository.list_comparisons_for_dataset(dataset_id, user_id, limit)

    # Fetch dataset names for each comparison
    response_comparisons = []
    for c in comparisons:
        # Get names for datasets
        ds_a = dataset_repository.get_by_id(c["dataset_a_id"], user_id)
        ds_b = dataset_repository.get_by_id(c["dataset_b_id"], user_id)

        response_comparisons.append(
            DatasetComparisonResponse(
                id=c["id"],
                dataset_a_id=c["dataset_a_id"],
                dataset_b_id=c["dataset_b_id"],
                dataset_a_name=ds_a["name"] if ds_a else None,
                dataset_b_name=ds_b["name"] if ds_b else None,
                name=c.get("name"),
                schema_comparison=c["schema_comparison"],
                statistics_comparison=c["statistics_comparison"],
                key_metrics_comparison=c["key_metrics_comparison"],
                insights=c.get("insights") or [],
                created_at=c["created_at"],
            )
        )

    return DatasetComparisonListResponse(
        comparisons=response_comparisons,
        total_count=len(response_comparisons),
    )


@router.get(
    "/{dataset_id}/comparisons/{comparison_id}",
    response_model=DatasetComparisonResponse,
    summary="Get comparison",
    description="Get a specific comparison by ID",
)
@handle_api_errors("get comparison")
async def get_comparison(
    dataset_id: str,
    comparison_id: str,
    user: dict = Depends(get_current_user),
) -> DatasetComparisonResponse:
    """Get a specific comparison by ID."""
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    comparison = dataset_repository.get_comparison(comparison_id, user_id)
    if not comparison:
        raise http_error(ErrorCode.API_NOT_FOUND, "Comparison not found", status=404)

    # Verify comparison involves this dataset
    if comparison["dataset_a_id"] != dataset_id and comparison["dataset_b_id"] != dataset_id:
        raise http_error(
            ErrorCode.API_NOT_FOUND, "Comparison not found for this dataset", status=404
        )

    # Get dataset names
    ds_a = dataset_repository.get_by_id(comparison["dataset_a_id"], user_id)
    ds_b = dataset_repository.get_by_id(comparison["dataset_b_id"], user_id)

    return DatasetComparisonResponse(
        id=comparison["id"],
        dataset_a_id=comparison["dataset_a_id"],
        dataset_b_id=comparison["dataset_b_id"],
        dataset_a_name=ds_a["name"] if ds_a else None,
        dataset_b_name=ds_b["name"] if ds_b else None,
        name=comparison.get("name"),
        schema_comparison=comparison["schema_comparison"],
        statistics_comparison=comparison["statistics_comparison"],
        key_metrics_comparison=comparison["key_metrics_comparison"],
        insights=comparison.get("insights") or [],
        created_at=comparison["created_at"],
    )


@router.delete(
    "/{dataset_id}/comparisons/{comparison_id}",
    status_code=204,
    summary="Delete comparison",
    description="Delete a comparison",
)
@handle_api_errors("delete comparison")
async def delete_comparison(
    dataset_id: str,
    comparison_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    """Delete a comparison."""
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    # Verify dataset ownership
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)

    # Verify comparison exists and involves this dataset
    comparison = dataset_repository.get_comparison(comparison_id, user_id)
    if not comparison:
        raise http_error(ErrorCode.API_NOT_FOUND, "Comparison not found", status=404)

    if comparison["dataset_a_id"] != dataset_id and comparison["dataset_b_id"] != dataset_id:
        raise http_error(
            ErrorCode.API_NOT_FOUND, "Comparison not found for this dataset", status=404
        )

    deleted = dataset_repository.delete_comparison(comparison_id, user_id)
    if not deleted:
        raise http_error(ErrorCode.API_NOT_FOUND, "Comparison not found", status=404)


# =============================================================================
# Multi-Dataset Analysis Endpoints
# =============================================================================


@router.post(
    "/multi-analysis",
    response_model=MultiDatasetAnalysisResponse,
    status_code=201,
    summary="Run multi-dataset analysis",
    description="Analyze 2-5 datasets for cross-dataset anomalies (schema drift, metric outliers)",
)
@handle_api_errors("multi-dataset analysis")
async def run_multi_dataset_analysis(
    body: MultiDatasetAnalysisCreate,
    user: dict = Depends(get_current_user),
) -> MultiDatasetAnalysisResponse:
    """Analyze multiple datasets for cross-dataset anomalies.

    Detects:
    - Schema drift: columns present in only some datasets
    - Metric outliers: values >2 std dev from cross-dataset mean
    - Type mismatches: same column with different types across datasets

    Minimum 2 datasets, maximum 5 datasets required.
    """
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    dataset_ids = body.dataset_ids

    # Validate dataset count (also enforced by Pydantic)
    if len(dataset_ids) < 2:
        raise http_error(
            ErrorCode.SERVICE_VALIDATION_ERROR, "At least 2 datasets required", status=422
        )
    if len(dataset_ids) > 5:
        raise http_error(
            ErrorCode.SERVICE_VALIDATION_ERROR, "Maximum 5 datasets allowed", status=422
        )

    # Remove duplicates while preserving order
    seen = set()
    unique_ids = []
    for did in dataset_ids:
        if did not in seen:
            seen.add(did)
            unique_ids.append(did)
    dataset_ids = unique_ids

    if len(dataset_ids) < 2:
        raise http_error(
            ErrorCode.SERVICE_VALIDATION_ERROR, "Need at least 2 distinct datasets", status=422
        )

    # Verify ownership and load all datasets
    datasets = []
    dataframes = []
    dataset_names = []

    for dataset_id in dataset_ids:
        dataset = dataset_repository.get_by_id(dataset_id, user_id)
        if not dataset:
            raise http_error(
                ErrorCode.API_NOT_FOUND,
                f"Dataset not found: {dataset_id}",
                status=404,
            )

        file_key = dataset.get("file_key")
        if not file_key:
            raise http_error(
                ErrorCode.SERVICE_ANALYSIS_ERROR,
                f"Dataset '{dataset['name']}' has no file",
                status=422,
            )

        try:
            df = load_dataframe(file_key)
            dataframes.append(df)
            datasets.append(dataset)
            dataset_names.append(dataset["name"])
        except DataFrameLoadError as e:
            raise http_error(
                ErrorCode.SERVICE_ANALYSIS_ERROR,
                f"Failed to load dataset '{dataset['name']}': {e}",
                status=422,
            ) from e

    # Run analysis
    result = analyze_multiple_datasets(dataframes, dataset_names)

    # Save to database
    saved = dataset_repository.save_multi_analysis(
        user_id=user_id,
        dataset_ids=dataset_ids,
        common_schema=result.common_schema.to_dict(),
        anomalies=[a.to_dict() for a in result.anomalies],
        dataset_summaries=[s.to_dict() for s in result.dataset_summaries],
        pairwise_comparisons=result.pairwise_comparisons,
        name=body.name,
    )

    # Build response
    return MultiDatasetAnalysisResponse(
        id=saved["id"],
        dataset_ids=saved["dataset_ids"],
        dataset_names=dataset_names,
        name=saved.get("name"),
        common_schema=MultiDatasetCommonSchema(**saved["common_schema"]),
        anomalies=[MultiDatasetAnomaly(**a) for a in saved["anomalies"] or []],
        dataset_summaries=[MultiDatasetSummary(**s) for s in saved["dataset_summaries"] or []],
        pairwise_comparisons=saved.get("pairwise_comparisons") or [],
        created_at=saved["created_at"],
    )


@router.get(
    "/multi-analysis",
    response_model=MultiDatasetAnalysisListResponse,
    summary="List multi-dataset analyses",
    description="List all multi-dataset analyses for the current user",
)
@handle_api_errors("list multi-analyses")
async def list_multi_analyses(
    limit: int = Query(20, ge=1, le=50, description="Max results"),
    user: dict = Depends(get_current_user),
) -> MultiDatasetAnalysisListResponse:
    """List all multi-dataset analyses for the current user."""
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    analyses = dataset_repository.list_multi_analyses(user_id, limit)

    # Fetch dataset names for each analysis
    response_analyses = []
    for a in analyses:
        # Get names for all dataset_ids
        names = []
        for did in a.get("dataset_ids", []):
            ds = dataset_repository.get_by_id(did, user_id)
            names.append(ds["name"] if ds else "Deleted")

        response_analyses.append(
            MultiDatasetAnalysisResponse(
                id=a["id"],
                dataset_ids=a.get("dataset_ids") or [],
                dataset_names=names,
                name=a.get("name"),
                common_schema=MultiDatasetCommonSchema(**(a.get("common_schema") or {})),
                anomalies=[MultiDatasetAnomaly(**an) for an in a.get("anomalies") or []],
                dataset_summaries=[
                    MultiDatasetSummary(**s) for s in a.get("dataset_summaries") or []
                ],
                pairwise_comparisons=a.get("pairwise_comparisons") or [],
                created_at=a["created_at"],
            )
        )

    return MultiDatasetAnalysisListResponse(
        analyses=response_analyses,
        total_count=len(response_analyses),
    )


@router.get(
    "/multi-analysis/{analysis_id}",
    response_model=MultiDatasetAnalysisResponse,
    summary="Get multi-dataset analysis",
    description="Get a specific multi-dataset analysis by ID",
)
@handle_api_errors("get multi-analysis")
async def get_multi_analysis(
    analysis_id: str,
    user: dict = Depends(get_current_user),
) -> MultiDatasetAnalysisResponse:
    """Get a specific multi-dataset analysis by ID."""
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    analysis = dataset_repository.get_multi_analysis(analysis_id, user_id)
    if not analysis:
        raise http_error(ErrorCode.API_NOT_FOUND, "Analysis not found", status=404)

    # Get dataset names
    names = []
    for did in analysis.get("dataset_ids", []):
        ds = dataset_repository.get_by_id(did, user_id)
        names.append(ds["name"] if ds else "Deleted")

    return MultiDatasetAnalysisResponse(
        id=analysis["id"],
        dataset_ids=analysis.get("dataset_ids") or [],
        dataset_names=names,
        name=analysis.get("name"),
        common_schema=MultiDatasetCommonSchema(**(analysis.get("common_schema") or {})),
        anomalies=[MultiDatasetAnomaly(**a) for a in analysis.get("anomalies") or []],
        dataset_summaries=[
            MultiDatasetSummary(**s) for s in analysis.get("dataset_summaries") or []
        ],
        pairwise_comparisons=analysis.get("pairwise_comparisons") or [],
        created_at=analysis["created_at"],
    )


@router.delete(
    "/multi-analysis/{analysis_id}",
    status_code=204,
    summary="Delete multi-dataset analysis",
    description="Delete a multi-dataset analysis",
)
@handle_api_errors("delete multi-analysis")
async def delete_multi_analysis(
    analysis_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    """Delete a multi-dataset analysis."""
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.API_UNAUTHORIZED, "User ID not found", status=401)

    deleted = dataset_repository.delete_multi_analysis(analysis_id, user_id)
    if not deleted:
        raise http_error(ErrorCode.API_NOT_FOUND, "Analysis not found", status=404)
