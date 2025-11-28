<script lang="ts">
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import { Button } from '$lib/components/ui';
	import { Plus, Trash2, Mail, Lock } from 'lucide-svelte';

	interface WhitelistEntry {
		id: string;
		email: string;
		added_by: string | null;
		notes: string | null;
		created_at: string;
	}

	let entries = $state<WhitelistEntry[]>([]);
	let envEmails = $state<string[]>([]);
	let totalCount = $state(0);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let newEmail = $state('');
	let newNotes = $state('');
	let isAdding = $state(false);
	let addError = $state<string | null>(null);

	// Check if an email is only in env (not in db)
	function isEnvOnly(email: string): boolean {
		const dbEmails = entries.map(e => e.email.toLowerCase());
		return envEmails.includes(email.toLowerCase()) && !dbEmails.includes(email.toLowerCase());
	}

	async function loadWhitelist() {
		try {
			isLoading = true;
			error = null;
			const response = await apiClient.listWhitelist();
			entries = response.emails;
			envEmails = response.env_emails || [];
			totalCount = response.total_count;
		} catch (err) {
			console.error('Failed to load whitelist:', err);
			error = err instanceof Error ? err.message : 'Failed to load whitelist';
		} finally {
			isLoading = false;
		}
	}

	async function addToWhitelist() {
		if (!newEmail.trim()) return;

		try {
			isAdding = true;
			addError = null;
			await apiClient.addToWhitelist({ email: newEmail.trim(), notes: newNotes.trim() || undefined });
			newEmail = '';
			newNotes = '';
			await loadWhitelist();
		} catch (err) {
			console.error('Failed to add to whitelist:', err);
			addError = err instanceof Error ? err.message : 'Failed to add email';
		} finally {
			isAdding = false;
		}
	}

	async function removeFromWhitelist(email: string) {
		if (!confirm(`Remove ${email} from whitelist?`)) return;

		try {
			await apiClient.removeFromWhitelist(email);
			await loadWhitelist();
		} catch (err) {
			console.error('Failed to remove from whitelist:', err);
			error = err instanceof Error ? err.message : 'Failed to remove email';
		}
	}

	onMount(() => {
		loadWhitelist();
	});
</script>

<svelte:head>
	<title>Beta Whitelist - Admin</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Header -->
	<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center gap-4">
				<a
					href="/admin"
					class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors duration-200"
					aria-label="Back to admin"
				>
					<svg class="w-5 h-5 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
					</svg>
				</a>
				<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">
					Beta Whitelist
				</h1>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Add New Email Form -->
		<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 mb-8">
			<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">Add to Whitelist</h2>
			<form onsubmit={(e) => { e.preventDefault(); addToWhitelist(); }} class="space-y-4">
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div>
						<label for="email" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
							Email Address
						</label>
						<input
							type="email"
							id="email"
							bind:value={newEmail}
							placeholder="user@example.com"
							class="w-full px-4 py-2 border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 focus:ring-2 focus:ring-brand-500 focus:border-transparent"
							required
						/>
					</div>
					<div>
						<label for="notes" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
							Notes (optional)
						</label>
						<input
							type="text"
							id="notes"
							bind:value={newNotes}
							placeholder="YC batch W25, referred by..."
							class="w-full px-4 py-2 border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 focus:ring-2 focus:ring-brand-500 focus:border-transparent"
						/>
					</div>
				</div>
				{#if addError}
					<p class="text-sm text-error-600 dark:text-error-400">{addError}</p>
				{/if}
				<Button type="submit" variant="brand" disabled={isAdding || !newEmail.trim()}>
					<Plus class="w-4 h-4 mr-2" />
					{isAdding ? 'Adding...' : 'Add to Whitelist'}
				</Button>
			</form>
		</div>

		{#if isLoading}
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-8 text-center">
				<div class="animate-spin w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full mx-auto"></div>
				<p class="mt-2 text-neutral-600 dark:text-neutral-400">Loading...</p>
			</div>
		{:else if error}
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-8 text-center">
				<p class="text-error-600 dark:text-error-400">{error}</p>
				<Button onclick={loadWhitelist} variant="ghost" class="mt-2">Retry</Button>
			</div>
		{:else}
			<!-- Env-based Whitelist (if any) -->
			{#if envEmails.length > 0}
				<div class="bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800 overflow-hidden mb-6">
					<div class="px-6 py-4 border-b border-amber-200 dark:border-amber-800 flex items-center gap-2">
						<Lock class="w-4 h-4 text-amber-600 dark:text-amber-400" />
						<h2 class="text-lg font-semibold text-amber-900 dark:text-amber-100">
							Environment Whitelist ({envEmails.length})
						</h2>
					</div>
					<div class="px-6 py-4">
						<p class="text-sm text-amber-700 dark:text-amber-300 mb-3">
							These emails are set via BETA_WHITELIST environment variable and cannot be edited here.
						</p>
						<div class="flex flex-wrap gap-2">
							{#each envEmails as email}
								<span class="px-3 py-1 bg-amber-100 dark:bg-amber-800 text-amber-800 dark:text-amber-200 rounded-full text-sm">
									{email}
								</span>
							{/each}
						</div>
					</div>
				</div>
			{/if}

			<!-- Database Whitelist -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
				<div class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
						Database Whitelist ({entries.length})
					</h2>
					<p class="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
						Emails added via admin panel. Total whitelisted: {totalCount}
					</p>
				</div>

				{#if entries.length === 0}
					<div class="p-8 text-center">
						<Mail class="w-12 h-12 text-neutral-400 mx-auto mb-2" />
						<p class="text-neutral-600 dark:text-neutral-400">No database entries yet</p>
						<p class="text-sm text-neutral-500 dark:text-neutral-500 mt-1">
							Add emails above to persist them in the database
						</p>
					</div>
				{:else}
					<div class="divide-y divide-neutral-200 dark:divide-neutral-700">
						{#each entries as entry (entry.id)}
							<div class="px-6 py-4 flex items-center justify-between hover:bg-neutral-50 dark:hover:bg-neutral-700/50">
								<div>
									<p class="font-medium text-neutral-900 dark:text-white">{entry.email}</p>
									<p class="text-sm text-neutral-500 dark:text-neutral-400">
										{#if entry.notes}
											{entry.notes} &bull;
										{/if}
										Added {new Date(entry.created_at).toLocaleDateString()}
									</p>
								</div>
								<button
									onclick={() => removeFromWhitelist(entry.email)}
									class="p-2 text-neutral-400 hover:text-error-500 dark:hover:text-error-400 transition-colors"
									aria-label="Remove from whitelist"
								>
									<Trash2 class="w-5 h-5" />
								</button>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}
	</main>
</div>
