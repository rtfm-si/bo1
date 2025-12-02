/**
 * Loading Components - Barrel Export
 *
 * Unified loading UI system based on UX research from OpenAI, Anthropic, NN/G.
 */

// Components
export { default as LoadingDots } from './LoadingDots.svelte';
export { default as ShimmerSkeleton } from './ShimmerSkeleton.svelte';
export { default as ActivityStatus } from './ActivityStatus.svelte';

// Utilities
export {
	LOADING_MESSAGES,
	ROTATING_MESSAGES,
	getRotatingMessage,
} from './messages';

export {
	PHASE_PROGRESS,
	formatPhaseStep,
	getPhaseProgress,
	formatRoundProgress,
	formatSubProblemProgress,
	type MeetingPhase,
	type PhaseInfo,
} from './phases';
