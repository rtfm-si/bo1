<script lang="ts">
	/**
	 * ArticleDetailModal - Full article view with regeneration capability
	 * Shows article content, SEO metadata, and regeneration options
	 */
	import Modal from '$lib/components/ui/Modal.svelte';
	import BoButton from '$lib/components/ui/BoButton.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import { toast } from '$lib/stores/toast';
	import { apiClient } from '$lib/api/client';
	import type { SeoBlogArticle } from '$lib/api/types';
	import DOMPurify from 'isomorphic-dompurify';
	import { Copy, FileText, RefreshCw, Pencil, X, Save } from 'lucide-svelte';

	interface Props {
		article: SeoBlogArticle;
		open: boolean;
		defaultTone?: string | null;
		onclose: () => void;
		onupdate: (article: SeoBlogArticle) => void;
	}

	let { article, open = $bindable(false), defaultTone = null, onclose, onupdate }: Props = $props();

	// View state
	let activeTab = $state<'content' | 'seo'>('content');

	// Edit mode state
	let editMode = $state(false);
	let editContent = $state('');
	let saving = $state(false);
	let hasUnsavedChanges = $state(false);

	// Regenerate panel state (visible by default for revision-first UX)
	let regenerating = $state(false);
	let regenerateError = $state<string | null>(null);

	// Regeneration options
	let changes = $state<string[]>(['', '', '']);
	let selectedTone = $state<string>('');

	// Tone options
	const toneOptions = [
		{ value: 'Professional', label: 'Professional' },
		{ value: 'Friendly', label: 'Friendly' },
		{ value: 'Technical', label: 'Technical' },
		{ value: 'Persuasive', label: 'Persuasive' },
		{ value: 'Conversational', label: 'Conversational' }
	];

	// Initialize state when modal opens
	$effect(() => {
		if (open) {
			selectedTone = defaultTone || 'Professional';
			changes = ['', '', ''];
			regenerateError = null;
			editMode = false;
			editContent = '';
			hasUnsavedChanges = false;
		}
	});

	// Track unsaved changes in edit mode
	$effect(() => {
		if (editMode && editContent !== article.content) {
			hasUnsavedChanges = true;
		}
	});

	// Simple markdown to HTML rendering
	function renderMarkdown(md: string): string {
		const html = md
			.replace(/^### (.*$)/gm, '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>')
			.replace(/^## (.*$)/gm, '<h2 class="text-xl font-semibold mt-6 mb-3">$1</h2>')
			.replace(/^# (.*$)/gm, '<h1 class="text-2xl font-bold mt-8 mb-4">$1</h1>')
			.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
			.replace(/\*(.*?)\*/g, '<em>$1</em>')
			.replace(/`(.*?)`/g, '<code class="bg-neutral-100 dark:bg-neutral-800 px-1 rounded text-sm">$1</code>')
			.replace(/\n\n/g, '</p><p class="mb-4">')
			.replace(/\n/g, '<br>');
		return DOMPurify.sanitize(`<p class="mb-4">${html}</p>`);
	}

	async function copyContent() {
		try {
			await navigator.clipboard.writeText(article.content);
			toast.success('Content copied to clipboard');
		} catch {
			toast.error('Failed to copy content');
		}
	}

	async function copyAsHtml() {
		try {
			const html = renderMarkdown(article.content);
			await navigator.clipboard.writeText(html);
			toast.success('HTML copied to clipboard');
		} catch {
			toast.error('Failed to copy HTML');
		}
	}

	function getActiveChanges(): string[] {
		return changes.filter(c => c.trim().length > 0);
	}

	async function handleRegenerate() {
		const activeChanges = getActiveChanges();

		if (activeChanges.length === 0 && selectedTone === (defaultTone || 'Professional')) {
			regenerateError = 'Please add at least one change or select a different tone';
			return;
		}

		regenerating = true;
		regenerateError = null;

		try {
			const updated = await apiClient.regenerateSeoArticle(article.id, {
				tone: selectedTone || undefined,
				changes: activeChanges.length > 0 ? activeChanges : undefined
			});
			onupdate(updated);
			toast.success('Article regenerated successfully');
			changes = ['', '', ''];
		} catch (err: unknown) {
			if (err && typeof err === 'object' && 'message' in err) {
				regenerateError = (err as { message: string }).message;
			} else {
				regenerateError = 'Failed to regenerate article';
			}
		} finally {
			regenerating = false;
		}
	}

	function getStatusVariant(status: string): 'success' | 'neutral' {
		return status === 'published' ? 'success' : 'neutral';
	}

	function enterEditMode() {
		editContent = article.content;
		editMode = true;
		hasUnsavedChanges = false;
	}

	function cancelEditMode() {
		if (hasUnsavedChanges) {
			const confirmed = confirm('You have unsaved changes. Are you sure you want to discard them?');
			if (!confirmed) return;
		}
		editMode = false;
		editContent = '';
		hasUnsavedChanges = false;
	}

	async function saveEdit() {
		if (!editContent.trim()) {
			toast.error('Content cannot be empty');
			return;
		}
		saving = true;
		try {
			const updated = await apiClient.updateSeoArticle(article.id, { content: editContent });
			onupdate(updated);
			editMode = false;
			editContent = '';
			hasUnsavedChanges = false;
			toast.success('Article saved');
		} catch (err: unknown) {
			if (err && typeof err === 'object' && 'message' in err) {
				toast.error((err as { message: string }).message);
			} else {
				toast.error('Failed to save article');
			}
		} finally {
			saving = false;
		}
	}

	function handleCloseAttempt() {
		if (hasUnsavedChanges) {
			const confirmed = confirm('You have unsaved changes. Are you sure you want to close?');
			if (!confirmed) return;
		}
		onclose();
	}
</script>

<Modal {open} title={article.title} size="lg" onclose={handleCloseAttempt}>
	<!-- Tab Navigation -->
	<div class="flex items-center gap-4 border-b border-neutral-200 dark:border-neutral-700 -mx-6 px-6 mb-4">
		<button
			type="button"
			class="pb-3 text-sm font-medium transition-colors border-b-2 -mb-px {activeTab === 'content'
				? 'border-brand-500 text-brand-600 dark:text-brand-400'
				: 'border-transparent text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300'}"
			onclick={() => activeTab = 'content'}
		>
			<FileText class="w-4 h-4 inline mr-1" />
			Content
		</button>
		<button
			type="button"
			class="pb-3 text-sm font-medium transition-colors border-b-2 -mb-px {activeTab === 'seo'
				? 'border-brand-500 text-brand-600 dark:text-brand-400'
				: 'border-transparent text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300'}"
			onclick={() => activeTab = 'seo'}
		>
			SEO Metadata
		</button>
	</div>

	<!-- Content Tab -->
	{#if activeTab === 'content'}
		<div class="space-y-4">
			<!-- Article metadata -->
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3 text-sm text-neutral-500 dark:text-neutral-400">
					<Badge variant={getStatusVariant(article.status)}>{article.status}</Badge>
					<span>{new Date(article.created_at).toLocaleDateString()}</span>
					<span>{article.content.length.toLocaleString()} characters</span>
				</div>
				{#if !editMode}
					<BoButton variant="outline" size="sm" onclick={enterEditMode} disabled={regenerating}>
						<Pencil class="w-4 h-4 mr-1" />
						Edit
					</BoButton>
				{/if}
			</div>

			<!-- Excerpt -->
			{#if article.excerpt && !editMode}
				<div class="p-3 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg">
					<p class="text-sm text-neutral-600 dark:text-neutral-400 italic">
						{article.excerpt}
					</p>
				</div>
			{/if}

			<!-- Article content - Edit mode or Preview mode -->
			{#if editMode}
				<div class="space-y-3">
					<textarea
						bind:value={editContent}
						class="w-full h-[400px] px-4 py-3 border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
						placeholder="Enter article content in markdown..."
						disabled={saving}
					></textarea>
					<div class="flex items-center justify-between">
						<p class="text-xs text-neutral-500">{editContent.length.toLocaleString()} characters</p>
						<div class="flex items-center gap-2">
							<BoButton variant="ghost" size="sm" onclick={cancelEditMode} disabled={saving}>
								<X class="w-4 h-4 mr-1" />
								Cancel
							</BoButton>
							<BoButton variant="brand" size="sm" onclick={saveEdit} loading={saving} disabled={saving}>
								<Save class="w-4 h-4 mr-1" />
								{saving ? 'Saving...' : 'Save'}
							</BoButton>
						</div>
					</div>
				</div>
			{:else}
				<div class="prose dark:prose-invert max-w-none max-h-[400px] overflow-y-auto p-4 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-lg">
					{@html renderMarkdown(article.content)}
				</div>

				<!-- Action buttons -->
				<div class="flex items-center gap-2">
					<BoButton variant="outline" size="sm" onclick={copyContent}>
						<Copy class="w-4 h-4 mr-1" />
						Copy Markdown
					</BoButton>
					<BoButton variant="outline" size="sm" onclick={copyAsHtml}>
						<Copy class="w-4 h-4 mr-1" />
						Copy HTML
					</BoButton>
				</div>
			{/if}

			<!-- Regenerate Panel (always visible for revision-first UX) -->
			{#if !editMode}
				<div class="border-t border-neutral-200 dark:border-neutral-700 pt-4">
					<div class="p-4 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg space-y-4">
						<div class="flex items-center gap-2">
							<RefreshCw class="w-4 h-4 text-brand-500" />
							<span class="font-medium text-neutral-900 dark:text-white">Regenerate with changes</span>
						</div>

						<p class="text-sm text-neutral-600 dark:text-neutral-400">
							Specify up to 3 changes you want to make to the article, and select a tone of voice.
						</p>

						<!-- Changes inputs -->
						<div class="space-y-3">
							{#each changes as _, i (i)}
								<div>
									<label for="change-{i}" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
										Change {i + 1} {i === 0 ? '' : '(optional)'}
									</label>
									<input
										id="change-{i}"
										type="text"
										bind:value={changes[i]}
										placeholder={i === 0 ? 'e.g., Make the introduction more engaging' : 'e.g., Add more examples'}
										class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
										disabled={regenerating}
									/>
								</div>
							{/each}
						</div>

						<!-- Tone selector -->
						<div>
							<label for="tone-select" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
								Tone of Voice
							</label>
							<select
								id="tone-select"
								bind:value={selectedTone}
								class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
								disabled={regenerating}
							>
								{#each toneOptions as option (option.value)}
									<option value={option.value}>{option.label}</option>
								{/each}
							</select>
							{#if defaultTone}
								<p class="mt-1 text-xs text-neutral-500">
									Default from your brand settings: {defaultTone}
								</p>
							{/if}
						</div>

						{#if regenerateError}
							<Alert variant="error">{regenerateError}</Alert>
						{/if}

						<div class="flex justify-end">
							<BoButton
								variant="brand"
								onclick={handleRegenerate}
								loading={regenerating}
								disabled={regenerating}
							>
								<RefreshCw class="w-4 h-4 mr-1" />
								{regenerating ? 'Regenerating...' : 'Regenerate Article'}
							</BoButton>
						</div>
					</div>
				</div>
			{/if}
		</div>
	{/if}

	<!-- SEO Tab -->
	{#if activeTab === 'seo'}
		<div class="space-y-4">
			<div>
				<p class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
					Meta Title
				</p>
				<div class="p-3 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg">
					<p class="text-neutral-900 dark:text-white">
						{article.meta_title || article.title}
					</p>
					<p class="text-xs text-neutral-500 mt-1">
						{(article.meta_title || article.title).length} / 60 characters
					</p>
				</div>
			</div>

			<div>
				<p class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
					Meta Description
				</p>
				<div class="p-3 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg">
					<p class="text-neutral-900 dark:text-white">
						{article.meta_description || article.excerpt || 'No description'}
					</p>
					<p class="text-xs text-neutral-500 mt-1">
						{(article.meta_description || article.excerpt || '').length} / 160 characters
					</p>
				</div>
			</div>

			{#if article.excerpt}
				<div>
					<p class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						Excerpt
					</p>
					<div class="p-3 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg">
						<p class="text-neutral-900 dark:text-white">{article.excerpt}</p>
					</div>
				</div>
			{/if}

			<div class="pt-4 border-t border-neutral-200 dark:border-neutral-700">
				<h3 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
					SEO Preview
				</h3>
				<div class="p-4 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-lg">
					<p class="text-info-600 dark:text-info-400 text-lg hover:underline cursor-pointer">
						{article.meta_title || article.title}
					</p>
					<p class="text-success-700 dark:text-success-500 text-sm">
						example.com/blog/{article.id}
					</p>
					<p class="text-neutral-600 dark:text-neutral-400 text-sm mt-1">
						{article.meta_description || article.excerpt || 'No description available'}
					</p>
				</div>
			</div>
		</div>
	{/if}
</Modal>
