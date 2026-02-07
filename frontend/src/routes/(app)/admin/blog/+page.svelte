<script lang="ts">
	/**
	 * Admin Blog Page - List and manage blog posts
	 */
	import { onMount } from 'svelte';
	import { Button } from '$lib/components/ui';
	import { Plus, RefreshCw, FileText, Sparkles, Calendar, Eye, Trash2, Edit, Lightbulb, X } from 'lucide-svelte';
	import { adminApi, type BlogPost, type TopicProposal } from '$lib/api/admin';
	import BlogEditorModal from '$lib/components/admin/BlogEditorModal.svelte';
	import BlogGenerateModal from '$lib/components/admin/BlogGenerateModal.svelte';
	import AdminPageHeader from '$lib/components/admin/AdminPageHeader.svelte';
	import EmptyState from '$lib/components/ui/EmptyState.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';

	// State
	let posts = $state<BlogPost[]>([]);
	let total = $state(0);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let filter = $state<'all' | 'draft' | 'scheduled' | 'published'>('all');

	// Modals
	let showEditorModal = $state(false);
	let showGenerateModal = $state(false);
	let editingPost = $state<BlogPost | null>(null);
	let deleteConfirm = $state<BlogPost | null>(null);
	let isDeleting = $state(false);

	// Topic proposals
	let proposals = $state<TopicProposal[]>([]);
	let showProposals = $state(false);
	let isLoadingProposals = $state(false);
	let generateInitialTopic = $state('');
	let generateInitialKeywords = $state<string[]>([]);

	// Filtered posts based on status tab
	const filteredPosts = $derived(() => {
		if (filter === 'all') return posts;
		return posts.filter((p) => p.status === filter);
	});

	async function loadPosts() {
		isLoading = true;
		error = null;
		try {
			const statusParam = filter === 'all' ? undefined : filter;
			const response = await adminApi.listBlogPosts({ status: statusParam });
			posts = response.posts;
			total = response.total;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load posts';
		} finally {
			isLoading = false;
		}
	}

	async function openEditor(post?: BlogPost) {
		if (post) {
			// Fetch full post with content before editing
			try {
				editingPost = await adminApi.getBlogPost(post.id);
			} catch (err) {
				error = err instanceof Error ? err.message : 'Failed to load post';
				return;
			}
		} else {
			editingPost = null;
		}
		showEditorModal = true;
	}

	function handlePostSaved(post: BlogPost) {
		if (editingPost) {
			posts = posts.map((p) => (p.id === post.id ? post : p));
		} else {
			posts = [post, ...posts];
			total++;
		}
		showEditorModal = false;
		editingPost = null;
	}

	function handleGenerated(post: BlogPost) {
		posts = [post, ...posts];
		total++;
		showGenerateModal = false;
	}

	function requestDelete(post: BlogPost) {
		deleteConfirm = post;
	}

	function cancelDelete() {
		deleteConfirm = null;
	}

	async function confirmDelete() {
		if (!deleteConfirm) return;
		isDeleting = true;
		try {
			await adminApi.deleteBlogPost(deleteConfirm.id);
			posts = posts.filter((p) => p.id !== deleteConfirm!.id);
			total--;
			deleteConfirm = null;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to delete post';
		} finally {
			isDeleting = false;
		}
	}

	async function publishPost(post: BlogPost) {
		try {
			const updated = await adminApi.publishBlogPost(post.id);
			posts = posts.map((p) => (p.id === updated.id ? updated : p));
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to publish post';
		}
	}

	function formatDate(date: string | undefined) {
		if (!date) return '-';
		return new Date(date).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function getStatusColor(status: string) {
		switch (status) {
			case 'draft':
				return 'bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-300';
			case 'scheduled':
				return 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400';
			case 'published':
				return 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400';
			default:
				return 'bg-neutral-100 text-neutral-600';
		}
	}

	async function loadProposals() {
		isLoadingProposals = true;
		try {
			const response = await adminApi.proposeTopics(5);
			proposals = response.topics;
			showProposals = true;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load proposals';
		} finally {
			isLoadingProposals = false;
		}
	}

	function dismissProposal(index: number) {
		proposals = proposals.filter((_, i) => i !== index);
		if (proposals.length === 0) {
			showProposals = false;
		}
	}

	function generateFromProposal(proposal: TopicProposal) {
		generateInitialTopic = proposal.title;
		generateInitialKeywords = proposal.suggested_keywords || [];
		showGenerateModal = true;
	}

	function openGenerateModal() {
		generateInitialTopic = '';
		generateInitialKeywords = [];
		showGenerateModal = true;
	}

	onMount(() => {
		loadPosts();
	});
</script>

<svelte:head>
	<title>Blog Posts - Admin - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<AdminPageHeader title="Blog Posts" icon={FileText}>
		{#snippet badge()}
			<span class="px-2.5 py-0.5 rounded-full text-xs font-medium bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400">
				{total} posts
			</span>
		{/snippet}
		{#snippet actions()}
			<Button variant="outline" size="sm" onclick={() => loadPosts()} disabled={isLoading}>
				<RefreshCw class="w-4 h-4 mr-1.5 {isLoading ? 'animate-spin' : ''}" />
				Refresh
			</Button>
			<Button variant="outline" size="sm" onclick={() => loadProposals()} disabled={isLoadingProposals}>
				<Lightbulb class="w-4 h-4 mr-1.5 {isLoadingProposals ? 'animate-pulse' : ''}" />
				Propose Topics
			</Button>
			<Button variant="outline" size="sm" onclick={openGenerateModal}>
				<Sparkles class="w-4 h-4 mr-1.5" />
				Generate
			</Button>
			<Button size="sm" onclick={() => openEditor()}>
				<Plus class="w-4 h-4 mr-1.5" />
				New Post
			</Button>
		{/snippet}
	</AdminPageHeader>

	<!-- Filter tabs -->
	<div class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12">
			<nav class="flex gap-6" aria-label="Tabs">
				{#each ['all', 'draft', 'scheduled', 'published'] as tab}
					<button
						class="px-1 py-3 text-sm font-medium border-b-2 transition-colors {filter === tab
							? 'border-brand-500 text-brand-600 dark:text-brand-400'
							: 'border-transparent text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-300'}"
						onclick={() => {
							filter = tab as typeof filter;
							loadPosts();
						}}
					>
						{tab.charAt(0).toUpperCase() + tab.slice(1)}
					</button>
				{/each}
			</nav>
		</div>
	</div>

	<!-- Topic Proposals -->
	{#if showProposals && proposals.length > 0}
		<div class="bg-warning-50 dark:bg-warning-900/20 border-b border-warning-200 dark:border-warning-800">
			<div class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-4">
				<div class="flex items-center justify-between mb-3">
					<div class="flex items-center gap-2">
						<Lightbulb class="w-5 h-5 text-warning-600 dark:text-warning-400" />
						<h2 class="font-medium text-warning-900 dark:text-warning-100">Suggested Topics</h2>
					</div>
					<div class="flex items-center gap-2">
						<Button variant="ghost" size="sm" onclick={() => loadProposals()} disabled={isLoadingProposals}>
							<RefreshCw class="w-4 h-4 {isLoadingProposals ? 'animate-spin' : ''}" />
						</Button>
						<Button variant="ghost" size="sm" onclick={() => (showProposals = false)}>
							<X class="w-4 h-4" />
						</Button>
					</div>
				</div>
				<div class="space-y-3">
					{#each proposals as proposal, i}
						<div class="bg-white dark:bg-neutral-800 rounded-lg border border-warning-200 dark:border-warning-700 p-4">
							<div class="flex items-start justify-between gap-4">
								<div class="flex-1 min-w-0">
									<h3 class="font-medium text-neutral-900 dark:text-white">{proposal.title}</h3>
									<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">{proposal.rationale}</p>
									{#if proposal.suggested_keywords && proposal.suggested_keywords.length > 0}
										<div class="flex flex-wrap gap-1 mt-2">
											{#each proposal.suggested_keywords as keyword}
												<span class="px-2 py-0.5 rounded text-xs bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400">
													{keyword}
												</span>
											{/each}
										</div>
									{/if}
									<span class="inline-block mt-2 px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
										{proposal.source}
									</span>
								</div>
								<div class="flex items-center gap-2">
									<Button variant="outline" size="sm" onclick={() => generateFromProposal(proposal)}>
										<Sparkles class="w-4 h-4 mr-1" />
										Generate
									</Button>
									<Button variant="ghost" size="sm" onclick={() => dismissProposal(i)}>
										<X class="w-4 h-4" />
									</Button>
								</div>
							</div>
						</div>
					{/each}
				</div>
			</div>
		</div>
	{/if}

	<!-- Content -->
	<main class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-6">
		{#if error}
			<div class="rounded-lg bg-error-50 dark:bg-error-900/20 p-4 mb-6">
				<p class="text-sm text-error-700 dark:text-error-400">{error}</p>
			</div>
		{/if}

		{#if isLoading}
			<div class="animate-pulse space-y-4">
				{#each Array(3) as _}
					<div class="h-24 bg-neutral-200 dark:bg-neutral-700 rounded-lg"></div>
				{/each}
			</div>
		{:else if filteredPosts().length === 0}
			<EmptyState title="No posts yet" description="Create your first blog post or generate one with AI." icon={FileText}>
				{#snippet actions()}
					<Button variant="outline" onclick={() => (showGenerateModal = true)}>
						<Sparkles class="w-4 h-4 mr-1.5" />
						Generate with AI
					</Button>
					<Button onclick={() => openEditor()}>
						<Plus class="w-4 h-4 mr-1.5" />
						New Post
					</Button>
				{/snippet}
			</EmptyState>
		{:else}
			<div class="space-y-4">
				{#each filteredPosts() as post (post.id)}
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 hover:shadow-sm transition-shadow"
					>
						<div class="flex items-start justify-between gap-4">
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-2 mb-1">
									<span
										class="px-2 py-0.5 rounded text-xs font-medium {getStatusColor(post.status)}"
									>
										{post.status}
									</span>
									{#if post.generated_by_topic}
										<span
											class="px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400"
										>
											AI Generated
										</span>
									{/if}
								</div>
								<h3
									class="text-lg font-medium text-neutral-900 dark:text-white truncate"
									title={post.title}
								>
									{post.title}
								</h3>
								{#if post.excerpt}
									<p class="text-sm text-neutral-500 dark:text-neutral-400 mt-1 line-clamp-2">
										{post.excerpt}
									</p>
								{/if}
								<div class="flex items-center gap-4 mt-2 text-xs text-neutral-500 dark:text-neutral-400">
									<span>Slug: {post.slug}</span>
									{#if post.status === 'scheduled' && post.published_at}
										<span class="flex items-center gap-1">
											<Calendar class="w-3 h-3" />
											Scheduled: {formatDate(post.published_at)}
										</span>
									{:else if post.status === 'published' && post.published_at}
										<span>Published: {formatDate(post.published_at)}</span>
									{:else}
										<span>Updated: {formatDate(post.updated_at)}</span>
									{/if}
								</div>
							</div>
							<div class="flex items-center gap-2">
								{#if post.status === 'draft'}
									<Button variant="outline" size="sm" onclick={() => publishPost(post)}>
										<Eye class="w-4 h-4 mr-1" />
										Publish
									</Button>
								{/if}
								<Button variant="ghost" size="sm" onclick={() => openEditor(post)}>
									<Edit class="w-4 h-4" />
								</Button>
								<Button variant="ghost" size="sm" onclick={() => requestDelete(post)}>
									<Trash2 class="w-4 h-4 text-error-500" />
								</Button>
							</div>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</main>
</div>

<!-- Delete confirmation -->
<Modal open={!!deleteConfirm} title="Delete Post?" size="sm" onclose={cancelDelete}>
	<p class="text-neutral-600 dark:text-neutral-400">
		Are you sure you want to delete "{deleteConfirm?.title}"? This cannot be undone.
	</p>
	{#snippet footer()}
		<div class="flex justify-end gap-3">
			<Button variant="outline" onclick={cancelDelete} disabled={isDeleting}>Cancel</Button>
			<Button variant="danger" onclick={confirmDelete} disabled={isDeleting}>
				{isDeleting ? 'Deleting...' : 'Delete'}
			</Button>
		</div>
	{/snippet}
</Modal>

<!-- Editor Modal -->
{#if showEditorModal}
	<BlogEditorModal
		post={editingPost}
		onclose={() => {
			showEditorModal = false;
			editingPost = null;
		}}
		onsave={handlePostSaved}
	/>
{/if}

<!-- Generate Modal -->
{#if showGenerateModal}
	<BlogGenerateModal
		onclose={() => (showGenerateModal = false)}
		ongenerated={handleGenerated}
		initialTopic={generateInitialTopic}
		initialKeywords={generateInitialKeywords}
	/>
{/if}
