/**
 * Tour Store Unit Tests
 *
 * Tests use vi.stubGlobal for window mocking (consistent with other tests)
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { get } from 'svelte/store';

// Mock $app/environment
vi.mock('$app/environment', () => ({
	browser: true,
}));

// Mock api client
vi.mock('$lib/api/client', () => ({
	apiClient: {
		getOnboardingStatus: vi.fn().mockResolvedValue({
			needs_onboarding: true,
			tour_completed: false,
			completed_steps: [],
		}),
		completeTour: vi.fn().mockResolvedValue(undefined),
		resetOnboarding: vi.fn().mockResolvedValue(undefined),
		skipOnboarding: vi.fn().mockResolvedValue(undefined),
	},
}));

import tourStore, {
	setTourActive,
	shouldBlockNavigation,
	handleNavigationDuringTour,
	setTourPage,
	getPersistedTourPage,
	clearTourPage,
	allowTourNavigation,
	completeTour,
	CONTEXT_WELCOME_KEY,
	type TourPage,
} from './tour';

describe('tour store', () => {
	beforeEach(() => {
		// Reset store state
		tourStore.set({
			isActive: false,
			isCompleted: false,
			needsOnboarding: false,
			isLoading: false,
			error: null,
			currentPage: null,
		});
	});

	describe('setTourActive', () => {
		it('sets isActive to true', () => {
			setTourActive(true);
			expect(get(tourStore).isActive).toBe(true);
		});

		it('sets isActive to false', () => {
			setTourActive(true);
			setTourActive(false);
			expect(get(tourStore).isActive).toBe(false);
		});
	});

	describe('shouldBlockNavigation', () => {
		it('returns false when tour is not active', () => {
			tourStore.set({
				isActive: false,
				isCompleted: false,
				needsOnboarding: false,
				isLoading: false,
				error: null,
				currentPage: null,
			});
			expect(shouldBlockNavigation()).toBe(false);
		});

		it('returns true when tour is active', () => {
			tourStore.set({
				isActive: true,
				isCompleted: false,
				needsOnboarding: true,
				isLoading: false,
				error: null,
				currentPage: null,
			});
			expect(shouldBlockNavigation()).toBe(true);
		});
	});

	describe('handleNavigationDuringTour', () => {
		let confirmMock: ReturnType<typeof vi.fn>;

		beforeEach(() => {
			confirmMock = vi.fn();
			vi.stubGlobal('window', { confirm: confirmMock });
			// Stub localStorage for clearTourPage call
			vi.stubGlobal('localStorage', {
				getItem: vi.fn(() => null),
				setItem: vi.fn(),
				removeItem: vi.fn(),
			});
		});

		afterEach(() => {
			vi.unstubAllGlobals();
		});

		it('returns false when tour is not active (allows navigation)', () => {
			tourStore.set({
				isActive: false,
				isCompleted: false,
				needsOnboarding: false,
				isLoading: false,
				error: null,
				currentPage: null,
			});

			const result = handleNavigationDuringTour();
			expect(result).toBe(false);
			expect(confirmMock).not.toHaveBeenCalled();
		});

		it('shows confirm dialog when tour is active', () => {
			tourStore.set({
				isActive: true,
				isCompleted: false,
				needsOnboarding: true,
				isLoading: false,
				error: null,
				currentPage: null,
			});
			confirmMock.mockReturnValue(false);

			handleNavigationDuringTour();
			expect(confirmMock).toHaveBeenCalledWith(
				'The onboarding tour is in progress. Leave the tour and navigate away?'
			);
		});

		it('returns true (blocks navigation) when user cancels confirm', () => {
			tourStore.set({
				isActive: true,
				isCompleted: false,
				needsOnboarding: true,
				isLoading: false,
				error: null,
				currentPage: null,
			});
			confirmMock.mockReturnValue(false);

			const result = handleNavigationDuringTour();
			expect(result).toBe(true);
			expect(get(tourStore).isActive).toBe(true); // Tour remains active
		});

		it('returns false (allows navigation) and deactivates tour when user confirms', () => {
			tourStore.set({
				isActive: true,
				isCompleted: false,
				needsOnboarding: true,
				isLoading: false,
				error: null,
				currentPage: null,
			});
			confirmMock.mockReturnValue(true);

			const result = handleNavigationDuringTour();
			expect(result).toBe(false);
			expect(get(tourStore).isActive).toBe(false); // Tour deactivated
		});
	});

	describe('multi-page tour flow', () => {
		let localStorageMock: Record<string, string>;

		beforeEach(() => {
			localStorageMock = {};
			vi.stubGlobal('localStorage', {
				getItem: vi.fn((key: string) => localStorageMock[key] || null),
				setItem: vi.fn((key: string, value: string) => {
					localStorageMock[key] = value;
				}),
				removeItem: vi.fn((key: string) => {
					delete localStorageMock[key];
				}),
			});
		});

		afterEach(() => {
			vi.unstubAllGlobals();
		});

		describe('setTourPage', () => {
			it('sets currentPage in store', () => {
				tourStore.set({
					isActive: true,
					isCompleted: false,
					needsOnboarding: true,
					isLoading: false,
					error: null,
					currentPage: null,
				});

				setTourPage('actions');
				expect(get(tourStore).currentPage).toBe('actions');
			});

			it('persists page to localStorage', () => {
				setTourPage('projects');
				expect(localStorage.setItem).toHaveBeenCalledWith('bo1_tour_page', 'projects');
			});

			it('removes from localStorage when page is null', () => {
				setTourPage(null);
				expect(localStorage.removeItem).toHaveBeenCalledWith('bo1_tour_page');
			});
		});

		describe('getPersistedTourPage', () => {
			it('returns null when no page stored', () => {
				expect(getPersistedTourPage()).toBeNull();
			});

			it('returns stored page for valid values', () => {
				localStorageMock['bo1_tour_page'] = 'actions';
				expect(getPersistedTourPage()).toBe('actions');
			});

			it('returns null for invalid stored values', () => {
				localStorageMock['bo1_tour_page'] = 'invalid-page';
				expect(getPersistedTourPage()).toBeNull();
			});
		});

		describe('clearTourPage', () => {
			it('clears currentPage in store', () => {
				tourStore.set({
					isActive: true,
					isCompleted: false,
					needsOnboarding: true,
					isLoading: false,
					error: null,
					currentPage: 'actions',
				});

				clearTourPage();
				expect(get(tourStore).currentPage).toBeNull();
			});

			it('removes from localStorage', () => {
				clearTourPage();
				expect(localStorage.removeItem).toHaveBeenCalledWith('bo1_tour_page');
			});
		});

		describe('allowTourNavigation', () => {
			it('deactivates tour without showing confirmation', () => {
				tourStore.set({
					isActive: true,
					isCompleted: false,
					needsOnboarding: true,
					isLoading: false,
					error: null,
					currentPage: 'dashboard',
				});

				allowTourNavigation();
				expect(get(tourStore).isActive).toBe(false);
			});
		});

		describe('completeTour', () => {
			it('sets context welcome flag in localStorage', async () => {
				tourStore.set({
					isActive: true,
					isCompleted: false,
					needsOnboarding: true,
					isLoading: false,
					error: null,
					currentPage: 'dashboard',
				});

				const result = await completeTour();

				expect(result).toBe(true);
				expect(localStorage.setItem).toHaveBeenCalledWith(CONTEXT_WELCOME_KEY, 'true');
			});

			it('clears tour page state after completion', async () => {
				localStorageMock['bo1_tour_page'] = 'projects';

				await completeTour();

				expect(localStorage.removeItem).toHaveBeenCalledWith('bo1_tour_page');
			});

			it('updates store to completed state', async () => {
				tourStore.set({
					isActive: true,
					isCompleted: false,
					needsOnboarding: true,
					isLoading: false,
					error: null,
					currentPage: 'dashboard',
				});

				await completeTour();

				const state = get(tourStore);
				expect(state.isActive).toBe(false);
				expect(state.isCompleted).toBe(true);
				expect(state.needsOnboarding).toBe(false);
				expect(state.currentPage).toBeNull();
			});
		});
	});
});
