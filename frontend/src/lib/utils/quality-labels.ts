/**
 * Quality Label Utilities
 *
 * Translates backend technical metrics into user-friendly labels.
 * Follows prompting best practices: Explicit > Implicit, Show Don't Tell.
 *
 * Reference: UX_METRICS_REFACTOR_PLAN.md
 *
 * REFACTORED: Converted if/else chains to object-based lookups for better
 * maintainability and testability.
 */

// ============================================================================
// CONSTANTS - Centralized thresholds (previously magic numbers)
// ============================================================================

export const QUALITY_THRESHOLDS = {
	/** Comprehensively explored / Clear direction emerging */
	EXCELLENT: 0.85,
	/** Thorough discussion / Healthy debate */
	GOOD: 0.70,
	/** Moderate / Building consensus */
	MODERATE: 0.60,
	/** Good progress / Building momentum */
	PROGRESS: 0.40,
	/** High conflict threshold */
	HIGH_CONFLICT: 0.70,
	/** Moderate conflict threshold */
	MODERATE_CONFLICT: 0.40
} as const;

export const ROUND_THRESHOLDS = {
	/** Rounds 1-2: Exploration phase */
	EXPLORATION_END: 2,
	/** Rounds 5+: Convergence phase */
	CONVERGENCE_START: 5
} as const;

// ============================================================================
// INTERFACES
// ============================================================================

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

// ============================================================================
// LOOKUP TABLES
// ============================================================================

type ExplorationTier = 'excellent' | 'good' | 'progress' | 'early';

const EXPLORATION_LABELS: Record<ExplorationTier, QualityLabel> = {
	excellent: {
		label: 'Comprehensively Explored',
		description: 'All critical angles have been examined in depth',
		color: 'green',
		icon: 'check-circle'
	},
	good: {
		label: 'Thorough Discussion',
		description: 'Key topics covered with good depth',
		color: 'green',
		icon: 'check-circle'
	},
	progress: {
		label: 'Good Progress',
		description: 'Building momentum, still exploring angles',
		color: 'amber',
		icon: 'arrow-right'
	},
	early: {
		label: 'Just Getting Started',
		description: 'Experts are warming up, more to come',
		color: 'blue',
		icon: 'play-circle'
	}
};

type PhaseType = 'exploration' | 'convergence' | 'challenge';
type ConflictLevel = 'high' | 'moderate' | 'low';

const CONFLICT_LABELS: Record<PhaseType, Record<ConflictLevel, QualityLabel>> = {
	exploration: {
		high: {
			label: 'Vigorous Debate',
			description: 'Healthy disagreement surfacing diverse viewpoints',
			color: 'blue',
			icon: 'zap'
		},
		moderate: {
			label: 'Balanced Discussion',
			description: 'Mix of agreement and constructive challenge',
			color: 'green',
			icon: 'check-circle'
		},
		low: {
			label: 'Building on Ideas',
			description: 'Experts finding common ground early',
			color: 'green',
			icon: 'check-circle'
		}
	},
	convergence: {
		high: {
			label: 'Still Debating',
			description: "Experts haven't fully aligned yet",
			color: 'amber',
			icon: 'message-circle'
		},
		moderate: {
			label: 'Balanced Discussion',
			description: 'Mix of agreement and constructive challenge',
			color: 'green',
			icon: 'check-circle'
		},
		low: {
			label: 'Aligned Thinking',
			description: 'Strong consensus forming',
			color: 'green',
			icon: 'check-circle'
		}
	},
	challenge: {
		high: {
			label: 'Active Discussion',
			description: 'Experts challenging ideas and assumptions',
			color: 'blue',
			icon: 'message-circle'
		},
		moderate: {
			label: 'Balanced Discussion',
			description: 'Mix of agreement and constructive challenge',
			color: 'green',
			icon: 'check-circle'
		},
		low: {
			label: 'Aligned Thinking',
			description: 'Strong consensus forming',
			color: 'green',
			icon: 'check-circle'
		}
	}
};

type ConvergencePhase = 'complete' | 'finalizing' | 'aligning' | 'debating' | 'exploring' | 'diverse';

const CONVERGENCE_METAPHORS: Record<ConvergencePhase, OutcomeMetaphor> = {
	complete: {
		status: 'Discussion Complete',
		description: 'Experts have concluded their deliberation',
		icon: 'check-circle',
		color: 'green'
	},
	finalizing: {
		status: 'Finalizing Perspectives',
		description: 'Experts wrapping up with diverse viewpoints',
		icon: 'message-circle',
		color: 'blue'
	},
	aligning: {
		status: 'Clear Direction Emerging',
		description: 'Experts are aligning on a path forward',
		icon: 'trending-up',
		color: 'green'
	},
	debating: {
		status: 'Healthy Debate',
		description: 'Experts exploring different viewpoints',
		icon: 'message-circle',
		color: 'blue'
	},
	exploring: {
		status: 'Exploring Options',
		description: 'Wide range of ideas being considered',
		icon: 'compass',
		color: 'amber'
	},
	diverse: {
		status: 'Diverse Perspectives',
		description: 'Experts bringing unique angles (expected in exploration)',
		icon: 'layers',
		color: 'blue'
	}
};

