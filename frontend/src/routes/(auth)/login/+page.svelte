<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { isAuthenticated } from '$lib/stores/auth';
	import { initSuperTokens } from '$lib/supertokens';
	import ThirdParty from "supertokens-web-js/recipe/thirdparty";
	import EmailPassword from "supertokens-web-js/recipe/emailpassword";
	import Passwordless from "supertokens-web-js/recipe/passwordless";
	import { browser } from '$app/environment';
	import { env } from '$env/dynamic/public';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let gdprConsent = $state(false);

	// Email/password form state
	let email = $state('');
	let password = $state('');
	let isSignUp = $state(false);
	let emailError = $state<string | null>(null);
	let passwordError = $state<string | null>(null);

	// Magic link state
	let magicLinkEmail = $state('');
	let magicLinkEmailError = $state<string | null>(null);
	let magicLinkSent = $state(false);
	let showMagicLinkForm = $state(false);

	// Email verification state
	let verificationMessage = $state<string | null>(null);
	let showResendVerification = $state(false);
	let resendEmail = $state('');

	// Redirect if already authenticated
	onMount(() => {
		// Initialize SuperTokens
		initSuperTokens();

		const unsubscribe = isAuthenticated.subscribe((authenticated) => {
			if (authenticated) {
				goto('/dashboard');
			}
		});

		// Check for error/message query params (from backend redirect)
		if (browser) {
			const params = new URLSearchParams(window.location.search);
			const errorParam = params.get('error');
			const messageParam = params.get('message');

			// Handle success messages
			if (messageParam) {
				const successMessages: Record<string, string> = {
					email_verified: 'Email verified successfully! You can now sign in.',
					email_already_verified: 'Your email is already verified. Please sign in.',
				};
				verificationMessage = successMessages[messageParam] || null;
			}

			// Handle error messages
			if (errorParam) {
				// Map error codes to user-friendly messages
				const errorMessages: Record<string, string> = {
					auth_init_failed: 'Failed to initiate sign-in. Please try again.',
					oauth_error: 'OAuth provider returned an error.',
					missing_parameters: 'Missing authorization parameters.',
					csrf_validation_failed: 'Security validation failed. Please try again.',
					state_expired: 'Sign-in session expired. Please try again.',
					invalid_state: 'Invalid sign-in state.',
					token_exchange_failed: 'Failed to exchange authorization code for tokens.',
					invalid_token_response: 'Invalid response from authentication server.',
					missing_user_data: 'Failed to get user data from Google.',
					closed_beta: 'Access limited to beta users. Join our waitlist!',
					callback_failed: 'Authentication callback failed. Please try again.',
					verification_invalid: 'Invalid verification link. Please request a new one.',
					verification_expired: 'Verification link has expired. Please request a new one.',
					email_not_verified: 'Please verify your email before signing in.',
				};

				error = errorMessages[errorParam] || 'Authentication failed. Please try again.';

				// Show resend option for verification-related errors
				if (errorParam === 'verification_expired' || errorParam === 'verification_invalid' || errorParam === 'email_not_verified') {
					showResendVerification = true;
				}
			}
		}

		return unsubscribe;
	});

	let loadingProvider = $state<string | null>(null);

	/**
	 * Initiate OAuth flow via SuperTokens for the specified provider.
	 * Gets authorization URL from backend and redirects browser.
	 */
	async function handleOAuthSignIn(providerId: string) {
		// Require GDPR consent before proceeding
		if (!gdprConsent) {
			error = "Please accept the Privacy Policy to continue.";
			return;
		}

		isLoading = true;
		loadingProvider = providerId;
		error = null;

		try {
			// Store GDPR consent in localStorage before OAuth redirect
			// Will be read by callback page and sent to backend
			localStorage.setItem('gdpr_consent_pending', 'true');

			// Get authorization URL from SuperTokens backend
			const authUrl = await ThirdParty.getAuthorisationURLWithQueryParamsAndSetState({
				thirdPartyId: providerId,
				// Both frontendRedirectURI and redirectURIOnProviderDashboard should be the frontend callback
				// Provider sends a GET request to the frontend, then frontend POSTs to backend /api/auth/signinup
				frontendRedirectURI: `${window.location.origin}/callback`,
				redirectURIOnProviderDashboard: `${window.location.origin}/callback`,
			});

			// Redirect browser to OAuth provider
			window.location.href = authUrl;
		} catch (err: any) {
			console.error(`Failed to initiate ${providerId} sign-in:`, err);
			error = "Failed to initiate sign-in. Please try again.";
			isLoading = false;
			loadingProvider = null;
		}
	}

	function handleGoogleSignIn() {
		handleOAuthSignIn("google");
	}

	function handleLinkedInSignIn() {
		handleOAuthSignIn("linkedin");
	}

	function handleGitHubSignIn() {
		handleOAuthSignIn("github");
	}

	function handleTwitterSignIn() {
		handleOAuthSignIn("twitter");
	}

	function handleBlueskySignIn() {
		handleOAuthSignIn("bluesky");
	}

	/**
	 * Validate email format
	 */
	function validateEmail(value: string): boolean {
		const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
		if (!value) {
			emailError = 'Email is required';
			return false;
		}
		if (!emailRegex.test(value)) {
			emailError = 'Please enter a valid email address';
			return false;
		}
		emailError = null;
		return true;
	}

	/**
	 * Validate password strength
	 */
	function validatePassword(value: string): boolean {
		if (!value) {
			passwordError = 'Password is required';
			return false;
		}
		if (value.length < 8) {
			passwordError = 'Password must be at least 8 characters';
			return false;
		}
		passwordError = null;
		return true;
	}

	/**
	 * Handle magic link sign-in request
	 */
	async function handleMagicLinkSubmit(e: Event) {
		e.preventDefault();

		// Require GDPR consent
		if (!gdprConsent) {
			error = "Please accept the Privacy Policy to continue.";
			return;
		}

		// Validate email
		const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
		if (!magicLinkEmail) {
			magicLinkEmailError = 'Email is required';
			return;
		}
		if (!emailRegex.test(magicLinkEmail)) {
			magicLinkEmailError = 'Please enter a valid email address';
			return;
		}
		magicLinkEmailError = null;

		isLoading = true;
		loadingProvider = 'magic-link';
		error = null;

		try {
			const response = await Passwordless.createCode({
				email: magicLinkEmail,
			});

			if (response.status === "OK") {
				magicLinkSent = true;
			} else if (response.status === "SIGN_IN_UP_NOT_ALLOWED") {
				error = "Sign in is not allowed. You may not be on the beta whitelist.";
			}
		} catch (err: any) {
			console.error('Magic link request error:', err);
			if (err.message?.includes("rate limit")) {
				error = "Too many requests. Please wait a few minutes and try again.";
			} else {
				error = err.message || "Failed to send magic link. Please try again.";
			}
		} finally {
			isLoading = false;
			loadingProvider = null;
		}
	}

	/**
	 * Handle resending verification email
	 */
	async function handleResendVerification() {
		if (!resendEmail) {
			error = "Please enter your email address to resend verification.";
			return;
		}

		isLoading = true;
		loadingProvider = 'email';
		error = null;

		try {
			const response = await fetch('/api/v1/auth/resend-verification', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ email: resendEmail }),
			});

			if (response.ok) {
				verificationMessage = `If an account exists for ${resendEmail}, a verification link has been sent.`;
				showResendVerification = false;
			} else {
				error = "Failed to resend verification email. Please try again.";
			}
		} catch (err) {
			console.error('Resend verification error:', err);
			error = "Failed to resend verification email. Please try again.";
		} finally {
			isLoading = false;
			loadingProvider = null;
		}
	}

	/**
	 * Handle email/password sign-in or sign-up
	 */
	async function handleEmailPasswordSubmit(e: Event) {
		e.preventDefault();

		// Require GDPR consent
		if (!gdprConsent) {
			error = "Please accept the Privacy Policy to continue.";
			return;
		}

		// Validate inputs
		const isEmailValid = validateEmail(email);
		const isPasswordValid = validatePassword(password);

		if (!isEmailValid || !isPasswordValid) {
			return;
		}

		isLoading = true;
		loadingProvider = 'email';
		error = null;
		verificationMessage = null;

		try {
			if (isSignUp) {
				// Sign up
				const response = await EmailPassword.signUp({
					formFields: [
						{ id: "email", value: email },
						{ id: "password", value: password },
					],
				});

				if (response.status === "OK") {
					// Account created - show verification message instead of redirecting
					// Email/password users must verify their email before accessing the app
					verificationMessage = `Account created! Please check your email (${email}) for a verification link.`;
					// Clear the form
					email = '';
					password = '';
					isSignUp = false;  // Switch to sign-in mode
				} else if (response.status === "FIELD_ERROR") {
					// Handle field validation errors from backend
					for (const field of response.formFields) {
						if (field.id === "email") {
							emailError = field.error;
						} else if (field.id === "password") {
							passwordError = field.error;
						}
					}
				} else if (response.status === "SIGN_UP_NOT_ALLOWED") {
					error = "Sign up is not allowed. You may not be on the beta whitelist.";
				}
			} else {
				// Sign in
				const response = await EmailPassword.signIn({
					formFields: [
						{ id: "email", value: email },
						{ id: "password", value: password },
					],
				});

				if (response.status === "OK") {
					// Successful sign-in, redirect to dashboard
					goto('/dashboard');
				} else if (response.status === "FIELD_ERROR") {
					// Handle field validation errors
					for (const field of response.formFields) {
						if (field.id === "email") {
							emailError = field.error;
						} else if (field.id === "password") {
							passwordError = field.error;
						}
					}
				} else if (response.status === "WRONG_CREDENTIALS_ERROR") {
					error = "Invalid email or password.";
				} else if (response.status === "SIGN_IN_NOT_ALLOWED") {
					error = "Sign in is not allowed. Your account may be locked.";
				}
			}
		} catch (err: any) {
			console.error('Email/password auth error:', err);
			const errMsg = err.message || "";
			// Check for email verification error
			if (errMsg.includes("email not verified") || errMsg.includes("EMAIL_NOT_VERIFIED")) {
				error = "Please verify your email before signing in.";
				showResendVerification = true;
				resendEmail = email;
			} else {
				error = errMsg || "Authentication failed. Please try again.";
			}
		} finally {
			isLoading = false;
			loadingProvider = null;
		}
	}
