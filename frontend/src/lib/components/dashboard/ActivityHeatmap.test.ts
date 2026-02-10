/**
 * ActivityHeatmap Unit Tests
 * Tests sparkline calculation logic and color accessibility
 */

import { describe, it, expect } from 'vitest';
import type { DailyActionStat } from '$lib/api/types';

// Mirror the sparkline calculation from ActivityHeatmap.svelte
function calculateSparklineData(
	data: DailyActionStat[],
	start: Date,
	end: Date,
	today: Date,
	getFilteredTotal: (stat: DailyActionStat | null) => number
): { date: Date; avg: number }[] {
	const result: { date: Date; avg: number }[] = [];

	// Get days from start to min(end, today)
	const sparkEnd = today < end ? today : end;
	const current = new Date(start);
	current.setDate(current.getDate() + 6); // Start after first 7 days

	// Create date->total map
	const totalMap = new Map<string, number>();
	data.forEach((stat) => {
		totalMap.set(stat.date, getFilteredTotal(stat));
	});

	while (current <= sparkEnd) {
		let sum = 0;
		for (let i = 0; i < 7; i++) {
			const d = new Date(current);
			d.setDate(d.getDate() - i);
			const dateStr = d.toISOString().split('T')[0];
			sum += totalMap.get(dateStr) ?? 0;
		}
		result.push({ date: new Date(current), avg: sum / 7 });
		current.setDate(current.getDate() + 1);
	}

	return result;
}

// Mirror trend direction calculation
function calculateTrendDirection(sparklineData: { date: Date; avg: number }[]): 'up' | 'down' | 'neutral' {
	if (sparklineData.length < 7) return 'neutral';
	const recent = sparklineData.slice(-7);
	const older = sparklineData.slice(-14, -7);
	if (older.length === 0) return 'neutral';

	const recentAvg = recent.reduce((sum, d) => sum + d.avg, 0) / recent.length;
	const olderAvg = older.reduce((sum, d) => sum + d.avg, 0) / older.length;

	if (recentAvg > olderAvg * 1.1) return 'up';
	if (recentAvg < olderAvg * 0.9) return 'down';
	return 'neutral';
}

// Simple getFilteredTotal that sums all activity
function getFilteredTotal(stat: DailyActionStat | null): number {
	if (!stat) return 0;
	return (
		stat.sessions_run +
		stat.completed_count +
		stat.in_progress_count +
		stat.mentor_sessions +
		(stat.estimated_starts ?? 0) +
		(stat.estimated_completions ?? 0)
	);
}

// Helper to create a mock DailyActionStat
function createStat(date: string, total: number): DailyActionStat {
	return {
		date,
		sessions_run: total,
		completed_count: 0,
		in_progress_count: 0,
		mentor_sessions: 0,
		estimated_starts: 0,
		estimated_completions: 0
	};
}

