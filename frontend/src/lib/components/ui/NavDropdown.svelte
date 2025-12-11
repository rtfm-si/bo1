<script lang="ts">
	/**
	 * NavDropdown Component - Hover/click-triggered navigation dropdown
	 * Used in Header for grouped navigation items
	 */
	import { page } from '$app/stores';
	import { beforeNavigate } from '$app/navigation';
	import { ChevronDown } from 'lucide-svelte';

	interface NavLink {
		href: string;
		label: string;
	}

	interface Props {
		label: string;
		links: NavLink[];
		isGroupActive?: (links: NavLink[]) => boolean;
	}

	let { label, links, isGroupActive }: Props = $props();

	let isOpen = $state(false);
	let closeTimeout: ReturnType<typeof setTimeout> | null = null;

	// Check if any child link is active
	const isActive = $derived.by(() => {
		if (isGroupActive) return isGroupActive(links);
		const pathname = $page.url.pathname;
		return links.some((link) => pathname === link.href || pathname.startsWith(link.href + '/'));
	});

	// Check if specific link is active
	function isLinkActive(href: string): boolean {
		const pathname = $page.url.pathname;
		return pathname === href || pathname.startsWith(href + '/');
	}

	function openDropdown() {
		if (closeTimeout) {
			clearTimeout(closeTimeout);
			closeTimeout = null;
		}
		isOpen = true;
	}

	function closeDropdown() {
		// Small delay to allow mouse to move to dropdown
		closeTimeout = setTimeout(() => {
			isOpen = false;
		}, 150);
	}

	function handleKeydown(e: KeyboardEvent) {
		switch (e.key) {
			case 'Enter':
			case ' ':
				isOpen = !isOpen;
				e.preventDefault();
				break;
			case 'Escape':
				isOpen = false;
				e.preventDefault();
				break;
			case 'ArrowDown':
				if (!isOpen) {
					isOpen = true;
				}
				e.preventDefault();
				break;
		}
	}

	// Close on navigation
	beforeNavigate(() => {
		isOpen = false;
	});
</script>

<div
	class="relative"
	role="navigation"
	onmouseenter={openDropdown}
	onmouseleave={closeDropdown}
>
	<!-- Trigger button -->
	<button
		type="button"
		class="flex items-center gap-1 px-1 py-2 transition-colors {isActive
			? 'text-brand-600 dark:text-brand-400 font-medium'
			: 'text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400'}"
		aria-expanded={isOpen}
		aria-haspopup="true"
		onclick={() => (isOpen = !isOpen)}
		onkeydown={handleKeydown}
	>
		{label}
		<ChevronDown
			class="w-4 h-4 transition-transform {isOpen ? 'rotate-180' : ''}"
		/>
	</button>

	<!-- Dropdown menu -->
	{#if isOpen}
		<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
		<div
			class="absolute left-0 top-full mt-1 min-w-[160px] bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-lg py-1 z-50"
			role="menu"
			tabindex="0"
			onmouseenter={openDropdown}
			onmouseleave={closeDropdown}
		>
			{#each links as link (link.href)}
				<a
					href={link.href}
					class="block px-4 py-2 text-sm transition-colors {isLinkActive(link.href)
						? 'text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/20 font-medium'
						: 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700'}"
					role="menuitem"
				>
					{link.label}
				</a>
			{/each}
		</div>
	{/if}
</div>