</script>

<svelte:head>
	<title>Sign In - Board of One</title>
	<meta name="description" content="Sign in to Board of One" />
</svelte:head>

<div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-900 dark:to-neutral-800 px-4">
	<div class="max-w-md w-full">
		<!-- Logo -->
		<div class="text-center mb-8">
			<h1 class="text-4xl font-bold text-neutral-900 dark:text-white mb-2">
				Board of One
			</h1>
			<p class="text-neutral-600 dark:text-neutral-400">
				AI-powered strategic decision-making
			</p>
		</div>

		<!-- Sign-in card -->
		<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-lg p-8 border border-neutral-200 dark:border-neutral-700">
			<h2 class="text-2xl font-semibold text-neutral-900 dark:text-white mb-6">
				Sign in to continue
			</h2>

			<!-- Closed Beta Notice -->
			<div class="mb-6 p-4 bg-info-50 dark:bg-info-900/20 border border-info-200 dark:border-info-800 rounded-lg">
				<p class="text-sm text-info-900 dark:text-info-200">
					<span class="font-semibold">Closed Beta:</span> Access is currently limited to whitelisted users.
					<a href="/waitlist" class="underline hover:text-info-700 dark:hover:text-info-300">
						Join the waitlist
					</a>
				</p>
			</div>

			<!-- Verification success message -->
			{#if verificationMessage}
				<div class="mb-6 p-4 bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800 rounded-lg">
					<div class="flex items-start gap-3">
						<svg class="w-5 h-5 text-success-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
							<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
						</svg>
						<p class="text-sm text-success-900 dark:text-success-200">{verificationMessage}</p>
					</div>
				</div>
			{/if}

			<!-- Error message -->
			{#if error}
				<div class="mb-6 p-4 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg">
					<p class="text-sm text-error-900 dark:text-error-200">
						{error}
					</p>
					{#if error.includes('beta') || error.includes('whitelist')}
						<a href="/waitlist" class="block mt-2 text-sm text-error-900 dark:text-error-200 underline">
							Join our waitlist for early access
						</a>
					{/if}
				</div>
			{/if}

			<!-- Resend verification email form -->
			{#if showResendVerification}
				<div class="mb-6 p-4 bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-lg">
					<p class="text-sm text-warning-900 dark:text-warning-200 mb-3">
						Need a new verification link? Enter your email below:
					</p>
					<div class="flex gap-2">
						<input
							type="email"
							bind:value={resendEmail}
							placeholder="your@email.com"
							class="flex-1 px-3 py-2 text-sm border rounded-md focus:ring-2 focus:ring-warning-500 focus:border-warning-500 dark:bg-neutral-700 dark:border-neutral-600 dark:text-white"
						/>
						<button
							type="button"
							onclick={handleResendVerification}
							disabled={isLoading || !resendEmail}
							class="px-4 py-2 text-sm font-medium bg-warning-600 hover:bg-warning-700 text-white rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
						>
							{#if isLoading && loadingProvider === 'email'}
								Sending...
							{:else}
								Resend
							{/if}
						</button>
					</div>
				</div>
			{/if}

			<!-- GDPR Consent Checkbox -->
			<label class="flex items-start gap-3 mb-6 cursor-pointer">
				<input
					type="checkbox"
					bind:checked={gdprConsent}
					class="mt-1 h-4 w-4 rounded border-neutral-300 text-info-600 focus:ring-info-500 dark:border-neutral-600 dark:bg-neutral-700"
				/>
				<span class="text-sm text-neutral-600 dark:text-neutral-400">
					I agree to the
					<a href="/legal/privacy" class="text-info-600 hover:text-info-700 dark:text-info-400 dark:hover:text-info-300 underline" target="_blank">Privacy Policy</a>
					and consent to the processing of my personal data as described therein.
				</span>
			</label>

			<!-- Email/Password Form -->
			<form onsubmit={handleEmailPasswordSubmit} class="space-y-4 mb-6">
				<!-- Sign-in/Sign-up Toggle -->
				<div class="flex gap-2 p-1 bg-neutral-100 dark:bg-neutral-700 rounded-lg">
					<button
						type="button"
						onclick={() => isSignUp = false}
						class="flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors {!isSignUp ? 'bg-white dark:bg-neutral-600 text-neutral-900 dark:text-white shadow-sm' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'}"
					>
						Sign In
					</button>
					<button
						type="button"
						onclick={() => isSignUp = true}
						class="flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors {isSignUp ? 'bg-white dark:bg-neutral-600 text-neutral-900 dark:text-white shadow-sm' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'}"
					>
						Sign Up
					</button>
				</div>

				<!-- Email Input -->
				<div>
					<label for="email" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						Email
					</label>
					<input
						type="email"
						id="email"
						bind:value={email}
						oninput={() => emailError = null}
						disabled={isLoading}
						class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-info-500 focus:border-info-500 dark:bg-neutral-700 dark:border-neutral-600 dark:text-white disabled:opacity-50 {emailError ? 'border-error-500' : 'border-neutral-300 dark:border-neutral-600'}"
						placeholder="you@example.com"
					/>
					{#if emailError}
						<p class="mt-1 text-sm text-error-600 dark:text-error-400">{emailError}</p>
					{/if}
				</div>

				<!-- Password Input -->
				<div>
					<label for="password" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						Password
					</label>
					<input
						type="password"
						id="password"
						bind:value={password}
						oninput={() => passwordError = null}
						disabled={isLoading}
						class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-info-500 focus:border-info-500 dark:bg-neutral-700 dark:border-neutral-600 dark:text-white disabled:opacity-50 {passwordError ? 'border-error-500' : 'border-neutral-300 dark:border-neutral-600'}"
						placeholder={isSignUp ? 'At least 8 characters' : 'Your password'}
					/>
					{#if passwordError}
						<p class="mt-1 text-sm text-error-600 dark:text-error-400">{passwordError}</p>
					{/if}
				</div>

				<!-- Submit Button -->
				<button
					type="submit"
					disabled={isLoading || !gdprConsent}
					class="w-full flex items-center justify-center gap-2 px-6 py-3 bg-info-600 hover:bg-info-700 text-white font-medium rounded-lg transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
				>
					{#if loadingProvider === 'email'}
						<Spinner size="sm" variant="neutral" ariaLabel="Authenticating" />
						<span>{isSignUp ? 'Creating account...' : 'Signing in...'}</span>
					{:else}
						<span>{isSignUp ? 'Create Account' : 'Sign In'}</span>
					{/if}
				</button>

				<!-- Magic Link Toggle -->
				<div class="text-center">
					<button
						type="button"
						onclick={() => { showMagicLinkForm = !showMagicLinkForm; magicLinkSent = false; }}
						class="text-sm text-info-600 hover:text-info-700 dark:text-info-400 dark:hover:text-info-300 underline"
					>
						{showMagicLinkForm ? 'Use password instead' : 'Sign in with email link (no password)'}
					</button>
				</div>
			</form>

			<!-- Magic Link Form -->
			{#if showMagicLinkForm}
				<div class="mt-6 p-4 bg-info-50 dark:bg-info-900/20 border border-info-200 dark:border-info-800 rounded-lg">
					{#if magicLinkSent}
						<div class="text-center">
							<svg class="w-12 h-12 mx-auto mb-3 text-success-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
							</svg>
							<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-2">Check your email</h3>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-3">
								We've sent a sign-in link to <strong>{magicLinkEmail}</strong>
							</p>
							<p class="text-xs text-neutral-500 dark:text-neutral-500">
								The link expires in 15 minutes. Check your spam folder if you don't see it.
							</p>
							<button
								type="button"
								onclick={() => { magicLinkSent = false; magicLinkEmail = ''; }}
								class="mt-4 text-sm text-info-600 hover:text-info-700 dark:text-info-400 underline"
							>
								Use a different email
							</button>
						</div>
					{:else}
						<form onsubmit={handleMagicLinkSubmit} class="space-y-4">
							<div>
								<label for="magic-link-email" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
									Email address
								</label>
								<input
									type="email"
									id="magic-link-email"
									bind:value={magicLinkEmail}
									oninput={() => magicLinkEmailError = null}
									disabled={isLoading}
									class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-info-500 focus:border-info-500 dark:bg-neutral-700 dark:border-neutral-600 dark:text-white disabled:opacity-50 {magicLinkEmailError ? 'border-error-500' : 'border-neutral-300 dark:border-neutral-600'}"
									placeholder="you@example.com"
								/>
								{#if magicLinkEmailError}
									<p class="mt-1 text-sm text-error-600 dark:text-error-400">{magicLinkEmailError}</p>
								{/if}
							</div>
							<button
								type="submit"
								disabled={isLoading || !gdprConsent}
								class="w-full flex items-center justify-center gap-2 px-6 py-3 bg-info-600 hover:bg-info-700 text-white font-medium rounded-lg transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
							>
								{#if loadingProvider === 'magic-link'}
									<Spinner size="sm" variant="neutral" ariaLabel="Sending magic link" />
									<span>Sending link...</span>
								{:else}
									<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
									</svg>
									<span>Send sign-in link</span>
								{/if}
							</button>
							<p class="text-xs text-center text-neutral-500 dark:text-neutral-400">
								We'll email you a link to sign in instantly - no password needed.
							</p>
						</form>
					{/if}
				</div>
			{/if}

			<!-- Divider -->
			<div class="relative mb-6 mt-6">
				<div class="absolute inset-0 flex items-center">
					<div class="w-full border-t border-neutral-300 dark:border-neutral-600"></div>
				</div>
				<div class="relative flex justify-center text-sm">
					<span class="px-2 bg-white dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400">or continue with</span>
				</div>
			</div>

			<!-- Google Sign-in Button -->
			<button
				onclick={handleGoogleSignIn}
				disabled={isLoading || !gdprConsent}
				class="w-full flex items-center justify-center gap-3 px-6 py-3 bg-white dark:bg-neutral-700 border-2 border-neutral-300 dark:border-neutral-600 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-600 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
			>
				{#if loadingProvider === 'google'}
					<Spinner size="sm" variant="neutral" ariaLabel="Signing in with Google" />
					<span class="text-neutral-700 dark:text-neutral-300 font-medium">Redirecting...</span>
				{:else}
					<svg class="w-5 h-5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
						<path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
						<path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
						<path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
						<path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
					</svg>
					<span class="text-neutral-700 dark:text-neutral-300 font-medium">Sign in with Google</span>
				{/if}
			</button>

			<!-- LinkedIn Sign-in Button -->
			<div class="mt-4 space-y-2">
				<button
					onclick={handleLinkedInSignIn}
					disabled={isLoading || !gdprConsent}
					class="w-full flex items-center justify-center gap-3 px-6 py-3 bg-white dark:bg-neutral-700 border-2 border-neutral-300 dark:border-neutral-600 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-600 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
				>
					{#if loadingProvider === 'linkedin'}
						<Spinner size="sm" variant="neutral" ariaLabel="Signing in with LinkedIn" />
						<span class="text-neutral-700 dark:text-neutral-300 font-medium">Redirecting...</span>
					{:else}
						<svg class="w-5 h-5" viewBox="0 0 24 24" fill="#0A66C2" xmlns="http://www.w3.org/2000/svg">
							<path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
						</svg>
						<span class="text-neutral-700 dark:text-neutral-300 font-medium">Sign in with LinkedIn</span>
					{/if}
				</button>

				<!-- GitHub Sign-in Button -->
				<button
					onclick={handleGitHubSignIn}
					disabled={isLoading || !gdprConsent}
					class="w-full flex items-center justify-center gap-3 px-6 py-3 bg-white dark:bg-neutral-700 border-2 border-neutral-300 dark:border-neutral-600 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-600 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
				>
					{#if loadingProvider === 'github'}
						<Spinner size="sm" variant="neutral" ariaLabel="Signing in with GitHub" />
						<span class="text-neutral-700 dark:text-neutral-300 font-medium">Redirecting...</span>
					{:else}
						<svg class="w-5 h-5 text-neutral-900 dark:text-white" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
							<path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
						</svg>
						<span class="text-neutral-700 dark:text-neutral-300 font-medium">Sign in with GitHub</span>
					{/if}
				</button>

				<!-- Twitter/X Sign-in Button -->
				<button
					onclick={handleTwitterSignIn}
					disabled={isLoading || !gdprConsent}
					class="w-full flex items-center justify-center gap-3 px-6 py-3 bg-white dark:bg-neutral-700 border-2 border-neutral-300 dark:border-neutral-600 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-600 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
				>
					{#if loadingProvider === 'twitter'}
						<Spinner size="sm" variant="neutral" ariaLabel="Signing in with X" />
						<span class="text-neutral-700 dark:text-neutral-300 font-medium">Redirecting...</span>
					{:else}
						<svg class="w-5 h-5 text-neutral-900 dark:text-white" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
							<path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
						</svg>
						<span class="text-neutral-700 dark:text-neutral-300 font-medium">Sign in with X</span>
					{/if}
				</button>

				<!-- Bluesky Sign-in Button -->
				<button
					onclick={handleBlueskySignIn}
					disabled={isLoading || !gdprConsent}
					class="w-full flex items-center justify-center gap-3 px-6 py-3 bg-white dark:bg-neutral-700 border-2 border-neutral-300 dark:border-neutral-600 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-600 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
				>
					{#if loadingProvider === 'bluesky'}
						<Spinner size="sm" variant="neutral" ariaLabel="Signing in with Bluesky" />
						<span class="text-neutral-700 dark:text-neutral-300 font-medium">Redirecting...</span>
					{:else}
						<svg class="w-5 h-5" viewBox="0 0 600 530" fill="#1185fe" xmlns="http://www.w3.org/2000/svg">
							<path d="m135.72 44.03c66.496 49.921 138.02 151.14 164.28 205.46 26.262-54.316 97.782-155.54 164.28-205.46 47.98-36.021 125.72-63.892 125.72 24.795 0 17.712-10.155 148.79-16.111 170.07-20.703 73.984-96.144 92.854-163.25 81.433 117.3 19.964 147.14 86.092 82.697 152.22-122.39 125.59-175.91-31.511-189.63-71.766-2.514-7.3797-3.6904-10.832-3.7077-7.8964-0.0174-2.9357-1.1937 0.51669-3.7077 7.8964-13.714 40.255-67.233 197.36-189.63 71.766-64.444-66.128-34.605-132.26 82.697-152.22-67.108 11.421-142.55-7.4491-163.25-81.433-5.9562-21.282-16.111-152.36-16.111-170.07 0-88.687 77.742-60.816 125.72-24.795z"/>
						</svg>
						<span class="text-neutral-700 dark:text-neutral-300 font-medium">Sign in with Bluesky</span>
					{/if}
				</button>
			</div>

			<!-- Terms notice -->
			<p class="mt-6 text-xs text-center text-neutral-500 dark:text-neutral-400">
				By signing in, you also agree to our
				<a href="/legal/terms" class="underline hover:text-neutral-700 dark:hover:text-neutral-300">Terms of Service</a>.
			</p>
		</div>

		<!-- Back to home -->
		<div class="mt-6 text-center">
			<a href="/" class="text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-200 transition-colors">
				← Back to home
			</a>
		</div>
	</div>
</div>
