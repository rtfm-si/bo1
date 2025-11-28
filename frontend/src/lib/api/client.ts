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
	UserContext
} from './types';

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
	private async fetch<T>(
		endpoint: string,
		options?: RequestInit
	): Promise<T> {
		const url = `${this.baseUrl}${endpoint}`;

		// For admin endpoints, add X-Admin-Key header if available
		const headers: Record<string, string> = {
			'Content-Type': 'application/json'
		};

		// Merge in any additional headers from options
		if (options?.headers) {
			const optHeaders = options.headers;
			if (optHeaders instanceof Headers) {
				optHeaders.forEach((value, key) => {
					headers[key] = value;
				});
			} else if (Array.isArray(optHeaders)) {
				optHeaders.forEach(([key, value]) => {
					headers[key] = value;
				});
			} else {
				Object.assign(headers, optHeaders);
			}
		}

		// Add admin key for admin endpoints
		if (endpoint.startsWith('/api/admin/')) {
			const adminKey = env.PUBLIC_ADMIN_API_KEY;
			if (adminKey) {
				headers['X-Admin-Key'] = adminKey;
			}
		}

		try {
			const response = await fetch(url, {
				...options,
				credentials: 'include', // Send httpOnly cookies automatically
				headers
			});

			// Handle non-2xx responses
			if (!response.ok) {
				let error: ApiError;
				try {
					error = await response.json();
				} catch {
					error = { detail: response.statusText, status: response.status };
				}

				throw new ApiClientError(
					error.detail || 'Unknown error',
					response.status,
					error
				);
			}

			// Handle 204 No Content
			if (response.status === 204) {
				return {} as T;
			}

			return await response.json();
		} catch (error) {
			if (error instanceof ApiClientError) {
				throw error;
			}

			// Network error or other unexpected error
			throw new ApiClientError(
				error instanceof Error ? error.message : 'Network error',
				undefined,
				error
			);
		}
	}

	/**
	 * Health Endpoints
	 */

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

	/**
	 * Session Endpoints
	 */

	async createSession(request: CreateSessionRequest): Promise<SessionResponse> {
		return this.fetch<SessionResponse>('/api/v1/sessions', {
			method: 'POST',
			body: JSON.stringify(request)
		});
	}

	async listSessions(params?: {
		status?: string;
		limit?: number;
		offset?: number;
	}): Promise<SessionListResponse> {
		const searchParams = new URLSearchParams();
		if (params?.status) searchParams.set('status', params.status);
		if (params?.limit) searchParams.set('limit', params.limit.toString());
		if (params?.offset) searchParams.set('offset', params.offset.toString());

		const query = searchParams.toString();
		const endpoint = query ? `/api/v1/sessions?${query}` : '/api/v1/sessions';

		return this.fetch<SessionListResponse>(endpoint);
	}

	async getSession(sessionId: string): Promise<SessionDetailResponse> {
		return this.fetch<SessionDetailResponse>(`/api/v1/sessions/${sessionId}`);
	}

	async getSessionEvents(sessionId: string): Promise<{ session_id: string; events: any[]; count: number }> {
		return this.fetch<{ session_id: string; events: any[]; count: number }>(`/api/v1/sessions/${sessionId}/events`);
	}

	async deleteSession(sessionId: string): Promise<SessionResponse> {
		return this.fetch<SessionResponse>(`/api/v1/sessions/${sessionId}`, {
			method: 'DELETE'
		});
	}

	/**
	 * Control Endpoints
	 */

	async startDeliberation(sessionId: string): Promise<ControlResponse> {
		return this.fetch<ControlResponse>(`/api/v1/sessions/${sessionId}/start`, {
			method: 'POST'
		});
	}

	async pauseDeliberation(sessionId: string): Promise<ControlResponse> {
		return this.fetch<ControlResponse>(`/api/v1/sessions/${sessionId}/pause`, {
			method: 'POST'
		});
	}

	async resumeDeliberation(sessionId: string): Promise<ControlResponse> {
		return this.fetch<ControlResponse>(`/api/v1/sessions/${sessionId}/resume`, {
			method: 'POST'
		});
	}

	async killDeliberation(sessionId: string, reason?: string): Promise<ControlResponse> {
		return this.fetch<ControlResponse>(`/api/v1/sessions/${sessionId}/kill`, {
			method: 'POST',
			body: JSON.stringify({ reason: reason || 'User requested termination' })
		});
	}

	/**
	 * Context Endpoints
	 */

	async getUserContext(): Promise<UserContextResponse> {
		return this.fetch<UserContextResponse>('/api/v1/context');
	}

	async updateUserContext(context: UserContext): Promise<{ status: string }> {
		return this.fetch<{ status: string }>('/api/v1/context', {
			method: 'PUT',
			body: JSON.stringify(context)
		});
	}

	async deleteUserContext(): Promise<{ status: string }> {
		return this.fetch<{ status: string }>('/api/v1/context', {
			method: 'DELETE'
		});
	}

	async submitClarification(
		sessionId: string,
		answer: string
	): Promise<ControlResponse> {
		return this.fetch<ControlResponse>(`/api/v1/sessions/${sessionId}/clarify`, {
			method: 'POST',
			body: JSON.stringify({ answer })
		});
	}

	/**
	 * Task Extraction Endpoint
	 */

	async extractTasks(sessionId: string): Promise<{
		tasks: Array<{
			id: string;
			description: string;
			category: string;
			priority: string;
			suggested_completion_date: string | null;
			dependencies: string[];
			source_section: string;
			confidence: number;
		}>;
		total_tasks: number;
		extraction_confidence: number;
		synthesis_sections_analyzed: string[];
	}> {
		return this.fetch(`/api/v1/sessions/${sessionId}/extract-tasks`, {
			method: 'POST'
		});
	}

	/**
	 * Admin Endpoints
	 */

	async listUsers(params?: { page?: number; per_page?: number; email?: string }): Promise<{
		total_count: number;
		users: Array<{
			user_id: string;
			email: string;
			auth_provider: string;
			subscription_tier: string;
			is_admin: boolean;
			total_meetings: number;
			total_cost: number | null;
			last_meeting_at: string | null;
			last_meeting_id: string | null;
			created_at: string;
			updated_at: string;
		}>;
		page: number;
		per_page: number;
	}> {
		const searchParams = new URLSearchParams();
		if (params?.page) searchParams.set('page', params.page.toString());
		if (params?.per_page) searchParams.set('per_page', params.per_page.toString());
		if (params?.email) searchParams.set('email', params.email);

		const query = searchParams.toString();
		const endpoint = query ? `/api/admin/users?${query}` : '/api/admin/users';

		return this.fetch(endpoint);
	}

	async getUser(userId: string): Promise<{
		user_id: string;
		email: string;
		auth_provider: string;
		subscription_tier: string;
		is_admin: boolean;
		total_meetings: number;
		total_cost: number | null;
		last_meeting_at: string | null;
		last_meeting_id: string | null;
		created_at: string;
		updated_at: string;
	}> {
		return this.fetch(`/api/admin/users/${userId}`);
	}

	async updateUser(userId: string, data: { subscription_tier?: string; is_admin?: boolean }): Promise<{
		user_id: string;
		email: string;
		auth_provider: string;
		subscription_tier: string;
		is_admin: boolean;
		total_meetings: number;
		total_cost: number | null;
		last_meeting_at: string | null;
		last_meeting_id: string | null;
		created_at: string;
		updated_at: string;
	}> {
		return this.fetch(`/api/admin/users/${userId}`, {
			method: 'PATCH',
			body: JSON.stringify(data)
		});
	}

	async listWhitelist(): Promise<{
		total_count: number;
		emails: Array<{
			id: string;
			email: string;
			added_by: string | null;
			notes: string | null;
			created_at: string;
		}>;
	}> {
		return this.fetch('/api/admin/beta-whitelist');
	}

	async addToWhitelist(data: { email: string; notes?: string }): Promise<{
		id: string;
		email: string;
		added_by: string | null;
		notes: string | null;
		created_at: string;
	}> {
		return this.fetch('/api/admin/beta-whitelist', {
			method: 'POST',
			body: JSON.stringify(data)
		});
	}

	async removeFromWhitelist(email: string): Promise<{
		session_id: string;
		action: string;
		status: string;
		message: string;
	}> {
		return this.fetch(`/api/admin/beta-whitelist/${encodeURIComponent(email)}`, {
			method: 'DELETE'
		});
	}
}

/**
 * Singleton API client instance
 */
export const apiClient = new ApiClient();
