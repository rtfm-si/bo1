<script lang="ts">
	/**
	 * BlogEditorModal - Create and edit blog posts with markdown preview
	 */
	import { Button, Alert } from '$lib/components/ui';
	import { X, Eye, Edit, Calendar } from 'lucide-svelte';
	import { adminApi, type BlogPost, type BlogPostCreate, type BlogPostUpdate } from '$lib/api/admin';

	interface Props {
		post: BlogPost | null;
		onclose: () => void;
		onsave: (post: BlogPost) => void;
	}

	let { post, onclose, onsave }: Props = $props();

	// Form state
	let title = $state(post?.title || '');
	let content = $state(post?.content || '');
	let excerpt = $state(post?.excerpt || '');
	let status = $state<'draft' | 'scheduled' | 'published'>(post?.status || 'draft');
	let publishedAt = $state(post?.published_at ? post.published_at.slice(0, 16) : '');
	let seoKeywords = $state(post?.seo_keywords?.join(', ') || '');
	let metaTitle = $state(post?.meta_title || '');
	let metaDescription = $state(post?.meta_description || '');

	let isSubmitting = $state(false);
	let error = $state<string | null>(null);
	let activeTab = $state<'edit' | 'preview'>('edit');

	const isEditing = $derived(!!post);

	function validate(): string | null {
		if (!title.trim()) return 'Title is required';
		if (!content.trim()) return 'Content is required';
		if (status === 'scheduled' && !publishedAt) return 'Scheduled posts require a publish date';
		if (metaTitle.length > 100) return 'Meta title must be under 100 characters';
		if (metaDescription.length > 300) return 'Meta description must be under 300 characters';
		return null;
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();
		error = null;

		const validationError = validate();
		if (validationError) {
			error = validationError;
			return;
		}

		isSubmitting = true;
		try {
			const keywords = seoKeywords
				.split(',')
				.map((k) => k.trim())
				.filter(Boolean);

			if (isEditing && post) {
				const updates: BlogPostUpdate = {
					title: title.trim(),
					content: content.trim(),
					excerpt: excerpt.trim() || undefined,
					status,
					published_at: publishedAt ? new Date(publishedAt).toISOString() : undefined,
					seo_keywords: keywords.length > 0 ? keywords : undefined,
					meta_title: metaTitle.trim() || undefined,
					meta_description: metaDescription.trim() || undefined
				};
				const updated = await adminApi.updateBlogPost(post.id, updates);
				onsave(updated);
			} else {
				const request: BlogPostCreate = {
					title: title.trim(),
					content: content.trim(),
					excerpt: excerpt.trim() || undefined,
					status,
					published_at: publishedAt ? new Date(publishedAt).toISOString() : undefined,
					seo_keywords: keywords.length > 0 ? keywords : undefined,
					meta_title: metaTitle.trim() || undefined,
					meta_description: metaDescription.trim() || undefined
				};
				const created = await adminApi.createBlogPost(request);
				onsave(created);
			}
		} catch (err: unknown) {
			if (err && typeof err === 'object' && 'message' in err) {
				error = (err as { message: string }).message;
			} else {
				error = 'Failed to save post';
			}
		} finally {
			isSubmitting = false;
		}
	}

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) {
			onclose();
		}
	}

	// Simple markdown to HTML (basic support)
	function renderMarkdown(md: string): string {
		return md
			.replace(/^### (.*$)/gm, '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>')
			.replace(/^## (.*$)/gm, '<h2 class="text-xl font-semibold mt-6 mb-3">$1</h2>')
			.replace(/^# (.*$)/gm, '<h1 class="text-2xl font-bold mt-8 mb-4">$1</h1>')
			.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
			.replace(/\*(.*?)\*/g, '<em>$1</em>')
			.replace(/`(.*?)`/g, '<code class="bg-neutral-100 px-1 rounded">$1</code>')
			.replace(/\n/g, '<br>');
	}
</script>

{#if true}
	<div
		class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
		onclick={handleBackdropClick}
		role="button"
		tabindex="-1"
	>
		<div
			class="bg-white dark:bg-neutral-800 rounded-lg w-full max-w-4xl max-h-[90vh] flex flex-col"
			onclick={(e) => e.stopPropagation()}
			role="dialog"
		>
			<!-- Header -->
			<div
				class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700"
			>
				<h2 class="text-xl font-semibold text-neutral-900 dark:text-white">
					{isEditing ? 'Edit Post' : 'New Post'}
				</h2>
				<button
					class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
					onclick={onclose}
					aria-label="Close"
				>
					<X class="w-5 h-5 text-neutral-500" />
				</button>
			</div>

			<!-- Content -->
			<form onsubmit={handleSubmit} class="flex-1 overflow-y-auto p-6 space-y-6">
				{#if error}
					<Alert variant="error">{error}</Alert>
				{/if}

				<!-- Title -->
				<div>
					<label class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						Title <span class="text-red-500">*</span>
					</label>
					<input
						type="text"
						bind:value={title}
						class="w-full px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-transparent"
						placeholder="Enter post title..."
					/>
				</div>

				<!-- Content with tabs -->
				<div>
					<div class="flex items-center justify-between mb-1">
						<label class="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
							Content <span class="text-red-500">*</span>
						</label>
						<div class="flex gap-2">
							<button
								type="button"
								class="px-3 py-1 text-sm rounded-md transition-colors {activeTab === 'edit'
									? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400'
									: 'text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-700'}"
								onclick={() => (activeTab = 'edit')}
							>
								<Edit class="w-4 h-4 inline mr-1" />
								Edit
							</button>
							<button
								type="button"
								class="px-3 py-1 text-sm rounded-md transition-colors {activeTab === 'preview'
									? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400'
									: 'text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-700'}"
								onclick={() => (activeTab = 'preview')}
							>
								<Eye class="w-4 h-4 inline mr-1" />
								Preview
							</button>
						</div>
					</div>
					{#if activeTab === 'edit'}
						<textarea
							bind:value={content}
							rows={12}
							class="w-full px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-transparent font-mono text-sm"
							placeholder="Write your blog post in Markdown..."
						></textarea>
					{:else}
						<div
							class="w-full px-4 py-3 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-neutral-50 dark:bg-neutral-900 min-h-[300px] prose dark:prose-invert max-w-none"
						>
							{@html renderMarkdown(content)}
						</div>
					{/if}
				</div>

				<!-- Excerpt -->
				<div>
					<label class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						Excerpt
						<span class="text-neutral-400 font-normal">(for previews)</span>
					</label>
					<textarea
						bind:value={excerpt}
						rows={2}
						class="w-full px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-transparent"
						placeholder="Brief summary for search results and social shares..."
					></textarea>
				</div>

				<!-- Status & Schedule -->
				<div class="grid grid-cols-2 gap-4">
					<div>
						<label class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
							Status
						</label>
						<select
							bind:value={status}
							class="w-full px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500"
						>
							<option value="draft">Draft</option>
							<option value="scheduled">Scheduled</option>
							<option value="published">Published</option>
						</select>
					</div>
					<div>
						<label class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
							<Calendar class="w-4 h-4 inline mr-1" />
							Publish Date
							{#if status === 'scheduled'}
								<span class="text-red-500">*</span>
							{/if}
						</label>
						<input
							type="datetime-local"
							bind:value={publishedAt}
							class="w-full px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500"
						/>
					</div>
				</div>

				<!-- SEO Section -->
				<details class="border border-neutral-200 dark:border-neutral-700 rounded-lg">
					<summary
						class="px-4 py-3 cursor-pointer text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700/50"
					>
						SEO Settings
					</summary>
					<div class="px-4 pb-4 space-y-4">
						<div>
							<label class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
								Keywords
								<span class="text-neutral-400 font-normal">(comma-separated)</span>
							</label>
							<input
								type="text"
								bind:value={seoKeywords}
								class="w-full px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500"
								placeholder="business decisions, AI, productivity"
							/>
						</div>
						<div>
							<label class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
								Meta Title
								<span class="text-neutral-400 font-normal">({metaTitle.length}/100)</span>
							</label>
							<input
								type="text"
								bind:value={metaTitle}
								maxlength={100}
								class="w-full px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500"
								placeholder="Custom title for search engines"
							/>
						</div>
						<div>
							<label class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
								Meta Description
								<span class="text-neutral-400 font-normal">({metaDescription.length}/300)</span>
							</label>
							<textarea
								bind:value={metaDescription}
								rows={2}
								maxlength={300}
								class="w-full px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500"
								placeholder="Description for search results"
							></textarea>
						</div>
					</div>
				</details>
			</form>

			<!-- Footer -->
			<div
				class="flex items-center justify-end gap-3 px-6 py-4 border-t border-neutral-200 dark:border-neutral-700"
			>
				<Button variant="outline" onclick={onclose} disabled={isSubmitting}>Cancel</Button>
				<Button type="submit" onclick={handleSubmit} disabled={isSubmitting}>
					{isSubmitting ? 'Saving...' : isEditing ? 'Update Post' : 'Create Post'}
				</Button>
			</div>
		</div>
	</div>
{/if}
