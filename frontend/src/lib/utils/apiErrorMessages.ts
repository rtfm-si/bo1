/**
 * Centralized mapping from backend ErrorCode to user-friendly messages.
 *
 * Used by:
 * - MeetingError.svelte (error display)
 * - ErrorEvent.svelte (SSE error events)
 * - Toast notifications
 *
 * Maps backend ErrorCode enum values (from bo1/logging/errors.py) to:
 * - User-friendly titles and descriptions
 * - Severity levels for UI styling
 * - Actionable guidance (recovery times, retry suggestions)
 */

export type ErrorSeverity = 'info' | 'warning' | 'error' | 'critical';

export interface ErrorMessage {
	/** Short user-friendly title */
	title: string;
	/** Longer description explaining the issue */
	description: string;
	/** Severity level for UI styling */
	severity: ErrorSeverity;
	/** Actionable guidance for the user */
	action?: string;
	/** Estimated recovery time in seconds (if applicable) */
	recoveryTimeSeconds?: number;
	/** Whether the error is transient and retrying might help */
	isTransient: boolean;
}

/**
 * ErrorCode values from backend (bo1/logging/errors.py).
 * These are the error_code values that may appear in SSE error events.
 */
export type ErrorCode =
	// LLM errors
	| 'LLM_API_ERROR'
	| 'LLM_RATE_LIMIT'
	| 'LLM_TIMEOUT'
	| 'LLM_RETRIES_EXHAUSTED'
	| 'LLM_PARSE_FAILED'
	| 'LLM_CACHE_ERROR'
	| 'LLM_CIRCUIT_OPEN'
	| 'LLM_EMBEDDING_FAILED'
	// Database errors
	| 'DB_CONNECTION_ERROR'
	| 'DB_QUERY_ERROR'
	| 'DB_WRITE_ERROR'
	| 'DB_PARTITION_ERROR'
	// Redis errors
	| 'REDIS_CONNECTION_ERROR'
	| 'REDIS_READ_ERROR'
	| 'REDIS_WRITE_ERROR'
	// Service errors
	| 'SERVICE_UNAVAILABLE'
	| 'SERVICE_CONFIG_ERROR'
	| 'CONFIG_ERROR'
	| 'SERVICE_DEPENDENCY_ERROR'
	| 'SERVICE_EXECUTION_ERROR'
	// API errors
	| 'API_REQUEST_ERROR'
	| 'API_SSE_ERROR'
	| 'API_SESSION_ERROR'
	| 'API_RATE_LIMIT';

/**
 * Mapping of backend ErrorCode to user-friendly messages.
 *
 * Keys match ErrorCode enum values from bo1/logging/errors.py.
 * Keep in sync with backend when adding new error codes.
 */
