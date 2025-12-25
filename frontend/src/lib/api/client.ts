/**
 * API Client - Board of One Backend API Client
 *
 * Handles all HTTP communication with the FastAPI backend.
 * Includes error handling, type safety, and environment-based configuration.
 */

import { env } from '$env/dynamic/public';
import { operationTracker } from '../services/operation-tracker';
import type {
	CreateSessionRequest,
	SessionResponse,
	SessionDetailResponse,
	SessionListResponse,
	ControlResponse,
	HealthResponse,
	ApiError,
	UserContextResponse,
	UserContext,
	AdminUser,
	AdminUserListResponse,
	AdminUserUpdateRequest,
	WhitelistEntry,
	WhitelistResponse,
	WaitlistResponse,
	WaitlistApprovalResponse,
	TaskExtractionResponse,
	SessionEventsResponse,
	SessionActionsResponse,
	TaskStatusUpdateRequest,
	AllActionsResponse,
	ActionDetailResponse,
	ActionStatus,
	// Project types
	ProjectStatus,
	ProjectCreateRequest,
	ProjectUpdateRequest,
	ProjectDetailResponse,
	ProjectListResponse,
	ProjectActionsResponse,
	ProjectSessionsResponse,
	GanttResponse,
	// Action Update types (Phase 5)
	ActionUpdateCreateRequest,
	ActionUpdateResponse,
	ActionUpdatesResponse,
	// Action Dates types (Gantt drag-to-reschedule)
	ActionDatesUpdateRequest,
	ActionDatesResponse,
	// Replanning types (Phase 7)
	ReplanRequest,
	ReplanResponse,
	// Tag types
	TagCreateRequest,
	TagUpdateRequest,
	TagResponse,
	TagListResponse,
	ActionTagsUpdateRequest,
	// Dependency types
	DependencyType,
	DependencyListResponse,
	DependencyMutationResponse,
	// Global Gantt types
	GlobalGanttResponse,
	// Insights types
	InsightsResponse,
	ClarificationInsight,
	// Pending Updates types (Phase 6)
	PendingUpdatesResponse,
	ApproveUpdateResponse,
	// Action Stats types
	ActionStatsResponse,
	// Action Reminder types
	ActionRemindersResponse,
	ReminderSettingsResponse,
	ReminderSettingsUpdateRequest,
	// Unblock Suggestions types
	UnblockPathsResponse,
	// Query types (Data Analysis)
	QuerySpec,
	QueryResultResponse,
	// Dataset types (Data Analysis)
	Dataset,
	DatasetDetailResponse,
	DatasetListResponse,
	DatasetProfile,
	ChartSpec,
	ChartResultResponse,
	DatasetAnalysis,
	DatasetAnalysisListResponse,
	// Conversation types (Dataset Q&A)
	ConversationResponse,
	ConversationListResponse,
	// Mentor Chat types
	MentorConversationResponse,
	MentorConversationListResponse,
	MentorConversationDetailResponse,
	MentorPersonaListResponse,
	MentionSearchResponse,
	// Workspace & Invitation types
	InvitationResponse,
	InvitationListResponse,
	WorkspaceResponse,
	WorkspaceListResponse,
	// Join Request types
	JoinRequestResponse,
	JoinRequestListResponse,
	// Role Management types
	WorkspaceMemberResponse,
	RoleHistoryResponse,
	WorkspaceSettingsUpdate,
	WorkspaceDiscoverability,
	// Industry Benchmarks types
	IndustryInsight,
	IndustryInsightsResponse,
	BenchmarkComparisonResponse,
	StaleBenchmarksResponse,
	// Usage & Tier types
	UsageResponse,
	TierLimitsResponse,
	// Feedback types
	FeedbackCreateRequest,
	FeedbackResponse,
	// Calendar types
	CalendarStatusResponse,
	// Session-Project types
	SessionProjectLinkRequest,
	SessionProjectsResponse,
	AvailableProjectsResponse,
	ProjectSuggestionsResponse,
	CreatedProjectResponse,
	// Autogen types
	AutogenSuggestion,
	AutogenSuggestionsResponse,
	AutogenCreateResponse,
	UnassignedCountResponse,
	// Context suggestion types
	ContextProjectSuggestion,
	ContextSuggestionsResponse,
	// Cost Calculator types
	CostCalculatorDefaults,
	// Value Metrics types
	ValueMetricsResponse,
	// Extended KPIs types (Admin)
	ExtendedKPIsResponse,
	// Kanban Column Preferences
	KanbanColumn,
	KanbanColumnsResponse,
	// Public Blog types
	PublicBlogPost,
	PublicBlogPostListResponse,
	// Meeting Template types
	MeetingTemplate,
	MeetingTemplateListResponse,
	// Competitor Insight types
	CompetitorInsightResponse,
	CompetitorInsightsListResponse,
	// Trend Insight types
	TrendInsightResponse,
	TrendInsightsListResponse,
	// Managed Competitor types
	ManagedCompetitor,
	ManagedCompetitorCreate,
	ManagedCompetitorUpdate,
	ManagedCompetitorResponse,
	ManagedCompetitorListResponse
} from './types';

// Re-export types that are used by other modules
export type { ClarificationInsight, IndustryInsight, IndustryInsightsResponse };

// ============================================================================
// Onboarding Types
// ============================================================================

export type OnboardingStep = 'business_context' | 'first_meeting' | 'expert_panel' | 'results';

export interface OnboardingStatus {
	tour_completed: boolean;
	tour_completed_at: string | null;
	steps_completed: OnboardingStep[];
	context_setup: boolean;
	first_meeting_id: string | null;
	needs_onboarding: boolean;
}

export interface DemoQuestion {
	question: string;
	category: string;
	relevance: string;
}

export interface DemoQuestionsResponse {
	questions: DemoQuestion[];
	generated: boolean;
	cached: boolean;
}

export interface EnrichmentRequest {
	url: string;
}

export interface EnrichmentResponse {
	success: boolean;
	context?: UserContext;
	enrichment_source?: string;
	confidence?: string;
	error?: string;
}

export interface StaleFieldSummary {
	field_name: string;
	display_name: string;
	volatility: 'volatile' | 'moderate' | 'stable';
	days_since_update: number;
	action_affected: boolean;
}

export interface RefreshCheckResponse {
	needs_refresh: boolean;
	last_updated: string | null;
	days_since_update: number | null;
	stale_metrics: StaleFieldSummary[];
	highest_urgency: 'action_affected' | 'volatile' | 'moderate' | 'stable' | null;
}

export interface DismissRefreshRequest {
	volatility?: 'volatile' | 'moderate' | 'stable' | 'action_affected';
}

// ============================================================================
// Strategic Context Types (Phase 3)
// ============================================================================

export interface DetectedCompetitor {
	name: string;
	url: string | null;
	description: string | null;
}

export interface CompetitorDetectRequest {
	industry?: string;
	product_description?: string;
}

export interface CompetitorDetectResponse {
	success: boolean;
	competitors: DetectedCompetitor[];
	error?: string;
}

export interface MarketTrend {
	trend: string;
	source: string | null;
	source_url: string | null;
}

export interface TrendsRefreshRequest {
	industry?: string;
}

export interface TrendsRefreshResponse {
	success: boolean;
	trends: MarketTrend[];
	error?: string;
}

// ============================================================================
// Competitor Watch Types
// ============================================================================

export interface CompetitorProfile {
	id?: string;
	name: string;
	website?: string | null;
	tagline?: string | null;
	industry?: string | null;
	// Standard tier
	product_description?: string | null;
	pricing_model?: string | null;
	target_market?: string | null;
	business_model?: string | null;
	// Deep tier
	value_proposition?: string | null;
	tech_stack?: string[] | null;
	recent_news?: { title: string; url: string; date: string }[] | null;
	funding_info?: string | null;
	employee_count?: string | null;
	// Metadata
	display_order?: number;
	is_primary?: boolean;
	data_depth?: 'basic' | 'standard' | 'deep';
	last_enriched_at?: string | null;
	changes_detected?: string[] | null;
	created_at?: string;
	updated_at?: string;
}

export interface CompetitorListResponse {
	competitors: CompetitorProfile[];
	tier: string;
	max_allowed: number;
	data_depth: 'basic' | 'standard' | 'deep';
}

export interface CompetitorCreateRequest {
	name: string;
	website?: string;
	is_primary?: boolean;
}

export interface CompetitorEnrichResponse {
	success: boolean;
	competitor?: CompetitorProfile;
	changes?: string[];
	error?: string;
}

export interface CompetitorBulkEnrichResponse {
	success: boolean;
	enriched_count: number;
	competitors: CompetitorProfile[];
	errors?: string[];
}

// ============================================================================
// Industry Insights Types (Phase 4)
// ============================================================================

// IndustryInsight and IndustryInsightsResponse imported from ./types

// ============================================================================
// Business Metrics Types
// ============================================================================

export type MetricCategory = 'financial' | 'growth' | 'retention' | 'efficiency' | 'custom';
export type MetricSource = 'manual' | 'clarification' | 'integration';

export interface MetricTemplate {
	metric_key: string;
	name: string;
	definition: string;
	importance: string;
	category: MetricCategory;
	value_unit: string;
	display_order: number;
	applies_to: string[];
}

export interface UserMetric {
	id: string;
	user_id: string;
	metric_key: string;
	name: string;
	definition: string | null;
	importance: string | null;
	category: MetricCategory | null;
	value: number | null;
	value_unit: string | null;
	captured_at: string | null;
	source: MetricSource;
	is_predefined: boolean;
	display_order: number;
	created_at: string;
	updated_at: string;
}

export interface MetricsResponse {
	metrics: UserMetric[];
	templates: MetricTemplate[];
}

export interface UpdateMetricRequest {
	value: number | null;
	source?: MetricSource;
}

export interface CreateMetricRequest {
	metric_key: string;
	name: string;
	definition?: string;
	importance?: string;
	category?: MetricCategory;
	value_unit: string;
	value?: number;
}

// ============================================================================
// Billing Types
// ============================================================================

export interface PlanDetails {
	tier: string;
	name: string;
	price_monthly: number;
	meetings_limit: number | null;
	features: string[];
	billing_cycle_start: string | null;
	billing_cycle_end: string | null;
}

export interface UsageStats {
	meetings_used: number;
	meetings_limit: number | null;
	meetings_remaining: number | null;
	api_calls_used: number;
	total_cost_cents: number;
	period_start: string | null;
	period_end: string | null;
}

export interface BillingPortalResponse {
	url: string | null;
	message: string;
	available: boolean;
}

export interface CheckoutRequest {
	price_id: string;
}

export interface CheckoutResponse {
	session_id: string;
	url: string;
}

// Workspace Billing Types
export interface WorkspaceBillingInfoResponse {
	workspace_id: string;
	workspace_name: string;
	tier: string;
	billing_email: string | null;
	has_billing_account: boolean;
	is_billing_owner: boolean;
	can_manage_billing: boolean;
}

