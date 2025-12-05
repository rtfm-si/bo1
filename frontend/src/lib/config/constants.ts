/**
 * Frontend Configuration Constants
 *
 * Centralizes magic numbers and configuration values used across the frontend.
 * Import from '$lib/config/constants' instead of hardcoding values.
 */

// ============================================================================
// MEETING PAGE CONFIGURATION
// ============================================================================

/**
 * Debounce delays for event grouping recalculation.
 * Critical events (persona selection, round start) use shorter delay.
 */
export const DEBOUNCE_CRITICAL_MS = 50;
export const DEBOUNCE_NORMAL_MS = 100;

/**
 * Time threshold (ms) before showing "stale" warning.
 * If no events received for this long, show connectivity warning.
 */
export const STALENESS_THRESHOLD_MS = 8000;

/**
 * Maximum number of cached dynamic components.
 * Used by DynamicEventComponent to limit memory usage.
 */
export const MAX_CACHED_COMPONENTS = 20;

/**
 * Scroll debounce delay for auto-scroll behavior.
 */
export const SCROLL_DEBOUNCE_MS = 300;

/**
 * Event index recalculation debounce delay.
 */
export const EVENT_INDEX_DEBOUNCE_MS = 200;

// ============================================================================
// HIDDEN EVENT TYPES
// ============================================================================

/**
 * Internal event types that should not be displayed in the meeting UI.
 * These are technical/infrastructure events, not user-facing.
 */
export const HIDDEN_EVENT_TYPES = new Set([
	'parallel_round_start',
	'node_start',
	'stream_connected'
]);

// ============================================================================
// SSE CONNECTION CONFIGURATION
// ============================================================================

/**
 * Maximum retry attempts for SSE connection.
 */
export const SSE_MAX_RETRIES = 3;

/**
 * Base delay (ms) for exponential backoff on SSE reconnection.
 */
export const SSE_RETRY_BASE_DELAY_MS = 1000;

/**
 * Maximum delay (ms) for SSE reconnection backoff.
 */
export const SSE_RETRY_MAX_DELAY_MS = 30000;

// ============================================================================
// UI CONFIGURATION
// ============================================================================

/**
 * Default contribution view mode.
 */
export const DEFAULT_CONTRIBUTION_VIEW_MODE: 'simple' | 'full' = 'simple';

/**
 * Animation durations (ms).
 */
export const ANIMATION_DURATION_SHORT = 150;
export const ANIMATION_DURATION_MEDIUM = 300;
export const ANIMATION_DURATION_LONG = 500;

// ============================================================================
// API CONFIGURATION
// ============================================================================

/**
 * Default page size for paginated API requests.
 */
export const DEFAULT_PAGE_SIZE = 10;

/**
 * Maximum page size for paginated API requests.
 */
export const MAX_PAGE_SIZE = 100;

// ============================================================================
// TYPE EXPORTS
// ============================================================================

export type ContributionViewMode = 'simple' | 'full';
export type ConnectionStatus = 'connecting' | 'connected' | 'retrying' | 'error' | 'disconnected';
