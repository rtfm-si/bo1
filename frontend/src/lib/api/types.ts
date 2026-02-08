/**
 * API Types - TypeScript interfaces for Board of One API
 *
 * This file re-exports generated types from the OpenAPI spec as the primary source of truth.
 * Frontend-only types (HoneypotFields, UI state, etc.) are defined manually.
 *
 * To regenerate types from backend: npm run generate:types (requires backend running)
 * The generated types are in ./generated-types.ts
 */

import type { SSEEvent } from './sse-events';
import type { components } from './generated-types';

// =============================================================================
// Generated Types (from OpenAPI spec via openapi-typescript)
// =============================================================================
// These types are auto-generated from backend Pydantic models.
// To update: 1) make openapi-export  2) npm run generate:types

// ---- Core Session Types ----
export type SessionResponse = components['schemas']['SessionResponse'];
export type SessionDetailResponse = components['schemas']['SessionDetailResponse'];
export type FullSessionResponse = components['schemas']['FullSessionResponse'];
export type SessionListResponse = components['schemas']['SessionListResponse'];

// ---- Action Types ----
export type ActionDetailResponse = components['schemas']['ActionDetailResponse'];
export type AllActionsResponse = components['schemas']['AllActionsResponse'];
export type ActionStatus = components['schemas']['ActionDetailResponse']['status'];
export type ActionStatsResponse = components['schemas']['ActionStatsResponse'];

/**
 * Extended action detail with frontend-only fields
 * These fields are set locally but not persisted to backend (yet)
 */
export interface ActionDetailExtended extends ActionDetailResponse {
	/** Reason for closing/cancelling the action */
	closure_reason?: string | null;
	/** ID of action this was replanned to */
	replanned_to_id?: string | null;
	/** ID of action this was replanned from */
	replanned_from_id?: string | null;
	/** User reflection on lessons learned from this action */
	lessons_learned?: string | null;
	/** User reflection on what went well during this action */
	went_well?: string | null;
}

/**
 * Request body for completing an action with optional post-mortem
 */
export interface ActionCompleteRequest {
	/** Reflection on lessons learned (max 500 chars) */
	lessons_learned?: string | null;
	/** Reflection on what went well (max 500 chars) */
	went_well?: string | null;
}
export type ActionStatsTotals = components['schemas']['ActionStatsTotals'];
export type DailyActionStat = components['schemas']['DailyActionStat'];
export type ActionReminderResponse = components['schemas']['ActionReminderResponse'];
export type ActionRemindersResponse = components['schemas']['ActionRemindersResponse'];
export type ReminderSettingsResponse = components['schemas']['ReminderSettingsResponse'];
export type ActionUpdateResponse = components['schemas']['ActionUpdateResponse'];
export type ActionUpdatesResponse = components['schemas']['ActionUpdatesResponse'];

// ---- Project Types ----
export type ProjectDetailResponse = components['schemas']['ProjectDetailResponse'];
export type ProjectListResponse = components['schemas']['ProjectListResponse'];
export type ProjectStatus = components['schemas']['ProjectDetailResponse']['status'];
export type ProjectActionSummary = components['schemas']['ProjectActionSummary'];
export type ProjectActionsResponse = components['schemas']['ProjectActionsResponse'];
export type ProjectSessionLink = components['schemas']['ProjectSessionLink'];
export type GanttResponse = components['schemas']['GanttResponse'];
export type GanttActionData = components['schemas']['GanttActionData'];
export type GanttDependency = components['schemas']['GanttDependency'];
export type GanttProjectData = components['schemas']['GanttProjectData'];
export type GlobalGanttResponse = components['schemas']['GlobalGanttResponse'];

// ---- Context & User Types ----
export type BusinessContext = components['schemas']['BusinessContext'];
export type ContextResponse = components['schemas']['ContextResponse'];
export type ContextWithTrends = components['schemas']['ContextWithTrends'];
export type MetricTrend = components['schemas']['MetricTrend'];
export type TrendDirection = components['schemas']['TrendDirection'];
export type BusinessStage = components['schemas']['BusinessStage'];
export type PrimaryObjective = components['schemas']['PrimaryObjective'];
export type EnrichmentSource = components['schemas']['EnrichmentSource'];

// ---- Health & Control Types ----
export type HealthResponse = components['schemas']['HealthResponse'];
export type ControlResponse = components['schemas']['ControlResponse'];

// ---- Checkpoint State Types ----
/**
 * Response for session checkpoint state (resume capability).
 * Used to show resumable progress on failed sessions.
 */
export interface CheckpointStateResponse {
	session_id: string;
	completed_sub_problems: number;
	total_sub_problems: number | null;
	last_checkpoint_at: string | null;
	can_resume: boolean;
	status: string;
	phase: string | null;
}

// ---- Insights Types ----
export type InsightCategory = components['schemas']['InsightCategory'];
export type InsightMetricResponse = components['schemas']['InsightMetricResponse'];
/** @deprecated Use InsightMetricResponse */
export type InsightMetric = components['schemas']['InsightMetricResponse'];
export type InsightsResponse = components['schemas']['InsightsResponse'];
export type ClarificationInsight = components['schemas']['ClarificationInsight'];

// ---- Market Context Types (for insight enrichment) ----
export interface InsightMarketContext {
	percentile_position: number | null;
	comparison_text: string | null;
	source_url: string | null;
	enriched_at: string | null;
}

export interface InsightEnrichResponse {
	success: boolean;
	enriched: boolean;
	percentile_position: number | null;
	comparison_text: string | null;
	error: string | null;
}

// ---- Context Update Types ----
export type ContextUpdateSource = components['schemas']['ContextUpdateSource'];
export type ContextUpdateSuggestion = components['schemas']['ContextUpdateSuggestion'];
export type PendingUpdatesResponse = components['schemas']['PendingUpdatesResponse'];
export type ApproveUpdateResponse = components['schemas']['ApproveUpdateResponse'];

// ---- Objective Progress Types (manual until next type generation) ----
export interface ObjectiveProgress {
	current: string;
	target: string;
	unit?: string | null;
	updated_at: string;
}

export interface ObjectiveProgressUpdate {
	current: string;
	target: string;
	unit?: string | null;
}

export interface ObjectiveProgressResponse {
	objective_index: number;
	objective_text: string;
	progress: ObjectiveProgress | null;
}

export interface ObjectiveProgressListResponse {
	objectives: ObjectiveProgressResponse[];
	count: number;
}

// ---- Admin Types ----
export type UserInfo = components['schemas']['UserInfo'];
export type UserListResponse = components['schemas']['UserListResponse'];
export type BetaWhitelistEntry = components['schemas']['BetaWhitelistEntry'];
export type BetaWhitelistResponse = components['schemas']['BetaWhitelistResponse'];
export type WaitlistEntry = components['schemas']['WaitlistEntry'];
export type ApproveWaitlistResponse = components['schemas']['ApproveWaitlistResponse'];

// ---- Task/Extracted Task Types ----
export type TaskWithStatus = components['schemas']['TaskWithStatus'];
export type SessionActionsResponse = components['schemas']['SessionActionsResponse'];

// ---- Dependency Types ----
export type DependencyResponse = components['schemas']['DependencyResponse'];
export type DependencyListResponse = components['schemas']['DependencyListResponse'];

// ---- Tag Types ----
export type TagResponse = components['schemas']['TagResponse'];
export type TagListResponse = components['schemas']['TagListResponse'];

// ---- Dataset Types ----
export type DatasetResponse = components['schemas']['DatasetResponse'];
export type DatasetDetailResponse = components['schemas']['DatasetDetailResponse'];
export type DatasetListResponse = components['schemas']['DatasetListResponse'];
export type DatasetProfileResponse = components['schemas']['DatasetProfileResponse'];
export type QueryResultResponse = components['schemas']['QueryResultResponse'];
export type ChartResultResponse = components['schemas']['ChartResultResponse'];
export type ChartSpec = components['schemas']['ChartSpec'];
export type DatasetAnalysisResponse = components['schemas']['DatasetAnalysisResponse'];
export type DatasetAnalysisListResponse = components['schemas']['DatasetAnalysisListResponse'];
export type ConversationResponse = components['schemas']['ConversationResponse'];
export type ConversationDetailResponse = components['schemas']['ConversationDetailResponse'];
export type ConversationListResponse = components['schemas']['ConversationListResponse'];
export type ConversationMessage = components['schemas']['ConversationMessage'];

// ---- Dataset Folder Types ----
export interface DatasetFolderResponse {
	id: string;
	name: string;
	description: string | null;
	color: string | null;
	icon: string | null;
	parent_folder_id: string | null;
	tags: string[];
	dataset_count: number;
	created_at: string;
	updated_at: string;
}

export interface DatasetFolderTree extends DatasetFolderResponse {
	children: DatasetFolderTree[];
}

export interface DatasetFolderListResponse {
	folders: DatasetFolderResponse[];
	total: number;
}

export interface DatasetFolderTreeResponse {
	folders: DatasetFolderTree[];
	total: number;
}

export interface DatasetFolderCreate {
	name: string;
	description?: string | null;
	color?: string | null;
	icon?: string | null;
	parent_folder_id?: string | null;
	tags?: string[];
}

export interface DatasetFolderUpdate {
	name?: string | null;
	description?: string | null;
	color?: string | null;
	icon?: string | null;
	parent_folder_id?: string | null;
	tags?: string[] | null;
}

export interface FolderDatasetResponse {
	id: string;
	name: string;
	added_at: string;
}

export interface FolderDatasetsListResponse {
	datasets: FolderDatasetResponse[];
	total: number;
}

export interface FolderTagsResponse {
	tags: string[];
}

export interface AddDatasetsResponse {
	added: number;
	total_requested: number;
}

// ---- Mentor Types ----
export type MentorConversationResponse = components['schemas']['MentorConversationResponse'];
export type MentorConversationDetailResponse = components['schemas']['MentorConversationDetailResponse'];
export type MentorConversationListResponse = components['schemas']['MentorConversationListResponse'];
export type MentorMessage = components['schemas']['MentorMessage'];
export type MentorPersonaResponse = components['schemas']['MentorPersonaResponse'];
export type MentorPersonaListResponse = components['schemas']['MentorPersonaListResponse'];
export type MentionSuggestion = components['schemas']['MentionSuggestion'];
export type MentionSearchResponse = components['schemas']['MentionSearchResponse'];

