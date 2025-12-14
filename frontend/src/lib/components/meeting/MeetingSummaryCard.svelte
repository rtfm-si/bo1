<script lang="ts">
	/**
	 * MeetingSummaryCard - Shareable card displaying meeting summary for social media.
	 * Fixed dimensions for consistent social preview rendering.
	 */
	import { Award, Users, Calendar } from 'lucide-svelte';

	interface Props {
		/** Meeting recommendation/decision title */
		recommendation: string;
		/** Expert consensus level (0-1) */
		consensusLevel: number;
		/** Number of experts who participated */
		expertCount: number;
		/** Meeting completion date */
		completionDate: string;
		/** Problem statement (optional) */
		problemStatement?: string;
	}

	let { recommendation, consensusLevel, expertCount, completionDate, problemStatement }: Props = $props();

	// Format date for display
	function formatDate(dateStr: string): string {
		try {
			const date = new Date(dateStr);
			return date.toLocaleDateString('en-US', {
				month: 'short',
				day: 'numeric',
				year: 'numeric'
			});
		} catch {
			return dateStr;
		}
	}

	// Get consensus label based on level
	function getConsensusLabel(level: number): string {
		if (level >= 0.9) return 'Strong Consensus';
		if (level >= 0.7) return 'Good Consensus';
		if (level >= 0.5) return 'Moderate Agreement';
		return 'Mixed Opinions';
	}

	// Get consensus color based on level
	function getConsensusColor(level: number): string {
		if (level >= 0.9) return 'text-success-600 dark:text-success-400';
		if (level >= 0.7) return 'text-brand-600 dark:text-brand-400';
		if (level >= 0.5) return 'text-warning-600 dark:text-warning-400';
		return 'text-neutral-600 dark:text-neutral-400';
	}

	// Truncate recommendation text for card
	function truncateText(text: string, maxLength: number): string {
		if (text.length <= maxLength) return text;
		return text.slice(0, maxLength - 3) + '...';
	}
</script>

<!-- Card container with fixed dimensions for social sharing (1200x630 aspect ratio scaled down) -->
<div class="w-[600px] h-[315px] bg-white dark:bg-neutral-900 rounded-xl border border-neutral-200 dark:border-neutral-700 overflow-hidden flex flex-col">
	<!-- Header with branding -->
	<div class="px-6 py-4 bg-brand-50 dark:bg-brand-900/20 border-b border-neutral-200 dark:border-neutral-700">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2">
				<div class="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
					<span class="text-white font-bold text-sm">Bo1</span>
				</div>
				<span class="text-sm font-medium text-neutral-600 dark:text-neutral-400">Board of One</span>
			</div>
			<span class="text-xs text-neutral-500 dark:text-neutral-400">Meeting Summary</span>
		</div>
	</div>

	<!-- Main content -->
	<div class="flex-1 px-6 py-5 flex flex-col">
		<!-- Problem statement (if provided) -->
		{#if problemStatement}
			<p class="text-xs text-neutral-500 dark:text-neutral-400 mb-2 line-clamp-1">
				{truncateText(problemStatement, 100)}
			</p>
		{/if}

		<!-- Recommendation -->
		<div class="flex-1 flex items-center">
			<div class="flex items-start gap-3">
				<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
					<Award class="w-5 h-5 text-brand-600 dark:text-brand-400" />
				</div>
				<div class="flex-1 min-w-0">
					<p class="text-lg font-semibold text-neutral-900 dark:text-neutral-100 leading-snug line-clamp-3">
						{truncateText(recommendation, 200)}
					</p>
				</div>
			</div>
		</div>

		<!-- Metrics row -->
		<div class="flex items-center justify-between pt-4 border-t border-neutral-100 dark:border-neutral-800 mt-auto">
			<!-- Consensus -->
			<div class="flex items-center gap-2">
				<div class="w-16 h-2 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
					<div
						class="h-full bg-brand-500 rounded-full transition-all"
						style="width: {Math.round(consensusLevel * 100)}%"
					></div>
				</div>
				<span class={`text-sm font-medium ${getConsensusColor(consensusLevel)}`}>
					{getConsensusLabel(consensusLevel)}
				</span>
			</div>

			<!-- Expert count -->
			<div class="flex items-center gap-1.5 text-neutral-600 dark:text-neutral-400">
				<Users class="w-4 h-4" />
				<span class="text-sm">{expertCount} experts</span>
			</div>

			<!-- Date -->
			<div class="flex items-center gap-1.5 text-neutral-600 dark:text-neutral-400">
				<Calendar class="w-4 h-4" />
				<span class="text-sm">{formatDate(completionDate)}</span>
			</div>
		</div>
	</div>
</div>
