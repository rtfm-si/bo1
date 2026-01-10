<script lang="ts">
	/**
	 * DataQualityNotice - Actionable data quality issues display
	 *
	 * Shows data quality issues with actions to fix, ignore, or analyze anyway.
	 * Designed to be helpful without blocking the analysis flow.
	 */
	import type { DataQualityIssue, DatasetFixResponse } from '$lib/api/types';
	import { apiClient } from '$lib/api/client';

	interface Props {
		datasetId: string;
		issues: DataQualityIssue[];
		onFixed?: (result: DatasetFixResponse) => void;
		onIgnore?: () => void;
		onAnalyzeAnyway?: () => void;
	}

	let { datasetId, issues, onFixed, onIgnore, onAnalyzeAnyway }: Props = $props();

	let expanded = $state(issues.length <= 3);
	let fixing = $state(false);
	let fixingIssue = $state<DataQualityIssue | null>(null);
	let fixError = $state<string | null>(null);
	let fixResult = $state<DatasetFixResponse | null>(null);

	function getSeverityColor(severity: string): string {
		switch (severity) {
			case 'high':
				return 'text-error-600 dark:text-error-400';
			case 'medium':
				return 'text-warning-600 dark:text-warning-400';
			case 'low':
				return 'text-neutral-500 dark:text-neutral-400';
			default:
				return 'text-neutral-500 dark:text-neutral-400';
		}
	}

	function getSeverityBg(severity: string): string {
		switch (severity) {
			case 'high':
				return 'bg-error-100 dark:bg-error-900/30';
			case 'medium':
				return 'bg-warning-100 dark:bg-warning-900/30';
			case 'low':
				return 'bg-neutral-100 dark:bg-neutral-700';
			default:
				return 'bg-neutral-100 dark:bg-neutral-700';
		}
	}

	function getSeverityIcon(severity: string): string {
		switch (severity) {
			case 'high':
				return 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z';
			case 'medium':
				return 'M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z';
			case 'low':
				return 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z';
			default:
				return 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z';
		}
	}

	/**
	 * Get the fix action label for an issue type
	 */
	function getFixLabel(issue: DataQualityIssue): string {
		if (issue.fix_label) return issue.fix_label;

		// Default labels based on issue type
		switch (issue.issue_type) {
			case 'missing_values':
			case 'null_values':
				return 'Fill or Remove';
			case 'duplicates':
			case 'duplicate_rows':
				return 'Remove Duplicates';
			case 'whitespace':
			case 'leading_trailing_whitespace':
				return 'Trim';
			case 'outliers':
				return 'Review';
			default:
				return 'Fix';
		}
	}

	/**
	 * Check if an issue has a quick fix available
	 */
	function hasQuickFix(issue: DataQualityIssue): boolean {
		return !!issue.suggested_action ||
			['duplicates', 'duplicate_rows', 'whitespace', 'leading_trailing_whitespace'].includes(issue.issue_type);
	}

	/**
	 * Handle fixing a single issue
	 */
	async function handleFix(issue: DataQualityIssue) {
		fixing = true;
		fixingIssue = issue;
		fixError = null;

		try {
			// Determine action and config from issue
			let action = issue.suggested_action;
			let config = issue.action_config || {};

			// Infer action from issue type if not explicitly set
			if (!action) {
				switch (issue.issue_type) {
					case 'duplicates':
					case 'duplicate_rows':
						action = 'remove_duplicates';
						config = { keep: 'first' };
						break;
					case 'whitespace':
					case 'leading_trailing_whitespace':
						action = 'trim_whitespace';
						break;
					case 'missing_values':
					case 'null_values':
						// Default to removing null rows for the affected column
						action = 'remove_nulls';
						config = { columns: [issue.column], how: 'any' };
						break;
					default:
						fixError = 'No automatic fix available for this issue type';
						fixing = false;
						fixingIssue = null;
						return;
				}
			}

			const result = await apiClient.fixDataset(datasetId, action, config);
			fixResult = result;

			if (result.success && onFixed) {
				onFixed(result);
			}
		} catch (e) {
			fixError = e instanceof Error ? e.message : 'Failed to apply fix';
		} finally {
			fixing = false;
			fixingIssue = null;
		}
	}

	/**
	 * Trigger re-analysis after a fix
	 */
	function triggerReanalysis() {
		if (fixResult && onFixed) {
			onFixed(fixResult);
		}
		fixResult = null;
	}

	/**
	 * Dismiss the fix result
	 */
	function dismissFixResult() {
		fixResult = null;
	}

	const highSeverityCount = $derived(issues.filter((i) => i.severity === 'high').length);
	const displayedIssues = $derived(expanded ? issues : issues.slice(0, 3));
</script>

