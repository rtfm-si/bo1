/**
 * Meeting Phase Progress Mapping
 *
 * Maps meeting phases to progress indicators for UI display.
 * Provides step counts and labels for phase visibility.
 */

export type MeetingPhase =
	| 'initializing'
	| 'decomposing'
	| 'selecting_experts'
	| 'research'
	| 'deliberation'
	| 'voting'
	| 'synthesis'
	| 'complete'
	| 'failed';

export interface PhaseInfo {
	step: number;
	total: number;
	label: string;
	description: string;
}

export const PHASE_PROGRESS: Record<MeetingPhase, PhaseInfo> = {
	initializing: {
		step: 1,
		total: 7,
		label: 'Setting up',
		description: 'Initializing your meeting',
	},
	decomposing: {
		step: 2,
		total: 7,
		label: 'Analyzing',
		description: 'Breaking down your decision into focus areas',
	},
	selecting_experts: {
		step: 3,
		total: 7,
		label: 'Selecting experts',
		description: 'Choosing the best experts for your decision',
	},
	research: {
		step: 4,
		total: 7,
		label: 'Researching',
		description: 'Gathering background information',
	},
	deliberation: {
		step: 5,
		total: 7,
		label: 'Deliberating',
		description: 'Experts are discussing your decision',
	},
	voting: {
		step: 6,
		total: 7,
		label: 'Voting',
		description: 'Experts are forming recommendations',
	},
	synthesis: {
		step: 7,
		total: 7,
		label: 'Synthesizing',
		description: 'Generating final recommendations',
	},
	complete: {
		step: 7,
		total: 7,
		label: 'Complete',
		description: 'Meeting complete',
	},
	failed: {
		step: 0,
		total: 7,
		label: 'Failed',
		description: 'Something went wrong',
	},
};

/**
 * Format phase as "Step X of Y"
 */
export function formatPhaseStep(phase: MeetingPhase): string {
	const info = PHASE_PROGRESS[phase];
	if (phase === 'complete') return 'Complete';
	if (phase === 'failed') return 'Failed';
	return `Step ${info.step} of ${info.total}`;
}

/**
 * Get progress percentage for a phase
 */
export function getPhaseProgress(phase: MeetingPhase): number {
	const info = PHASE_PROGRESS[phase];
	return Math.round((info.step / info.total) * 100);
}

/**
 * Format round progress
 */
export function formatRoundProgress(current: number, total: number): string {
	return `Round ${current} of ${total}`;
}

/**
 * Format sub-problem progress
 */
export function formatSubProblemProgress(
	completed: number,
	total: number
): string {
	return `${completed} of ${total} focus areas completed`;
}
