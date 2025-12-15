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
}

export interface EmbeddingSampleResponse {
	points: EmbeddingPoint[];
	method: 'pca' | 'umap';
	total_available: number;
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

export const adminApi = new AdminApiClient();
