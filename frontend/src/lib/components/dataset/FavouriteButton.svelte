<script lang="ts">
	/**
	 * FavouriteButton - Reusable favourite toggle button
	 *
	 * Shows a star icon that toggles favourite state with optimistic UI.
	 */

	interface Props {
		isFavourited: boolean;
		loading?: boolean;
		size?: 'sm' | 'md';
		onclick: () => void;
	}

	let { isFavourited, loading = false, size = 'md', onclick }: Props = $props();

	const sizeClasses = {
		sm: 'w-4 h-4',
		md: 'w-5 h-5',
	};

	const buttonSizeClasses = {
		sm: 'p-1',
		md: 'p-1.5',
	};
</script>

<button
	type="button"
	onclick={onclick}
	disabled={loading}
	class="rounded-lg transition-all duration-200 {buttonSizeClasses[size]}
		{isFavourited
		? 'text-warning-500 hover:text-warning-600 bg-warning-50 dark:bg-warning-900/20'
		: 'text-neutral-400 hover:text-warning-500 hover:bg-neutral-100 dark:hover:bg-neutral-700'}
		disabled:opacity-50 disabled:cursor-not-allowed"
	title={isFavourited ? 'Remove from favourites' : 'Add to favourites'}
>
	{#if loading}
		<svg class="{sizeClasses[size]} animate-spin" fill="none" viewBox="0 0 24 24">
			<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
			<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
		</svg>
	{:else if isFavourited}
		<svg class={sizeClasses[size]} viewBox="0 0 24 24" fill="currentColor">
			<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
		</svg>
	{:else}
		<svg class={sizeClasses[size]} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
			<path stroke-linecap="round" stroke-linejoin="round" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
		</svg>
	{/if}
</button>
