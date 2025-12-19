/**
 * API Types - TypeScript interfaces for Board of One API
 *
 * This file re-exports generated types from the OpenAPI spec where available,
 * and defines frontend-only types (HoneypotFields, SSE events, etc.) manually.
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

/** Session detail response (full) - from OpenAPI */
export type GeneratedSessionResponse = components['schemas']['SessionResponse'];
export type GeneratedSessionDetailResponse = components['schemas']['FullSessionResponse'];
export type GeneratedActionDetailResponse = components['schemas']['ActionDetailResponse'];
export type GeneratedAllActionsResponse = components['schemas']['AllActionsResponse'];
export type GeneratedProjectDetailResponse = components['schemas']['ProjectDetailResponse'];
export type GeneratedBusinessContext = components['schemas']['BusinessContext'];
export type GeneratedHealthResponse = components['schemas']['HealthResponse'];

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

export interface CreateSessionRequest extends HoneypotFields {
	problem_statement: string;
	problem_context?: Record<string, unknown>;
	dataset_id?: string;
	context_ids?: SessionContextIds;
}

export interface StaleInsight {
	question: string;
	days_stale: number;
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

export interface SessionResponse {
	id: string;
	status: 'active' | 'paused' | 'completed' | 'failed' | 'killed' | 'deleted' | 'created';
	phase: string | null;
	created_at: string;
	updated_at: string;
	last_activity_at?: string;
	problem_statement: string;
	cost?: number | null;
	// Summary counts for dashboard cards
	expert_count?: number | null;
	contribution_count?: number | null;
	task_count?: number | null;
	focus_area_count?: number | null;
	// Stale insights warning (only on creation)
	stale_insights?: StaleInsight[] | null;
}

export interface SessionDetailResponse extends SessionResponse {
	problem?: {
		statement: string;
		context?: Record<string, unknown>;
		sub_problems?: Array<{
			id: string;
			goal: string;
		}>;
	};
	state?: {
		synthesis?: string;
		final_synthesis?: string;
		recommendations?: Array<{
			persona_code: string;
			recommendation: string;
			reasoning: string;
			confidence: number;
			conditions?: string[];
		}>;
		round_number?: number;
		max_rounds?: number;
		duration_seconds?: number;
		// Deliberation phase tracking
		phase?: string;
		current_phase?: string;
		// Personas and contributions
		personas?: Array<{ code: string; name: string; perspective: string }>;
		contributions?: Array<{ persona_code: string; content: string; round_number: number }>;
		// Sub-problem results
		sub_problem_results?: Array<{ id: string; synthesis: string }>;
		// Comparison detection
		comparison_detected?: boolean;
		comparison_options?: string[];
		comparison_type?: string;
		// Termination state
		should_stop?: boolean;
		stop_reason?: string | null;
		termination_requested?: boolean;
		termination_type?: string | null;
		termination_reason?: string | null;
	};
	metrics?: {
		total_cost: number;
		total_tokens: number;
		phase_costs: Record<string, number>;
		convergence_score?: number;
		duration_seconds?: number;
	};
	contributions?: Array<{
		persona_code: string;
		content: string;
		round_number: number;
		timestamp: string;
	}>;
	round_number?: number;
	max_rounds?: number;
}

export interface SessionListResponse {
	sessions: SessionResponse[];
	total: number;
	limit: number;
	offset: number;
}

export interface ControlResponse {
	status: string;
	message?: string;
}

export interface HealthResponse {
	status: 'healthy' | 'unhealthy';
	details?: Record<string, unknown>;
}

export interface ApiError {
	detail: string;
	status?: number;
}

// ============================================================================
// Business Context Types (Extended for Tier 3)
// ============================================================================

export type BusinessStage = 'idea' | 'early' | 'growing' | 'scaling';

export type PrimaryObjective =
	| 'acquire_customers'
	| 'improve_retention'
	| 'raise_capital'
	| 'launch_product'
	| 'reduce_costs';

export type EnrichmentSource = 'manual' | 'api' | 'scrape';

export interface UserContext {
	// Original fields
	business_model?: string;
	target_market?: string;
	product_description?: string;
	revenue?: string;
	customers?: string;
	growth_rate?: string;
	competitors?: string;
	website?: string;

	// Extended fields (Tier 3)
	company_name?: string;
	business_stage?: BusinessStage;
	primary_objective?: PrimaryObjective;
	industry?: string;
	product_categories?: string[];
	pricing_model?: string;
	brand_positioning?: string;
	brand_tone?: string;
	brand_maturity?: string;
	tech_stack?: string[];
	seo_structure?: Record<string, unknown>;
	detected_competitors?: string[];
	ideal_customer_profile?: string;
	keywords?: string[];
	target_geography?: string;
	traffic_range?: string;
	mau_bucket?: string;
	revenue_stage?: string;
	main_value_proposition?: string;
	team_size?: string;
	budget_constraints?: string;
	time_constraints?: string;
	regulatory_constraints?: string;
	enrichment_source?: EnrichmentSource;
	enrichment_date?: string;
	onboarding_completed?: boolean;