// ---- Advisor Search Types ----
/**
 * A single search result from conversation search.
 */
export interface ConversationSearchResult {
	/** ID of the matching conversation */
	conversation_id: string;
	/** Preview of the matching message */
	preview: string;
	/** Similarity score (0-1) */
	similarity: number;
	/** ISO timestamp of the message */
	created_at: string;
}

/**
 * Response from searching advisor conversations.
 */
export interface ConversationSearchResponse {
	/** Matching conversations sorted by similarity */
	matches: ConversationSearchResult[];
	/** Total number of matches */
	total: number;
}

/**
 * Response for blindspot discussions endpoint.
 */
export interface BlindspotDiscussionResponse {
	/** The blindspot ID queried */
	blindspot_id: string;
	/** Conversations about this blindspot */
	discussions: MentorConversationResponse[];
	/** Total discussion count */
	total: number;
}

// ---- Dataset Similarity Types ----
/**
 * A dataset similar to the query dataset.
 */
export interface SimilarDataset {
	/** Dataset UUID */
	dataset_id: string;
	/** Dataset name */
	name: string;
	/** Similarity score (0-1) */
	similarity: number;
	/** Column names in common with source dataset */
	shared_columns: string[];
	/** Preview of dataset summary/insight */
	insight_preview: string | null;
}

/**
 * Response from similar datasets endpoint.
 */
export interface SimilarDatasetsResponse {
	/** Similar datasets sorted by similarity */
	similar: SimilarDataset[];
	/** Source dataset ID for the query */
	query_dataset_id: string;
	/** Similarity threshold used */
	threshold: number;
}

// ---- Workspace & Invitation Types ----
export type WorkspaceResponse = components['schemas']['WorkspaceResponse'];
export type WorkspaceListResponse = components['schemas']['WorkspaceListResponse'];
export type WorkspaceMemberResponse = components['schemas']['WorkspaceMemberResponse'];
export type InvitationResponse = components['schemas']['InvitationResponse'];
export type InvitationListResponse = components['schemas']['InvitationListResponse'];
export type InvitationStatus = components['schemas']['InvitationStatus'];
export type MemberRole = components['schemas']['WorkspaceRole'];  // Renamed from MemberRole
export type JoinRequestResponse = components['schemas']['JoinRequestResponse'];
export type JoinRequestListResponse = components['schemas']['JoinRequestListResponse'];
export type JoinRequestStatus = components['schemas']['JoinRequestStatus'];
export type WorkspaceDiscoverability = components['schemas']['WorkspaceDiscoverability'];
export type RoleChangeResponse = components['schemas']['RoleChangeResponse'];
export type RoleHistoryResponse = components['schemas']['RoleHistoryResponse'];

// ---- Benchmark Types ----
export type BenchmarkCategory = components['schemas']['BenchmarkCategory'];
/** @deprecated Use AlignedBenchmarkComparison for objective-aware benchmarks */
export type BenchmarkComparison = components['schemas']['backend__api__industry_insights__BenchmarkComparison'];
export type BenchmarkComparisonResponse = components['schemas']['BenchmarkComparisonResponse'];
export type BenchmarkHistoryEntry = components['schemas']['BenchmarkHistoryEntry'];
export type IndustryInsight = components['schemas']['IndustryInsight'];
export type IndustryInsightsResponse = components['schemas']['IndustryInsightsResponse'];
export type StaleBenchmarkResponse = components['schemas']['StaleBenchmarkResponse'];
export type StaleBenchmarksResponse = components['schemas']['StaleBenchmarksResponse'];
export type StaleFieldSummary = components['schemas']['StaleFieldSummary'];

/** Extended benchmark comparison with objective alignment fields */
export interface AlignedBenchmarkComparison extends BenchmarkComparison {
	/** Relevance to user's objective (0.0-1.0) */
	relevance_score?: number | null;
	/** Why this metric matters for user's objective */
	relevance_reason?: string | null;
	// is_objective_aligned inherited from BenchmarkComparison (required boolean)
}

/** @deprecated Use StaleBenchmarkResponse */
export type StaleBenchmark = StaleBenchmarkResponse;

// ---- Usage & Tier Types ----
export type UsageResponse = components['schemas']['UsageResponse'];
export type UsageMetricResponse = components['schemas']['UsageMetricResponse'];
/** @deprecated Use UsageMetricResponse */
export type UsageMetric = components['schemas']['UsageMetricResponse'];
export type TierLimitsResponse = components['schemas']['TierLimitsResponse'];

// ---- Feedback Types ----
export type FeedbackResponse = components['schemas']['FeedbackResponse'];
export type FeedbackListResponse = components['schemas']['FeedbackListResponse'];
export type FeedbackStats = components['schemas']['FeedbackStats'];

// ---- Value Metrics Types ----
export type ValueMetricResponse = components['schemas']['ValueMetricResponse'];
export type ValueMetricsResponse = components['schemas']['ValueMetricsResponse'];

// ---- Extended KPIs Types (Admin) ----
export type ExtendedKPIsResponse = components['schemas']['ExtendedKPIsResponse'];
export type MentorSessionStats = components['schemas']['MentorSessionStats'];
export type DataAnalysisStats = components['schemas']['DataAnalysisStats'];
export type ProjectStats = components['schemas']['ProjectStats'];
export type ActionStats = components['schemas']['ActionStats'];

// ---- Kanban Types ----
export type KanbanColumn = components['schemas']['KanbanColumn'];
export type KanbanColumnsResponse = components['schemas']['KanbanColumnsResponse'];

// ---- Blog Types ----
export type BlogPostResponse = components['schemas']['BlogPostResponse'];
export type BlogPostListResponse = components['schemas']['BlogPostListResponse'];

// ---- Meeting Template Types ----
export type MeetingTemplate = components['schemas']['MeetingTemplate'];
export type MeetingTemplateListResponse = components['schemas']['MeetingTemplateListResponse'];
export type MeetingTemplateCreate = components['schemas']['MeetingTemplateCreate'];
export type MeetingTemplateUpdate = components['schemas']['MeetingTemplateUpdate'];

// ---- Request Types (used for API calls) ----
export type CreateSessionRequest = components['schemas']['CreateSessionRequest'];
export type ClarificationRequest = components['schemas']['ClarificationRequest'];
export type ActionStatusUpdate = components['schemas']['ActionStatusUpdate'];
export type ActionDatesUpdate = components['schemas']['ActionDatesUpdate'];
export type ActionUpdateCreate = components['schemas']['ActionUpdateCreate'];
export type ActionCloseRequest = components['schemas']['ActionCloseRequest'];
export type ActionCloneReplanRequest = components['schemas']['ActionCloneReplanRequest'];
export type ActionTagsUpdate = components['schemas']['ActionTagsUpdate'];
export type BlockActionRequest = components['schemas']['BlockActionRequest'];
export type UnblockActionRequest = components['schemas']['UnblockActionRequest'];
export type DependencyCreate = components['schemas']['DependencyCreate'];
export type ProjectCreate = components['schemas']['ProjectCreate'];
export type ProjectUpdate = components['schemas']['ProjectUpdate'];
export type ProjectStatusUpdate = components['schemas']['ProjectStatusUpdate'];
export type TagCreate = components['schemas']['TagCreate'];
export type TagUpdate = components['schemas']['TagUpdate'];
export type QuerySpec = components['schemas']['QuerySpec'];
export type FilterSpec = components['schemas']['FilterSpec'];
export type AggregateSpec = components['schemas']['AggregateSpec'];
export type GroupBySpec = components['schemas']['GroupBySpec'];
export type TrendSpec = components['schemas']['TrendSpec'];
export type CompareSpec = components['schemas']['CompareSpec'];
export type CorrelateSpec = components['schemas']['CorrelateSpec'];
export type AskRequest = components['schemas']['backend__api__models__AskRequest'];
export type MentorChatRequest = components['schemas']['MentorChatRequest'];
export type WorkspaceCreate = components['schemas']['WorkspaceCreate'];
export type WorkspaceUpdate = components['schemas']['WorkspaceUpdate'];
export type WorkspaceSettingsUpdate = components['schemas']['WorkspaceSettingsUpdate'];
export type InvitationCreate = components['schemas']['InvitationCreate'];
export type InvitationAcceptRequest = components['schemas']['InvitationAcceptRequest'];
export type InvitationDeclineRequest = components['schemas']['InvitationDeclineRequest'];
export type TransferOwnershipRequest = components['schemas']['TransferOwnershipRequest'];
export type FeedbackCreate = components['schemas']['FeedbackCreate'];
export type ReminderSettingsUpdate = components['schemas']['ReminderSettingsUpdate'];
export type SnoozeReminderRequest = components['schemas']['SnoozeReminderRequest'];
export type RaiseHandRequest = components['schemas']['RaiseHandRequest'];
export type ReplanRequest = components['schemas']['ReplanRequest'];
export type AutogenCreateRequest = components['schemas']['AutogenCreateRequest'];
export type ContextCreateRequest = components['schemas']['ContextCreateRequest'];
export type TaskStatusUpdate = components['schemas']['TaskStatusUpdate'];

// Legacy aliases for request types
/** @deprecated Use ProjectCreate */
export type ProjectCreateRequest = components['schemas']['ProjectCreate'];
/** @deprecated Use ProjectUpdate */
export type ProjectUpdateRequest = components['schemas']['ProjectUpdate'];
/** @deprecated Use ActionUpdateCreate */
export type ActionUpdateCreateRequest = components['schemas']['ActionUpdateCreate'];
/** @deprecated Use ActionDatesUpdate */
export type ActionDatesUpdateRequest = components['schemas']['ActionDatesUpdate'];
/** @deprecated Use TagCreate */
export type TagCreateRequest = components['schemas']['TagCreate'];
/** @deprecated Use TagUpdate */
export type TagUpdateRequest = components['schemas']['TagUpdate'];
/** @deprecated Use ActionTagsUpdate */
export type ActionTagsUpdateRequest = components['schemas']['ActionTagsUpdate'];
/** @deprecated Use ReminderSettingsUpdate */
export type ReminderSettingsUpdateRequest = components['schemas']['ReminderSettingsUpdate'];
/** @deprecated Use TaskStatusUpdate */
export type TaskStatusUpdateRequest = components['schemas']['TaskStatusUpdate'];

