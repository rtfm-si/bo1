/**
 * BenchmarkRangeBar Component Unit Tests
 *
 * Tests marker position calculation, color coding, and edge cases
 */

import { describe, it, expect } from 'vitest';

// Test the core logic extracted from the component

// Calculate extended range (20% beyond P25-P75 on each side)
function calculateExtendedRange(rangeMin: number, rangeMax: number): { extendedMin: number; extendedMax: number } {
	const spread = rangeMax - rangeMin;
	return {
		extendedMin: rangeMin - spread * 0.2,
		extendedMax: rangeMax + spread * 0.2,
	};
}

// Calculate marker position as percentage (0-100)
function calculateMarkerPosition(
	userValue: number | null | undefined,
	rangeMin: number,
	rangeMax: number
): number | null {
	if (userValue === null || userValue === undefined) return null;

	const { extendedMin, extendedMax } = calculateExtendedRange(rangeMin, rangeMax);
	const range = extendedMax - extendedMin;
	if (range === 0) return 50;

	const pos = ((userValue - extendedMin) / range) * 100;
	// Clamp to 2-98% so marker stays visible at edges
	return Math.max(2, Math.min(98, pos));
}

// Calculate range positions
function calculateRangePositions(rangeMin: number, rangeMedian: number, rangeMax: number) {
	const { extendedMin, extendedMax } = calculateExtendedRange(rangeMin, rangeMax);
	const totalRange = extendedMax - extendedMin;

	return {
		rangeStartPos: ((rangeMin - extendedMin) / totalRange) * 100,
		rangeEndPos: ((rangeMax - extendedMin) / totalRange) * 100,
		medianPos: ((rangeMedian - extendedMin) / totalRange) * 100,
	};
}

// Get marker color based on status
function getMarkerColor(status: string): string {
	switch (status) {
		case 'top_performer':
			return 'bg-green-500';
		case 'above_average':
			return 'bg-emerald-500';
		case 'average':
			return 'bg-yellow-500';
		case 'below_average':
			return 'bg-red-500';
		default:
			return 'bg-slate-400';
	}
}

// Format value with unit
function formatValue(val: number, unit: string): string {
	if (unit === '%') return `${val}%`;
	if (unit) return `${val} ${unit}`;
	return String(val);
}

