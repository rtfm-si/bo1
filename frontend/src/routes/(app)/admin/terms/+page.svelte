<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/stores';
	import { Button, Modal, Alert, Badge } from '$lib/components/ui';
	import { apiClient, type TermsVersionItem } from '$lib/api/client';
	import {
		ChevronLeft,
		ChevronRight,
		FileText,
		Clock,
		Plus,
		Edit,
		Send,
		Eye,
		Users
	} from 'lucide-svelte';

	let { data } = $props();

	let versions = $state<TermsVersionItem[]>([]);
	let total = $state(0);
	let limit = $state(50);
	let offset = $state(0);
	let hasMore = $state(false);

	// Modal states
	let showCreateModal = $state(false);
	let showEditModal = $state(false);
	let showPreviewModal = $state(false);
	let showPublishModal = $state(false);

	// Form state
	let newVersion = $state('');
	let newContent = $state('');
	let editingVersion = $state<TermsVersionItem | null>(null);
	let editContent = $state('');
	let previewVersion = $state<TermsVersionItem | null>(null);
	let publishingVersion = $state<TermsVersionItem | null>(null);

	// Loading/error states
	let isLoading = $state(false);
	let error = $state('');

	$effect(() => {
		versions = data.versions || [];
		total = data.total || 0;
		limit = data.limit || 50;
		offset = data.offset || 0;
		hasMore = data.hasMore || false;
	});

	function nextPage() {
		if (hasMore) {
			const url = new URL($page.url);
			url.searchParams.set('offset', (offset + limit).toString());
			goto(url.toString());
		}
	}

	function prevPage() {
		if (offset > 0) {
			const url = new URL($page.url);
			url.searchParams.set('offset', Math.max(0, offset - limit).toString());
			goto(url.toString());
		}
	}

	function formatDate(dateString: string | null): string {
		if (!dateString) return '-';
		const date = new Date(dateString);
		return date.toLocaleString();
	}

	function getStatusBadge(version: TermsVersionItem): {
		variant: 'success' | 'neutral' | 'info';
		label: string;
	} {
		if (version.is_active) {
			return { variant: 'success', label: 'Active' };
		}
		if (version.published_at) {
			return { variant: 'neutral', label: 'Archived' };
		}
		return { variant: 'info', label: 'Draft' };
	}

	async function handleCreate() {
		if (!newVersion.trim() || !newContent.trim()) {
			error = 'Version and content are required';
			return;
		}

		isLoading = true;
		error = '';

		try {
			await apiClient.createTermsVersion({
				version: newVersion.trim(),
				content: newContent.trim()
			});
			showCreateModal = false;
			newVersion = '';
			newContent = '';
			await invalidateAll();
		} catch (err: unknown) {
			const errMsg = err instanceof Error ? err.message : String(err);
			error = errMsg.includes('409') ? `Version "${newVersion}" already exists` : errMsg;
		} finally {
			isLoading = false;
		}
	}

	function openEditModal(version: TermsVersionItem) {
		if (version.is_active) {
			error = 'Cannot edit active version';
			return;
		}
		editingVersion = version;
		editContent = version.content;
		showEditModal = true;
	}

	async function handleUpdate() {
		if (!editingVersion || !editContent.trim()) {
			error = 'Content is required';
			return;
		}

		isLoading = true;
		error = '';

		try {
			await apiClient.updateTermsVersion(editingVersion.id, {
				content: editContent.trim()
			});
			showEditModal = false;
			editingVersion = null;
			editContent = '';
			await invalidateAll();
		} catch (err: unknown) {
			error = err instanceof Error ? err.message : String(err);
		} finally {
			isLoading = false;
		}
	}

	function openPreviewModal(version: TermsVersionItem) {
		previewVersion = version;
		showPreviewModal = true;
	}

	function openPublishModal(version: TermsVersionItem) {
		publishingVersion = version;
		showPublishModal = true;
	}

	async function handlePublish() {
		if (!publishingVersion) return;

		isLoading = true;
		error = '';

		try {
			await apiClient.publishTermsVersion(publishingVersion.id);
			showPublishModal = false;
			publishingVersion = null;
			await invalidateAll();
		} catch (err: unknown) {
			error = err instanceof Error ? err.message : String(err);
		} finally {
			isLoading = false;
		}
	}

	const currentPage = $derived(Math.floor(offset / limit) + 1);
	const totalPages = $derived(Math.ceil(total / limit));
