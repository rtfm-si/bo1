<script lang="ts">
	/**
	 * Privacy Settings - GDPR data export, account deletion, email preferences, data retention
	 */
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { apiClient } from '$lib/api/client';
	import type { EmailPreferences } from '$lib/api/client';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';

	// Retention period options (days) - 1-3 years or forever
	const RETENTION_OPTIONS = [
		{ value: 365, label: '1 year' },
		{ value: 730, label: '2 years' },
		{ value: 1095, label: '3 years' },
		{ value: -1, label: 'Forever' }
	];

	// Compute display options (includes legacy value if needed)
	const displayOptions = $derived(() => {
		const knownValues = RETENTION_OPTIONS.map((o) => o.value);
		if (!knownValues.includes(retentionDays) && retentionDays > 0) {
			// Legacy value (e.g., 5 years = 1825, 10 years = 3650)
			const years = Math.round(retentionDays / 365);
			return [
				{ value: retentionDays, label: `${years} years (legacy)` },
				...RETENTION_OPTIONS
			];
		}
		return RETENTION_OPTIONS;
	});

	// State
	let emailPrefs = $state<EmailPreferences | null>(null);
	let retentionDays = $state<number>(730);
	let isLoading = $state(true);
	let isSaving = $state(false);
	let isSavingRetention = $state(false);
	let isExporting = $state(false);
	let isDeleting = $state(false);
	let error = $state<string | null>(null);
	let successMessage = $state<string | null>(null);
	let exportError = $state<string | null>(null);
	let retentionError = $state<string | null>(null);
	let retentionSuccess = $state<string | null>(null);

	// Delete account modal
	let showDeleteModal = $state(false);
	let deleteConfirmText = $state('');
	let deleteError = $state<string | null>(null);

	// Load email preferences and retention setting
	onMount(async () => {
		try {
			const [emailResponse, retentionResponse] = await Promise.all([
				apiClient.getEmailPreferences(),
				apiClient.getRetentionSetting()
			]);
			emailPrefs = emailResponse.preferences;
			retentionDays = retentionResponse.data_retention_days;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load settings';
			// Set defaults if load fails
			emailPrefs = {
				meeting_emails: true,
				reminder_emails: true,
				digest_emails: true
			};
			retentionDays = 730;
		} finally {
			isLoading = false;
		}
	});

	// Save email preferences
	async function savePreferences() {
		if (!emailPrefs) return;
		isSaving = true;
		error = null;
		successMessage = null;

		try {
			await apiClient.updateEmailPreferences(emailPrefs);
			successMessage = 'Email preferences saved';
			setTimeout(() => {
				successMessage = null;
			}, 3000);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to save preferences';
		} finally {
			isSaving = false;
		}
	}

	// Save retention setting
	async function saveRetentionSetting() {
		isSavingRetention = true;
		retentionError = null;
		retentionSuccess = null;

		try {
			const response = await apiClient.updateRetentionSetting(retentionDays);
			retentionDays = response.data_retention_days;
			retentionSuccess = 'Data retention setting saved';
			setTimeout(() => {
				retentionSuccess = null;
			}, 3000);
		} catch (e) {
			retentionError = e instanceof Error ? e.message : 'Failed to save retention setting';
		} finally {
			isSavingRetention = false;
		}
	}

	// Export user data
	async function exportData() {
		isExporting = true;
		exportError = null;

		try {
			const blob = await apiClient.exportUserData();
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `boardof_one_export_${new Date().toISOString().split('T')[0]}.json`;
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			URL.revokeObjectURL(url);
		} catch (e: unknown) {
			if (e && typeof e === 'object' && 'status' in e && e.status === 429) {
				exportError = 'You can only export data once every 24 hours.';
			} else {
				exportError = e instanceof Error ? e.message : 'Failed to export data';
			}
		} finally {
			isExporting = false;
		}
	}

	// Delete account
	async function deleteAccount() {
		if (deleteConfirmText !== 'DELETE') return;

		isDeleting = true;
		deleteError = null;

		try {
			await apiClient.deleteUserAccount();
			// Redirect to login after deletion
			goto('/login?deleted=true');
		} catch (e: unknown) {
			if (e && typeof e === 'object' && 'status' in e && e.status === 429) {
				deleteError = 'A deletion request is already in progress.';
			} else {
				deleteError = e instanceof Error ? e.message : 'Failed to delete account';
			}
		} finally {
			isDeleting = false;
		}
	}

	function openDeleteModal() {
		deleteConfirmText = '';
		deleteError = null;
		showDeleteModal = true;
	}

	function closeDeleteModal() {
		showDeleteModal = false;
		deleteConfirmText = '';
		deleteError = null;
	}
