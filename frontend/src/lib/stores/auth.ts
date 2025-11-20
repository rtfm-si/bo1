/**
 * Authentication store for Board of One frontend.
 *
 * Manages:
 * - User authentication state (logged in/out)
 * - JWT token storage in httpOnly cookies
 * - User profile data
 * - OAuth flow state
 */

import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';

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
 */
export async function initAuth(): Promise<void> {
	if (!browser) return;

	try {
		authStore.update((state) => ({ ...state, isLoading: true, error: null }));

		// Check if we have a valid session by calling a protected endpoint
		// The JWT is stored in httpOnly cookie, so it's sent automatically
		const response = await fetch('/api/sessions', {
			credentials: 'include' // Send cookies
		});

		if (response.ok) {
			// User is authenticated - fetch user profile
			const userData = await fetchUserProfile();
			authStore.set({
				user: userData,
				isAuthenticated: true,
				isLoading: false,
				error: null
			});
		} else {
			// Not authenticated
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
 * Fetch user profile data.
 * Assumes user is authenticated (JWT in cookie).
 */
async function fetchUserProfile(): Promise<User> {
	// For MVP, we'll get user data from the OAuth callback response
	// In production, this would be a separate /api/auth/me endpoint
	const storedUser = browser ? localStorage.getItem('bo1_user') : null;

	if (storedUser) {
		return JSON.parse(storedUser);
	}

	// Fallback - return default user (should not happen in normal flow)
	throw new Error('User profile not found in localStorage');
}

/**
 * Handle OAuth callback - exchange code for tokens and set user.
 *
 * @param code - Authorization code from OAuth provider
 * @param redirectUri - Redirect URI used in OAuth flow
 * @returns User data
 */
export async function handleOAuthCallback(code: string, redirectUri: string): Promise<User> {
	try {
		authStore.update((state) => ({ ...state, isLoading: true, error: null }));

		const response = await fetch('/api/auth/google/callback', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			credentials: 'include', // Send and store cookies
			body: JSON.stringify({ code, redirect_uri: redirectUri })
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.detail || 'OAuth callback failed');
		}

		const data = await response.json();

		// Store JWT tokens in httpOnly cookies (done by backend)
		// Store user data in localStorage for quick access
		const user: User = data.user;
		if (browser) {
			localStorage.setItem('bo1_user', JSON.stringify(user));
			localStorage.setItem('bo1_access_token', data.access_token);
			localStorage.setItem('bo1_refresh_token', data.refresh_token);
		}

		// Update auth state
		authStore.set({
			user,
			isAuthenticated: true,
			isLoading: false,
			error: null
		});

		return user;
	} catch (error) {
		console.error('OAuth callback failed:', error);
		const errorMessage = error instanceof Error ? error.message : 'OAuth callback failed';

		authStore.set({
			user: null,
			isAuthenticated: false,
			isLoading: false,
			error: errorMessage
		});

		throw error;
	}
}

/**
 * Sign out user - clear tokens and user data.
 */
export async function signOut(): Promise<void> {
	try {
		const accessToken = browser ? localStorage.getItem('bo1_access_token') : null;

		if (accessToken) {
			// Call backend signout endpoint to invalidate tokens
			await fetch('/api/auth/signout', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				credentials: 'include',
				body: JSON.stringify({ access_token: accessToken })
			});
		}
	} catch (error) {
		console.error('Signout API call failed:', error);
		// Continue with local cleanup even if API call fails
	}

	// Clear local storage
	if (browser) {
		localStorage.removeItem('bo1_user');
		localStorage.removeItem('bo1_access_token');
		localStorage.removeItem('bo1_refresh_token');
	}

	// Reset auth state
	authStore.set({
		user: null,
		isAuthenticated: false,
		isLoading: false,
		error: null
	});
}

/**
 * Refresh access token using refresh token.
 * Called automatically when access token expires.
 */
export async function refreshAccessToken(): Promise<boolean> {
	try {
		const refreshToken = browser ? localStorage.getItem('bo1_refresh_token') : null;

		if (!refreshToken) {
			throw new Error('No refresh token available');
		}

		const response = await fetch('/api/auth/refresh', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			credentials: 'include',
			body: JSON.stringify({ refresh_token: refreshToken })
		});

		if (!response.ok) {
			throw new Error('Token refresh failed');
		}

		const data = await response.json();

		// Update stored tokens
		if (browser) {
			localStorage.setItem('bo1_access_token', data.access_token);
			localStorage.setItem('bo1_refresh_token', data.refresh_token);
		}

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
