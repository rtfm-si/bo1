/**
 * Decision Matrix utilities for weighted scoring and sensitivity analysis.
 */

import type { OptionCard } from '$lib/api/sse-events';

export interface Criterion {
	key: string;
	label: string;
	weight: number;
}

export interface WeightedScores {
	[optionId: string]: number;
}

export interface SensitivityResult {
	criterion: string;
	current_winner: string;
	flip_delta: number;
	new_winner: string;
}

/**
 * Default criteria derived from ConstraintType values
 */
export function getDefaultCriteria(): Criterion[] {
	return [
		{ key: 'feasibility', label: 'Feasibility', weight: 1 },
		{ key: 'cost_efficiency', label: 'Cost Efficiency', weight: 1 },
		{ key: 'speed', label: 'Speed', weight: 1 },
		{ key: 'risk_level', label: 'Low Risk', weight: 1 },
		{ key: 'alignment', label: 'Alignment', weight: 1 }
	];
}

/**
 * Compute weighted scores for each option
 */
export function computeWeightedScores(
	options: OptionCard[],
	criteria: Criterion[]
): WeightedScores {
	const scores: WeightedScores = {};
	const totalWeight = criteria.reduce((sum, c) => sum + c.weight, 0) || 1;

	for (const option of options) {
		let score = 0;
		for (const criterion of criteria) {
			const raw = option.criteria_scores?.[criterion.key] ?? 0.5;
			score += raw * criterion.weight;
		}
		scores[option.id] = Math.round((score / totalWeight) * 100) / 100;
	}

	return scores;
}

/**
 * Find the winning option ID from scores
 */
export function getWinner(scores: WeightedScores): string {
	let bestId = '';
	let bestScore = -1;
	for (const [id, score] of Object.entries(scores)) {
		if (score > bestScore) {
			bestScore = score;
			bestId = id;
		}
	}
	return bestId;
}

/**
 * Sensitivity analysis: How much does each weight need to change
 * to flip the winner?
 */
export function computeSensitivity(
	options: OptionCard[],
	criteria: Criterion[]
): SensitivityResult[] {
	const results: SensitivityResult[] = [];
	const baseScores = computeWeightedScores(options, criteria);
	const currentWinner = getWinner(baseScores);

	for (const criterion of criteria) {
		// Try increasing weight by 1-10 to find flip point
		for (let delta = 1; delta <= 10; delta++) {
			const modified = criteria.map((c) =>
				c.key === criterion.key ? { ...c, weight: c.weight + delta } : c
			);
			const newScores = computeWeightedScores(options, modified);
			const newWinner = getWinner(newScores);

			if (newWinner !== currentWinner) {
				const winnerOption = options.find((o) => o.id === newWinner);
				results.push({
					criterion: criterion.label,
					current_winner: currentWinner,
					flip_delta: delta,
					new_winner: winnerOption?.label ?? newWinner
				});
				break;
			}
		}
	}

	return results;
}
