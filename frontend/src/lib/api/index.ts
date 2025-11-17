/**
 * API Module Exports
 *
 * Barrel export for all API-related modules
 */

// API Client
export { ApiClient, apiClient, ApiClientError } from './client';

// SSE Client
export {
	SSEClient,
	createSSEClient,
	type SSEEventType,
	type SSEEvent,
	type AnySSEEvent,
	type NodeStartEvent,
	type NodeEndEvent,
	type ContributionEvent,
	type FacilitatorDecisionEvent,
	type ConvergenceEvent,
	type CompleteEvent,
	type ErrorEvent,
	type ClarificationRequestedEvent,
	type ClarificationAnsweredEvent,
	type SSEEventHandler,
	type SSEClientOptions
} from './sse';

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
