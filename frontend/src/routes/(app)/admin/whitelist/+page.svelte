<script lang="ts">
	import { enhance } from '$app/forms';
	import { Button } from '$lib/components/ui';
	import { Plus, Trash2, Mail, Lock } from 'lucide-svelte';

	interface WhitelistEntry {
		id: string;
		email: string;
		added_by: string | null;
		notes: string | null;
		created_at: string;
	}

	let { data, form } = $props();

	let entries = $state<WhitelistEntry[]>(data.entries || []);
	let envEmails = $state<string[]>(data.envEmails || []);
	let totalCount = $state(data.totalCount || 0);
	let newEmail = $state('');
	let newNotes = $state('');
	let isAdding = $state(false);
	let isRemoving = $state(false);

	// Update local state when data changes
	$effect(() => {
		entries = data.entries || [];
		envEmails = data.envEmails || [];
		totalCount = data.totalCount || 0;
	});

	// Check if an email is only in env (not in db)
	function isEnvOnly(email: string): boolean {
		const dbEmails = entries.map(e => e.email.toLowerCase());
		return envEmails.includes(email.toLowerCase()) && !dbEmails.includes(email.toLowerCase());
	}
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
			<form
				method="POST"
				action="?/add"
				use:enhance={() => {
					isAdding = true;
					return async ({ result, update }) => {
						isAdding = false;
						if (result.type === 'success') {
							newEmail = '';
							newNotes = '';
							await update();
						}
					};
				}}
				class="space-y-4"
			>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div>
						<label for="email" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
							Email Address
						</label>
						<input
							type="email"
							id="email"
							name="email"
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
							name="notes"
							bind:value={newNotes}
							placeholder="YC batch W25, referred by..."
							class="w-full px-4 py-2 border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 focus:ring-2 focus:ring-brand-500 focus:border-transparent"
						/>
					</div>
				</div>
				{#if form?.error}
					<p class="text-sm text-error-600 dark:text-error-400">{form.error}</p>
				{/if}
				<Button type="submit" variant="brand" disabled={isAdding || !newEmail.trim()}>
					{#snippet children()}
						<Plus class="w-4 h-4 mr-2" />
						{isAdding ? 'Adding...' : 'Add to Whitelist'}
					{/snippet}
				</Button>
			</form>
		</div>
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
						<ul class="space-y-1">
							{#each envEmails as email}
								<li class="text-amber-900 dark:text-amber-100 font-mono text-sm">
									{email}
								</li>
							{/each}
						</ul>
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
								<form
									method="POST"
									action="?/remove"
									use:enhance={() => {
										if (!confirm(`Remove ${entry.email} from whitelist?`)) {
											return () => {};
										}
										isRemoving = true;
										return async ({ update }) => {
											isRemoving = false;
											await update();
										};
									}}
								>
									<input type="hidden" name="email" value={entry.email} />
									<button
										type="submit"
										disabled={isRemoving}
										class="p-2 text-neutral-400 hover:text-error-500 dark:hover:text-error-400 transition-colors disabled:opacity-50"
										aria-label="Remove from whitelist"
									>
										<Trash2 class="w-5 h-5" />
									</button>
								</form>
							</div>
						{/each}
					</div>
				{/if}
			</div>
	</main>
</div>
