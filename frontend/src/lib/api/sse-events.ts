/**
 * SSE Event Types - TypeScript interfaces for Board of One Server-Sent Events
 *
 * These types document the SSE event payloads emitted by:
 * - backend/api/event_collector.py (graph node handlers)
 * - backend/api/event_extractors.py (data extraction)
 *
 * Schema Versioning:
 * - EXPECTED_SSE_VERSION: The version this client expects
 * - MIN_SUPPORTED_VERSION: Minimum version client can handle
 * - checkEventVersion(): Utility to validate and warn on mismatches
 *
 * Event categories:
 * - Lifecycle: working_status, complete, error, session_status_error
 * - Decomposition: decomposition_complete, comparison_detected
 * - Personas: persona_selected, persona_selection_complete
 * - Deliberation: contribution, parallel_round_start, facilitator_decision, moderator_intervention
 * - Quality: discussion_quality_status, convergence
 * - Sub-problems: subproblem_started, subproblem_complete, dependency_analysis_complete
 * - Voting/Synthesis: voting_complete, synthesis_complete, meta_synthesis_complete, expert_summaries
 * - Research: research_results, context_collection_complete
 * - Clarification: clarification_required, context_insufficient
 * - Cost: phase_cost_breakdown, cost_anomaly
 * - Persistence: persistence_verification_warning
 * - Interjection: user_interjection_raised, interjection_response, interjection_complete
 */

// =============================================================================
// Schema Versioning Constants
// =============================================================================

/**
 * Expected SSE schema version - client expects server to send this version
 * Update this when upgrading to a new schema version
 */
export const EXPECTED_SSE_VERSION = 1;

/**
 * Minimum supported SSE schema version - client can handle down to this version
 * Older events may be missing fields but should still work
 */
export const MIN_SUPPORTED_VERSION = 1;

// =============================================================================
// Core Event Types
// =============================================================================

/**
 * All SSE event types emitted by the deliberation system
 */
export type SSEEventType =
	// Session lifecycle
	| 'session_started'
	| 'working_status'
	| 'complete'
	| 'error'
	| 'session_status_error'
	// Decomposition
	| 'decomposition_started'
	| 'decomposition_complete'
	| 'comparison_detected'
	// Personas
	| 'persona_selection_started'
	| 'persona_selected'
	| 'persona_selection_complete'
	// Deliberation rounds
	| 'initial_round_started'
	| 'round_started'
	| 'contribution'
	| 'parallel_round_start'
	| 'facilitator_decision'
	| 'moderator_intervention'
	// Quality
	| 'discussion_quality_status'
	| 'convergence'
	| 'quality_metrics_update'
	// Sub-problems
	| 'subproblem_started'
	| 'subproblem_complete'
	| 'dependency_analysis_complete'
	// Voting/Synthesis
	| 'voting_started'
	| 'persona_vote'
	| 'voting_complete'
	| 'synthesis_started'
	| 'synthesis_complete'
	| 'meta_synthesis_started'
	| 'meta_synthesis_complete'
	| 'expert_summaries'
	// Research
	| 'research_results'
	| 'context_collection_complete'
	// Clarification
	| 'clarification_required'
	| 'clarification_requested'
	| 'clarification_answered'
	| 'context_insufficient'
	// Cost
	| 'phase_cost_breakdown'
	| 'cost_anomaly'
	// Node lifecycle
	| 'node_start'
	| 'node_end'
	// Persistence
	| 'persistence_verification_warning'
	// Meeting failure
	| 'meeting_failed'
	// Gap detection
	| 'gap_detected'
	// User Interjection ("Raise Hand")
	| 'user_interjection_raised'
	| 'interjection_response'
	| 'interjection_complete'
	// State transitions (progress visualization)
	| 'state_transition';

// =============================================================================
// Lifecycle Events
// =============================================================================

/**
 * Indicates ongoing processing phase
 * Emitted: Before long-running operations (voting, synthesis, rounds)
 */
export interface WorkingStatusPayload {
	phase: string;
	sub_problem_index: number;
}

/**
 * Session completed successfully
 * Emitted: After final state is reached
 */