const errorMessages: Record<ErrorCode, ErrorMessage> = {
	// LLM/AI Provider Errors
	LLM_API_ERROR: {
		title: 'AI Service Temporarily Unavailable',
		description: 'Our AI provider is experiencing issues. We\'re automatically retrying.',
		severity: 'warning',
		action: 'Please wait a moment. If this persists, try starting a new meeting.',
		recoveryTimeSeconds: 30,
		isTransient: true
	},
	LLM_RATE_LIMIT: {
		title: 'High Demand',
		description: 'We\'re experiencing high demand. Your request is queued.',
		severity: 'info',
		action: 'Please wait ~30 seconds. Your meeting will continue automatically.',
		recoveryTimeSeconds: 30,
		isTransient: true
	},
	LLM_TIMEOUT: {
		title: 'Request Timed Out',
		description: 'The AI is taking longer than expected to respond.',
		severity: 'warning',
		action: 'We\'re retrying with a longer timeout. Please wait.',
		recoveryTimeSeconds: 60,
		isTransient: true
	},
	LLM_RETRIES_EXHAUSTED: {
		title: 'Unable to Complete Request',
		description: 'After multiple attempts, we couldn\'t complete this request.',
		severity: 'error',
		action: 'Please try starting a new meeting. If this persists, contact support.',
		isTransient: false
	},
	LLM_PARSE_FAILED: {
		title: 'Unexpected AI Response',
		description: 'The AI returned an unexpected response format.',
		severity: 'warning',
		action: 'We\'re retrying the request.',
		recoveryTimeSeconds: 15,
		isTransient: true
	},
	LLM_CACHE_ERROR: {
		title: 'Cache Issue',
		description: 'A caching issue occurred. Using live AI response instead.',
		severity: 'info',
		action: 'Your meeting will continue normally.',
		isTransient: true
	},
	LLM_CIRCUIT_OPEN: {
		title: 'Switching to Backup Provider',
		description: 'Our primary AI is temporarily unavailable. Switching to backup.',
		severity: 'info',
		action: 'Please wait ~30 seconds while we switch providers.',
		recoveryTimeSeconds: 30,
		isTransient: true
	},
	LLM_EMBEDDING_FAILED: {
		title: 'Research Processing Issue',
		description: 'Unable to process research results. Continuing with available data.',
		severity: 'warning',
		action: 'Your meeting will continue with slightly reduced research context.',
		isTransient: true
	},

	// Database Errors
	DB_CONNECTION_ERROR: {
		title: 'Database Connection Issue',
		description: 'Temporarily unable to connect to our database.',
		severity: 'error',
		action: 'Please wait a moment and try again.',
		recoveryTimeSeconds: 10,
		isTransient: true
	},
	DB_QUERY_ERROR: {
		title: 'Database Query Issue',
		description: 'A database operation failed.',
		severity: 'error',
		action: 'Please try again. If this persists, contact support.',
		isTransient: true
	},
	DB_WRITE_ERROR: {
		title: 'Unable to Save',
		description: 'We couldn\'t save your data. Your meeting results may not be preserved.',
		severity: 'error',
		action: 'Please try again or export your results manually.',
		isTransient: true
	},
	DB_PARTITION_ERROR: {
		title: 'Database Maintenance',
		description: 'A database maintenance operation is in progress.',
		severity: 'warning',
		action: 'Please wait a moment and try again.',
		recoveryTimeSeconds: 30,
		isTransient: true
	},

	// Redis Errors
	REDIS_CONNECTION_ERROR: {
		title: 'Real-time Updates Interrupted',
		description: 'Connection to real-time updates service was lost.',
		severity: 'warning',
		action: 'Reconnecting automatically. Your meeting data is safe.',
		recoveryTimeSeconds: 5,
		isTransient: true
	},
	REDIS_READ_ERROR: {
		title: 'Temporary Data Issue',
		description: 'Unable to read temporary data.',
		severity: 'warning',
		action: 'Falling back to database. Your meeting will continue.',
		isTransient: true
	},
	REDIS_WRITE_ERROR: {
		title: 'Real-time Sync Issue',
		description: 'Unable to sync real-time data.',
		severity: 'warning',
		action: 'Data will be synced when connection is restored.',
		isTransient: true
	},

	// Service Errors
	SERVICE_UNAVAILABLE: {
		title: 'Service Unavailable',
		description: 'A required service is temporarily unavailable.',
		severity: 'error',
		action: 'Please try again in a few minutes.',
		recoveryTimeSeconds: 60,
		isTransient: true
	},
	SERVICE_CONFIG_ERROR: {
		title: 'Configuration Issue',
		description: 'There\'s a configuration issue with your request.',
		severity: 'error',
		action: 'Please contact support if this persists.',
		isTransient: false
	},
	CONFIG_ERROR: {
		title: 'Configuration Issue',
		description: 'A configuration issue prevented this operation.',
		severity: 'error',
		action: 'Please contact support.',
		isTransient: false
	},
	SERVICE_DEPENDENCY_ERROR: {
		title: 'External Service Issue',
		description: 'One of our external services is experiencing issues.',
		severity: 'warning',
		action: 'We\'re working on it. Please try again shortly.',
		recoveryTimeSeconds: 60,
		isTransient: true
	},
	SERVICE_EXECUTION_ERROR: {
		title: 'Processing Error',
		description: 'An error occurred while processing your request.',
		severity: 'error',
		action: 'Please try again. If this persists, contact support.',
		isTransient: true
	},

	// API Errors
	API_REQUEST_ERROR: {
		title: 'Request Failed',
		description: 'Your request could not be processed.',
		severity: 'error',
		action: 'Please try again.',
		isTransient: true
	},
	API_SSE_ERROR: {
		title: 'Stream Interrupted',
		description: 'The event stream was interrupted.',
		severity: 'warning',
		action: 'Reconnecting automatically...',
		recoveryTimeSeconds: 5,
		isTransient: true
	},
	API_SESSION_ERROR: {
		title: 'Session Error',
		description: 'There was an issue with your meeting session.',
		severity: 'error',
		action: 'Please try starting a new meeting.',
		isTransient: false
	},
	API_RATE_LIMIT: {
		title: 'Too Many Requests',
		description: 'You\'ve made too many requests. Please slow down.',
		severity: 'warning',
		action: 'Wait a moment before trying again.',
		recoveryTimeSeconds: 60,
		isTransient: true
	}
};