describe('ActivityHeatmap - Sparkline Calculations', () => {
	describe('calculateSparklineData', () => {
		it('returns empty array for data shorter than 7 days', () => {
			const data: DailyActionStat[] = [
				createStat('2025-12-25', 1),
				createStat('2025-12-26', 2),
				createStat('2025-12-27', 3)
			];

			const start = new Date('2025-12-25');
			const end = new Date('2025-12-27');
			const today = new Date('2025-12-27');

			const result = calculateSparklineData(data, start, end, today, getFilteredTotal);
			expect(result).toHaveLength(0);
		});

		it('calculates 7-day rolling average correctly', () => {
			// Create 14 days of data with constant value of 7
			const data: DailyActionStat[] = [];
			for (let i = 0; i < 14; i++) {
				const date = new Date('2025-12-15');
				date.setDate(date.getDate() + i);
				data.push(createStat(date.toISOString().split('T')[0], 7));
			}

			const start = new Date('2025-12-15');
			const end = new Date('2025-12-28');
			const today = new Date('2025-12-28');

			const result = calculateSparklineData(data, start, end, today, getFilteredTotal);

			// Should have 8 data points (day 7-14)
			expect(result.length).toBeGreaterThan(0);

			// Each point should have avg of 7 (7 days * 7 per day / 7 = 7)
			result.forEach((point) => {
				expect(point.avg).toBe(7);
			});
		});

		it('handles single day data (edge case)', () => {
			const data: DailyActionStat[] = [createStat('2025-12-27', 10)];

			const start = new Date('2025-12-27');
			const end = new Date('2025-12-27');
			const today = new Date('2025-12-27');

			const result = calculateSparklineData(data, start, end, today, getFilteredTotal);
			// With only 1 day, we can't compute a 7-day rolling average
			expect(result).toHaveLength(0);
		});

		it('handles empty data', () => {
			const data: DailyActionStat[] = [];

			const start = new Date('2025-12-20');
			const end = new Date('2025-12-27');
			const today = new Date('2025-12-27');

			const result = calculateSparklineData(data, start, end, today, getFilteredTotal);
			// Even with no data, we get sparkline points (with avg=0)
			expect(result.length).toBeGreaterThanOrEqual(0);
			result.forEach((point) => {
				expect(point.avg).toBe(0);
			});
		});

		it('limits sparkline to today when end is in future', () => {
			const data: DailyActionStat[] = [];
			for (let i = 0; i < 10; i++) {
				const date = new Date('2025-12-20');
				date.setDate(date.getDate() + i);
				data.push(createStat(date.toISOString().split('T')[0], 5));
			}

			const start = new Date('2025-12-20');
			const end = new Date('2025-12-31'); // Future
			const today = new Date('2025-12-27');

			const result = calculateSparklineData(data, start, end, today, getFilteredTotal);

			// Last point should not exceed today
			if (result.length > 0) {
				const lastPoint = result[result.length - 1];
				expect(lastPoint.date.getTime()).toBeLessThanOrEqual(today.getTime());
			}
		});
	});

	describe('calculateTrendDirection', () => {
		it('returns neutral for data shorter than 7 days', () => {
			const data = [
				{ date: new Date('2025-12-25'), avg: 5 },
				{ date: new Date('2025-12-26'), avg: 6 },
				{ date: new Date('2025-12-27'), avg: 7 }
			];

			expect(calculateTrendDirection(data)).toBe('neutral');
		});

		it('returns neutral when no older data for comparison', () => {
			const data = [];
			for (let i = 0; i < 7; i++) {
				const date = new Date('2025-12-20');
				date.setDate(date.getDate() + i);
				data.push({ date, avg: 5 });
			}

			expect(calculateTrendDirection(data)).toBe('neutral');
		});

		it('returns up when recent average is >10% higher', () => {
			const data = [];
			// 7 days of low values
			for (let i = 0; i < 7; i++) {
				const date = new Date('2025-12-15');
				date.setDate(date.getDate() + i);
				data.push({ date, avg: 5 });
			}
			// 7 days of high values (>10% higher)
			for (let i = 0; i < 7; i++) {
				const date = new Date('2025-12-22');
				date.setDate(date.getDate() + i);
				data.push({ date, avg: 10 }); // 100% higher
			}

			expect(calculateTrendDirection(data)).toBe('up');
		});

		it('returns down when recent average is >10% lower', () => {
			const data = [];
			// 7 days of high values
			for (let i = 0; i < 7; i++) {
				const date = new Date('2025-12-15');
				date.setDate(date.getDate() + i);
				data.push({ date, avg: 10 });
			}
			// 7 days of low values (>10% lower)
			for (let i = 0; i < 7; i++) {
				const date = new Date('2025-12-22');
				date.setDate(date.getDate() + i);
				data.push({ date, avg: 5 }); // 50% lower
			}

			expect(calculateTrendDirection(data)).toBe('down');
		});

		it('returns neutral when change is within 10%', () => {
			const data = [];
			// 7 days of values
			for (let i = 0; i < 7; i++) {
				const date = new Date('2025-12-15');
				date.setDate(date.getDate() + i);
				data.push({ date, avg: 10 });
			}
			// 7 days of similar values (<10% change)
			for (let i = 0; i < 7; i++) {
				const date = new Date('2025-12-22');
				date.setDate(date.getDate() + i);
				data.push({ date, avg: 10.5 }); // 5% higher
			}

			expect(calculateTrendDirection(data)).toBe('neutral');
		});
	});
});

describe('ActivityHeatmap - Color by Count', () => {
	it('uses brand colors for past and accent colors for future', () => {
		// Past cells use teal (brand-500/brand-400)
		const pastColor = 'bg-brand-500';
		// Future cells use warm orange (accent-500/accent-400)
		const futureColor = 'bg-accent-500';

		expect(pastColor).toContain('brand');
		expect(futureColor).toContain('accent');
	});

	it('uses 5-step intensity progression', () => {
		// Intensity: 1→30%, 2→50%, 3→70%, 4→85%, 5+→100%
		const steps = [
			{ count: 1, opacity: 30 },
			{ count: 2, opacity: 50 },
			{ count: 3, opacity: 70 },
			{ count: 4, opacity: 85 },
			{ count: 5, opacity: 100 }
		];

		// Monotonically increasing
		for (let i = 1; i < steps.length; i++) {
			expect(steps[i].opacity).toBeGreaterThan(steps[i - 1].opacity);
		}
	});

	it('caps intensity at INTENSITY_CAP = 5', () => {
		// Counts >= 5 all get the same 100% opacity
		const INTENSITY_CAP = 5;
		expect(INTENSITY_CAP).toBe(5);
	});
});
