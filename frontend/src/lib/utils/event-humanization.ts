/**
 * Event Humanization Utilities
 *
 * Converts technical event names into user-friendly descriptions
 * that explain what's happening in plain language.
 */

import { formatCurrency, type CurrencyCode } from './currency';

// Default currency used when none specified
const DEFAULT_CURRENCY: CurrencyCode = 'GBP';

export const EVENT_TITLES: Record<string, string> = {
	// Session lifecycle
	session_started: "Meeting Started",
	complete: "Meeting Complete",

	// Decomposition phase
	decomposition_started: "Analyzing Your Decision",
	decomposition_complete: "Decision Breakdown Complete",

	// Persona selection phase
	persona_selection_started: "Selecting Expert Advisors",
	persona_selected: "Expert Joined",
	persona_selection_complete: "Board Assembled",

	// Focus area handling
	subproblem_started: "Starting Focus Area",
	subproblem_complete: "Focus Area Complete",

	// Discussion rounds
	initial_round_started: "Initial Discussion Begins",
	round_started: "New Discussion Round",
	contribution: "Expert Perspective",

	// Facilitator actions
	facilitator_decision: "Board Decision",
	moderator_intervention: "Moderator Intervention",

	// Convergence
	convergence: "Measuring Consensus",

	// Voting phase
	voting_started: "Collecting Final Recommendations",
	persona_vote: "Expert Recommendation",
	voting_complete: "Recommendations Complete",

	// Synthesis phase
	synthesis_started: "Synthesizing Insights",
	synthesis_complete: "Recommendation Ready",
	meta_synthesis_started: "Synthesizing Overall Strategy",
	meta_synthesis_complete: "Final Strategy Ready",

	// Cost tracking
	phase_cost_breakdown: "Cost Breakdown",

	// Error handling
	error: "Error Occurred",
	clarification_requested: "Clarification Needed",

	// Internal events (should be hidden by default)
	node_start: "Node Started",
	node_end: "Node Completed",
};

/**
 * Dynamic event descriptions based on event data
 */
