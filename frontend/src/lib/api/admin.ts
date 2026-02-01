/**
 * Admin API Client - Admin-only endpoints for session management and cost analytics
 */
import { env } from '$env/dynamic/public';
import { ApiClientError } from './client';

// CSRF token helper (same as client.ts)
function getCsrfToken(): string | null {
	if (typeof document === 'undefined') return null;
	const match = document.cookie.match(/(?:^|; )csrf_token=([^;]*)/);
	return match ? decodeURIComponent(match[1]) : null;
}

// =============================================================================
// Types
// =============================================================================

export interface ActiveSessionInfo {
	session_id: string;
	user_id: string;
	status: string;
	phase: string | null;
	started_at: string;
	duration_seconds: number;
	cost: number | null;
}

export interface ActiveSessionsResponse {
	active_count: number;
	sessions: ActiveSessionInfo[];
	longest_running: ActiveSessionInfo[];
	most_expensive: ActiveSessionInfo[];
}

export interface FullSessionResponse {
	session_id: string;
	metadata: Record<string, unknown>;
	state: Record<string, unknown> | null;
	is_active: boolean;
}

export interface ControlResponse {
	session_id: string;
	action: string;
	status: string;
	message: string;
}

export interface KillAllResponse {
	killed_count: number;
	message: string;
}

export interface CostSummaryResponse {
	today: number;
	this_week: number;
	this_month: number;
	all_time: number;
	session_count_today: number;
	session_count_week: number;
	session_count_month: number;
	session_count_total: number;
}

export interface UserCostItem {
	user_id: string;
	email: string | null;
	total_cost: number;
	session_count: number;
}

export interface UserCostsResponse {
	users: UserCostItem[];
	total: number;
	limit: number;
	offset: number;
}

export interface DailyCostItem {
	date: string;
	total_cost: number;
	session_count: number;
}

export interface DailyCostsResponse {
	days: DailyCostItem[];
	start_date: string;
	end_date: string;
}

export interface SessionKill {
	id: number;
	session_id: string | null;
	killed_by: string;
	reason: string;
	cost_at_kill: number | null;
	created_at: string;
}

export interface SessionKillsResponse {
	kills: SessionKill[];
	total: number;
	limit: number;
	offset: number;
}

// =============================================================================
// User Metrics Types
// =============================================================================

export interface DailyCount {
	date: string;
	count: number;
}

export interface UserMetricsResponse {
	total_users: number;
	new_users_today: number;
	new_users_7d: number;
	new_users_30d: number;
	dau: number;
	wau: number;
	mau: number;
	daily_signups: DailyCount[];
	daily_active: DailyCount[];
}

export interface UsageMetricsResponse {
	total_meetings: number;
	meetings_today: number;
	meetings_7d: number;
	meetings_30d: number;
	total_actions: number;
	actions_created_7d: number;
	daily_meetings: DailyCount[];
	daily_actions: DailyCount[];
	// Extended KPIs
	mentor_sessions_count: number;
	data_analyses_count: number;
	projects_count: number;
	actions_started_count: number;
	actions_completed_count: number;
	actions_cancelled_count: number;
}

export interface FunnelStage {
	name: string;
	count: number;
	conversion_rate: number;
}

export interface CohortMetrics {
	period_days: number;
	signups: number;
	context_completed: number;
	first_meeting: number;
	meeting_completed: number;
}

export interface OnboardingFunnelResponse {
	total_signups: number;
	context_completed: number;
	first_meeting: number;
	meeting_completed: number;
	signup_to_context: number;
	context_to_meeting: number;
	meeting_to_complete: number;
	overall_conversion: number;
	stages: FunnelStage[];
	cohort_7d: CohortMetrics;
	cohort_30d: CohortMetrics;
}

// =============================================================================
// Alert Types
// =============================================================================

export interface AlertHistoryItem {
	id: number;
	alert_type: string;
	severity: string;
	title: string;
	message: string;
	metadata: Record<string, unknown> | null;
	delivered: boolean;
	created_at: string;
}

export interface AlertHistoryResponse {
	total: number;
	alerts: AlertHistoryItem[];
	limit: number;
	offset: number;
}

export interface AlertSettingsResponse {
	auth_failure_threshold: number;
	auth_failure_window_minutes: number;
	rate_limit_threshold: number;
	rate_limit_window_minutes: number;
	lockout_threshold: number;
}

// =============================================================================
// Page Analytics Types
// =============================================================================

export interface DailyStat {
	date: string;
	total_views: number;
	unique_visitors: number;
	avg_duration_ms: number | null;
	avg_scroll_depth: number | null;
}

export interface GeoBreakdownItem {
	country: string;
	views: number;
	visitors: number;
}

export interface FunnelStats {
	start_date: string;
	end_date: string;
	unique_visitors: number;
	signup_clicks: number;
	signup_completions: number;
	click_through_rate: number;
	completion_rate: number;
	overall_conversion_rate: number;
}

export interface BounceRateStats {
	path: string;
	start_date: string;
	end_date: string;
	total_sessions: number;
	bounced_sessions: number;
	bounce_rate: number;
}

export interface LandingPageMetricsResponse {
	daily_stats: DailyStat[];
	geo_breakdown: GeoBreakdownItem[];
	funnel: FunnelStats;
	bounce_rate: BounceRateStats;
}

// =============================================================================
// Observability Links Types
// =============================================================================

export interface ObservabilityLinksResponse {
	grafana_url: string | null;
	prometheus_url: string | null;
	sentry_url: string | null;
	status_url: string | null;
	analytics_url: string | null;
	uptimerobot_url: string | null;
}

// =============================================================================
// Impersonation Types
// =============================================================================

export interface StartImpersonationRequest {
	reason: string;
	write_mode: boolean;
	duration_minutes: number;
}

export interface ImpersonationSessionResponse {
	admin_user_id: string;
	target_user_id: string;
	target_email: string | null;
	reason: string;
	is_write_mode: boolean;
	started_at: string;
	expires_at: string;
	remaining_seconds: number;
}

export interface ImpersonationStatusResponse {
	is_impersonating: boolean;
	session: ImpersonationSessionResponse | null;
}

export interface EndImpersonationResponse {
	ended: boolean;
	message: string;
}

export interface ImpersonationHistoryItem {
	id: number;
	admin_user_id: string;
	admin_email: string;
	target_user_id: string;
	target_email: string;
	reason: string;
	is_write_mode: boolean;
	started_at: string;
	expires_at: string;
	ended_at: string | null;
}

export interface ImpersonationHistoryResponse {
	total: number;
	sessions: ImpersonationHistoryItem[];
	limit: number;
}

// =============================================================================
// Promotion Types
// =============================================================================

export interface Promotion {
	id: string;
	code: string;
	type: string;
	value: number;
	max_uses: number | null;
	uses_count: number;
	expires_at: string | null;
	created_at: string;
	deleted_at: string | null;
}

export interface CreatePromotionRequest {
	code: string;
	type: string;
	value: number;
	max_uses?: number | null;
	expires_at?: string | null;
}

export interface DeactivatePromotionResponse {
	status: string;
	promotion_id: string;
}

export interface ApplyPromoToUserRequest {
	user_id: string;
	code: string;
}

export interface ApplyPromoToUserResponse {
	status: string;
	user_id: string;
	user_promotion_id: string;
	promotion_code: string;
}

export interface RemoveUserPromotionResponse {
	status: string;
	user_promotion_id: string;
}

export interface UserPromotionBrief {
	id: string;
	promotion_id: string;
	promotion_code: string;
	promotion_type: string;
	promotion_value: number;
	status: string;
	applied_at: string;
	deliberations_remaining: number | null;
	discount_applied: number | null;
}

export interface UserWithPromotions {
	user_id: string;
	email: string | null;
	promotions: UserPromotionBrief[];
}

// =============================================================================
// Feedback Types
// =============================================================================

