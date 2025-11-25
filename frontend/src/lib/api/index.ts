/**
 * API Module Exports
 *
 * Barrel export for all API-related modules
 */

// API Client
export { ApiClient, apiClient, ApiClientError } from './client';

// SSE Event Types (moved to sse-events.ts)
// Import SSEClient from $lib/utils/sse instead
export type { DeliberationEvent } from './sse-events';

// Types
export type {
	CreateSessionRequest,
	SessionResponse,
	SessionDetailResponse,
	SessionListResponse,
	ControlResponse,
	HealthResponse,
	ApiError,
	UserContext,
	UserContextResponse
} from './types';