describe('BenchmarkRangeBar', () => {
	describe('calculateMarkerPosition', () => {
		it('returns null for null user value', () => {
			expect(calculateMarkerPosition(null, 10, 30)).toBeNull();
		});

		it('returns null for undefined user value', () => {
			expect(calculateMarkerPosition(undefined, 10, 30)).toBeNull();
		});

		it('returns 50% when range is zero', () => {
			expect(calculateMarkerPosition(20, 20, 20)).toBe(50);
		});

		it('positions user at median correctly', () => {
			// Range 10-30, median would be 20
			// Extended range: 10 - 4 = 6, 30 + 4 = 34 (total 28)
			// Position of 20 in extended range: (20-6)/28 = 0.5 = 50%
			const pos = calculateMarkerPosition(20, 10, 30);
			expect(pos).toBeCloseTo(50, 0);
		});

		it('positions user at bottom of range correctly', () => {
			// User at P25 (rangeMin)
			const pos = calculateMarkerPosition(10, 10, 30);
			// Extended range: 6-34, rangeMin (10) is at (10-6)/28 = 14.3%
			expect(pos).toBeCloseTo(14.3, 0);
		});

		it('positions user at top of range correctly', () => {
			// User at P75 (rangeMax)
			const pos = calculateMarkerPosition(30, 10, 30);
			// Extended range: 6-34, rangeMax (30) is at (30-6)/28 = 85.7%
			expect(pos).toBeCloseTo(85.7, 0);
		});

		it('clamps position to minimum 2% for very low values', () => {
			// User value far below range
			const pos = calculateMarkerPosition(-100, 10, 30);
			expect(pos).toBe(2);
		});

		it('clamps position to maximum 98% for very high values', () => {
			// User value far above range
			const pos = calculateMarkerPosition(200, 10, 30);
			expect(pos).toBe(98);
		});

		it('handles negative ranges correctly', () => {
			// For metrics where lower is better (e.g., churn rate)
			const pos = calculateMarkerPosition(-5, -10, -2);
			expect(pos).toBeGreaterThan(0);
			expect(pos).toBeLessThan(100);
		});
	});

	describe('calculateRangePositions', () => {
		it('calculates range start at ~14% of extended range', () => {
			const { rangeStartPos } = calculateRangePositions(10, 20, 30);
			// Extended: 6-34 (28 total), rangeMin at 10 = (10-6)/28 = 14.3%
			expect(rangeStartPos).toBeCloseTo(14.3, 0);
		});

		it('calculates range end at ~86% of extended range', () => {
			const { rangeEndPos } = calculateRangePositions(10, 20, 30);
			// Extended: 6-34 (28 total), rangeMax at 30 = (30-6)/28 = 85.7%
			expect(rangeEndPos).toBeCloseTo(85.7, 0);
		});

		it('calculates median at 50% of extended range', () => {
			const { medianPos } = calculateRangePositions(10, 20, 30);
			// Extended: 6-34 (28 total), median at 20 = (20-6)/28 = 50%
			expect(medianPos).toBeCloseTo(50, 0);
		});

		it('handles asymmetric ranges', () => {
			// Median not exactly at midpoint
			const { medianPos, rangeStartPos, rangeEndPos } = calculateRangePositions(10, 15, 30);
			expect(rangeStartPos).toBeLessThan(medianPos);
			expect(medianPos).toBeLessThan(rangeEndPos);
		});
	});

	describe('getMarkerColor', () => {
		it('returns green for top_performer', () => {
			expect(getMarkerColor('top_performer')).toBe('bg-green-500');
		});

		it('returns emerald for above_average', () => {
			expect(getMarkerColor('above_average')).toBe('bg-emerald-500');
		});

		it('returns yellow for average', () => {
			expect(getMarkerColor('average')).toBe('bg-yellow-500');
		});

		it('returns red for below_average', () => {
			expect(getMarkerColor('below_average')).toBe('bg-red-500');
		});

		it('returns slate for no_data', () => {
			expect(getMarkerColor('no_data')).toBe('bg-slate-400');
		});

		it('returns slate for unknown status', () => {
			expect(getMarkerColor('unknown')).toBe('bg-slate-400');
		});
	});

	describe('formatValue', () => {
		it('formats percentage values', () => {
			expect(formatValue(25, '%')).toBe('25%');
		});

		it('formats values with custom units', () => {
			expect(formatValue(100, 'users')).toBe('100 users');
		});

		it('formats values with empty unit', () => {
			expect(formatValue(42, '')).toBe('42');
		});

		it('handles decimal values', () => {
			expect(formatValue(3.14, '%')).toBe('3.14%');
		});

		it('handles zero', () => {
			expect(formatValue(0, '%')).toBe('0%');
		});

		it('handles negative values', () => {
			expect(formatValue(-5, '%')).toBe('-5%');
		});
	});

	describe('edge cases', () => {
		it('handles very small ranges', () => {
			const pos = calculateMarkerPosition(10.5, 10, 11);
			expect(pos).toBeGreaterThan(0);
			expect(pos).toBeLessThan(100);
		});

		it('handles very large ranges', () => {
			const pos = calculateMarkerPosition(50000, 10000, 100000);
			expect(pos).toBeGreaterThan(0);
			expect(pos).toBeLessThan(100);
		});

		it('handles zero as valid value', () => {
			const pos = calculateMarkerPosition(0, -10, 10);
			expect(pos).toBeCloseTo(50, 0);
		});
	});
});
