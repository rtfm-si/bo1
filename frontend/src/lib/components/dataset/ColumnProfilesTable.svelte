<script lang="ts">
	/**
	 * ColumnProfilesTable - Table showing column statistics and profile data
	 */
	import type { DatasetDetailResponse } from '$lib/api/types';
	import { Button } from '$lib/components/ui';

	// Use the profiles type from DatasetDetailResponse for compatibility
	type ProfileType = NonNullable<DatasetDetailResponse['profiles']>[number];

	interface Props {
		profiles: ProfileType[];
		isProfiling?: boolean;
		profileError?: string | null;
		onProfile?: () => void;
	}

	let { profiles, isProfiling = false, profileError = null, onProfile }: Props = $props();

	function formatValue(value: unknown): string {
		if (value === null || value === undefined) return '—';
		if (typeof value === 'number') {
			return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2);
		}
		return String(value);
	}

	function getTypeColor(type: string): string {
		switch (type.toLowerCase()) {
			case 'integer':
			case 'float':
			case 'numeric':
				return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300';
			case 'string':
			case 'text':
				return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300';
			case 'date':
			case 'datetime':
			case 'timestamp':
				return 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300';
			case 'boolean':
				return 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300';
			case 'currency':
				return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300';
			case 'percentage':
				return 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300';
			default:
				return 'bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-300';
		}
	}
</script>

<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
	<div class="flex items-center justify-between mb-4">
		<h2 class="text-lg font-semibold text-neutral-900 dark:text-white flex items-center gap-2">
			<svg class="w-5 h-5 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
			</svg>
			Column Profiles
		</h2>
		{#if profiles.length === 0 && onProfile}
			<Button variant="brand" size="md" onclick={onProfile} disabled={isProfiling}>
				{#snippet children()}
					{#if isProfiling}
						<svg class="w-4 h-4 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
						Generating...
					{:else}
						Generate Profile
					{/if}
				{/snippet}
			</Button>
		{/if}
	</div>

	{#if profileError}
		<div class="mb-4 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-4">
			<p class="text-sm text-error-700 dark:text-error-300">{profileError}</p>
		</div>
	{/if}

	{#if profiles.length === 0}
		<div class="text-center py-8">
			<svg class="w-12 h-12 mx-auto text-neutral-400 dark:text-neutral-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
			</svg>
			<p class="text-neutral-600 dark:text-neutral-400">
				No profile data yet. Click "Generate Profile" to analyze this dataset.
			</p>
		</div>
	{:else}
		<div class="overflow-x-auto">
			<table class="w-full text-sm">
				<thead>
					<tr class="border-b border-neutral-200 dark:border-neutral-700">
						<th class="text-left py-3 px-4 font-medium text-neutral-600 dark:text-neutral-400">Column</th>
						<th class="text-left py-3 px-4 font-medium text-neutral-600 dark:text-neutral-400">Type</th>
						<th class="text-right py-3 px-4 font-medium text-neutral-600 dark:text-neutral-400">Nulls</th>
						<th class="text-right py-3 px-4 font-medium text-neutral-600 dark:text-neutral-400">Unique</th>
						<th class="text-right py-3 px-4 font-medium text-neutral-600 dark:text-neutral-400">Min</th>
						<th class="text-right py-3 px-4 font-medium text-neutral-600 dark:text-neutral-400">Max</th>
						<th class="text-right py-3 px-4 font-medium text-neutral-600 dark:text-neutral-400">Mean</th>
					</tr>
				</thead>
				<tbody>
					{#each profiles as profile (profile.id)}
						<tr class="border-b border-neutral-100 dark:border-neutral-700/50 hover:bg-neutral-50 dark:hover:bg-neutral-700/30">
							<td class="py-3 px-4 font-medium text-neutral-900 dark:text-white">
								{profile.column_name}
							</td>
							<td class="py-3 px-4">
								<span class="px-2 py-1 text-xs font-medium rounded {getTypeColor(profile.data_type)}">
									{profile.data_type}
								</span>
							</td>
							<td class="py-3 px-4 text-right text-neutral-600 dark:text-neutral-400">
								{formatValue(profile.null_count)}
							</td>
							<td class="py-3 px-4 text-right text-neutral-600 dark:text-neutral-400">
								{formatValue(profile.unique_count)}
							</td>
							<td class="py-3 px-4 text-right text-neutral-600 dark:text-neutral-400">
								{formatValue(profile.min_value)}
							</td>
							<td class="py-3 px-4 text-right text-neutral-600 dark:text-neutral-400">
								{formatValue(profile.max_value)}
							</td>
							<td class="py-3 px-4 text-right text-neutral-600 dark:text-neutral-400">
								{formatValue(profile.mean_value)}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