</script>

<svelte:head>
	<title>Privacy Settings - Board of One</title>
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
			<Alert variant="success" dismissable ondismiss={() => (successMessage = null)}
				>{successMessage}</Alert
			>
		{/if}

		<!-- Email Preferences -->
		<div
			class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6"
		>
			<h2 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">Email Preferences</h2>
			<p class="text-sm text-slate-600 dark:text-slate-400 mb-6">
				Choose which emails you want to receive from Board of One.
			</p>

			<div class="space-y-4">
				<label class="flex items-center justify-between cursor-pointer">
					<div>
						<p class="font-medium text-slate-900 dark:text-white">Meeting notifications</p>
						<p class="text-sm text-slate-500 dark:text-slate-400">
							Emails when your meetings complete
						</p>
					</div>
					<button
						type="button"
						role="switch"
						aria-checked={emailPrefs?.meeting_emails}
						aria-label="Toggle meeting notifications"
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors {emailPrefs?.meeting_emails
							? 'bg-brand-600'
							: 'bg-slate-300 dark:bg-slate-600'}"
						onclick={() => {
							if (emailPrefs) emailPrefs.meeting_emails = !emailPrefs.meeting_emails;
						}}
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {emailPrefs?.meeting_emails
								? 'translate-x-6'
								: 'translate-x-1'}"
						></span>
					</button>
				</label>

				<label class="flex items-center justify-between cursor-pointer">
					<div>
						<p class="font-medium text-slate-900 dark:text-white">Action reminders</p>
						<p class="text-sm text-slate-500 dark:text-slate-400">
							Reminders for upcoming and overdue actions
						</p>
					</div>
					<button
						type="button"
						role="switch"
						aria-checked={emailPrefs?.reminder_emails}
						aria-label="Toggle action reminders"
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors {emailPrefs?.reminder_emails
							? 'bg-brand-600'
							: 'bg-slate-300 dark:bg-slate-600'}"
						onclick={() => {
							if (emailPrefs) emailPrefs.reminder_emails = !emailPrefs.reminder_emails;
						}}
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {emailPrefs?.reminder_emails
								? 'translate-x-6'
								: 'translate-x-1'}"
						></span>
					</button>
				</label>

				<label class="flex items-center justify-between cursor-pointer">
					<div>
						<p class="font-medium text-slate-900 dark:text-white">Weekly digest</p>
						<p class="text-sm text-slate-500 dark:text-slate-400">
							Weekly summary of your meetings and actions
						</p>
					</div>
					<button
						type="button"
						role="switch"
						aria-checked={emailPrefs?.digest_emails}
						aria-label="Toggle weekly digest"
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors {emailPrefs?.digest_emails
							? 'bg-brand-600'
							: 'bg-slate-300 dark:bg-slate-600'}"
						onclick={() => {
							if (emailPrefs) emailPrefs.digest_emails = !emailPrefs.digest_emails;
						}}
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {emailPrefs?.digest_emails
								? 'translate-x-6'
								: 'translate-x-1'}"
						></span>
					</button>
				</label>
			</div>

			<div class="mt-6 flex justify-end">
				<Button variant="brand" loading={isSaving} onclick={savePreferences}>
					Save Preferences
				</Button>
			</div>
		</div>

		<!-- Data Retention -->
		<div
			class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6"
		>
			<h2 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">Data Retention</h2>
			<p class="text-sm text-slate-600 dark:text-slate-400 mb-4">
				Choose how long to keep your meeting data. After this period, meetings, actions, and
				associated data will be automatically deleted. Select "Forever" to keep data until you
				delete your account.
			</p>

			{#if retentionError}
				<Alert variant="error" class="mb-4" dismissable ondismiss={() => (retentionError = null)}
					>{retentionError}</Alert
				>
			{/if}

			{#if retentionSuccess}
				<Alert variant="success" class="mb-4" dismissable ondismiss={() => (retentionSuccess = null)}
					>{retentionSuccess}</Alert
				>
			{/if}

			<div class="flex flex-col sm:flex-row sm:items-center gap-4">
				<label for="retention-select" class="sr-only">Data retention period</label>
				<select
					id="retention-select"
					bind:value={retentionDays}
					class="flex-1 sm:flex-none sm:w-48 px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
				>
					{#each displayOptions() as option}
						<option value={option.value}>{option.label}</option>
					{/each}
				</select>
				<Button variant="brand" loading={isSavingRetention} onclick={saveRetentionSetting}>
					Save
				</Button>
			</div>

			<div class="mt-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg p-4">
				<p class="text-sm text-amber-800 dark:text-amber-200">
					<strong>What gets deleted:</strong> Meetings, contributions, actions, and session data older
					than your retention period. Your profile, business context, and datasets are not affected.
				</p>
			</div>

			<p class="mt-3 text-xs text-slate-500 dark:text-slate-400">
				Note: Changing to a shorter period does not immediately delete data. The cleanup job runs
				periodically.
			</p>
		</div>

		<!-- Data Export -->
		<div
			class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6"
		>
			<h2 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">Export Your Data</h2>
			<p class="text-sm text-slate-600 dark:text-slate-400 mb-4">
				Download a copy of all your data including your profile, business context, meetings,
				actions, and datasets. This export is provided in JSON format.
			</p>

			{#if exportError}
				<Alert variant="warning" class="mb-4">{exportError}</Alert>
			{/if}

			<Button variant="secondary" loading={isExporting} onclick={exportData}>
				{#if isExporting}
					Preparing Export...
				{:else}
					Download My Data
				{/if}
			</Button>

			<p class="mt-3 text-xs text-slate-500 dark:text-slate-400">
				Note: You can request a data export once every 24 hours.
			</p>
		</div>

		<!-- Account Deletion -->
		<div
			class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-error-200 dark:border-error-800 p-6"
		>
			<h2 class="text-lg font-semibold text-error-700 dark:text-error-400 mb-4">Delete Account</h2>
			<p class="text-sm text-slate-600 dark:text-slate-400 mb-4">
				Permanently delete your account and all associated data. This action cannot be undone.
			</p>

			<div class="bg-error-50 dark:bg-error-900/20 rounded-lg p-4 mb-4">
				<p class="text-sm text-error-800 dark:text-error-200 font-medium mb-2">
					What happens when you delete your account:
				</p>
				<ul class="text-sm text-error-700 dark:text-error-300 space-y-1 list-disc list-inside">
					<li>Your profile and business context will be permanently deleted</li>
					<li>Your meetings will be anonymized</li>
					<li>Your actions will be anonymized</li>
					<li>Your datasets and uploaded files will be deleted</li>
				</ul>
			</div>

			<Button variant="danger" onclick={openDeleteModal}>Delete My Account</Button>
		</div>

		<!-- GDPR Info -->
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
					<p class="font-semibold mb-1">Your Privacy Rights</p>
					<p class="text-blue-800 dark:text-blue-300">
						Under GDPR, you have the right to access, export, and delete your personal data. For
						more information, see our
						<a href="/legal/privacy" class="underline hover:no-underline">Privacy Policy</a>.
					</p>
				</div>
			</div>
		</div>
	</div>
{/if}

<!-- Delete Account Confirmation Modal -->
<Modal bind:open={showDeleteModal} title="Delete Account" size="md" onclose={closeDeleteModal}>
	<div class="space-y-4">
		<Alert variant="error">
			This action is permanent and cannot be undone. All your data will be deleted or anonymized.
		</Alert>

		{#if deleteError}
			<Alert variant="warning">{deleteError}</Alert>
		{/if}

		<p class="text-slate-700 dark:text-slate-300">
			To confirm deletion, please type <span class="font-mono font-bold">DELETE</span> below:
		</p>

		<input
			type="text"
			bind:value={deleteConfirmText}
			placeholder="Type DELETE to confirm"
			class="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-error-500 focus:border-error-500"
		/>
	</div>

	{#snippet footer()}
		<div class="flex justify-end gap-3">
			<Button variant="secondary" onclick={closeDeleteModal}>Cancel</Button>
			<Button
				variant="danger"
				disabled={deleteConfirmText !== 'DELETE'}
				loading={isDeleting}
				onclick={deleteAccount}
			>
				Delete My Account
			</Button>
		</div>
	{/snippet}
</Modal>
