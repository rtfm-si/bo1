<script lang="ts">
	/**
	 * Security Settings - Two-Factor Authentication (2FA)
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { TwoFactorStatusResponse, SetupTwoFactorResponse } from '$lib/api/client';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';

	// State
	let status = $state<TwoFactorStatusResponse | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let successMessage = $state<string | null>(null);

	// Setup flow state
	let setupData = $state<SetupTwoFactorResponse | null>(null);
	let isSettingUp = $state(false);
	let setupStep = $state<'idle' | 'qr' | 'verify'>('idle');
	let verifyCode = $state('');
	let isVerifying = $state(false);
	let setupError = $state<string | null>(null);

	// Disable flow state
	let showDisableModal = $state(false);
	let disablePassword = $state('');
	let isDisabling = $state(false);
	let disableError = $state<string | null>(null);

	// Backup codes state
	let showBackupCodesModal = $state(false);
	let backupCodes = $state<string[]>([]);
	let isRegeneratingCodes = $state(false);
	let regenerateError = $state<string | null>(null);
	let codesCopied = $state(false);

	// Load 2FA status
	onMount(async () => {
		try {
			status = await apiClient.getTwoFactorStatus();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load 2FA status';
		} finally {
			isLoading = false;
		}
	});

	// Start 2FA setup
	async function startSetup() {
		isSettingUp = true;
		setupError = null;

		try {
			setupData = await apiClient.setupTwoFactor();
			backupCodes = setupData.backup_codes;
			setupStep = 'qr';
		} catch (e) {
			setupError = e instanceof Error ? e.message : 'Failed to start 2FA setup';
		} finally {
			isSettingUp = false;
		}
	}

	// Verify setup code
	async function verifySetup() {
		if (verifyCode.length !== 6) {
			setupError = 'Please enter a 6-digit code';
			return;
		}

		isVerifying = true;
		setupError = null;

		try {
			const result = await apiClient.verifyTwoFactorSetup(verifyCode);
			if (result.success) {
				successMessage = '2FA has been enabled successfully!';
				status = await apiClient.getTwoFactorStatus();
				setupStep = 'idle';
				setupData = null;
				verifyCode = '';
				// Show backup codes modal
				showBackupCodesModal = true;
			} else {
				setupError = result.message || 'Verification failed';
			}
		} catch (e: unknown) {
			if (e && typeof e === 'object' && 'status' in e && e.status === 429) {
				setupError = 'Too many failed attempts. Please try again later.';
			} else {
				setupError = e instanceof Error ? e.message : 'Failed to verify code';
			}
		} finally {
			isVerifying = false;
		}
	}

	// Cancel setup
	function cancelSetup() {
		setupStep = 'idle';
		setupData = null;
		verifyCode = '';
		setupError = null;
	}

	// Open disable modal
	function openDisableModal() {
		disablePassword = '';
		disableError = null;
		showDisableModal = true;
	}

	// Close disable modal
	function closeDisableModal() {
		showDisableModal = false;
		disablePassword = '';
		disableError = null;
	}

	// Disable 2FA
	async function disable2FA() {
		if (!disablePassword) {
			disableError = 'Please enter your password';
			return;
		}

		isDisabling = true;
		disableError = null;

		try {
			const result = await apiClient.disableTwoFactor(disablePassword);
			if (result.success) {
				successMessage = '2FA has been disabled';
				status = await apiClient.getTwoFactorStatus();
				closeDisableModal();
			} else {
				disableError = result.message || 'Failed to disable 2FA';
			}
		} catch (e) {
			disableError = e instanceof Error ? e.message : 'Failed to disable 2FA';
		} finally {
			isDisabling = false;
		}
	}

	// Regenerate backup codes
	async function regenerateBackupCodes() {
		isRegeneratingCodes = true;
		regenerateError = null;

		try {
			const result = await apiClient.regenerateBackupCodes();
			backupCodes = result.backup_codes;
			codesCopied = false;
			status = await apiClient.getTwoFactorStatus();
			successMessage = 'Backup codes regenerated. Save them securely!';
			showBackupCodesModal = true;
		} catch (e) {
			regenerateError = e instanceof Error ? e.message : 'Failed to regenerate codes';
		} finally {
			isRegeneratingCodes = false;
		}
	}

	// Copy backup codes to clipboard
	async function copyBackupCodes() {
		try {
			await navigator.clipboard.writeText(backupCodes.join('\n'));
			codesCopied = true;
			setTimeout(() => (codesCopied = false), 3000);
		} catch {
			// Fallback for older browsers
			const textarea = document.createElement('textarea');
			textarea.value = backupCodes.join('\n');
			document.body.appendChild(textarea);
			textarea.select();
			document.execCommand('copy');
			document.body.removeChild(textarea);
			codesCopied = true;
			setTimeout(() => (codesCopied = false), 3000);
		}
	}

	// Format date
	function formatDate(dateStr: string | null): string {
		if (!dateStr) return 'Unknown';
		return new Date(dateStr).toLocaleDateString(undefined, {
			year: 'numeric',
			month: 'long',
			day: 'numeric'
		});
	}
</script>

<svelte:head>
	<title>Security Settings - Board of One</title>
</svelte:head>

{#if isLoading}
	<div class="flex items-center justify-center py-12">
		<div
			class="animate-spin h-8 w-8 border-4 border-brand-600 border-t-transparent rounded-full"
		></div>
	</div>
{:else}
	<div class="space-y-6">
		{#if error}
			<Alert variant="error" dismissable ondismiss={() => (error = null)}>{error}</Alert>
		{/if}

		{#if successMessage}
			<Alert variant="success" dismissable ondismiss={() => (successMessage = null)}>
				{successMessage}
			</Alert>
		{/if}

		<!-- Two-Factor Authentication -->
		<div
			class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6"
		>
			<div class="flex items-start justify-between mb-4">
				<div>
					<h2 class="text-lg font-semibold text-slate-900 dark:text-white">
						Two-Factor Authentication
					</h2>
					<p class="text-sm text-slate-600 dark:text-slate-400 mt-1">
						Add an extra layer of security to your account using an authenticator app.
					</p>
				</div>
				{#if status?.enabled}
					<span
						class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-success-100 dark:bg-success-900/30 text-success-800 dark:text-success-400"
					>
						Enabled
					</span>
				{:else}
					<span
						class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400"
					>
						Disabled
					</span>
				{/if}
			</div>

			{#if status?.enabled}
				<!-- 2FA is enabled -->
				<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4 mb-4">
					<div class="flex items-center gap-3">
						<div class="p-2 bg-success-100 dark:bg-success-900/30 rounded-full">
							<svg
								class="w-5 h-5 text-success-600 dark:text-success-400"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
								/>
							</svg>
						</div>
						<div>
							<p class="font-medium text-slate-900 dark:text-white">
								Your account is protected with 2FA
							</p>
							<p class="text-sm text-slate-500 dark:text-slate-400">
								Enabled on {formatDate(status.enabled_at)}
							</p>
						</div>
					</div>
				</div>

				<!-- Backup codes info -->
				<div class="flex items-center justify-between py-3 border-t border-slate-200 dark:border-slate-700">
					<div>
						<p class="font-medium text-slate-900 dark:text-white">Backup Codes</p>
						<p class="text-sm text-slate-500 dark:text-slate-400">
							{status.backup_codes_remaining} codes remaining
						</p>
					</div>
					<Button
						variant="secondary"
						loading={isRegeneratingCodes}
						onclick={regenerateBackupCodes}
					>
						Regenerate
					</Button>
				</div>

				{#if regenerateError}
					<Alert variant="error" class="mt-2">{regenerateError}</Alert>
				{/if}

				<!-- Disable button -->
				<div class="mt-6 pt-6 border-t border-slate-200 dark:border-slate-700">
					<Button variant="danger" onclick={openDisableModal}>Disable 2FA</Button>
					<p class="text-xs text-slate-500 dark:text-slate-400 mt-2">
						You'll need to enter your password to disable 2FA.
					</p>
				</div>
			{:else if setupStep === 'idle'}
				<!-- 2FA not enabled -->
				{#if status?.available === false}
					<!-- 2FA not available (requires license) -->
					<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4 mb-4">
						<div class="flex gap-3">
							<svg
								class="w-5 h-5 text-slate-500 dark:text-slate-400 flex-shrink-0 mt-0.5"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
								/>
							</svg>
							<div>
								<p class="font-medium text-slate-700 dark:text-slate-300">
									Two-Factor Authentication Coming Soon
								</p>
								<p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
									{status?.unavailable_reason || 'This feature is currently not available.'}
									We're working on making this available in a future update.
								</p>
							</div>
						</div>
					</div>
				{:else}
					<!-- 2FA available, show setup prompt -->
					<div class="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-4 mb-4">
						<div class="flex gap-3">
							<svg
								class="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
								/>
							</svg>
							<div>
								<p class="font-medium text-amber-800 dark:text-amber-200">
									Protect your account
								</p>
								<p class="text-sm text-amber-700 dark:text-amber-300 mt-1">
									Enable 2FA to add an extra layer of security. You'll need an authenticator
									app like Google Authenticator, Authy, or 1Password.
								</p>
							</div>
						</div>
					</div>

					<Button variant="brand" loading={isSettingUp} onclick={startSetup}>Enable 2FA</Button>
				{/if}
			{:else if setupStep === 'qr'}
				<!-- Setup step 1: Show QR code -->
				{#if setupError}
					<Alert variant="error" class="mb-4">{setupError}</Alert>
				{/if}

				<div class="space-y-4">
					<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-6 text-center">
						<p class="text-sm text-slate-600 dark:text-slate-400 mb-4">
							Scan this QR code with your authenticator app:
						</p>

						<!-- QR Code placeholder - using a simple representation -->
						<div class="inline-block bg-white p-4 rounded-lg shadow-sm">
							<!-- Use an img tag with the QR URI encoded as a data URL or a QR library -->
							<!-- For now, show the secret for manual entry -->
							{#if setupData?.qr_uri}
								<img
									src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={encodeURIComponent(setupData.qr_uri)}"
									alt="2FA QR Code"
									class="w-48 h-48"
								/>
							{/if}
						</div>

						<div class="mt-4">
							<p class="text-xs text-slate-500 dark:text-slate-400 mb-1">
								Or enter this code manually:
							</p>
							<code
								class="inline-block px-3 py-1.5 bg-slate-100 dark:bg-slate-800 rounded font-mono text-sm text-slate-900 dark:text-white select-all"
							>
								{setupData?.secret}
							</code>
						</div>
					</div>

					<div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
						<p class="text-sm text-blue-800 dark:text-blue-200">
							<strong>Important:</strong> Save your backup codes now! These are shown only once and can
							be used to access your account if you lose your authenticator.
						</p>
					</div>

					<!-- Backup codes display -->
					<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4">
						<div class="flex items-center justify-between mb-2">
							<p class="font-medium text-slate-900 dark:text-white">Backup Codes</p>
							<Button variant="ghost" size="sm" onclick={copyBackupCodes}>
								{codesCopied ? 'Copied!' : 'Copy'}
							</Button>
						</div>
						<div class="grid grid-cols-2 gap-2">
							{#each backupCodes as code}
								<code
									class="px-2 py-1 bg-white dark:bg-slate-800 rounded font-mono text-sm text-slate-700 dark:text-slate-300"
								>
									{code}
								</code>
							{/each}
						</div>
					</div>

					<div>
						<label for="verify-code" class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
							Enter the code from your authenticator app to verify:
						</label>
						<div class="flex gap-3">
							<input
								id="verify-code"
								type="text"
								inputmode="numeric"
								pattern="[0-9]*"
								maxlength="6"
								bind:value={verifyCode}
								placeholder="123456"
								class="flex-1 px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500 font-mono text-lg tracking-widest text-center"
								onkeydown={(e) => e.key === 'Enter' && verifySetup()}
							/>
							<Button variant="brand" loading={isVerifying} onclick={verifySetup}>
								Verify
							</Button>
						</div>
					</div>

					<div class="flex justify-start">
						<Button variant="ghost" onclick={cancelSetup}>Cancel Setup</Button>
					</div>
				</div>
			{/if}
		</div>

		<!-- Security recommendations -->
		<div
			class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4"
		>
			<div class="flex gap-3">
				<svg
					class="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
				<div class="text-sm text-blue-900 dark:text-blue-200">
					<p class="font-semibold mb-1">Security Tips</p>
					<ul class="text-blue-800 dark:text-blue-300 list-disc list-inside space-y-1">
						<li>Use a unique, strong password for your account</li>
						<li>Enable 2FA for an extra layer of protection</li>
						<li>Store your backup codes in a secure location</li>
						<li>Never share your 2FA codes with anyone</li>
					</ul>
				</div>
			</div>
		</div>
	</div>
{/if}

<!-- Disable 2FA Modal -->
<Modal bind:open={showDisableModal} title="Disable Two-Factor Authentication" size="md" onclose={closeDisableModal}>
	<div class="space-y-4">
		<Alert variant="warning">
			Disabling 2FA will make your account less secure. You'll only need your password to sign in.
		</Alert>

		{#if disableError}
			<Alert variant="error">{disableError}</Alert>
		{/if}

		<div>
			<label for="disable-password" class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
				Enter your password to confirm:
			</label>
			<input
				id="disable-password"
				type="password"
				bind:value={disablePassword}
				placeholder="Your password"
				class="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
				onkeydown={(e) => e.key === 'Enter' && disable2FA()}
			/>
		</div>
	</div>

	{#snippet footer()}
		<div class="flex justify-end gap-3">
			<Button variant="secondary" onclick={closeDisableModal}>Cancel</Button>
			<Button variant="danger" loading={isDisabling} onclick={disable2FA}>
				Disable 2FA
			</Button>
		</div>
	{/snippet}
</Modal>

<!-- Backup Codes Modal -->
<Modal bind:open={showBackupCodesModal} title="Backup Codes" size="md" onclose={() => showBackupCodesModal = false}>
	<div class="space-y-4">
		<Alert variant="warning">
			Save these codes in a secure place. Each code can only be used once and this is the last time
			they'll be shown.
		</Alert>

		<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4">
			<div class="flex items-center justify-between mb-3">
				<p class="font-medium text-slate-900 dark:text-white">Your Backup Codes</p>
				<Button variant="ghost" size="sm" onclick={copyBackupCodes}>
					{codesCopied ? 'Copied!' : 'Copy All'}
				</Button>
			</div>
			<div class="grid grid-cols-2 gap-2">
				{#each backupCodes as code}
					<code
						class="px-3 py-2 bg-white dark:bg-slate-800 rounded font-mono text-sm text-slate-700 dark:text-slate-300 text-center"
					>
						{code}
					</code>
				{/each}
			</div>
		</div>

		<p class="text-sm text-slate-600 dark:text-slate-400">
			If you lose access to your authenticator app, use one of these codes to sign in. Each code
			can only be used once.
		</p>
	</div>

	{#snippet footer()}
		<div class="flex justify-end">
			<Button variant="brand" onclick={() => showBackupCodesModal = false}>
				I've Saved My Codes
			</Button>
		</div>
	{/snippet}
</Modal>
