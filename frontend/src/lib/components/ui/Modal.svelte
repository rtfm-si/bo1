<script lang="ts">
	/**
	 * Modal Component - Accessible dialog overlay
	 * Used for session details, confirmations, background mode settings
	 */

	import { onMount, onDestroy } from 'svelte';
	import { createEventDispatcher } from 'svelte';
	import { browser } from '$app/environment';

	// Props
	export let open = false;
	export let title: string;
	export let size: 'sm' | 'md' | 'lg' | 'full' = 'md';
	export let closable = true;

	const dispatch = createEventDispatcher();

	// Size styles
	const sizes = {
		sm: 'max-w-md',
		md: 'max-w-lg',
		lg: 'max-w-2xl',
		full: 'max-w-full mx-4',
	};

	// Focus trap elements
	let modalElement: HTMLDivElement;
	let previousActiveElement: Element | null = null;

	// Handle ESC key
	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && closable) {
			close();
		}
	}

	// Close modal
	function close() {
		dispatch('close');
	}

	// Lock body scroll when modal opens (only in browser)
	$: if (browser) {
		if (open) {
			previousActiveElement = document.activeElement;
			document.body.style.overflow = 'hidden';
		} else {
			document.body.style.overflow = '';
			if (previousActiveElement instanceof HTMLElement) {
				previousActiveElement.focus();
			}
		}
	}

	onDestroy(() => {
		if (browser) {
			document.body.style.overflow = '';
		}
	});
</script>

{#if open}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 z-modalBackdrop bg-black/50 backdrop-blur-sm transition-opacity duration-300"
		on:click={closable ? close : undefined}
		aria-hidden="true"
	></div>

	<!-- Modal -->
	<div
		class="fixed inset-0 z-modal flex items-center justify-center p-4"
		on:keydown={handleKeydown}
		role="presentation"
	>
		<div
			bind:this={modalElement}
			class={[
				'relative w-full bg-white dark:bg-neutral-900 rounded-xl shadow-2xl',
				'transform transition-all duration-300',
				'max-h-[90vh] flex flex-col',
				sizes[size],
			].join(' ')}
			role="dialog"
			aria-modal="true"
			aria-labelledby="modal-title"
		>
			<!-- Header -->
			<div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
				<h2 id="modal-title" class="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
					{title}
				</h2>
				{#if closable}
					<button
						type="button"
						class="text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200 transition-colors"
						on:click={close}
						aria-label="Close modal"
					>
						<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				{/if}
			</div>

			<!-- Body -->
			<div class="flex-1 overflow-y-auto px-6 py-4">
				<slot />
			</div>

			<!-- Footer (optional) -->
			{#if $$slots.footer}
				<div class="px-6 py-4 border-t border-neutral-200 dark:border-neutral-700">
					<slot name="footer" />
				</div>
			{/if}
		</div>
	</div>
{/if}
