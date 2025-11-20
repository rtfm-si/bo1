<script module lang="ts">
	// Types
	export interface DropdownItem {
		value: string;
		label: string;
		icon?: string;
	}
</script>

<script lang="ts">
	/**
	 * Dropdown Component - Accessible select with keyboard navigation
	 * Used for theme switcher, advisor filtering, etc.
	 */

	import { clickOutside } from '$lib/utils/clickOutside';

	// Props
	interface Props {
		items: DropdownItem[];
		value?: string;
		placeholder?: string;
		disabled?: boolean;
		searchable?: boolean;
		onselect?: (value: string) => void;
	}

	let {
		items,
		value = $bindable(),
		placeholder = 'Select...',
		disabled = false,
		searchable = false,
		onselect
	}: Props = $props();

	// State
	let isOpen = $state(false);
	let searchQuery = $state('');
	let highlightedIndex = $state(0);

	// Computed
	const selectedItem = $derived(items.find((item) => item.value === value));
	const filteredItems = $derived(searchable && searchQuery
		? items.filter((item) =>
				item.label.toLowerCase().includes(searchQuery.toLowerCase())
		  )
		: items);

	// Handlers
	function toggle() {
		if (!disabled) {
			isOpen = !isOpen;
			if (isOpen) {
				highlightedIndex = items.findIndex((item) => item.value === value);
				if (highlightedIndex === -1) highlightedIndex = 0;
			}
		}
	}

	function select(item: DropdownItem) {
		value = item.value;
		onselect?.(item.value);
		isOpen = false;
		searchQuery = '';
	}

	function handleKeydown(e: KeyboardEvent) {
		if (disabled) return;

		switch (e.key) {
			case 'Enter':
			case ' ':
				if (!isOpen) {
					isOpen = true;
				} else {
					select(filteredItems[highlightedIndex]);
				}
				e.preventDefault();
				break;
			case 'Escape':
				isOpen = false;
				searchQuery = '';
				e.preventDefault();
				break;
			case 'ArrowDown':
				if (!isOpen) {
					isOpen = true;
				} else {
					highlightedIndex = (highlightedIndex + 1) % filteredItems.length;
				}
				e.preventDefault();
				break;
			case 'ArrowUp':
				if (isOpen) {
					highlightedIndex =
						(highlightedIndex - 1 + filteredItems.length) % filteredItems.length;
				}
				e.preventDefault();
				break;
		}
	}

	function handleClickOutside() {
		isOpen = false;
		searchQuery = '';
	}
</script>

<div
	class="relative w-full"
	use:clickOutside={handleClickOutside}
>
	<!-- Trigger button -->
	<button
		type="button"
		class={[
			'w-full flex items-center justify-between gap-2 px-4 py-2 text-left',
			'bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700',
			'rounded-md shadow-sm transition-colors',
			'focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500',
			disabled
				? 'opacity-50 cursor-not-allowed'
				: 'hover:border-neutral-300 dark:hover:border-neutral-600',
		].join(' ')}
		{disabled}
		onclick={toggle}
		onkeydown={handleKeydown}
		aria-haspopup="listbox"
		aria-expanded={isOpen}
	>
		<span class="flex items-center gap-2 text-neutral-900 dark:text-neutral-100">
			{#if selectedItem?.icon}
				<span>{selectedItem.icon}</span>
			{/if}
			{selectedItem?.label || placeholder}
		</span>
		<svg
			class={[
				'w-5 h-5 text-neutral-500 transition-transform',
				isOpen ? 'rotate-180' : '',
			].join(' ')}
			fill="none"
			stroke="currentColor"
			viewBox="0 0 24 24"
		>
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
		</svg>
	</button>

	<!-- Dropdown menu -->
	{#if isOpen}
		<div
			class="absolute z-dropdown w-full mt-1 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-md shadow-lg max-h-60 overflow-auto"
			role="listbox"
		>
			{#if searchable}
				<div class="p-2 border-b border-neutral-200 dark:border-neutral-700">
					<input
						type="text"
						class="w-full px-3 py-1.5 text-sm bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded focus:outline-none focus:ring-2 focus:ring-brand-500"
						placeholder="Search..."
						bind:value={searchQuery}
					/>
				</div>
			{/if}

			{#each filteredItems as item, index}
				<button
					type="button"
					class={[
						'w-full flex items-center gap-2 px-4 py-2 text-left transition-colors',
						highlightedIndex === index
							? 'bg-brand-50 dark:bg-brand-900/20'
							: 'hover:bg-neutral-50 dark:hover:bg-neutral-700',
						item.value === value
							? 'text-brand-700 dark:text-brand-400 font-medium'
							: 'text-neutral-900 dark:text-neutral-100',
					].join(' ')}
					role="option"
					aria-selected={item.value === value}
					onclick={() => select(item)}
					onmouseenter={() => (highlightedIndex = index)}
				>
					{#if item.icon}
						<span>{item.icon}</span>
					{/if}
					{item.label}
					{#if item.value === value}
						<svg class="w-5 h-5 ml-auto" fill="currentColor" viewBox="0 0 20 20">
							<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
						</svg>
					{/if}
				</button>
			{/each}

			{#if filteredItems.length === 0}
				<div class="px-4 py-2 text-sm text-neutral-500 dark:text-neutral-400">
					No results found
				</div>
			{/if}
		</div>
	{/if}
</div>
