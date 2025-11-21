/**
 * SSE Event Type Definitions
 *
 * TypeScript interfaces for all 25 Board of One event types
 * Based on schemas in STREAMING_IMPLEMENTATION_PLAN.md
 */

// ============================================================================
// Base Event Interface
// ============================================================================

export interface SSEEvent {
	event_type: string;
	session_id: string;
	timestamp: string;
	data: Record<string, unknown>;
}

// ============================================================================
// Sub-Problem Schema
// ============================================================================

export interface SubProblem {
	id: string;
	goal: string;
	rationale: string;
	complexity_score: number;
	dependencies: string[];
}

// ============================================================================
// Persona Schema
// ============================================================================

export interface Persona {
	code: string;
	name: string;
	display_name: string;
	domain_expertise: string[];
}

// ============================================================================
// Event 1: Session Started
// ============================================================================

export interface SessionStartedEvent extends SSEEvent {
	event_type: 'session_started';
	data: {
		problem_statement: string;
		max_rounds: number;
		user_id: string;
	};
}

// ============================================================================
// Event 2: Decomposition Started
// ============================================================================

export interface DecompositionStartedEvent extends SSEEvent {
	event_type: 'decomposition_started';
	data: Record<string, never>;
}

// ============================================================================
// Event 3: Decomposition Complete
// ============================================================================

export interface DecompositionCompleteEvent extends SSEEvent {
	event_type: 'decomposition_complete';
	data: {
		sub_problems: SubProblem[];
		count: number;
	};
}

// ============================================================================
// Event 4: Persona Selection Started
// ============================================================================

export interface PersonaSelectionStartedEvent extends SSEEvent {
	event_type: 'persona_selection_started';
	data: Record<string, never>;
}

// ============================================================================
// Event 5: Persona Selected
// ============================================================================

export interface PersonaSelectedEvent extends SSEEvent {
	event_type: 'persona_selected';
	data: {
		persona: Persona;
		rationale: string;
		order: number;
	};
}

// ============================================================================
// Event 6: Persona Selection Complete
// ============================================================================

export interface PersonaSelectionCompleteEvent extends SSEEvent {
	event_type: 'persona_selection_complete';
	data: {
		personas: string[];
		count: number;
	};
}

// ============================================================================
// Event 7: Sub-Problem Started
// ============================================================================

export interface SubProblemStartedEvent extends SSEEvent {
	event_type: 'subproblem_started';
	data: {
		sub_problem_index: number;
		sub_problem_id: string;
		goal: string;
		total_sub_problems: number;
	};
}

// ============================================================================
// Event 8: Initial Round Started
// ============================================================================

export interface InitialRoundStartedEvent extends SSEEvent {
	event_type: 'initial_round_started';
	data: {
		round_number: number;
		experts: string[];
	};
}

// ============================================================================
// Event 9: Contribution (Persona Contribution)
// ============================================================================

export interface ContributionEvent extends SSEEvent {
	event_type: 'contribution';
	data: {
		persona_code: string;
		persona_name: string;
		content: string;
		round: number;
		contribution_type: 'initial' | 'followup';
	};
}

// ============================================================================
// Event 10: Facilitator Decision
// ============================================================================

export interface FacilitatorDecisionEvent extends SSEEvent {
	event_type: 'facilitator_decision';
	data: {
		action: 'continue' | 'vote' | 'research' | 'clarify' | 'moderator';
		reasoning: string;
		next_speaker?: string;
		round: number;
	};
}

// ============================================================================
// Event 11: Moderator Intervention
// ============================================================================

export interface ModeratorInterventionEvent extends SSEEvent {
	event_type: 'moderator_intervention';
	data: {
		moderator_type: 'contrarian' | 'balance' | 'focus';
		content: string;
		trigger_reason: string;
		round: number;
	};
}

// ============================================================================
// Event 12: Convergence Check
// ============================================================================

export interface ConvergenceEvent extends SSEEvent {
	event_type: 'convergence';
	data: {
		converged: boolean;
		score: number;
		threshold: number;
		should_stop: boolean;
		stop_reason: string | null;
		round: number;
		max_rounds: number;
	};
}

// ============================================================================
// Event 13: Round Started
// ============================================================================

export interface RoundStartedEvent extends SSEEvent {
	event_type: 'round_started';
	data: {
		round_number: number;
	};
}

// ============================================================================
// Event 14: Voting Started
// ============================================================================

export interface VotingStartedEvent extends SSEEvent {
	event_type: 'voting_started';
	data: {
		experts: string[];
		count: number;
	};
}

// ============================================================================
// Event 15: Persona Vote (Recommendation)
// ============================================================================

export interface PersonaVoteEvent extends SSEEvent {
	event_type: 'persona_vote';
	data: {
		persona_code: string;
		persona_name: string;
		recommendation: string;
		confidence: number;
		reasoning: string;
		conditions: string[];
	};
}

// ============================================================================
// Event 16: Voting Complete
// ============================================================================

export interface VotingCompleteEvent extends SSEEvent {
	event_type: 'voting_complete';
	data: {
		votes_count: number;
		consensus_level: 'strong' | 'moderate' | 'weak';
	};
}

// ============================================================================
// Event 17: Synthesis Started
// ============================================================================

export interface SynthesisStartedEvent extends SSEEvent {
	event_type: 'synthesis_started';
	data: Record<string, never>;
}

// ============================================================================
// Event 18: Synthesis Complete
// ============================================================================