export interface CompletePayload {
	session_id: string;
	final_output: string;
	total_cost: number;
	total_rounds: number;
	total_contributions: number;
	total_tokens: number;
	duration_seconds: number;
	stop_reason: string;
}

/**
 * Error occurred during deliberation
 * Emitted: On any exception during graph execution
 */
export interface ErrorPayload {
	error: string;
	error_type: string;
	event_type_attempted?: string;
	sub_problem_index?: number;
}

/**
 * Failed to update session status in database
 * Emitted: When PostgreSQL status update fails after completion
 */
export interface SessionStatusErrorPayload {
	error: string;
	message: string;
	synthesis_available: boolean;
}

// =============================================================================
// Decomposition Events
// =============================================================================

/**
 * Sub-problem for decomposition events
 */
export interface SubProblemInfo {
	id: string;
	goal: string;
	rationale: string;
	complexity_score: number;
	dependencies: string[];
}

/**
 * Problem decomposition completed
 * Emitted: After decompose node finishes
 */
export interface DecompositionCompletePayload {
	sub_problems: SubProblemInfo[];
	count: number;
	sub_problem_index: number;
}

/**
 * Comparison scenario detected (e.g., "X vs Y")
 * Emitted: When decompose identifies a comparison question
 */
export interface ComparisonDetectedPayload {
	comparison_type: string;
	options: string[];
	research_queries_count: number;
}

// =============================================================================
// Persona Events
// =============================================================================

/**
 * Persona info for selection events
 */
export interface PersonaInfo {
	code: string;
	name: string;
	archetype: string;
	display_name: string;
	domain_expertise: string[];
}

/**
 * Single persona selected for panel
 * Emitted: For each persona added to the expert panel
 */
export interface PersonaSelectedPayload {
	persona: PersonaInfo;
	rationale: string;
	order: number;
	sub_problem_index: number;
}

/**
 * All personas selected for panel
 * Emitted: After select_personas node completes
 */
export interface PersonaSelectionCompletePayload {
	personas: string[];
	count: number;
	sub_problem_index: number;
}

/**
 * Expert info for display in expert panels (derived from PersonaSelectedPayload)
 */
export interface ExpertInfo {
	persona: PersonaInfo;
	rationale: string;
	order: number;
}

/**
 * Alias for PersonaInfo for backwards compatibility
 */
export type Persona = PersonaInfo;

// =============================================================================
// Deliberation Events
// =============================================================================

/**
 * AI-generated summary structure for contributions
 */
export interface ContributionSummary {
	concise: string;
	detailed: string;
	key_points: string[];
}

/**
 * Expert contribution during deliberation
 * Emitted: For each contribution in initial_round and parallel_round
 */
export interface ContributionPayload {
	persona_code: string;
	persona_name: string;
	archetype: string;
	domain_expertise: string[];
	content: string;
	summary: ContributionSummary | null;
	round: number;
	contribution_type: 'initial' | 'parallel';
	sub_problem_index: number;
}

/**
 * New deliberation round started
 * Emitted: At start of each parallel round
 */
export interface ParallelRoundStartPayload {
	round: number;
	phase: string;
	experts_selected: string[];
	expert_count: number;
	sub_problem_index: number;
}

/**
 * Facilitator decision about discussion direction
 * Emitted: After facilitator_decide node
 */
export interface FacilitatorDecisionPayload {
	action: string;
	reasoning: string;
	next_speaker?: string;
	moderator_type?: string;
	research_query?: string;
	round: number;
	sub_problem_index: number;
}

/**
 * Moderator intervention in discussion
 * Emitted: After moderator_intervene node
 */
export interface ModeratorInterventionPayload {
	moderator_type: string;
	content: string;
	trigger_reason: string;
	round: number;
	sub_problem_index: number;
}

// =============================================================================
// Quality Events
// =============================================================================

/**
 * Discussion quality status update
 * Emitted: During analysis phases (analyzing, selecting, gathering)
 */
export interface DiscussionQualityStatusPayload {
	status: string;
	message: string;
	round: number;
	sub_problem_index: number;
}

/**
 * Aspect coverage information for quality metrics
 */
export interface AspectCoverage {
	aspect: string;
	coverage: number;
	contributors: string[];
}

/**
 * Convergence check result
 * Emitted: After check_convergence node
 */
