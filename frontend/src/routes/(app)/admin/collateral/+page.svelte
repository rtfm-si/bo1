<script lang="ts">
	/**
	 * Admin Collateral Bank Page
	 *
	 * Manage marketing assets (images, animations, concepts, templates)
	 * for AI content generation. Features:
	 * - Upload with drag-drop
	 * - Tag-based organization
	 * - Asset type filtering
	 * - Edit/delete operations
	 */
	import { onMount } from 'svelte';
	import { Button } from '$lib/components/ui';
	import {
		RefreshCw,
		Upload,
		Image,
		Film,
		Lightbulb,
		FileText,
		Search,
		X,
		Trash2,
		Edit,
		Copy,
		Check
	} from 'lucide-svelte';
	import { apiClient } from '$lib/api/client';
	import type { MarketingAsset, MarketingAssetType } from '$lib/api/types';

	// State
	let assets = $state<MarketingAsset[]>([]);
	let total = $state(0);
	let remaining = $state(0);
	let isLoading = $state(true);
	let error = $state<string | null>(null);

	// Filters
	let filterType = $state<MarketingAssetType | ''>('');
	let searchQuery = $state('');

	// Upload state
	let isUploading = $state(false);
	let uploadError = $state<string | null>(null);
	let showUploadModal = $state(false);
	let dragOver = $state(false);

	// Upload form
	let uploadFile = $state<File | null>(null);
	let uploadTitle = $state('');
	let uploadType = $state<MarketingAssetType>('image');
	let uploadDescription = $state('');
	let uploadTags = $state('');

	// Edit state
	let editingAsset = $state<MarketingAsset | null>(null);
	let editTitle = $state('');
	let editDescription = $state('');
	let editTags = $state('');
	let isSaving = $state(false);

	// Copy state
	let copiedId = $state<number | null>(null);

	// Load assets
	async function loadAssets() {
		isLoading = true;
		error = null;
		try {
			const response = await apiClient.listMarketingAssets({
				asset_type: filterType || undefined,
				search: searchQuery || undefined,
				limit: 100
			});
			assets = response.assets;
			total = response.total;
			remaining = response.remaining;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load assets';
		} finally {
			isLoading = false;
		}
	}

	// Handle file drop
	function handleDrop(e: DragEvent) {
		e.preventDefault();
		dragOver = false;
		const file = e.dataTransfer?.files?.[0];
		if (file) {
			uploadFile = file;
			uploadTitle = file.name.replace(/\.[^/.]+$/, '');
			showUploadModal = true;
		}
	}

	// Handle file select
	function handleFileSelect(e: Event) {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0];
		if (file) {
			uploadFile = file;
			uploadTitle = file.name.replace(/\.[^/.]+$/, '');
		}
	}

	// Upload asset
	async function handleUpload() {
		if (!uploadFile || !uploadTitle) return;

		isUploading = true;
		uploadError = null;
		try {
			const tags = uploadTags
				.split(',')
				.map((t) => t.trim())
				.filter(Boolean);
			await apiClient.uploadMarketingAsset(
				uploadFile,
				uploadTitle,
				uploadType,
				uploadDescription || undefined,
				tags.length > 0 ? tags : undefined
			);
			showUploadModal = false;
			resetUploadForm();
			await loadAssets();
		} catch (err) {
			uploadError = err instanceof Error ? err.message : 'Upload failed';
		} finally {
			isUploading = false;
		}
	}

	function resetUploadForm() {
		uploadFile = null;
		uploadTitle = '';
		uploadType = 'image';
		uploadDescription = '';
		uploadTags = '';
	}

	// Delete asset
	async function handleDelete(asset: MarketingAsset) {
		if (!confirm(`Delete "${asset.title}"? This cannot be undone.`)) return;

		try {
			await apiClient.deleteMarketingAsset(asset.id);
			await loadAssets();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Delete failed';
		}
	}

	// Edit asset
	function startEdit(asset: MarketingAsset) {
		editingAsset = asset;
		editTitle = asset.title;
		editDescription = asset.description || '';
		editTags = asset.tags.join(', ');
	}

	async function saveEdit() {
		if (!editingAsset) return;

		isSaving = true;
		try {
			const tags = editTags
				.split(',')
				.map((t) => t.trim())
				.filter(Boolean);
			await apiClient.updateMarketingAsset(editingAsset.id, {
				title: editTitle,
				description: editDescription || undefined,
				tags
			});
			editingAsset = null;
			await loadAssets();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Update failed';
		} finally {
			isSaving = false;
		}
	}

	// Copy CDN URL
	function copyUrl(asset: MarketingAsset) {
		navigator.clipboard.writeText(asset.cdn_url);
		copiedId = asset.id;
		setTimeout(() => {
			copiedId = null;
		}, 2000);
	}

	// Format file size
	function formatSize(bytes: number): string {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	// Get type icon
	function getTypeIcon(type: MarketingAssetType) {
		switch (type) {
			case 'image':
				return Image;
			case 'animation':
				return Film;
			case 'concept':
				return Lightbulb;
			case 'template':
				return FileText;
			default:
				return Image;
		}
	}

	// Search debounce
	let searchTimeout: ReturnType<typeof setTimeout>;
	function handleSearch(e: Event) {
		const value = (e.target as HTMLInputElement).value;
		searchQuery = value;
		clearTimeout(searchTimeout);
		searchTimeout = setTimeout(loadAssets, 300);
	}

	onMount(() => {
		loadAssets();
	});
</script>

<svelte:head>
	<title>Collateral Bank - Admin - Board of One</title>
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
						aria-label="Back to admin dashboard"
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
							Marketing Collateral Bank
						</h1>
						<p class="text-sm text-neutral-500 dark:text-neutral-400">
							{total} assets
							{#if remaining >= 0}
								<span class="text-neutral-400">({remaining} slots remaining)</span>
							{/if}
						</p>
					</div>
				</div>
				<div class="flex items-center gap-2">
					<Button
						variant="secondary"
						size="sm"
						onclick={loadAssets}
						disabled={isLoading}
					>
						{#snippet children()}
							<RefreshCw class="w-4 h-4 {isLoading ? 'animate-spin' : ''}" />
							Refresh
						{/snippet}
					</Button>
					<Button
						variant="brand"
						size="sm"
						onclick={() => (showUploadModal = true)}
						disabled={remaining === 0}
					>
						{#snippet children()}
							<Upload class="w-4 h-4" />
							Upload
						{/snippet}
					</Button>
				</div>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Error State -->
		{#if error}
			<div
				class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-4 mb-6"
			>
				<p class="text-error-800 dark:text-error-200">{error}</p>
				<Button variant="secondary" size="sm" onclick={loadAssets} class="mt-2">
					{#snippet children()}Retry{/snippet}
				</Button>
			</div>
		{/if}

		<!-- Filters -->
		<div class="flex flex-col sm:flex-row gap-4 mb-6">
			<!-- Search -->
			<div class="flex-1 relative">
				<Search
					class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400"
				/>
				<input
					type="text"
					placeholder="Search assets..."
					class="w-full pl-10 pr-4 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder-neutral-400"
					oninput={handleSearch}
					value={searchQuery}
				/>
			</div>

			<!-- Type Filter -->
			<select
				class="px-4 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
				bind:value={filterType}
				onchange={loadAssets}
			>
				<option value="">All Types</option>
				<option value="image">Images</option>
				<option value="animation">Animations</option>
				<option value="concept">Concepts</option>
				<option value="template">Templates</option>
			</select>
		</div>

		<!-- Drop Zone -->
		<div
			class="border-2 border-dashed rounded-lg p-8 mb-6 text-center transition-colors duration-200 {dragOver
				? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20'
				: 'border-neutral-300 dark:border-neutral-600'}"
			ondragover={(e) => {
				e.preventDefault();
				dragOver = true;
			}}
			ondragleave={() => (dragOver = false)}
			ondrop={handleDrop}
			role="region"
			aria-label="Drop zone for file uploads"
		>
			<Upload class="w-8 h-8 mx-auto text-neutral-400 mb-2" />
			<p class="text-neutral-600 dark:text-neutral-400">
				Drag and drop files here, or
				<button
					type="button"
					class="text-brand-600 dark:text-brand-400 hover:underline"
					onclick={() => (showUploadModal = true)}>browse</button
				>
			</p>
			<p class="text-sm text-neutral-400 mt-1">
				PNG, JPG, GIF, WebP, SVG, MP4, WebM (max 10MB images, 50MB video)
			</p>
		</div>

		<!-- Loading State -->
		{#if isLoading}
			<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
				{#each [1, 2, 3, 4, 5, 6, 7, 8] as _}
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden animate-pulse"
					>
						<div class="aspect-video bg-neutral-200 dark:bg-neutral-700"></div>
						<div class="p-3">
							<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-3/4 mb-2"></div>
							<div class="h-3 bg-neutral-200 dark:bg-neutral-700 rounded w-1/2"></div>
						</div>
					</div>
				{/each}
			</div>
		{:else if assets.length === 0}
			<!-- Empty State -->
			<div
				class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-12 text-center"
			>
				<Image class="w-12 h-12 mx-auto text-neutral-400 mb-4" />
				<h3 class="text-lg font-medium text-neutral-900 dark:text-white mb-2">
					No assets yet
				</h3>
				<p class="text-neutral-600 dark:text-neutral-400 mb-4">
					Upload images, animations, and other marketing collateral to use in AI-generated content.
				</p>
				<Button variant="brand" size="sm" onclick={() => (showUploadModal = true)}>
					{#snippet children()}
						<Upload class="w-4 h-4" />
						Upload First Asset
					{/snippet}
				</Button>
			</div>
		{:else}
			<!-- Asset Grid -->
			<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
				{#each assets as asset}
					{@const TypeIcon = getTypeIcon(asset.asset_type as MarketingAssetType)}
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden group"
					>
						<!-- Preview -->
						<div class="aspect-video bg-neutral-100 dark:bg-neutral-900 relative">
							{#if asset.mime_type.startsWith('image/')}
								<img
									src={asset.cdn_url}
									alt={asset.title}
									class="w-full h-full object-cover"
								/>
							{:else if asset.mime_type.startsWith('video/')}
								<video
									src={asset.cdn_url}
									class="w-full h-full object-cover"
									muted
								></video>
							{:else}
								<div class="flex items-center justify-center h-full">
									<TypeIcon class="w-12 h-12 text-neutral-400" />
								</div>
							{/if}

							<!-- Actions Overlay -->
							<div
								class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center gap-2"
							>
								<button
									type="button"
									class="p-2 bg-white rounded-full hover:bg-neutral-100"
									onclick={() => copyUrl(asset)}
									title="Copy CDN URL"
								>
									{#if copiedId === asset.id}
										<Check class="w-4 h-4 text-success-600" />
									{:else}
										<Copy class="w-4 h-4 text-neutral-700" />
									{/if}
								</button>
								<button
									type="button"
									class="p-2 bg-white rounded-full hover:bg-neutral-100"
									onclick={() => startEdit(asset)}
									title="Edit"
								>
									<Edit class="w-4 h-4 text-neutral-700" />
								</button>
								<button
									type="button"
									class="p-2 bg-white rounded-full hover:bg-error-100"
									onclick={() => handleDelete(asset)}
									title="Delete"
								>
									<Trash2 class="w-4 h-4 text-error-600" />
								</button>
							</div>
						</div>

						<!-- Info -->
						<div class="p-3">
							<div class="flex items-center gap-2 mb-1">
								<TypeIcon class="w-4 h-4 text-neutral-400 flex-shrink-0" />
								<h3
									class="font-medium text-neutral-900 dark:text-white truncate"
									title={asset.title}
								>
									{asset.title}
								</h3>
							</div>
							<p class="text-xs text-neutral-500 dark:text-neutral-400">
								{formatSize(asset.file_size)}
							</p>
							{#if asset.tags.length > 0}
								<div class="flex flex-wrap gap-1 mt-2">
									{#each asset.tags.slice(0, 3) as tag}
										<span
											class="px-1.5 py-0.5 text-xs bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300 rounded"
										>
											{tag}
										</span>
									{/each}
									{#if asset.tags.length > 3}
										<span class="text-xs text-neutral-400">
											+{asset.tags.length - 3}
										</span>
									{/if}
								</div>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</main>
</div>

<!-- Upload Modal -->
{#if showUploadModal}
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
		onclick={() => (showUploadModal = false)}
		onkeydown={(e) => e.key === 'Escape' && (showUploadModal = false)}
		role="dialog"
		aria-modal="true"
		aria-labelledby="upload-modal-title"
		tabindex="-1"
	>
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<div
			class="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-md w-full mx-4 p-6"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="document"
		>
			<div class="flex items-center justify-between mb-4">
				<h2 id="upload-modal-title" class="text-lg font-semibold text-neutral-900 dark:text-white">
					Upload Asset
				</h2>
				<button
					type="button"
					class="p-1 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded"
					onclick={() => (showUploadModal = false)}
				>
					<X class="w-5 h-5 text-neutral-500" />
				</button>
			</div>

			{#if uploadError}
				<div class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded p-3 mb-4">
					<p class="text-sm text-error-800 dark:text-error-200">{uploadError}</p>
				</div>
			{/if}

			<form
				onsubmit={(e) => {
					e.preventDefault();
					handleUpload();
				}}
			>
				<!-- File Input -->
				<div class="mb-4">
					<label for="upload-file" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						File
					</label>
					{#if uploadFile}
						<div class="flex items-center gap-2 p-2 bg-neutral-100 dark:bg-neutral-700 rounded">
							<span class="text-sm text-neutral-900 dark:text-white truncate flex-1">
								{uploadFile.name}
							</span>
							<button
								type="button"
								class="text-neutral-400 hover:text-neutral-600"
								onclick={() => (uploadFile = null)}
							>
								<X class="w-4 h-4" />
							</button>
						</div>
					{:else}
						<input
							id="upload-file"
							type="file"
							accept="image/png,image/jpeg,image/gif,image/webp,image/svg+xml,video/mp4,video/webm"
							class="w-full text-sm text-neutral-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100"
							onchange={handleFileSelect}
						/>
					{/if}
				</div>

				<!-- Title -->
				<div class="mb-4">
					<label for="upload-title" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						Title
					</label>
					<input
						id="upload-title"
						type="text"
						class="w-full px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
						bind:value={uploadTitle}
						required
					/>
				</div>

				<!-- Type -->
				<div class="mb-4">
					<label for="upload-type" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						Type
					</label>
					<select
						id="upload-type"
						class="w-full px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
						bind:value={uploadType}
					>
						<option value="image">Image</option>
						<option value="animation">Animation</option>
						<option value="concept">Concept</option>
						<option value="template">Template</option>
					</select>
				</div>

				<!-- Description -->
				<div class="mb-4">
					<label for="upload-description" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						Description (optional)
					</label>
					<textarea
						id="upload-description"
						class="w-full px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
						rows="2"
						bind:value={uploadDescription}
					></textarea>
				</div>

				<!-- Tags -->
				<div class="mb-6">
					<label for="upload-tags" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						Tags (comma-separated)
					</label>
					<input
						id="upload-tags"
						type="text"
						placeholder="pricing, saas, hero"
						class="w-full px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
						bind:value={uploadTags}
					/>
				</div>

				<!-- Actions -->
				<div class="flex justify-end gap-2">
					<Button variant="secondary" size="sm" onclick={() => (showUploadModal = false)}>
						{#snippet children()}Cancel{/snippet}
					</Button>
					<Button
						variant="brand"
						size="sm"
						type="submit"
						disabled={!uploadFile || !uploadTitle || isUploading}
					>
						{#snippet children()}
							{#if isUploading}
								<RefreshCw class="w-4 h-4 animate-spin" />
								Uploading...
							{:else}
								<Upload class="w-4 h-4" />
								Upload
							{/if}
						{/snippet}
					</Button>
				</div>
			</form>
		</div>
	</div>
{/if}

<!-- Edit Modal -->
{#if editingAsset}
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
		onclick={() => (editingAsset = null)}
		onkeydown={(e) => e.key === 'Escape' && (editingAsset = null)}
		role="dialog"
		aria-modal="true"
		aria-labelledby="edit-modal-title"
		tabindex="-1"
	>
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<div
			class="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-md w-full mx-4 p-6"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="document"
		>
			<div class="flex items-center justify-between mb-4">
				<h2 id="edit-modal-title" class="text-lg font-semibold text-neutral-900 dark:text-white">
					Edit Asset
				</h2>
				<button
					type="button"
					class="p-1 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded"
					onclick={() => (editingAsset = null)}
				>
					<X class="w-5 h-5 text-neutral-500" />
				</button>
			</div>

			<form
				onsubmit={(e) => {
					e.preventDefault();
					saveEdit();
				}}
			>
				<!-- Title -->
				<div class="mb-4">
					<label for="edit-title" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						Title
					</label>
					<input
						id="edit-title"
						type="text"
						class="w-full px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
						bind:value={editTitle}
						required
					/>
				</div>

				<!-- Description -->
				<div class="mb-4">
					<label for="edit-description" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						Description
					</label>
					<textarea
						id="edit-description"
						class="w-full px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
						rows="2"
						bind:value={editDescription}
					></textarea>
				</div>

				<!-- Tags -->
				<div class="mb-6">
					<label for="edit-tags" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						Tags (comma-separated)
					</label>
					<input
						id="edit-tags"
						type="text"
						class="w-full px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
						bind:value={editTags}
					/>
				</div>

				<!-- Actions -->
				<div class="flex justify-end gap-2">
					<Button variant="secondary" size="sm" onclick={() => (editingAsset = null)}>
						{#snippet children()}Cancel{/snippet}
					</Button>
					<Button variant="brand" size="sm" type="submit" disabled={!editTitle || isSaving}>
						{#snippet children()}
							{#if isSaving}
								<RefreshCw class="w-4 h-4 animate-spin" />
								Saving...
							{:else}
								Save
							{/if}
						{/snippet}
					</Button>
				</div>
			</form>
		</div>
	</div>
{/if}
