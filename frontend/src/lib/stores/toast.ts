/**
 * Toast Store
 *
 * Centralized store for managing toast notifications.
 * Uses Svelte writable store for compatibility with both Svelte 4/5 and vitest.
 *
 * Default auto-dismiss durations:
 * - success: 3000ms
 * - info: 5000ms
 * - warning: 7000ms
 * - error: 0 (manual dismiss required)
 */

import { writable, get } from 'svelte/store';
import { browser } from '$app/environment';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
	id: string;
	type: ToastType;
	message: string;
	duration: number;
	createdAt: number;
}

export interface ToastOptions {
	duration?: number;
}

// Default durations per type (ms)
const DEFAULT_DURATIONS: Record<ToastType, number> = {
	success: 3000,
	info: 5000,
	warning: 7000,
	error: 0, // No auto-dismiss for errors
};

// Maximum visible toasts to prevent flooding
const MAX_TOASTS = 5;

// Generate unique ID
function generateId(): string {
	return `toast-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

// Internal state
const toastsStore = writable<Toast[]>([]);
const timeouts = new Map<string, ReturnType<typeof setTimeout>>();

/**
 * Add a new toast notification
 */
function addToast(type: ToastType, message: string, options?: ToastOptions): string {
	if (!browser) return '';

	const id = generateId();
	const duration = options?.duration ?? DEFAULT_DURATIONS[type];

	const newToast: Toast = {
		id,
		type,
		message,
		duration,
		createdAt: Date.now(),
	};

	toastsStore.update((toasts) => {
		// Remove oldest if at max
		let updated = [...toasts];
		if (updated.length >= MAX_TOASTS) {
			const oldest = updated[0];
			dismissToast(oldest.id);
			updated = updated.slice(1);
		}
		return [...updated, newToast];
	});

	// Set auto-dismiss timeout if duration > 0
	if (duration > 0) {
		const timeout = setTimeout(() => {
			dismissToast(id);
		}, duration);
		timeouts.set(id, timeout);
	}

	return id;
}

/**
 * Dismiss a specific toast
 */
function dismissToast(id: string): void {
	// Clear timeout if exists
	const timeout = timeouts.get(id);
	if (timeout) {
		clearTimeout(timeout);
		timeouts.delete(id);
	}

	// Remove from list
	toastsStore.update((toasts) => toasts.filter((t) => t.id !== id));
}

/**
 * Clear all toasts
 */
function clearAll(): void {
	// Clear all timeouts
	for (const timeout of timeouts.values()) {
		clearTimeout(timeout);
	}
	timeouts.clear();

	// Clear all toasts
	toastsStore.set([]);
}

// Toast API object with convenience methods
export const toast = {
	subscribe: toastsStore.subscribe,

	/** Get current toasts (for reactive access in components) */
	get toasts() {
		return get(toastsStore);
	},

	addToast,
	dismissToast,
	clearAll,

	// Convenience methods
	success: (message: string, options?: ToastOptions) => addToast('success', message, options),
	error: (message: string, options?: ToastOptions) => addToast('error', message, options),
	info: (message: string, options?: ToastOptions) => addToast('info', message, options),
	warning: (message: string, options?: ToastOptions) => addToast('warning', message, options),
};

// Export for testing
export { DEFAULT_DURATIONS, MAX_TOASTS, toastsStore as _toastsStore };
