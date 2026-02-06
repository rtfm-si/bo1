<script lang="ts">
	import { Pause, Play, CheckCircle, Download, Share2, ChevronDown, FileJson, FileText, StopCircle, AlertTriangle } from 'lucide-svelte';
	import { Button } from '$lib/components/ui';
	import { apiClient } from '$lib/api/client';
	import TerminationModal from './TerminationModal.svelte';

	interface Props {
		sessionId: string;
		sessionStatus: string | undefined;
		isSynthesisComplete?: boolean;
		onPause: () => Promise<void>;
		onResume: () => Promise<void>;
		onShareClick?: () => void;
		onTerminated?: (result: {
			termination_type: string;
			billable_portion: number;
			completed_sub_problems: number;
			total_sub_problems: number;
		}) => void;
	}

	let { sessionId, sessionStatus, isSynthesisComplete = false, onPause, onResume, onShareClick, onTerminated }: Props = $props();

	// Local completion: API says 'completed' OR synthesis events arrived before API catches up
	const isComplete = $derived(sessionStatus === 'completed' || isSynthesisComplete);
	const isTerminated = $derived(sessionStatus === 'terminated');
	const isPaused = $derived(sessionStatus === 'paused');
	const isActive = $derived(!isComplete && !isTerminated && (sessionStatus === 'active' || sessionStatus === 'paused'));

	// Export dropdown state
	let exportDropdownOpen = $state(false);
	let isExporting = $state<'json' | 'markdown' | null>(null);

	// Termination modal state
	let terminationModalOpen = $state(false);

	async function handleExport(format: 'json' | 'markdown') {
		isExporting = format;
		exportDropdownOpen = false;

		try {
			const blob = await apiClient.exportSession(sessionId, format);
			const url = window.URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `meeting_${sessionId}_${new Date().toISOString().split('T')[0]}.${format === 'json' ? 'json' : 'md'}`;
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			window.URL.revokeObjectURL(url);
		} catch (err) {
			console.error('Export failed:', err);
			alert('Export failed. Please try again.');
		} finally {
			isExporting = null;
		}
	}

	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('.export-dropdown')) {
			exportDropdownOpen = false;
		}
	}

	function handleTerminated(result: {
		termination_type: string;
		billable_portion: number;
		completed_sub_problems: number;
		total_sub_problems: number;
	}) {
		onTerminated?.(result);
	}
</script>

<svelte:window onclick={handleClickOutside} />

<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700 sticky top-0 z-10">
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-4">
				<a
					href="/dashboard"
					class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors duration-200"
					aria-label="Back to dashboard"
				>
					<svg class="w-5 h-5 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
					</svg>
				</a>
				<div class="flex-1 flex items-center gap-3">
					<h1 class="text-[1.875rem] font-semibold leading-tight text-neutral-900 dark:text-white">
						{#if isComplete}
							Meeting Complete
						{:else if isTerminated}
							Meeting Ended Early
						{:else if isPaused}
							Action Required
						{:else}
							Meeting in Progress
						{/if}
					</h1>
					{#if isComplete}
						<CheckCircle class="w-6 h-6 text-success-600 dark:text-success-400" />
					{:else if isTerminated}
						<AlertTriangle class="w-6 h-6 text-warning-600 dark:text-warning-400" />
					{:else if isPaused}
						<AlertTriangle class="w-6 h-6 text-warning-600 dark:text-warning-400" />
					{/if}
				</div>
			</div>

			<div class="flex items-center gap-2">
				{#if sessionStatus === 'active'}
					<Button variant="secondary" size="md" onclick={onPause}>
						{#snippet children()}
							<Pause size={16} />
							<span>Pause</span>
						{/snippet}
					</Button>
				{:else if sessionStatus === 'paused'}
					<Button variant="brand" size="md" onclick={onResume}>
						{#snippet children()}
							<Play size={16} />
							<span>Resume</span>
						{/snippet}
					</Button>
				{/if}

				<!-- End Early button (visible during active deliberation) -->
				{#if isActive}
					<Button variant="secondary" size="md" onclick={() => (terminationModalOpen = true)}>
						{#snippet children()}
							<StopCircle size={16} />
							<span>End Early</span>
						{/snippet}
					</Button>
				{/if}

				{#if isComplete || isTerminated}
					<!-- Export Dropdown -->
					<div class="relative export-dropdown">
						<Button
							variant="secondary"
							size="md"
							onclick={() => (exportDropdownOpen = !exportDropdownOpen)}
							disabled={isExporting !== null}
						>
							{#snippet children()}
								<Download size={16} />
								<span>{isExporting ? 'Exporting...' : 'Export'}</span>
								<ChevronDown size={14} class={exportDropdownOpen ? 'rotate-180 transition-transform' : 'transition-transform'} />
							{/snippet}
						</Button>

						{#if exportDropdownOpen}
							<div class="absolute right-0 mt-2 w-48 bg-white dark:bg-neutral-800 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-700 py-1 z-20">
								<button
									class="w-full px-4 py-2 text-left text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700 flex items-center gap-2"
									onclick={() => handleExport('json')}
								>
									<FileJson size={16} />
									Export as JSON
								</button>
								<button
									class="w-full px-4 py-2 text-left text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700 flex items-center gap-2"
									onclick={() => handleExport('markdown')}
								>
									<FileText size={16} />
									Export as Markdown
								</button>
							</div>
						{/if}
					</div>

					<!-- Share Button -->
					{#if onShareClick}
						<Button variant="brand" size="md" onclick={onShareClick}>
							{#snippet children()}
								<Share2 size={16} />
								<span>Share</span>
							{/snippet}
						</Button>
					{/if}
				{/if}
			</div>
		</div>
	</div>
</header>

<!-- Termination Modal -->
<TerminationModal
	{sessionId}
	open={terminationModalOpen}
	onClose={() => (terminationModalOpen = false)}
	onTerminated={handleTerminated}
/>
