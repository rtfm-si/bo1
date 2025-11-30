<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { enhance } from '$app/forms';
	import { Button } from '$lib/components/ui';
	import { Search, ChevronLeft, ChevronRight } from 'lucide-svelte';
	import { getTierColor } from '$lib/utils/color-helpers';

	let { data } = $props();

	let users = $state(data.users || []);
	let totalCount = $state(data.totalCount || 0);
	let currentPage = $state(data.page || 1);
	let perPage = $state(data.perPage || 20);
	let searchEmail = $state($page.url.searchParams.get('email') || '');

	// Edit state
	let editingUserId = $state<string | null>(null);
	let editForm = $state<{ subscription_tier?: string; is_admin?: boolean }>({});
	let isSubmitting = $state(false);

	// Update local state when data changes
	$effect(() => {
		users = data.users || [];
		totalCount = data.totalCount || 0;
		currentPage = data.page || 1;
		perPage = data.perPage || 20;
	});

	function handleSearch() {
		const url = new URL($page.url);
		url.searchParams.set('page', '1');
		if (searchEmail) {
			url.searchParams.set('email', searchEmail);
		} else {
			url.searchParams.delete('email');
		}
		goto(url.toString());
	}

	function nextPage() {
		if (currentPage * perPage < totalCount) {
			const url = new URL($page.url);
			url.searchParams.set('page', (currentPage + 1).toString());
			goto(url.toString());
		}
	}

	function prevPage() {
		if (currentPage > 1) {
			const url = new URL($page.url);
			url.searchParams.set('page', (currentPage - 1).toString());
			goto(url.toString());
		}
	}

	function startEdit(userId: string, currentTier: string, currentIsAdmin: boolean) {
		editingUserId = userId;
		editForm = {
			subscription_tier: currentTier,
			is_admin: currentIsAdmin
		};
	}

	function cancelEdit() {
		editingUserId = null;
		editForm = {};
	}

	function formatDate(dateString: string | null): string {
		if (!dateString) return 'Never';
		const date = new Date(dateString);
		return date.toLocaleDateString();
	}
</script>

