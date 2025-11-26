/**
 * Quality Labels Unit Tests
 *
 * Note: Requires vitest to be installed and configured.
 * To run: npm install -D vitest && npm run test
 *
 * Reference: UX_METRICS_REFACTOR_PLAN.md § P0.1
 */

import { describe, it, expect } from 'vitest';
import {
	getExplorationLabel,
	getConvergenceMetaphor,
	getConflictLabel,
	getOverallQuality
} from './quality-labels';

describe('quality-labels', () => {
	describe('getExplorationLabel', () => {
		it('maps high scores to comprehensive', () => {
			const result = getExplorationLabel(0.88);
			expect(result.label).toBe('Comprehensively Explored');
			expect(result.color).toBe('green');
			expect(result.icon).toBe('check-circle');
		});

		it('maps thorough scores correctly', () => {
			const result = getExplorationLabel(0.75);
			expect(result.label).toBe('Thorough Discussion');
			expect(result.color).toBe('green');
		});

		it('maps moderate scores to good progress', () => {
			const result = getExplorationLabel(0.55);
			expect(result.label).toBe('Good Progress');
			expect(result.color).toBe('amber');
		});

		it('maps low scores to just starting', () => {
			const result = getExplorationLabel(0.25);
			expect(result.label).toBe('Just Getting Started');
			expect(result.color).toBe('blue'); // Blue, not red!
			expect(result.description).toContain('warming up');
		});

		it('handles edge case at threshold boundaries', () => {
			expect(getExplorationLabel(0.85).label).toBe('Comprehensively Explored');
			expect(getExplorationLabel(0.84).label).toBe('Thorough Discussion');
			expect(getExplorationLabel(0.70).label).toBe('Thorough Discussion');
			expect(getExplorationLabel(0.69).label).toBe('Good Progress');
		});
	});

	describe('getConvergenceMetaphor', () => {
		it('uses positive framing for low convergence in early rounds', () => {
			const result = getConvergenceMetaphor(0.14, 0.65, 1);
			expect(result.status).toBe('Diverse Perspectives');
			expect(result.color).toBe('blue');
			expect(result.description).toContain('expected in exploration');
		});

		it('shows clear direction for high convergence', () => {
			const result = getConvergenceMetaphor(0.90, 0.25, 5);
			expect(result.status).toBe('Clear Direction Emerging');
			expect(result.color).toBe('green');
			expect(result.description).toContain('aligning');
		});

		it('shows healthy debate for moderate convergence', () => {
			const result = getConvergenceMetaphor(0.65, 0.50, 3);
			expect(result.status).toBe('Healthy Debate');
			expect(result.color).toBe('blue');
		});

		it('handles late rounds with low convergence appropriately', () => {
			const result = getConvergenceMetaphor(0.30, 0.60, 5);
			expect(result.status).toBe('Finalizing Perspectives');
			expect(result.color).toBe('blue');
		});

		it('handles null novelty score gracefully', () => {
			const result = getConvergenceMetaphor(0.85, null, 4);
			expect(result.status).toBe('Clear Direction Emerging');
		});

		it('shows completion label when phase is complete', () => {
			const result = getConvergenceMetaphor(0.30, 0.60, 5, 'complete');
			expect(result.status).toBe('Discussion Complete');
			expect(result.color).toBe('green');
			expect(result.description).toContain('concluded');
		});

		it('shows completion label when phase is synthesis', () => {
			const result = getConvergenceMetaphor(0.30, 0.60, 5, 'synthesis');
			expect(result.status).toBe('Discussion Complete');
			expect(result.color).toBe('green');
		});

		it('shows finalizing label for late rounds with low convergence', () => {
			const result = getConvergenceMetaphor(0.30, 0.60, 6, 'discussion');
			expect(result.status).toBe('Finalizing Perspectives');
			expect(result.color).toBe('blue');
			expect(result.description).toContain('diverse viewpoints');
		});

		it('ignores phase parameter when null', () => {
			const result = getConvergenceMetaphor(0.85, null, 4, null);
			expect(result.status).toBe('Clear Direction Emerging');
		});
	});

	describe('getConflictLabel', () => {
		it('treats high conflict as positive in exploration phase', () => {
			const result = getConflictLabel(0.85, 1, 6);
			expect(result.label).toBe('Vigorous Debate');
			expect(result.color).toBe('blue');
			expect(result.description).toContain('Healthy');
		});

		it('treats high conflict as warning in convergence phase', () => {
			const result = getConflictLabel(0.85, 6, 6);
			expect(result.label).toBe('Still Debating');
			expect(result.color).toBe('amber');
		});

		it('handles moderate conflict appropriately', () => {
			const result = getConflictLabel(0.55, 3, 6);
			expect(result.label).toBe('Balanced Discussion');
			expect(result.color).toBe('green');
		});

		it('handles low conflict in exploration phase', () => {
			const result = getConflictLabel(0.20, 1, 6);
			expect(result.label).toBe('Building on Ideas');
			expect(result.color).toBe('green');
		});

		it('handles low conflict in convergence phase', () => {
			const result = getConflictLabel(0.20, 6, 6);
			expect(result.label).toBe('Aligned Thinking');
			expect(result.color).toBe('green');
		});

		it('treats challenge phase appropriately', () => {
			const result = getConflictLabel(0.75, 3, 6);
			expect(result.label).toBe('Active Discussion');
			expect(result.color).toBe('blue');
		});
	});

	describe('getOverallQuality', () => {
		it('uses meeting_completeness_index when available', () => {
			const result = getOverallQuality({
				meeting_completeness_index: 0.75,
				exploration_score: 0.50 // Should be ignored
			});
			expect(result.label).toBe('Excellent');
			expect(result.color).toBe('green');
		});

		it('falls back to exploration_score when MCI not available', () => {
			const result = getOverallQuality({
				exploration_score: 0.75
			});
			expect(result.label).toBe('Excellent');
			expect(result.color).toBe('green');
		});

		it('handles moderate MCI scores', () => {
			const result = getOverallQuality({
				meeting_completeness_index: 0.60
			});
			expect(result.label).toBe('Good Progress');
			expect(result.color).toBe('amber');
		});

		it('handles low scores with positive framing', () => {
			const result = getOverallQuality({
				exploration_score: 0.25
			});
			expect(result.label).toBe('Warming Up');
			expect(result.color).toBe('blue'); // Blue, not red!
			expect(result.description).not.toContain('bad');
			expect(result.description).not.toContain('poor');
		});

		it('handles null/undefined values gracefully', () => {
			const result = getOverallQuality({
				exploration_score: null,
				convergence_score: null
			});
			expect(result.label).toBe('Warming Up');
			expect(result.color).toBe('blue');
		});

		it('treats zero exploration as starting phase', () => {
			const result = getOverallQuality({
				exploration_score: 0
			});
			expect(result.label).toBe('Warming Up');
		});
	});

	describe('Edge Cases and Robustness', () => {
		it('handles scores at exact threshold boundaries', () => {
			// Test that thresholds are inclusive
			expect(getExplorationLabel(0.85).label).toBe('Comprehensively Explored');
			expect(getExplorationLabel(0.70).label).toBe('Thorough Discussion');
			expect(getExplorationLabel(0.40).label).toBe('Good Progress');
		});

		it('handles scores slightly below thresholds', () => {
			expect(getExplorationLabel(0.849).label).toBe('Thorough Discussion');
			expect(getExplorationLabel(0.699).label).toBe('Good Progress');
			expect(getExplorationLabel(0.399).label).toBe('Just Getting Started');
		});

		it('handles extreme values', () => {
			expect(getExplorationLabel(1.0).label).toBe('Comprehensively Explored');
			expect(getExplorationLabel(0.0).label).toBe('Just Getting Started');
		});

		it('all functions return valid color values', () => {
			const validColors = ['green', 'amber', 'blue', 'red'];

			const exploreColors = [
				getExplorationLabel(0.9).color,
				getExplorationLabel(0.5).color,
				getExplorationLabel(0.2).color
			];
			exploreColors.forEach((color) => {
				expect(validColors).toContain(color);
			});

			const convergenceColors = [
				getConvergenceMetaphor(0.9, null, 5).color,
				getConvergenceMetaphor(0.3, null, 1).color
			];
			convergenceColors.forEach((color) => {
				expect(validColors).toContain(color);
			});

			const conflictColors = [
				getConflictLabel(0.8, 1, 6).color,
				getConflictLabel(0.8, 6, 6).color
			];
			conflictColors.forEach((color) => {
				expect(validColors).toContain(color);
			});
		});
	});

	describe('Phase-Aware Logic', () => {
		it('changes interpretation based on round number', () => {
			// Same high conflict score, different interpretations
			const earlyRound = getConflictLabel(0.80, 1, 6);
			const lateRound = getConflictLabel(0.80, 6, 6);

			expect(earlyRound.color).toBe('blue'); // Positive
			expect(lateRound.color).toBe('amber'); // Warning
		});

		it('convergence metaphor adapts to phase', () => {
			// Low convergence in early vs late rounds
			const earlyRound = getConvergenceMetaphor(0.20, 0.60, 1);
			const lateRound = getConvergenceMetaphor(0.20, 0.60, 5);

			expect(earlyRound.status).toBe('Diverse Perspectives');
			expect(lateRound.status).toBe('Finalizing Perspectives');
		});

		it('completion phase overrides convergence score', () => {
			// Even with low convergence, show "complete" when meeting is done
			const result = getConvergenceMetaphor(0.20, 0.60, 5, 'complete');
			expect(result.status).toBe('Discussion Complete');
			expect(result.color).toBe('green');
		});

		it('synthesis phase shows completion', () => {
			const result = getConvergenceMetaphor(0.50, 0.60, 5, 'synthesis');
			expect(result.status).toBe('Discussion Complete');
		});
	});

	describe('No Technical Jargon Validation', () => {
		it('labels do not expose technical terms', () => {
			const bannedTerms = [
				'convergence',
				'embedding',
				'semantic',
				'threshold',
				'algorithm',
				'score',
				'percentage',
				'%'
			];

			const allLabels = [
				getExplorationLabel(0.5).label,
				getExplorationLabel(0.5).description,
				getConvergenceMetaphor(0.5, null, 3).status,
				getConvergenceMetaphor(0.5, null, 3).description,
				getConflictLabel(0.5, 3, 6).label,
				getConflictLabel(0.5, 3, 6).description,
				getOverallQuality({ exploration_score: 0.5 }).label,
				getOverallQuality({ exploration_score: 0.5 }).description
			];

			allLabels.forEach((text) => {
				const lowerText = text.toLowerCase();
				bannedTerms.forEach((term) => {
					expect(lowerText).not.toContain(term);
				});
			});
		});

		it('uses positive, user-friendly language', () => {
			const negativeTerms = ['bad', 'poor', 'failed', 'wrong', 'error'];

			const result = getExplorationLabel(0.1); // Worst case
			const text = (result.label + ' ' + result.description).toLowerCase();

			negativeTerms.forEach((term) => {
				expect(text).not.toContain(term);
			});
		});
	});
});