</script>

<svelte:head>
	<title>T&C Versions - Admin</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Header -->
	<header
		class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700"
	>
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<a
						href="/admin"
						class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors duration-200"
						aria-label="Back to admin"
					>
						<svg
							class="w-5 h-5 text-neutral-600 dark:text-neutral-400"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M10 19l-7-7m0 0l7-7m-7 7h18"
							/>
						</svg>
					</a>
					<div>
						<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">
							Terms & Conditions
						</h1>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">
							Manage T&C versions and view consent audit
						</p>
					</div>
				</div>
				<Button variant="brand" onclick={() => (showCreateModal = true)}>
					{#snippet children()}
						<Plus class="w-4 h-4" />
						New Version
					{/snippet}
				</Button>
			</div>
		</div>
	</header>

	<!-- Tabs -->
	<div class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
			<nav class="flex gap-4">
				<a
					href="/admin/terms"
					class="py-3 px-1 border-b-2 border-brand-600 text-brand-600 dark:text-brand-400 font-medium text-sm"
					aria-current="page"
				>
					Versions
				</a>
				<a
					href="/admin/terms/consents"
					class="py-3 px-1 border-b-2 border-transparent text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white font-medium text-sm"
				>
					Consent Audit
				</a>
			</nav>
		</div>
	</div>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		{#if error}
			<Alert variant="error" class="mb-6">
				{error}
			</Alert>
		{/if}

		<!-- Stats -->
		<div class="mb-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
			<div
				class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700"
			>
				<div class="flex items-center gap-3">
					<div class="p-2 bg-brand-100 dark:bg-brand-900/20 rounded-lg">
						<FileText class="w-5 h-5 text-brand-600 dark:text-brand-400" />
					</div>
					<div>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Total Versions</p>
						<p class="text-2xl font-semibold text-neutral-900 dark:text-white">{total}</p>
					</div>
				</div>
			</div>
			<div
				class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700"
			>
				<div class="flex items-center gap-3">
					<div class="p-2 bg-success-100 dark:bg-success-900/20 rounded-lg">
						<Send class="w-5 h-5 text-success-600 dark:text-success-400" />
					</div>
					<div>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Active Version</p>
						<p class="text-lg font-medium text-neutral-900 dark:text-white">
							{versions.find((v) => v.is_active)?.version || 'None'}
						</p>
					</div>
				</div>
			</div>
			<a
				href="/admin/terms/consents"
				class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
			>
				<div class="flex items-center gap-3">
					<div class="p-2 bg-info-100 dark:bg-info-900/20 rounded-lg">
						<Users class="w-5 h-5 text-info-600 dark:text-info-400" />
					</div>
					<div>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Consent Audit</p>
						<p class="text-lg font-medium text-neutral-900 dark:text-white">View Records →</p>
					</div>
				</div>
			</a>
		</div>

		<!-- Table -->
		{#if versions.length === 0}
			<div
				class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-12 text-center"
			>
				<FileText class="w-12 h-12 text-neutral-400 mx-auto mb-3" />
				<p class="text-neutral-600 dark:text-neutral-400">No T&C versions found</p>
				<p class="text-sm text-neutral-500 dark:text-neutral-500 mt-1">
					Create your first version to get started
				</p>
				<Button variant="brand" class="mt-4" onclick={() => (showCreateModal = true)}>
					{#snippet children()}
						<Plus class="w-4 h-4" />
						Create Version
					{/snippet}
				</Button>
			</div>
		{:else}
			<div
				class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden"
			>
				<div class="overflow-x-auto">
					<table class="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
						<thead class="bg-neutral-50 dark:bg-neutral-900">
							<tr>
								<th
									class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider"
								>
									Version
								</th>
								<th
									class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider"
								>
									Status
								</th>
								<th
									class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider"
								>
									Published
								</th>
								<th
									class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider"
								>
									Created
								</th>
								<th
									class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider"
								>
									Actions
								</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
							{#each versions as version (version.id)}
								{@const status = getStatusBadge(version)}
								<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
									<td class="px-6 py-4 whitespace-nowrap">
										<div class="flex items-center gap-2">
											<FileText class="w-4 h-4 text-neutral-400" />
											<span class="text-sm font-medium text-neutral-900 dark:text-white">
												v{version.version}
											</span>
										</div>
									</td>
									<td class="px-6 py-4 whitespace-nowrap">
										<Badge variant={status.variant}>
											{status.label}
										</Badge>
									</td>
									<td class="px-6 py-4 whitespace-nowrap">
										<div
											class="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400"
										>
											<Clock class="w-4 h-4 text-neutral-400" />
											{formatDate(version.published_at)}
										</div>
									</td>
									<td class="px-6 py-4 whitespace-nowrap">
										<div
											class="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400"
										>
											{formatDate(version.created_at)}
										</div>
									</td>
									<td class="px-6 py-4 whitespace-nowrap text-right">
										<div class="flex items-center justify-end gap-2">
											<Button
												variant="ghost"
												size="sm"
												onclick={() => openPreviewModal(version)}
												title="Preview"
											>
												{#snippet children()}
													<Eye class="w-4 h-4" />
												{/snippet}
											</Button>
											{#if !version.is_active && !version.published_at}
												<Button
													variant="ghost"
													size="sm"
													onclick={() => openEditModal(version)}
													title="Edit"
												>
													{#snippet children()}
														<Edit class="w-4 h-4" />
													{/snippet}
												</Button>
												<Button
													variant="brand"
													size="sm"
													onclick={() => openPublishModal(version)}
													title="Publish"
												>
													{#snippet children()}
														<Send class="w-4 h-4" />
														Publish
													{/snippet}
												</Button>
											{/if}
										</div>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>

				<!-- Pagination -->
				{#if total > limit}
					<div
						class="bg-neutral-50 dark:bg-neutral-900 px-6 py-3 flex items-center justify-between border-t border-neutral-200 dark:border-neutral-700"
					>
						<div class="text-sm text-neutral-700 dark:text-neutral-300">
							Showing {offset + 1} to {Math.min(offset + limit, total)} of {total} versions
						</div>
						<div class="flex gap-2">
							<Button variant="secondary" size="sm" disabled={offset === 0} onclick={prevPage}>
								{#snippet children()}
									<ChevronLeft class="w-4 h-4" />
									Previous
								{/snippet}
							</Button>
							<Button variant="secondary" size="sm" disabled={!hasMore} onclick={nextPage}>
								{#snippet children()}
									Next
									<ChevronRight class="w-4 h-4" />
								{/snippet}
							</Button>
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</main>
</div>

<!-- Create Modal -->
<Modal bind:open={showCreateModal} title="Create New Version">
	<div class="space-y-4">
		<div>
			<label for="version" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300"
				>Version</label
			>
			<input
				id="version"
				type="text"
				bind:value={newVersion}
				placeholder="e.g., 1.1"
				class="mt-1 block w-full rounded-md border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-3 py-2 text-sm text-neutral-900 dark:text-white placeholder-neutral-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
			/>
		</div>
		<div>
			<label for="content" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300"
				>Content (Markdown)</label
			>
			<textarea
				id="content"
				bind:value={newContent}
				rows="12"
				placeholder="Enter T&C content in Markdown..."
				class="mt-1 block w-full rounded-md border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-3 py-2 text-sm text-neutral-900 dark:text-white placeholder-neutral-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 font-mono"
			></textarea>
		</div>
	</div>
	{#snippet footer()}
		<div class="flex justify-end gap-3">
			<Button variant="secondary" onclick={() => (showCreateModal = false)} disabled={isLoading}>
				{#snippet children()}Cancel{/snippet}
			</Button>
			<Button variant="brand" onclick={handleCreate} loading={isLoading}>
				{#snippet children()}Create Draft{/snippet}
			</Button>
		</div>
	{/snippet}
</Modal>

<!-- Edit Modal -->
<Modal bind:open={showEditModal} title="Edit Draft Version">
	{#if editingVersion}
		<div class="space-y-4">
			<div class="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400">
				<FileText class="w-4 h-4" />
				Editing version <strong>v{editingVersion.version}</strong>
			</div>
			<div>
				<label
					for="editContent"
					class="block text-sm font-medium text-neutral-700 dark:text-neutral-300"
					>Content (Markdown)</label
				>
				<textarea
					id="editContent"
					bind:value={editContent}
					rows="12"
					class="mt-1 block w-full rounded-md border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-3 py-2 text-sm text-neutral-900 dark:text-white placeholder-neutral-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 font-mono"
				></textarea>
			</div>
		</div>
	{/if}
	{#snippet footer()}
		<div class="flex justify-end gap-3">
			<Button variant="secondary" onclick={() => (showEditModal = false)} disabled={isLoading}>
				{#snippet children()}Cancel{/snippet}
			</Button>
			<Button variant="brand" onclick={handleUpdate} loading={isLoading}>
				{#snippet children()}Save Changes{/snippet}
			</Button>
		</div>
	{/snippet}
</Modal>

<!-- Preview Modal -->
<Modal bind:open={showPreviewModal} title="Preview Version">
	{#if previewVersion}
		<div class="space-y-4">
			<div
				class="flex items-center justify-between p-3 bg-neutral-50 dark:bg-neutral-900 rounded-lg"
			>
				<div class="flex items-center gap-2">
					<FileText class="w-4 h-4 text-neutral-400" />
					<span class="font-medium">v{previewVersion.version}</span>
				</div>
				<Badge variant={getStatusBadge(previewVersion).variant}>
					{getStatusBadge(previewVersion).label}
				</Badge>
			</div>
			<div
				class="prose prose-sm dark:prose-invert max-w-none max-h-96 overflow-y-auto p-4 bg-neutral-50 dark:bg-neutral-900 rounded-lg"
			>
				<!-- eslint-disable-next-line svelte/no-at-html-tags -->
				{@html previewVersion.content
					.split('\n')
					.map((line) => {
						if (line.startsWith('# ')) return `<h1>${line.slice(2)}</h1>`;
						if (line.startsWith('## ')) return `<h2>${line.slice(3)}</h2>`;
						if (line.startsWith('### ')) return `<h3>${line.slice(4)}</h3>`;
						if (line.startsWith('- ')) return `<li>${line.slice(2)}</li>`;
						if (line.trim() === '') return '<br/>';
						return `<p>${line}</p>`;
					})
					.join('')}
			</div>
		</div>
	{/if}
	{#snippet footer()}
		<Button variant="secondary" onclick={() => (showPreviewModal = false)}>
			{#snippet children()}Close{/snippet}
		</Button>
	{/snippet}
</Modal>

<!-- Publish Confirmation Modal -->
<Modal bind:open={showPublishModal} title="Publish Version">
	{#if publishingVersion}
		<div class="space-y-4">
			<Alert variant="warning">
				Publishing this version will make it the active T&C. The previous active version will be
				archived. Users who haven't consented to this version will be prompted to accept.
			</Alert>
			<div
				class="flex items-center gap-3 p-4 bg-neutral-50 dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-700"
			>
				<FileText class="w-6 h-6 text-brand-600" />
				<div>
					<p class="font-medium text-neutral-900 dark:text-white">
						Version {publishingVersion.version}
					</p>
					<p class="text-sm text-neutral-600 dark:text-neutral-400">
						Created {formatDate(publishingVersion.created_at)}
					</p>
				</div>
			</div>
		</div>
	{/if}
	{#snippet footer()}
		<div class="flex justify-end gap-3">
			<Button variant="secondary" onclick={() => (showPublishModal = false)} disabled={isLoading}>
				{#snippet children()}Cancel{/snippet}
			</Button>
			<Button variant="brand" onclick={handlePublish} loading={isLoading}>
				{#snippet children()}
					<Send class="w-4 h-4" />
					Publish Now
				{/snippet}
			</Button>
		</div>
	{/snippet}
</Modal>
