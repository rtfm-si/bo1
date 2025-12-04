/**
 * API Client - Board of One Backend API Client
 *
 * Handles all HTTP communication with the FastAPI backend.
 * Includes error handling, type safety, and environment-based configuration.
 */

import { env } from '$env/dynamic/public';
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
	// Replanning types (Phase 7)
	ReplanRequest,
	ReplanResponse,
	// Tag types
	TagCreateRequest,
	TagUpdateRequest,
	TagResponse,
	TagListResponse,
	ActionTagsUpdateRequest,
	// Global Gantt types
	GlobalGanttResponse
} from './types';

// ============================================================================
// Onboarding Types
// ============================================================================

export type OnboardingStep = 'business_context' | 'first_meeting' | 'expert_panel' | 'results';

export interface OnboardingStatus {
	is_new_user: boolean;
	onboarding_completed: boolean;
	completed_steps: OnboardingStep[];
	current_step: OnboardingStep | null;
	tours_completed: string[];
	skipped: boolean;
	skipped_at: string | null;
	started_at: string | null;
	completed_at: string | null;
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

export interface RefreshCheckResponse {
	needs_refresh: boolean;
	last_updated: string | null;
	days_since_update: number | null;
	missing_fields: string[];
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

export interface IndustryInsight {
	id: string;
	industry: string;
	insight_type: 'trend' | 'benchmark' | 'competitor' | 'best_practice';
	content: Record<string, unknown>;
	source_count: number;
	confidence: number;
	expires_at: string | null;
	created_at: string;
}

export interface IndustryInsightsResponse {
	industry: string;
	insights: IndustryInsight[];
	has_benchmarks: boolean;
}

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
	 */
	private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
		const url = `${this.baseUrl}${endpoint}`;
		const headers = mergeHeaders({ 'Content-Type': 'application/json' }, options?.headers);

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
				throw new ApiClientError(error.detail || 'Unknown error', response.status, error);
			}

			if (response.status === 204) {
				return {} as T;
			}

			return await response.json();
		} catch (error) {
			if (error instanceof ApiClientError) throw error;
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

	async submitClarification(sessionId: string, answer: string): Promise<ControlResponse> {
		return this.post<ControlResponse>(`/api/v1/sessions/${sessionId}/clarify`, { answer });
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

	async getGlobalGantt(params?: {
		status_filter?: ActionStatus;
		project_id?: string;
		session_id?: string;
		tag_ids?: string;
	}): Promise<GlobalGanttResponse> {
		const endpoint = withQueryString('/api/v1/actions/gantt', params || {});
		return this.fetch<GlobalGanttResponse>(endpoint);
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
	// Onboarding Endpoints
	// ==========================================================================

	async getOnboardingStatus(): Promise<OnboardingStatus> {
		return this.fetch<OnboardingStatus>('/api/v1/onboarding/status');
	}

	async completeOnboardingStep(step: OnboardingStep): Promise<{ status: string; step: string }> {
		return this.post<{ status: string; step: string }>('/api/v1/onboarding/step', { step });
	}

	async completeTour(tourName: string): Promise<{ status: string; tour: string }> {
		return this.post<{ status: string; tour: string }>('/api/v1/onboarding/tour/complete', { tour_name: tourName });
	}

	async skipOnboarding(): Promise<{ status: string }> {
		return this.post<{ status: string }>('/api/v1/onboarding/skip');
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

	async dismissRefresh(): Promise<{ status: string }> {
		return this.post<{ status: string }>('/api/v1/context/dismiss-refresh');
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
}

/**
 * Singleton API client instance
 */
export const apiClient = new ApiClient();