export interface ConvergencePayload {
	converged: boolean;
	should_stop: boolean;
	stop_reason: string | null;
	score: number;
	threshold: number;
	round: number;
	max_rounds: number;
	sub_problem_index: number;
	phase: string | null;
	// Quality metrics (Meeting Quality Enhancement)
	exploration_score: number | null;
	focus_score: number | null;
	novelty_score: number | null;
	conflict_score: number | null;
	meeting_completeness_index: number | null;
	aspect_coverage: AspectCoverage[];
	drift_events: number;
	facilitator_guidance: string | null;
}

// =============================================================================
// Sub-problem Events
// =============================================================================

/**
 * Sub-problem deliberation started
 * Emitted: At start of each sub-problem
 */
export interface SubproblemStartedPayload {
	sub_problem_index: number;
	sub_problem_id: string;
	goal: string;
	total_sub_problems: number;
}

/**
 * Sub-problem deliberation completed
 * Emitted: After synthesis for a sub-problem
 */
export interface SubproblemCompletePayload {
	sub_problem_index: number;
	sub_problem_id: string;
	sub_problem_goal: string;
	synthesis: string;
	cost: number;
	duration_seconds: number;
	expert_panel: string[];
	contribution_count: number;
	expert_summaries: Record<string, string>;
}

/**
 * Batch information for dependency analysis
 */
export interface BatchInfo {
	batch_index: number;
	sub_problem_ids: string[];
}

/**
 * Dependency analysis completed
 * Emitted: After analyze_dependencies node
 */
export interface DependencyAnalysisCompletePayload {
	batch_count: number;
	parallel_mode: boolean;
	batches: BatchInfo[];
}

// =============================================================================
// Voting/Synthesis Events
// =============================================================================

/**
 * Single vote/recommendation from an expert
 */
export interface Vote {
	persona_code: string;
	persona_name: string;
	recommendation: string;
	confidence: number;
	reasoning: string;
	conditions: string[];
}

/**
 * Voting started - experts begin making recommendations
 * Emitted: When vote phase begins
 */
export interface VotingStartedPayload {
	experts: string[];
	count: number;
	sub_problem_index: number;
}

/**
 * Individual expert vote/recommendation
 * Emitted: For each expert's vote during voting phase
 */
export interface PersonaVotePayload {
	persona_code: string;
	persona_name: string;
	recommendation: string;
	confidence: number;
	reasoning: string;
	conditions: string[];
	sub_problem_index: number;
}

/**
 * Voting phase completed
 * Emitted: After vote node
 */
export interface VotingCompletePayload {
	votes: Vote[];
	votes_count: number;
	consensus_level: 'strong' | 'moderate' | 'weak' | 'unknown';
	avg_confidence: number;
	sub_problem_index: number;
}

/**
 * Synthesis started
 * Emitted: When synthesis phase begins
 */
export interface SynthesisStartedPayload {
	sub_problem_index: number;
}

/**
 * Synthesis completed for a sub-problem
 * Emitted: After synthesize node
 */
export interface SynthesisCompletePayload {
	synthesis: string;
	word_count: number;
	sub_problem_index: number;
}

/**
 * Meta-synthesis completed (combining all sub-problem syntheses)
 * Emitted: After meta_synthesize node
 */
export interface MetaSynthesisCompletePayload {
	synthesis: string;
	word_count: number;
}

/**
 * Per-expert summaries generated
 * Emitted: After synthesis when expert_summaries available
 */
export interface ExpertSummariesPayload {
	expert_summaries: Record<string, string>;
	sub_problem_index: number;
	sub_problem_goal: string;
}

// =============================================================================
// Research Events
// =============================================================================

/**
 * Single research result
 */
export interface ResearchResult {
	query: string;
	summary: string;
	sources: string[];
	cached: boolean;
	round: number;
	depth: 'basic' | 'deep';
	proactive?: boolean;
}

/**
 * Research results from external sources
 * Emitted: After research node
 */
export interface ResearchResultsPayload {
	research_results: ResearchResult[];
	sub_problem_index: number;
	round_number: number;
}

/**
 * Business context collection completed
 * Emitted: After context_collection node
 */
