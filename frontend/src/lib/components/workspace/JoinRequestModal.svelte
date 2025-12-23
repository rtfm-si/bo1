<script lang="ts">
	/**
	 * JoinRequestModal - Request to join a workspace
	 *
	 * Allows users to submit a join request with an optional message
	 * when a workspace has request_to_join discoverability enabled.
	 */
	import { X, Send, AlertCircle } from 'lucide-svelte';
	import { Button } from '$lib/components/ui';
	import { apiClient } from '$lib/api/client';

	interface Props {
		workspaceId: string;
		workspaceName: string;
		open?: boolean;
		onclose?: () => void;
		onsuccess?: () => void;
	}

	let { workspaceId, workspaceName, open = $bindable(false), onclose, onsuccess }: Props = $props();

	// State
	let message = $state('');
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);

	// Handle form submission
	async function handleSubmit(e: Event) {
		e.preventDefault();
		if (isSubmitting) return;

		isSubmitting = true;
		error = null;

		try {
			await apiClient.submitJoinRequest(workspaceId, message.trim() || undefined);
			open = false;
			onsuccess?.();
		} catch (err: unknown) {
			console.error('Failed to submit join request:', err);
			if (err instanceof Error) {
				error = err.message;
			} else {
				error = 'Failed to submit join request';
			}
		} finally {
			isSubmitting = false;
		}
	}

	// Handle close
	function handleClose() {
		open = false;
		message = '';
		error = null;
		onclose?.();
	}

	// Close on escape key
	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && open) {
			handleClose();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
		onclick={() => handleClose()}
		role="presentation"
	>
		<!-- svelte-ignore a11y_click_events_have_key_events a11y_interactive_supports_focus -->
		<!-- Modal -->
		<div
			class="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-md w-full"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			aria-labelledby="join-request-title"
			tabindex="-1"
		>
			<!-- Header -->
			<div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
				<h2 id="join-request-title" class="text-lg font-semibold text-neutral-900 dark:text-white">
					Request to Join
				</h2>
				<button
					onclick={handleClose}
					class="text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
					aria-label="Close"
				>
					<X size={20} />
				</button>
			</div>

			<!-- Content -->
			<form onsubmit={handleSubmit} class="p-6 space-y-4">
				<p class="text-sm text-neutral-600 dark:text-neutral-400">
					You're requesting to join <strong class="text-neutral-900 dark:text-white">{workspaceName}</strong>.
					The workspace admin will review your request.
				</p>

				{#if error}
					<div class="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
						<AlertCircle size={18} class="text-red-600 dark:text-red-400 shrink-0" />
						<span class="text-sm text-red-700 dark:text-red-300">{error}</span>
					</div>
				{/if}

				<div>
					<label
						for="join-message"
						class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
					>
						Message (optional)
					</label>
					<textarea
						id="join-message"
						bind:value={message}
						placeholder="Tell the admin why you'd like to join..."
						maxlength={1000}
						rows={3}
						disabled={isSubmitting}
						class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:opacity-50 resize-none"
					></textarea>
					<p class="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
						{message.length}/1000 characters
					</p>
				</div>

				<!-- Actions -->
				<div class="flex justify-end gap-3 pt-2">
					<Button variant="ghost" onclick={handleClose} disabled={isSubmitting}>
						Cancel
					</Button>
					<Button type="submit" disabled={isSubmitting}>
						{#if isSubmitting}
							Sending...
						{:else}
							<Send size={16} class="mr-1" />
							Send Request
						{/if}
					</Button>
				</div>
			</form>
		</div>
	</div>
{/if}
