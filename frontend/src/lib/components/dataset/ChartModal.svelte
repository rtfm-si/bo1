<script lang="ts">
	/**
	 * ChartModal - Fullscreen chart view modal
	 *
	 * Opens a chart in a large modal for detailed interaction
	 */
	import Modal from '$lib/components/ui/Modal.svelte';
	import ChartRenderer from './ChartRenderer.svelte';
	import type { ChartSpec } from '$lib/api/types';

	// Accept any figure_json from the API (loose type)
	type FigureJsonLike = { data?: unknown[]; layout?: Record<string, unknown>; [key: string]: unknown } | null;

	interface Props {
		open?: boolean;
		figureJson: FigureJsonLike;
		chartSpec?: ChartSpec | null;
		title?: string;
		onclose?: () => void;
	}

	let { open = $bindable(false), figureJson, chartSpec = null, title = 'Chart', onclose }: Props =
		$props();

	function handleClose() {
		open = false;
		onclose?.();
	}
</script>

<Modal bind:open title={title} size="lg" onclose={handleClose}>
	<div class="min-h-[60vh]">
		{#if figureJson}
			<ChartRenderer
				figureJson={figureJson as { data?: unknown[]; layout?: Record<string, unknown> }}
				{chartSpec}
				viewMode="detail"
				title=""
				width={800}
				height={500}
			/>
		{:else}
			<div
				class="flex items-center justify-center h-60 text-neutral-400 dark:text-neutral-500 text-sm"
			>
				No chart data available
			</div>
		{/if}
	</div>
</Modal>