export type FeedbackType = 'feature_request' | 'problem_report';
export type FeedbackStatus = 'new' | 'reviewing' | 'resolved' | 'closed';

export interface FeedbackContext {
	user_tier?: string;
	page_url?: string;
	user_agent?: string;
	timestamp?: string;
}

export type FeedbackSentiment = 'positive' | 'negative' | 'neutral' | 'mixed';

export interface FeedbackAnalysis {
	sentiment: FeedbackSentiment;
	sentiment_confidence: number;
	themes: string[];
	analyzed_at?: string | null;
}

export interface FeedbackResponse {
	id: string;
	user_id: string;
	type: FeedbackType;
	title: string;
	description: string;
	context?: FeedbackContext | null;
	analysis?: FeedbackAnalysis | null;
	status: FeedbackStatus;
	created_at: string;
	updated_at: string;
}

export interface FeedbackListResponse {
	items: FeedbackResponse[];
	total: number;
}

export interface FeedbackStatsResponse {
	total: number;
	by_type: Partial<Record<FeedbackType, number>>;
	by_status: Partial<Record<FeedbackStatus, number>>;
}

export interface ThemeCount {
	theme: string;
	count: number;
}

export interface FeedbackAnalysisSummary {
	analyzed_count: number;
	sentiment_counts: Partial<Record<FeedbackSentiment, number>>;
	top_themes: ThemeCount[];
}

// =============================================================================
// Embedding Visualization Types
// =============================================================================

export interface EmbeddingStatsResponse {
	total_embeddings: number;
	by_type: {
		contributions: number;
		research_cache: number;
		context_chunks: number;
	};
	dimensions: number;
	storage_estimate_mb: number;
	umap_available: boolean;
}

export interface EmbeddingPoint {
	x: number;
	y: number;
	type: 'contribution' | 'research' | 'context';
	preview: string;
	metadata: Record<string, unknown>;
	created_at: string;
	cluster_id: number;
}

export interface ClusterInfo {
	id: number;
	label: string;
	count: number;
	centroid: { x: number; y: number };
}

export interface EmbeddingSampleResponse {
	points: EmbeddingPoint[];
	method: 'pca' | 'umap';
	total_available: number;
	clusters: ClusterInfo[];
}

// =============================================================================
// Ops/Self-Healing Types
// =============================================================================

export interface ErrorPattern {
	id: number;
	pattern_name: string;
	pattern_regex: string;
	error_type: string;
	severity: string;
	description: string | null;
	enabled: boolean;
	threshold_count: number;
	threshold_window_minutes: number;
	cooldown_minutes: number;
	created_at: string;
	recent_matches: number;
	match_count: number; // Total matches (persisted in DB)
	last_match_at: string | null;
	fix_count: number;
	last_remediation: string | null;
}

export interface ErrorPatternListResponse {
	patterns: ErrorPattern[];
	total: number;
}

export interface RemediationLogEntry {
	id: number;
	pattern_name: string | null;
	fix_type: string | null;
	triggered_at: string;
	outcome: string;
	details: Record<string, unknown> | null;
	duration_ms: number | null;
}

export interface RemediationHistoryResponse {
	entries: RemediationLogEntry[];
	total: number;
}

export interface SystemHealthComponent {
	status: string;
	error?: string;
}

export interface SystemHealthResponse {
	checked_at: string;
	overall: string;
	components: Record<string, SystemHealthComponent | Record<string, unknown>>;
	recent_remediations: Record<string, number>;
}

export interface CreatePatternRequest {
	pattern_name: string;
	pattern_regex: string;
	error_type: string;
	severity?: string;
	description?: string;
	threshold_count?: number;
	threshold_window_minutes?: number;
	cooldown_minutes?: number;
}

export interface UpdatePatternRequest {
	pattern_regex?: string;
	severity?: string;
	description?: string;
	enabled?: boolean;
	threshold_count?: number;
	threshold_window_minutes?: number;
	cooldown_minutes?: number;
}

export interface ErrorCheckResult {
	checked_at: string;
	errors_scanned: number;
	patterns_matched: number;
	remediations_triggered: number;
	detections: Array<{
		pattern_name: string;
		error_type: string;
		severity: string;
		matched_text: string;
	}>;
	remediations: Array<{
		pattern_name: string;
		fix_type: string;
		outcome: string;
		message: string;
		duration_ms: number;
	}>;
	error?: string;
}

// =============================================================================
// A/B Experiment Types
// =============================================================================

export interface ExperimentVariantStats {
	variant: number;
	session_count: number;
	completed_count: number;
	avg_cost: number | null;
	avg_duration_seconds: number | null;
	avg_rounds: number | null;
	avg_persona_count: number | null;
	completion_rate: number;
}

export interface ExperimentMetricsResponse {
	experiment_name: string;
	variants: ExperimentVariantStats[];
	total_sessions: number;
	period_start: string;
	period_end: string;
}

// =============================================================================
// Experiment Management Types
// =============================================================================

export interface ExperimentVariant {
	name: string;
	weight: number;
}

export interface Experiment {
	id: string;
	name: string;
	description: string | null;
	status: 'draft' | 'running' | 'paused' | 'concluded';
	variants: ExperimentVariant[];
	metrics: string[];
	start_date: string | null;
	end_date: string | null;
	created_at: string;
	updated_at: string;
}

export interface ExperimentListResponse {
	experiments: Experiment[];
	total: number;
}

export interface ExperimentCreate {
	name: string;
	description?: string;
	variants?: ExperimentVariant[];
	metrics?: string[];
}

export interface ExperimentUpdate {
	description?: string;
	variants?: ExperimentVariant[];
	metrics?: string[];
}

export interface VariantAssignmentResponse {
	experiment_name: string;
	user_id: string;
	variant: string | null;
}

// =============================================================================
// Admin API Client
// =============================================================================

class AdminApiClient {
	private baseUrl: string;

	constructor(baseUrl?: string) {
		this.baseUrl = baseUrl || env.PUBLIC_API_URL || 'http://localhost:8000';
	}

	private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
		const url = `${this.baseUrl}${endpoint}`;
		const headers: Record<string, string> = {
			'Content-Type': 'application/json',
			...(options?.headers as Record<string, string>)
		};