export interface SynthesisCompleteEvent extends SSEEvent {
	event_type: 'synthesis_complete';
	data: {
		synthesis: string;
		word_count: number;
	};
}

// ============================================================================
// Event 19: Sub-Problem Complete
// ============================================================================

export interface SubProblemCompleteEvent extends SSEEvent {
	event_type: 'subproblem_complete';
	data: {
		sub_problem_index: number;
		sub_problem_id: string;
		goal: string;
		cost: number;
		duration_seconds: number;
		expert_panel: string[];
		contribution_count: number;
	};
}

// ============================================================================
// Event 20: Meta-Synthesis Started
// ============================================================================

export interface MetaSynthesisStartedEvent extends SSEEvent {
	event_type: 'meta_synthesis_started';
	data: {
		sub_problem_count: number;
		total_contributions: number;
		total_cost: number;
	};
}

// ============================================================================
// Event 21: Meta-Synthesis Complete
// ============================================================================

export interface MetaSynthesisCompleteEvent extends SSEEvent {
	event_type: 'meta_synthesis_complete';
	data: {
		synthesis: string;
		word_count: number;
	};
}

// ============================================================================
// Event 22: Phase Cost Breakdown
// ============================================================================

export interface PhaseCostBreakdownEvent extends SSEEvent {
	event_type: 'phase_cost_breakdown';
	data: {
		phase_costs: Record<string, number>;
		total_cost: number;
	};
}

// ============================================================================
// Event 23: Complete
// ============================================================================

export interface CompleteEvent extends SSEEvent {
	event_type: 'complete';
	data: {
		session_id: string;
		final_output: string;
		total_cost: number;
		total_rounds: number;
		total_contributions: number;
		total_tokens: number;
		duration_seconds: number;
		stop_reason: string;
	};
}

// ============================================================================
// Event 24: Error
// ============================================================================

export interface ErrorEvent extends SSEEvent {
	event_type: 'error';
	data: {
		session_id: string;
		error: string;
		error_type: string;
		node?: string;
		recoverable: boolean;
	};
}

// ============================================================================
// Event 25: Clarification Requested
// ============================================================================

export interface ClarificationRequestedEvent extends SSEEvent {
	event_type: 'clarification_requested';
	data: {
		session_id: string;
		question: string;
		reason: string;
		round: number;
		question_id: string;
	};
}

// ============================================================================
// Union Type for All Events
// ============================================================================

export type DeliberationEvent =
	| SessionStartedEvent
	| DecompositionStartedEvent
	| DecompositionCompleteEvent
	| PersonaSelectionStartedEvent
	| PersonaSelectedEvent
	| PersonaSelectionCompleteEvent
	| SubProblemStartedEvent
	| InitialRoundStartedEvent
	| ContributionEvent
	| FacilitatorDecisionEvent
	| ModeratorInterventionEvent
	| ConvergenceEvent
	| RoundStartedEvent
	| VotingStartedEvent
	| PersonaVoteEvent
	| VotingCompleteEvent
	| SynthesisStartedEvent
	| SynthesisCompleteEvent
	| SubProblemCompleteEvent
	| MetaSynthesisStartedEvent
	| MetaSynthesisCompleteEvent
	| PhaseCostBreakdownEvent
	| CompleteEvent
	| ErrorEvent
	| ClarificationRequestedEvent;

// ============================================================================
// Type Guards
// ============================================================================

export function isDecompositionCompleteEvent(event: SSEEvent): event is DecompositionCompleteEvent {
	return event.event_type === 'decomposition_complete';
}

export function isPersonaSelectedEvent(event: SSEEvent): event is PersonaSelectedEvent {
	return event.event_type === 'persona_selected';
}

export function isContributionEvent(event: SSEEvent): event is ContributionEvent {
	return event.event_type === 'contribution';
}

export function isFacilitatorDecisionEvent(event: SSEEvent): event is FacilitatorDecisionEvent {
	return event.event_type === 'facilitator_decision';
}

export function isModeratorInterventionEvent(event: SSEEvent): event is ModeratorInterventionEvent {
	return event.event_type === 'moderator_intervention';
}

export function isConvergenceEvent(event: SSEEvent): event is ConvergenceEvent {
	return event.event_type === 'convergence';
}

export function isVotingStartedEvent(event: SSEEvent): event is VotingStartedEvent {
	return event.event_type === 'voting_started';
}

export function isPersonaVoteEvent(event: SSEEvent): event is PersonaVoteEvent {
	return event.event_type === 'persona_vote';
}

export function isSynthesisCompleteEvent(event: SSEEvent): event is SynthesisCompleteEvent {
	return event.event_type === 'synthesis_complete';
}

export function isSubProblemCompleteEvent(event: SSEEvent): event is SubProblemCompleteEvent {
	return event.event_type === 'subproblem_complete';
}

export function isMetaSynthesisCompleteEvent(event: SSEEvent): event is MetaSynthesisCompleteEvent {
	return event.event_type === 'meta_synthesis_complete';
}

export function isPhaseCostBreakdownEvent(event: SSEEvent): event is PhaseCostBreakdownEvent {
	return event.event_type === 'phase_cost_breakdown';
}

export function isCompleteEvent(event: SSEEvent): event is CompleteEvent {
	return event.event_type === 'complete';
}

export function isErrorEvent(event: SSEEvent): event is ErrorEvent {
	return event.event_type === 'error';
}
