<script lang="ts">
	/**
	 * CancellationModal - Modal for capturing cancellation reason
	 * Prompts user for "what went wrong" when cancelling an action
	 */

	import { XCircle, Loader2, X } from 'lucide-svelte';
	import Button from '$lib/components/ui/Button.svelte';

	interface Props {
		open?: boolean;
		actionTitle?: string;
		isSubmitting?: boolean;
		error?: string | null;
		oncancel?: () => void;
		onsubmit?: (reason: string, category: FailureReasonCategory) => void;
	}

	type FailureReasonCategory = 'blocker' | 'scope_creep' | 'dependency' | 'unknown';

	let {
		open = $bindable(false),
		actionTitle = '',
		isSubmitting = false,
		error = null,
		oncancel,
		onsubmit
	}: Props = $props();

	let reason = $state('');

	function categorizeFailureReason(text: string): FailureReasonCategory {
		const lowerText = text.toLowerCase();

		if (/\b(blocker|blocked|blocking|stuck)\b/.test(lowerText)) {
			return 'blocker';
		}
		if (/\b(scope|expanded|change|changed|scope creep|grow|growing)\b/.test(lowerText)) {
			return 'scope_creep';
		}
		if (/\b(depend|wait|waiting|waiting for|relies on|blocking)\b/.test(lowerText)) {
			return 'dependency';
		}
		return 'unknown';
	}

	function handleClose() {
		if (!isSubmitting) {
			reason = '';
			oncancel?.();
		}
	}

	function handleSubmit() {
		if (reason.trim() && onsubmit) {
			const category = categorizeFailureReason(reason.trim());
			onsubmit(reason.trim(), category);
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && !isSubmitting) {
			handleClose();
		}
		if (e.key === 'Enter' && e.ctrlKey && reason.trim()) {
			handleSubmit();
		}
	}
</script>

{#if open}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="fixed inset-0 z-50 flex items-center justify-center" onkeydown={handleKeydown}>
		<!-- Backdrop -->
		<button
			type="button"
			class="absolute inset-0 bg-black/50 backdrop-blur-sm"
			onclick={handleClose}
			disabled={isSubmitting}
			aria-label="Close modal"
		></button>

		<!-- Modal Content -->
		<div
			class="relative bg-white dark:bg-neutral-900 rounded-xl shadow-xl max-w-lg w-full mx-4 overflow-hidden"
			role="dialog"
			aria-modal="true"
			aria-labelledby="cancellation-modal-title"
		>
			<!-- Header -->
			<div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
				<div class="flex items-center gap-3">
					<div class="p-2 rounded-lg bg-neutral-100 dark:bg-neutral-800">
						<XCircle class="w-5 h-5 text-neutral-600 dark:text-neutral-400" />
					</div>
					<div>
						<h3 id="cancellation-modal-title" class="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
							Cancel Action
						</h3>
						<p class="text-sm text-neutral-500 dark:text-neutral-400">What went wrong?</p>
					</div>
				</div>
				<button
					onclick={handleClose}
					disabled={isSubmitting}
					class="p-2 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors disabled:opacity-50"
					aria-label="Close"
				>
					<X class="w-5 h-5 text-neutral-500" />
				</button>
			</div>

			<!-- Body -->
			<div class="px-6 py-4">
				{#if actionTitle}
					<div class="mb-4 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800/50">
						<div class="text-sm font-medium text-neutral-900 dark:text-neutral-100">{actionTitle}</div>
					</div>
				{/if}

				<label class="block">
					<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5 block">
						Reason for cancellation <span class="text-error-500">*</span>
					</span>
					<textarea
						bind:value={reason}
						placeholder="Explain why this action is being cancelled (e.g., no longer relevant, blocked by external factors, superseded by another approach...)"
						rows="4"
						disabled={isSubmitting}
						class="w-full px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none disabled:opacity-50"
					></textarea>
					<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1.5">
						This helps track why actions weren't completed and improves future planning.
					</p>
				</label>

				{#if error}
					<div class="mt-4 p-3 rounded-lg bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800">
						<p class="text-sm text-error-700 dark:text-error-300">{error}</p>
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div class="flex items-center justify-end gap-3 px-6 py-4 bg-neutral-50 dark:bg-neutral-800/50">
				<Button variant="ghost" onclick={handleClose} disabled={isSubmitting}>
					Keep Action
				</Button>
				<Button
					variant="secondary"
					onclick={handleSubmit}
					disabled={isSubmitting || !reason.trim()}
				>
					{#if isSubmitting}
						<Loader2 class="w-4 h-4 mr-2 animate-spin" />
						Cancelling...
					{:else}
						<XCircle class="w-4 h-4 mr-2" />
						Cancel Action
					{/if}
				</Button>
			</div>
		</div>
	</div>
{/if}
