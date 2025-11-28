/**
 * Authentication store for Board of One frontend - SuperTokens BFF Pattern.
 *
 * Manages:
 * - User authentication state (logged in/out)
 * - User profile data
 * - Session management via httpOnly cookies (SuperTokens)
 *
 * Security:
 * - NO token storage in localStorage/sessionStorage
 * - Tokens stored as httpOnly cookies (XSS-proof)
 * - Session management handled by SuperTokens SDK
 * - All auth flows handled server-side (BFF pattern)
 */

import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';
import { goto } from '$app/navigation';
import Session from "supertokens-web-js/recipe/session";
import { env } from '$env/dynamic/public';

const API_BASE_URL = env.PUBLIC_API_URL || 'http://localhost:8000';

export interface User {
	id: string;
	email: string;
	auth_provider: 'google' | 'linkedin' | 'github';
	subscription_tier: 'free' | 'pro' | 'enterprise';
	is_admin?: boolean;
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
 * Initialize auth store - check if user has valid SuperTokens session.
 * Called on app mount in +layout.svelte.
 *
 * SuperTokens automatically checks httpOnly session cookie.
 * If valid, fetches user data from backend /api/auth/me.
 */
export async function initAuth(): Promise<void> {
	if (!browser) return;

	console.log('[Auth] Initializing auth...');

	try {
		authStore.update((state) => ({ ...state, isLoading: true, error: null }));

		// Check if SuperTokens session exists (checks httpOnly cookie)
		console.log('[Auth] Checking if session exists...');
		const sessionExists = await Session.doesSessionExist();
		console.log('[Auth] Session exists:', sessionExists);

		if (sessionExists) {
			// Get user info from backend
			console.log('[Auth] Fetching user info from /api/auth/me...');
			const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
				credentials: 'include', // Send cookies
			});
			console.log('[Auth] /api/auth/me response status:', response.status);

			if (response.ok) {
				const userData = await response.json();
				console.log('[Auth] User data:', userData);

				// User is authenticated
				authStore.set({
					user: userData,
					isAuthenticated: true,
					isLoading: false,
					error: null
				});
				console.log('[Auth] Authentication successful!');
			} else {
				// Session exists but /me failed - sign out
				console.error('[Auth] /api/auth/me failed with status:', response.status);
				const errorText = await response.text();
				console.error('[Auth] Error response:', errorText);
				await signOut();
			}
		} else {
			// No session
			console.log('[Auth] No session found, user not authenticated');
			authStore.set({
				user: null,
				isAuthenticated: false,
				isLoading: false,
				error: null
			});
		}
	} catch (error) {
		console.error('[Auth] Failed to initialize auth:', error);
		authStore.set({
			user: null,
			isAuthenticated: false,
			isLoading: false,
			error: 'Failed to check authentication status'
		});
	}
}

/**
 * Sign out user - clear SuperTokens session and redirect to login.
 *
 * SuperTokens SDK calls backend to invalidate session and clears httpOnly cookies.
 */
export async function signOut(): Promise<void> {
	try {
		// Call SuperTokens signOut - clears session and httpOnly cookies
		await Session.signOut();
	} catch (error) {
		console.error('Sign out failed:', error);
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
 * Check if session is still valid.
 * SuperTokens automatically refreshes tokens when needed.
 */
export async function checkSession(): Promise<void> {
	await initAuth();
}

// Export store
export default authStore;
