/**
 * Quality Label Utilities
 *
 * Translates backend technical metrics into user-friendly labels.
 * Follows prompting best practices: Explicit > Implicit, Show Don't Tell.
 *
 * Reference: UX_METRICS_REFACTOR_PLAN.md
 */

export interface QualityLabel {
	label: string;
	description: string;
	color: 'green' | 'amber' | 'blue' | 'red';
	icon?: string;
}

export interface OutcomeMetaphor {
	status: string;
	description: string;
	icon: string;
	color: string;
}

/**
 * Map exploration score to natural language.
 *
 * Exploration measures coverage of 8 critical decision aspects.
 * Backend: bo1/graph/quality_metrics.py::calculate_exploration_score_llm()
 *
 * Thresholds based on backend stopping rules:
 * - 0.85+: Comprehensively explored (meeting can end)
 * - 0.70-0.85: Thorough discussion
 * - 0.40-0.70: Good progress
 * - <0.40: Just getting started
 */
export function getExplorationLabel(score: number): QualityLabel {
	if (score >= 0.85) {
		return {
			label: 'Comprehensively Explored',
			description: 'All critical angles have been examined in depth',
			color: 'green',
			icon: 'check-circle'
		};
	}

	if (score >= 0.70) {
		return {
			label: 'Thorough Discussion',
			description: 'Key topics covered with good depth',
			color: 'green',
			icon: 'check-circle'
		};
	}

	if (score >= 0.40) {
		return {
			label: 'Good Progress',
			description: 'Building momentum, still exploring angles',
			color: 'amber',
			icon: 'arrow-right'
		};
	}

	return {
		label: 'Just Getting Started',
		description: 'Experts are warming up, more to come',
		color: 'blue',
		icon: 'play-circle'
	};
}

/**
 * Map convergence score to outcome metaphor.
 *
 * IMPORTANT: convergence_score measures SEMANTIC REPETITION, not agreement.
 * - High score (0.85+) = Experts repeating similar ideas (ready to conclude)
 * - Low score (<0.40) = Experts saying different things (exploring)
 *
 * Backend: bo1/graph/safety/loop_prevention.py::_calculate_convergence_score_semantic()
 * Algorithm: Compares embeddings, high similarity = high convergence
 *
 * UX Challenge: "Convergence" is technical jargon. Use outcome metaphors instead.
 *
 * Phase-aware: Returns completion labels when meeting is done, regardless of convergence score.
 */
export function getConvergenceMetaphor(
	convergenceScore: number,
	noveltyScore: number | null,
	currentRound: number,
	phase?: string | null
): OutcomeMetaphor {
	// PRIORITY 1: Check if meeting is complete (phase-aware)
	// This ensures we show "Discussion Complete" at the end, not "Exploring Options"
	if (phase === 'complete' || phase === 'synthesis') {
		return {
			status: 'Discussion Complete',
			description: 'Experts have concluded their deliberation',
			icon: 'check-circle',
			color: 'green'
		};
	}

	// Check for late rounds with low convergence (finalizing with diverse views)
	if (currentRound >= 5 && convergenceScore < 0.60) {
		return {
			status: 'Finalizing Perspectives',
			description: 'Experts wrapping up with diverse viewpoints',
			icon: 'message-circle',
			color: 'blue'
		};
	}

	// High convergence = repetition = aligning on solution
	if (convergenceScore >= 0.85) {
		return {
			status: 'Clear Direction Emerging',
			description: 'Experts are aligning on a path forward',
			icon: 'trending-up',
			color: 'green'
		};
	}

	// Moderate convergence = some repetition = building consensus
	if (convergenceScore >= 0.60) {
		return {
			status: 'Healthy Debate',
			description: 'Experts exploring different viewpoints',
			icon: 'message-circle',
			color: 'blue'
		};
	}

	// Low convergence = diverse perspectives = exploring
	// This is GOOD in early rounds!
	if (currentRound <= 2) {
		return {
			status: 'Diverse Perspectives',
			description: 'Experts bringing unique angles (expected in exploration)',
			icon: 'layers',
			color: 'blue' // Blue = neutral/positive, not red/warning
		};
	}

	return {
		status: 'Exploring Options',
		description: 'Wide range of ideas being considered',
		icon: 'compass',
		color: 'amber'
	};
}

