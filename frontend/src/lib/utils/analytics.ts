/**
 * Analytics utility for Umami event tracking.
 *
 * Provides type-safe event tracking that integrates with self-hosted Umami.
 * Events are only tracked in production (when umami script is loaded).
 */

// Declare umami global type
declare global {
	interface Window {
		umami?: {
			track: (eventName: string, eventData?: Record<string, unknown>) => void;
		};
	}
}

/**
 * Pre-defined analytics events for consistent tracking.
 */
export const AnalyticsEvents = {
	// Onboarding events
	ONBOARDING_STARTED: 'onboarding_started',
	ONBOARDING_COMPLETED: 'onboarding_completed',
	ONBOARDING_SKIPPED: 'onboarding_skipped',

	// Business context events
	CONTEXT_SETUP_STARTED: 'context_setup_started',
	CONTEXT_SETUP_COMPLETED: 'context_setup_completed',
	CONTEXT_ENRICHED: 'context_enriched',
	CONTEXT_UPDATED: 'context_updated',

	// Tour events
	TOUR_STARTED: 'tour_started',
	TOUR_COMPLETED: 'tour_completed',
	TOUR_STEP_COMPLETED: 'tour_step_completed',
	TOUR_DISMISSED: 'tour_dismissed',

	// Meeting events
	MEETING_STARTED: 'meeting_started',
	MEETING_COMPLETED: 'meeting_completed',
	MEETING_PAUSED: 'meeting_paused',
	MEETING_RESUMED: 'meeting_resumed',

	// Feature usage events
	EXPERT_PANEL_VIEWED: 'expert_panel_viewed',
	RESULTS_VIEWED: 'results_viewed',
	ACTIONS_VIEWED: 'actions_viewed',
	ACTION_STATUS_CHANGED: 'action_status_changed',

	// Navigation events
	PAGE_VIEW: 'page_view',
	CTA_CLICKED: 'cta_clicked'
} as const;

export type AnalyticsEvent = (typeof AnalyticsEvents)[keyof typeof AnalyticsEvents];

/**
 * Track a custom event to Umami.
 *
 * Events are only tracked if Umami script is loaded (production).
 *
 * @param eventName - Name of the event to track
 * @param eventData - Optional data to attach to the event
 */
export function trackEvent(eventName: string, eventData?: Record<string, unknown>): void {
	if (typeof window !== 'undefined' && window.umami) {
		try {
			window.umami.track(eventName, eventData);
		} catch (error) {
			console.warn('Failed to track event:', error);
		}
	}
}

/**
 * Track onboarding start.
 */
export function trackOnboardingStarted(): void {
	trackEvent(AnalyticsEvents.ONBOARDING_STARTED);
}

/**
 * Track onboarding completion.
 *
 * @param data - Completion data
 */
export function trackOnboardingCompleted(data?: { has_context?: boolean }): void {
	trackEvent(AnalyticsEvents.ONBOARDING_COMPLETED, data);
}

/**
 * Track tour step completion.
 *
 * @param step - Step name that was completed
 */
export function trackTourStep(step: string): void {
	trackEvent(AnalyticsEvents.TOUR_STEP_COMPLETED, { step });
}

/**
 * Track context enrichment.
 *
 * @param data - Enrichment data
 */
export function trackContextEnriched(data: { source: string; confidence: string }): void {
	trackEvent(AnalyticsEvents.CONTEXT_ENRICHED, data);
}

/**
 * Track meeting start.
 *
 * @param meetingId - ID of the meeting
 */
export function trackMeetingStarted(meetingId: string): void {
	trackEvent(AnalyticsEvents.MEETING_STARTED, { meeting_id: meetingId });
}

/**
 * Track meeting completion.
 *
 * @param data - Completion data
 */
export function trackMeetingCompleted(data: {
	meeting_id: string;
	duration_seconds?: number;
}): void {
	trackEvent(AnalyticsEvents.MEETING_COMPLETED, data);
}

/**
 * Track CTA click.
 *
 * @param ctaName - Name of the CTA clicked
 * @param location - Location on the page
 */
export function trackCTAClick(ctaName: string, location?: string): void {
	trackEvent(AnalyticsEvents.CTA_CLICKED, { cta: ctaName, location });
}