		// Add CSRF token for mutating methods
		const method = options?.method?.toUpperCase() || 'GET';
		if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
			const csrfToken = getCsrfToken();
			if (csrfToken) {
				headers['X-CSRF-Token'] = csrfToken;
			}
		}

		const response = await fetch(url, {
			...options,
			credentials: 'include',
			headers
		});

		if (!response.ok) {
			let error;
			try {
				error = await response.json();
			} catch {
				error = { detail: response.statusText };
			}
			throw new ApiClientError(error.detail || 'Unknown error', response.status, error);
		}

		if (response.status === 204) {
			return {} as T;
		}

		return response.json();
	}

	// =========================================================================
	// Session Management
	// =========================================================================

	async getActiveSessions(topN: number = 10): Promise<ActiveSessionsResponse> {
		return this.fetch<ActiveSessionsResponse>(`/api/admin/sessions/active?top_n=${topN}`);
	}

	async getSessionFull(sessionId: string): Promise<FullSessionResponse> {
		return this.fetch<FullSessionResponse>(`/api/admin/sessions/${sessionId}/full`);
	}

	async killSession(sessionId: string, reason: string = 'Admin terminated'): Promise<ControlResponse> {
		return this.fetch<ControlResponse>(
			`/api/admin/sessions/${sessionId}/kill?reason=${encodeURIComponent(reason)}`,
			{ method: 'POST' }
		);
	}

	async killAllSessions(reason: string = 'System maintenance'): Promise<KillAllResponse> {
		return this.fetch<KillAllResponse>(
			`/api/admin/sessions/kill-all?confirm=true&reason=${encodeURIComponent(reason)}`,
			{ method: 'POST' }
		);
	}

	// =========================================================================
	// Cost Analytics
	// =========================================================================

	async getCostSummary(): Promise<CostSummaryResponse> {
		return this.fetch<CostSummaryResponse>('/api/admin/analytics/costs');
	}

	async getUserCosts(params?: {
		start_date?: string;
		end_date?: string;
		limit?: number;
		offset?: number;
	}): Promise<UserCostsResponse> {
		const searchParams = new URLSearchParams();
		if (params?.start_date) searchParams.set('start_date', params.start_date);
		if (params?.end_date) searchParams.set('end_date', params.end_date);
		if (params?.limit) searchParams.set('limit', String(params.limit));
		if (params?.offset) searchParams.set('offset', String(params.offset));

		const query = searchParams.toString();
		return this.fetch<UserCostsResponse>(`/api/admin/analytics/costs/users${query ? `?${query}` : ''}`);
	}

	async getDailyCosts(params?: {
		start_date?: string;
		end_date?: string;
	}): Promise<DailyCostsResponse> {
		const searchParams = new URLSearchParams();
		if (params?.start_date) searchParams.set('start_date', params.start_date);
		if (params?.end_date) searchParams.set('end_date', params.end_date);

		const query = searchParams.toString();
		return this.fetch<DailyCostsResponse>(`/api/admin/analytics/costs/daily${query ? `?${query}` : ''}`);
	}

	// =========================================================================
	// Kill History (Audit Trail)
	// =========================================================================

	async getKillHistory(params?: {
		limit?: number;
		offset?: number;
	}): Promise<SessionKillsResponse> {
		const searchParams = new URLSearchParams();
		if (params?.limit) searchParams.set('limit', String(params.limit));
		if (params?.offset) searchParams.set('offset', String(params.offset));

		const query = searchParams.toString();
		return this.fetch<SessionKillsResponse>(`/api/admin/sessions/kill-history${query ? `?${query}` : ''}`);
	}

	// =========================================================================
	// User & Usage Metrics
	// =========================================================================

	async getUserMetrics(days: number = 30): Promise<UserMetricsResponse> {
		return this.fetch<UserMetricsResponse>(`/api/admin/metrics/users?days=${days}`);
	}

	async getUsageMetrics(days: number = 30): Promise<UsageMetricsResponse> {
		return this.fetch<UsageMetricsResponse>(`/api/admin/metrics/usage?days=${days}`);
	}

	async getOnboardingMetrics(): Promise<OnboardingFunnelResponse> {
		return this.fetch<OnboardingFunnelResponse>('/api/admin/metrics/onboarding');
	}

	// =========================================================================
	// Alerts
	// =========================================================================

	async getAlertHistory(params?: {
		alert_type?: string;
		limit?: number;
		offset?: number;
	}): Promise<AlertHistoryResponse> {
		const searchParams = new URLSearchParams();
		if (params?.alert_type) searchParams.set('alert_type', params.alert_type);
		if (params?.limit) searchParams.set('limit', String(params.limit));
		if (params?.offset) searchParams.set('offset', String(params.offset));

		const query = searchParams.toString();
		return this.fetch<AlertHistoryResponse>(`/api/admin/alerts/history${query ? `?${query}` : ''}`);
	}

	async getAlertSettings(): Promise<AlertSettingsResponse> {
		return this.fetch<AlertSettingsResponse>('/api/admin/alerts/settings');
	}

	async getAlertTypes(): Promise<string[]> {
		return this.fetch<string[]>('/api/admin/alerts/types');
	}

	// =========================================================================
	// Observability Links
	// =========================================================================

	async getObservabilityLinks(): Promise<ObservabilityLinksResponse> {
		return this.fetch<ObservabilityLinksResponse>('/api/admin/observability-links');
	}

	// =========================================================================
	// Impersonation
	// =========================================================================

	async startImpersonation(
		userId: string,
		request: StartImpersonationRequest
	): Promise<ImpersonationSessionResponse> {
		return this.fetch<ImpersonationSessionResponse>(`/api/admin/impersonate/${userId}`, {
			method: 'POST',
			body: JSON.stringify(request)
		});
	}

	async endImpersonation(): Promise<EndImpersonationResponse> {
		return this.fetch<EndImpersonationResponse>('/api/admin/impersonate', {
			method: 'DELETE'
		});
	}

	async getImpersonationStatus(): Promise<ImpersonationStatusResponse> {
		return this.fetch<ImpersonationStatusResponse>('/api/admin/impersonate/status');
	}

	async getImpersonationHistory(params?: {
		admin_user_id?: string;
		target_user_id?: string;
		limit?: number;
	}): Promise<ImpersonationHistoryResponse> {
		const searchParams = new URLSearchParams();
		if (params?.admin_user_id) searchParams.set('admin_user_id', params.admin_user_id);
		if (params?.target_user_id) searchParams.set('target_user_id', params.target_user_id);
		if (params?.limit) searchParams.set('limit', String(params.limit));

		const query = searchParams.toString();
		return this.fetch<ImpersonationHistoryResponse>(
			`/api/admin/impersonate/history${query ? `?${query}` : ''}`
		);
	}

	// =========================================================================
	// Promotions
	// =========================================================================

	async listPromotions(): Promise<Promotion[]> {
		return this.fetch<Promotion[]>('/api/admin/promotions');
	}

	async createPromotion(data: CreatePromotionRequest): Promise<Promotion> {
		return this.fetch<Promotion>('/api/admin/promotions', {
			method: 'POST',
			body: JSON.stringify(data)
		});
	}

	async deletePromotion(promotionId: string): Promise<DeactivatePromotionResponse> {
		return this.fetch<DeactivatePromotionResponse>(`/api/admin/promotions/${promotionId}`, {
			method: 'DELETE'
		});
	}

	async applyPromoToUser(userId: string, code: string): Promise<ApplyPromoToUserResponse> {
		return this.fetch<ApplyPromoToUserResponse>('/api/admin/promotions/apply', {
			method: 'POST',
			body: JSON.stringify({ user_id: userId, code })
		});
	}

	async removeUserPromotion(userPromotionId: string): Promise<RemoveUserPromotionResponse> {
		return this.fetch<RemoveUserPromotionResponse>(`/api/admin/promotions/user/${userPromotionId}`, {
			method: 'DELETE'
		});
	}

	async getUsersWithPromotions(): Promise<UserWithPromotions[]> {
		return this.fetch<UserWithPromotions[]>('/api/admin/promotions/users');
	}

	// =========================================================================
	// Feedback
	// =========================================================================

	async listFeedback(params?: {
		type?: 'feature_request' | 'problem_report';
		status?: 'new' | 'reviewing' | 'resolved' | 'closed';
		sentiment?: FeedbackSentiment;
		theme?: string;
		limit?: number;
		offset?: number;
	}): Promise<FeedbackListResponse> {
		const searchParams = new URLSearchParams();
		if (params?.type) searchParams.set('type', params.type);
		if (params?.status) searchParams.set('status', params.status);
		if (params?.sentiment) searchParams.set('sentiment', params.sentiment);
		if (params?.theme) searchParams.set('theme', params.theme);
		if (params?.limit) searchParams.set('limit', String(params.limit));
		if (params?.offset) searchParams.set('offset', String(params.offset));

		const query = searchParams.toString();
		return this.fetch<FeedbackListResponse>(
			`/api/admin/feedback${query ? `?${query}` : ''}`
		);
	}

	async getFeedbackStats(): Promise<FeedbackStatsResponse> {
		return this.fetch<FeedbackStatsResponse>('/api/admin/feedback/stats');
	}

	async getFeedbackAnalysisSummary(): Promise<FeedbackAnalysisSummary> {
		return this.fetch<FeedbackAnalysisSummary>('/api/admin/feedback/analysis-summary');
	}

	async getFeedbackByTheme(theme: string, limit: number = 50): Promise<FeedbackListResponse> {
		return this.fetch<FeedbackListResponse>(
			`/api/admin/feedback/by-theme/${encodeURIComponent(theme)}?limit=${limit}`
		);
	}

	async getFeedback(feedbackId: string): Promise<FeedbackResponse> {
		return this.fetch<FeedbackResponse>(`/api/admin/feedback/${feedbackId}`);
	}

	async updateFeedbackStatus(
		feedbackId: string,
		status: 'new' | 'reviewing' | 'resolved' | 'closed'
	): Promise<FeedbackResponse> {
		return this.fetch<FeedbackResponse>(`/api/admin/feedback/${feedbackId}`, {
			method: 'PATCH',
			body: JSON.stringify({ status })
		});
	}

	// =========================================================================
	// Ops / Self-Healing
	// =========================================================================

	async getErrorPatterns(params?: {
		error_type?: string;
		enabled_only?: boolean;
	}): Promise<ErrorPatternListResponse> {
		const searchParams = new URLSearchParams();
		if (params?.error_type) searchParams.set('error_type', params.error_type);
		if (params?.enabled_only) searchParams.set('enabled_only', 'true');

		const query = searchParams.toString();
		return this.fetch<ErrorPatternListResponse>(
			`/api/admin/ops/patterns${query ? `?${query}` : ''}`
		);
	}

	async getRemediationHistory(params?: {
		limit?: number;
		offset?: number;
		outcome?: string;
	}): Promise<RemediationHistoryResponse> {
		const searchParams = new URLSearchParams();
		if (params?.limit) searchParams.set('limit', String(params.limit));
		if (params?.offset) searchParams.set('offset', String(params.offset));
		if (params?.outcome) searchParams.set('outcome', params.outcome);

		const query = searchParams.toString();
		return this.fetch<RemediationHistoryResponse>(
			`/api/admin/ops/remediations${query ? `?${query}` : ''}`
		);
	}

	async getSystemHealth(): Promise<SystemHealthResponse> {
		return this.fetch<SystemHealthResponse>('/api/admin/ops/health');
	}

	async createErrorPattern(data: CreatePatternRequest): Promise<{ id: number; pattern_name: string; message: string }> {
		return this.fetch<{ id: number; pattern_name: string; message: string }>('/api/admin/ops/patterns', {
			method: 'POST',
			body: JSON.stringify(data)
		});
	}

	async updateErrorPattern(patternId: number, data: UpdatePatternRequest): Promise<{ message: string }> {
		return this.fetch<{ message: string }>(`/api/admin/ops/patterns/${patternId}`, {
			method: 'PATCH',
			body: JSON.stringify(data)
		});
	}

	async triggerErrorCheck(executeFixes: boolean = true): Promise<ErrorCheckResult> {
		return this.fetch<ErrorCheckResult>(
			`/api/admin/ops/check?execute_fixes=${executeFixes}`,
			{ method: 'POST' }
		);
	}

	// =========================================================================
	// Page Analytics (Landing Page)
	// =========================================================================

	async getLandingPageMetrics(params?: {
		start_date?: string;
		end_date?: string;
	}): Promise<LandingPageMetricsResponse> {
		const searchParams = new URLSearchParams();
		if (params?.start_date) searchParams.set('start_date', params.start_date);
		if (params?.end_date) searchParams.set('end_date', params.end_date);

		const query = searchParams.toString();
		return this.fetch<LandingPageMetricsResponse>(
			`/api/admin/analytics/landing-page${query ? `?${query}` : ''}`
		);
	}

	async getDailyPageStats(params?: {
		start_date?: string;
		end_date?: string;
		path?: string;
	}): Promise<DailyStat[]> {
		const searchParams = new URLSearchParams();
		if (params?.start_date) searchParams.set('start_date', params.start_date);
		if (params?.end_date) searchParams.set('end_date', params.end_date);
		if (params?.path) searchParams.set('path', params.path);

		const query = searchParams.toString();
		return this.fetch<DailyStat[]>(`/api/admin/analytics/daily-stats${query ? `?${query}` : ''}`);
	}

	async getGeoBreakdown(params?: {
		start_date?: string;
		end_date?: string;
		limit?: number;
	}): Promise<GeoBreakdownItem[]> {
		const searchParams = new URLSearchParams();
		if (params?.start_date) searchParams.set('start_date', params.start_date);
		if (params?.end_date) searchParams.set('end_date', params.end_date);
		if (params?.limit) searchParams.set('limit', String(params.limit));

		const query = searchParams.toString();
		return this.fetch<GeoBreakdownItem[]>(
			`/api/admin/analytics/geo-breakdown${query ? `?${query}` : ''}`
		);
	}

	async getFunnelStatsPage(params?: {
		start_date?: string;
		end_date?: string;
	}): Promise<FunnelStats> {
		const searchParams = new URLSearchParams();
		if (params?.start_date) searchParams.set('start_date', params.start_date);
		if (params?.end_date) searchParams.set('end_date', params.end_date);

		const query = searchParams.toString();
		return this.fetch<FunnelStats>(`/api/admin/analytics/funnel${query ? `?${query}` : ''}`);
	}

	async getBounceRate(params?: {
		start_date?: string;
		end_date?: string;
		path?: string;
	}): Promise<BounceRateStats> {
		const searchParams = new URLSearchParams();
		if (params?.start_date) searchParams.set('start_date', params.start_date);
		if (params?.end_date) searchParams.set('end_date', params.end_date);
		if (params?.path) searchParams.set('path', params.path);

		const query = searchParams.toString();
		return this.fetch<BounceRateStats>(`/api/admin/analytics/bounce-rate${query ? `?${query}` : ''}`);
	}

	// =========================================================================
	// Blog Management
	// =========================================================================

	async listBlogPosts(params?: {
		status?: 'draft' | 'scheduled' | 'published';
		limit?: number;
		offset?: number;
	}): Promise<BlogPostListResponse> {
		const searchParams = new URLSearchParams();
		if (params?.status) searchParams.set('status', params.status);
		if (params?.limit) searchParams.set('limit', String(params.limit));
		if (params?.offset) searchParams.set('offset', String(params.offset));

		const query = searchParams.toString();
		return this.fetch<BlogPostListResponse>(`/api/admin/blog/posts${query ? `?${query}` : ''}`);
	}

	async createBlogPost(request: BlogPostCreate): Promise<BlogPost> {
		return this.fetch<BlogPost>('/api/admin/blog/posts', {
			method: 'POST',
			body: JSON.stringify(request)
		});
	}

	async getBlogPost(id: string): Promise<BlogPost> {
		return this.fetch<BlogPost>(`/api/admin/blog/posts/${id}`);
	}

	async updateBlogPost(id: string, request: BlogPostUpdate): Promise<BlogPost> {
		return this.fetch<BlogPost>(`/api/admin/blog/posts/${id}`, {
			method: 'PATCH',
			body: JSON.stringify(request)
		});
	}

	async deleteBlogPost(id: string): Promise<{ success: boolean; message: string }> {
		return this.fetch<{ success: boolean; message: string }>(`/api/admin/blog/posts/${id}`, {
			method: 'DELETE'
		});
	}

	async publishBlogPost(id: string): Promise<BlogPost> {
		return this.fetch<BlogPost>(`/api/admin/blog/posts/${id}/publish`, {
			method: 'POST'
		});
	}

	async scheduleBlogPost(id: string, publishAt: string): Promise<BlogPost> {
		return this.fetch<BlogPost>(`/api/admin/blog/posts/${id}/schedule`, {
			method: 'POST',
			body: JSON.stringify({ published_at: publishAt })
		});
	}

	async generateBlogPost(
		request: BlogGenerateRequest,
		saveDraft: boolean = true
	): Promise<BlogGenerateResponse> {
		return this.fetch<BlogGenerateResponse>(
			`/api/admin/blog/generate?save_draft=${saveDraft}`,
			{
				method: 'POST',
				body: JSON.stringify(request)
			}
		);
	}

	async discoverTopics(industry?: string): Promise<TopicsResponse> {
		const searchParams = new URLSearchParams();
		if (industry) searchParams.set('industry', industry);
		const query = searchParams.toString();
		return this.fetch<TopicsResponse>(`/api/admin/blog/topics${query ? `?${query}` : ''}`);
	}

	// =========================================================================
	// Embedding Visualization
	// =========================================================================

	async getEmbeddingStats(): Promise<EmbeddingStatsResponse> {
		return this.fetch<EmbeddingStatsResponse>('/api/admin/embeddings/stats');
	}

	async getEmbeddingSample(params?: {
		embedding_type?: 'all' | 'contributions' | 'research' | 'context';
		limit?: number;
		method?: 'pca' | 'umap';
	}): Promise<EmbeddingSampleResponse> {
		const searchParams = new URLSearchParams();
		if (params?.embedding_type) searchParams.set('embedding_type', params.embedding_type);
		if (params?.limit) searchParams.set('limit', String(params.limit));
		if (params?.method) searchParams.set('method', params.method);

		const query = searchParams.toString();
		return this.fetch<EmbeddingSampleResponse>(
			`/api/admin/embeddings/sample${query ? `?${query}` : ''}`
		);
	}

	// =========================================================================
	// Enhanced Cost Tracking
	// =========================================================================

	async getFixedCosts(includeInactive: boolean = false): Promise<FixedCostsResponse> {
		return this.fetch<FixedCostsResponse>(
			`/api/admin/costs/fixed?include_inactive=${includeInactive}`
		);
	}

	async createFixedCost(data: {
		provider: string;
		description: string;
		monthly_amount_usd: number;
		category?: string;
		notes?: string;
	}): Promise<FixedCostItem> {
		return this.fetch<FixedCostItem>('/api/admin/costs/fixed', {
			method: 'POST',
			body: JSON.stringify(data)
		});
	}

	async updateFixedCost(
		costId: number,
		data: { monthly_amount_usd?: number; active?: boolean; notes?: string }
	): Promise<FixedCostItem> {
		return this.fetch<FixedCostItem>(`/api/admin/costs/fixed/${costId}`, {
			method: 'PATCH',
			body: JSON.stringify(data)
		});
	}

	async deleteFixedCost(costId: number): Promise<{ deleted: boolean; cost_id: number }> {
		return this.fetch<{ deleted: boolean; cost_id: number }>(
			`/api/admin/costs/fixed/${costId}`,
			{ method: 'DELETE' }
		);
	}

	async seedFixedCosts(): Promise<FixedCostsResponse> {
		return this.fetch<FixedCostsResponse>('/api/admin/costs/fixed/seed', { method: 'POST' });
	}

	async getCostsByProvider(days: number = 30): Promise<CostsByProviderResponse> {
		return this.fetch<CostsByProviderResponse>(`/api/admin/costs/by-provider?days=${days}`);
	}

	async getMeetingCosts(sessionId: string): Promise<MeetingCostResponse> {
		return this.fetch<MeetingCostResponse>(`/api/admin/costs/by-meeting/${sessionId}`);
	}

	async getPerUserCosts(params?: {
		days?: number;
		limit?: number;
	}): Promise<PerUserCostResponse> {
		const searchParams = new URLSearchParams();
		if (params?.days) searchParams.set('days', String(params.days));
		if (params?.limit) searchParams.set('limit', String(params.limit));

		const query = searchParams.toString();
		return this.fetch<PerUserCostResponse>(
			`/api/admin/costs/per-user${query ? `?${query}` : ''}`
		);
	}

	async getDailyCostSummary(days: number = 30): Promise<DailySummaryResponse> {
		return this.fetch<DailySummaryResponse>(`/api/admin/costs/daily-summary?days=${days}`);
	}

	async getUnifiedCacheMetrics(): Promise<UnifiedCacheMetricsResponse> {
		return this.fetch<UnifiedCacheMetricsResponse>('/api/admin/costs/cache-metrics');
	}

	async getPayingUsersCount(): Promise<{ paying_users_count: number }> {
		return this.fetch<{ paying_users_count: number }>('/api/admin/costs/paying-users-count');
	}

	// =========================================================================
	// Email Stats
	// =========================================================================

	async getEmailStats(days: number = 30): Promise<EmailStatsResponse> {
		return this.fetch<EmailStatsResponse>(`/api/admin/email-stats?days=${days}`);
	}

	// =========================================================================
	// SEO Analytics
	// =========================================================================

	async getSeoAnalytics(topLimit: number = 10): Promise<AdminSeoAnalyticsResponse> {
		return this.fetch<AdminSeoAnalyticsResponse>(
			`/api/admin/seo/analytics?top_limit=${topLimit}`
		);
	}

	async getBlogPerformance(
		limit: number = 50,
		sortBy: 'views' | 'ctr' | 'cost_per_click' | 'roi' = 'views'
	): Promise<BlogPerformanceResponse> {
		return this.fetch<BlogPerformanceResponse>(
			`/api/admin/seo/performance?limit=${limit}&sort_by=${sortBy}`
		);
	}

	// =========================================================================
	// Published Decisions
	// =========================================================================

	async listDecisions(params?: {
		status?: 'draft' | 'published';
		category?: DecisionCategory;
		limit?: number;
		offset?: number;
	}): Promise<DecisionListResponse> {
		const searchParams = new URLSearchParams();
		if (params?.status) searchParams.set('status', params.status);
		if (params?.category) searchParams.set('category', params.category);
		if (params?.limit) searchParams.set('limit', String(params.limit));
		if (params?.offset) searchParams.set('offset', String(params.offset));

		const query = searchParams.toString();
		return this.fetch<DecisionListResponse>(
			`/api/admin/decisions${query ? `?${query}` : ''}`
		);
	}

	async getDecision(id: string): Promise<Decision> {
		return this.fetch<Decision>(`/api/admin/decisions/${id}`);
	}

	async createDecision(request: DecisionCreate): Promise<Decision> {
		return this.fetch<Decision>('/api/admin/decisions', {
			method: 'POST',
			body: JSON.stringify(request)
		});
	}

	async updateDecision(id: string, request: DecisionUpdate): Promise<Decision> {
		return this.fetch<Decision>(`/api/admin/decisions/${id}`, {
			method: 'PATCH',
			body: JSON.stringify(request)
		});
	}

	async deleteDecision(id: string): Promise<{ success: boolean; message: string }> {
		return this.fetch<{ success: boolean; message: string }>(`/api/admin/decisions/${id}`, {
			method: 'DELETE'
		});
	}

	async publishDecision(id: string): Promise<Decision> {
		return this.fetch<Decision>(`/api/admin/decisions/${id}/publish`, {
			method: 'POST'
		});
	}

	async unpublishDecision(id: string): Promise<Decision> {
		return this.fetch<Decision>(`/api/admin/decisions/${id}/unpublish`, {
			method: 'POST'
		});
	}

	async generateDecision(request: DecisionGenerateRequest, saveDraft: boolean = true): Promise<Decision> {
		return this.fetch<Decision>(`/api/admin/decisions/generate?save_draft=${saveDraft}`, {
			method: 'POST',
			body: JSON.stringify(request)
		});
	}

	async getDecisionCategories(): Promise<CategoriesResponse> {
		return this.fetch<CategoriesResponse>('/api/admin/decisions/categories');
	}

	// =========================================================================
	// Blog Topic Proposer
	// =========================================================================

	async proposeTopics(count: number = 5): Promise<TopicProposalsResponse> {
		return this.fetch<TopicProposalsResponse>('/api/admin/blog/propose-topics', {
			method: 'POST',
			body: JSON.stringify({ count })
		});
	}

	// =========================================================================
	// Runtime Config (Emergency Toggles)
	// =========================================================================

	async getRuntimeConfig(): Promise<RuntimeConfigResponse> {
		return this.fetch<RuntimeConfigResponse>('/api/admin/runtime-config');
	}

	async setRuntimeConfig(key: string, value: boolean): Promise<RuntimeConfigItem> {
		return this.fetch<RuntimeConfigItem>(`/api/admin/runtime-config/${encodeURIComponent(key)}`, {
			method: 'PATCH',
			body: JSON.stringify({ value })
		});
	}

	async clearRuntimeConfig(key: string): Promise<RuntimeConfigItem> {
		return this.fetch<RuntimeConfigItem>(`/api/admin/runtime-config/${encodeURIComponent(key)}`, {
			method: 'DELETE'
		});
	}

	// =========================================================================
	// Research Cache
	// =========================================================================

	async getResearchCacheStats(): Promise<ResearchCacheStats> {
		return this.fetch<ResearchCacheStats>('/api/admin/research-cache/stats');
	}

	async getResearchCacheMetrics(): Promise<CacheMetricsResponse> {
		return this.fetch<CacheMetricsResponse>('/api/admin/research-cache/metrics');
	}

	async getResearchCosts(): Promise<ResearchCostsResponse> {
		return this.fetch<ResearchCostsResponse>('/api/admin/costs/research');
	}

	async getCostAggregations(days: number = 30): Promise<CostAggregationsResponse> {
		return this.fetch<CostAggregationsResponse>(`/api/admin/costs/aggregations?days=${days}`);
	}

	// =========================================================================
	// A/B Experiments (Legacy Metrics)
	// =========================================================================

	async getPersonaCountExperiment(): Promise<ExperimentMetricsResponse> {
		return this.fetch<ExperimentMetricsResponse>('/api/admin/experiments/persona-count');
	}

	// =========================================================================
	// A/B Experiment Management
	// =========================================================================

	async listExperiments(status?: string): Promise<ExperimentListResponse> {
		const searchParams = new URLSearchParams();
		if (status) searchParams.set('status', status);
		const query = searchParams.toString();
		return this.fetch<ExperimentListResponse>(
			`/api/admin/experiments${query ? `?${query}` : ''}`
		);
	}

	async createExperiment(data: ExperimentCreate): Promise<Experiment> {
		return this.fetch<Experiment>('/api/admin/experiments', {
			method: 'POST',
			body: JSON.stringify(data)
		});
	}

	async getExperiment(experimentId: string): Promise<Experiment> {
		return this.fetch<Experiment>(`/api/admin/experiments/${experimentId}`);
	}

	async updateExperiment(experimentId: string, data: ExperimentUpdate): Promise<Experiment> {
		return this.fetch<Experiment>(`/api/admin/experiments/${experimentId}`, {
			method: 'PATCH',
			body: JSON.stringify(data)
		});
	}

	async deleteExperiment(experimentId: string): Promise<{ status: string; id: string }> {
		return this.fetch<{ status: string; id: string }>(
			`/api/admin/experiments/${experimentId}`,
			{ method: 'DELETE' }
		);
	}

	async startExperiment(experimentId: string): Promise<Experiment> {
		return this.fetch<Experiment>(`/api/admin/experiments/${experimentId}/start`, {
			method: 'POST'
		});
	}

	async pauseExperiment(experimentId: string): Promise<Experiment> {
		return this.fetch<Experiment>(`/api/admin/experiments/${experimentId}/pause`, {
			method: 'POST'
		});
	}

	async concludeExperiment(experimentId: string): Promise<Experiment> {
		return this.fetch<Experiment>(`/api/admin/experiments/${experimentId}/conclude`, {
			method: 'POST'
		});
	}

	async getUserVariant(experimentName: string, userId: string): Promise<VariantAssignmentResponse> {
		return this.fetch<VariantAssignmentResponse>(
			`/api/admin/experiments/${encodeURIComponent(experimentName)}/variant/${encodeURIComponent(userId)}`
		);
	}

	// =========================================================================
	// Admin Email
	// =========================================================================

	async sendUserEmail(userId: string, request: SendEmailRequest): Promise<SendEmailResponse> {
		return this.fetch<SendEmailResponse>(`/api/admin/users/${userId}/send-email`, {
			method: 'POST',
			body: JSON.stringify(request)
		});
	}

	// =========================================================================
	// Internal Costs
	// =========================================================================

	async getInternalCosts(): Promise<InternalCostsResponse> {
		return this.fetch<InternalCostsResponse>('/api/admin/costs/internal');
	}

	// =========================================================================
	// Cost Insight Drill-Downs
	// =========================================================================

	async getCacheEffectiveness(
		period: string = 'week'
	): Promise<CacheEffectivenessResponse> {
		return this.fetch<CacheEffectivenessResponse>(
			`/api/admin/drilldown/cache-effectiveness?period=${period}`
		);
	}

	async getModelImpact(period: string = 'week'): Promise<ModelImpactResponse> {
		return this.fetch<ModelImpactResponse>(
			`/api/admin/drilldown/model-impact?period=${period}`
		);
	}

	async getFeatureEfficiency(
		period: string = 'week'
	): Promise<FeatureEfficiencyResponse> {
		return this.fetch<FeatureEfficiencyResponse>(
			`/api/admin/drilldown/feature-efficiency?period=${period}`
		);
	}

	async getTuningRecommendations(): Promise<TuningRecommendationsResponse> {
		return this.fetch<TuningRecommendationsResponse>(
			'/api/admin/drilldown/tuning-recommendations'
		);
	}

	async getQualityIndicators(
		period: string = 'month'
	): Promise<QualityIndicatorsResponse> {
		return this.fetch<QualityIndicatorsResponse>(
			`/api/admin/drilldown/quality-indicators?period=${period}`
		);
	}

	// =========================================================================
	// Billing Products & Prices
	// =========================================================================

	async getBillingProducts(): Promise<BillingConfigResponse> {
		return this.fetch<BillingConfigResponse>('/api/admin/billing/products');
	}

	async createBillingProduct(data: ProductCreate): Promise<BillingProduct> {
		return this.fetch<BillingProduct>('/api/admin/billing/products', {
			method: 'POST',
			body: JSON.stringify(data)
		});
	}

	async updateBillingProduct(productId: string, data: ProductUpdate): Promise<BillingProduct> {
		return this.fetch<BillingProduct>(`/api/admin/billing/products/${productId}`, {
			method: 'PUT',
			body: JSON.stringify(data)
		});
	}

	async deleteBillingProduct(productId: string): Promise<{ success: boolean; slug: string }> {
		return this.fetch<{ success: boolean; slug: string }>(
			`/api/admin/billing/products/${productId}`,
			{ method: 'DELETE' }
		);
	}

	async createBillingPrice(data: PriceCreate): Promise<BillingPrice> {
		return this.fetch<BillingPrice>('/api/admin/billing/prices', {
			method: 'POST',
			body: JSON.stringify(data)
		});
	}

	async updateBillingPrice(priceId: string, data: PriceUpdate): Promise<BillingPrice> {
		return this.fetch<BillingPrice>(`/api/admin/billing/prices/${priceId}`, {
			method: 'PUT',
			body: JSON.stringify(data)
		});
	}

	async syncBillingToStripe(): Promise<SyncResult> {
		return this.fetch<SyncResult>('/api/admin/billing/sync/stripe', {
			method: 'POST'
		});
	}

	async getBillingSyncStatus(): Promise<SyncStatus> {
		return this.fetch<SyncStatus>('/api/admin/billing/sync/status');
	}

	async getStripeConfigStatus(): Promise<StripeConfigStatus> {
		return this.fetch<StripeConfigStatus>('/api/admin/billing/stripe/status');
	}

	// =========================================================================
	// SEO Access Management
	// =========================================================================

	async getSeoAccess(userId: string): Promise<SeoAccessResponse> {
		return this.fetch<SeoAccessResponse>(`/api/admin/users/${encodeURIComponent(userId)}/seo-access`);
	}

	async grantSeoAccess(userId: string): Promise<SeoAccessResponse> {
		return this.fetch<SeoAccessResponse>(`/api/admin/users/${encodeURIComponent(userId)}/seo-access`, {
			method: 'POST'
		});
	}

	async revokeSeoAccess(userId: string): Promise<SeoAccessResponse> {
		return this.fetch<SeoAccessResponse>(`/api/admin/users/${encodeURIComponent(userId)}/seo-access`, {
			method: 'DELETE'
		});
	}
}