// ---- Response Types (additional) ----
export type ReplanResponse = components['schemas']['ReplanResponse'];
export type ActionCloneReplanResponse = components['schemas']['ActionCloneReplanResponse'];
export type ActionDatesResponse = components['schemas']['ActionDatesResponse'];
export type DependencyAddedResponse = components['schemas']['DependencyAddedResponse'];
export type DependencyRemovedResponse = components['schemas']['DependencyRemovedResponse'];
export type ActionBlockedResponse = components['schemas']['ActionBlockedResponse'];
export type ActionUnblockedResponse = components['schemas']['ActionUnblockedResponse'];
export type UnblockSuggestion = components['schemas']['UnblockSuggestionModel'];
export type UnblockPathsResponse = components['schemas']['UnblockPathsResponse'];
export type AutogenSuggestion = components['schemas']['AutogenSuggestion'];
export type AutogenSuggestionsResponse = components['schemas']['AutogenSuggestionsResponse'];
export type AutogenCreateResponse = components['schemas']['AutogenCreateResponse'];
export type ContextProjectSuggestion = components['schemas']['ContextProjectSuggestion'];
export type ContextSuggestionsResponse = components['schemas']['ContextSuggestionsResponse'];
export type ReminderSnoozedResponse = components['schemas']['ReminderSnoozedResponse'];
export type CostCalculatorDefaults = components['schemas']['CostCalculatorDefaults'];

// =============================================================================
// Frontend-Only Types (not in backend)
// =============================================================================

/**
 * Honeypot fields for bot detection - should always be empty from legitimate users
 */
export interface HoneypotFields {
	_hp_email?: string;
	_hp_url?: string;
	_hp_phone?: string;
}

/**
 * Context IDs for attaching past meetings, actions, and datasets to a new session
 */
export interface SessionContextIds {
	meetings?: string[];
	actions?: string[];
	datasets?: string[];
}

/**
 * Extended session create request with honeypot fields
 */
export interface CreateSessionRequestWithHoneypot extends HoneypotFields {
	problem_statement: string;
	problem_context?: Record<string, unknown>;
	dataset_id?: string;
	context_ids?: SessionContextIds;
}

/**
 * Meeting cap status for beta rate limiting
 */
export interface MeetingCapStatus {
	allowed: boolean;
	remaining: number;
	limit: number;
	reset_time: string | null;
	exceeded: boolean;
	recent_count: number;
}

/**
 * Failed meeting info for dashboard alert
 */
export interface FailedMeeting {
	session_id: string;
	problem_statement_preview: string;
	created_at: string;
}

/**
 * Recent failures response for dashboard alert
 */
export interface RecentFailuresResponse {
	count: number;
	failures: FailedMeeting[];
}

/**
 * Structured API error response.
 */
export interface ApiError {
	/** Legacy string detail (deprecated - use message) */
	detail?: string;
	/** HTTP status code */
	status?: number;
	/** Machine-readable error code for programmatic handling */
	error_code?: string;
	/** Human-readable error message */
	message?: string;
	/** Rate limit reset time (ISO 8601) for 429 errors */
	reset_time?: string;
	/** Rate limit for 429 errors */
	limit?: number;
	/** Remaining requests for 429 errors */
	remaining?: number;
}

/**
 * Session events response (for event history)
 */
export interface SessionEventsResponse {
	session_id: string;
	events: SSEEvent[];
	count: number;
}

// Re-export SSE event types for convenience
export type { SSEEvent, SSEEventType, SSEEventMap, SSEEventHandlers } from './sse-events';
export type {
	WorkingStatusPayload,
	CompletePayload,
	ErrorPayload,
	ContributionPayload,
	ConvergencePayload,
	VotingCompletePayload,
	SynthesisCompletePayload
} from './sse-events';

// =============================================================================
// Legacy Type Aliases (for backward compatibility during migration)
// =============================================================================
// These aliases map old names to generated types. New code should import
// the generated type names directly.

/** @deprecated Use UserContext from BusinessContext fields */
export type UserContext = components['schemas']['BusinessContext'];

/** @deprecated Use UserInfo */
export type AdminUser = components['schemas']['UserInfo'];

/** @deprecated Use UserListResponse */
export type AdminUserListResponse = components['schemas']['UserListResponse'];

/** @deprecated Use BetaWhitelistEntry */
export type WhitelistEntry = components['schemas']['BetaWhitelistEntry'];

/** @deprecated Use BetaWhitelistResponse */
export type WhitelistResponse = components['schemas']['BetaWhitelistResponse'];

/** @deprecated Use DatasetResponse */
export type Dataset = components['schemas']['DatasetResponse'];

/** @deprecated Use MentorPersonaResponse['id'] */
export type MentorPersonaId = 'general' | 'action_coach' | 'data_analyst';

/** @deprecated Use MentorPersonaResponse */
export type MentorPersonaDetail = components['schemas']['MentorPersonaResponse'];

// =============================================================================
// Derived Frontend Types
// =============================================================================

/**
 * Stale insight warning shown on session creation
 */
export interface StaleInsight {
	question: string;
	days_stale: number;
}

/**
 * Extracted task from synthesis (subset of TaskWithStatus without status)
 */
export interface ExtractedTask {
	id: string;
	title: string;
	description: string;
	what_and_how: string[];
	success_criteria: string[];
	kill_criteria: string[];
	dependencies: string[];
	timeline: string;
	priority: string;
	category: string;
	source_section: string | null;
	confidence: number;
	sub_problem_index: number | null;
	suggested_completion_date?: string | null;
	updated_at?: string | null;
}

/**
 * Task with session context for global actions view
 */
export interface TaskWithSessionContext extends TaskWithStatus {
	session_id: string;
	/** Status of source session (completed/failed). 'failed' indicates action from acknowledged failure. */
	source_session_status: string | null;
	problem_statement: string;
	/** Frontend-derived field for due date filtering */
	suggested_completion_date?: string | null;
	/** Last update timestamp */
	updated_at?: string | null;
	/** User-set planned start date (YYYY-MM-DD) */
	target_start_date?: string | null;
	/** User-set planned end date (YYYY-MM-DD) */
	target_end_date?: string | null;
	/** AI-estimated start date (YYYY-MM-DD) */
	estimated_start_date?: string | null;
	/** AI-estimated end date (YYYY-MM-DD) */
	estimated_end_date?: string | null;
	/** AI-estimated duration in days */
	estimated_duration_days?: number | null;
}

/**
 * Session with tasks for global actions view
 */
export interface SessionWithTasks {
	session_id: string;
	problem_statement: string;
	session_status: string;
	created_at: string | null;
	extracted_at: string | null;
	tasks: TaskWithSessionContext[];
	task_count: number;
	by_status: Record<string, number>;
}

/**
 * Global gantt action data
 */
export interface GlobalGanttActionData {
	id: string;
	name: string;
	start: string;
	end: string;
	progress: number;
	dependencies: string;
	status: ActionStatus;
	priority: string;
	session_id: string;
}

/**
 * Global gantt dependency
 */
export interface GlobalGanttDependency {
	action_id: string;
	depends_on_id: string;
	dependency_type: string;
	lag_days: number;
}

/**
 * SSE event types for dataset Q&A streaming
 */
export type DatasetAskEventType = 'token' | 'query_spec' | 'chart_spec' | 'done' | 'error';

export interface DatasetAskEvent {
	type: DatasetAskEventType;
	data: string | Record<string, unknown>;
	conversation_id?: string;
}

/**
 * SSE event types for mentor chat streaming
 */
export type MentorChatEventType = 'thinking' | 'context' | 'response' | 'done' | 'error';

/**
 * Resolved mention reference (returned in done event)
 */
export interface MentionRef {
	id: string;
	title: string;
}

/**
 * Resolved mentions in done event
 */
export interface ResolvedMentions {
	meetings?: MentionRef[];
	actions?: MentionRef[];
	datasets?: MentionRef[];
}

/**
 * Query type enum
 */
export type QueryType = 'filter' | 'aggregate' | 'trend' | 'compare' | 'correlate';

/**
 * Filter operator enum
 */
export type FilterOperator = 'eq' | 'ne' | 'gt' | 'lt' | 'gte' | 'lte' | 'contains' | 'in';

/**
 * Aggregate function enum
 */
export type AggregateFunction = 'sum' | 'avg' | 'min' | 'max' | 'count' | 'distinct';

/**
 * Trend interval enum
 */
export type TrendInterval = 'day' | 'week' | 'month' | 'quarter' | 'year';

/**
 * Correlation method enum
 */
export type CorrelationMethod = 'pearson' | 'spearman';

/**
 * Chart type enum
 */
export type ChartType = 'line' | 'bar' | 'pie' | 'scatter';

/**
 * Dataset source type enum
 */
export type DatasetSourceType = 'csv' | 'sheets' | 'api';

/**
 * Dependency type enum
 */
export type DependencyType = 'finish_to_start' | 'start_to_start' | 'finish_to_finish';

/**
 * Action update type enum
 */
export type ActionUpdateType =
	| 'progress'
	| 'blocker'
	| 'note'
	| 'status_change'
	| 'date_change'
	| 'completion';

/**
 * Feedback type enum
 */
export type FeedbackType = 'feature_request' | 'problem_report';

/**
 * Feedback status enum
 */
export type FeedbackStatus = 'new' | 'reviewing' | 'resolved' | 'closed';

/**
 * Metric type classification for color coding
 */
export type MetricType = 'higher_is_better' | 'lower_is_better' | 'neutral';

/**
 * Insight content base
 */
export interface InsightContent {
	title: string;
	description: string;
	metadata?: Record<string, unknown>;
}

/**
 * Benchmark content with percentile data
 */
export interface BenchmarkContent extends InsightContent {
	metric_name: string;
	metric_unit: string;
	category: BenchmarkCategory;
	industry_segment: string;
	p25?: number;
	p50?: number;
	p75?: number;
	sample_size?: number;
}

/**
 * A pending context update with frontend-friendly typing
 */
export interface ContextUpdateSuggestionUI {
	id: string;
	field_name: string;
	new_value: string | number | string[];
	current_value?: string | number | string[] | null;
	confidence: number;
	source_type: ContextUpdateSource;
	source_text: string;
	extracted_at: string;
	session_id?: string | null;
}

