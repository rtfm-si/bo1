/**
 * WeeklyPlanView Unit Tests
 * Tests the rolling 7-day window date logic
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// Test the date calculation logic directly
// This mirrors the getWeekDays() function in WeeklyPlanView.svelte
function getWeekDays(referenceDate: Date = new Date()): Date[] {
	const today = new Date(referenceDate);
	today.setHours(0, 0, 0, 0);

	const days: Date[] = [];
	for (let i = -3; i <= 3; i++) {
		const d = new Date(today);
		d.setDate(today.getDate() + i);
		days.push(d);
	}
	return days;
}

describe('WeeklyPlanView - getWeekDays', () => {
	beforeEach(() => {
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('returns array of exactly 7 dates', () => {
		const days = getWeekDays(new Date('2025-12-27'));
		expect(days).toHaveLength(7);
	});

	it('centers today at index 3 (middle of array)', () => {
		const referenceDate = new Date('2025-12-27');
		const days = getWeekDays(referenceDate);

		const centerDay = days[3];
		expect(centerDay.getDate()).toBe(27);
		expect(centerDay.getMonth()).toBe(11); // December (0-indexed)
		expect(centerDay.getFullYear()).toBe(2025);
	});

	it('first date is today-3', () => {
		const referenceDate = new Date('2025-12-27');
		const days = getWeekDays(referenceDate);

		const firstDay = days[0];
		expect(firstDay.getDate()).toBe(24); // Dec 27 - 3 = Dec 24
		expect(firstDay.getMonth()).toBe(11);
	});

	it('last date is today+3', () => {
		const referenceDate = new Date('2025-12-27');
		const days = getWeekDays(referenceDate);

		const lastDay = days[6];
		expect(lastDay.getDate()).toBe(30); // Dec 27 + 3 = Dec 30
		expect(lastDay.getMonth()).toBe(11);
	});

	it('handles month boundary crossing backward', () => {
		// Dec 2 - 3 = Nov 29
		const referenceDate = new Date('2025-12-02');
		const days = getWeekDays(referenceDate);

		const firstDay = days[0];
		expect(firstDay.getDate()).toBe(29);
		expect(firstDay.getMonth()).toBe(10); // November
	});

	it('handles month boundary crossing forward', () => {
		// Dec 30 + 3 = Jan 2
		const referenceDate = new Date('2025-12-30');
		const days = getWeekDays(referenceDate);

		const lastDay = days[6];
		expect(lastDay.getDate()).toBe(2);
		expect(lastDay.getMonth()).toBe(0); // January
		expect(lastDay.getFullYear()).toBe(2026);
	});

	it('handles year boundary crossing', () => {
		// Jan 1 - 3 = Dec 29 of previous year
		const referenceDate = new Date('2026-01-01');
		const days = getWeekDays(referenceDate);

		const firstDay = days[0];
		expect(firstDay.getDate()).toBe(29);
		expect(firstDay.getMonth()).toBe(11); // December
		expect(firstDay.getFullYear()).toBe(2025);
	});

	it('all dates have time normalized to midnight', () => {
		const referenceDate = new Date('2025-12-27T14:30:45.123');
		const days = getWeekDays(referenceDate);

		for (const day of days) {
			expect(day.getHours()).toBe(0);
			expect(day.getMinutes()).toBe(0);
			expect(day.getSeconds()).toBe(0);
			expect(day.getMilliseconds()).toBe(0);
		}
	});

	it('dates are in consecutive order', () => {
		const referenceDate = new Date('2025-12-27');
		const days = getWeekDays(referenceDate);

		for (let i = 1; i < days.length; i++) {
			const prevDay = days[i - 1].getTime();
			const currDay = days[i].getTime();
			const oneDayMs = 24 * 60 * 60 * 1000;
			expect(currDay - prevDay).toBe(oneDayMs);
		}
	});
});