{#if fixResult}
	<!-- Fix Result -->
	<div class="bg-success-50 dark:bg-success-900/20 rounded-lg border border-success-200 dark:border-success-800 p-4">
		<div class="flex items-start gap-3">
			<div class="p-1.5 rounded-lg bg-success-100 dark:bg-success-900/40">
				<svg class="w-5 h-5 text-success-600 dark:text-success-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
				</svg>
			</div>
			<div class="flex-1">
				<h4 class="text-sm font-semibold text-success-800 dark:text-success-200">
					Fix Applied Successfully
				</h4>
				<p class="text-xs text-success-700 dark:text-success-300 mt-1">
					{fixResult.message}
				</p>
				<p class="text-xs text-success-600 dark:text-success-400 mt-1">
					{fixResult.rows_affected} rows affected. New total: {fixResult.new_row_count} rows
				</p>
			</div>
		</div>

		<div class="flex items-center gap-2 mt-4 pt-3 border-t border-success-200 dark:border-success-700">
			{#if fixResult.reanalysis_required}
				<button
					onclick={triggerReanalysis}
					class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-success-600 text-white hover:bg-success-700 transition-colors"
				>
					<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
					</svg>
					Re-analyze Data
				</button>
			{/if}
			<button
				onclick={dismissFixResult}
				class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md text-success-600 dark:text-success-400 hover:bg-success-100 dark:hover:bg-success-900/30 transition-colors"
			>
				Dismiss
			</button>
		</div>
	</div>
{:else if issues.length > 0}
	<div class="bg-warning-50 dark:bg-warning-900/20 rounded-lg border border-warning-200 dark:border-warning-800 p-4">
		<!-- Header -->
		<div class="flex items-start gap-3 mb-3">
			<div class="p-1.5 rounded-lg bg-warning-100 dark:bg-warning-900/40">
				<svg class="w-5 h-5 text-warning-600 dark:text-warning-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
				</svg>
			</div>
			<div class="flex-1">
				<h4 class="text-sm font-semibold text-warning-800 dark:text-warning-200">
					Data Quality Notice
				</h4>
				<p class="text-xs text-warning-700 dark:text-warning-300">
					{issues.length} issue{issues.length !== 1 ? 's' : ''} detected
					{#if highSeverityCount > 0}
						<span class="text-error-600 dark:text-error-400">({highSeverityCount} high severity)</span>
					{/if}
				</p>
			</div>
		</div>

		<!-- Error message -->
		{#if fixError}
			<div class="mb-3 p-2 rounded-md bg-error-100 dark:bg-error-900/30 text-xs text-error-700 dark:text-error-300">
				{fixError}
			</div>
		{/if}

		<!-- Issues list -->
		<div class="space-y-2 mb-4">
			{#each displayedIssues as issue}
				<div class="flex items-start gap-2 p-2 rounded-md {getSeverityBg(issue.severity)}">
					<svg class="w-4 h-4 mt-0.5 flex-shrink-0 {getSeverityColor(issue.severity)}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={getSeverityIcon(issue.severity)} />
					</svg>
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2">
							<span class="text-sm font-medium text-neutral-800 dark:text-neutral-200">{issue.column}</span>
							<span class="text-xs px-1.5 py-0.5 rounded bg-neutral-200 dark:bg-neutral-600 text-neutral-600 dark:text-neutral-300">
								{issue.issue_type}
							</span>
							{#if issue.affected_rows}
								<span class="text-xs text-neutral-500 dark:text-neutral-400">
									({issue.affected_rows} rows)
								</span>
							{/if}
						</div>
						<p class="text-xs text-neutral-600 dark:text-neutral-400 mt-0.5">{issue.description}</p>
						{#if issue.examples && issue.examples.length > 0}
							<p class="text-xs text-neutral-500 dark:text-neutral-500 mt-1 italic">
								Examples: {issue.examples.slice(0, 3).join(', ')}
							</p>
						{/if}
					</div>
					{#if hasQuickFix(issue)}
						<button
							onclick={() => handleFix(issue)}
							disabled={fixing}
							class="flex-shrink-0 text-xs px-2 py-1 rounded bg-white dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
						>
							{#if fixing && fixingIssue === issue}
								<span class="inline-flex items-center gap-1">
									<svg class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
										<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
										<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
									</svg>
									Fixing...
								</span>
							{:else}
								{getFixLabel(issue)}
							{/if}
						</button>
					{/if}
				</div>
			{/each}
		</div>

		<!-- Expand/collapse -->
		{#if issues.length > 3}
			<button
				onclick={() => (expanded = !expanded)}
				class="text-xs text-warning-700 dark:text-warning-300 hover:underline mb-3"
			>
				{expanded ? 'Show less' : `Show ${issues.length - 3} more issues`}
			</button>
		{/if}

		<!-- Actions -->
		<div class="flex items-center gap-2 pt-3 border-t border-warning-200 dark:border-warning-700">
			{#if onAnalyzeAnyway}
				<button
					onclick={onAnalyzeAnyway}
					disabled={fixing}
					class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-warning-600 text-white hover:bg-warning-700 transition-colors disabled:opacity-50"
				>
					<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
					</svg>
					Analyze Anyway
				</button>
			{/if}
			{#if onIgnore}
				<button
					onclick={onIgnore}
					disabled={fixing}
					class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md text-warning-600 dark:text-warning-400 hover:bg-warning-100 dark:hover:bg-warning-900/30 transition-colors disabled:opacity-50"
				>
					Ignore Issues
				</button>
			{/if}
		</div>
	</div>
{/if}
