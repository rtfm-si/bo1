/**
 * Report Data Extractor Utilities
 *
 * Utilities for extracting and transforming event data for reports.
 * Extracted from pdf-report-generator.ts for reusability and testability.
 */

import type { SSEEvent } from '$lib/api/sse-events';

// Type definitions for event data
interface PersonaSelectedData {
	persona?: {
		name?: string;
		display_name?: string;
		archetype?: string;
		domain_expertise?: string[];
	};
	rationale?: string;
}

interface SynthesisData {
	synthesis?: string;
}

interface DecompositionData {
	sub_problems?: Array<{ goal?: string }>;
}

interface ContributionData {
	persona_name?: string;
	round?: number;
}

/**
 * Expert information extracted from persona_selected events
 */
export interface ExpertInfo {
	name: string;
	displayName: string;
	archetype: string;
	expertise: string[];
	rationale: string;
}

/**
 * Metrics computed from events
 */
export interface ReportMetrics {
	expertCount: number;
	totalRounds: number;
	contributionCount: number;
	durationMins: number;
}

/**
 * Extract expert information from persona_selected events.
 *
 * @param events - Array of SSE events
 * @returns Array of expert info objects
 */
export function extractExperts(events: SSEEvent[]): ExpertInfo[] {
	const expertEvents = events.filter((e) => e.event_type === 'persona_selected');

	return expertEvents.map((e) => {
		const data = e.data as PersonaSelectedData;
		return {
			name: data.persona?.name || data.persona?.display_name || 'Expert',
			displayName: data.persona?.display_name || data.persona?.name || 'Expert',
			archetype: data.persona?.archetype || '',
			expertise: data.persona?.domain_expertise || [],
			rationale: data.rationale || ''
		};
	});
}

/**
 * Count contributions per expert (by display name).
 *
 * @param events - Array of SSE events
 * @returns Map of display name to contribution count
 */
export function countContributionsByExpert(events: SSEEvent[]): Map<string, number> {
	const contributions = events.filter((e) => e.event_type === 'contribution');
	const contributionsByDisplayName = new Map<string, number>();

	contributions.forEach((c) => {
		const data = c.data as ContributionData;
		const displayName = data.persona_name || 'Unknown';
		contributionsByDisplayName.set(displayName, (contributionsByDisplayName.get(displayName) || 0) + 1);
	});

	return contributionsByDisplayName;
}

/**
 * Get total contribution count from events.
 *
 * @param events - Array of SSE events
 * @returns Total number of contributions
 */
export function getContributionCount(events: SSEEvent[]): number {
	return events.filter((e) => e.event_type === 'contribution').length;
}

/**
 * Calculate total rounds from events.
 *
 * Tries event-based counting first (round_started events),
 * falls back to max round number from contributions.
 *
 * @param events - Array of SSE events
 * @returns Total number of rounds
 */
export function calculateRounds(events: SSEEvent[]): number {
	// Try event-based first
	const roundEvents = events.filter(
		(e) => e.event_type === 'round_started' || e.event_type === 'initial_round_started'
	);

	if (roundEvents.length > 0) {
		return roundEvents.length;
	}

	// Fallback: calculate max round from contributions
	const contributions = events.filter((e) => e.event_type === 'contribution');
	if (contributions.length > 0) {
		const roundNumbers = contributions.map((c) => {
			const data = c.data as ContributionData;
			return data.round || 0;
		});
		return Math.max(...roundNumbers, 0);
	}

	return 0;
}

/**
 * Extract sub-problems from decomposition event.
 *
 * @param events - Array of SSE events
 * @returns Array of sub-problem objects
 */
export function extractSubProblems(events: SSEEvent[]): Array<{ goal?: string }> {
	const decompositionEvent = events.find((e) => e.event_type === 'decomposition_complete');
	const data = decompositionEvent?.data as DecompositionData | undefined;
	return data?.sub_problems || [];
}

/**
 * Extract synthesis content from meta_synthesis or synthesis events.
 *
 * Prefers meta_synthesis_complete over synthesis_complete.
 *
 * @param events - Array of SSE events
 * @returns Synthesis markdown string
 */
export function extractSynthesis(events: SSEEvent[]): string {
	const metaSynthesisEvent = events.find((e) => e.event_type === 'meta_synthesis_complete');
	const synthesisCompleteEvent = events.find((e) => e.event_type === 'synthesis_complete');

	const metaData = metaSynthesisEvent?.data as SynthesisData | undefined;
	const synthData = synthesisCompleteEvent?.data as SynthesisData | undefined;

	return metaData?.synthesis || synthData?.synthesis || '';
}

/**
 * Calculate meeting duration in minutes.
 *
 * @param sessionCreatedAt - Session creation timestamp (ISO string)
 * @param events - Array of SSE events (uses last event timestamp as end time)
 * @returns Duration in minutes
 */
export function calculateDuration(sessionCreatedAt: string, events: SSEEvent[]): number {
	const startTime = new Date(sessionCreatedAt).getTime();
	const endTime =
		events.length > 0 ? new Date(events[events.length - 1].timestamp).getTime() : Date.now();

	return Math.round((endTime - startTime) / 60000);
}

/**
 * Format date for report display.
 *
 * @param date - Date to format (defaults to now)
 * @returns Formatted date string (e.g., "December 2, 2025")
 */
export function formatReportDate(date: Date = new Date()): string {
	return date.toLocaleDateString('en-US', {
		year: 'numeric',
		month: 'long',
		day: 'numeric'
	});
}

/**
 * Get initials from a name.
 *
 * @param name - Full name
 * @returns Initials (up to 2 characters)
 */
export function getInitials(name: string): string {
	return name
		.split(' ')
		.map((n) => n[0])
		.join('')
		.substring(0, 2)
		.toUpperCase();
}

/**
 * Extract all report metrics from events.
 *
 * @param events - Array of SSE events
 * @param sessionCreatedAt - Session creation timestamp
 * @returns Report metrics object
 */
export function extractReportMetrics(events: SSEEvent[], sessionCreatedAt: string): ReportMetrics {
	const experts = extractExperts(events);

	return {
		expertCount: experts.length,
		totalRounds: calculateRounds(events),
		contributionCount: getContributionCount(events),
		durationMins: calculateDuration(sessionCreatedAt, events)
	};
}