type QualityTier = 'excellent' | 'good' | 'early' | 'warming';

const OVERALL_QUALITY_LABELS: Record<QualityTier, QualityLabel> = {
	excellent: {
		label: 'Excellent',
		description: 'Thorough discussion covering all key aspects',
		color: 'green',
		icon: 'check-circle'
	},
	good: {
		label: 'Good Progress',
		description: 'Building toward comprehensive coverage',
		color: 'amber',
		icon: 'trending-up'
	},
	early: {
		label: 'Early Exploration',
		description: 'Experts are diving into your question. More insights coming.',
		color: 'blue',
		icon: 'compass'
	},
	warming: {
		label: 'Warming Up',
		description: 'Experts are getting oriented. More depth to come.',
		color: 'blue',
		icon: 'play-circle'
	}
};

// ============================================================================
// HELPER FUNCTIONS - Pure, testable tier determination
// ============================================================================

function getExplorationTier(score: number): ExplorationTier {
	if (score >= QUALITY_THRESHOLDS.EXCELLENT) return 'excellent';
	if (score >= QUALITY_THRESHOLDS.GOOD) return 'good';
	if (score >= QUALITY_THRESHOLDS.PROGRESS) return 'progress';
	return 'early';
}

function getPhaseType(currentRound: number, maxRounds: number): PhaseType {
	if (currentRound <= ROUND_THRESHOLDS.EXPLORATION_END) return 'exploration';
	if (currentRound >= maxRounds - 1) return 'convergence';
	return 'challenge';
}

function getConflictLevel(score: number): ConflictLevel {
	if (score >= QUALITY_THRESHOLDS.HIGH_CONFLICT) return 'high';
	if (score >= QUALITY_THRESHOLDS.MODERATE_CONFLICT) return 'moderate';
	return 'low';
}

function getConvergencePhase(
	score: number,
	currentRound: number,
	phase?: string | null
): ConvergencePhase {
	if (phase === 'complete' || phase === 'synthesis') return 'complete';
	if (currentRound >= ROUND_THRESHOLDS.CONVERGENCE_START && score < QUALITY_THRESHOLDS.MODERATE) {
		return 'finalizing';
	}
	if (score >= QUALITY_THRESHOLDS.EXCELLENT) return 'aligning';
	if (score >= QUALITY_THRESHOLDS.MODERATE) return 'debating';
	if (currentRound <= ROUND_THRESHOLDS.EXPLORATION_END) return 'diverse';
	return 'exploring';
}

function getQualityTier(
	exploration: number | null | undefined,
	convergence: number | null | undefined
): QualityTier {
	if (typeof exploration === 'number' && exploration > 0) {
		if (exploration >= QUALITY_THRESHOLDS.GOOD) return 'excellent';
		if (exploration >= QUALITY_THRESHOLDS.PROGRESS) return 'good';
		return 'early';
	}
	if (typeof convergence === 'number' && convergence > 0) {
		if (convergence >= QUALITY_THRESHOLDS.GOOD) return 'good';
		return 'early';
	}
	return 'warming';
}

// ============================================================================
// PUBLIC API - Clean, simple functions using lookup tables
// ============================================================================

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
	return EXPLORATION_LABELS[getExplorationTier(score)];
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
	return CONVERGENCE_METAPHORS[getConvergencePhase(convergenceScore, currentRound, phase)];
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
	const phase = getPhaseType(currentRound, maxRounds);
	const level = getConflictLevel(conflictScore);
	return CONFLICT_LABELS[phase][level];
}

/**
 * Generate composite quality summary.
 *
 * Combines multiple metrics into single user-facing assessment.
 * Prioritizes simplicity over completeness.
 * Phase-aware: returns completion label when meeting is done.
 */
export function getOverallQuality(
	metrics: {
		exploration_score?: number | null;
		convergence_score?: number | null;
		focus_score?: number | null;
		novelty_score?: number | null;
		meeting_completeness_index?: number | null;
	},
	phase?: string | null
): QualityLabel {
	// If meeting is complete, return completed label regardless of scores
	if (phase === 'complete' || phase === 'synthesis') {
		return {
			label: 'Discussion Complete',
			description: 'Experts have concluded their deliberation.',
			color: 'green',
			icon: 'check-circle'
		};
	}
	const tier = getQualityTier(metrics.exploration_score, metrics.convergence_score);
	return OVERALL_QUALITY_LABELS[tier];
}