<svelte:head>
	<title>User Management - Admin - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Header -->
	<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center gap-4">
				<a
					href="/admin"
					class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors duration-200"
					aria-label="Back to admin dashboard"
				>
					<svg class="w-5 h-5 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
					</svg>
				</a>
				<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">
					User Management
				</h1>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Search -->
		<div class="mb-6 bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
			<div class="flex gap-4">
				<div class="flex-1 relative">
					<div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
						<Search class="w-5 h-5 text-neutral-400" />
					</div>
					<input
						type="text"
						bind:value={searchEmail}
						placeholder="Search by email..."
						class="block w-full pl-10 pr-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
						onkeydown={(e) => e.key === 'Enter' && handleSearch()}
					/>
				</div>
				<Button variant="brand" size="md" onclick={handleSearch}>
					{#snippet children()}
						Search
					{/snippet}
				</Button>
			</div>
		</div>

		{#if users.length === 0}
			<!-- Empty State -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-12 text-center">
				<p class="text-neutral-600 dark:text-neutral-400">No users found</p>
			</div>
		{:else}
			<!-- Users Table -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
				<div class="overflow-x-auto">
					<table class="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
						<thead class="bg-neutral-50 dark:bg-neutral-900">
							<tr>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Email</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Tier</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Admin</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Meetings</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Cost</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Last Meeting</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Actions</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
							{#each users as user (user.user_id)}
								<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
									<td class="px-6 py-4 whitespace-nowrap">
										<div class="text-sm font-medium text-neutral-900 dark:text-white">{user.email}</div>
										<div class="text-xs text-neutral-500 dark:text-neutral-400">{user.auth_provider}</div>
									</td>
									<td class="px-6 py-4 whitespace-nowrap">
										{#if editingUserId === user.user_id}
											<select
												bind:value={editForm.subscription_tier}
												class="text-xs px-2 py-1 rounded-full border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900"
											>
												<option value="free">Free</option>
												<option value="pro">Pro</option>
												<option value="enterprise">Enterprise</option>
											</select>
										{:else}
											<span class="inline-flex text-xs px-2 py-1 rounded-full {getTierColor(user.subscription_tier)}">
												{user.subscription_tier}
											</span>
										{/if}
									</td>
									<td class="px-6 py-4 whitespace-nowrap">
										{#if editingUserId === user.user_id}
											<input
												type="checkbox"
												bind:checked={editForm.is_admin}
												class="rounded"
											/>
										{:else}
											{#if user.is_admin}
												<span class="inline-flex text-xs px-2 py-1 rounded-full bg-success-100 text-success-800 dark:bg-success-900/20 dark:text-success-300">
													Admin
												</span>
											{:else}
												<span class="text-neutral-400">-</span>
											{/if}
										{/if}
									</td>
									<td class="px-6 py-4 whitespace-nowrap text-sm text-neutral-900 dark:text-white">
										{user.total_meetings}
									</td>
									<td class="px-6 py-4 whitespace-nowrap text-sm text-neutral-900 dark:text-white">
										${user.total_cost?.toFixed(4) || '0.0000'}
									</td>
									<td class="px-6 py-4 whitespace-nowrap">
										{#if user.last_meeting_id}
											<a href="/meeting/{user.last_meeting_id}" class="text-sm text-brand-600 dark:text-brand-400 hover:underline">
												{formatDate(user.last_meeting_at)}
											</a>
										{:else}
											<span class="text-sm text-neutral-400">Never</span>
										{/if}
									</td>
									<td class="px-6 py-4 whitespace-nowrap text-sm">
										{#if editingUserId === user.user_id}
											<form
												method="POST"
												action="?/updateUser"
												use:enhance={() => {
													isSubmitting = true;
													return async ({ result }) => {
														isSubmitting = false;
														if (result.type === 'success') {
															editingUserId = null;
															editForm = {};
														} else if (result.type === 'failure') {
															alert(result.data?.error || 'Failed to update user');
														}
													};
												}}
											>
												<input type="hidden" name="userId" value={user.user_id} />
												<input type="hidden" name="subscription_tier" value={editForm.subscription_tier || user.subscription_tier} />
												<input type="hidden" name="is_admin" value={editForm.is_admin?.toString() || user.is_admin.toString()} />
												<div class="flex gap-2">
													<button
														type="submit"
														disabled={isSubmitting}
														class="text-success-600 dark:text-success-400 hover:underline disabled:opacity-50"
													>
														{isSubmitting ? 'Saving...' : 'Save'}
													</button>
													<button
														type="button"
														onclick={cancelEdit}
														disabled={isSubmitting}
														class="text-neutral-600 dark:text-neutral-400 hover:underline disabled:opacity-50"
													>
														Cancel
													</button>
												</div>
											</form>
										{:else}
											<button
												onclick={() => startEdit(user.user_id, user.subscription_tier, user.is_admin)}
												class="text-brand-600 dark:text-brand-400 hover:underline"
											>
												Edit
											</button>
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>

				<!-- Pagination -->
				<div class="bg-neutral-50 dark:bg-neutral-900 px-6 py-3 flex items-center justify-between border-t border-neutral-200 dark:border-neutral-700">
					<div class="text-sm text-neutral-700 dark:text-neutral-300">
						Showing {(currentPage - 1) * perPage + 1} to {Math.min(currentPage * perPage, totalCount)} of {totalCount} users
					</div>
					<div class="flex gap-2">
						<Button
							variant="secondary"
							size="sm"
							disabled={currentPage === 1}
							onclick={prevPage}
						>
							{#snippet children()}
								<ChevronLeft class="w-4 h-4" />
								Previous
							{/snippet}
						</Button>
						<Button
							variant="secondary"
							size="sm"
							disabled={currentPage * perPage >= totalCount}
							onclick={nextPage}
						>
							{#snippet children()}
								Next
								<ChevronRight class="w-4 h-4" />
							{/snippet}
						</Button>
					</div>
				</div>
			</div>
		{/if}
	</main>
</div>