export const EVENT_DESCRIPTIONS: Record<string, string | ((data: any) => string)> = {
	// Session lifecycle
	session_started: "The board is reviewing your decision and preparing for deliberation.",
	complete: (data: any) => {
		const rounds = data.total_rounds || 0;
		const contributions = data.total_contributions || 0;
		return `Meeting completed after ${rounds} round${rounds !== 1 ? 's' : ''} with ${contributions} expert contribution${contributions !== 1 ? 's' : ''}.`;
	},

	// Decomposition phase
	decomposition_started: "Breaking down your decision into key focus areas...",
	decomposition_complete: (data: any) => {
		const count = data.count || data.sub_problems?.length || 0;
		return `Identified ${count} key focus area${count !== 1 ? 's' : ''} to address.`;
	},

	// Persona selection phase
	persona_selection_started: "Identifying the best experts for this decision...",
	persona_selected: (data: any) => {
		const name = data.persona?.display_name || data.persona?.name || "Expert";
		return `${name} has joined the board.`;
	},
	persona_selection_complete: (data: any) => {
		const count = data.count || data.personas?.length || 0;
		return `Assembled a board of ${count} expert${count !== 1 ? 's' : ''}.`;
	},

	// Focus area handling
	subproblem_started: (data: any) => {
		const index = (data.sub_problem_index || 0) + 1;
		const total = data.total_sub_problems || 1;
		return `Addressing focus area ${index} of ${total}.`;
	},
	subproblem_complete: (data: any) => {
		const contributions = data.contribution_count || 0;
		return `Resolved with ${contributions} expert contribution${contributions !== 1 ? 's' : ''}.`;
	},

	// Discussion rounds
	initial_round_started: (data: any) => {
		const count = data.experts?.length || 0;
		return `${count} expert${count !== 1 ? 's are' : ' is'} sharing initial perspectives.`;
	},
	round_started: (data: any) => {
		const round = data.round_number || 1;
		return `Round ${round}: Experts are refining their analysis.`;
	},
	contribution: (data: any) => {
		const name = data.persona_name || "Expert";
		const type = data.contribution_type === 'initial' ? 'initial perspective' : 'follow-up analysis';
		return `${name} is sharing their ${type}.`;
	},

	// Facilitator actions
	facilitator_decision: (data: any) => {
		const actionDescriptions: Record<string, string> = {
			continue: "The board continues discussing to refine their perspectives.",
			vote: "The board has reached sufficient clarity and is moving to final recommendations.",
			research: "The board is gathering additional information to inform their analysis.",
			moderator: "A moderator is being brought in to address concerns or balance perspectives.",
			clarify: "The board needs clarification from you to proceed effectively.",
		};
		return actionDescriptions[data.action] || "The board has made a procedural decision.";
	},
	moderator_intervention: (data: any) => {
		const typeDescriptions: Record<string, string> = {
			contrarian: "A contrarian perspective is being introduced to challenge assumptions.",
			balance: "A balanced viewpoint is being added to ensure fair consideration.",
			focus: "The discussion is being refocused on key issues.",
		};
		return typeDescriptions[data.moderator_type] || "A moderator is helping guide the discussion.";
	},

	// Convergence
	convergence: (data: any) => {
		const score = data.score || 0;
		const converged = data.converged;

		if (converged) {
			return "The board has reached strong consensus and is ready to proceed.";
		} else if (score > 0.7) {
			return "The board is reaching strong consensus on key points.";
		} else if (score > 0.5) {
			return "The board is finding common ground on several issues.";
		} else if (score > 0.3) {
			return "The board is exploring different perspectives and approaches.";
		}
		return "The board is in early stages of discussion with diverse viewpoints.";
	},

	// Voting phase
	voting_started: (data: any) => {
		const count = data.count || data.experts?.length || 0;
		return `Collecting final recommendations from ${count} expert${count !== 1 ? 's' : ''}.`;
	},
	persona_vote: (data: any) => {
		const name = data.persona_name || "Expert";
		const confidence = data.confidence || 0;
		return `${name} has provided their recommendation (${Math.round(confidence * 100)}% confidence).`;
	},
	voting_complete: (data: any) => {
		const count = data.recommendations_count || 0;
		const level = data.consensus_level || 'moderate';
		return `Collected ${count} recommendation${count !== 1 ? 's' : ''} with ${level} consensus.`;
	},

	// Synthesis phase
	synthesis_started: "The board is synthesizing expert opinions into actionable recommendations...",
	synthesis_complete: (data: any) => {
		const words = data.word_count || 0;
		return `Generated a comprehensive ${words}-word recommendation.`;
	},
	meta_synthesis_started: "Integrating insights from all sub-problems into a unified strategy...",
	meta_synthesis_complete: (data: any) => {
		const words = data.word_count || 0;
		return `Generated a comprehensive ${words}-word strategic plan.`;
	},

	// Cost tracking (admin-only, filtered in UI)
	// Note: Uses $ as these are API costs in USD; for user-facing costs, pass currency
	phase_cost_breakdown: (data: any) => {
		const total = data.total_cost || 0;
		const currency = data.currency || DEFAULT_CURRENCY;
		return `Meeting cost: ${formatCurrency(total, currency, { decimals: 2 })}`;
	},

	// Error handling
	error: (data: any) => {
		const recoverable = data.recoverable ? "The system will attempt to recover." : "Manual intervention may be required.";
		return `An error occurred: ${data.error || 'Unknown error'}. ${recoverable}`;
	},
	clarification_requested: (data: any) => {
		return `The board needs your input: ${data.question || 'Question not provided'}`;
	},

	// Internal events
	node_start: (data: any) => `Started processing ${data.node || 'unknown node'}`,
	node_end: (data: any) => `Completed processing ${data.node || 'unknown node'}`,
};

/**
 * Get user-friendly title for an event type
 */
export function getEventTitle(eventType: string): string {
	return EVENT_TITLES[eventType] || formatTechnicalEventType(eventType);
}

/**
 * Get user-friendly description for an event
 */
export function getEventDescription(eventType: string, data: any = {}): string {
	const desc = EVENT_DESCRIPTIONS[eventType];

	if (typeof desc === 'function') {
		return desc(data);
	}

	return desc || '';
}

/**
 * Fallback: Format technical event types into readable titles
 */
function formatTechnicalEventType(eventType: string): string {
	return eventType
		.split('_')
		.map(word => word.charAt(0).toUpperCase() + word.slice(1))
		.join(' ');
}

/**
 * Check if an event is considered "internal" (technical, not user-facing)
 */
export function isInternalEvent(eventType: string): boolean {
	const internalEvents = ['node_start', 'node_end'];
	return internalEvents.includes(eventType);
}

/**
 * Get event priority for visual hierarchy
 */
export type EventPriority = 'major' | 'standard' | 'meta';

export function getEventPriority(eventType: string): EventPriority {
	const majorEvents = [
		'synthesis_complete',
		'meta_synthesis_complete',
		'complete',
		'voting_started',
		'decomposition_complete',
		'persona_selection_complete',
	];

	const metaEvents = [
		'convergence',
		'round_started',
		'facilitator_decision',
		'node_start',
		'node_end',
	];

	if (majorEvents.includes(eventType)) return 'major';
	if (metaEvents.includes(eventType)) return 'meta';
	return 'standard';
}
