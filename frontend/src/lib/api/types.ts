/**
 * API Types - TypeScript interfaces for Board of One API
 *
 * These types match the Pydantic models in backend/api/models.py
 */

export interface CreateSessionRequest {
	problem_statement: string;
	problem_context?: Record<string, unknown>;
	dataset_id?: string;
}

export interface StaleInsight {
	question: string;
	days_stale: number;
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
		[key: string]: any;
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
 * A clarification answer from a meeting
 */
export interface ClarificationInsight {
	question: string;
	answer: string;
	answered_at?: string;
	session_id?: string;
}

/**
 * Response containing user's accumulated insights
 */
export interface InsightsResponse {
	clarifications: ClarificationInsight[];
	total_count: number;
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
}

/**
 * Action status enum (6 states)
 */
export type ActionStatus = 'todo' | 'in_progress' | 'blocked' | 'in_review' | 'done' | 'cancelled';

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
	events: unknown[];
	count: number;
}

/**
 * Task with session context for global actions view
 */
export interface TaskWithSessionContext extends TaskWithStatus {
	session_id: string;
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
	created_count: number;
	sessions_run: number;
	sessions_completed: number;
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

export type MentorPersona = 'general' | 'action_coach' | 'data_analyst';

/**
 * Mentor chat request
 */
export interface MentorChatRequest {
	message: string;
	conversation_id?: string | null;
	persona?: MentorPersona | null;
}

/**
 * Mentor message in a conversation
 */
export interface MentorMessage {
	role: 'user' | 'assistant';
	content: string;
	timestamp: string;
	persona?: MentorPersona | null;
}

/**
 * Mentor conversation summary
 */
export interface MentorConversationResponse {
	id: string;
	user_id: string;
	persona: MentorPersona;
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
