<script lang="ts">
	/**
	 * Alert Component - shadcn-svelte wrapper with backward-compatible API
	 * Preserves icon, dismissible behavior, and variant mapping
	 */
	import { Alert as ShadcnAlert, AlertTitle, AlertDescription, type AlertVariant } from './shadcn/alert';
	import type { Snippet } from 'svelte';

	// Props matching the legacy API
	interface Props {
		variant?: 'success' | 'warning' | 'error' | 'info';
		dismissable?: boolean;
		title?: string;
		class?: string;
		children?: Snippet;
		ondismiss?: () => void;
	}

	let {
		variant = 'info',
		dismissable = false,
		title,
		class: className = '',
		children,
		ondismiss
	}: Props = $props();

	// Map legacy variants to shadcn + custom classes
	// shadcn only has: default, destructive
	const variantConfig: Record<string, { shadcn: AlertVariant; custom: string }> = {
		success: { shadcn: 'default', custom: 'border-success-200 bg-success-50 text-success-800 dark:border-success-800 dark:bg-success-900/20 dark:text-success-200' },
		warning: { shadcn: 'default', custom: 'border-warning-200 bg-warning-50 text-warning-800 dark:border-warning-800 dark:bg-warning-900/20 dark:text-warning-200' },
		error: { shadcn: 'destructive', custom: 'border-error-200 bg-error-50 dark:border-error-800 dark:bg-error-900/20' },
		info: { shadcn: 'default', custom: 'border-info-200 bg-info-50 text-info-800 dark:border-info-800 dark:bg-info-900/20 dark:text-info-200' },
	};

	// Icon paths for each variant
	const icons = {
		success: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
		warning: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
		error: 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z',
		info: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
	};

	const config = $derived(variantConfig[variant] ?? variantConfig.info);

	function handleDismiss() {
		ondismiss?.();
	}
</script>

<ShadcnAlert variant={config.shadcn} class="{config.custom} {className}">
	<!-- Icon -->
	<svg
		class="w-5 h-5 flex-shrink-0"
		xmlns="http://www.w3.org/2000/svg"
		fill="none"
		viewBox="0 0 24 24"
		stroke="currentColor"
	>
		<path
			stroke-linecap="round"
			stroke-linejoin="round"
			stroke-width="2"
			d={icons[variant]}
		/>
	</svg>

	{#if title}
		<AlertTitle>{title}</AlertTitle>
	{/if}

	<AlertDescription>
		<div class="flex items-start gap-3">
			<div class="flex-1">
				{@render children?.()}
			</div>

			<!-- Dismiss button -->
			{#if dismissable}
				<button
					type="button"
					class="flex-shrink-0 p-1 rounded-md hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
					onclick={handleDismiss}
					aria-label="Dismiss alert"
				>
					<svg
						class="w-4 h-4"
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			{/if}
		</div>
	</AlertDescription>
</ShadcnAlert>
