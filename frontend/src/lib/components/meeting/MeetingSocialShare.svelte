<script lang="ts">
	/**
	 * MeetingSocialShare - Social media share button with dropdown for meeting summaries.
	 * Generates branded cards for Twitter/LinkedIn sharing.
	 */
	import { Share2, Twitter, Linkedin, Copy, Download, Check, Link } from 'lucide-svelte';
	import { clickOutside } from '$lib/utils/clickOutside';
	import {
		generateMeetingShareText,
		getTwitterShareUrl,
		getLinkedInShareUrl,
		openSharePopup,
		copyToClipboard,
		type MeetingSummaryShareData
	} from '$lib/utils/share-content';
	import {
		exportMeetingSummary,
		downloadImage,
		shareImage,
		canShareFiles,
		type MeetingSummaryData
	} from '$lib/utils/canvas-export';

	interface Props {
		/** Meeting summary data */
		summary: MeetingSummaryData;
		/** Share URL (for private share links) */
		shareUrl?: string;
		/** Small icon-only mode */
		compact?: boolean;
		/** Callback when share link is clicked */
		onShareLinkClick?: () => void;
	}

	let { summary, shareUrl, compact = true, onShareLinkClick }: Props = $props();

	let isOpen = $state(false);
	let isExporting = $state(false);
	let copied = $state(false);

	// Convert summary data to share text format
	const shareData: MeetingSummaryShareData = $derived({
		recommendation: summary.recommendation,
		consensusLevel: summary.consensusLevel,
		expertCount: summary.expertCount,
		problemStatement: summary.problemStatement
	});

	function toggle() {
		isOpen = !isOpen;
	}

	function close() {
		isOpen = false;
	}

	async function handleTwitterShare() {
		close();
		const text = generateMeetingShareText(shareData, 'twitter');
		const url = getTwitterShareUrl(text, shareUrl);
		openSharePopup(url, 'twitter');
	}

	async function handleLinkedInShare() {
		close();
		if (shareUrl) {
			const text = generateMeetingShareText(shareData, 'linkedin');
			const url = getLinkedInShareUrl(shareUrl, 'Meeting Summary', text);
			openSharePopup(url, 'linkedin');
		} else {
			// LinkedIn requires a URL, fall back to text copy
			await handleCopyText();
		}
	}

	async function handleCopyText() {
		close();
		const text = generateMeetingShareText(shareData, 'generic');
		const success = await copyToClipboard(text);
		if (success) {
			copied = true;
			setTimeout(() => (copied = false), 2000);
		}
	}

	async function handleDownloadImage() {
		close();
		isExporting = true;

		try {
			const dataUrl = await exportMeetingSummary(summary);
			downloadImage(dataUrl, `meeting-summary-${Date.now()}.png`);
		} catch (error) {
			console.error('Failed to export image:', error);
		} finally {
			isExporting = false;
		}
	}

	async function handleNativeShare() {
		close();
		isExporting = true;

		try {
			const dataUrl = await exportMeetingSummary(summary);
			const text = generateMeetingShareText(shareData, 'generic');
			const shared = await shareImage(dataUrl, 'Meeting Summary', text, 'meeting-summary.png');
			if (!shared) {
				// Fall back to download
				downloadImage(dataUrl, `meeting-summary-${Date.now()}.png`);
			}
		} catch (error) {
			console.error('Failed to share:', error);
		} finally {
			isExporting = false;
		}
	}

	function handleShareLinkClick() {
		close();
		onShareLinkClick?.();
	}

	const canShare = $derived(canShareFiles());
</script>

<div class="relative inline-block" use:clickOutside={close}>
	<!-- Trigger button -->
	<button
		type="button"
		class="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-neutral-700 dark:text-neutral-300
			hover:text-neutral-900 dark:hover:text-neutral-100 hover:bg-neutral-100 dark:hover:bg-neutral-800
			rounded-lg transition-colors disabled:opacity-50 border border-neutral-200 dark:border-neutral-700"
		onclick={toggle}
		disabled={isExporting}
		title="Share meeting"
	>
		{#if isExporting}
			<svg class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
				<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" opacity="0.25"></circle>
				<path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
			</svg>
		{:else}
			<Share2 class="w-4 h-4" />
		{/if}
		{#if !compact}
			<span>Share</span>
		{/if}
	</button>

	<!-- Dropdown menu -->
	{#if isOpen}
		<div
			class="absolute right-0 mt-1 w-52 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700
				rounded-lg shadow-lg z-dropdown overflow-hidden"
		>
			<!-- Share Link (opens modal) -->
			{#if onShareLinkClick}
				<button
					type="button"
					class="w-full flex items-center gap-2 px-3 py-2 text-sm text-neutral-700 dark:text-neutral-300
						hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
					onclick={handleShareLinkClick}
				>
					<Link class="w-4 h-4" />
					<span>Create Share Link</span>
				</button>
				<div class="border-t border-neutral-100 dark:border-neutral-700"></div>
			{/if}

			<!-- Native share (mobile) -->
			{#if canShare}
				<button
					type="button"
					class="w-full flex items-center gap-2 px-3 py-2 text-sm text-neutral-700 dark:text-neutral-300
						hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
					onclick={handleNativeShare}
				>
					<Share2 class="w-4 h-4" />
					<span>Share...</span>
				</button>
				<div class="border-t border-neutral-100 dark:border-neutral-700"></div>
			{/if}

			<!-- Social platforms -->
			<button
				type="button"
				class="w-full flex items-center gap-2 px-3 py-2 text-sm text-neutral-700 dark:text-neutral-300
					hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
				onclick={handleTwitterShare}
			>
				<Twitter class="w-4 h-4" />
				<span>Post to X</span>
			</button>

			<button
				type="button"
				class="w-full flex items-center gap-2 px-3 py-2 text-sm text-neutral-700 dark:text-neutral-300
					hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
				onclick={handleLinkedInShare}
			>
				<Linkedin class="w-4 h-4" />
				<span>Share on LinkedIn</span>
			</button>

			<div class="border-t border-neutral-100 dark:border-neutral-700"></div>

			<!-- Copy & Download -->
			<button
				type="button"
				class="w-full flex items-center gap-2 px-3 py-2 text-sm text-neutral-700 dark:text-neutral-300
					hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
				onclick={handleCopyText}
			>
				{#if copied}
					<Check class="w-4 h-4 text-success-500" />
					<span class="text-success-600 dark:text-success-400">Copied!</span>
				{:else}
					<Copy class="w-4 h-4" />
					<span>Copy summary text</span>
				{/if}
			</button>

			<button
				type="button"
				class="w-full flex items-center gap-2 px-3 py-2 text-sm text-neutral-700 dark:text-neutral-300
					hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
				onclick={handleDownloadImage}
			>
				<Download class="w-4 h-4" />
				<span>Download card image</span>
			</button>
		</div>
	{/if}
</div>
