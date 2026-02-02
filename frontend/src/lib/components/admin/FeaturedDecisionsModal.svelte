<script lang="ts">
	/**
	 * FeaturedDecisionsModal - Drag-and-drop reorder for homepage featured decisions
	 */
	import { onMount } from 'svelte';
	import { Button } from '$lib/components/ui';
	import { X, GripVertical, Star, Trash2, Loader2 } from 'lucide-svelte';
	import { adminApi, type FeaturedDecision } from '$lib/api/admin';

	interface Props {
		onclose: () => void;
		onsave: () => void;
	}

	let { onclose, onsave }: Props = $props();

	let featured = $state<FeaturedDecision[]>([]);
	let isLoading = $state(true);
	let isSaving = $state(false);
	let error = $state<string | null>(null);
	let hasChanges = $state(false);
	let draggedIndex = $state<number | null>(null);

	async function loadFeatured() {
		isLoading = true;
		error = null;
		try {
			const response = await adminApi.listFeaturedDecisions();
			featured = response.decisions;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load featured decisions';
		} finally {
			isLoading = false;
		}
	}

	async function saveOrder() {
		if (!hasChanges) {
			onclose();
			return;
		}

		isSaving = true;
		error = null;
		try {
			await adminApi.reorderFeaturedDecisions(featured.map((d) => d.id));
			onsave();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to save order';
		} finally {
			isSaving = false;
		}
	}

	async function removeFromFeatured(decision: FeaturedDecision) {
		try {
			await adminApi.unfeatureDecision(decision.id);
			featured = featured.filter((d) => d.id !== decision.id);
			hasChanges = true;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to remove from featured';
		}
	}

	function handleDragStart(index: number) {
		draggedIndex = index;
	}

	function handleDragOver(e: DragEvent, index: number) {
		e.preventDefault();
		if (draggedIndex === null || draggedIndex === index) return;

		const newFeatured = [...featured];
		const [removed] = newFeatured.splice(draggedIndex, 1);
		newFeatured.splice(index, 0, removed);
		featured = newFeatured;
		draggedIndex = index;
		hasChanges = true;
	}

	function handleDragEnd() {
		draggedIndex = null;
	}

	function getCategoryColor(category: string) {
		const colors: Record<string, string> = {
			hiring: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
			pricing: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
			fundraising: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
			marketing: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400',
			strategy: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
			product: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
			operations: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
			growth: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
		};
		return colors[category] || 'bg-neutral-100 text-neutral-600';
	}

	onMount(() => {
		loadFeatured();
	});
</script>

<div
	class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
	role="dialog"
	aria-modal="true"
	aria-labelledby="modal-title"
>
	<div
		class="bg-white dark:bg-neutral-800 rounded-xl shadow-xl max-w-lg w-full max-h-[80vh] flex flex-col"
	>
		<!-- Header -->
		<div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
			<div class="flex items-center gap-2">
				<Star class="w-5 h-5 text-amber-500" />
				<h2 id="modal-title" class="text-lg font-semibold text-neutral-900 dark:text-white">
					Homepage Featured
				</h2>
				<span class="text-sm text-neutral-500 dark:text-neutral-400">
					({featured.length}/6)
				</span>
			</div>
			<button
				onclick={onclose}
				class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
				aria-label="Close"
			>
				<X class="w-5 h-5 text-neutral-500" />
			</button>
		</div>

		<!-- Content -->
		<div class="flex-1 overflow-y-auto p-6">
			{#if error}
				<div class="rounded-lg bg-red-50 dark:bg-red-900/20 p-3 mb-4">
					<p class="text-sm text-red-700 dark:text-red-400">{error}</p>
				</div>
			{/if}

			{#if isLoading}
				<div class="flex items-center justify-center py-8">
					<Loader2 class="w-6 h-6 text-brand-500 animate-spin" />
				</div>
			{:else if featured.length === 0}
				<div class="text-center py-8">
					<Star class="w-12 h-12 mx-auto text-neutral-300 dark:text-neutral-600 mb-3" />
					<p class="text-neutral-600 dark:text-neutral-400">
						No featured decisions yet.
					</p>
					<p class="text-sm text-neutral-500 dark:text-neutral-500 mt-1">
						Click the star icon on published decisions to feature them.
					</p>
				</div>
			{:else}
				<p class="text-sm text-neutral-500 dark:text-neutral-400 mb-4">
					Drag to reorder. First 6 will appear on homepage.
				</p>
				<div class="space-y-2">
					{#each featured as decision, index (decision.id)}
						<div
							role="listitem"
							draggable="true"
							ondragstart={() => handleDragStart(index)}
							ondragover={(e) => handleDragOver(e, index)}
							ondragend={handleDragEnd}
							class="flex items-center gap-3 p-3 bg-neutral-50 dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-700 cursor-move transition-all {draggedIndex === index ? 'opacity-50 scale-95' : ''}"
						>
							<div class="flex-shrink-0 text-neutral-400 dark:text-neutral-500">
								<GripVertical class="w-5 h-5" />
							</div>
							<div class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center text-xs font-bold text-brand-600 dark:text-brand-400">
								{index + 1}
							</div>
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-2 mb-0.5">
									<span class="px-1.5 py-0.5 rounded text-xs font-medium {getCategoryColor(decision.category)}">
										{decision.category}
									</span>
								</div>
								<p class="text-sm font-medium text-neutral-900 dark:text-white truncate">
									{decision.title}
								</p>
							</div>
							<button
								onclick={() => removeFromFeatured(decision)}
								class="flex-shrink-0 p-1.5 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-colors"
								title="Remove from featured"
							>
								<Trash2 class="w-4 h-4 text-red-500" />
							</button>
						</div>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Footer -->
		<div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-neutral-200 dark:border-neutral-700">
			<Button variant="outline" onclick={onclose} disabled={isSaving}>
				Cancel
			</Button>
			<Button onclick={saveOrder} disabled={isSaving || isLoading}>
				{#if isSaving}
					<Loader2 class="w-4 h-4 mr-1.5 animate-spin" />
					Saving...
				{:else}
					Save Order
				{/if}
			</Button>
		</div>
	</div>
</div>