export interface ContextCollectionCompletePayload {
	context_loaded: boolean;
	context_summary: string;
	metrics_count: number;
}

// =============================================================================
// Clarification Events
// =============================================================================

/**
 * Clarification question for user
 */
export interface ClarificationQuestion {
	question: string;
	category?: string;
	priority?: string;
}

/**
 * Clarification required from user
 * Emitted: When identify_gaps finds critical information gaps
 */
export interface ClarificationRequiredPayload {
	questions: ClarificationQuestion[];
	phase: string;
	reason: string;
	question_count: number;
}

/**
 * Choice option for context insufficient scenario
 */
export interface ContextInsufficientChoice {
	id: string;
	label: string;
	description: string;
}

/**
 * Experts indicate insufficient context
 * Emitted: When convergence detects high meta-contribution ratio
 */
export interface ContextInsufficientPayload {
	meta_ratio: number;
	expert_questions: string[];
	reason: string;
	round_number: number;
	sub_problem_index: number;
	choices: ContextInsufficientChoice[];
	timeout_seconds: number;
}

// =============================================================================
// Cost Events
// =============================================================================

/**
 * Cost breakdown by phase
 * Emitted: At session completion
 */
export interface PhaseCostBreakdownPayload {
	phase_costs: Record<string, number>;
	total_cost: number;
}

/**
 * Cost exceeded anomaly threshold
 * Emitted: When session cost > $1.00
 */
export interface CostAnomalyPayload {
	total_cost: number;
	threshold: number;
	by_provider: Record<string, number>;
	total_calls: number;
}

// =============================================================================
// Meeting Failure Events
// =============================================================================

/**
 * Meeting failed event payload
 * Emitted: When sub-problem validation fails before meta-synthesis
 */
export interface MeetingFailedPayload {
	failed_count: number;
	failed_goals: string[];
	completed_count: number;
	total_count: number;
	reason: string;
	failed_ids?: string[];
}

// =============================================================================
// Persistence Events
// =============================================================================

/**
 * Event persistence verification warning
 * Emitted: When PostgreSQL has fewer events than Redis
 */
export interface PersistenceVerificationWarningPayload {
	redis_events: number;
	postgres_events: number;
	missing_events: number;
	message: string;
}

// =============================================================================
// Gap Detection Events
// =============================================================================

/**
 * SSE sequence gap detected during reconnection
 * Emitted: When client reconnects and gaps are found in event sequence
 */
export interface GapDetectedPayload {
	session_id: string;
	expected_sequence: number;
	actual_sequence: number;
	missed_count: number;
	message: string;
}

// =============================================================================
// State Transition Events (Progress Visualization)
// =============================================================================

/**
 * State transition between graph nodes
 * Emitted: When execution moves from one node to another
 */
export interface StateTransitionPayload {
	from_node: string | null;
	to_node: string;
	sub_problem_index: number;
}

// =============================================================================
// User Interjection Events ("Raise Hand")
// =============================================================================

/**
 * User raised hand with interjection message
 * Emitted: When user submits a question/comment during deliberation
 */
export interface UserInterjectionRaisedPayload {
	session_id: string;
	message: string;
	timestamp: string;
}

/**
 * Expert response to user interjection
 * Emitted: For each expert's brief response to the user's question
 */
export interface InterjectionResponsePayload {
	session_id: string;
	persona_code: string;
	persona_name: string;
	response: string;
	round_number: number;
	timestamp: string;
}

/**
 * Interjection processing complete
 * Emitted: After all experts have responded to the interjection
 */
export interface InterjectionCompletePayload {
	session_id: string;
	total_responses: number;
	round_number: number;
	timestamp: string;
}

// =============================================================================
// Event Map & Wrapper
// =============================================================================

/**
 * Map of event types to their payload types
 * Note: Events not listed here use SSEEventPayload (generic payload with sub_problem_index)
 */