export interface WorkspacePortalResponse {
	url: string;
}

// Privacy & GDPR Types
export interface EmailPreferences {
	meeting_emails: boolean;
	reminder_emails: boolean;
	digest_emails: boolean;
}

export interface EmailPreferencesResponse {
	preferences: EmailPreferences;
}

export interface AccountDeletionResponse {
	status: string;
	message: string;
	summary: {
		sessions_anonymized: number;
		actions_anonymized: number;
		datasets_deleted: number;
	};
}

export interface RetentionSettingResponse {
	data_retention_days: number;
}

export interface RetentionSettingUpdate {
	days: number;
}

export interface UserPreferences {
	skip_clarification: boolean;
}

export interface UserPreferencesResponse {
	skip_clarification: boolean;
}

// ============================================================================
// CSRF Token Utilities
// ============================================================================

/**
 * Read the CSRF token from the csrf_token cookie.
 * Returns null if not found (e.g., before first GET request).
 */
export function getCsrfToken(): string | null {
	if (typeof document === 'undefined') return null; // SSR safety
	const match = document.cookie.match(/(?:^|; )csrf_token=([^;]*)/);
	return match ? decodeURIComponent(match[1]) : null;
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Build a query string from optional parameters.
 *
 * @param params - Object of key-value pairs (values can be string, number, or undefined)
 * @returns Query string without leading '?' or empty string if no params
 */
function buildQueryString(params: Record<string, string | number | undefined>): string {
	const searchParams = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value !== undefined) {
			searchParams.set(key, String(value));
		}
	}
	return searchParams.toString();
}

/**
 * Append query string to endpoint if params exist.
 *
 * @param endpoint - Base endpoint path
 * @param params - Optional query parameters
 * @returns Endpoint with query string appended if needed
 */
function withQueryString(endpoint: string, params: Record<string, string | number | undefined>): string {
	const query = buildQueryString(params);
	return query ? `${endpoint}?${query}` : endpoint;
}

/**
 * Merge headers from various formats into a single Record.
 *
 * @param defaultHeaders - Default headers to start with
 * @param optionHeaders - Headers from RequestInit options (Headers, array, or object)
 * @returns Merged headers as Record
 */
function mergeHeaders(
	defaultHeaders: Record<string, string>,
	optionHeaders?: HeadersInit
): Record<string, string> {
	const headers = { ...defaultHeaders };

	if (!optionHeaders) return headers;

	if (optionHeaders instanceof Headers) {
		optionHeaders.forEach((value, key) => {
			headers[key] = value;
		});
	} else if (Array.isArray(optionHeaders)) {
		optionHeaders.forEach(([key, value]) => {
			headers[key] = value;
		});
	} else {
		Object.assign(headers, optionHeaders);
	}

	return headers;
}

// ============================================================================
// Error Class
// ============================================================================

/**
 * Custom error class for API errors
 */
export class ApiClientError extends Error {
	constructor(
		message: string,
		public status?: number,
		public details?: unknown
	) {
		super(message);
		this.name = 'ApiClientError';
	}
}

// ============================================================================
// API Client Class
// ============================================================================

/**
 * API Client for Board of One backend
 */
export class ApiClient {
	private baseUrl: string;

	constructor(baseUrl?: string) {
		this.baseUrl = baseUrl || env.PUBLIC_API_URL || 'http://localhost:8000';
	}

	/**
	 * Internal fetch wrapper with error handling and authentication.
	 *
	 * BFF Pattern: Authentication via httpOnly cookies (no tokens in localStorage).
	 * Cookies are automatically sent with credentials: 'include'.
	 * CSRF token is attached to mutating requests via X-CSRF-Token header.
	 *
	 * Includes operation tracking for observability.
	 */
	private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
		const url = `${this.baseUrl}${endpoint}`;
		const defaultHeaders: Record<string, string> = { 'Content-Type': 'application/json' };