// Blog Post Types
export interface BlogPost {
	id: string;
	title: string;
	slug: string;
	content?: string;
	excerpt?: string;
	status: 'draft' | 'scheduled' | 'published';
	published_at?: string;
	seo_keywords?: string[];
	generated_by_topic?: string;
	meta_title?: string;
	meta_description?: string;
	author_id?: string;
	created_at: string;
	updated_at: string;
}

export interface BlogPostListResponse {
	posts: BlogPost[];
	total: number;
}

export interface BlogPostCreate {
	title: string;
	content: string;
	excerpt?: string;
	status?: 'draft' | 'scheduled' | 'published';
	published_at?: string;
	seo_keywords?: string[];
	meta_title?: string;
	meta_description?: string;
}

export interface BlogPostUpdate {
	title?: string;
	content?: string;
	excerpt?: string;
	status?: 'draft' | 'scheduled' | 'published';
	published_at?: string;
	seo_keywords?: string[];
	meta_title?: string;
	meta_description?: string;
}

export interface BlogGenerateRequest {
	topic: string;
	keywords?: string[];
}

export interface BlogGenerateResponse {
	title: string;
	excerpt: string;
	content: string;
	meta_title: string;
	meta_description: string;
	post_id?: string;
}

export interface Topic {
	title: string;
	description: string;
	keywords: string[];
	relevance_score: number;
	source: 'context' | 'trend' | 'gap';
}

