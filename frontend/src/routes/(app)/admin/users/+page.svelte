<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/stores';
	import { enhance } from '$app/forms';
	import { Button } from '$lib/components/ui';
	import { Search, ChevronLeft, ChevronRight, Lock, Unlock, Trash2, Eye, Gift, Mail, Heart } from 'lucide-svelte';
	import SendEmailModal from '$lib/components/admin/SendEmailModal.svelte';
	import { getTierColor } from '$lib/utils/colors';
	import { adminApi, type StartImpersonationRequest } from '$lib/api/admin';

	let { data } = $props();

	let users = $state<typeof data.users>([]);
	let totalCount = $state(0);
	let currentPage = $state(1);
	let perPage = $state(20);
	let searchEmail = $state($page.url.searchParams.get('email') || '');

	// Sync state when data prop changes
	$effect(() => {
		users = data.users || [];
		totalCount = data.totalCount || 0;
		currentPage = data.page || 1;
		perPage = data.perPage || 20;
	});

	// Edit state
	let editingUserId = $state<string | null>(null);
	let editForm = $state<{ subscription_tier?: string; is_admin?: boolean }>({});
	let isSubmitting = $state(false);

	// Modal state for lock/delete/impersonate/promo actions
	let lockModalUser = $state<{ user_id: string; email: string } | null>(null);
	let deleteModalUser = $state<{ user_id: string; email: string } | null>(null);
	let impersonateModalUser = $state<{ user_id: string; email: string; is_admin: boolean } | null>(null);
	let promoModalUser = $state<{ user_id: string; email: string } | null>(null);
	let lockReason = $state('');
	let hardDelete = $state(false);
	let impersonateReason = $state('');
	let impersonateWriteMode = $state(false);
	let impersonateDuration = $state(30);
	let promoCode = $state('');
	let promoError = $state('');
	let emailModalUser = $state<{ user_id: string; email: string } | null>(null);

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

	function openLockModal(user: { user_id: string; email: string }) {
		lockModalUser = user;
		lockReason = '';
	}

	function closeLockModal() {
		lockModalUser = null;
		lockReason = '';
	}

	function openDeleteModal(user: { user_id: string; email: string }) {
		deleteModalUser = user;
		hardDelete = false;
	}

	function closeDeleteModal() {
		deleteModalUser = null;
		hardDelete = false;
	}

	function openImpersonateModal(user: { user_id: string; email: string; is_admin: boolean }) {
		impersonateModalUser = user;
		impersonateReason = '';
		impersonateWriteMode = false;
		impersonateDuration = 30;
	}

	function closeImpersonateModal() {
		impersonateModalUser = null;
		impersonateReason = '';
		impersonateWriteMode = false;
		impersonateDuration = 30;
	}

	function openPromoModal(user: { user_id: string; email: string }) {
		promoModalUser = user;
		promoCode = '';
		promoError = '';
	}

	function closePromoModal() {
		promoModalUser = null;
		promoCode = '';
		promoError = '';
	}

	async function handleApplyPromo() {
		if (!promoModalUser || !promoCode.trim()) return;

		isSubmitting = true;
		promoError = '';
		try {
			await adminApi.applyPromoToUser(promoModalUser.user_id, promoCode.trim());
			closePromoModal();
			await invalidateAll();
		} catch (error: unknown) {
			if (error instanceof Error) {
				promoError = error.message;
			} else {
				promoError = 'Failed to apply promotion';
			}
		} finally {
			isSubmitting = false;
		}
	}

	async function handleImpersonate() {
		if (!impersonateModalUser || !impersonateReason.trim()) return;

		isSubmitting = true;
		try {
			const request: StartImpersonationRequest = {
				reason: impersonateReason,
				write_mode: impersonateWriteMode,
				duration_minutes: impersonateDuration
			};
			await adminApi.startImpersonation(impersonateModalUser.user_id, request);
			// Reload the page to apply impersonation context
			window.location.href = '/dashboard';
		} catch (error: unknown) {
			const message = error instanceof Error ? error.message : 'Failed to start impersonation';
			alert(message);
		} finally {
			isSubmitting = false;
		}
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
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Status</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Tier</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Badges</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Meetings</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Cost</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Last Meeting</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Actions</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
							{#each users as user (user.user_id)}
								<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-900/50 {user.deleted_at ? 'opacity-50' : ''}">
									<td class="px-6 py-4 whitespace-nowrap">
										<div class="text-sm font-medium text-neutral-900 dark:text-white">{user.email}</div>
										<div class="text-xs text-neutral-500 dark:text-neutral-400">{user.auth_provider}</div>
									</td>
									<td class="px-6 py-4 whitespace-nowrap">
										{#if user.deleted_at}
											<span class="inline-flex text-xs px-2 py-1 rounded-full bg-neutral-100 text-neutral-800 dark:bg-neutral-700 dark:text-neutral-300" title="Deleted at: {formatDate(user.deleted_at)}">
												Deleted
											</span>
										{:else if user.is_locked}
											<span class="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-error-100 text-error-800 dark:bg-error-900/20 dark:text-error-300" title={user.lock_reason || 'No reason provided'}>
												<Lock class="w-3 h-3" />
												Locked
											</span>
										{:else}
											<span class="inline-flex text-xs px-2 py-1 rounded-full bg-success-100 text-success-800 dark:bg-success-900/20 dark:text-success-300">
												Active
											</span>
										{/if}
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
										<div class="flex flex-wrap gap-1">
											{#if editingUserId === user.user_id}
												<label class="flex items-center gap-1 text-xs">
													<input
														type="checkbox"
														bind:checked={editForm.is_admin}
														class="rounded"
													/>
													Admin
												</label>
											{:else}
												{#if user.is_admin}
													<span class="inline-flex text-xs px-2 py-1 rounded-full bg-success-100 text-success-800 dark:bg-success-900/20 dark:text-success-300">
														Admin
													</span>
												{/if}
												{#if user.is_nonprofit}
													<span class="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-pink-100 text-pink-800 dark:bg-pink-900/20 dark:text-pink-300" title={user.nonprofit_org_name || 'Nonprofit'}>
														<Heart class="w-3 h-3" />
														Nonprofit
													</span>
												{/if}
												{#if !user.is_admin && !user.is_nonprofit}
													<span class="text-neutral-400">-</span>
												{/if}
											{/if}
										</div>
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
													return async ({ result, update }) => {
														isSubmitting = false;
														if (result.type === 'success') {
															editingUserId = null;
															editForm = {};
															await update();
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
											<div class="flex items-center gap-3">
												<button
													onclick={() => startEdit(user.user_id, user.subscription_tier, user.is_admin)}
													class="text-brand-600 dark:text-brand-400 hover:underline"
													disabled={!!user.deleted_at}
												>
													Edit
												</button>

												{#if !user.deleted_at}
													{#if user.is_locked}
														<form
															method="POST"
															action="?/unlockUser"
															use:enhance={() => {
																return async ({ result, update }) => {
																	if (result.type === 'success') {
																		await update();
																	} else if (result.type === 'failure') {
																		alert(result.data?.error || 'Failed to unlock user');
																	}
																};
															}}
														>
															<input type="hidden" name="userId" value={user.user_id} />
															<button type="submit" class="text-success-600 dark:text-success-400 hover:underline flex items-center gap-1">
																<Unlock class="w-3 h-3" />
																Unlock
															</button>
														</form>
													{:else}
														<button
															onclick={() => openLockModal(user)}
															class="text-warning-600 dark:text-warning-400 hover:underline flex items-center gap-1"
														>
															<Lock class="w-3 h-3" />
															Lock
														</button>
													{/if}
												{/if}

												<button
													onclick={() => openDeleteModal(user)}
													class="text-error-600 dark:text-error-400 hover:underline flex items-center gap-1"
													disabled={!!user.deleted_at}
												>
													<Trash2 class="w-3 h-3" />
													Delete
												</button>

												{#if !user.is_admin && !user.deleted_at}
													<button
														onclick={() => openImpersonateModal(user)}
														class="text-info-600 dark:text-info-400 hover:underline flex items-center gap-1"
													>
														<Eye class="w-3 h-3" />
														Impersonate
													</button>
												{/if}

												{#if !user.deleted_at}
													<button
														onclick={() => openPromoModal(user)}
														class="text-purple-600 dark:text-purple-400 hover:underline flex items-center gap-1"
													>
														<Gift class="w-3 h-3" />
														Promo
													</button>
													<button
														onclick={() => emailModalUser = { user_id: user.user_id, email: user.email }}
														class="text-teal-600 dark:text-teal-400 hover:underline flex items-center gap-1"
													>
														<Mail class="w-3 h-3" />
														Email
													</button>
												{/if}
											</div>
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

<!-- Lock User Modal -->
{#if lockModalUser}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
	<div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onclick={closeLockModal} role="presentation">
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-md w-full mx-4 p-6" onclick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" tabindex="-1">
			<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">Lock User Account</h2>
			<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
				Are you sure you want to lock <strong>{lockModalUser.email}</strong>? This will prevent them from signing in and revoke all active sessions.
			</p>
			<form
				method="POST"
				action="?/lockUser"
				use:enhance={() => {
					isSubmitting = true;
					return async ({ result, update }) => {
						isSubmitting = false;
						if (result.type === 'success') {
							closeLockModal();
							await update();
						} else if (result.type === 'failure') {
							alert(result.data?.error || 'Failed to lock user');
						}
					};
				}}
			>
				<input type="hidden" name="userId" value={lockModalUser.user_id} />
				<div class="mb-4">
					<label for="lockReason" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						Reason (optional)
					</label>
					<input
						type="text"
						id="lockReason"
						name="reason"
						bind:value={lockReason}
						placeholder="e.g., Suspicious activity, Payment issue"
						class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
					/>
				</div>
				<div class="flex justify-end gap-3">
					<Button variant="secondary" size="md" onclick={closeLockModal} disabled={isSubmitting}>
						{#snippet children()}Cancel{/snippet}
					</Button>
					<Button variant="danger" size="md" type="submit" disabled={isSubmitting}>
						{#snippet children()}{isSubmitting ? 'Locking...' : 'Lock User'}{/snippet}
					</Button>
				</div>
			</form>
		</div>
	</div>
{/if}

<!-- Delete User Modal -->
{#if deleteModalUser}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
	<div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onclick={closeDeleteModal} role="presentation">
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-md w-full mx-4 p-6" onclick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" tabindex="-1">
			<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">Delete User Account</h2>
			<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
				Are you sure you want to delete <strong>{deleteModalUser.email}</strong>? This action will revoke all active sessions.
			</p>
			<form
				method="POST"
				action="?/deleteUser"
				use:enhance={() => {
					isSubmitting = true;
					return async ({ result, update }) => {
						isSubmitting = false;
						if (result.type === 'success') {
							closeDeleteModal();
							await update();
						} else if (result.type === 'failure') {
							alert(result.data?.error || 'Failed to delete user');
						}
					};
				}}
			>
				<input type="hidden" name="userId" value={deleteModalUser.user_id} />
				<div class="mb-4">
					<label class="flex items-center gap-2 text-sm text-neutral-700 dark:text-neutral-300">
						<input
							type="checkbox"
							name="hard_delete"
							bind:checked={hardDelete}
							value="true"
							class="rounded border-neutral-300 dark:border-neutral-600"
						/>
						<span>Permanent deletion (cannot be undone)</span>
					</label>
					{#if hardDelete}
						<p class="mt-2 text-xs text-error-600 dark:text-error-400">
							Warning: This will permanently delete all user data including meetings, contributions, and settings.
						</p>
					{:else}
						<p class="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
							Soft delete: User will be marked as deleted but data is preserved.
						</p>
					{/if}
				</div>
				<div class="flex justify-end gap-3">
					<Button variant="secondary" size="md" onclick={closeDeleteModal} disabled={isSubmitting}>
						{#snippet children()}Cancel{/snippet}
					</Button>
					<Button variant="danger" size="md" type="submit" disabled={isSubmitting}>
						{#snippet children()}{isSubmitting ? 'Deleting...' : (hardDelete ? 'Permanently Delete' : 'Delete User')}{/snippet}
					</Button>
				</div>
			</form>
		</div>
	</div>
{/if}

<!-- Impersonate User Modal -->
{#if impersonateModalUser}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
	<div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onclick={closeImpersonateModal} role="presentation">
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-md w-full mx-4 p-6" onclick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" tabindex="-1">
			<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4 flex items-center gap-2">
				<Eye class="w-5 h-5 text-info-500" />
				View As User
			</h2>
			<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
				You will see the application as <strong>{impersonateModalUser.email}</strong>. This is logged for audit purposes.
			</p>

			<div class="space-y-4">
				<div>
					<label for="impersonateReason" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						Reason <span class="text-error-500">*</span>
					</label>
					<input
						type="text"
						id="impersonateReason"
						bind:value={impersonateReason}
						placeholder="e.g., Investigating user-reported bug"
						minlength="5"
						required
						class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-info-500"
					/>
					<p class="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
						Required for audit trail (min 5 characters)
					</p>
				</div>

				<div>
					<label for="impersonateDuration" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						Duration
					</label>
					<select
						id="impersonateDuration"
						bind:value={impersonateDuration}
						class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-info-500"
					>
						<option value={5}>5 minutes</option>
						<option value={15}>15 minutes</option>
						<option value={30}>30 minutes</option>
						<option value={60}>60 minutes</option>
					</select>
				</div>

				<div>
					<label class="flex items-center gap-2 text-sm text-neutral-700 dark:text-neutral-300">
						<input
							type="checkbox"
							bind:checked={impersonateWriteMode}
							class="rounded border-neutral-300 dark:border-neutral-600"
						/>
						<span>Enable write mode (allow mutations)</span>
					</label>
					{#if impersonateWriteMode}
						<p class="mt-2 text-xs text-warning-600 dark:text-warning-400">
							Warning: Write mode allows creating, editing, and deleting data as this user.
						</p>
					{:else}
						<p class="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
							Read-only mode: You can view the app but cannot make changes.
						</p>
					{/if}
				</div>
			</div>

			<div class="flex justify-end gap-3 mt-6">
				<Button variant="secondary" size="md" onclick={closeImpersonateModal} disabled={isSubmitting}>
					{#snippet children()}Cancel{/snippet}
				</Button>
				<Button
					variant="brand"
					size="md"
					onclick={handleImpersonate}
					disabled={isSubmitting || impersonateReason.trim().length < 5}
				>
					{#snippet children()}
						{#if isSubmitting}
							Starting...
						{:else}
							<Eye class="w-4 h-4" />
							View As User
						{/if}
					{/snippet}
				</Button>
			</div>
		</div>
	</div>
{/if}

<!-- Apply Promo Modal -->
{#if promoModalUser}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
	<div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onclick={closePromoModal} role="presentation">
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-md w-full mx-4 p-6" onclick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" tabindex="-1">
			<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4 flex items-center gap-2">
				<Gift class="w-5 h-5 text-purple-500" />
				Apply Promotion
			</h2>
			<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
				Apply a promo code to <strong>{promoModalUser.email}</strong>
			</p>

			{#if promoError}
				<div class="mb-4 p-3 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-md">
					<p class="text-sm text-error-800 dark:text-error-200">{promoError}</p>
				</div>
			{/if}

			<div class="mb-4">
				<label for="promoCode" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
					Promo Code <span class="text-error-500">*</span>
				</label>
				<input
					type="text"
					id="promoCode"
					bind:value={promoCode}
					placeholder="e.g., WELCOME10"
					class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-purple-500 uppercase"
					onkeydown={(e) => e.key === 'Enter' && handleApplyPromo()}
				/>
			</div>

			<div class="flex justify-end gap-3">
				<Button variant="secondary" size="md" onclick={closePromoModal} disabled={isSubmitting}>
					{#snippet children()}Cancel{/snippet}
				</Button>
				<Button
					variant="brand"
					size="md"
					onclick={handleApplyPromo}
					disabled={isSubmitting || !promoCode.trim()}
				>
					{#snippet children()}
						{#if isSubmitting}
							Applying...
						{:else}
							<Gift class="w-4 h-4" />
							Apply Promo
						{/if}
					{/snippet}
				</Button>
			</div>
		</div>
	</div>
{/if}

<!-- Send Email Modal -->
<SendEmailModal
	open={!!emailModalUser}
	userId={emailModalUser?.user_id ?? ''}
	userEmail={emailModalUser?.email ?? ''}
	onClose={() => emailModalUser = null}
/>
