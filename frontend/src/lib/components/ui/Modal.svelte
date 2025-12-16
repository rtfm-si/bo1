<script lang="ts">
	/**
	 * Modal Component - Accessible dialog overlay
	 * Used for session details, confirmations, background mode settings
	 */

	import { onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import type { Snippet } from 'svelte';

	// Props
	interface Props {
		open?: boolean;
		title: string;
		size?: 'sm' | 'md' | 'lg' | 'full';
		closable?: boolean;
		children?: Snippet;
		footer?: Snippet;
		onclose?: () => void;
	}

	let {
		open = $bindable(false),
		title,
		size = 'md',
		closable = true,
		children,
		footer,
		onclose
	}: Props = $props();

	// Size styles
	const sizes = {
		sm: 'max-w-md',
		md: 'max-w-lg',
		lg: 'max-w-2xl',
		full: 'max-w-full mx-4',
	};

	// Focus trap elements
	let modalElement = $state<HTMLDivElement>();
	let previousActiveElement: Element | null = null;

	// Handle ESC key and focus trap
	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && closable) {
			close();
			return;
		}

		// Focus trap: Tab key navigation within modal
		if (e.key === 'Tab' && modalElement) {
			const focusableElements = modalElement.querySelectorAll<HTMLElement>(
				'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
			);
			const firstElement = focusableElements[0];
			const lastElement = focusableElements[focusableElements.length - 1];

			if (e.shiftKey && document.activeElement === firstElement) {
				e.preventDefault();
				lastElement?.focus();
			} else if (!e.shiftKey && document.activeElement === lastElement) {
				e.preventDefault();
				firstElement?.focus();
			}
		}
	}

	// Close modal
	function close() {
		onclose?.();
	}

	// Lock body scroll when modal opens (only in browser) and manage focus
	$effect(() => {
		if (browser) {
			if (open) {
				previousActiveElement = document.activeElement;
				document.body.style.overflow = 'hidden';
				// Focus first focusable element in modal after a short delay
				setTimeout(() => {
					if (modalElement) {
						const firstFocusable = modalElement.querySelector<HTMLElement>(
							'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
						);
						firstFocusable?.focus();
					}
				}, 50);
			} else {
				document.body.style.overflow = '';
				if (previousActiveElement instanceof HTMLElement) {
					previousActiveElement.focus();
				}
			}
		}
	});

	onDestroy(() => {
		if (browser) {
			document.body.style.overflow = '';
		}
	});
</script>

{#if open}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 z-modal-backdrop bg-black/50 backdrop-blur-sm transition-opacity duration-300"
		onclick={closable ? close : undefined}
		aria-hidden="true"
	></div>

	<!-- Modal -->
	<div
		class="fixed inset-0 z-modal flex items-center justify-center p-4"
		onkeydown={handleKeydown}
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
						onclick={close}
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
				{@render children?.()}
			</div>

			<!-- Footer (optional) -->
			{#if footer}
				<div class="px-6 py-4 border-t border-neutral-200 dark:border-neutral-700">
					{@render footer()}
				</div>
			{/if}
		</div>
	</div>
{/if}