export interface SSEEventMap {
	// Session lifecycle
	working_status: WorkingStatusPayload;
	complete: CompletePayload;
	error: ErrorPayload;
	session_status_error: SessionStatusErrorPayload;
	// Decomposition
	decomposition_complete: DecompositionCompletePayload;
	comparison_detected: ComparisonDetectedPayload;
	// Personas
	persona_selected: PersonaSelectedPayload;
	persona_selection_complete: PersonaSelectionCompletePayload;
	// Deliberation
	contribution: ContributionPayload;
	parallel_round_start: ParallelRoundStartPayload;
	facilitator_decision: FacilitatorDecisionPayload;
	moderator_intervention: ModeratorInterventionPayload;
	// Quality
	discussion_quality_status: DiscussionQualityStatusPayload;
	convergence: ConvergencePayload;
	// Sub-problems
	subproblem_started: SubproblemStartedPayload;
	subproblem_complete: SubproblemCompletePayload;
	dependency_analysis_complete: DependencyAnalysisCompletePayload;
	// Voting
	voting_started: VotingStartedPayload;
	persona_vote: PersonaVotePayload;
	voting_complete: VotingCompletePayload;
	// Synthesis
	synthesis_started: SynthesisStartedPayload;
	synthesis_complete: SynthesisCompletePayload;
	meta_synthesis_complete: MetaSynthesisCompletePayload;
	expert_summaries: ExpertSummariesPayload;
	// Research
	research_results: ResearchResultsPayload;
	context_collection_complete: ContextCollectionCompletePayload;
	// Clarification
	clarification_required: ClarificationRequiredPayload;
	context_insufficient: ContextInsufficientPayload;
	// Cost
	phase_cost_breakdown: PhaseCostBreakdownPayload;
	cost_anomaly: CostAnomalyPayload;
	// Persistence
	persistence_verification_warning: PersistenceVerificationWarningPayload;
	// Meeting failure
	meeting_failed: MeetingFailedPayload;
	// Gap detection
	gap_detected: GapDetectedPayload;
	// User Interjection
	user_interjection_raised: UserInterjectionRaisedPayload;
	interjection_response: InterjectionResponsePayload;
	interjection_complete: InterjectionCompletePayload;
	// State transitions
	state_transition: StateTransitionPayload;
}

/**
 * Generic event payload type that allows any property access
 * Used for backwards compatibility with existing code that accesses data without type narrowing
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type GenericEventPayload = Record<string, any>;

/**
 * Generic SSE event wrapper with type discriminator
 *
 * For backwards compatibility, SSEEvent uses GenericEventPayload for data.
 * Use typed event aliases (e.g., ContributionEvent, ConvergenceEvent) for strict typing.
 *
 * @example
 * // Generic usage (backwards compatible) - data allows any property access
 * const event: SSEEvent = ...;
 * event.data.persona_code; // OK
 *
 * // Strict typing - use specific event type aliases
 * const event: ContributionEvent = ...;
 * event.data.persona_code; // Strictly typed
 */
export interface SSEEvent<T extends SSEEventType = SSEEventType> {
	event_type: T;
	data: T extends keyof SSEEventMap ? SSEEventMap[T] : GenericEventPayload;
	timestamp?: string;
	session_id?: string;
}

/**
 * Type-safe event handler function
 */
export type SSEEventHandler<T extends SSEEventType> = (
	data: T extends keyof SSEEventMap ? SSEEventMap[T] : unknown
) => void;

/**
 * Type-safe event handlers map
 */
export type SSEEventHandlers = {
	[K in SSEEventType]?: SSEEventHandler<K>;
};

// =============================================================================
// Type Aliases (Backwards Compatibility)
// =============================================================================

/**
 * Legacy alias for SSEEvent - used throughout the codebase
 * @deprecated Use SSEEvent instead
 */
export type DeliberationEvent = SSEEvent;

/**
 * Typed decomposition_complete event
 */
export type DecompositionCompleteEvent = SSEEvent<'decomposition_complete'>;

/**
 * Typed contribution event
 */
export type ContributionEvent = SSEEvent<'contribution'>;

/**
 * Typed convergence event
 */
export type ConvergenceEvent = SSEEvent<'convergence'>;

/**
 * Typed voting_complete event
 */
export type VotingCompleteEvent = SSEEvent<'voting_complete'>;

/**
 * Typed synthesis_complete event
 */
export type SynthesisCompleteEvent = SSEEvent<'synthesis_complete'>;

/**
 * Typed complete event
 */
export type CompleteEvent = SSEEvent<'complete'>;

