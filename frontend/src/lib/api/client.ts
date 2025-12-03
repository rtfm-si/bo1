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
	TaskStatusUpdateRequest
} from './types';

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
}

/**
 * Singleton API client instance
 */
export const apiClient = new ApiClient();
