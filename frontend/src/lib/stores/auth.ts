/**
 * Authentication store for Board of One frontend - BFF Pattern.
 *
 * Manages:
 * - User authentication state (logged in/out)
 * - User profile data
 * - Session management via httpOnly cookies
 *
 * Security:
 * - NO token storage in localStorage/sessionStorage
 * - Tokens stored in Redis (backend only)
 * - httpOnly cookies prevent XSS attacks
 * - All auth flows handled by backend
 */

import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';
import { goto } from '$app/navigation';

const API_BASE_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';

export interface User {
	id: string;
	email: string;
	auth_provider: 'google' | 'linkedin' | 'github';
	subscription_tier: 'free' | 'pro' | 'enterprise';
}

export interface AuthState {
	user: User | null;
	isAuthenticated: boolean;
	isLoading: boolean;
	error: string | null;
}

// Initial state
const initialState: AuthState = {
	user: null,
	isAuthenticated: false,
	isLoading: true, // Start as loading to check auth on mount
	error: null
};

// Create writable store
const authStore = writable<AuthState>(initialState);

// Derived stores for convenience
export const user = derived(authStore, ($auth) => $auth.user);
export const isAuthenticated = derived(authStore, ($auth) => $auth.isAuthenticated);
export const isLoading = derived(authStore, ($auth) => $auth.isLoading);

/**
 * Initialize auth store - check if user is already authenticated.
 * Called on app mount.
 *
 * Checks session cookie by calling /api/auth/me endpoint.
 * Backend validates session and returns user data if valid.
 */
export async function initAuth(): Promise<void> {
	if (!browser) return;

	try {
		authStore.update((state) => ({ ...state, isLoading: true, error: null }));

		// Call backend to check session
		// Backend checks httpOnly cookie, validates session in Redis
		const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
			method: 'GET',
			credentials: 'include', // Send cookies
			headers: {
				'Content-Type': 'application/json'
			}
		});

		if (response.ok) {
			const userData = await response.json();

			// User is authenticated
			authStore.set({
				user: userData,
				isAuthenticated: true,
				isLoading: false,
				error: null
			});
		} else {
			// Not authenticated or session expired
			authStore.set({
				user: null,
				isAuthenticated: false,
				isLoading: false,
				error: null
			});
		}
	} catch (error) {
		console.error('Failed to initialize auth:', error);
		authStore.set({
			user: null,
			isAuthenticated: false,
			isLoading: false,
			error: 'Failed to check authentication status'
		});
	}
}

/**
 * Sign out user - clear session and redirect to login.
 *
 * Calls backend /api/auth/logout to invalidate session in Redis.
 * Backend also clears the httpOnly cookie.
 */
export async function signOut(): Promise<void> {
	try {
		// Call backend logout endpoint
		await fetch(`${API_BASE_URL}/api/auth/logout`, {
			method: 'POST',
			credentials: 'include', // Send cookies
			headers: {
				'Content-Type': 'application/json'
			}
		});
	} catch (error) {
		console.error('Logout API call failed:', error);
		// Continue with local cleanup even if API call fails
	}

	// Reset auth state
	authStore.set({
		user: null,
		isAuthenticated: false,
		isLoading: false,
		error: null
	});

	// Redirect to login
	if (browser) {
		goto('/login');
	}
}

/**
 * Refresh access token using refresh token from session.
 * Called automatically by interceptor when access token expires.
 *
 * Returns true if refresh succeeded, false otherwise.
 */
export async function refreshAccessToken(): Promise<boolean> {
	try {
		const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
			method: 'POST',
			credentials: 'include', // Send cookies
			headers: {
				'Content-Type': 'application/json'
			}
		});

		if (!response.ok) {
			throw new Error('Token refresh failed');
		}

		// Token refreshed successfully (session updated in Redis by backend)
		return true;
	} catch (error) {
		console.error('Token refresh failed:', error);
		// Sign out user if refresh fails
		await signOut();
		return false;
	}
}

// Export store
export default authStore;
