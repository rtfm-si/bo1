<script module lang="ts">
	// Types
	export interface Tab {
		id: string;
		label: string;
		icon?: string;
	}
</script>

<script lang="ts">
	/**
	 * Tabs Component - Accessible tab navigation
	 * Used for session views (overview/contributions/synthesis)
	 */

	import type { Snippet } from 'svelte';

	// Props
	interface Props {
		tabs: Tab[];
		activeTab?: string;
		children?: Snippet<[{ activeTab: string | undefined }]>;
		onchange?: (tabId: string) => void;
	}

	let {
		tabs,
		activeTab = $bindable(),
		children,
		onchange
	}: Props = $props();

	// Handlers
	function selectTab(tabId: string) {
		activeTab = tabId;
		onchange?.(tabId);
	}

	function handleKeydown(e: KeyboardEvent, tabId: string) {
		const currentIndex = tabs.findIndex((t) => t.id === activeTab);
		let newIndex = currentIndex;

		switch (e.key) {
			case 'ArrowLeft':
				newIndex = currentIndex > 0 ? currentIndex - 1 : tabs.length - 1;
				e.preventDefault();
				break;
			case 'ArrowRight':
				newIndex = currentIndex < tabs.length - 1 ? currentIndex + 1 : 0;
				e.preventDefault();
				break;
			case 'Home':
				newIndex = 0;
				e.preventDefault();
				break;
			case 'End':
				newIndex = tabs.length - 1;
				e.preventDefault();
				break;
		}

		if (newIndex !== currentIndex) {
			selectTab(tabs[newIndex].id);
		}
	}
</script>

<div class="w-full">
	<!-- Tab list -->
	<div
		class="flex border-b border-neutral-200 dark:border-neutral-700"
		role="tablist"
		aria-label="Content tabs"
	>
		{#each tabs as tab}
			<button
				type="button"
				class={[
					'flex items-center gap-2 px-4 py-2 font-medium transition-colors',
					'border-b-2 -mb-px',
					'focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2',
					activeTab === tab.id
						? 'border-brand-600 text-brand-700 dark:border-brand-400 dark:text-brand-400'
						: 'border-transparent text-neutral-600 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100 hover:border-neutral-300 dark:hover:border-neutral-600',
				].join(' ')}
				role="tab"
				aria-selected={activeTab === tab.id}
				aria-controls={`tabpanel-${tab.id}`}
				id={`tab-${tab.id}`}
				onclick={() => selectTab(tab.id)}
				onkeydown={(e) => handleKeydown(e, tab.id)}
			>
				{#if tab.icon}
					<span>{tab.icon}</span>
				{/if}
				{tab.label}
			</button>
		{/each}
	</div>

	<!-- Tab panel (single slot, consumer manages visibility) -->
	<div class="mt-4">
		{@render children?.({ activeTab })}
	</div>
</div>