/**
 * Typed error event
 */
export type ErrorEvent = SSEEvent<'error'>;

/**
 * Typed persona_selected event
 */
export type PersonaSelectedEvent = SSEEvent<'persona_selected'>;

/**
 * Typed facilitator_decision event
 */
export type FacilitatorDecisionEvent = SSEEvent<'facilitator_decision'>;

/**
 * Typed moderator_intervention event
 */
export type ModeratorInterventionEvent = SSEEvent<'moderator_intervention'>;

/**
 * Typed discussion_quality_status event
 */
export type DiscussionQualityStatusEvent = SSEEvent<'discussion_quality_status'>;

/**
 * Typed subproblem_started event
 */
export type SubproblemStartedEvent = SSEEvent<'subproblem_started'>;

/**
 * Typed subproblem_complete event
 */
export type SubproblemCompleteEvent = SSEEvent<'subproblem_complete'>;

/**
 * Typed research_results event
 */
export type ResearchResultsEvent = SSEEvent<'research_results'>;

/**
 * Typed clarification_required event
 */
export type ClarificationRequiredEvent = SSEEvent<'clarification_required'>;

/**
 * Typed context_insufficient event
 */
export type ContextInsufficientEvent = SSEEvent<'context_insufficient'>;

/**
 * Typed voting_started event
 */
export type VotingStartedEvent = SSEEvent<'voting_started'>;

/**
 * Typed persona_vote event
 */
export type PersonaVoteEvent = SSEEvent<'persona_vote'>;

/**
 * Typed meta_synthesis_complete event
 */
export type MetaSynthesisCompleteEvent = SSEEvent<'meta_synthesis_complete'>;

/**
 * Alias for SubproblemCompleteEvent (PascalCase naming)
 */
export type SubProblemCompleteEvent = SubproblemCompleteEvent;

/**
 * Typed phase_cost_breakdown event
 */
export type PhaseCostBreakdownEvent = SSEEvent<'phase_cost_breakdown'>;

/**
 * Typed cost_anomaly event
 */
export type CostAnomalyEvent = SSEEvent<'cost_anomaly'>;

/**
 * Typed meeting_failed event
 */
export type MeetingFailedEvent = SSEEvent<'meeting_failed'>;

/**
 * Typed gap_detected event
 */
export type GapDetectedEvent = SSEEvent<'gap_detected'>;

/**
 * Typed user_interjection_raised event
 */
export type UserInterjectionRaisedEvent = SSEEvent<'user_interjection_raised'>;

/**
 * Typed interjection_response event
 */
export type InterjectionResponseEvent = SSEEvent<'interjection_response'>;

/**
 * Typed interjection_complete event
 */
export type InterjectionCompleteEvent = SSEEvent<'interjection_complete'>;

/**
 * Typed state_transition event
 */
export type StateTransitionEvent = SSEEvent<'state_transition'>;

// =============================================================================
// Type Guards
// =============================================================================

/**
 * Generic type guard for narrowing SSEEvent by event_type
 * @example
 * if (isEventType(event, 'contribution')) {
 *   event.data.persona_code; // TypeScript knows this is ContributionPayload
 * }
 */
export function isEventType<T extends keyof SSEEventMap>(
	event: SSEEvent,
	type: T
): event is SSEEvent<T> {
	return event.event_type === type;
}

/**
 * Type guard for convergence events
 */
export function isConvergenceEvent(event: SSEEvent): event is SSEEvent<'convergence'> {
	return event.event_type === 'convergence';
}

/**
 * Type guard for contribution events
 */
export function isContributionEvent(event: SSEEvent): event is SSEEvent<'contribution'> {
	return event.event_type === 'contribution';
}

/**
 * Type guard for decomposition_complete events
 */
export function isDecompositionEvent(event: SSEEvent): event is SSEEvent<'decomposition_complete'> {
	return event.event_type === 'decomposition_complete';
}

/**
 * Type guard for subproblem_started events
 */
export function isSubproblemStartedEvent(event: SSEEvent): event is SSEEvent<'subproblem_started'> {
	return event.event_type === 'subproblem_started';
}

/**
 * Type guard for subproblem_complete events
 */
