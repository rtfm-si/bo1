<script lang="ts">
	/**
	 * AnalyseTab - Deep analysis with KeyInsightsPanel and column profiles
	 */
	import type { DatasetDetailResponse, DatasetInvestigation } from '$lib/api/types';
	import KeyInsightsPanel from '../KeyInsightsPanel.svelte';
	import ColumnProfilesTable from '../ColumnProfilesTable.svelte';

	// Use the profiles type from DatasetDetailResponse to match what's passed from the page
	type ProfileType = NonNullable<DatasetDetailResponse['profiles']>[number];

	interface Props {
		dataset: DatasetDetailResponse;
		investigation: DatasetInvestigation | null;
		investigationLoading: boolean;
		investigationError: string | null;
		profiles: ProfileType[];
		isProfiling: boolean;
		profileError: string | null;
		onRefreshInvestigation: () => void;
		onProfile: () => void;
		onUpdateColumnRole: (columnName: string, newRole: string) => Promise<void>;
	}

	let {
		dataset,
		investigation,
		investigationLoading,
		investigationError,
		profiles,
		isProfiling,
		profileError,
		onRefreshInvestigation,
		onProfile,
		onUpdateColumnRole
	}: Props = $props();
</script>

<div class="space-y-6">
	<!-- Key Insights Panel - 8 deterministic analyses -->
	<KeyInsightsPanel
		{investigation}
		loading={investigationLoading}
		error={investigationError}
		onRefresh={onRefreshInvestigation}
		{onUpdateColumnRole}
	/>

	<!-- Column Profiles Table -->
	<ColumnProfilesTable
		{profiles}
		{isProfiling}
		{profileError}
		{onProfile}
	/>
</div>