/**
 * Map conflict score to phase-aware interpretation.
 *
 * Conflict measures disagreement vs agreement keywords.
 * Backend: bo1/graph/quality_metrics.py::calculate_conflict_score()
 *
 * Phase-aware interpretation:
 * - Exploration phase (rounds 1-2): High conflict = GOOD (diverse debate)
 * - Convergence phase (rounds 5-6): High conflict = WARNING (not aligning)
 */
export function getConflictLabel(
	conflictScore: number,
	currentRound: number,
	maxRounds: number
): QualityLabel {
	const phase =
		currentRound <= 2 ? 'exploration' : currentRound >= maxRounds - 1 ? 'convergence' : 'challenge';

	// High conflict (0.7+)
	if (conflictScore >= 0.7) {
		if (phase === 'exploration') {
			return {
				label: 'Vigorous Debate',
				description: 'Healthy disagreement surfacing diverse viewpoints',
				color: 'blue', // Positive in exploration!
				icon: 'zap'
			};
		} else if (phase === 'convergence') {
			return {
				label: 'Still Debating',
				description: 'Experts haven\'t fully aligned yet',
				color: 'amber',
				icon: 'message-circle'
			};
		} else {
			return {
				label: 'Active Discussion',
				description: 'Experts challenging ideas and assumptions',
				color: 'blue',
				icon: 'message-circle'
			};
		}
	}

	// Moderate conflict (0.4-0.7)
	if (conflictScore >= 0.4) {
		return {
			label: 'Balanced Discussion',
			description: 'Mix of agreement and constructive challenge',
			color: 'green',
			icon: 'check-circle'
		};
	}

	// Low conflict (<0.4)
	if (phase === 'exploration') {
		return {
			label: 'Building on Ideas',
			description: 'Experts finding common ground early',
			color: 'green',
			icon: 'check-circle'
		};
	}

	return {
		label: 'Aligned Thinking',
		description: 'Strong consensus forming',
		color: 'green',
		icon: 'check-circle'
	};
}

/**
 * Generate composite quality summary.
 *
 * Combines multiple metrics into single user-facing assessment.
 * Prioritizes simplicity over completeness.
 */
export function getOverallQuality(metrics: {
	exploration_score?: number | null;
	convergence_score?: number | null;
	focus_score?: number | null;
	novelty_score?: number | null;
	meeting_completeness_index?: number | null;
}): QualityLabel {
	// DEBUG: Log incoming metrics to diagnose the issue
	console.log('[getOverallQuality] Received metrics:', {
		exploration_score: metrics.exploration_score,
		convergence_score: metrics.convergence_score,
		focus_score: metrics.focus_score,
		novelty_score: metrics.novelty_score,
		meeting_completeness_index: metrics.meeting_completeness_index
	});

	// PRIORITY 1: Use exploration_score (most direct indicator of topic coverage)
	// This is the primary quality metric - measures coverage of 8 critical decision aspects
	if (
		typeof metrics.exploration_score === 'number' &&
		metrics.exploration_score > 0
	) {
		const exploration = metrics.exploration_score;
		console.log('[getOverallQuality] Using exploration_score (primary):', exploration);

		if (exploration >= 0.7) {
			return {
				label: 'Excellent',
				description: 'Thorough discussion covering all key aspects',
				color: 'green',
				icon: 'check-circle'
			};
		}

		if (exploration >= 0.4) {
			return {
				label: 'Good Progress',
				description: 'Building toward comprehensive coverage',
				color: 'amber',
				icon: 'trending-up'
			};
		}

		return {
			label: 'Early Exploration',
			description: 'Experts are diving into your question. More insights coming.',
			color: 'blue',
			icon: 'compass'
		};
	}

	// Last fallback: Use convergence score as a proxy
	if (
		typeof metrics.convergence_score === 'number' &&
		metrics.convergence_score > 0
	) {
		const convergence = metrics.convergence_score;
		console.log('[getOverallQuality] Using convergence_score as last fallback:', convergence);

		if (convergence >= 0.7) {
			return {
				label: 'Good Progress',
				description: 'Experts are building toward consensus.',
				color: 'amber',
				icon: 'trending-up'
			};
		}

		return {
			label: 'Early Exploration',
			description: 'Experts are diving into your question. More insights coming.',
			color: 'blue',
			icon: 'compass'
		};
	}

	// No valid metrics available - show default
	console.warn('[getOverallQuality] No valid quality metrics available, showing default');
	return {
		label: 'Warming Up',
		description: 'Experts are getting oriented. More depth to come.',
		color: 'blue',
		icon: 'play-circle'
	};
}
