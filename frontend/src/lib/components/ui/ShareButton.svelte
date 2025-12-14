<script lang="ts">
	/**
	 * ShareButton - Social media share button with dropdown menu.
	 * Supports Twitter/X, LinkedIn, copy to clipboard, and image download.
	 */
	import { Share2, Twitter, Linkedin, Copy, Download, Check } from 'lucide-svelte';
	import { clickOutside } from '$lib/utils/clickOutside';
	import {
		generateShareText,
		getTwitterShareUrl,
		getLinkedInShareUrl,
		openSharePopup,
		copyToClipboard,
		type ActivityStats
	} from '$lib/utils/share-content';
	import {
		exportElementAsImage,
		downloadImage,
		shareImage,
		canShareFiles
	} from '$lib/utils/canvas-export';

	interface Props {
		/** Element to capture as image */
		targetElement?: HTMLElement | null;
		/** Activity stats for share text */
		stats: ActivityStats;
		/** Share URL (optional) */
		shareUrl?: string;
		/** Small icon-only mode */
		compact?: boolean;
	}

	let { targetElement = null, stats, shareUrl, compact = true }: Props = $props();

	let isOpen = $state(false);
	let isExporting = $state(false);
	let copied = $state(false);

	// Generate share content
	const shareText = $derived(generateShareText(stats));

	function toggle() {
		isOpen = !isOpen;
	}

	function close() {
		isOpen = false;
	}

	async function handleTwitterShare() {
		close();
		const url = getTwitterShareUrl(shareText, shareUrl);
		openSharePopup(url, 'twitter');
	}

	async function handleLinkedInShare() {
		close();
		if (shareUrl) {
			const url = getLinkedInShareUrl(shareUrl, 'My Activity Progress', shareText);
			openSharePopup(url, 'linkedin');
		} else {
			// LinkedIn requires a URL, fall back to text copy
			await handleCopyText();
		}
	}

	async function handleCopyText() {
		close();
		const success = await copyToClipboard(shareText);
		if (success) {
			copied = true;
			setTimeout(() => (copied = false), 2000);
		}
	}

	async function handleDownloadImage() {
		if (!targetElement) return;
		close();
		isExporting = true;

		try {
			const dataUrl = await exportElementAsImage(targetElement, {
				title: 'Activity Heatmap',
				subtitle: stats.period,
				includeBranding: true
			});
			downloadImage(dataUrl, `activity-heatmap-${Date.now()}.png`);
		} catch (error) {
			console.error('Failed to export image:', error);
		} finally {
			isExporting = false;
		}
	}

	async function handleNativeShare() {
		if (!targetElement) return;
		close();
		isExporting = true;

		try {
			const dataUrl = await exportElementAsImage(targetElement, {
				title: 'Activity Heatmap',
				subtitle: stats.period,
				includeBranding: true
			});

			const shared = await shareImage(dataUrl, 'My Activity Progress', shareText);
			if (!shared) {
				// Fall back to download
				downloadImage(dataUrl, `activity-heatmap-${Date.now()}.png`);
			}
		} catch (error) {
			console.error('Failed to share:', error);
		} finally {
			isExporting = false;
		}
	}

	const canShare = $derived(canShareFiles());
</script>

<div class="relative inline-block" use:clickOutside={close}>
	<!-- Trigger button -->
	<button
		type="button"
		class="flex items-center gap-1.5 px-2 py-1 text-xs font-medium text-neutral-600 dark:text-neutral-400
			hover:text-neutral-900 dark:hover:text-neutral-100 hover:bg-neutral-100 dark:hover:bg-neutral-800
			rounded-md transition-colors disabled:opacity-50"
		onclick={toggle}
		disabled={isExporting}
		title="Share activity"
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
			class="absolute right-0 mt-1 w-44 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700
				rounded-lg shadow-lg z-dropdown overflow-hidden"
		>
			{#if canShare && targetElement}
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
					<span>Copy text</span>
				{/if}
			</button>

			{#if targetElement}
				<button
					type="button"
					class="w-full flex items-center gap-2 px-3 py-2 text-sm text-neutral-700 dark:text-neutral-300
						hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
					onclick={handleDownloadImage}
				>
					<Download class="w-4 h-4" />
					<span>Download image</span>
				</button>
			{/if}
		</div>
	{/if}
</div>
