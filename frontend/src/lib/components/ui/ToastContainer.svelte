<script lang="ts">
	/**
	 * ToastContainer Component
	 *
	 * Renders all active toasts from the toast store.
	 * Fixed position bottom-right with stacking.
	 * Include once in root layout for global toast support.
	 */

	import { toast } from '$lib/stores/toast';
	import Toast from './Toast.svelte';
</script>

{#if $toast.length > 0}
	<div
		class="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none"
		aria-live="polite"
		aria-label="Notifications"
	>
		{#each $toast as t (t.id)}
			<div class="pointer-events-auto">
				<Toast
					type={t.type}
					message={t.message}
					duration={0}
					dismissable={true}
					ondismiss={() => toast.dismissToast(t.id)}
				/>
			</div>
		{/each}
	</div>
{/if}