export interface TopicsResponse {
	topics: Topic[];
}

// =============================================================================
// SEO Analytics Types
// =============================================================================

export interface SeoTopArticle {
	article_id: number;
	title: string;
	user_email: string | null;
	views: number;
	clicks: number;
	signups: number;
	ctr: number;
	signup_rate: number;
}

export interface SeoAnalyticsSummary {
	total_articles: number;
	total_views: number;
	total_clicks: number;
	total_signups: number;
	overall_ctr: number;
	overall_signup_rate: number;
	views_today: number;
	views_this_week: number;
	views_this_month: number;
}

export interface AdminSeoAnalyticsResponse {
	summary: SeoAnalyticsSummary;
	top_by_views: SeoTopArticle[];
	top_by_conversion: SeoTopArticle[];
}

export interface BlogPostPerformance {
	id: string;
	title: string;
	slug: string;
	view_count: number;
	click_through_count: number;
	ctr_percent: number;
	generation_cost: number;
	cost_per_view: number;
	cost_per_click: number;
	published_at: string | null;
	last_viewed_at: string | null;
}

export interface BlogPerformanceResponse {
	posts: BlogPostPerformance[];
	total_views: number;
	total_clicks: number;
	total_cost: number;
	overall_ctr: number;
}

// =============================================================================
// Enhanced Cost Tracking Types
// =============================================================================

