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
}

export const adminApi = new AdminApiClient();
