<script lang="ts">
	/**
	 * ActionSocialShare - Social media share button for completed action achievements.
	 * Generates branded achievement cards for Twitter/LinkedIn sharing.
	 */
	import { Share2, Twitter, Linkedin, Copy, Download, Check } from 'lucide-svelte';
	import { clickOutside } from '$lib/utils/clickOutside';
	import {
		generateActionShareText,
		getTwitterShareUrl,
		getLinkedInShareUrl,
		openSharePopup,
		copyToClipboard,
		type ActionAchievementShareData
	} from '$lib/utils/share-content';
	import {
		exportActionAchievement,
		downloadImage,
		shareImage,
		canShareFiles,
		type ActionAchievementData
	} from '$lib/utils/canvas-export';

	interface Props {
		/** Action achievement data */
		achievement: ActionAchievementData;
		/** Share URL (optional) */
		shareUrl?: string;
		/** Small icon-only mode */
		compact?: boolean;
	}

	let { achievement, shareUrl, compact = false }: Props = $props();

	let isOpen = $state(false);
	let isExporting = $state(false);
	let copied = $state(false);

	// Convert achievement data to share text format
	const shareData: ActionAchievementShareData = $derived({
		title: achievement.title,
		daysToComplete: achievement.daysToComplete,
		projectName: achievement.projectName
	});

	function toggle() {
		isOpen = !isOpen;
	}

	function close() {
		isOpen = false;
	}

	async function handleTwitterShare() {
		close();
		const text = generateActionShareText(shareData, 'twitter');
		const url = getTwitterShareUrl(text, shareUrl);
		openSharePopup(url, 'twitter');
	}

	async function handleLinkedInShare() {
		close();
		if (shareUrl) {
			const text = generateActionShareText(shareData, 'linkedin');
			const url = getLinkedInShareUrl(shareUrl, 'Action Completed', text);
			openSharePopup(url, 'linkedin');
		} else {
			// LinkedIn requires a URL, fall back to text copy
			await handleCopyText();
		}
	}

	async function handleCopyText() {
		close();
		const text = generateActionShareText(shareData, 'generic');
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
			const dataUrl = await exportActionAchievement(achievement);
			downloadImage(dataUrl, `action-achievement-${Date.now()}.png`);
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
			const dataUrl = await exportActionAchievement(achievement);
			const text = generateActionShareText(shareData, 'generic');
			const shared = await shareImage(dataUrl, 'Action Achievement', text, 'action-achievement.png');
			if (!shared) {
				// Fall back to download
				downloadImage(dataUrl, `action-achievement-${Date.now()}.png`);
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
		class="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-success-700 dark:text-success-300
			hover:text-success-800 dark:hover:text-success-200 bg-success-50 dark:bg-success-900/20
			hover:bg-success-100 dark:hover:bg-success-900/30
			rounded-lg transition-colors disabled:opacity-50 border border-success-200 dark:border-success-800"
		onclick={toggle}
		disabled={isExporting}
		title="Share achievement"
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
			<span>Share Achievement</span>
		{/if}
	</button>

	<!-- Dropdown menu -->
	{#if isOpen}
		<div
			class="absolute right-0 mt-1 w-52 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700
				rounded-lg shadow-lg z-dropdown overflow-hidden"
		>
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
					<span>Copy text</span>
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