// =============================================================================
// Session-Project Linking Types (Frontend Convenience)
// =============================================================================

/**
 * A project linked to a session (UI view)
 */
export interface SessionProjectItem {
	project_id: string;
	name: string;
	description: string | null;
	status: ProjectStatus;
	progress_percent: number;
	relationship: string;
	linked_at: string | null;
}

/**
 * Response with session's linked projects
 */
export interface SessionProjectsResponse {
	session_id: string;
	projects: SessionProjectItem[];
}

/**
 * A project available for linking
 */
export interface AvailableProjectItem {
	id: string;
	name: string;
	description: string | null;
	status: ProjectStatus;
	progress_percent: number;
	is_linked: boolean;
}

/**
 * Response with available projects
 */
export interface AvailableProjectsResponse {
	session_id: string;
	projects: AvailableProjectItem[];
}

/**
 * A project suggestion from meeting analysis
 */
export interface ProjectSuggestion {
	name: string;
	description: string;
	action_ids: string[];
	confidence: number;
	rationale: string;
}

/**
 * Response with project suggestions
 */
export interface ProjectSuggestionsResponse {
	session_id: string;
	suggestions: ProjectSuggestion[];
}

/**
 * Unassigned actions count response
 */
export interface UnassignedCountResponse {
	unassigned_count: number;
	min_required: number;
	can_autogenerate: boolean;
}

/**
 * Task extraction response (legacy)
 */
export interface TaskExtractionResponse {
	tasks: ExtractedTask[];
	total_tasks: number;
	extraction_confidence: number;
	synthesis_sections_analyzed: string[];
}

/**
 * Tier limit error (429 response)
 */
export interface TierLimitError {
	error: 'tier_limit_exceeded';
	metric: string;
	current: number;
	limit: number;
	remaining: number;
	reset_at: string | null;
	upgrade_prompt: string;
}

/**
 * User context response (wraps BusinessContext)
 */
export interface UserContextResponse {
	exists: boolean;
	context?: BusinessContext;
	updated_at?: string;
}

/**
 * A value metric with trend information
 */
export interface ValueMetric {
	name: string;
	label: string;
	current_value: string | number | null;
	previous_value: string | number | null;
	change_percent: number | null;
	trend_direction: TrendDirection;
	metric_type: MetricType;
	last_updated: string | null;
	is_positive_change: boolean | null;
}

/**
 * Public blog post (published content only)
 */
export interface PublicBlogPost {
	id: string;
	title: string;
	slug: string;
	content?: string;
	excerpt?: string;
	status: 'published';
	published_at?: string;
	seo_keywords?: string[];
	meta_title?: string;
	meta_description?: string;
	created_at: string;
	updated_at: string;
}

/**
 * Public blog post list response
 */
export interface PublicBlogPostListResponse {
	posts: PublicBlogPost[];
	total: number;
}

/**
 * Public decision (SEO decision library)
 */
export interface PublicDecision {
	category: string;
	slug: string;
	title: string;
	meta_description?: string;
	founder_context?: {
		stage?: string;
		constraints?: string[];
		situation?: string;
	};
	expert_perspectives?: Array<{
		persona_name: string;
		persona_code?: string;
		quote: string;
	}>;
	synthesis?: string;
	faqs?: Array<{
		question: string;
		answer: string;
	}>;
	published_at?: string;
	featured_image_url?: string;
	seo_keywords?: string[];
	reading_time_minutes?: number;
	meta_title?: string;
}

/**
 * Public decision list item (for index pages)
 */
export interface PublicDecisionListItem {
	id: string;
	category: string;
	slug: string;
	title: string;
	meta_description?: string;
	founder_context?: {
		stage?: string;
		constraints?: string[];
		situation?: string;
	};
	published_at?: string;
	created_at: string;
	updated_at: string;
	view_count: number;
	click_through_count: number;
}

/**
 * Public decision list response
 */
export interface PublicDecisionListResponse {
	decisions: PublicDecisionListItem[];
	total: number;
}

/**
 * Decision category with count
 */
export interface DecisionCategoryCount {
	category: string;
	count: number;
}

/**
 * Decision categories response
 */
export interface DecisionCategoriesResponse {
	categories: DecisionCategoryCount[];
}

/**
 * Featured decision for homepage
 */
export interface FeaturedDecision {
	id: string;
	category: string;
	slug: string;
	title: string;
	meta_description?: string;
	synthesis?: string;
	homepage_order?: number | null;
}

/**
 * Featured decisions response
 */
export interface FeaturedDecisionsResponse {
	decisions: FeaturedDecision[];
}

/**
 * Waitlist response (admin)
 */
export interface WaitlistResponse {
	total_count: number;
	pending_count: number;
	entries: WaitlistEntry[];
}

/**
 * Waitlist approval response
 */
export interface WaitlistApprovalResponse {
	email: string;
	whitelist_added: boolean;
	email_sent: boolean;
	message: string;
}

/**
 * Project sessions response
 */
export interface ProjectSessionsResponse {
	sessions: ProjectSessionLink[];
}

/**
 * Dependency mutation response (add/remove operations)
 */
export interface DependencyMutationResponse {
	message: string;
	action_id: string;
	depends_on_action_id?: string;
	depends_on_id?: string;
	auto_blocked?: boolean;
	auto_unblocked?: boolean;
	blocking_reason?: string | null;
	new_status?: ActionStatus | null;
}

/**
 * Session-project link request
 */
export interface SessionProjectLinkRequest {
	project_ids: string[];
	relationship?: 'discusses' | 'created_from' | 'replanning';
}

/**
 * Response from creating a suggested project
 */
export interface CreatedProjectResponse {
	project: {
		id: string;
		name: string;
		description: string | null;
		status: ProjectStatus;
		progress_percent: number;
		total_actions: number;
	};
	session_id: string;
	action_count: number;
}

/**
 * Admin user update request
 */
export interface AdminUserUpdateRequest {
	subscription_tier?: string;
	is_admin?: boolean;
}

/**
 * Action create request (frontend variant)
 */
export interface ActionCreateRequest {
	title: string;
	description: string;
	what_and_how?: string[];
	success_criteria?: string[];
	kill_criteria?: string[];
	priority?: 'high' | 'medium' | 'low';
	category?: 'implementation' | 'research' | 'decision' | 'communication';
	timeline?: string | null;
	estimated_duration_days?: number | null;
	target_start_date?: string | null;
	target_end_date?: string | null;
}

/**
 * Action update request (frontend variant)
 */
export interface ActionUpdateRequest {
	title?: string;
	description?: string;
	what_and_how?: string[];
	success_criteria?: string[];
	kill_criteria?: string[];
	priority?: 'high' | 'medium' | 'low';
	category?: 'implementation' | 'research' | 'decision' | 'communication';
	timeline?: string | null;
	estimated_duration_days?: number | null;
	target_start_date?: string | null;
	target_end_date?: string | null;
}

/**
 * Feedback create request with honeypot
 */
export interface FeedbackCreateRequest extends HoneypotFields {
	type: FeedbackType;
	title: string;
	description: string;
	include_context?: boolean;
}

/**
 * Feedback context (auto-attached)
 */
export interface FeedbackContext {
	user_tier?: string;
	page_url?: string;
	user_agent?: string;
	timestamp?: string;
}

/**
 * Dataset analysis record (chart/query history) - frontend view
 */
export interface DatasetAnalysis {
	id: string;
	dataset_id: string;
	query_spec?: Record<string, unknown> | null;
	chart_spec?: ChartSpec | null;
	chart_url?: string | null;
	title?: string | null;
	created_at: string;
}

/**
 * Dataset column profile
 */
export interface DatasetProfile {
	id: string;
	column_name: string;
	data_type: string;
	null_count: number | null;
	unique_count: number | null;
	min_value: string | null;
	max_value: string | null;
	mean_value: number | null;
	sample_values: unknown[] | null;
}

// =============================================================================
// Dataset Insight Types (Business Intelligence)
// =============================================================================

export type BusinessDomain =
	| 'ecommerce'
	| 'saas'
	| 'services'
	| 'marketing'
	| 'finance'
	| 'operations'
	| 'hr'
	| 'product'
	| 'unknown';

export type InsightSeverity = 'positive' | 'neutral' | 'warning' | 'critical';
export type InsightType = 'trend' | 'pattern' | 'anomaly' | 'risk' | 'opportunity' | 'benchmark';

export interface DataIdentity {
	domain: BusinessDomain;
	confidence: number;
	entity_type: string;
	description: string;
	time_range: string | null;
}

export interface HeadlineMetric {
	label: string;
	value: string;
	context: string | null;
	trend: string | null;
	is_good: boolean | null;
}

export interface Insight {
	type: InsightType;
	severity: InsightSeverity;
	headline: string;
	detail: string;
	metric: string | null;
	action: string | null;
}

export interface DataQualityScore {
	overall_score: number;
	completeness: number;
	consistency: number;
	freshness: number | null;
	issues: string[];
	missing_data: string[];
	suggestions: string[];
}

export interface ColumnSemantic {
	column_name: string;
	technical_type: string;
	semantic_type: string;
	confidence: number;
	business_meaning: string;
	sample_insight: string | null;
}

export interface SuggestedQuestion {
	question: string;
	category: string;
	why_relevant: string;
}

export interface SuggestedChart {
	chart_spec: ChartSpec;
	title: string;
	rationale: string;
}

export interface ObjectiveAlignment {
	score: number;
	summary: string;
	strengths: string[];
	gaps: string[];
	recommendations: string[];
}

export interface DatasetInsights {
	identity: DataIdentity;
	headline_metrics: HeadlineMetric[];
	insights: Insight[];
	quality: DataQualityScore;
	suggested_questions: SuggestedQuestion[];
	column_semantics: ColumnSemantic[];
	narrative_summary: string;
	suggested_charts?: SuggestedChart[];
	objective_alignment?: ObjectiveAlignment;
}

export interface DatasetInsightsResponse {
	insights: DatasetInsights;
	generated_at: string;
	model_used: string;
	tokens_used: number;
	cached: boolean;
}

// =============================================================================
// Competitor Insight Types
// =============================================================================

/**
 * AI-generated competitor insight card
 */
export interface CompetitorInsight {
	name: string;
	tagline: string | null;
	size_estimate: string | null;
	revenue_estimate: string | null;
	strengths: string[];
	weaknesses: string[];
	market_gaps: string[];
	last_updated: string | null;
}

