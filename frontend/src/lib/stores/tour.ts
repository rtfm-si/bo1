/**
 * Tour State Store
 *
 * Manages the onboarding tour state including:
 * - Tour completion status
 * - Auto-start logic for new users
 * - Manual restart functionality
 * - Navigation blocking during active tour
 */

import { writable, derived, get } from 'svelte/store';
import { browser } from '$app/environment';
import { apiClient } from '$lib/api/client';
import type { OnboardingStatus } from '$lib/api/client';

/** Tour page identifier for multi-page flow */
export type TourPage = 'dashboard' | 'actions' | 'projects' | null;

/** localStorage key for tour page state */
const TOUR_PAGE_KEY = 'bo1_tour_page';

/** localStorage key for showing welcome banner on context page */
export const CONTEXT_WELCOME_KEY = 'bo1_show_context_welcome';

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
	/** Current page in multi-page tour flow */
	currentPage: TourPage;
}

const initialState: TourState = {
	isActive: false,
	isCompleted: false,
	needsOnboarding: false,
	isLoading: true,
	error: null,
	currentPage: null,
};

// Create writable store
const tourStore = writable<TourState>(initialState);

// Derived stores for convenience
export const isActive = derived(tourStore, ($tour) => $tour.isActive);
export const isCompleted = derived(tourStore, ($tour) => $tour.isCompleted);
export const needsOnboarding = derived(tourStore, ($tour) => $tour.needsOnboarding);
export const isLoading = derived(tourStore, ($tour) => $tour.isLoading);
export const tourError = derived(tourStore, ($tour) => $tour.error);
export const currentTourPage = derived(tourStore, ($tour) => $tour.currentPage);

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
			currentPage: null,
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
 * Set current tour page for multi-page navigation
 * Persists to localStorage for page refresh recovery
 */
export function setTourPage(page: TourPage): void {
	tourStore.update((state) => ({ ...state, currentPage: page }));
	if (browser) {
		if (page) {
			localStorage.setItem(TOUR_PAGE_KEY, page);
		} else {
			localStorage.removeItem(TOUR_PAGE_KEY);
		}
	}
}

/**
 * Get persisted tour page from localStorage
 * Used to recover tour state after page navigation
 */
export function getPersistedTourPage(): TourPage {
	if (!browser) return null;
	const stored = localStorage.getItem(TOUR_PAGE_KEY);
	if (stored === 'dashboard' || stored === 'actions' || stored === 'projects') {
		return stored;
	}
	return null;
}

/**
 * Clear tour page state (call after tour completes or is skipped)
 */
export function clearTourPage(): void {
	tourStore.update((state) => ({ ...state, currentPage: null }));
	if (browser) {
		localStorage.removeItem(TOUR_PAGE_KEY);
	}
}

/**
 * Mark tour as complete
 * Returns true if this was a fresh completion (for redirect handling)
 */
export async function completeTour(): Promise<boolean> {
	try {
		await apiClient.completeTour();
		clearTourPage();
		// Set flag for welcome banner on context page
		if (browser) {
			localStorage.setItem(CONTEXT_WELCOME_KEY, 'true');
		}
		tourStore.update((state) => ({
			...state,
			isActive: false,
			isCompleted: true,
			needsOnboarding: false,
			currentPage: null,
		}));
		return true;
	} catch (error) {
		console.error('Failed to complete tour:', error);
		return false;
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
		clearTourPage();
		tourStore.update((state) => ({
			...state,
			isActive: false,
			isCompleted: true,
			needsOnboarding: false,
			currentPage: null,
		}));
	} catch (error) {
		console.error('Failed to skip tour:', error);
	}
}

/**
 * Check if navigation should be blocked (tour is active)
 * Returns true if navigation should be cancelled
 */
export function shouldBlockNavigation(): boolean {
	return get(tourStore).isActive;
}

/**
 * Handle navigation attempt during tour
 * Returns true if navigation was blocked (user chose to stay)
 */
export function handleNavigationDuringTour(): boolean {
	if (!shouldBlockNavigation()) return false;

	const confirmed = window.confirm(
		'The onboarding tour is in progress. Leave the tour and navigate away?'
	);

	if (confirmed) {
		// User wants to leave - deactivate tour and clear page state
		clearTourPage();
		tourStore.update((state) => ({
			...state,
			isActive: false,
			currentPage: null,
		}));
		return false; // Allow navigation
	}

	return true; // Block navigation
}

/**
 * Allow navigation during tour (for intentional tour-guided navigation)
 * Does NOT show confirmation dialog
 */
export function allowTourNavigation(): void {
	tourStore.update((state) => ({
		...state,
		isActive: false,
	}));
}

// Export store
export default tourStore;