export function isSubproblemCompleteEvent(event: SSEEvent): event is SSEEvent<'subproblem_complete'> {
	return event.event_type === 'subproblem_complete';
}

/**
 * Type guard for research_results events
 */
export function isResearchResultsEvent(event: SSEEvent): event is SSEEvent<'research_results'> {
	return event.event_type === 'research_results';
}

/**
 * Type guard for clarification_required events
 */
export function isClarificationRequiredEvent(event: SSEEvent): event is SSEEvent<'clarification_required'> {
	return event.event_type === 'clarification_required';
}

/**
 * Type guard for clarification_answered events
 */
export function isClarificationAnsweredEvent(event: SSEEvent): event is SSEEvent<'clarification_answered'> {
	return event.event_type === 'clarification_answered';
}

/**
 * Type guard for synthesis_complete events
 */
export function isSynthesisCompleteEvent(event: SSEEvent): event is SSEEvent<'synthesis_complete'> {
	return event.event_type === 'synthesis_complete';
}

/**
 * Type guard for meta_synthesis_complete events
 */
export function isMetaSynthesisCompleteEvent(event: SSEEvent): event is SSEEvent<'meta_synthesis_complete'> {
	return event.event_type === 'meta_synthesis_complete';
}

/**
 * Type guard for persona_selected events
 */
export function isPersonaSelectedEvent(event: SSEEvent): event is SSEEvent<'persona_selected'> {
	return event.event_type === 'persona_selected';
}

/**
 * Type guard for error events
 */
export function isErrorEvent(event: SSEEvent): event is SSEEvent<'error'> {
	return event.event_type === 'error';
}

/**
 * Type guard for working_status events
 */
export function isWorkingStatusEvent(event: SSEEvent): event is SSEEvent<'working_status'> {
	return event.event_type === 'working_status';
}

/**
 * Type guard for facilitator_decision events
 */
export function isFacilitatorDecisionEvent(event: SSEEvent): event is SSEEvent<'facilitator_decision'> {
	return event.event_type === 'facilitator_decision';
}

/**
 * Type guard for moderator_intervention events
 */
export function isModeratorInterventionEvent(event: SSEEvent): event is SSEEvent<'moderator_intervention'> {
	return event.event_type === 'moderator_intervention';
}

/**
 * Type guard for voting_complete events
 */
export function isVotingCompleteEvent(event: SSEEvent): event is SSEEvent<'voting_complete'> {
	return event.event_type === 'voting_complete';
}

/**
 * Type guard for discussion_quality_status events
 */
export function isDiscussionQualityStatusEvent(event: SSEEvent): event is SSEEvent<'discussion_quality_status'> {
	return event.event_type === 'discussion_quality_status';
}

/**
 * Type guard for gap_detected events
 */
export function isGapDetectedEvent(event: SSEEvent): event is SSEEvent<'gap_detected'> {
	return event.event_type === 'gap_detected';
}

/**
 * Type guard for user_interjection_raised events
 */
export function isUserInterjectionRaisedEvent(event: SSEEvent): event is SSEEvent<'user_interjection_raised'> {
	return event.event_type === 'user_interjection_raised';
}

/**
 * Type guard for interjection_response events
 */
export function isInterjectionResponseEvent(event: SSEEvent): event is SSEEvent<'interjection_response'> {
	return event.event_type === 'interjection_response';
}

/**
 * Type guard for interjection_complete events
 */
export function isInterjectionCompleteEvent(event: SSEEvent): event is SSEEvent<'interjection_complete'> {
	return event.event_type === 'interjection_complete';
}

/**
 * Type guard for state_transition events
 */
export function isStateTransitionEvent(event: SSEEvent): event is SSEEvent<'state_transition'> {
	return event.event_type === 'state_transition';
}

/**
 * Helper to safely access sub_problem_index from any event
 * Returns the index or undefined if not present
 */
export function getSubProblemIndex(event: SSEEvent): number | undefined {
	const data = event.data as { sub_problem_index?: number };
	return data.sub_problem_index;
}

/**
 * Helper to safely check if an event has a specific typed payload property
 */
export function hasPayloadProperty<K extends string>(
	event: SSEEvent,
	key: K
): event is SSEEvent & { data: Record<K, unknown> } {
	return event.data !== null && typeof event.data === 'object' && key in event.data;
}

