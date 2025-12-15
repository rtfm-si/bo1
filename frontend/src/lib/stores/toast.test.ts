/**
 * Toast Store Unit Tests
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { get } from 'svelte/store';

// Mock $app/environment before importing toast
vi.mock('$app/environment', () => ({
	browser: true,
}));

import { toast, DEFAULT_DURATIONS, MAX_TOASTS, _toastsStore } from './toast';

describe('toast store', () => {
	beforeEach(() => {
		vi.useFakeTimers();
		toast.clearAll();
	});

	afterEach(() => {
		toast.clearAll();
		vi.useRealTimers();
	});

	describe('addToast', () => {
		it('adds a toast to the list', () => {
			const id = toast.addToast('success', 'Test message');

			expect(id).toBeTruthy();
			expect(get(_toastsStore)).toHaveLength(1);
			expect(get(_toastsStore)[0].message).toBe('Test message');
			expect(get(_toastsStore)[0].type).toBe('success');
		});

		it('uses default duration for each type', () => {
			toast.success('Success');
			toast.info('Info');
			toast.warning('Warning');
			toast.error('Error');

			const toasts = get(_toastsStore);
			expect(toasts[0].duration).toBe(DEFAULT_DURATIONS.success);
			expect(toasts[1].duration).toBe(DEFAULT_DURATIONS.info);
			expect(toasts[2].duration).toBe(DEFAULT_DURATIONS.warning);
			expect(toasts[3].duration).toBe(DEFAULT_DURATIONS.error);
		});

		it('allows custom duration override', () => {
			toast.addToast('success', 'Test', { duration: 10000 });

			expect(get(_toastsStore)[0].duration).toBe(10000);
		});

		it('enforces max toast limit', () => {
			for (let i = 0; i < MAX_TOASTS + 2; i++) {
				toast.addToast('info', `Message ${i}`);
			}

			const toasts = get(_toastsStore);
			expect(toasts).toHaveLength(MAX_TOASTS);
			// Should have the most recent toasts
			expect(toasts[0].message).toBe('Message 2');
			expect(toasts[MAX_TOASTS - 1].message).toBe(`Message ${MAX_TOASTS + 1}`);
		});
	});

	describe('dismissToast', () => {
		it('removes a specific toast', () => {
			const id = toast.addToast('info', 'Test');
			expect(get(_toastsStore)).toHaveLength(1);

			toast.dismissToast(id);
			expect(get(_toastsStore)).toHaveLength(0);
		});

		it('does nothing for non-existent id', () => {
			toast.addToast('info', 'Test');
			toast.dismissToast('non-existent');
			expect(get(_toastsStore)).toHaveLength(1);
		});
	});

	describe('clearAll', () => {
		it('removes all toasts', () => {
			toast.addToast('success', 'One');
			toast.addToast('info', 'Two');
			toast.addToast('error', 'Three');

			expect(get(_toastsStore)).toHaveLength(3);

			toast.clearAll();
			expect(get(_toastsStore)).toHaveLength(0);
		});
	});

	describe('auto-dismiss', () => {
		it('auto-dismisses success toasts after default duration', () => {
			toast.success('Auto-dismiss me');
			expect(get(_toastsStore)).toHaveLength(1);

			vi.advanceTimersByTime(DEFAULT_DURATIONS.success - 1);
			expect(get(_toastsStore)).toHaveLength(1);

			vi.advanceTimersByTime(1);
			expect(get(_toastsStore)).toHaveLength(0);
		});

		it('auto-dismisses info toasts after default duration', () => {
			toast.info('Info message');
			expect(get(_toastsStore)).toHaveLength(1);

			vi.advanceTimersByTime(DEFAULT_DURATIONS.info);
			expect(get(_toastsStore)).toHaveLength(0);
		});

		it('does NOT auto-dismiss error toasts', () => {
			toast.error('Error message');
			expect(get(_toastsStore)).toHaveLength(1);

			// Advance far beyond any reasonable timeout
			vi.advanceTimersByTime(60000);
			expect(get(_toastsStore)).toHaveLength(1);
		});

		it('clears timeout when manually dismissed', () => {
			const id = toast.success('Manual dismiss');

			// Dismiss before timeout
			vi.advanceTimersByTime(1000);
			toast.dismissToast(id);
			expect(get(_toastsStore)).toHaveLength(0);

			// Ensure no errors from dangling timeout
			vi.advanceTimersByTime(DEFAULT_DURATIONS.success);
			expect(get(_toastsStore)).toHaveLength(0);
		});
	});

	describe('convenience methods', () => {
		it('success() adds success toast', () => {
			toast.success('Success!');
			expect(get(_toastsStore)[0].type).toBe('success');
		});

		it('error() adds error toast', () => {
			toast.error('Error!');
			expect(get(_toastsStore)[0].type).toBe('error');
		});

		it('info() adds info toast', () => {
			toast.info('Info!');
			expect(get(_toastsStore)[0].type).toBe('info');
		});

		it('warning() adds warning toast', () => {
			toast.warning('Warning!');
			expect(get(_toastsStore)[0].type).toBe('warning');
		});
	});

	describe('store subscription', () => {
		it('exposes subscribe method for Svelte reactivity', () => {
			expect(typeof toast.subscribe).toBe('function');

			let value: unknown[] = [];
			const unsubscribe = toast.subscribe((v) => {
				value = v;
			});

			expect(value).toHaveLength(0);

			toast.success('Test');
			expect(value).toHaveLength(1);

			unsubscribe();
		});
	});
});
