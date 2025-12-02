/**
 * Contextual Loading Messages
 *
 * Centralized library of loading messages for consistent UX.
 * Research shows contextual messages ("Analyzing...") beat generic ("Loading...").
 */

export const LOADING_MESSAGES = {
	// Authentication
	auth: {
		verifying: 'Verifying your session',
		signingIn: 'Signing you in',
		redirecting: 'Redirecting to dashboard',
		completing: 'Completing sign in',
	},

	// Meeting lifecycle
	meeting: {
		initializing: 'Setting up your meeting',
		decomposing: 'Breaking down your decision into focus areas',
		selectingExperts: 'Selecting the best experts for your decision',
		researchPhase: 'Researching background information',
		loading: 'Loading meeting',
	},

	// Deliberation
	deliberation: {
		thinking: (expertName: string) => `${expertName} is thinking`,
		contributing: (expertName: string) => `${expertName} is contributing`,
		roundStart: (round: number, total: number) => `Starting round ${round} of ${total}`,
		betweenRounds: 'Preparing next round of discussion',
		facilitating: 'Facilitator is reviewing progress',
		waitingForFirst: 'Waiting for first contributions',
		expertsDeliberating: 'Experts are deliberating',
	},

	// Synthesis
	synthesis: {
		voting: 'Experts are forming recommendations',
		synthesizing: 'Generating final synthesis',
		metaSynthesis: 'Combining insights from all focus areas',
		complete: 'Meeting complete',
		generatingFinal: 'Generating final synthesis',
	},

	// Dashboard
	dashboard: {
		loadingMeetings: 'Loading your meetings',
		loadingStats: 'Loading statistics',
	},

	// Generic
	generic: {
		loading: 'Loading',
		processing: 'Processing',
		saving: 'Saving changes',
		pleaseWait: 'Please wait a moment',
	},
} as const;

/**
 * Rotating messages for long waits
 * Changes every few seconds to keep users engaged
 */
export const ROTATING_MESSAGES = {
	initialWait: [
		'Setting up your meeting...',
		'Assembling your expert panel...',
		'Preparing the discussion space...',
		'Almost ready...',
	],
	betweenRounds: [
		'Experts are reflecting on the discussion...',
		'Preparing next round of insights...',
		'Analyzing previous contributions...',
		'Gathering new perspectives...',
	],
	synthesis: [
		'Synthesizing insights...',
		'Combining expert perspectives...',
		'Generating final recommendations...',
		'Almost complete...',
	],
} as const;

/**
 * Get a rotating message based on elapsed time
 */
export function getRotatingMessage(
	messages: readonly string[],
	elapsedSeconds: number,
	intervalSeconds: number = 5
): string {
	const index = Math.floor(elapsedSeconds / intervalSeconds) % messages.length;
	return messages[index];
}