	// Goals
	north_star_goal?: string;
	strategic_objectives?: string[];
}

export interface UserContextResponse {
	exists: boolean;
	context?: UserContext;
	updated_at?: string;
}

// ============================================================================
// Insights Types (Clarifications from Meetings)
// ============================================================================

/**
 * Business insight category (from Haiku parsing)
 */
export type InsightCategory =
	| 'revenue'
	| 'growth'
	| 'customers'
	| 'team'
	| 'product'
	| 'operations'
	| 'market'
	| 'competition'
	| 'funding'
	| 'costs'
	| 'uncategorized';

/**
 * Extracted metric from insight (from Haiku parsing)
 */
export interface InsightMetric {
	value?: number | null;
	unit?: string | null; // USD, %, count, etc.
	metric_type?: string | null; // MRR, ARR, headcount, etc.
	period?: string | null; // monthly, yearly, etc.
	raw_text?: string | null;
}

/**
 * A clarification answer from a meeting
 */
export interface ClarificationInsight {
	question: string;
	answer: string;
	answered_at?: string;
	session_id?: string;
	// Structured fields (from Haiku parsing)
	category?: InsightCategory;
	metric?: InsightMetric;
	confidence_score?: number;
	summary?: string;
	key_entities?: string[];
	parsed_at?: string;
}

/**
 * Response containing user's accumulated insights
 */
export interface InsightsResponse {
	clarifications: ClarificationInsight[];
	total_count: number;
}

// ============================================================================
// Context Auto-Update Types (Phase 6)
// ============================================================================

/**
 * Source of a context update
 */
export type ContextUpdateSource = 'clarification' | 'problem_statement' | 'action';

/**
 * A pending context update suggestion requiring user approval
 */
export interface ContextUpdateSuggestion {
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

/**
 * Response for pending updates endpoint
 */
export interface PendingUpdatesResponse {
	suggestions: ContextUpdateSuggestion[];
	count: number;
}

/**
 * Response after approving a pending update
 */
export interface ApproveUpdateResponse {
	success: boolean;
	field_name: string;
	new_value: string | number | string[];
}

/**
 * Trend direction for a metric
 */
export type TrendDirection = 'improving' | 'worsening' | 'stable' | 'insufficient_data';

/**
 * Trend information for a context metric
 */
export interface MetricTrend {
	field_name: string;
	direction: TrendDirection;
	current_value?: string | number | null;
	previous_value?: string | number | null;
	change_percent?: number | null;
	period_description?: string | null;
}

/**
 * Business context with trend indicators
 */
export interface ContextWithTrends {
	context: UserContext;
	trends: MetricTrend[];
	updated_at?: string | null;
}

// ============================================================================
// Admin Types
// ============================================================================

/**
 * Admin user information with metrics
 */
export interface AdminUser {
	user_id: string;
	email: string;
	auth_provider: string;
	subscription_tier: string;
	is_admin: boolean;
	is_locked: boolean;
	locked_at: string | null;
	lock_reason: string | null;
	deleted_at: string | null;
	total_meetings: number;
	total_cost: number | null;
	last_meeting_at: string | null;
	last_meeting_id: string | null;
	created_at: string;
	updated_at: string;
}

/**
 * Admin user list response
 */
export interface AdminUserListResponse {
	total_count: number;
	users: AdminUser[];
	page: number;
	per_page: number;
}

/**
 * Admin user update request
 */
export interface AdminUserUpdateRequest {
	subscription_tier?: string;
	is_admin?: boolean;
}

/**
 * Beta whitelist entry
 */
export interface WhitelistEntry {
	id: string;
	email: string;
	added_by: string | null;
	notes: string | null;
	created_at: string;
}

/**
 * Beta whitelist response
 */
export interface WhitelistResponse {
	total_count: number;
	emails: WhitelistEntry[];
	env_emails: string[];
}

/**
 * Waitlist entry
 */
export interface WaitlistEntry {
	id: string;
	email: string;
	status: string;
	source: string | null;
	notes: string | null;
	created_at: string;
}

/**
 * Waitlist response
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
 * Extracted task from synthesis
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
 * Action status enum (9 states)
 * - todo, in_progress, blocked, in_review, done: standard workflow
 * - cancelled: general cancellation
 * - failed: closed because task could not be completed
 * - abandoned: closed because task is no longer relevant
 * - replanned: closed because task was cloned to a new action with different approach
 */
export type ActionStatus = 'todo' | 'in_progress' | 'blocked' | 'in_review' | 'done' | 'cancelled' | 'failed' | 'abandoned' | 'replanned';

/**
 * Task with Kanban status
 */
export interface TaskWithStatus extends ExtractedTask {
	status: ActionStatus;
}

/**
 * Session actions response (tasks with statuses)
 */
export interface SessionActionsResponse {
	session_id: string;
	tasks: TaskWithStatus[];
	total_tasks: number;
	by_status: Record<ActionStatus, number>;
}

/**
 * Task status update request (uses ActionStatus)
 */
export interface TaskStatusUpdateRequest {
	status: ActionStatus;
}

/**
 * Task extraction response
 */
export interface TaskExtractionResponse {
	tasks: ExtractedTask[];
	total_tasks: number;
	extraction_confidence: number;
	synthesis_sections_analyzed: string[];
}

/**
 * Session events response
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

/**
 * Task with session context for global actions view
 */
export interface TaskWithSessionContext extends TaskWithStatus {
	session_id: string;
	/** Status of source session (completed/failed). 'failed' indicates action from acknowledged failure. */
	source_session_status: string | null;
	problem_statement: string;
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
	by_status: Record<ActionStatus, number>;
}

/**
 * All actions response (global across sessions)
 */
export interface AllActionsResponse {
	sessions: SessionWithTasks[];
	total_tasks: number;
	by_status: Record<ActionStatus, number>;
}

/**
 * Action detail response (single action with full context)
 */
export interface ActionDetailResponse {
	id: string;
	title: string;
	description: string;
	what_and_how: string[];
	success_criteria: string[];
	kill_criteria: string[];
	dependencies: string[];
	timeline: string;
	priority: 'high' | 'medium' | 'low';
	category: 'implementation' | 'research' | 'decision' | 'communication';
	source_section: string | null;
	confidence: number;
	sub_problem_index: number | null;
	status: ActionStatus;
	session_id: string;
	/** Status of source session (completed/failed). 'failed' indicates action from acknowledged failure. */
	source_session_status: string | null;
	problem_statement: string;
	estimated_duration_days: number | null;
	target_start_date: string | null;
	target_end_date: string | null;
	estimated_start_date: string | null;
	estimated_end_date: string | null;
	actual_start_date: string | null;
	actual_end_date: string | null;
	blocking_reason: string | null;
	blocked_at: string | null;
	auto_unblock: boolean;
	// Replanning fields
	replan_session_id: string | null;
	replan_requested_at: string | null;
	replanning_reason: string | null;
	can_replan: boolean;
	// Cancellation fields
	cancellation_reason: string | null;
	cancelled_at: string | null;
	// Closure fields (failed/abandoned)
	closure_reason: string | null;
	// Replan lineage
	replanned_from_id: string | null;
	replanned_to_id: string | null;
	// Project assignment
	project_id: string | null;
}

/**
 * Replan request - request AI replanning for blocked action
 */
export interface ReplanRequest {
	additional_context?: string | null;
}

/**
 * Replan response - result of replan request
 */
export interface ReplanResponse {
	session_id: string;
	action_id: string;
	message: string;
	redirect_url: string;
	is_existing: boolean;
}

/**
 * Action create request
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
 * Action update request
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
 * Action status update request
 */
export interface ActionStatusUpdateRequest {
	status: ActionStatus;
	blocking_reason?: string | null;
	auto_unblock?: boolean;
}

/**
 * Action close request - for marking as failed/abandoned
 */
export interface ActionCloseRequest {
	status: 'failed' | 'abandoned';
	reason: string;
}

/**
 * Action replan request - clone action with modifications
 */
export interface ActionReplanRequest {
	new_steps?: string[] | null;
	new_target_date?: string | null;
}

/**
 * Action replan response - new action created from replan
 */
export interface ActionReplanResponse {
	new_action_id: string;
	original_action_id: string;
	message: string;
}

/**
 * Action response (summary view)
 */
export interface ActionResponse {
	id: string;
	title: string;
	status: ActionStatus;
	priority: 'high' | 'medium' | 'low';
	category: 'implementation' | 'research' | 'decision' | 'communication';
	timeline: string | null;
	estimated_duration_days: number | null;
	target_start_date: string | null;
	estimated_start_date: string | null;
	created_at: string;
	updated_at: string;
}

// ============================================================================
// Dependency Types
// ============================================================================

export type DependencyType = 'finish_to_start' | 'start_to_start' | 'finish_to_finish';

/**
 * Request to create a dependency
 */
export interface DependencyCreateRequest {
	depends_on_action_id: string;
	dependency_type?: DependencyType;
	lag_days?: number;
}

/**
 * Dependency response
 */
export interface DependencyResponse {
	action_id: string;
	depends_on_action_id: string;
	depends_on_title: string;
	depends_on_status: ActionStatus;
	dependency_type: DependencyType;
	lag_days: number;
	created_at: string;
}

/**
 * List of dependencies response
 */
export interface DependencyListResponse {
	action_id: string;
	dependencies: DependencyResponse[];
	has_incomplete: boolean;
}

/**
 * Request to block an action
 */
export interface BlockActionRequest {
	blocking_reason: string;
	auto_unblock?: boolean;
}

/**
 * Request to unblock an action
 */
export interface UnblockActionRequest {
	target_status?: 'todo' | 'in_progress';
}

/**
 * Response when adding/removing dependencies
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
 * Response when blocking/unblocking actions
 */
export interface BlockUnblockResponse {
	message: string;
	action_id: string;
	blocking_reason?: string;
	auto_unblock?: boolean;
	new_status?: ActionStatus;
	warning?: string;
	incomplete_dependencies?: Array<{
		id: string;
		title: string;
	}>;
}

// ============================================================================
// Project Types
// ============================================================================

export type ProjectStatus = 'active' | 'paused' | 'completed' | 'archived';

/**
 * Request to create a project
 */
export interface ProjectCreateRequest {
	name: string;
	description?: string | null;
	target_start_date?: string | null;
	target_end_date?: string | null;
	color?: string | null;
	icon?: string | null;
}

/**
 * Request to update a project
 */
export interface ProjectUpdateRequest {
	name?: string;
	description?: string | null;
	target_start_date?: string | null;
	target_end_date?: string | null;
	color?: string | null;
	icon?: string | null;
}

/**
 * Request to update project status
 */
export interface ProjectStatusUpdateRequest {
	status: ProjectStatus;
}

/**
 * Project detail response
 */
export interface ProjectDetailResponse {
	id: string;
	user_id: string;
	name: string;
	description: string | null;
	status: ProjectStatus;
	target_start_date: string | null;
	target_end_date: string | null;
	estimated_start_date: string | null;
	estimated_end_date: string | null;
	actual_start_date: string | null;
	actual_end_date: string | null;
	progress_percent: number;
	total_actions: number;
	completed_actions: number;
	color: string | null;
	icon: string | null;
	created_at: string | null;
	updated_at: string | null;
}

/**
 * Project list response
 */
export interface ProjectListResponse {
	projects: ProjectDetailResponse[];
	total: number;
	page: number;
	per_page: number;
}

/**
 * Action summary within a project
 */
export interface ProjectActionSummary {
	id: string;
	session_id: string;
	title: string;
	description: string;
	status: ActionStatus;
	priority: 'high' | 'medium' | 'low';
	category: string;
	timeline: string | null;
	estimated_duration_days: number | null;
	estimated_start_date: string | null;
	estimated_end_date: string | null;
	blocking_reason: string | null;
}

/**
 * Project actions response
 */
export interface ProjectActionsResponse {
	actions: ProjectActionSummary[];
	total: number;
	page: number;
	per_page: number;
}

/**
 * Request to link a session to a project
 */
export interface ProjectSessionLinkRequest {
	session_id: string;
	relationship?: 'discusses' | 'created_from' | 'replanning';
}

/**
 * Project session link
 */
export interface ProjectSessionLink {
	session_id: string;
	relationship: string;
	problem_statement: string;
	session_status: string;
	created_at: string | null;
}

/**
 * Project sessions response
 */
export interface ProjectSessionsResponse {
	sessions: ProjectSessionLink[];
}

// =========================================================================
// Project Autogeneration Types
// =========================================================================

/**
 * A suggested project from action clustering
 */
export interface AutogenSuggestion {
	id: string;
	name: string;
	description: string;
	action_ids: string[];
	confidence: number;
	rationale: string;
}

/**
 * Response from autogenerate suggestions endpoint
 */
export interface AutogenSuggestionsResponse {
	suggestions: AutogenSuggestion[];
	unassigned_count: number;
	min_required: number;
}

/**
 * Request to create projects from suggestions
 */
export interface AutogenCreateRequest {
	suggestions: AutogenSuggestion[];
	workspace_id?: string;
}

/**
 * Response from creating projects from suggestions
 */
export interface AutogenCreateResponse {
	created_projects: ProjectDetailResponse[];
	count: number;
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
 * Context-based project suggestion
 */
export interface ContextProjectSuggestion {
	id: string;
	name: string;
	description: string;
	rationale: string;
	category: string;
	priority: string;
}

/**
 * Response from context suggestions endpoint
 */
export interface ContextSuggestionsResponse {
	suggestions: ContextProjectSuggestion[];
	context_completeness: number;
	has_minimum_context: boolean;
	missing_fields: string[];
}

/**
 * Request to create projects from context suggestions
 */
export interface ContextCreateRequest {
	suggestions: ContextProjectSuggestion[];
	workspace_id?: string;
}

/**
 * Gantt action data
 */
export interface GanttActionData {
	id: string;
	title: string;
	status: ActionStatus;
	priority: string;
	estimated_start_date: string | null;
	estimated_end_date: string | null;
	actual_start_date: string | null;
	actual_end_date: string | null;
	blocking_reason: string | null;
}

/**
 * Gantt dependency data
 */
export interface GanttDependency {
	from: string;
	to: string;
	type: DependencyType;
	lag_days: number;
}

/**
 * Gantt project summary
 */
export interface GanttProjectData {
	id: string;
	name: string;
	status: ProjectStatus;
	estimated_start_date: string | null;
	estimated_end_date: string | null;
	progress_percent: number;
	color: string | null;
}

/**
 * Gantt chart response
 */
export interface GanttResponse {
	project: GanttProjectData;
	actions: GanttActionData[];
	dependencies: GanttDependency[];
}

// ============================================================================
// Action Dates Types (Gantt drag-to-reschedule)
// ============================================================================

/**
 * Request to update action dates
 */
export interface ActionDatesUpdateRequest {
	target_start_date?: string | null;
	target_end_date?: string | null;
	timeline?: string | null;
}

/**
 * Response from action dates update
 */
export interface ActionDatesResponse {
	action_id: string;
	target_start_date: string | null;
	target_end_date: string | null;
	estimated_start_date: string | null;
	estimated_end_date: string | null;
	estimated_duration_days: number | null;
	cascade_updated: number;
}

// ============================================================================
// Action Update Types (Phase 5)
// ============================================================================

/**
 * Types of action updates
 */
export type ActionUpdateType =
	| 'progress'
	| 'blocker'
	| 'note'
	| 'status_change'
	| 'date_change'
	| 'completion';

/**
 * Request to create an action update
 */
export interface ActionUpdateCreateRequest {
	update_type: 'progress' | 'blocker' | 'note';
	content: string;
	progress_percent?: number | null;
}

/**
 * Single action update response
 */
export interface ActionUpdateResponse {
	id: number;
	action_id: string;
	user_id: string;
	update_type: ActionUpdateType;
	content: string | null;
	old_status: ActionStatus | null;
	new_status: ActionStatus | null;
	old_date: string | null;
	new_date: string | null;
	date_field: string | null;
	progress_percent: number | null;
	created_at: string;
}

/**
 * List of action updates response
 */
export interface ActionUpdatesResponse {
	action_id: string;
	updates: ActionUpdateResponse[];
	total: number;
}

// ============================================================================
// Tag Types
// ============================================================================

/**
 * Request to create a tag
 */
export interface TagCreateRequest {
	name: string;
	color?: string;
}

/**
 * Request to update a tag
 */
export interface TagUpdateRequest {
	name?: string;
	color?: string;
}

/**
 * Tag response
 */
export interface TagResponse {
	id: string;
	user_id: string;
	name: string;
	color: string;
	action_count: number;
	created_at: string;
	updated_at: string;
}

/**
 * Tag list response
 */
export interface TagListResponse {
	tags: TagResponse[];
	total: number;
}

/**
 * Request to set tags on an action
 */
export interface ActionTagsUpdateRequest {
	tag_ids: string[];
}

// ============================================================================
// Global Gantt Types
// ============================================================================

/**
 * Gantt action data (for global gantt view)
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
 * Gantt dependency (for global gantt view)
 */
export interface GlobalGanttDependency {
	action_id: string;
	depends_on_id: string;
	dependency_type: DependencyType;
	lag_days: number;
}

/**
 * Global gantt chart response
 */
export interface GlobalGanttResponse {
	actions: GlobalGanttActionData[];
	dependencies: GlobalGanttDependency[];
}

// ============================================================================
// Action Stats Types (Dashboard Progress Visualization)
// ============================================================================

/**
 * Daily action statistics
 */
export interface DailyActionStat {
	date: string;
	completed_count: number;
	in_progress_count: number;
	sessions_run: number;
	mentor_sessions: number;
	estimated_starts: number;
	estimated_completions: number;
}

/**
 * Total action counts by status
 */
export interface ActionStatsTotals {
	completed: number;
	in_progress: number;
	todo: number;
}

/**
 * Action stats response
 */
export interface ActionStatsResponse {
	daily: DailyActionStat[];
	totals: ActionStatsTotals;
}

// ============================================================================
// Action Reminder Types
// ============================================================================

/**
 * Single pending action reminder
 */
export interface ActionReminderResponse {
	action_id: string;
	action_title: string;
	reminder_type: 'start_overdue' | 'deadline_approaching';
	due_date: string | null;
	days_overdue: number | null;
	days_until_deadline: number | null;
	session_id: string;
	problem_statement: string;
}

/**
 * List of pending reminders response
 */
export interface ActionRemindersResponse {
	reminders: ActionReminderResponse[];
	total: number;
}

/**
 * Reminder settings for an action
 */
export interface ReminderSettingsResponse {
	action_id: string;
	reminders_enabled: boolean;
	reminder_frequency_days: number;
	snoozed_until: string | null;
	last_reminder_sent_at: string | null;
}

/**
 * Request to update reminder settings
 */
export interface ReminderSettingsUpdateRequest {
	reminders_enabled?: boolean;
	reminder_frequency_days?: number;
}

/**
 * Request to snooze a reminder
 */
export interface SnoozeReminderRequest {
	snooze_days: number;
}

// ============================================================================
// Cost Calculator Types (Meeting Cost Calculator Widget)
// ============================================================================

/**
 * User defaults for the meeting cost calculator widget
 */
export interface CostCalculatorDefaults {
	avg_hourly_rate: number;
	typical_participants: number;
	typical_duration_mins: number;
	typical_prep_mins: number;
}

// ============================================================================
// Query Types (Data Analysis Platform - EPIC 3)
// ============================================================================

/**
 * Filter operators for query operations
 */
export type FilterOperator = 'eq' | 'ne' | 'gt' | 'lt' | 'gte' | 'lte' | 'contains' | 'in';

/**
 * Aggregate functions for query operations
 */
export type AggregateFunction = 'sum' | 'avg' | 'min' | 'max' | 'count' | 'distinct';

/**
 * Time intervals for trend analysis
 */
export type TrendInterval = 'day' | 'week' | 'month' | 'quarter' | 'year';

/**
 * Correlation methods
 */
export type CorrelationMethod = 'pearson' | 'spearman';

/**
 * Query types
 */
export type QueryType = 'filter' | 'aggregate' | 'trend' | 'compare' | 'correlate';

/**
 * Filter specification
 */
export interface FilterSpec {
	field: string;
	operator: FilterOperator;
	value: unknown;
}

/**
 * Aggregate specification
 */
export interface AggregateSpec {
	field: string;
	function: AggregateFunction;
	alias?: string | null;
}

/**
 * GroupBy specification
 */
export interface GroupBySpec {
	fields: string[];
	aggregates: AggregateSpec[];
}

/**
 * Trend specification
 */
export interface TrendSpec {
	date_field: string;
	value_field: string;
	interval?: TrendInterval;
	aggregate_function?: 'sum' | 'avg' | 'min' | 'max' | 'count';
}

/**
 * Comparison specification
 */
export interface CompareSpec {
	group_field: string;
	value_field: string;
	comparison_type?: 'absolute' | 'percentage';
	aggregate_function?: 'sum' | 'avg' | 'min' | 'max' | 'count';
}

/**
 * Correlation specification
 */
export interface CorrelateSpec {
	field_a: string;
	field_b: string;
	method?: CorrelationMethod;
}

/**
 * Full query specification
 */
export interface QuerySpec {
	query_type: QueryType;
	filters?: FilterSpec[] | null;
	group_by?: GroupBySpec | null;
	trend?: TrendSpec | null;
	compare?: CompareSpec | null;
	correlate?: CorrelateSpec | null;
	limit?: number;
	offset?: number;
}

/**
 * Query result response
 */
export interface QueryResultResponse {
	rows: Record<string, unknown>[];
	columns: string[];
	total_count: number;
	has_more: boolean;
	query_type: QueryType;
}

// ============================================================================
// Dataset Types (Data Analysis Platform - EPIC 6)
// ============================================================================

/**
 * Dataset source type
 */
export type DatasetSourceType = 'csv' | 'sheets' | 'api';

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

/**
 * Dataset response (summary)
 */
export interface Dataset {
	id: string;
	user_id: string;
	name: string;
	description: string | null;
	source_type: DatasetSourceType;
	source_uri: string | null;
	file_key: string | null;
	row_count: number | null;
	column_count: number | null;
	file_size_bytes: number | null;
	created_at: string;
	updated_at: string;
}

/**
 * Dataset detail response (with profile)
 */
export interface DatasetDetailResponse extends Dataset {
	profiles: DatasetProfile[];
	summary: string | null;
}

/**
 * Dataset list response
 */
export interface DatasetListResponse {
	datasets: Dataset[];
	total: number;
	limit: number;
	offset: number;
}

/**
 * Dataset upload response
 */
export interface DatasetUploadResponse extends Dataset {}

/**
 * Chart types
 */
export type ChartType = 'line' | 'bar' | 'pie' | 'scatter';

/**
 * Chart specification
 */
export interface ChartSpec {
	chart_type: ChartType;
	x_field: string;
	y_field: string;
	group_field?: string | null;
	title?: string | null;
	filters?: FilterSpec[] | null;
	width?: number;
	height?: number;
}

/**
 * Chart result response
 */
export interface ChartResultResponse {
	figure_json: Record<string, unknown>;
	chart_type: ChartType;
	width: number;
	height: number;
	row_count: number;
	analysis_id?: string | null;
}

/**
 * Dataset analysis record (chart/query history)
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
 * Dataset analysis list response
 */
export interface DatasetAnalysisListResponse {
	analyses: DatasetAnalysis[];
	total: number;
}

// ============================================================================
// Dataset Q&A / Conversation Types
// ============================================================================

/**
 * Ask request for dataset Q&A
 */
export interface AskRequest {
	question: string;
	conversation_id?: string | null;
}

/**
 * Single message in a dataset conversation
 */
export interface ConversationMessage {
	role: 'user' | 'assistant';
	content: string;
	timestamp: string;
	query_spec?: Record<string, unknown> | null;
	chart_spec?: ChartSpec | null;
	query_result?: Record<string, unknown> | null;
}

/**
 * Conversation response from API
 */
export interface ConversationResponse {
	id: string;
	dataset_id: string;
	messages: ConversationMessage[];
	created_at: string;
	updated_at: string;
}

/**
 * List of conversations response
 */
export interface ConversationListResponse {
	conversations: ConversationResponse[];
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

// ============================================================================
// Mentor Chat Types
// ============================================================================

export type MentorPersonaId = 'general' | 'action_coach' | 'data_analyst';

/**
 * Detailed mentor persona information
 */
export interface MentorPersonaDetail {
	id: MentorPersonaId;
	name: string;
	description: string;
	expertise: string[];
	icon: string;
}

/**
 * List of mentor personas response
 */
export interface MentorPersonaListResponse {
	personas: MentorPersonaDetail[];
	total: number;
}

/**
 * Mentor chat request
 */
export interface MentorChatRequest {
	message: string;
	conversation_id?: string | null;
	persona?: MentorPersonaId | null;
}

/**
 * Mentor message in a conversation
 */
export interface MentorMessage {
	role: 'user' | 'assistant';
	content: string;
	timestamp: string;
	persona?: MentorPersonaId | null;
}

/**
 * Mentor conversation summary
 */
export interface MentorConversationResponse {
	id: string;
	user_id: string;
	persona: MentorPersonaId;
	created_at: string;
	updated_at: string;
	message_count: number;
	context_sources: string[];
}

/**
 * Mentor conversation detail with messages
 */
export interface MentorConversationDetailResponse extends MentorConversationResponse {
	messages: MentorMessage[];
}

/**
 * List of mentor conversations
 */
export interface MentorConversationListResponse {
	conversations: MentorConversationResponse[];
	total: number;
}

/**
 * SSE event types for mentor chat streaming
 */
export type MentorChatEventType = 'thinking' | 'context' | 'response' | 'done' | 'error';

/**
 * Mention suggestion for autocomplete
 */
export interface MentionSuggestion {
	id: string;
	type: 'meeting' | 'action' | 'dataset';
	title: string;
	preview?: string | null;
}

/**
 * Mention search response
 */
export interface MentionSearchResponse {
	suggestions: MentionSuggestion[];
	total: number;
}

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

// ============================================================================
// Workspace & Invitation Types
// ============================================================================

/**
 * Member role in a workspace
 */
export type MemberRole = 'owner' | 'admin' | 'member';

/**
 * Invitation status
 */
export type InvitationStatus = 'pending' | 'accepted' | 'declined' | 'revoked' | 'expired';

/**
 * Workspace response
 */
export interface WorkspaceResponse {
	id: string;
	name: string;
	slug: string;
	owner_id: string;
	created_at: string;
	updated_at: string;
	member_count?: number;
}

/**
 * Workspace member response
 */
export interface WorkspaceMemberResponse {
	id: string;
	workspace_id: string;
	user_id: string;
	role: MemberRole;
	invited_by?: string;
	joined_at: string;
	user_email?: string;
	user_name?: string;
}

/**
 * Workspace list response
 */
export interface WorkspaceListResponse {
	workspaces: WorkspaceResponse[];
	total: number;
	default_workspace_id: string | null;
}

/**
 * Invitation create request
 */
export interface InvitationCreateRequest {
	email: string;
	role?: MemberRole;
}

/**
 * Invitation response
 */
export interface InvitationResponse {
	id: string;
	workspace_id: string;
	email: string;
	role: MemberRole;
	status: InvitationStatus;
	expires_at: string;
	created_at: string;
	invited_by?: string;
	accepted_at?: string;
	workspace_name?: string;
	inviter_name?: string;
}

/**
 * Invitation list response
 */
export interface InvitationListResponse {
	invitations: InvitationResponse[];
	total: number;
}

/**
 * Invitation accept request
 */
export interface InvitationAcceptRequest {
	token: string;
}

/**
 * Invitation decline request
 */
export interface InvitationDeclineRequest {
	token: string;
}

// ============================================================================
// Join Request Types
// ============================================================================

/**
 * Workspace discoverability setting
 */
export type WorkspaceDiscoverability = 'private' | 'invite_only' | 'request_to_join';

/**
 * Join request status
 */
export type JoinRequestStatus = 'pending' | 'approved' | 'rejected' | 'cancelled';

/**
 * Join request response
 */
export interface JoinRequestResponse {
	id: string;
	workspace_id: string;
	user_id: string;
	message: string | null;
	status: JoinRequestStatus;
	rejection_reason: string | null;
	reviewed_by: string | null;
	reviewed_at: string | null;
	created_at: string;
	user_email?: string;
	user_name?: string;
	workspace_name?: string;
}

/**
 * Join request list response
 */
export interface JoinRequestListResponse {
	requests: JoinRequestResponse[];
	total: number;
}

/**
 * Workspace settings update request
 */
export interface WorkspaceSettingsUpdate {
	discoverability?: WorkspaceDiscoverability;
}

// ============================================================================
// Role Transfer Types
// ============================================================================

/**
 * Transfer ownership request
 */
export interface TransferOwnershipRequest {
	new_owner_id: string;
	confirm: boolean;
}

/**
 * Role change record
 */
export interface RoleChangeResponse {
	id: string;
	workspace_id: string;
	user_id: string;
	user_email: string | null;
	old_role: string;
	new_role: string;
	change_type: string;
	changed_by: string | null;
	changed_by_email: string | null;
	changed_at: string;
}

/**
 * Role history response
 */
export interface RoleHistoryResponse {
	changes: RoleChangeResponse[];
	total: number;
}

// ============================================================================
// Industry Benchmarks Types
// ============================================================================

/**
 * Benchmark metric category
 */
export type BenchmarkCategory = 'growth' | 'retention' | 'efficiency' | 'engagement';

/**
 * Industry insight base content
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
 * Industry insight
 */
export interface IndustryInsight {
	id: string;
	industry: string;
	insight_type: 'trend' | 'benchmark' | 'competitor' | 'best_practice';
	content: InsightContent | BenchmarkContent | Record<string, unknown>;
	source_count: number;
	confidence: number;
	expires_at?: string;
	created_at: string;
	locked: boolean;
}

/**
 * Industry insights response
 */
export interface IndustryInsightsResponse {
	industry: string;
	insights: IndustryInsight[];
	has_benchmarks: boolean;
	locked_count: number;
	upgrade_prompt?: string;
	user_tier: string;
}

/**
 * Historical benchmark value entry
 */
export interface BenchmarkHistoryEntry {
	value: number;
	date: string; // YYYY-MM-DD
}

/**
 * Benchmark comparison result
 */
export interface BenchmarkComparison {
	metric_name: string;
	metric_unit: string;
	category: BenchmarkCategory;
	user_value?: number;
	user_value_updated_at?: string; // ISO timestamp when user value was last set
	history?: BenchmarkHistoryEntry[]; // Up to 6 historical values, newest first
	p25?: number;
	p50?: number;
	p75?: number;
	percentile?: number;
	status: 'below_average' | 'average' | 'above_average' | 'top_performer' | 'unknown' | 'locked';
	locked: boolean;
}

/**
 * Benchmark comparison response
 */
export interface BenchmarkComparisonResponse {
	industry: string;
	comparisons: BenchmarkComparison[];
	total_metrics: number;
	compared_count: number;
	locked_count: number;
	upgrade_prompt?: string;
}

/**
 * A stale benchmark needing user check-in
 */
export interface StaleBenchmark {
	field_name: string;
	display_name: string;
	current_value: number | string | null;
	days_since_update: number;
}

/**
 * Response for stale benchmarks check
 */
export interface StaleBenchmarksResponse {
	has_stale_benchmarks: boolean;
	stale_benchmarks: StaleBenchmark[];
	threshold_days: number;
}

// =============================================================================
// Usage & Tier Types
// =============================================================================

/**
 * Single metric usage details
 */
export interface UsageMetric {
	metric: string;
	current: number;
	limit: number;
	remaining: number;
	reset_at: string | null;
}

/**
 * User usage response
 */
export interface UsageResponse {
	tier: string;
	effective_tier: string;
	metrics: UsageMetric[];
	features: Record<string, boolean>;
}

/**
 * Tier limits response
 */
export interface TierLimitsResponse {
	tier: string;
	limits: Record<string, number>;
	features: Record<string, boolean>;
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

// =============================================================================
// Feedback Types
// =============================================================================

/**
 * Feedback type
 */
export type FeedbackType = 'feature_request' | 'problem_report';

/**
 * Feedback status
 */
export type FeedbackStatus = 'new' | 'reviewing' | 'resolved' | 'closed';

/**
 * Feedback create request
 */
export interface FeedbackCreateRequest extends HoneypotFields {
	type: FeedbackType;
	title: string;
	description: string;
	include_context?: boolean;
}

/**
 * Feedback context (auto-attached for problem reports)
 */
export interface FeedbackContext {
	user_tier?: string;
	page_url?: string;
	user_agent?: string;
	timestamp?: string;
}

/**
 * Feedback response
 */
export interface FeedbackResponse {
	id: string;
	user_id: string;
	type: FeedbackType;
	title: string;
	description: string;
	context?: FeedbackContext | null;
	status: FeedbackStatus;
	created_at: string;
	updated_at: string;
}

/**
 * Feedback list response
 */
export interface FeedbackListResponse {
	items: FeedbackResponse[];
	total: number;
}

/**
 * Feedback stats response
 */
export interface FeedbackStatsResponse {
	total: number;
	by_type: Record<FeedbackType, number>;
	by_status: Record<FeedbackStatus, number>;
}

// =============================================================================
// Calendar Integration Types
// =============================================================================

/**
 * Google Calendar connection status
 */
export interface CalendarStatusResponse {
	connected: boolean;
	connected_at: string | null;
	feature_enabled: boolean;
	sync_enabled: boolean;
}

// =============================================================================
// Session-Project Linking Types
// =============================================================================

/**
 * Request to link projects to a session
 */
export interface SessionProjectLinkRequest {
	project_ids: string[];
	relationship?: 'discusses' | 'created_from' | 'replanning';
}

/**
 * A project linked to a session
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
 * A project available for linking (same workspace)
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
 * Response with available projects for linking
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

// =============================================================================
// Value Metrics Types
// =============================================================================

// TrendDirection already defined earlier in this file (line ~270)

/**
 * Metric type classification for color coding
 */
export type MetricType = 'higher_is_better' | 'lower_is_better' | 'neutral';

/**
 * A single value metric with trend information
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
 * Response from GET /api/v1/user/value-metrics
 */
export interface ValueMetricsResponse {
	metrics: ValueMetric[];
	has_context: boolean;
	has_history: boolean;
}

// ============================================================================
// Extended KPIs Types (Admin)
// ============================================================================

/**
 * Mentor session statistics
 */
export interface MentorSessionStats {
	total_sessions: number;
	sessions_today: number;
	sessions_this_week: number;
	sessions_this_month: number;
}

/**
 * Dataset analysis statistics
 */
export interface DataAnalysisStats {
	total_analyses: number;
	analyses_today: number;
	analyses_this_week: number;
	analyses_this_month: number;
}

/**
 * Project statistics by status
 */
export interface ProjectStats {
	total_projects: number;
	active: number;
	paused: number;
	completed: number;
	archived: number;
}

/**
 * Action statistics by status
 */
export interface ActionKPIStats {
	total_actions: number;
	pending: number;
	in_progress: number;
	completed: number;
	cancelled: number;
}

/**
 * Extended KPIs response from GET /api/admin/extended-kpis
 */
export interface ExtendedKPIsResponse {
	mentor_sessions: MentorSessionStats;
	data_analyses: DataAnalysisStats;
	projects: ProjectStats;
	actions: ActionKPIStats;
}

// ============================================================================
// Kanban Column Preferences
// ============================================================================

/**
 * Single kanban column configuration
 */
export interface KanbanColumn {
	id: ActionStatus;
	title: string;
	color?: string | null;
}

/**
 * Kanban columns response
 */
export interface KanbanColumnsResponse {
	columns: KanbanColumn[];
}

/**
 * Kanban columns update request
 */
export interface KanbanColumnsUpdate {
	columns: KanbanColumn[];
}

// ============================================================================
// Public Blog Types
// ============================================================================

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