/**
 * Response from generating a competitor insight
 */
export interface CompetitorInsightResponse {
	success: boolean;
	insight: CompetitorInsight | null;
	error?: string | null;
	generation_status: 'complete' | 'cached' | 'limited_data' | 'error' | null;
}

/**
 * Response from listing competitor insights (tier-gated)
 */
export interface CompetitorInsightsListResponse {
	success: boolean;
	insights: CompetitorInsight[];
	visible_count: number;
	total_count: number;
	tier: string | null;
	upgrade_prompt: string | null;
	error?: string | null;
}

/**
 * AI-generated trend insight from a market trend URL
 */
export interface TrendInsight {
	url: string;
	title: string | null;
	key_takeaway: string | null;
	relevance: string | null;
	actions: string[];
	timeframe: 'immediate' | 'short_term' | 'long_term' | null;
	confidence: 'high' | 'medium' | 'low' | null;
	analyzed_at: string | null;
}

/**
 * Request to analyze a trend URL
 */
export interface TrendInsightRequest {
	url: string;
}

/**
 * Response from analyzing a trend URL
 */
export interface TrendInsightResponse {
	success: boolean;
	insight: TrendInsight | null;
	error?: string | null;
	analysis_status: 'complete' | 'cached' | 'limited_data' | 'error' | null;
}

/**
 * Response from listing trend insights
 */
export interface TrendInsightsListResponse {
	success: boolean;
	insights: TrendInsight[];
	count: number;
	error?: string | null;
}

// =============================================================================
// Managed Competitor Types (User-submitted competitor list)
// =============================================================================

/**
 * Relevance flags for a competitor
 */
export interface RelevanceFlags {
	similar_product: boolean;
	same_icp: boolean;
	same_market: boolean;
}

/**
 * A user-managed competitor entry
 */
export interface ManagedCompetitor {
	name: string;
	url: string | null;
	notes: string | null;
	added_at: string;
	/** Relevance score: 1.0=3 checks, 0.66=2, 0.33=1, 0.0=0 */
	relevance_score?: number | null;
	/** Individual relevance check results */
	relevance_flags?: RelevanceFlags | null;
	/** Warning message if <2 checks pass */
	relevance_warning?: string | null;
	// Enrichment fields
	tagline?: string | null;
	product_description?: string | null;
	funding_info?: string | null;
	employee_count?: string | null;
	tech_stack?: string[] | null;
	recent_news?: Array<{ title: string; url: string; date: string }> | null;
	last_enriched_at?: string | null;
	changes_detected?: string[] | null;
	// Deep intelligence fields (Pro tier)
	product_updates?: Array<{
		title: string;
		date: string | null;
		description: string;
		source_url: string | null;
	}> | null;
	key_signals?: string[] | null;
	funding_rounds?: Array<{
		round_type: string;
		amount: string | null;
		date: string | null;
		investors: string[];
	}> | null;
	intel_gathered_at?: string | null;
}

/**
 * Request to add a new managed competitor
 */
export interface ManagedCompetitorCreate {
	name: string;
	url?: string | null;
	notes?: string | null;
}

/**
 * Request to update a managed competitor
 */
export interface ManagedCompetitorUpdate {
	url?: string | null;
	notes?: string | null;
}

/**
 * Response from managed competitor operations
 */
export interface ManagedCompetitorResponse {
	success: boolean;
	competitor: ManagedCompetitor | null;
	error?: string | null;
	relevance_warning?: string | null;
	relevance_score?: number | null;
}

/**
 * Response from listing managed competitors
 */
export interface ManagedCompetitorListResponse {
	success: boolean;
	competitors: ManagedCompetitor[];
	count: number;
	error?: string | null;
}

/**
 * Response from enriching a single managed competitor
 */
export interface ManagedCompetitorEnrichResponse {
	success: boolean;
	competitor: ManagedCompetitor | null;
	changes: string[] | null;
	error?: string | null;
}

/**
 * Response from enriching all managed competitors
 */
export interface ManagedCompetitorBulkEnrichResponse {
	success: boolean;
	enriched_count: number;
	competitors: ManagedCompetitor[];
	errors?: string[] | null;
}

// =============================================================================
// User Ratings (Thumbs Up/Down)
// =============================================================================

/**
 * Rating response from API
 */
export interface RatingResponse {
	id: string;
	user_id: string;
	entity_type: 'meeting' | 'action';
	entity_id: string;
	rating: number;
	comment?: string | null;
	created_at: string;
}

/**
 * Rating metrics for admin dashboard
 */
export interface RatingMetricsResponse {
	period_days: number;
	total: number;
	thumbs_up: number;
	thumbs_down: number;
	thumbs_up_pct: number;
	by_type: {
		meeting: { up: number; down: number };
		action: { up: number; down: number };
	};
}

/**
 * Daily rating trend data point
 */
export interface RatingTrendItem {
	date: string;
	up: number;
	down: number;
	total: number;
}

/**
 * Negative rating item for admin triage
 */
export interface NegativeRatingItem {
	id: string;
	user_id: string;
	user_email?: string | null;
	entity_type: 'meeting' | 'action';
	entity_id: string;
	entity_title?: string | null;
	comment?: string | null;
	created_at: string;
}

/**
 * Response containing negative ratings list
 */
export interface NegativeRatingsResponse {
	items: NegativeRatingItem[];
}

// =============================================================================
// SEO Tools Types
// =============================================================================

/**
 * SEO trend opportunity
 */
export interface SeoTrendOpportunity {
	topic: string;
	trend_direction: string;
	relevance_score: number;
	description: string;
}

/**
 * SEO trend threat
 */
export interface SeoTrendThreat {
	topic: string;
	threat_type: string;
	severity: string;
	description: string;
}

/**
 * SEO trend analysis result
 */
export interface SeoTrendAnalysisResult {
	executive_summary: string;
	key_trends: string[];
	opportunities: SeoTrendOpportunity[];
	threats: SeoTrendThreat[];
	keywords_analyzed: string[];
	industry: string | null;
	sources: string[];
}

/**
 * SEO trend analysis response
 */
export interface SeoTrendAnalysisResponse {
	id: number;
	results: SeoTrendAnalysisResult;
	created_at: string;
	remaining_analyses: number;
}

/**
 * SEO history entry
 */
export interface SeoHistoryEntry {
	id: number;
	keywords: string[];
	industry: string | null;
	executive_summary: string;
	created_at: string;
}

/**
 * SEO history response
 */
export interface SeoHistoryResponse {
	analyses: SeoHistoryEntry[];
	total: number;
	remaining_this_month: number;
}

/**
 * SEO topic status
 */
export type SeoTopicStatus = 'researched' | 'writing' | 'published';

/**
 * SEO topic for blog generation workflow
 */
export interface SeoTopic {
	id: number;
	keyword: string;
	status: SeoTopicStatus;
	source_analysis_id: number | null;
	notes: string | null;
	created_at: string;
	updated_at: string;
}

/**
 * SEO topic create request
 */
export interface SeoTopicCreate {
	keyword: string;
	source_analysis_id?: number | null;
	notes?: string | null;
}

/**
 * SEO topic update request
 */
export interface SeoTopicUpdate {
	status?: SeoTopicStatus;
	notes?: string | null;
}

/**
 * SEO topic list response
 */
export interface SeoTopicListResponse {
	topics: SeoTopic[];
	total: number;
}

/**
 * SEO topics autogenerate response
 */
export interface SeoTopicsAutogenerateResponse {
	topics: SeoTopic[];
	count: number;
}

/**
 * SEO blog article status
 */
export type SeoBlogArticleStatus = 'draft' | 'published';

/**
 * SEO blog article
 */
export interface SeoBlogArticle {
	id: number;
	topic_id: number | null;
	title: string;
	excerpt: string | null;
	content: string;
	meta_title: string | null;
	meta_description: string | null;
	status: SeoBlogArticleStatus;
	created_at: string;
	updated_at: string;
}

/**
 * SEO blog article update request
 */
export interface SeoBlogArticleUpdate {
	title?: string;
	excerpt?: string;
	content?: string;
	meta_title?: string;
	meta_description?: string;
	status?: SeoBlogArticleStatus;
}

/**
 * SEO blog article list response
 */
export interface SeoBlogArticleListResponse {
	articles: SeoBlogArticle[];
	total: number;
	remaining_this_month: number;
}

/**
 * SEO article regeneration request
 */
export interface RegenerateArticleRequest {
	tone?: string;
	changes?: string[];
}

/**
 * A topic suggestion from analyzing user-submitted words
 */
export interface TopicSuggestion {
	keyword: string;
	seo_potential: 'high' | 'medium' | 'low';
	trend_status: 'rising' | 'stable' | 'declining';
	related_keywords: string[];
	description: string;
	/** Validation status from web research */
	validation_status: 'validated' | 'unvalidated';
	/** Competitor presence indicator */
	competitor_presence: 'high' | 'medium' | 'low' | 'unknown';
	/** Search volume indicator */
	search_volume_indicator: 'high' | 'medium' | 'low' | 'unknown';
	/** URLs from validation research */
	validation_sources: string[];
}

/**
 * Request to analyze user-submitted words for topic suggestions
 */
export interface AnalyzeTopicsRequest {
	words: string[];
	/** Skip web research validation for faster response */
	skip_validation?: boolean;
}

/**
 * Response containing topic suggestions
 */
export interface AnalyzeTopicsResponse {
	suggestions: TopicSuggestion[];
	analyzed_words: string[];
}

/**
 * A single discovered trend suggestion
 */
export interface TrendSuggestion {
	title: string;
	description: string;
	suggested_keywords: string[];
	trend_signal: 'rising' | 'emerging' | 'seasonal';
	relevance_to_business: string;
}

/**
 * Response from discover-trends endpoint
 */
export interface DiscoverTrendsResponse {
	suggestions: TrendSuggestion[];
	context_used: Record<string, string | null>;
}

// =============================================================================
// Marketing Assets Types
// =============================================================================

/**
 * Asset type for marketing collateral
 */
export type MarketingAssetType = 'image' | 'animation' | 'concept' | 'template';

/**
 * Marketing asset in the collateral bank
 */