/**
 * Default error message for unknown error codes.
 */
const defaultErrorMessage: ErrorMessage = {
	title: 'Something Went Wrong',
	description: 'An unexpected error occurred.',
	severity: 'error',
	action: 'Please try again. If this persists, contact support.',
	isTransient: true
};

/**
 * Get user-friendly error message for a backend error code.
 *
 * @param errorCode - The error_code from backend (e.g., 'LLM_CIRCUIT_OPEN')
 * @returns ErrorMessage with user-friendly title, description, and guidance
 *
 * @example
 * ```ts
 * const msg = getErrorMessage('LLM_CIRCUIT_OPEN');
 * // { title: 'Switching to Backup Provider', ... }
 * ```
 */
export function getErrorMessage(errorCode: string | undefined | null): ErrorMessage {
	if (!errorCode) {
		return defaultErrorMessage;
	}
	return errorMessages[errorCode as ErrorCode] ?? defaultErrorMessage;
}

/**
 * Check if an error code indicates a transient/recoverable error.
 *
 * @param errorCode - The error_code from backend
 * @returns true if the error is likely transient and retrying may help
 */
export function isTransientError(errorCode: string | undefined | null): boolean {
	return getErrorMessage(errorCode).isTransient;
}

/**
 * Get estimated recovery time for an error.
 *
 * @param errorCode - The error_code from backend
 * @returns Recovery time in seconds, or undefined if not applicable
 */
export function getRecoveryTime(errorCode: string | undefined | null): number | undefined {
	return getErrorMessage(errorCode).recoveryTimeSeconds;
}

/**
 * Format recovery time as human-readable string.
 *
 * @param seconds - Recovery time in seconds
 * @returns Formatted string like "~30 seconds" or "~1 minute"
 */
export function formatRecoveryTime(seconds: number | undefined): string {
	if (!seconds) return '';
	if (seconds < 60) return `~${seconds} seconds`;
	const minutes = Math.round(seconds / 60);
	return minutes === 1 ? '~1 minute' : `~${minutes} minutes`;
}

/**
 * Get CSS class suffix for error severity.
 *
 * @param severity - Error severity level
 * @returns CSS class suffix (e.g., 'info', 'warning', 'error')
 */
export function getSeverityClass(severity: ErrorSeverity): string {
	return severity;
}

/**
 * Progress message for provider fallback scenario.
 * Used when circuit breaker triggers automatic provider switch.
 */
export const PROVIDER_FALLBACK_MESSAGE = {
	title: 'Switching AI Providers',
	description: 'Our primary AI provider is temporarily unavailable. Automatically switching to backup.',
	icon: '🔄',
	estimatedTime: '~30 seconds'
} as const;

/**
 * Progress message for retry scenario.
 * Used when system is automatically retrying a failed request.
 */
export const RETRY_IN_PROGRESS_MESSAGE = {
	title: 'Retrying Request',
	description: 'Automatically retrying your request...',
	icon: '🔁',
	estimatedTime: '~15 seconds'
} as const;
