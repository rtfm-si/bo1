/**
 * Tour State Store
 *
 * Manages the onboarding tour state including:
 * - Tour completion status
 * - Auto-start logic for new users
 * - Manual restart functionality
 */

import { writable, derived, get } from 'svelte/store';
import { browser } from '$app/environment';
import { apiClient } from '$lib/api/client';
import type { OnboardingStatus } from '$lib/api/client';

export interface TourState {
	/** Whether tour is currently running */
	isActive: boolean;
	/** Whether tour has been completed */
	isCompleted: boolean;
	/** Whether user needs onboarding */
	needsOnboarding: boolean;
	/** Loading state for initial check */
	isLoading: boolean;
	/** Error message if any */
	error: string | null;
}

const initialState: TourState = {
	isActive: false,
	isCompleted: false,
	needsOnboarding: false,
	isLoading: true,
	error: null,
};

// Create writable store
const tourStore = writable<TourState>(initialState);

// Derived stores for convenience
export const isActive = derived(tourStore, ($tour) => $tour.isActive);
export const isCompleted = derived(tourStore, ($tour) => $tour.isCompleted);
export const needsOnboarding = derived(tourStore, ($tour) => $tour.needsOnboarding);
export const isLoading = derived(tourStore, ($tour) => $tour.isLoading);
export const tourError = derived(tourStore, ($tour) => $tour.error);

/**
 * Check if user needs onboarding tour
 */
export async function checkOnboardingStatus(): Promise<boolean> {
	if (!browser) return false;

	tourStore.update((state) => ({ ...state, isLoading: true, error: null }));

	try {
		const status = await apiClient.getOnboardingStatus();

		const needsTour = status.needs_onboarding && !status.tour_completed;

		tourStore.set({
			isActive: false,
			isCompleted: status.tour_completed,
			needsOnboarding: needsTour,
			isLoading: false,
			error: null,
		});

		return needsTour;
	} catch (error) {
		console.error('Failed to check onboarding status:', error);
		tourStore.update((state) => ({
			...state,
			isLoading: false,
			error: 'Failed to check onboarding status',
		}));
		return false;
	}
}

/**
 * Set tour as active
 */
export function setTourActive(active: boolean): void {
	tourStore.update((state) => ({ ...state, isActive: active }));
}

/**
 * Mark tour as complete
 */
export async function completeTour(): Promise<void> {
	try {
		await apiClient.completeTour();
		tourStore.update((state) => ({
			...state,
			isActive: false,
			isCompleted: true,
			needsOnboarding: false,
		}));
	} catch (error) {
		console.error('Failed to complete tour:', error);
	}
}

/**
 * Reset tour for restart
 */
export async function resetTour(): Promise<void> {
	try {
		await apiClient.resetOnboarding();
		tourStore.update((state) => ({
			...state,
			isActive: false,
			isCompleted: false,
			needsOnboarding: true,
		}));
	} catch (error) {
		console.error('Failed to reset tour:', error);
		throw error;
	}
}

/**
 * Skip tour entirely
 */
export async function skipTour(): Promise<void> {
	try {
		await apiClient.skipOnboarding();
		tourStore.update((state) => ({
			...state,
			isActive: false,
			isCompleted: true,
			needsOnboarding: false,
		}));
	} catch (error) {
		console.error('Failed to skip tour:', error);
	}
}

// Export store
export default tourStore;