export interface MarketingAsset {
	id: number;
	filename: string;
	cdn_url: string;
	asset_type: MarketingAssetType;
	title: string;
	description: string | null;
	tags: string[];
	file_size: number;
	mime_type: string;
	created_at: string;
	updated_at: string;
}

/**
 * Marketing asset creation request (used with FormData)
 */
export interface MarketingAssetCreate {
	title: string;
	asset_type: MarketingAssetType;
	description?: string;
	tags?: string[];
}

/**
 * Marketing asset update request
 */
export interface MarketingAssetUpdate {
	title?: string;
	description?: string;
	tags?: string[];
}

/**
 * Marketing asset list response
 */
export interface MarketingAssetListResponse {
	assets: MarketingAsset[];
	total: number;
	remaining: number;
}

/**
 * Asset suggestion for article content
 */
export interface AssetSuggestion {
	id: number;
	title: string;
	cdn_url: string;
	asset_type: MarketingAssetType;
	relevance_score: number;
	matching_tags: string[];
}

/**
 * Asset suggestions response
 */
export interface AssetSuggestionsResponse {
	suggestions: AssetSuggestion[];
	article_keywords: string[];
}


// =============================================================================
// Peer Benchmarking Types
// =============================================================================

/**
 * Consent status for peer benchmarking.
 */
export interface PeerBenchmarkConsentStatus {
	consented: boolean;
	consented_at: string | null;
	revoked_at: string | null;
}

/**
 * Consent status for research sharing.
 */
export interface ResearchSharingConsentStatus {
	consented: boolean;
	consented_at: string | null;
	revoked_at: string | null;
}

/**
 * A single peer benchmark metric with percentiles.
 */
export interface PeerBenchmarkMetric {
	metric: string;
	display_name: string;
	p10: number | null;
	p25: number | null;
	p50: number | null;
	p75: number | null;
	p90: number | null;
	sample_count: number;
	user_value: number | null;
	user_percentile: number | null;
	locked: boolean;
}

/**
 * Response containing peer benchmark data.
 */
export interface PeerBenchmarksResponse {
	industry: string;
	metrics: PeerBenchmarkMetric[];
	updated_at: string | null;
	k_anonymity_threshold: number;
	/** Data source type: peer_data, industry_research, or similar_industry */
	source?: 'peer_data' | 'industry_research' | 'similar_industry';
	/** Citation URLs for research-based data */
	sources?: string[] | null;
	/** Confidence score (0-1) for research data */
	confidence?: number | null;
	/** If source is similar_industry, the matched industry name */
	similar_industry?: string | null;
}

/**
 * User's comparison for a single metric.
 */
export interface PeerComparisonMetric {
	metric: string;
	display_name: string;
	user_value: number | null;
	user_percentile: number | null;
	p50: number | null;
	sample_count: number;
}

/**
 * Response containing user's peer comparison.
 */
export interface PeerComparisonResponse {
	industry: string;
	comparisons: PeerComparisonMetric[];
}

/**
 * Preview metric for non-opted users (shows industry median only).
 */
export interface PeerBenchmarkPreviewResponse {
	metric: string;
	display_name: string;
	industry: string;
	p50: number;
	sample_count: number;
}

// ---- Key Metrics Types (Metrics You Need to Know) ----

/**
 * Importance classification for key metrics.
 */
export type MetricImportance = 'now' | 'later' | 'monitor';

/**
 * Source category for key metrics.
 */
export type MetricSourceCategory = 'user' | 'competitor' | 'industry';

/**
 * Trend indicator for a metric.
 */
export type MetricTrendIndicator = 'up' | 'down' | 'stable' | 'unknown';

/**
 * Configuration for a single key metric.
 */
export interface KeyMetricConfig {
	metric_key: string;
	importance: MetricImportance;
	category: MetricSourceCategory;
	display_order: number;
	notes?: string | null;
}

/**
 * Single point in metric history for sparkline visualization.
 */
export interface MetricHistoryPoint {
	value: number | null;
	recorded_at: string;
}

/**
 * Display model for a key metric with current value and trends.
 */
export interface KeyMetricDisplay {
	metric_key: string;
	name: string;
	value: string | number | null;
	unit?: string | null;
	trend: MetricTrendIndicator;
	trend_change?: string | null;
	importance: MetricImportance;
	category: MetricSourceCategory;
	benchmark_value?: string | number | null;
	percentile?: number | null;
	notes?: string | null;
	last_updated?: string | null;
	history?: MetricHistoryPoint[];
}

/**
 * Request to update key metrics configuration.
 */
export interface KeyMetricConfigUpdate {
	metrics: KeyMetricConfig[];
}

/**
 * Response containing user's key metrics.
 */
export interface KeyMetricsResponse {
	success: boolean;
	metrics: KeyMetricDisplay[];
	now_count: number;
	later_count: number;
	monitor_count: number;
	error?: string | null;
}

// =============================================================================
// Insight-to-Metric Auto-Population
// =============================================================================

/**
 * A suggestion to auto-populate a context metric from insights.
 */
export interface MetricSuggestion {
	/** Context field name (e.g., 'revenue', 'customers') */
	field: string;
	/** Current value in context (if any) */
	current_value?: string | null;
	/** Value extracted from insight */
	suggested_value: string;
	/** The clarification question that provided this */
	source_question: string;
	/** Extraction confidence (0-1) */
	confidence: number;
	/** When the insight was recorded (ISO) */
	answered_at?: string | null;
}

/**
 * Response containing metric suggestions from insights.
 */
export interface MetricSuggestionsResponse {
	success: boolean;
	suggestions: MetricSuggestion[];
	count: number;
	error?: string | null;
}

/**
 * Request to apply a single metric suggestion.
 */
export interface ApplyMetricSuggestionRequest {
	/** Context field to update (e.g., 'revenue') */
	field: string;
	/** Value to set */
	value: string;
	/** Original question (for audit trail) */
	source_question?: string | null;
}

/**
 * Response after applying a metric suggestion.
 */
export interface ApplyMetricSuggestionResponse {
	success: boolean;
	field: string;
	new_value: string;
	error?: string | null;
}

// =============================================================================
// Metric Calculation Types (Q&A-guided metric derivation)
// =============================================================================

/**
 * Definition of a metric calculation question.
 */
export interface MetricQuestionDef {
	id: string;
	question: string;
	input_type: 'currency' | 'number' | 'percent';
	placeholder: string;
	help_text?: string | null;
}

/**
 * Response with questions for calculating a metric.
 */
export interface MetricFormulaResponse {
	metric_key: string;
	questions: MetricQuestionDef[];
	result_unit: string;
}

/**
 * A single answer to a calculation question.
 */
export interface MetricCalculationAnswer {
	question_id: string;
	value: number;
}

/**
 * Request to calculate a metric from Q&A answers.
 */
export interface MetricCalculationRequest {
	answers: MetricCalculationAnswer[];
	save_insight?: boolean;
}

/**
 * Response from metric calculation.
 */
export interface MetricCalculationResponse {
	success: boolean;
	calculated_value?: number | null;
	formula_used?: string | null;
	result_unit?: string | null;
	confidence: number;
	insight_saved: boolean;
	error?: string | null;
}

/**
 * Response listing metrics with calculation support.
 */
export interface AvailableMetricsResponse {
	metrics: string[];
}

// =============================================================================
// Business Metrics Insight Suggestion Types
// =============================================================================

/**
 * A suggestion to auto-populate a business metric from insights.
 * Uses keyword-based matching to map insights to specific metrics.
 */
export interface BusinessMetricSuggestion {
	/** Business metric key (e.g., 'mrr', 'churn') */
	metric_key: string;
	/** Display name of the metric */
	metric_name?: string | null;
	/** Current metric value (if any) */
	current_value?: number | null;
	/** Value extracted from insight */
	suggested_value: string;
	/** The clarification question that provided this */
	source_question: string;
	/** Match confidence (0-1) */
	confidence: number;
	/** When the insight was recorded (ISO) */
	answered_at?: string | null;
	/** Whether user dismissed this suggestion */
	is_dismissed: boolean;
}

/**
 * Response containing business metric suggestions from insights.
 */
export interface BusinessMetricSuggestionsResponse {
	success: boolean;
	suggestions: BusinessMetricSuggestion[];
	count: number;
	error?: string | null;
}

/**
 * Request to apply a business metric suggestion.
 */
export interface ApplyBusinessMetricSuggestionRequest {
	/** Business metric key to update (e.g., 'mrr') */
	metric_key: string;
	/** Numeric value to set */
	value: number;
	/** Original question (for audit trail) */
	source_question?: string | null;
}

/**
 * Response after applying a business metric suggestion.
 */
export interface ApplyBusinessMetricSuggestionResponse {
	success: boolean;
	metric_key: string;
	new_value: number;
	error?: string | null;
}

/**
 * Request to dismiss a business metric suggestion.
 */
export interface DismissBusinessMetricSuggestionRequest {
	/** Business metric key to dismiss */
	metric_key: string;
	/** The source question of the suggestion to dismiss */
	source_question: string;
}

// =============================================================================
// Working Pattern (Activity Heatmap)
// =============================================================================

/**
 * User's regular working pattern for activity visualization.
 * Non-working days are greyed out in ActivityHeatmap.
 */
export interface WorkingPattern {
	/** Working days as ISO weekday numbers (1=Mon, 7=Sun). Default: Mon-Fri */
	working_days: number[];
}

/**
 * Response for working pattern endpoint.
 */
export interface WorkingPatternResponse {
	success: boolean;
	pattern: WorkingPattern;
	error?: string | null;
}

/**
 * Request to update working pattern.
 */
export interface WorkingPatternUpdate {
	/** Working days as ISO weekday numbers (1=Mon, 7=Sun). At least one day required. */
	working_days: number[];
}

// =============================================================================
// Heatmap History Depth Types
// =============================================================================

/**
 * User's preferred activity heatmap history depth.
 * Controls how many months of history are shown in the ActivityHeatmap.
 */
export interface HeatmapHistoryDepth {
	/** History depth in months: 1, 3, or 6. Default: 3 */
	history_months: 1 | 3 | 6;
}

/**
 * Response for heatmap history depth endpoint.
 */
export interface HeatmapHistoryDepthResponse {
	success: boolean;
	depth: HeatmapHistoryDepth;
	error?: string | null;
}

/**
 * Request to update heatmap history depth.
 */
export interface HeatmapHistoryDepthUpdate {
	/** History depth in months: 1, 3, or 6 */
	history_months: 1 | 3 | 6;
}