export interface FixedCostItem {
	id: number;
	provider: string;
	description: string;
	monthly_amount_usd: number;
	category: string;
	active: boolean;
	notes: string | null;
}

export interface CreateFixedCostRequest {
	provider: string;
	description: string;
	monthly_amount_usd: number;
	category?: string;
	notes?: string;
}

export interface UpdateFixedCostRequest {
	monthly_amount_usd?: number;
	active?: boolean;
	notes?: string;
}

export interface FixedCostsResponse {
	costs: FixedCostItem[];
	monthly_total: number;
}

export interface ProviderCostItem {
	provider: string;
	amount_usd: number;
	request_count: number;
	percentage: number;
}

export interface CostsByProviderResponse {
	providers: ProviderCostItem[];
	total_usd: number;
	period_start: string;
	period_end: string;
}

export interface MeetingCostResponse {
	session_id: string;
	total_cost: number;
	api_calls: number;
	by_provider: Record<string, number>;
	by_phase: Record<string, number>;
}

export interface PerUserCostItem {
	user_id: string;
	email: string | null;
	total_cost: number;
	session_count: number;
	avg_cost_per_session: number;
}

export interface PerUserCostResponse {
	users: PerUserCostItem[];
	overall_avg: number;
	total_users: number;
	period_start: string;
	period_end: string;
}