// =============================================================================
// Version Checking Utilities
// =============================================================================

/**
 * Version check result for SSE events
 */
export interface VersionCheckResult {
	isCompatible: boolean;
	eventVersion: number;
	expectedVersion: number;
	minSupported: number;
	warning?: string;
}

/**
 * Check if an SSE event version is compatible with this client.
 *
 * Logs console warnings for:
 * - Events with version below MIN_SUPPORTED_VERSION
 * - Events with version above EXPECTED_SSE_VERSION (future version)
 *
 * @param event - SSE event to check (must have event_version in data)
 * @returns Version check result with compatibility status and any warnings
 *
 * @example
 * const result = checkEventVersion(event);
 * if (!result.isCompatible) {
 *   console.warn(result.warning);
 * }
 */
export function checkEventVersion(event: SSEEvent): VersionCheckResult {
	// Get event_version from the data payload
	const eventVersion =
		typeof event.data === 'object' && event.data !== null
			? ((event.data as Record<string, unknown>).event_version as number | undefined)
			: undefined;

	// Default to expected version if not present (backwards compatibility)
	const version = eventVersion ?? EXPECTED_SSE_VERSION;

	const result: VersionCheckResult = {
		isCompatible: true,
		eventVersion: version,
		expectedVersion: EXPECTED_SSE_VERSION,
		minSupported: MIN_SUPPORTED_VERSION
	};

	// Check if version is too old
	if (version < MIN_SUPPORTED_VERSION) {
		result.isCompatible = false;
		result.warning = `SSE event version ${version} is below minimum supported version ${MIN_SUPPORTED_VERSION}. Some features may not work correctly.`;
		if (typeof console !== 'undefined') {
			console.warn(`[SSE VERSION] ${result.warning}`, { event_type: event.event_type });
		}
	}
	// Check if version is newer than expected (future version)
	else if (version > EXPECTED_SSE_VERSION) {
		// Still compatible (additive changes), but log for awareness
		result.warning = `SSE event version ${version} is newer than expected ${EXPECTED_SSE_VERSION}. Client may be outdated.`;
		if (typeof console !== 'undefined') {
			console.info(`[SSE VERSION] ${result.warning}`, { event_type: event.event_type });
		}
	}

	return result;
}

/**
 * Check if the server's SSE schema version (from X-SSE-Schema-Version header) is compatible.
 *
 * Call this when establishing an SSE connection to validate server compatibility.
 *
 * @param headerValue - Value of X-SSE-Schema-Version response header
 * @returns Version check result
 *
 * @example
 * const response = await fetch('/api/v1/sessions/123/stream');
 * const serverVersion = response.headers.get('X-SSE-Schema-Version');
 * const result = checkServerVersion(serverVersion);
 * if (result.warning) {
 *   console.warn(result.warning);
 * }
 */
export function checkServerVersion(headerValue: string | null): VersionCheckResult {
	const version = headerValue ? parseInt(headerValue, 10) : EXPECTED_SSE_VERSION;

	const result: VersionCheckResult = {
		isCompatible: true,
		eventVersion: version,
		expectedVersion: EXPECTED_SSE_VERSION,
		minSupported: MIN_SUPPORTED_VERSION
	};

	if (isNaN(version)) {
		result.warning = `Invalid X-SSE-Schema-Version header: ${headerValue}`;
		if (typeof console !== 'undefined') {
			console.warn(`[SSE VERSION] ${result.warning}`);
		}
		return result;
	}

	if (version < MIN_SUPPORTED_VERSION) {
		result.isCompatible = false;
		result.warning = `Server SSE schema version ${version} is below minimum supported ${MIN_SUPPORTED_VERSION}`;
		if (typeof console !== 'undefined') {
			console.warn(`[SSE VERSION] ${result.warning}`);
		}
	} else if (version > EXPECTED_SSE_VERSION) {
		result.warning = `Server SSE schema version ${version} is newer than client expected ${EXPECTED_SSE_VERSION}. Consider updating client.`;
		if (typeof console !== 'undefined') {
			console.info(`[SSE VERSION] ${result.warning}`);
		}
	}

	return result;
}