// =============================================================================
// Recent Research (Dashboard Widget)
// =============================================================================

/**
 * A source/citation from research.
 */
export interface ResearchSource {
	url?: string | null;
	title?: string | null;
	snippet?: string | null;
}

/**
 * A recent research item for dashboard display.
 */
export interface RecentResearchItem {
	id: number;
	question: string;
	summary?: string | null;
	sources: ResearchSource[];
	category?: string | null;
	created_at: string;
}

/**
 * Response containing user's recent research for dashboard widget.
 */
export interface RecentResearchResponse {
	success: boolean;
	research: RecentResearchItem[];
	total_count: number;
	error?: string | null;
}

// Research Embeddings Visualization
// =============================================================================

/**
 * A single point in the research embeddings visualization.
 */
export interface ResearchPoint {
	x: number;
	y: number;
	preview: string;
	category: string | null;
	created_at: string;
}

/**
 * Category summary for legend display.
 */
export interface ResearchCategory {
	name: string;
	count: number;
}

/**
 * Response containing user's research embeddings for visualization.
 */
export interface ResearchEmbeddingsResponse {
	success: boolean;
	points: ResearchPoint[];
	categories: ResearchCategory[];
	total_count: number;
	error?: string | null;
}

// =============================================================================
// Dataset Investigation Types (Deterministic Analyses)
// =============================================================================

/**
 * Column role classification
 */
export type ColumnRole = 'id' | 'timestamp' | 'metric' | 'dimension' | 'unknown';

/**
 * Column role analysis result
 */
export interface ColumnRoleInfo {
	column: string;
	role: ColumnRole;
	confidence: number;
	reason: string;
}

/**
 * Column roles analysis
 */
export interface ColumnRolesAnalysis {
	roles: ColumnRoleInfo[];
	id_columns: string[];
	timestamp_columns: string[];
	metric_columns: string[];
	dimension_columns: string[];
}

/**
 * Missingness analysis for a column
 */
export interface ColumnMissingness {
	column: string;
	null_count: number;
	null_percent: number;
	unique_count: number;
	unique_percent: number;
	cardinality_category: 'low' | 'medium' | 'high' | 'unique';
}

/**
 * Missingness analysis
 */
export interface MissingnessAnalysis {
	columns: ColumnMissingness[];
	total_rows: number;
	columns_with_nulls: number;
	high_null_columns: string[];
}

/**
 * Descriptive stats for a column
 */
export interface ColumnDescriptiveStats {
	column: string;
	dtype: string;
	mean?: number | null;
	median?: number | null;
	std?: number | null;
	min?: number | string | null;
	max?: number | string | null;
	skew?: number | null;
	kurtosis?: number | null;
	top_values?: Array<{ value: string; count: number; percent: number }>;
}

/**
 * Descriptive stats analysis
 */
export interface DescriptiveStatsAnalysis {
	numeric_columns: ColumnDescriptiveStats[];
	categorical_columns: ColumnDescriptiveStats[];
	datetime_columns: ColumnDescriptiveStats[];
}

/**
 * Outlier detection result
 */
export interface OutlierInfo {
	column: string;
	method: 'iqr' | 'zscore';
	outlier_count: number;
	outlier_percent: number;
	lower_bound?: number | null;
	upper_bound?: number | null;
	extreme_values: Array<{ value: number; index: number }>;
}

/**
 * Outlier analysis
 */
export interface OutliersAnalysis {
	outliers: OutlierInfo[];
	columns_with_outliers: number;
	total_outlier_rows: number;
}

/**
 * Correlation pair
 */
export interface CorrelationPair {
	column_a: string;
	column_b: string;
	correlation: number;
	strength: 'weak' | 'moderate' | 'strong' | 'very_strong';
}

/**
 * Correlation analysis
 */
export interface CorrelationsAnalysis {
	top_positive: CorrelationPair[];
	top_negative: CorrelationPair[];
	potential_leakage: CorrelationPair[];
	matrix?: Record<string, Record<string, number>> | null;
}

/**
 * Time series readiness
 */
export interface TimeSeriesReadiness {
	is_ready: boolean;
	timestamp_column?: string | null;
	detected_frequency?: string | null;
	gap_count: number;
	gaps?: Array<{ start: string; end: string; missing_periods: number }>;
	date_range?: { start: string; end: string } | null;
	recommendations: string[];
}

/**
 * Segmentation opportunity
 */
export interface SegmentationOpportunity {
	dimension: string;
	metric: string;
	segment_count: number;
	variance_ratio: number;
	recommendation: string;
}

/**
 * Segmentation builder analysis
 */
export interface SegmentationBuilderAnalysis {
	opportunities: SegmentationOpportunity[];
	best_dimensions: string[];
	best_metrics: string[];
}

/**
 * Data quality issue
 */
export interface DataQualityIssue {
	column: string;
	issue_type: string;
	description: string;
	severity: 'low' | 'medium' | 'high';
	affected_rows?: number;
	examples?: string[];
	/** Suggested fix action for this issue */
	suggested_action?: DatasetFixAction;
	/** Configuration for the suggested fix action */
	action_config?: DatasetFixConfig;
	/** Human-readable label for the fix button */
	fix_label?: string;
}

/**
 * Data quality analysis
 */
export interface DataQualityAnalysis {
	issues: DataQualityIssue[];
	overall_score: number;
	completeness_score: number;
	consistency_score: number;
	validity_score: number;
}

/**
 * Full dataset investigation result (returned directly from API)
 */
export interface DatasetInvestigation {
	id: string;
	dataset_id: string;
	column_roles: ColumnRolesAnalysis;
	missingness: MissingnessAnalysis;
	descriptive_stats: DescriptiveStatsAnalysis;
	outliers: OutliersAnalysis;
	correlations: CorrelationsAnalysis;
	time_series_readiness: TimeSeriesReadiness;
	/** @deprecated Use segmentation_suggestions - keeping for backward compat */
	segmentation_builder?: SegmentationBuilderAnalysis;
	segmentation_suggestions: SegmentationBuilderAnalysis;
	data_quality: DataQualityAnalysis;
	computed_at: string;
}

/**
 * Investigation response from API (flat structure, no nesting)
 */
export type DatasetInvestigationResponse = DatasetInvestigation;

/**
 * Business context for dataset
 */
export interface DatasetBusinessContext {
	business_goal?: string | null;
	key_metrics?: string[] | null;
	kpis?: string[] | null;
	objectives?: string | null;
	industry?: string | null;
	additional_context?: string | null;
}

/**
 * Business context response from API
 * When id is null, context is inherited from user's global business context.
 */
export interface DatasetBusinessContextResponse extends DatasetBusinessContext {
	id: string | null;
	dataset_id: string;
	created_at?: string | null;
	updated_at?: string | null;
}

// =============================================================================
// Dataset Favourites Types
// =============================================================================

/**
 * Type of favourite (chart, insight, or message)
 */
export type FavouriteType = 'chart' | 'insight' | 'message';

/**
 * A favourited dataset item
 */
export interface DatasetFavourite {
	id: string;
	user_id: string;
	dataset_id: string;
	favourite_type: FavouriteType;
	analysis_id?: string | null;
	message_id?: string | null;
	insight_data?: Record<string, unknown> | null;
	title?: string | null;
	content?: string | null;
	chart_spec?: Record<string, unknown> | null;
	figure_json?: Record<string, unknown> | null;
	user_note?: string | null;
	sort_order: number;
	created_at: string;
}

/**
 * Response for a single favourite
 */
export interface DatasetFavouriteResponse extends DatasetFavourite {}

/**
 * Response for list of favourites
 */
export interface DatasetFavouriteListResponse {
	favourites: DatasetFavourite[];
	total: number;
}

// =============================================================================
// Dataset Reports Types
// =============================================================================

/**
 * A section in a generated report
 */
export interface ReportSection {
	section_type: string;
	title: string;
	content: string;
	chart_refs?: string[];
}

/**
 * A generated dataset report
 */
export interface DatasetReport {
	id: string;
	user_id: string;
	dataset_id: string | null; // Can be null if dataset was deleted
	title: string;
	executive_summary?: string | null;
	report_content: {
		title: string;
		executive_summary?: string;
		sections: ReportSection[];
	};
	favourite_ids: string[];
	model_used?: string | null;
	tokens_used?: number | null;
	created_at: string;
	updated_at: string;
}

/**
 * Response for a single report (includes expanded data from API)
 * API flattens report_content.sections to root-level sections
 */
export interface DatasetReportResponse extends Omit<DatasetReport, 'report_content'> {
	sections: ReportSection[]; // Flattened sections from report_content
	favourites?: DatasetFavourite[]; // Full favourite data for rendering charts
}

/**
 * Response for list of reports
 */
export interface DatasetReportListResponse {
	reports: DatasetReport[];
	total: number;
}

/**
 * Report item with dataset info for cross-dataset listing
 */
export interface AllReportItem {
	id: string;
	dataset_id: string | null; // Can be null if dataset was deleted
	dataset_name: string | null; // Can be null if dataset was deleted
	title: string;
	executive_summary?: string | null;
	created_at: string;
}

/**
 * Response for listing all reports across datasets
 */
export interface AllReportsListResponse {
	reports: AllReportItem[];
	total: number;
}

// =============================================================================
// Dataset Update Types
// =============================================================================

/**
 * Request to update dataset metadata (name/description)
 */
export interface DatasetUpdate {
	name?: string;
	description?: string;
}

// =============================================================================
// Dataset Comparison Types
// =============================================================================

/**
 * Schema comparison between two datasets
 */
export interface SchemaComparison {
	common_columns: string[];
	only_in_a: string[];
	only_in_b: string[];
	type_mismatches: Array<{
		column: string;
		type_a: string;
		type_b: string;
	}>;
}

/**
 * Column stat delta for statistics comparison
 */
export interface ColumnStatDelta {
	column: string;
	dtype: string;
	stat_deltas: Record<
		string,
		{
			value_a: number | string | null;
			value_b: number | string | null;
			delta?: number | null;
			percent_change?: number | null;
		}
	>;
}

/**
 * Statistics comparison between two datasets
 */
export interface StatisticsComparison {
	row_count_a: number;
	row_count_b: number;
	row_count_delta: number;
	row_count_percent_change: number | null;
	column_deltas: ColumnStatDelta[];
}