export interface DailySummaryItem {
	date: string;
	total_usd: number;
	by_provider: Record<string, number>;
	request_count: number;
}

export interface DailySummaryResponse {
	days: DailySummaryItem[];
	period_start: string;
	period_end: string;
}

// =============================================================================
// Email Stats Types
// =============================================================================

export interface EmailPeriodCounts {
	today: number;
	week: number;
	month: number;
}

export interface EmailStatsResponse {
	total: number;
	by_type: Record<string, number>;
	by_period: EmailPeriodCounts;
}

// =============================================================================
// Runtime Config Types
// =============================================================================

export interface RuntimeConfigItem {
	key: string;
	override_value: boolean | null;
	default_value: boolean | null;
	effective_value: boolean | null;
	is_overridden: boolean;
}

export interface RuntimeConfigResponse {
	items: RuntimeConfigItem[];
	count: number;
}

export interface UpdateRuntimeConfigRequest {
	value: boolean;
}

// =============================================================================
// Research Cache Types
// =============================================================================

export interface ResearchCacheStats {
	total_cached_results: number;
	cache_hit_rate_30d: number;
	cost_savings_30d: number;
	top_cached_questions: Array<{
		question: string;
		hit_count: number;
		last_accessed: string;
	}>;
}

export interface SimilarityBucket {
	bucket: number;
	range_start: number;
	range_end: number;
	count: number;
}

export interface CacheMetricsResponse {
	hit_rate_1d: number;
	hit_rate_7d: number;
	hit_rate_30d: number;
	total_queries_1d: number;
	total_queries_7d: number;
	total_queries_30d: number;
	cache_hits_1d: number;
	cache_hits_7d: number;
	cache_hits_30d: number;
	avg_similarity_on_hit: number;
	miss_distribution: SimilarityBucket[];
	current_threshold: number;
	recommended_threshold: number;
	recommendation_reason: string;
	recommendation_confidence: 'low' | 'medium' | 'high';
	total_cached_results: number;
	cost_savings_30d: number;
}

// =============================================================================
// Unified Cache Metrics Types
// =============================================================================

export interface CacheTypeMetrics {
	hit_rate: number;
	hits: number;
	misses: number;
	total: number;
}

export interface AggregatedCacheMetrics {
	hit_rate: number;
	total_hits: number;
	total_requests: number;
}

export interface UnifiedCacheMetricsResponse {
	prompt: CacheTypeMetrics;
	research: CacheTypeMetrics;
	llm: CacheTypeMetrics;
	aggregate: AggregatedCacheMetrics;
}

// =============================================================================
// Research Costs Types
// =============================================================================

export interface ResearchCostItem {
	provider: string;
	amount_usd: number;
	query_count: number;
}

export interface ResearchCostsByPeriod {
	today: number;
	week: number;
	month: number;
	all_time: number;
}

export interface DailyResearchCost {
	date: string;
	brave: number;
	tavily: number;
	total: number;
}

export interface ResearchCostsResponse {
	brave: ResearchCostItem;
	tavily: ResearchCostItem;
	total_usd: number;
	total_queries: number;
	by_period: ResearchCostsByPeriod;
	daily_trend: DailyResearchCost[];
}

// =============================================================================
// Cost Aggregations Types
// =============================================================================

export interface CategoryCostAggregation {
	category: string;
	total_cost: number;
	avg_per_meeting: number | null;
	avg_per_user: number | null;
	meeting_count: number;
	user_count: number;
}

export interface CostAggregationsResponse {
	categories: CategoryCostAggregation[];
	overall: CategoryCostAggregation;
	period_start: string;
	period_end: string;
}

// =============================================================================
// Admin Email Types
// =============================================================================

