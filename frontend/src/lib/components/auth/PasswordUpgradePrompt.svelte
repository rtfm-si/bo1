<script lang="ts">
	/**
	 * Password Upgrade Prompt - Non-blocking modal for weak password upgrade
	 *
	 * Shows when user logs in with a password that doesn't meet current strength
	 * requirements. User can upgrade now or dismiss (snooze for 7 days).
	 *
	 * Requirements for new password:
	 * - At least 12 characters
	 * - Contains at least one letter (a-z or A-Z)
	 * - Contains at least one digit (0-9)
	 */

	import { browser } from '$app/environment';
	import { env } from '$env/dynamic/public';
	import { passwordUpgradeNeeded, clearPasswordUpgradeFlag } from '$lib/stores/auth';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import { Shield } from 'lucide-svelte';

	const API_BASE_URL = env.PUBLIC_API_URL || 'http://localhost:8000';
	const DISMISS_KEY = 'bo1_password_upgrade_dismissed';
	const SNOOZE_DAYS = 7;

	// State
	let isOpen = $state(false);
	let isDismissedLocally = $state(false);
	let oldPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);
	let successMessage = $state<string | null>(null);

	// Validation
	const passwordRequirements = $derived.by(() => ({
		length: newPassword.length >= 12,
		hasLetter: /[a-zA-Z]/.test(newPassword),
		hasDigit: /\d/.test(newPassword),
		matches: newPassword === confirmPassword && newPassword.length > 0,
	}));

	const isValidNewPassword = $derived(
		passwordRequirements.length &&
			passwordRequirements.hasLetter &&
			passwordRequirements.hasDigit &&
			passwordRequirements.matches
	);

	// Check snooze status on mount
	// Defer mutations to avoid state_unsafe_mutation during effect
	$effect(() => {
		if (browser) {
			const dismissedAt = localStorage.getItem(DISMISS_KEY);
			if (dismissedAt) {
				const dismissedDate = new Date(dismissedAt);
				const now = new Date();
				const daysSinceDismiss =
					(now.getTime() - dismissedDate.getTime()) / (1000 * 60 * 60 * 24);
				if (daysSinceDismiss < SNOOZE_DAYS) {
					queueMicrotask(() => { isDismissedLocally = true; });
				} else {
					localStorage.removeItem(DISMISS_KEY);
				}
			}
		}
	});

	// Show modal when needed
	// Defer mutation to avoid state_unsafe_mutation during effect
	$effect(() => {
		if ($passwordUpgradeNeeded && !isDismissedLocally && !successMessage) {
			queueMicrotask(() => { isOpen = true; });
		}
	});

	function handleSnooze() {
		if (browser) {
			localStorage.setItem(DISMISS_KEY, new Date().toISOString());
		}
		isDismissedLocally = true;
		isOpen = false;
	}

	async function handleUpgrade() {
		if (!isValidNewPassword || isSubmitting) return;

		isSubmitting = true;
		error = null;

		try {
			const response = await fetch(`${API_BASE_URL}/api/v1/user/upgrade-password`, {
				method: 'POST',
				credentials: 'include',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					old_password: oldPassword,
					new_password: newPassword,
				}),
			});

			if (!response.ok) {
				const data = await response.json();
				throw new Error(data.detail || 'Failed to upgrade password');
			}

			// Success - clear flag and show success message
			clearPasswordUpgradeFlag();
			if (browser) {
				localStorage.removeItem(DISMISS_KEY);
			}
			successMessage = 'Password upgraded successfully!';

			// Close modal after a short delay
			setTimeout(() => {
				isOpen = false;
				successMessage = null;
			}, 2000);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to upgrade password';
		} finally {
			isSubmitting = false;
		}
	}

	function handleClose() {
		handleSnooze();
	}
</script>

<Modal open={isOpen} title="Upgrade Your Password" size="sm" onclose={handleClose}>
	<div class="space-y-4">
		{#if successMessage}
			<Alert variant="success" title="Success">
				{successMessage}
			</Alert>
		{:else}
			<div class="flex items-start gap-3 p-3 bg-warning-50 dark:bg-warning-900/20 rounded-lg">
				<Shield class="w-5 h-5 text-warning-600 dark:text-warning-400 flex-shrink-0 mt-0.5" />
				<p class="text-sm text-warning-800 dark:text-warning-200">
					Your current password doesn't meet our updated security requirements. Please update it to
					keep your account secure.
				</p>
			</div>

			{#if error}
				<Alert variant="error" dismissable ondismiss={() => (error = null)}>
					{error}
				</Alert>
			{/if}

			<form onsubmit={(e) => { e.preventDefault(); handleUpgrade(); }} class="space-y-4">
				<Input
					type="password"
					label="Current Password"
					placeholder="Enter your current password"
					bind:value={oldPassword}
					required
				/>

				<Input
					type="password"
					label="New Password"
					placeholder="Enter a new password"
					bind:value={newPassword}
					required
					error={newPassword.length > 0 && !passwordRequirements.length
						? 'Password must be at least 12 characters'
						: undefined}
				/>

				<!-- Password requirements checklist -->
				<div class="text-sm space-y-1 text-neutral-600 dark:text-neutral-400">
					<p class="font-medium">Password requirements:</p>
					<ul class="space-y-0.5 ml-2">
						<li class={passwordRequirements.length ? 'text-success-600 dark:text-success-400' : ''}>
							{passwordRequirements.length ? '✓' : '○'} At least 12 characters
						</li>
						<li class={passwordRequirements.hasLetter ? 'text-success-600 dark:text-success-400' : ''}>
							{passwordRequirements.hasLetter ? '✓' : '○'} Contains a letter (a-z)
						</li>
						<li class={passwordRequirements.hasDigit ? 'text-success-600 dark:text-success-400' : ''}>
							{passwordRequirements.hasDigit ? '✓' : '○'} Contains a number (0-9)
						</li>
					</ul>
				</div>

				<Input
					type="password"
					label="Confirm New Password"
					placeholder="Confirm your new password"
					bind:value={confirmPassword}
					required
					error={confirmPassword.length > 0 && !passwordRequirements.matches
						? 'Passwords do not match'
						: undefined}
				/>

				<div class="flex justify-end gap-3 pt-2">
					<Button variant="ghost" onclick={handleSnooze} disabled={isSubmitting}>
						Remind me later
					</Button>
					<Button
						type="submit"
						variant="brand"
						disabled={!isValidNewPassword || !oldPassword}
						loading={isSubmitting}
					>
						Upgrade Password
					</Button>
				</div>
			</form>
		{/if}
	</div>
</Modal>