/**
 * Key metric comparison
 */
export interface KeyMetricComparisonItem {
	metric_name: string;
	value_a: number;
	value_b: number;
	delta: number;
	percent_change: number | null;
	is_significant: boolean;
}

/**
 * Key metrics comparison between two datasets
 */
export interface KeyMetricsComparison {
	metrics: KeyMetricComparisonItem[];
	significant_changes: number;
}

/**
 * Full dataset comparison result
 */
export interface DatasetComparison {
	id: string;
	dataset_a_id: string;
	dataset_b_id: string;
	dataset_a_name?: string | null;
	dataset_b_name?: string | null;
	name?: string | null;
	schema_comparison: SchemaComparison;
	statistics_comparison: StatisticsComparison;
	key_metrics_comparison: KeyMetricsComparison;
	insights: string[];
	created_at: string;
}

/**
 * Response for a single comparison
 */
export interface DatasetComparisonResponse extends DatasetComparison {}

/**
 * Response for list of comparisons
 */
export interface DatasetComparisonListResponse {
	comparisons: DatasetComparison[];
	total_count: number;
}

// =============================================================================
// Multi-Dataset Analysis Types
// =============================================================================

/**
 * Request to create a multi-dataset analysis
 */
export interface MultiDatasetAnalysisCreate {
	dataset_ids: string[];
	name?: string | null;
}

/**
 * A detected anomaly across datasets
 */
export interface MultiDatasetAnomaly {
	anomaly_type: 'schema_drift' | 'metric_outlier' | 'type_mismatch' | 'no_common_columns';
	severity: 'high' | 'medium' | 'low';
	description: string;
	affected_datasets: string[];
	column?: string | null;
	details: Record<string, unknown>;
}

/**
 * Summary statistics for a single dataset in multi-analysis
 */
export interface MultiDatasetSummary {
	name: string;
	row_count: number;
	column_count: number;
	columns: string[];
	numeric_columns: string[];
	categorical_columns: string[];
}

/**
 * Schema information common across all datasets
 */
export interface MultiDatasetCommonSchema {
	common_columns: string[];
	partial_columns: Record<string, string[]>;
	type_consensus: Record<string, string>;
	type_conflicts: Record<string, Record<string, string>>;
}

/**
 * Response for a multi-dataset analysis
 */
export interface MultiDatasetAnalysisResponse {
	id: string;
	dataset_ids: string[];
	dataset_names: string[];
	name?: string | null;
	common_schema: MultiDatasetCommonSchema;
	anomalies: MultiDatasetAnomaly[];
	dataset_summaries: MultiDatasetSummary[];
	pairwise_comparisons: Record<string, unknown>[];
	created_at: string;
}

/**
 * Response for list of multi-dataset analyses
 */
export interface MultiDatasetAnalysisListResponse {
	analyses: MultiDatasetAnalysisResponse[];
	total_count: number;
}

// =============================================================================
// Objective Analysis Types (Data Analysis Reimagination)
// =============================================================================

/**
 * Analysis mode for objective analysis
 */
export type ObjectiveAnalysisMode = 'objective_focused' | 'open_exploration';

/**
 * Relevance level for objective matching
 */
export type ObjectiveRelevanceLevel = 'high' | 'medium' | 'low' | 'none';

/**
 * Confidence level for insights
 */
export type ObjectiveConfidenceLevel = 'high' | 'medium' | 'low';

/**
 * Match assessment between dataset and a specific objective
 */
export interface ObjectiveMatch {
	objective_id?: string | null;
	objective_name: string;
	relevance: ObjectiveRelevanceLevel;
	explanation: string;
	answerable_questions: string[];
	unanswerable_questions: string[];
}

/**
 * Data that would strengthen the analysis if available
 */
export interface MissingData {
	data_needed: string;
	why_valuable: string;
	objectives_unlocked: string[];
}

/**
 * Full relevance assessment for a dataset against user objectives
 */
export interface ObjectiveRelevanceAssessment {
	relevance_score: number;
	assessment_summary: string;
	objective_matches: ObjectiveMatch[];
	missing_data: MissingData[];
	recommended_focus: string;
}

/**
 * Visualization configuration for an insight
 */
export interface InsightVisualization {
	type: 'bar' | 'line' | 'scatter' | 'pie';
	x_axis?: string | null;
	y_axis?: string | null;
	group_by?: string | null;
	title: string;
	figure_json?: Record<string, unknown> | null;
}

/**
 * Benchmark comparison for an insight
 */
export interface InsightBenchmarkComparison {
	metric_name: string;
	your_value: number;
	industry_median: number | null;
	industry_top_quartile: number | null;
	performance: 'top_performer' | 'above_average' | 'average' | 'below_average';
	gap_to_median: number | null;
	gap_to_top: number | null;
	unit: string;
}

/**
 * Impact model for an insight
 */
export interface InsightImpactModel {
	scenario: string;
	monthly_impact: number;
	annual_impact: number;
	narrative: string;
	assumptions?: string[];
}

/**
 * Single insight generated from objective analysis
 */
export interface ObjectiveInsight {
	id: string;
	objective_id?: string | null;
	objective_name?: string | null;
	headline: string;
	narrative: string;
	supporting_data?: Record<string, unknown>;
	visualization?: InsightVisualization | null;
	recommendation: string;
	follow_up_questions: string[];
	confidence: ObjectiveConfidenceLevel;
	benchmark_comparison?: InsightBenchmarkComparison | null;
	impact_model?: InsightImpactModel | null;
	industry_context?: string | null;
}

/**
 * Section of data story focused on a specific objective
 */
export interface ObjectiveSection {
	objective_id?: string | null;
	objective_name: string;
	summary: string;
	insight_ids: string[];
	key_metric: string;
	recommended_action: string;
}

/**
 * Something interesting not directly related to objectives
 */
export interface UnexpectedFinding {
	headline: string;
	narrative: string;
	should_investigate: boolean;
}

/**
 * AI-generated narrative from analysis results
 */
export interface ObjectiveDataStory {
	opening_hook: string;
	objective_sections: ObjectiveSection[];
	data_quality_summary: string;
	unexpected_finding?: UnexpectedFinding | null;
	next_steps: string[];
	suggested_questions: string[];
}

/**
 * Full objective analysis response
 */
export interface ObjectiveAnalysisResponse {
	id: string;
	dataset_id: string;
	analysis_mode: ObjectiveAnalysisMode;
	relevance_score?: number | null;
	relevance_assessment?: ObjectiveRelevanceAssessment | null;
	data_story?: ObjectiveDataStory | null;
	insights: ObjectiveInsight[];
	created_at: string;
}

/**
 * Request to trigger analysis
 */
export interface AnalyzeDatasetRequest {
	include_context?: boolean;
	objective_id?: string | null;
	force_mode?: ObjectiveAnalysisMode | null;
}

/**
 * Response from triggering analysis
 */
export interface AnalyzeDatasetResponse {
	analysis_id: string;
	analysis_mode: ObjectiveAnalysisMode;
	relevance_score?: number | null;
	status: string;
}

// =============================================================================
// Data Requirements Types (for "What Data Do I Need?" feature)
// =============================================================================

/**
 * Essential data required for meaningful analysis
 */
export interface EssentialData {
	name: string;
	description: string;
	example_columns: string[];
	why_essential: string;
	questions_answered: string[];
}

/**
 * Valuable addition that would strengthen analysis
 */
export interface ValuableAddition {
	name: string;
	description: string;
	insight_unlocked: string;
	priority: 'high' | 'medium' | 'low';
}

/**
 * Suggested source for obtaining data
 */
export interface DataSource {
	source_type: string;
	example_tools: string[];
	typical_export_name: string;
	columns_typically_included: string[];
}

/**
 * Full data requirements for an objective
 */
export interface DataRequirements {
	objective_summary: string;
	essential_data: EssentialData[];
	valuable_additions: ValuableAddition[];
	data_sources: DataSource[];
	analysis_preview: string;
}

/**
 * Summary of an objective with index identifier
 */
export interface ObjectiveSummary {
	index: number;
	name: string;
	has_progress: boolean;
	current_value?: string | null;
	target_value?: string | null;
}

/**
 * Response for data requirements for a specific objective
 */
export interface ObjectiveDataRequirementsResponse {
	objective: ObjectiveSummary;
	requirements: DataRequirements;
	generated_at: string;
	model_used: string;
}

/**
 * Summary of data requirements for one objective
 */
export interface ObjectiveRequirementsSummary {
	index: number;
	name: string;
	requirements_summary: string;
	essential_data_count: number;
}

/**
 * Response for all objectives data requirements overview
 */
export interface AllObjectivesRequirementsResponse {
	objectives: ObjectiveRequirementsSummary[];
	count: number;
	north_star_goal?: string | null;
}

// =============================================================================
// Dataset Fix/Cleaning Types (Data Quality Actions)
// =============================================================================

/**
 * Available data cleaning actions
 */
export type DatasetFixAction =
	| 'remove_duplicates'
	| 'fill_nulls'
	| 'remove_nulls'
	| 'trim_whitespace';

/**
 * Configuration for data fixing actions
 */
export interface DatasetFixConfig {
	/** For remove_duplicates: which duplicate to keep */
	keep?: 'first' | 'last';
	/** For remove_duplicates: subset of columns to consider */
	subset?: string[];
	/** For fill_nulls: column to fill */
	column?: string;
	/** For fill_nulls: strategy to use */
	strategy?: 'mean' | 'median' | 'mode' | 'zero' | 'value' | 'forward' | 'backward';
	/** For fill_nulls with strategy='value': the value to fill */
	fill_value?: string | number;
	/** For remove_nulls: columns to check for nulls */
	columns?: string[];
	/** For remove_nulls: how to determine null rows */
	how?: 'any' | 'all';
}

/**
 * Response from applying a data fix
 */
export interface DatasetFixResponse {
	success: boolean;
	rows_affected: number;
	new_row_count: number;
	reanalysis_required: boolean;
	message: string;
	stats: Record<string, unknown>;
}

// ---- GSC Integration Types ----
export type GSCStatusResponse = components['schemas']['GSCStatusResponse'];
export type GSCSitesResponse = components['schemas']['GSCSitesResponse'];
export type GSCSiteResponse = components['schemas']['GSCSiteResponse'];