export type EmailTemplateType = 'welcome' | 'custom';

export interface SendEmailRequest {
	template_type: EmailTemplateType;
	subject?: string;
	body?: string;
}

export interface SendEmailResponse {
	user_id: string;
	email: string;
	template_type: string;
	subject: string;
	sent: boolean;
	message: string;
}

// =============================================================================
// Internal Costs Types
// =============================================================================

export interface InternalCostItem {
	provider: string;
	prompt_type: string | null;
	total_cost: number;
	request_count: number;
	input_tokens: number;
	output_tokens: number;
}

export interface FeatureCostItem {
	feature: string;
	provider: string;
	total_cost: number;
	request_count: number;
	input_tokens: number;
	output_tokens: number;
	user_count: number;
}

export interface InternalCostsByPeriod {
	today: number;
	week: number;
	month: number;
	all_time: number;
}

export interface InternalCostsResponse {
	seo: InternalCostItem[];
	system: InternalCostItem[];
	data_analysis: FeatureCostItem[];
	mentor_chat: FeatureCostItem[];
	by_period: InternalCostsByPeriod;
	total_usd: number;
	total_requests: number;
}

// =============================================================================
// Cost Insight Drill-Down Types
// =============================================================================

export interface CacheEffectivenessBucket {
	bucket_label: string;
	bucket_min: number;
	bucket_max: number;
	session_count: number;
	avg_cost: number;
	total_cost: number;
	total_saved: number;
	avg_optimization_savings: number;
}

export interface CacheEffectivenessResponse {
	buckets: CacheEffectivenessBucket[];
	overall_hit_rate: number;
	total_sessions: number;
	total_cost: number;
	total_saved: number;
	period: string;
	min_sample_warning: string | null;
}

export interface ModelImpactItem {
	model_name: string;
	model_display: string;
	request_count: number;
	total_cost: number;
	avg_cost_per_request: number;
	cache_hit_rate: number;
	total_tokens: number;
}

export interface ModelImpactResponse {
	models: ModelImpactItem[];
	total_cost: number;
	total_requests: number;
	cost_if_all_opus: number;
	cost_if_all_haiku: number;
	savings_from_model_mix: number;
	period: string;
}

export interface FeatureEfficiencyItem {
	feature: string;
	request_count: number;
	total_cost: number;
	avg_cost: number;
	cache_hit_rate: number;
	unique_sessions: number;
	cost_per_session: number;
}

export interface FeatureEfficiencyResponse {
	features: FeatureEfficiencyItem[];
	total_cost: number;
	total_requests: number;
	period: string;
}

export interface TuningRecommendation {
	area: string;
	current_value: string;
	recommended_value: string;
	impact_description: string;
	estimated_savings_usd: number | null;
	confidence: string;
}

export interface TuningRecommendationsResponse {
	recommendations: TuningRecommendation[];
	analysis_period_days: number;
	data_quality: string;
}

export interface QualityIndicatorsResponse {
	overall_cache_hit_rate: number;
	session_continuation_rate: number;
	correlation_score: number | null;
	sample_size: number;
	cached_continuation_rate: number | null;
	uncached_continuation_rate: number | null;
	quality_assessment: string;
	period: string;
}

// =============================================================================
// Billing Product & Price Types
// =============================================================================

export interface BillingPrice {
	id: string;
	product_id: string;
	amount_cents: number;
	currency: string;
	interval: string | null;
	stripe_price_id: string | null;
	stripe_product_id: string | null;
	stripe_synced_at: string | null;
	active: boolean;
}

export interface BillingProduct {
	id: string;
	slug: string;
	name: string;
	description: string | null;
	type: 'subscription' | 'one_time';
	meetings_monthly: number;
	datasets_total: number;
	mentor_daily: number;
	api_daily: number;
	features: Record<string, boolean>;
	display_order: number;
	highlighted: boolean;
	active: boolean;
	prices: BillingPrice[];
	sync_status: 'synced' | 'out_of_sync' | 'not_synced';
}

export interface BillingConfigResponse {
	products: BillingProduct[];
	last_sync: string | null;
}

export interface ProductCreate {
	slug: string;
	name: string;
	description?: string;
	type: 'subscription' | 'one_time';
	meetings_monthly?: number;
	datasets_total?: number;
	mentor_daily?: number;
	api_daily?: number;
	features?: Record<string, boolean>;
	display_order?: number;
	highlighted?: boolean;
}

export interface ProductUpdate {
	name?: string;
	description?: string;
	meetings_monthly?: number;
	datasets_total?: number;
	mentor_daily?: number;
	api_daily?: number;
	features?: Record<string, boolean>;
	display_order?: number;
	highlighted?: boolean;
	active?: boolean;
}

export interface PriceCreate {
	product_id: string;
	amount_cents: number;
	currency?: string;
	interval?: 'month' | 'year' | null;
}

export interface PriceUpdate {
	amount_cents?: number;
	active?: boolean;
}

export interface SyncResult {
	success: boolean;
	synced_products: number;
	synced_prices: number;
	errors: string[];
}

export interface SyncStatus {
	total_products: number;
	synced: number;
	out_of_sync: number;
	not_synced: number;
	all_synced: boolean;
}

export interface StripeConfigStatus {
	configured: boolean;
	mode: 'test' | 'live' | null;
	error: string | null;
}

// =============================================================================
// SEO Access Types
// =============================================================================

export interface SeoAccessResponse {
	user_id: string;
	has_seo_access: boolean;
	granted_at: string | null;
	via_promotion: boolean;
	message: string;
}

// =============================================================================
// Published Decisions Types
// =============================================================================

export const DECISION_CATEGORIES = [
	'hiring',
	'pricing',
	'fundraising',
	'marketing',
	'strategy',
	'product',
	'operations',
	'growth'
] as const;

export type DecisionCategory = (typeof DECISION_CATEGORIES)[number];

export interface FounderContext {
	stage?: string;
	constraints?: string[];
	situation?: string;
}

export interface ExpertPerspective {
	persona_name: string;
	persona_code?: string;
	quote: string;
}

export interface FAQ {
	question: string;
	answer: string;
}

export interface Decision {
	id: string;
	session_id?: string;
	category: DecisionCategory;
	slug: string;
	title: string;
	meta_description?: string;
	founder_context?: FounderContext;
	expert_perspectives?: ExpertPerspective[];
	synthesis?: string;
	faqs?: FAQ[];
	related_decision_ids?: string[];
	status: 'draft' | 'published';
	published_at?: string;
	created_at: string;
	updated_at: string;
	view_count: number;
	click_through_count: number;
}

export interface DecisionListResponse {
	decisions: Decision[];
	total: number;
}

export interface DecisionCreate {
	title: string;
	category: DecisionCategory;
	founder_context: FounderContext;
	session_id?: string;
	meta_description?: string;
	expert_perspectives?: ExpertPerspective[];
	synthesis?: string;
	faqs?: FAQ[];
}

export interface DecisionUpdate {
	title?: string;
	category?: DecisionCategory;
	slug?: string;
	meta_description?: string;
	founder_context?: FounderContext;
	expert_perspectives?: ExpertPerspective[];
	synthesis?: string;
	faqs?: FAQ[];
	related_decision_ids?: string[];
	status?: 'draft' | 'published';
}

export interface DecisionGenerateRequest {
	question: string;
	category: DecisionCategory;
	founder_context: FounderContext;
}

export interface CategoryWithCount {
	category: DecisionCategory;
	count: number;
}

export interface CategoriesResponse {
	categories: CategoryWithCount[];
}

// =============================================================================
// Topic Proposer Types
// =============================================================================

export interface TopicProposal {
	title: string;
	rationale: string;
	suggested_keywords: string[];
	source: 'chatgpt-seo-seed' | 'positioning-gap' | 'llm-generated';
}

export interface TopicProposalsResponse {
	topics: TopicProposal[];
}

export const adminApi = new AdminApiClient();