		// Add CSRF token for mutating methods
		const method = options?.method?.toUpperCase() || 'GET';
		if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
			const csrfToken = getCsrfToken();
			if (csrfToken) {
				defaultHeaders['X-CSRF-Token'] = csrfToken;
			}
		}

		const headers = mergeHeaders(defaultHeaders, options?.headers);

		// Track operation for observability
		const opName = `api:${method}:${endpoint.split('?')[0]}`;
		const opId = operationTracker.startOp(opName, { endpoint, method });

		try {
			const response = await fetch(url, {
				...options,
				credentials: 'include',
				headers
			});

			if (!response.ok) {
				let error: ApiError;
				try {
					error = await response.json();
				} catch {
					error = { detail: response.statusText, status: response.status };
				}
				const apiError = new ApiClientError(error.detail || 'Unknown error', response.status, error);
				operationTracker.failOp(opId, apiError.message, { status: response.status });
				throw apiError;
			}

			if (response.status === 204) {
				operationTracker.endOp(opId, { status: 204 });
				return {} as T;
			}

			const result = await response.json();
			operationTracker.endOp(opId, { status: response.status });
			return result;
		} catch (error) {
			if (error instanceof ApiClientError) {
				// Already tracked above
				throw error;
			}
			operationTracker.failOp(opId, error instanceof Error ? error.message : 'Network error');
			throw new ApiClientError(
				error instanceof Error ? error.message : 'Network error',
				undefined,
				error
			);
		}
	}

	/**
	 * POST request helper
	 */
	private post<T>(endpoint: string, data?: unknown): Promise<T> {
		return this.fetch<T>(endpoint, {
			method: 'POST',
			body: data !== undefined ? JSON.stringify(data) : undefined
		});
	}

	/**
	 * PUT request helper
	 */
	private put<T>(endpoint: string, data: unknown): Promise<T> {
		return this.fetch<T>(endpoint, {
			method: 'PUT',
			body: JSON.stringify(data)
		});
	}

	/**
	 * PATCH request helper
	 */
	private patch<T>(endpoint: string, data: unknown): Promise<T> {
		return this.fetch<T>(endpoint, {
			method: 'PATCH',
			body: JSON.stringify(data)
		});
	}

	/**
	 * DELETE request helper
	 */
	private delete<T>(endpoint: string): Promise<T> {
		return this.fetch<T>(endpoint, { method: 'DELETE' });
	}

	// ==========================================================================
	// Health Endpoints
	// ==========================================================================

	async healthCheck(): Promise<HealthResponse> {
		return this.fetch<HealthResponse>('/api/health');
	}

	async healthCheckDb(): Promise<HealthResponse> {
		return this.fetch<HealthResponse>('/api/health/db');
	}

	async healthCheckRedis(): Promise<HealthResponse> {
		return this.fetch<HealthResponse>('/api/health/redis');
	}

	async healthCheckAnthropic(): Promise<HealthResponse> {
		return this.fetch<HealthResponse>('/api/health/anthropic');
	}

	// ==========================================================================
	// Session Endpoints
	// ==========================================================================

	async createSession(request: CreateSessionRequest): Promise<SessionResponse> {
		return this.post<SessionResponse>('/api/v1/sessions', request);
	}

	async getMeetingCapStatus(): Promise<import('./types').MeetingCapStatus> {
		return this.fetch<import('./types').MeetingCapStatus>('/api/v1/sessions/cap-status');
	}

	async getRecentFailures(hours?: number): Promise<import('./types').RecentFailuresResponse> {
		const endpoint = hours ? `/api/v1/sessions/recent-failures?hours=${hours}` : '/api/v1/sessions/recent-failures';
		return this.fetch<import('./types').RecentFailuresResponse>(endpoint);
	}

	/**
	 * Acknowledge failed meetings to make their actions visible.
	 * Call this when user dismisses the failed meeting alert.
	 */
	async acknowledgeFailures(sessionIds: string[]): Promise<{ status: string; message: string }> {
		return this.post<{ status: string; message: string }>('/api/v1/sessions/acknowledge-failures', {
			session_ids: sessionIds
		});
	}

	async listSessions(params?: { status?: string; limit?: number; offset?: number }): Promise<SessionListResponse> {
		const endpoint = withQueryString('/api/v1/sessions', params || {});
		return this.fetch<SessionListResponse>(endpoint);
	}

	async getSession(sessionId: string): Promise<SessionDetailResponse> {
		return this.fetch<SessionDetailResponse>(`/api/v1/sessions/${sessionId}`);
	}

	async getSessionEvents(sessionId: string): Promise<SessionEventsResponse> {
		return this.fetch<SessionEventsResponse>(`/api/v1/sessions/${sessionId}/events`);
	}

	async deleteSession(sessionId: string): Promise<SessionResponse> {
		return this.delete<SessionResponse>(`/api/v1/sessions/${sessionId}`);
	}

	// ==========================================================================
	// Control Endpoints
	// ==========================================================================

	async startDeliberation(sessionId: string): Promise<ControlResponse> {
		return this.post<ControlResponse>(`/api/v1/sessions/${sessionId}/start`);
	}

	async pauseDeliberation(sessionId: string): Promise<ControlResponse> {
		return this.post<ControlResponse>(`/api/v1/sessions/${sessionId}/pause`);
	}

	async resumeDeliberation(sessionId: string): Promise<ControlResponse> {
		return this.post<ControlResponse>(`/api/v1/sessions/${sessionId}/resume`);
	}

	async killDeliberation(sessionId: string, reason?: string): Promise<ControlResponse> {
		return this.post<ControlResponse>(`/api/v1/sessions/${sessionId}/kill`, {
			reason: reason || 'User requested termination'
		});
	}

	/**
	 * Retry a failed session from its last checkpoint.
	 * Unlike resume (for paused sessions), retry handles failed sessions
	 * by resetting error state and continuing from the last successful checkpoint.
	 *
	 * @param sessionId - Session identifier
	 * @returns ControlResponse with retry confirmation
	 */
	async retrySession(sessionId: string): Promise<ControlResponse> {
		return this.post<ControlResponse>(`/api/v1/sessions/${sessionId}/retry`);
	}

	/**
	 * Raise hand to interject during an active meeting.
	 * Experts will acknowledge and respond to the user's question/context.
	 *
	 * @param sessionId - Session identifier
	 * @param message - User's interjection message (question or context)
	 */
	async raiseHand(sessionId: string, message: string): Promise<ControlResponse> {
		return this.post<ControlResponse>(`/api/v1/sessions/${sessionId}/raise-hand`, { message });
	}

	// ==========================================================================
	// Context Endpoints
	// ==========================================================================

	async getUserContext(): Promise<UserContextResponse> {
		return this.fetch<UserContextResponse>('/api/v1/context');
	}

	async updateUserContext(context: UserContext): Promise<{ status: string }> {
		return this.put<{ status: string }>('/api/v1/context', context);
	}

	async deleteUserContext(): Promise<{ status: string }> {
		return this.delete<{ status: string }>('/api/v1/context');
	}

	async getGoalHistory(limit = 10): Promise<{ entries: Array<{ goal_text: string; changed_at: string; previous_goal: string | null }> }> {
		return this.fetch<{ entries: Array<{ goal_text: string; changed_at: string; previous_goal: string | null }> }>(`/api/v1/context/goal-history?limit=${limit}`);
	}

	async getValueMetrics(): Promise<ValueMetricsResponse> {
		return this.fetch<ValueMetricsResponse>('/api/v1/user/value-metrics');
	}

	async getDemoQuestions(refresh: boolean = false): Promise<DemoQuestionsResponse> {
		const endpoint = refresh ? '/api/v1/context/demo-questions?refresh=true' : '/api/v1/context/demo-questions';
		return this.fetch<DemoQuestionsResponse>(endpoint);
	}

	// ==========================================================================
	// Insights Endpoints (Clarifications from Meetings)
	// ==========================================================================

	async getInsights(): Promise<InsightsResponse> {
		return this.fetch<InsightsResponse>('/api/v1/context/insights');
	}

	async updateInsight(question: string, value: string, note?: string): Promise<ClarificationInsight> {
		// Encode question as URL-safe base64
		const questionHash = btoa(question)
			.replace(/\+/g, '-')
			.replace(/\//g, '_')
			.replace(/=+$/, '');
		return this.patch<ClarificationInsight>(`/api/v1/context/insights/${questionHash}`, {
			value,
			note
		});
	}

	async deleteInsight(question: string): Promise<{ status: string }> {
		// Encode question as URL-safe base64
		const questionHash = btoa(question)
			.replace(/\+/g, '-')
			.replace(/\//g, '_')
			.replace(/=+$/, '');
		return this.delete<{ status: string }>(`/api/v1/context/insights/${questionHash}`);
	}

	// ==========================================================================
	// Pending Context Updates (Phase 6)
	// ==========================================================================

	async getPendingUpdates(): Promise<PendingUpdatesResponse> {
		return this.fetch<PendingUpdatesResponse>('/api/v1/context/pending-updates');
	}

	async approvePendingUpdate(suggestionId: string): Promise<ApproveUpdateResponse> {
		return this.post<ApproveUpdateResponse>(
			`/api/v1/context/pending-updates/${suggestionId}/approve`,
			{}
		);
	}

	async dismissPendingUpdate(suggestionId: string): Promise<{ status: string }> {
		return this.delete<{ status: string }>(`/api/v1/context/pending-updates/${suggestionId}`);
	}

	async submitClarification(sessionId: string, answer: string): Promise<ControlResponse> {
		return this.post<ControlResponse>(`/api/v1/sessions/${sessionId}/clarify`, { answer });
	}

	// ==========================================================================
	// Session Termination
	// ==========================================================================

	/**
	 * Terminate a session early with partial billing
	 * @param sessionId - Session ID
	 * @param terminationType - Type of termination: blocker_identified, user_cancelled, continue_best_effort
	 * @param reason - Optional user-provided reason
	 */
	async terminateSession(
		sessionId: string,
		terminationType: 'blocker_identified' | 'user_cancelled' | 'continue_best_effort',
		reason?: string
	): Promise<{
		session_id: string;
		status: string;
		terminated_at: string;
		termination_type: string;
		billable_portion: number;
		completed_sub_problems: number;
		total_sub_problems: number;
		synthesis_available: boolean;
	}> {
		return this.post(`/api/v1/sessions/${sessionId}/terminate`, {
			termination_type: terminationType,
			reason
		});
	}

	// ==========================================================================
	// Task Extraction Endpoint
	// ==========================================================================

	async extractTasks(sessionId: string): Promise<TaskExtractionResponse> {
		return this.post<TaskExtractionResponse>(`/api/v1/sessions/${sessionId}/extract-tasks`);
	}

	// ==========================================================================
	// Actions/Kanban Endpoints
	// ==========================================================================

	async getSessionActions(sessionId: string): Promise<SessionActionsResponse> {
		return this.fetch<SessionActionsResponse>(`/api/v1/sessions/${sessionId}/actions`);
	}

	async updateTaskStatus(
		sessionId: string,
		taskId: string,
		status: TaskStatusUpdateRequest['status']
	): Promise<{ status: string; message: string }> {
		return this.patch<{ status: string; message: string }>(
			`/api/v1/sessions/${sessionId}/actions/${taskId}`,
			{ status }
		);
	}

	// ==========================================================================
	// Global Actions Endpoints
	// ==========================================================================

	async getAllActions(params?: {
		status_filter?: ActionStatus;
		project_id?: string;
		session_id?: string;
		tag_ids?: string;
		limit?: number;
		offset?: number;
	}): Promise<AllActionsResponse> {
		const endpoint = withQueryString('/api/v1/actions', params || {});
		return this.fetch<AllActionsResponse>(endpoint);
	}

	async getActionDetail(actionId: string): Promise<ActionDetailResponse> {
		return this.fetch<ActionDetailResponse>(`/api/v1/actions/${actionId}`);
	}

	async deleteAction(actionId: string): Promise<{ message: string; action_id: string }> {
		return this.delete<{ message: string; action_id: string }>(`/api/v1/actions/${actionId}`);
	}

	async startAction(actionId: string): Promise<{ message: string; action_id: string }> {
		return this.post<{ message: string; action_id: string }>(`/api/v1/actions/${actionId}/start`);
	}

	async completeAction(
		actionId: string,
		postMortem?: { lessonsLearned?: string; wentWell?: string }
	): Promise<{ message: string; action_id: string }> {
		const body = postMortem
			? {
					lessons_learned: postMortem.lessonsLearned || null,
					went_well: postMortem.wentWell || null
				}
			: undefined;
		return this.post<{ message: string; action_id: string }>(
			`/api/v1/actions/${actionId}/complete`,
			body
		);
	}

	async updateActionStatus(
		actionId: string,
		status: ActionStatus,
		options?: { blockingReason?: string; cancellationReason?: string }
	): Promise<{ message: string; action_id: string; status: string }> {
		return this.patch<{ message: string; action_id: string; status: string }>(
			`/api/v1/actions/${actionId}/status`,
			{
				status,
				blocking_reason: options?.blockingReason,
				cancellation_reason: options?.cancellationReason
			}
		);
	}

	async closeAction(
		actionId: string,
		status: 'failed' | 'abandoned',
		reason: string
	): Promise<{ action_id: string; status: string; message: string }> {
		return this.post<{ action_id: string; status: string; message: string }>(
			`/api/v1/actions/${actionId}/close`,
			{ status, reason }
		);
	}

	async cloneReplanAction(
		actionId: string,
		options?: { newSteps?: string[]; newTargetDate?: string }
	): Promise<{ new_action_id: string; original_action_id: string; message: string }> {
		return this.post<{ new_action_id: string; original_action_id: string; message: string }>(
			`/api/v1/actions/${actionId}/clone-replan`,
			{
				new_steps: options?.newSteps,
				new_target_date: options?.newTargetDate
			}
		);
	}

	async getGlobalGantt(params?: {
		status_filter?: ActionStatus;
		project_id?: string;
		session_id?: string;
		tag_ids?: string;
	}): Promise<GlobalGanttResponse> {
		const endpoint = withQueryString('/api/v1/actions/gantt', params || {});
		return this.fetch<GlobalGanttResponse>(endpoint);
	}

	async getActionStats(days?: number): Promise<ActionStatsResponse> {
		const endpoint = withQueryString('/api/v1/actions/stats', days ? { days } : {});
		return this.fetch<ActionStatsResponse>(endpoint);
	}

	// ==========================================================================
	// Action Reminders Endpoints
	// ==========================================================================

	async getActionReminders(limit?: number): Promise<ActionRemindersResponse> {
		const endpoint = withQueryString('/api/v1/actions/reminders', limit ? { limit } : {});
		return this.fetch<ActionRemindersResponse>(endpoint);
	}

	async getActionReminderSettings(actionId: string): Promise<ReminderSettingsResponse> {
		return this.fetch<ReminderSettingsResponse>(`/api/v1/actions/${actionId}/reminder-settings`);
	}

	async updateActionReminderSettings(
		actionId: string,
		settings: ReminderSettingsUpdateRequest
	): Promise<ReminderSettingsResponse> {
		return this.patch<ReminderSettingsResponse>(`/api/v1/actions/${actionId}/reminder-settings`, settings);
	}

	async snoozeActionReminder(actionId: string, snoozeDays: number): Promise<{ message: string }> {
		return this.post<{ message: string }>(`/api/v1/actions/${actionId}/snooze-reminder`, {
			snooze_days: snoozeDays
		});
	}

	// ==========================================================================
	// Action Unblock Suggestions Endpoints
	// ==========================================================================

	/**
	 * Get AI-generated suggestions for unblocking a blocked action.
	 * Rate limited to 5 requests per minute.
	 */
	async suggestUnblockPaths(actionId: string): Promise<UnblockPathsResponse> {
		return this.post<UnblockPathsResponse>(`/api/v1/actions/${actionId}/suggest-unblock`, {});
	}

	/**
	 * Escalate a blocked action to a meeting for AI-assisted resolution.
	 * Creates a deliberation session with action context and optional suggestions.
	 * Rate limited to 1 request per minute.
	 */
	async escalateBlocker(
		actionId: string,
		includeSuggestions: boolean = true
	): Promise<{ session_id: string; redirect_url: string }> {
		return this.post<{ session_id: string; redirect_url: string }>(
			`/api/v1/actions/${actionId}/escalate-blocker`,
			{ include_suggestions: includeSuggestions }
		);
	}

	// ==========================================================================
	// Admin Endpoints - Users
	// ==========================================================================

	async listUsers(params?: { page?: number; per_page?: number; email?: string }): Promise<AdminUserListResponse> {
		const endpoint = withQueryString('/api/admin/users', params || {});
		return this.fetch<AdminUserListResponse>(endpoint);
	}

	async getUser(userId: string): Promise<AdminUser> {
		return this.fetch<AdminUser>(`/api/admin/users/${userId}`);
	}

	async updateUser(userId: string, data: AdminUserUpdateRequest): Promise<AdminUser> {
		return this.patch<AdminUser>(`/api/admin/users/${userId}`, data);
	}

	// ==========================================================================
	// Admin Endpoints - Whitelist
	// ==========================================================================

	async listWhitelist(): Promise<WhitelistResponse> {
		return this.fetch<WhitelistResponse>('/api/admin/beta-whitelist');
	}

	async addToWhitelist(data: { email: string; notes?: string }): Promise<WhitelistEntry> {
		return this.post<WhitelistEntry>('/api/admin/beta-whitelist', data);
	}

	async removeFromWhitelist(email: string): Promise<ControlResponse> {
		return this.delete<ControlResponse>(`/api/admin/beta-whitelist/${encodeURIComponent(email)}`);
	}

	// ==========================================================================
	// Admin Endpoints - Waitlist
	// ==========================================================================

	async listWaitlist(params?: { status?: string }): Promise<WaitlistResponse> {
		const endpoint = withQueryString('/api/admin/waitlist', params || {});
		return this.fetch<WaitlistResponse>(endpoint);
	}

	async approveWaitlistEntry(email: string): Promise<WaitlistApprovalResponse> {
		return this.post<WaitlistApprovalResponse>(`/api/admin/waitlist/${encodeURIComponent(email)}/approve`);
	}

	// ==========================================================================
	// Admin Endpoints - Extended KPIs
	// ==========================================================================

	async getExtendedKPIs(): Promise<ExtendedKPIsResponse> {
		return this.fetch<ExtendedKPIsResponse>('/api/admin/extended-kpis');
	}

	// ==========================================================================
	// Onboarding Endpoints
	// ==========================================================================

	async getOnboardingStatus(): Promise<OnboardingStatus> {
		return this.fetch<OnboardingStatus>('/api/v1/onboarding/status');
	}

	async completeOnboardingStep(step: OnboardingStep): Promise<{ status: string; step: string }> {
		return this.post<{ status: string; step: string }>('/api/v1/onboarding/step', { step });
	}

	async completeTour(firstMeetingId?: string): Promise<OnboardingStatus> {
		const body = firstMeetingId ? { first_meeting_id: firstMeetingId } : {};
		return this.post<OnboardingStatus>('/api/v1/onboarding/tour/complete', body);
	}

	async skipOnboarding(): Promise<OnboardingStatus> {
		return this.post<OnboardingStatus>('/api/v1/onboarding/skip');
	}

	async resetOnboarding(): Promise<OnboardingStatus> {
		return this.post<OnboardingStatus>('/api/v1/onboarding/reset');
	}

	// ==========================================================================
	// Context Enrichment Endpoints
	// ==========================================================================

	async enrichContext(url: string): Promise<EnrichmentResponse> {
		return this.post<EnrichmentResponse>('/api/v1/context/enrich', { website_url: url });
	}

	async checkRefreshNeeded(): Promise<RefreshCheckResponse> {
		return this.fetch<RefreshCheckResponse>('/api/v1/context/refresh-check');
	}

	async dismissRefresh(
		volatility?: 'volatile' | 'moderate' | 'stable' | 'action_affected'
	): Promise<{ status: string; dismissed_until: string }> {
		return this.post<{ status: string; dismissed_until: string }>(
			'/api/v1/context/dismiss-refresh',
			volatility ? { volatility } : undefined
		);
	}

	// ==========================================================================
	// Strategic Context Endpoints (Phase 3)
	// ==========================================================================

	async detectCompetitors(request?: CompetitorDetectRequest): Promise<CompetitorDetectResponse> {
		return this.post<CompetitorDetectResponse>('/api/v1/context/competitors/detect', request);
	}

	async refreshTrends(request?: TrendsRefreshRequest): Promise<TrendsRefreshResponse> {
		return this.post<TrendsRefreshResponse>('/api/v1/context/trends/refresh', request);
	}

	// ==========================================================================
	// Competitor Insight Endpoints (AI-powered analysis)
	// ==========================================================================

	/**
	 * Generate or retrieve cached insight for a competitor.
	 * @param name - Competitor name
	 * @param refresh - Force regeneration instead of using cache
	 */
	async generateCompetitorInsight(
		name: string,
		refresh = false
	): Promise<CompetitorInsightResponse> {
		const encodedName = encodeURIComponent(name);
		return this.post<CompetitorInsightResponse>(
			`/api/v1/context/competitors/${encodedName}/insights${refresh ? '?refresh=true' : ''}`
		);
	}

	/**
	 * List all cached competitor insights (tier-gated).
	 */
	async listCompetitorInsights(): Promise<CompetitorInsightsListResponse> {
		return this.fetch<CompetitorInsightsListResponse>('/api/v1/context/competitors/insights');
	}

	/**
	 * Delete a cached competitor insight.
	 * @param name - Competitor name
	 */
	async deleteCompetitorInsight(name: string): Promise<{ status: string }> {
		const encodedName = encodeURIComponent(name);
		return this.fetch<{ status: string }>(`/api/v1/context/competitors/${encodedName}/insights`, {
			method: 'DELETE'
		});
	}

	// ==========================================================================
	// Managed Competitors Endpoints (User-submitted competitor list)
	// ==========================================================================

	/**
	 * List user's managed competitors.
	 */
	async listManagedCompetitors(): Promise<ManagedCompetitorListResponse> {
		return this.fetch<ManagedCompetitorListResponse>('/api/v1/context/managed-competitors');
	}

	/**
	 * Add a new managed competitor.
	 * @param request - Competitor details
	 */
	async addManagedCompetitor(request: ManagedCompetitorCreate): Promise<ManagedCompetitorResponse> {
		return this.post<ManagedCompetitorResponse>('/api/v1/context/managed-competitors', request);
	}

	/**
	 * Update a managed competitor's url and/or notes.
	 * @param name - Competitor name
	 * @param request - Updated fields
	 */
	async updateManagedCompetitor(
		name: string,
		request: ManagedCompetitorUpdate
	): Promise<ManagedCompetitorResponse> {
		const encodedName = encodeURIComponent(name);
		return this.fetch<ManagedCompetitorResponse>(
			`/api/v1/context/managed-competitors/${encodedName}`,
			{
				method: 'PATCH',
				body: JSON.stringify(request)
			}
		);
	}

	/**
	 * Remove a managed competitor.
	 * @param name - Competitor name
	 */
	async removeManagedCompetitor(name: string): Promise<{ status: string }> {
		const encodedName = encodeURIComponent(name);
		return this.fetch<{ status: string }>(
			`/api/v1/context/managed-competitors/${encodedName}`,
			{
				method: 'DELETE'
			}
		);
	}

	// ==========================================================================
	// Trend Insight Endpoints
	// ==========================================================================

	/**
	 * Analyze a trend URL and generate structured insights.
	 * @param url - URL of the trend article to analyze
	 * @param refresh - Force regeneration instead of using cache
	 */
	async analyzeTrendUrl(
		url: string,
		refresh = false
	): Promise<TrendInsightResponse> {
		return this.post<TrendInsightResponse>(
			`/api/v1/context/trends/analyze${refresh ? '?refresh=true' : ''}`,
			{ url }
		);
	}

	/**
	 * List all cached trend insights.
	 */
	async listTrendInsights(): Promise<TrendInsightsListResponse> {
		return this.fetch<TrendInsightsListResponse>('/api/v1/context/trends/insights');
	}

	/**
	 * Delete a cached trend insight.
	 * @param url - URL of the trend to delete
	 */
	async deleteTrendInsight(url: string): Promise<{ status: string }> {
		// Encode URL as base64 for path parameter
		const urlHash = btoa(url).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
		return this.fetch<{ status: string }>(`/api/v1/context/trends/insights/${urlHash}`, {
			method: 'DELETE'
		});
	}

	// ==========================================================================
	// Competitor Watch Endpoints
	// ==========================================================================

	async getCompetitors(): Promise<CompetitorListResponse> {
		return this.fetch<CompetitorListResponse>('/api/v1/competitors');
	}

	async createCompetitor(request: CompetitorCreateRequest): Promise<CompetitorProfile> {
		return this.fetch<CompetitorProfile>('/api/v1/competitors', {
			method: 'POST',
			body: JSON.stringify(request)
		});
	}

	async updateCompetitor(id: string, profile: CompetitorProfile): Promise<CompetitorProfile> {
		return this.fetch<CompetitorProfile>(`/api/v1/competitors/${id}`, {
			method: 'PUT',
			body: JSON.stringify(profile)
		});
	}

	async deleteCompetitor(id: string): Promise<{ status: string }> {
		return this.fetch<{ status: string }>(`/api/v1/competitors/${id}`, {
			method: 'DELETE'
		});
	}

	async enrichCompetitor(id: string): Promise<CompetitorEnrichResponse> {
		return this.fetch<CompetitorEnrichResponse>(`/api/v1/competitors/${id}/enrich`, {
			method: 'POST'
		});
	}

	async enrichAllCompetitors(): Promise<CompetitorBulkEnrichResponse> {
		return this.fetch<CompetitorBulkEnrichResponse>('/api/v1/competitors/enrich-all', {
			method: 'POST'
		});
	}

	// ==========================================================================
	// Industry Insights Endpoints (Phase 4)
	// ==========================================================================

	async getIndustryInsights(insightType?: string): Promise<IndustryInsightsResponse> {
		const endpoint = withQueryString('/api/v1/industry-insights', { insight_type: insightType });
		return this.fetch<IndustryInsightsResponse>(endpoint);
	}

	async getIndustryInsightsByIndustry(industry: string, insightType?: string): Promise<IndustryInsightsResponse> {
		const endpoint = withQueryString(`/api/v1/industry-insights/${encodeURIComponent(industry)}`, { insight_type: insightType });
		return this.fetch<IndustryInsightsResponse>(endpoint);
	}

	// ==========================================================================
	// Business Metrics Endpoints
	// ==========================================================================

	async getMetrics(businessModel?: string): Promise<MetricsResponse> {
		const endpoint = withQueryString('/api/v1/business-metrics', { business_model: businessModel });
		return this.fetch<MetricsResponse>(endpoint);
	}

	async getMetricTemplates(businessModel?: string): Promise<MetricTemplate[]> {
		const endpoint = withQueryString('/api/v1/business-metrics/templates', { business_model: businessModel });
		return this.fetch<MetricTemplate[]>(endpoint);
	}

	async updateMetric(metricKey: string, value: number | null, source: MetricSource = 'manual'): Promise<UserMetric> {
		return this.put<UserMetric>(`/api/v1/business-metrics/${metricKey}`, { value, source });
	}

	async createMetric(request: CreateMetricRequest): Promise<UserMetric> {
		return this.post<UserMetric>('/api/v1/business-metrics', request);
	}

	async deleteMetric(metricKey: string): Promise<{ status: string }> {
		return this.delete<{ status: string }>(`/api/v1/business-metrics/${metricKey}`);
	}

	async initializeMetrics(businessModel?: string): Promise<UserMetric[]> {
		const endpoint = withQueryString('/api/v1/business-metrics/initialize', { business_model: businessModel });
		return this.post<UserMetric[]>(endpoint);
	}

	// ==========================================================================
	// Billing Endpoints
	// ==========================================================================

	async getBillingPlan(): Promise<PlanDetails> {
		return this.fetch<PlanDetails>('/api/v1/billing/plan');
	}

	async getBillingUsage(): Promise<UsageStats> {
		return this.fetch<UsageStats>('/api/v1/billing/usage');
	}

	async createBillingPortalSession(): Promise<BillingPortalResponse> {
		return this.post<BillingPortalResponse>('/api/v1/billing/portal');
	}

	async createCheckoutSession(priceId: string): Promise<CheckoutResponse> {
		return this.post<CheckoutResponse>('/api/v1/billing/checkout', { price_id: priceId });
	}

	// ==========================================================================
	// Workspace Billing Endpoints
	// ==========================================================================

	async getWorkspaceBilling(workspaceId: string): Promise<WorkspaceBillingInfoResponse> {
		return this.fetch<WorkspaceBillingInfoResponse>(`/api/v1/workspaces/${workspaceId}/billing`);
	}

	async createWorkspaceCheckout(
		workspaceId: string,
		priceId: string
	): Promise<CheckoutResponse> {
		return this.post<CheckoutResponse>(`/api/v1/workspaces/${workspaceId}/billing/checkout`, {
			price_id: priceId
		});
	}

	async createWorkspacePortalSession(workspaceId: string): Promise<WorkspacePortalResponse> {
		return this.post<WorkspacePortalResponse>(`/api/v1/workspaces/${workspaceId}/billing/portal`);
	}

	// ==========================================================================
	// Privacy & GDPR Endpoints
	// ==========================================================================

	async getEmailPreferences(): Promise<EmailPreferencesResponse> {
		return this.fetch<EmailPreferencesResponse>('/api/v1/user/email-preferences');
	}

	async updateEmailPreferences(preferences: EmailPreferences): Promise<EmailPreferencesResponse> {
		return this.patch<EmailPreferencesResponse>('/api/v1/user/email-preferences', preferences);
	}

	async exportUserData(): Promise<Blob> {
		const url = `${this.baseUrl}/api/v1/user/export`;

		// Track data export operation for observability
		const opId = operationTracker.startOp('api:GET:/api/v1/user/export');

		try {
			const response = await fetch(url, {
				method: 'GET',
				credentials: 'include'
			});
			if (!response.ok) {
				let error: ApiError;
				try {
					error = await response.json();
				} catch {
					error = { detail: response.statusText, status: response.status };
				}
				const apiError = new ApiClientError(error.detail || 'Unknown error', response.status, error);
				operationTracker.failOp(opId, apiError.message, { status: response.status });
				throw apiError;
			}
			operationTracker.endOp(opId, { status: response.status });
			return response.blob();
		} catch (error) {
			if (error instanceof ApiClientError) throw error;
			operationTracker.failOp(opId, error instanceof Error ? error.message : 'Export failed');
			throw error;
		}
	}

	async deleteUserAccount(): Promise<AccountDeletionResponse> {
		return this.delete<AccountDeletionResponse>('/api/v1/user/delete');
	}

	async getRetentionSetting(): Promise<RetentionSettingResponse> {
		return this.fetch<RetentionSettingResponse>('/api/v1/user/retention');
	}

	async updateRetentionSetting(days: number): Promise<RetentionSettingResponse> {
		return this.patch<RetentionSettingResponse>('/api/v1/user/retention', { days });
	}

	async getUserPreferences(): Promise<UserPreferencesResponse> {
		return this.fetch<UserPreferencesResponse>('/api/v1/user/preferences');
	}

	async updateUserPreferences(preferences: Partial<UserPreferences>): Promise<UserPreferencesResponse> {
		return this.patch<UserPreferencesResponse>('/api/v1/user/preferences', preferences);
	}

	// ==========================================================================
	// Cost Calculator Defaults
	// ==========================================================================

	async getCostCalculatorDefaults(): Promise<CostCalculatorDefaults> {
		return this.fetch<CostCalculatorDefaults>('/api/v1/user/cost-calculator-defaults');
	}

	async updateCostCalculatorDefaults(defaults: CostCalculatorDefaults): Promise<CostCalculatorDefaults> {
		return this.patch<CostCalculatorDefaults>('/api/v1/user/cost-calculator-defaults', defaults);
	}

	// ==========================================================================
	// Kanban Column Preferences
	// ==========================================================================

	async getKanbanColumns(): Promise<KanbanColumnsResponse> {
		return this.fetch<KanbanColumnsResponse>('/api/v1/user/preferences/kanban-columns');
	}

	async updateKanbanColumns(columns: KanbanColumn[]): Promise<KanbanColumnsResponse> {
		return this.patch<KanbanColumnsResponse>('/api/v1/user/preferences/kanban-columns', { columns });
	}

	// ==========================================================================
	// Project Endpoints
	// ==========================================================================

	async listProjects(params?: {
		status?: string;
		page?: number;
		per_page?: number;
	}): Promise<ProjectListResponse> {
		const endpoint = withQueryString('/api/v1/projects', params || {});
		return this.fetch<ProjectListResponse>(endpoint);
	}

	async createProject(request: ProjectCreateRequest): Promise<ProjectDetailResponse> {
		return this.post<ProjectDetailResponse>('/api/v1/projects', request);
	}

	async getProject(projectId: string): Promise<ProjectDetailResponse> {
		return this.fetch<ProjectDetailResponse>(`/api/v1/projects/${projectId}`);
	}

	async updateProject(projectId: string, request: ProjectUpdateRequest): Promise<ProjectDetailResponse> {
		return this.fetch<ProjectDetailResponse>(`/api/v1/projects/${projectId}`, {
			method: 'PATCH',
			body: JSON.stringify(request)
		});
	}

	async deleteProject(projectId: string): Promise<void> {
		return this.delete<void>(`/api/v1/projects/${projectId}`);
	}

	async updateProjectStatus(projectId: string, status: ProjectStatus): Promise<ProjectDetailResponse> {
		return this.fetch<ProjectDetailResponse>(`/api/v1/projects/${projectId}/status`, {
			method: 'PATCH',
			body: JSON.stringify({ status })
		});
	}

	async getProjectActions(
		projectId: string,
		params?: { status?: string; page?: number; per_page?: number }
	): Promise<ProjectActionsResponse> {
		const endpoint = withQueryString(`/api/v1/projects/${projectId}/actions`, params || {});
		return this.fetch<ProjectActionsResponse>(endpoint);
	}

	async assignActionToProject(projectId: string, actionId: string): Promise<void> {
		return this.post<void>(`/api/v1/projects/${projectId}/actions/${actionId}`);
	}

	async removeActionFromProject(projectId: string, actionId: string): Promise<void> {
		return this.delete<void>(`/api/v1/projects/${projectId}/actions/${actionId}`);
	}

	async getProjectGantt(projectId: string): Promise<GanttResponse> {
		return this.fetch<GanttResponse>(`/api/v1/projects/${projectId}/gantt`);
	}

	async linkSessionToProject(
		projectId: string,
		sessionId: string,
		relationship?: 'discusses' | 'created_from' | 'replanning'
	): Promise<{ project_id: string; session_id: string; relationship: string }> {
		return this.post<{ project_id: string; session_id: string; relationship: string }>(
			`/api/v1/projects/${projectId}/sessions`,
			{ session_id: sessionId, relationship: relationship || 'discusses' }
		);
	}

	async unlinkSessionFromProject(projectId: string, sessionId: string): Promise<void> {
		return this.delete<void>(`/api/v1/projects/${projectId}/sessions/${sessionId}`);
	}

	async getProjectSessions(projectId: string): Promise<ProjectSessionsResponse> {
		return this.fetch<ProjectSessionsResponse>(`/api/v1/projects/${projectId}/sessions`);
	}

	/**
	 * Create a meeting linked to a project
	 *
	 * Creates a new deliberation session pre-linked to the project.
	 */
	async createProjectMeeting(
		projectId: string,
		request?: { problem_statement?: string; include_project_context?: boolean }
	): Promise<SessionResponse> {
		return this.post<SessionResponse>(`/api/v1/projects/${projectId}/meetings`, request || {});
	}

	// ==========================================================================
	// Project Autogeneration Endpoints
	// ==========================================================================

	/**
	 * Get autogenerate suggestions from unassigned actions
	 *
	 * Analyzes unassigned actions and suggests project groupings.
	 */
	async getAutogenSuggestions(): Promise<AutogenSuggestionsResponse> {
		return this.fetch<AutogenSuggestionsResponse>('/api/v1/projects/autogenerate-suggestions');
	}

	/**
	 * Create projects from autogen suggestions
	 *
	 * Creates projects from selected suggestions and assigns actions.
	 */
	async createFromAutogenSuggestions(
		suggestions: AutogenSuggestion[],
		workspaceId?: string
	): Promise<AutogenCreateResponse> {
		return this.post<AutogenCreateResponse>('/api/v1/projects/autogenerate', {
			suggestions,
			workspace_id: workspaceId
		});
	}

	/**
	 * Get unassigned actions count
	 *
	 * Returns count of actions not assigned to any project.
	 */
	async getUnassignedCount(): Promise<UnassignedCountResponse> {
		return this.fetch<UnassignedCountResponse>('/api/v1/projects/unassigned-count');
	}

	/**
	 * Get context-based project suggestions
	 *
	 * Analyzes user's business context and suggests strategic projects.
	 */
	async getContextProjectSuggestions(): Promise<ContextSuggestionsResponse> {
		return this.fetch<ContextSuggestionsResponse>('/api/v1/projects/context-suggestions');
	}

	/**
	 * Create projects from context suggestions
	 *
	 * Creates projects from selected context-based suggestions.
	 */
	async createFromContextSuggestions(
		suggestions: ContextProjectSuggestion[],
		workspaceId?: string
	): Promise<AutogenCreateResponse> {
		return this.post<AutogenCreateResponse>('/api/v1/projects/context-suggestions', {
			suggestions,
			workspace_id: workspaceId
		});
	}

	// ==========================================================================
	// Action Dates Endpoints (Gantt drag-to-reschedule)
	// ==========================================================================

	/**
	 * Update action dates (for Gantt drag-to-reschedule)
	 */
	async updateActionDates(
		actionId: string,
		dates: ActionDatesUpdateRequest
	): Promise<ActionDatesResponse> {
		return this.patch<ActionDatesResponse>(`/api/v1/actions/${actionId}/dates`, dates);
	}

	// ==========================================================================
	// Action Updates Endpoints (Phase 5)
	// ==========================================================================

	/**
	 * Get activity timeline for an action
	 */
	async getActionUpdates(actionId: string, limit?: number): Promise<ActionUpdatesResponse> {
		const params = new URLSearchParams();
		if (limit) params.append('limit', limit.toString());
		const query = params.toString();
		return this.fetch<ActionUpdatesResponse>(
			`/api/v1/actions/${actionId}/updates${query ? `?${query}` : ''}`
		);
	}

	/**
	 * Add a progress update, blocker, or note to an action
	 */
	async addActionUpdate(
		actionId: string,
		update: ActionUpdateCreateRequest
	): Promise<ActionUpdateResponse> {
		return this.post<ActionUpdateResponse>(`/api/v1/actions/${actionId}/updates`, update);
	}

	/**
	 * Request AI replanning for a blocked action
	 * Creates a new deliberation session with context about the blocked action
	 */
	async requestReplan(
		actionId: string,
		additionalContext?: string
	): Promise<ReplanResponse> {
		const body: ReplanRequest = additionalContext ? { additional_context: additionalContext } : {};
		return this.post<ReplanResponse>(`/api/v1/actions/${actionId}/replan`, body);
	}

	// ==========================================================================
	// Action Dependency Endpoints
	// ==========================================================================

	/**
	 * Get dependencies for an action
	 */
	async getActionDependencies(actionId: string): Promise<DependencyListResponse> {
		return this.fetch<DependencyListResponse>(`/api/v1/actions/${actionId}/dependencies`);
	}

	/**
	 * Add a dependency to an action
	 */
	async addActionDependency(
		actionId: string,
		dependsOnId: string,
		dependencyType?: DependencyType,
		lagDays?: number
	): Promise<DependencyMutationResponse> {
		return this.post<DependencyMutationResponse>(`/api/v1/actions/${actionId}/dependencies`, {
			depends_on_action_id: dependsOnId,
			dependency_type: dependencyType,
			lag_days: lagDays
		});
	}

	/**
	 * Remove a dependency from an action
	 */
	async removeActionDependency(actionId: string, dependsOnId: string): Promise<void> {
		return this.delete<void>(`/api/v1/actions/${actionId}/dependencies/${dependsOnId}`);
	}

	// ==========================================================================
	// Tag Endpoints
	// ==========================================================================

	/**
	 * Get all tags for the current user
	 */
	async getTags(): Promise<TagListResponse> {
		return this.fetch<TagListResponse>('/api/v1/tags');
	}

	/**
	 * Create a new tag
	 */
	async createTag(request: TagCreateRequest): Promise<TagResponse> {
		return this.post<TagResponse>('/api/v1/tags', request);
	}

	/**
	 * Update an existing tag
	 */
	async updateTag(tagId: string, request: TagUpdateRequest): Promise<TagResponse> {
		return this.patch<TagResponse>(`/api/v1/tags/${tagId}`, request);
	}

	/**
	 * Delete a tag
	 */
	async deleteTag(tagId: string): Promise<{ message: string; tag_id: string }> {
		return this.delete<{ message: string; tag_id: string }>(`/api/v1/tags/${tagId}`);
	}

	/**
	 * Get tags for an action
	 */
	async getActionTags(actionId: string): Promise<TagResponse[]> {
		return this.fetch<TagResponse[]>(`/api/v1/actions/${actionId}/tags`);
	}

	/**
	 * Set tags for an action (replaces existing)
	 */
	async setActionTags(actionId: string, tagIds: string[]): Promise<TagResponse[]> {
		return this.put<TagResponse[]>(`/api/v1/actions/${actionId}/tags`, { tag_ids: tagIds });
	}

	// ==========================================================================
	// Dataset Query Endpoints (Data Analysis Platform)
	// ==========================================================================

	/**
	 * Execute a structured query against a dataset
	 */
	async executeDatasetQuery(datasetId: string, query: QuerySpec): Promise<QueryResultResponse> {
		return this.post<QueryResultResponse>(`/api/v1/datasets/${datasetId}/query`, query);
	}

	// ==========================================================================
	// Dataset Endpoints (Data Analysis Platform - EPIC 6)
	// ==========================================================================

	/**
	 * List user's datasets
	 */
	async getDatasets(params?: { limit?: number; offset?: number }): Promise<DatasetListResponse> {
		const endpoint = withQueryString('/api/v1/datasets', params || {});
		return this.fetch<DatasetListResponse>(endpoint);
	}

	/**
	 * Get a single dataset with profile
	 */
	async getDataset(datasetId: string): Promise<DatasetDetailResponse> {
		return this.fetch<DatasetDetailResponse>(`/api/v1/datasets/${datasetId}`);
	}

	/**
	 * Upload a CSV dataset
	 * Note: Uses FormData, not JSON
	 */
	async uploadDataset(file: File, name: string, description?: string): Promise<Dataset> {
		const formData = new FormData();
		formData.append('file', file);
		formData.append('name', name);
		if (description) {
			formData.append('description', description);
		}

		const url = `${this.baseUrl}/api/v1/datasets/upload`;
		const headers: Record<string, string> = {};
		const csrfToken = getCsrfToken();
		if (csrfToken) {
			headers['X-CSRF-Token'] = csrfToken;
		}

		// Track upload operation for observability
		const opId = operationTracker.startOp('api:POST:/api/v1/datasets/upload', {
			fileSize: file.size,
			fileName: file.name
		});

		try {
			const response = await fetch(url, {
				method: 'POST',
				credentials: 'include',
				headers,
				body: formData
				// Note: Don't set Content-Type header - browser sets it with boundary
			});

			if (!response.ok) {
				let error;
				try {
					error = await response.json();
				} catch {
					error = { detail: response.statusText };
				}
				const apiError = new ApiClientError(error.detail || 'Upload failed', response.status, error);
				operationTracker.failOp(opId, apiError.message, { status: response.status });
				throw apiError;
			}

			operationTracker.endOp(opId, { status: response.status });
			return response.json();
		} catch (error) {
			if (error instanceof ApiClientError) throw error;
			operationTracker.failOp(opId, error instanceof Error ? error.message : 'Upload failed');
			throw error;
		}
	}

	/**
	 * Import a Google Sheet as a dataset
	 */
	async importSheetsDataset(url: string, name?: string, description?: string): Promise<Dataset> {
		return this.post<Dataset>('/api/v1/datasets/import-sheets', {
			url,
			name,
			description
		});
	}

	/**
	 * Delete a dataset
	 */
	async deleteDataset(datasetId: string): Promise<void> {
		return this.delete<void>(`/api/v1/datasets/${datasetId}`);
	}

	/**
	 * Trigger profiling for a dataset
	 */
	async profileDataset(datasetId: string): Promise<{ profiles: DatasetProfile[]; summary: string }> {
		return this.post<{ profiles: DatasetProfile[]; summary: string }>(`/api/v1/datasets/${datasetId}/profile`);
	}

	/**
	 * Generate a chart from dataset
	 */
	async generateChart(datasetId: string, spec: ChartSpec): Promise<ChartResultResponse> {
		return this.post<ChartResultResponse>(`/api/v1/datasets/${datasetId}/chart`, spec);
	}

	/**
	 * Get analysis history for a dataset (charts/queries)
	 */
	async getDatasetAnalyses(datasetId: string, limit?: number): Promise<DatasetAnalysisListResponse> {
		const endpoint = withQueryString(`/api/v1/datasets/${datasetId}/analyses`, { limit });
		return this.fetch<DatasetAnalysisListResponse>(endpoint);
	}

	/**
	 * Ask a question about a dataset with SSE streaming
	 * Returns an object with connect() that yields SSE events
	 */
	askDataset(
		datasetId: string,
		question: string,
		conversationId?: string | null
	): {
		connect: () => AsyncGenerator<{ event: string; data: string }, void, unknown>;
		abort: () => void;
	} {
		const abortController = new AbortController();
		const url = `${this.baseUrl}/api/v1/datasets/${datasetId}/ask`;

		const connect = async function* () {
			const headers: Record<string, string> = {
				'Content-Type': 'application/json',
				Accept: 'text/event-stream'
			};
			const csrfToken = getCsrfToken();
			if (csrfToken) {
				headers['X-CSRF-Token'] = csrfToken;
			}

			const response = await fetch(url, {
				method: 'POST',
				headers,
				credentials: 'include',
				signal: abortController.signal,
				body: JSON.stringify({
					question,
					conversation_id: conversationId
				})
			});

			if (!response.ok) {
				const error = await response.text();
				throw new Error(`Ask failed: ${response.status} - ${error}`);
			}

			const reader = response.body?.getReader();
			if (!reader) {
				throw new Error('No response body');
			}

			const decoder = new TextDecoder();
			let buffer = '';

			try {
				while (true) {
					const { done, value } = await reader.read();
					if (done) break;

					buffer += decoder.decode(value, { stream: true });
					const lines = buffer.split('\n');
					buffer = lines.pop() || '';

					let currentEvent = 'message';
					for (const line of lines) {
						if (line.startsWith('event:')) {
							currentEvent = line.slice(6).trim();
						} else if (line.startsWith('data:')) {
							const data = line.slice(5).trim();
							yield { event: currentEvent, data };
							currentEvent = 'message';
						}
					}
				}
			} finally {
				reader.releaseLock();
			}
		};

		return {
			connect,
			abort: () => abortController.abort()
		};
	}

	/**
	 * Get conversations for a dataset
	 */
	async getConversations(datasetId: string): Promise<ConversationListResponse> {
		return this.fetch<ConversationListResponse>(`/api/v1/datasets/${datasetId}/conversations`);
	}

	/**
	 * Get a specific conversation
	 */
	async getConversation(datasetId: string, conversationId: string): Promise<ConversationResponse> {
		return this.fetch<ConversationResponse>(
			`/api/v1/datasets/${datasetId}/conversations/${conversationId}`
		);
	}

	/**
	 * Delete a conversation
	 */
	async deleteConversation(datasetId: string, conversationId: string): Promise<void> {
		await this.delete<void>(`/api/v1/datasets/${datasetId}/conversations/${conversationId}`);
	}

	// ============================================================================
	// Analysis Methods
	// ============================================================================

	/**
	 * Ask data analysis question using SSE streaming
	 * Routes to dataset Q&A if datasetId provided, otherwise general guidance
	 * Returns an object with connect() that yields SSE events
	 */
	askAnalysis(
		question: string,
		conversationId?: string | null,
		datasetId?: string | null
	): {
		connect: () => AsyncGenerator<{ event: string; data: string }, void, unknown>;
		abort: () => void;
	} {
		const abortController = new AbortController();
		const url = `${this.baseUrl}/api/v1/analysis/ask`;

		const connect = async function* () {
			const headers: Record<string, string> = {
				'Content-Type': 'application/json',
				Accept: 'text/event-stream'
			};
			const csrfToken = getCsrfToken();
			if (csrfToken) {
				headers['X-CSRF-Token'] = csrfToken;
			}

			const response = await fetch(url, {
				method: 'POST',
				headers,
				credentials: 'include',
				signal: abortController.signal,
				body: JSON.stringify({
					question,
					conversation_id: conversationId,
					dataset_id: datasetId
				})
			});

			if (!response.ok) {
				const error = await response.text();
				throw new Error(`Analysis failed: ${response.status} - ${error}`);
			}

			const reader = response.body?.getReader();
			if (!reader) {
				throw new Error('No response body');
			}

			const decoder = new TextDecoder();
			let buffer = '';

			try {
				while (true) {
					const { done, value } = await reader.read();
					if (done) break;

					buffer += decoder.decode(value, { stream: true });
					const lines = buffer.split('\n');
					buffer = lines.pop() || '';

					let currentEvent = 'message';
					for (const line of lines) {
						if (line.startsWith('event:')) {
							currentEvent = line.slice(6).trim();
						} else if (line.startsWith('data:')) {
							const data = line.slice(5).trim();
							yield { event: currentEvent, data };
							currentEvent = 'message';
						}
					}
				}
			} finally {
				reader.releaseLock();
			}
		};

		return {
			connect,
			abort: () => abortController.abort()
		};
	}

	// ============================================================================
	// Mentor Chat Methods
	// ============================================================================

	/**
	 * Chat with mentor using SSE streaming
	 * Returns an object with connect() that yields SSE events
	 */
	chatWithMentor(
		message: string,
		conversationId?: string | null,
		persona?: string | null,
		honeypot?: import('./types').HoneypotFields
	): {
		connect: () => AsyncGenerator<{ event: string; data: string }, void, unknown>;
		abort: () => void;
	} {
		const abortController = new AbortController();
		const url = `${this.baseUrl}/api/v1/mentor/chat`;

		const connect = async function* () {
			const headers: Record<string, string> = {
				'Content-Type': 'application/json',
				Accept: 'text/event-stream'
			};
			const csrfToken = getCsrfToken();
			if (csrfToken) {
				headers['X-CSRF-Token'] = csrfToken;
			}

			const response = await fetch(url, {
				method: 'POST',
				headers,
				credentials: 'include',
				signal: abortController.signal,
				body: JSON.stringify({
					message,
					conversation_id: conversationId,
					persona,
					...honeypot
				})
			});

			if (!response.ok) {
				const error = await response.text();
				throw new Error(`Mentor chat failed: ${response.status} - ${error}`);
			}

			const reader = response.body?.getReader();
			if (!reader) {
				throw new Error('No response body');
			}

			const decoder = new TextDecoder();
			let buffer = '';

			try {
				while (true) {
					const { done, value } = await reader.read();
					if (done) break;

					buffer += decoder.decode(value, { stream: true });
					const lines = buffer.split('\n');
					buffer = lines.pop() || '';

					let currentEvent = 'message';
					for (const line of lines) {
						if (line.startsWith('event:')) {
							currentEvent = line.slice(6).trim();
						} else if (line.startsWith('data:')) {
							const data = line.slice(5).trim();
							yield { event: currentEvent, data };
							currentEvent = 'message';
						}
					}
				}
			} finally {
				reader.releaseLock();
			}
		};

		return {
			connect,
			abort: () => abortController.abort()
		};
	}

	/**
	 * Get mentor conversations for current user
	 */
	async getMentorConversations(limit = 20): Promise<MentorConversationListResponse> {
		return this.fetch<MentorConversationListResponse>(`/api/v1/mentor/conversations?limit=${limit}`);
	}

	/**
	 * Get a specific mentor conversation
	 */
	async getMentorConversation(conversationId: string): Promise<MentorConversationDetailResponse> {
		return this.fetch<MentorConversationDetailResponse>(
			`/api/v1/mentor/conversations/${conversationId}`
		);
	}

	/**
	 * Delete a mentor conversation
	 */
	async deleteMentorConversation(conversationId: string): Promise<void> {
		await this.delete<void>(`/api/v1/mentor/conversations/${conversationId}`);
	}

	/**
	 * Update a mentor conversation label
	 */
	async updateMentorConversationLabel(
		conversationId: string,
		label: string
	): Promise<MentorConversationResponse> {
		return this.patch<MentorConversationResponse>(
			`/api/v1/mentor/conversations/${conversationId}`,
			{ label }
		);
	}

	/**
	 * Get available mentor personas for manual selection
	 */
	async getMentorPersonas(): Promise<MentorPersonaListResponse> {
		return this.fetch<MentorPersonaListResponse>('/api/v1/mentor/personas');
	}

	/**
	 * Search for mentionable entities (@meeting, @action, @dataset, @chat)
	 * Used by autocomplete when user types @ in mentor chat
	 */
	async searchMentions(
		type: 'meeting' | 'action' | 'dataset' | 'chat',
		query: string = '',
		limit: number = 10,
		conversationId?: string
	): Promise<MentionSearchResponse> {
		const params = new URLSearchParams({ type, q: query, limit: String(limit) });
		if (conversationId) {
			params.set('conversation_id', conversationId);
		}
		return this.fetch<MentionSearchResponse>(`/api/v1/mentor/mentions/search?${params}`);
	}

	// ============================================================================
	// Google Sheets Connection Methods
	// ============================================================================

	/**
	 * Get Google Sheets connection status for current user
	 */
	async getSheetsConnectionStatus(): Promise<{ connected: boolean; scopes: string | null }> {
		return this.fetch<{ connected: boolean; scopes: string | null }>('/api/v1/auth/google/sheets/status');
	}

	/**
	 * Get the URL to initiate Google Sheets OAuth flow
	 * User should be redirected to this URL to connect their Google account
	 */
	getSheetsConnectUrl(): string {
		return `${this.baseUrl}/api/v1/auth/google/sheets/connect`;
	}

	/**
	 * Disconnect Google Sheets (revoke access)
	 */
	async disconnectSheets(): Promise<{ success: boolean }> {
		return this.delete<{ success: boolean }>('/api/v1/auth/google/sheets/disconnect');
	}

	// ==========================================================================
	// Session Export & Sharing Endpoints
	// ==========================================================================

	/**
	 * Export session as JSON or Markdown file.
	 * Returns a Blob for download.
	 */
	async exportSession(sessionId: string, format: 'json' | 'markdown' = 'json'): Promise<Blob> {
		const url = `${this.baseUrl}/api/v1/sessions/${sessionId}/export?format=${format}`;

		// Track export operation for observability
		const opId = operationTracker.startOp('api:GET:/api/v1/sessions/export', {
			sessionId,
			format
		});

		try {
			const response = await fetch(url, {
				method: 'GET',
				credentials: 'include'
			});

			if (!response.ok) {
				let error;
				try {
					error = await response.json();
				} catch {
					error = { detail: response.statusText };
				}
				const apiError = new ApiClientError(error.detail || 'Export failed', response.status, error);
				operationTracker.failOp(opId, apiError.message, { status: response.status });
				throw apiError;
			}

			operationTracker.endOp(opId, { status: response.status });
			return response.blob();
		} catch (error) {
			if (error instanceof ApiClientError) throw error;
			operationTracker.failOp(opId, error instanceof Error ? error.message : 'Export failed');
			throw error;
		}
	}

	/**
	 * Create a shareable link for a session.
	 */
	async createShare(
		sessionId: string,
		ttlDays: number = 7
	): Promise<{ token: string; share_url: string; expires_at: string }> {
		return this.post<{ token: string; share_url: string; expires_at: string }>(
			`/api/v1/sessions/${sessionId}/share?ttl_days=${ttlDays}`
		);
	}

	/**
	 * List active shares for a session.
	 */
	async listShares(sessionId: string): Promise<{
		session_id: string;
		shares: Array<{
			token: string;
			expires_at: string;
			created_at: string;
			is_active: boolean;
		}>;
		total: number;
	}> {
		return this.fetch<{
			session_id: string;
			shares: Array<{
				token: string;
				expires_at: string;
				created_at: string;
				is_active: boolean;
			}>;
			total: number;
		}>(`/api/v1/sessions/${sessionId}/share`);
	}

	/**
	 * Revoke/delete a share link.
	 */
	async revokeShare(sessionId: string, token: string): Promise<void> {
		return this.delete<void>(`/api/v1/sessions/${sessionId}/share/${token}`);
	}

	/**
	 * Get shared session data (public, no auth required).
	 */
	async getPublicShare(token: string): Promise<{
		session_id: string;
		title: string;
		created_at: string;
		owner_name: string;
		expires_at: string;
		is_active: boolean;
		synthesis: unknown;
		conclusion: unknown;
		problem_context: Record<string, unknown>;
	}> {
		return this.fetch<{
			session_id: string;
			title: string;
			created_at: string;
			owner_name: string;
			expires_at: string;
			is_active: boolean;
			synthesis: unknown;
			conclusion: unknown;
			problem_context: Record<string, unknown>;
		}>(`/api/v1/share/${token}`);
	}

	// =========================================================================
	// Workspace Invitation Methods
	// =========================================================================

	/**
	 * Send a workspace invitation
	 */
	async sendWorkspaceInvitation(
		workspaceId: string,
		email: string,
		role: 'admin' | 'member' = 'member'
	): Promise<InvitationResponse> {
		return this.fetch<InvitationResponse>(`/api/v1/workspaces/${workspaceId}/invitations`, {
			method: 'POST',
			body: JSON.stringify({ email, role })
		});
	}

	/**
	 * List pending invitations for a workspace
	 */
	async listWorkspaceInvitations(workspaceId: string): Promise<InvitationListResponse> {
		return this.fetch<InvitationListResponse>(`/api/v1/workspaces/${workspaceId}/invitations`);
	}

	/**
	 * Revoke a workspace invitation
	 */
	async revokeInvitation(workspaceId: string, invitationId: string): Promise<void> {
		await this.fetch<void>(`/api/v1/workspaces/${workspaceId}/invitations/${invitationId}`, {
			method: 'DELETE'
		});
	}

	/**
	 * Get invitation details by token (public)
	 */
	async getInvitation(token: string): Promise<InvitationResponse> {
		return this.fetch<InvitationResponse>(`/api/v1/invitations/${token}`);
	}

	/**
	 * Accept a workspace invitation
	 */
	async acceptInvitation(token: string): Promise<InvitationResponse> {
		return this.fetch<InvitationResponse>('/api/v1/invitations/accept', {
			method: 'POST',
			body: JSON.stringify({ token })
		});
	}

	/**
	 * Decline a workspace invitation
	 */
	async declineInvitation(token: string): Promise<void> {
		await this.fetch<void>('/api/v1/invitations/decline', {
			method: 'POST',
			body: JSON.stringify({ token })
		});
	}

	/**
	 * Get pending invitations for current user
	 */
	async getPendingInvitations(): Promise<InvitationListResponse> {
		return this.fetch<InvitationListResponse>('/api/v1/invitations/pending');
	}

	// =========================================================================
	// Workspace Methods
	// =========================================================================

	/**
	 * List all workspaces the current user is a member of
	 */
	async listWorkspaces(): Promise<WorkspaceListResponse> {
		return this.fetch<WorkspaceListResponse>('/api/v1/workspaces');
	}

	/**
	 * Get a single workspace by ID
	 */
	async getWorkspace(workspaceId: string): Promise<WorkspaceResponse> {
		return this.fetch<WorkspaceResponse>(`/api/v1/workspaces/${workspaceId}`);
	}

	/**
	 * Create a new workspace
	 */
	async createWorkspace(name: string, slug?: string): Promise<WorkspaceResponse> {
		return this.post<WorkspaceResponse>('/api/v1/workspaces', { name, slug });
	}

	/**
	 * Update a workspace (admin/owner only)
	 */
	async updateWorkspace(
		workspaceId: string,
		updates: { name?: string; slug?: string }
	): Promise<WorkspaceResponse> {
		return this.patch<WorkspaceResponse>(`/api/v1/workspaces/${workspaceId}`, updates);
	}

	/**
	 * Delete a workspace (owner only)
	 */
	async deleteWorkspace(workspaceId: string): Promise<void> {
		return this.delete<void>(`/api/v1/workspaces/${workspaceId}`);
	}

	/**
	 * Leave a workspace (remove self as member)
	 */
	async leaveWorkspace(workspaceId: string, userId: string): Promise<void> {
		return this.delete<void>(`/api/v1/workspaces/${workspaceId}/members/${userId}`);
	}

	// =========================================================================
	// Workspace Join Request Methods
	// =========================================================================

	/**
	 * Submit a request to join a workspace
	 * Only works for workspaces with request_to_join discoverability
	 */
	async submitJoinRequest(workspaceId: string, message?: string): Promise<JoinRequestResponse> {
		return this.post<JoinRequestResponse>(`/api/v1/workspaces/${workspaceId}/join-request`, {
			message
		});
	}

	/**
	 * List pending join requests for a workspace (admin/owner only)
	 */
	async listJoinRequests(workspaceId: string): Promise<JoinRequestListResponse> {
		return this.fetch<JoinRequestListResponse>(
			`/api/v1/workspaces/${workspaceId}/join-requests`
		);
	}

	/**
	 * Approve a join request (admin/owner only)
	 */
	async approveJoinRequest(
		workspaceId: string,
		requestId: string
	): Promise<JoinRequestResponse> {
		return this.post<JoinRequestResponse>(
			`/api/v1/workspaces/${workspaceId}/join-requests/${requestId}/approve`
		);
	}

	/**
	 * Reject a join request (admin/owner only)
	 */
	async rejectJoinRequest(
		workspaceId: string,
		requestId: string,
		reason?: string
	): Promise<JoinRequestResponse> {
		return this.post<JoinRequestResponse>(
			`/api/v1/workspaces/${workspaceId}/join-requests/${requestId}/reject`,
			{ reason }
		);
	}

	/**
	 * Update workspace settings (admin/owner only)
	 */
	async updateWorkspaceSettings(
		workspaceId: string,
		settings: WorkspaceSettingsUpdate
	): Promise<WorkspaceResponse> {
		return this.patch<WorkspaceResponse>(
			`/api/v1/workspaces/${workspaceId}/settings`,
			settings
		);
	}

	// =========================================================================
	// Workspace Role Management Methods
	// =========================================================================

	/**
	 * Transfer workspace ownership to another member (owner only)
	 * The current owner will become an admin after the transfer
	 */
	async transferWorkspaceOwnership(
		workspaceId: string,
		newOwnerId: string
	): Promise<WorkspaceResponse> {
		return this.post<WorkspaceResponse>(
			`/api/v1/workspaces/${workspaceId}/transfer-ownership`,
			{ new_owner_id: newOwnerId, confirm: true }
		);
	}

	/**
	 * Promote a member to admin role (owner only)
	 */
	async promoteMember(
		workspaceId: string,
		userId: string
	): Promise<WorkspaceMemberResponse> {
		return this.post<WorkspaceMemberResponse>(
			`/api/v1/workspaces/${workspaceId}/members/${userId}/promote`
		);
	}

	/**
	 * Demote an admin to member role (owner only)
	 */
	async demoteMember(
		workspaceId: string,
		userId: string
	): Promise<WorkspaceMemberResponse> {
		return this.post<WorkspaceMemberResponse>(
			`/api/v1/workspaces/${workspaceId}/members/${userId}/demote`
		);
	}

	/**
	 * Get role change history for a workspace (admin/owner only)
	 */
	async getRoleHistory(
		workspaceId: string,
		limit: number = 50
	): Promise<RoleHistoryResponse> {
		const endpoint = withQueryString(
			`/api/v1/workspaces/${workspaceId}/role-history`,
			{ limit }
		);
		return this.fetch<RoleHistoryResponse>(endpoint);
	}

	// ============================================================================
	// Industry Benchmarks (additional methods)
	// ============================================================================

	/**
	 * Get industry insights with filtering options
	 * Returns benchmarks, trends, and best practices (tier-limited)
	 */
	async getIndustryBenchmarks(options?: {
		insightType?: 'trend' | 'benchmark' | 'best_practice';
		category?: 'growth' | 'retention' | 'efficiency' | 'engagement';
	}): Promise<IndustryInsightsResponse> {
		const endpoint = withQueryString('/api/v1/industry-insights', {
			insight_type: options?.insightType,
			category: options?.category
		});
		return this.fetch<IndustryInsightsResponse>(endpoint);
	}

	/**
	 * Compare user's metrics against industry benchmarks
	 * Returns percentile rankings for each metric (tier-limited)
	 */
	async compareBenchmarks(): Promise<BenchmarkComparisonResponse> {
		return this.fetch<BenchmarkComparisonResponse>('/api/v1/industry-insights/compare');
	}

	/**
	 * Check for stale benchmark values needing monthly check-in
	 * Returns benchmarks not updated in 30+ days
	 */
	async getStaleBenchmarks(): Promise<StaleBenchmarksResponse> {
		return this.fetch<StaleBenchmarksResponse>('/api/v1/benchmarks/stale');
	}

	// ============================================================================
	// Usage & Tier Limits
	// ============================================================================

	/**
	 * Get current usage across all metrics (meetings, datasets, mentor chats)
	 */
	async getUsage(): Promise<UsageResponse> {
		return this.fetch<UsageResponse>('/api/v1/user/usage');
	}

	/**
	 * Get tier limits and features for current user
	 */
	async getTierInfo(): Promise<TierLimitsResponse> {
		return this.fetch<TierLimitsResponse>('/api/v1/user/tier-info');
	}

	// ============================================================================
	// Feedback
	// ============================================================================

	/**
	 * Submit feedback (feature request or problem report)
	 * Rate limited to 5 submissions per hour
	 */
	async submitFeedback(data: FeedbackCreateRequest): Promise<FeedbackResponse> {
		return this.post<FeedbackResponse>('/api/v1/feedback', data);
	}

	// ============================================================================
	// Calendar Integration
	// ============================================================================

	/**
	 * Get Google Calendar connection status
	 */
	async getCalendarStatus(): Promise<CalendarStatusResponse> {
		return this.fetch<CalendarStatusResponse>('/api/v1/integrations/calendar/status');
	}

	/**
	 * Disconnect Google Calendar integration
	 */
	async disconnectCalendar(): Promise<{ success: boolean }> {
		return this.delete<{ success: boolean }>('/api/v1/integrations/calendar/disconnect');
	}

	/**
	 * Toggle calendar sync on/off without disconnecting
	 */
	async toggleCalendarSync(enabled: boolean): Promise<CalendarStatusResponse> {
		return this.patch<CalendarStatusResponse>('/api/v1/integrations/calendar/status', {
			enabled
		});
	}

	// ============================================================================
	// Session-Project Linking
	// ============================================================================

	/**
	 * Get projects linked to a session
	 */
	async getSessionProjects(sessionId: string): Promise<SessionProjectsResponse> {
		return this.fetch<SessionProjectsResponse>(`/api/v1/sessions/${sessionId}/projects`);
	}

	/**
	 * Get projects available for linking (same workspace)
	 */
	async getAvailableProjects(sessionId: string): Promise<AvailableProjectsResponse> {
		return this.fetch<AvailableProjectsResponse>(`/api/v1/sessions/${sessionId}/available-projects`);
	}

	/**
	 * Link projects to a session
	 */
	async linkProjectsToSession(
		sessionId: string,
		data: SessionProjectLinkRequest
	): Promise<{ session_id: string; linked_count: number; project_ids: string[] }> {
		return this.post<{ session_id: string; linked_count: number; project_ids: string[] }>(
			`/api/v1/sessions/${sessionId}/projects`,
			data
		);
	}

	/**
	 * Unlink a project from a session
	 */
	async unlinkProjectFromSession(sessionId: string, projectId: string): Promise<void> {
		return this.delete<void>(`/api/v1/sessions/${sessionId}/projects/${projectId}`);
	}

	/**
	 * Get project suggestions from a completed meeting
	 */
	async getProjectSuggestions(
		sessionId: string,
		minConfidence: number = 0.6
	): Promise<ProjectSuggestionsResponse> {
		return this.fetch<ProjectSuggestionsResponse>(
			`/api/v1/sessions/${sessionId}/suggest-projects?min_confidence=${minConfidence}`
		);
	}

	/**
	 * Create a project from a suggestion
	 */
	async createSuggestedProject(
		sessionId: string,
		suggestion: { name: string; description: string; action_ids: string[] }
	): Promise<CreatedProjectResponse> {
		return this.post<CreatedProjectResponse>(
			`/api/v1/sessions/${sessionId}/create-suggested-project`,
			suggestion
		);
	}

	// =========================================================================
	// Public Blog (no auth required)
	// =========================================================================

	/**
	 * List published blog posts (public, no auth)
	 */
	async listPublishedBlogPosts(params?: {
		limit?: number;
		offset?: number;
	}): Promise<PublicBlogPostListResponse> {
		const searchParams = new URLSearchParams();
		if (params?.limit) searchParams.set('limit', String(params.limit));
		if (params?.offset) searchParams.set('offset', String(params.offset));

		const query = searchParams.toString();
		return this.fetch<PublicBlogPostListResponse>(`/api/v1/blog/posts${query ? `?${query}` : ''}`);
	}

	/**
	 * Get a published blog post by slug (public, no auth)
	 */
	async getBlogPostBySlug(slug: string): Promise<PublicBlogPost> {
		return this.fetch<PublicBlogPost>(`/api/v1/blog/posts/${slug}`);
	}

	// =========================================================================
	// Meeting Templates (public read, no auth required for list/get)
	// =========================================================================

	/**
	 * List active meeting templates for the template gallery
	 */
	async listMeetingTemplates(params?: {
		category?: string;
	}): Promise<MeetingTemplateListResponse> {
		const searchParams = new URLSearchParams();
		if (params?.category) searchParams.set('category', params.category);

		const query = searchParams.toString();
		return this.fetch<MeetingTemplateListResponse>(
			`/api/v1/templates${query ? `?${query}` : ''}`
		);
	}

	/**
	 * Get a meeting template by slug
	 */
	async getMeetingTemplateBySlug(slug: string): Promise<MeetingTemplate> {
		return this.fetch<MeetingTemplate>(`/api/v1/templates/${slug}`);
	}
}

/**
 * Singleton API client instance
 */
export const apiClient = new ApiClient();
