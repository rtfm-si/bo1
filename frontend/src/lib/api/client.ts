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

		try {
			const response = await fetch(url, {
				...options,
				credentials: 'include', // Send httpOnly cookies automatically
				headers: {
					'Content-Type': 'application/json',
					...options?.headers
				}
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
}

/**
 * Singleton API client instance
 */
export const apiClient = new ApiClient();
