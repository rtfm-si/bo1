<script lang="ts">
	/**
	 * ClarifyTab - Business context form with guidance
	 */
	import type { DatasetBusinessContext } from '$lib/api/types';
	import BusinessContextForm from '../BusinessContextForm.svelte';

	interface Props {
		context: DatasetBusinessContext | null;
		loading: boolean;
		saving: boolean;
		onSave: (context: DatasetBusinessContext) => void;
	}

	let { context, loading, saving, onSave }: Props = $props();
</script>

<div class="space-y-6">
	<!-- Guidance text -->
	<div class="bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800 rounded-lg p-4">
		<div class="flex items-start gap-3">
			<svg class="w-5 h-5 text-brand-600 dark:text-brand-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
			</svg>
			<div>
				<h3 class="font-medium text-brand-900 dark:text-brand-100">Why add business context?</h3>
				<p class="text-sm text-brand-700 dark:text-brand-300 mt-1">
					Providing context about your goals and KPIs helps our AI generate more relevant insights,
					suggest meaningful charts, and focus analysis on what matters to your business.
				</p>
			</div>
		</div>
	</div>

	<!-- Business Context Form -->
	<BusinessContextForm
		{context}
		{loading}
		{saving}
		{onSave}
	/>
</div>
