<script lang="ts">
	/**
	 * Theme Switcher Component - Dropdown for selecting theme
	 */

	import { onMount } from 'svelte';
	import { themeStore } from '$lib/stores/theme';
	import { themes, type ThemeName } from '$lib/design/themes';

	let isOpen = false;
	let currentTheme: ThemeName;

	// Subscribe to theme store
	themeStore.subscribe((theme) => {
		currentTheme = theme;
	});

	onMount(() => {
		// Initialize theme
		themeStore.initialize();

		// Close dropdown when clicking outside
		const handleClickOutside = (event: MouseEvent) => {
			const target = event.target as HTMLElement;
			if (!target.closest('.theme-switcher')) {
				isOpen = false;
			}
		};

		document.addEventListener('click', handleClickOutside);
		return () => {
			document.removeEventListener('click', handleClickOutside);
		};
	});

	function toggleDropdown() {
		isOpen = !isOpen;
	}

	function selectTheme(theme: ThemeName) {
		themeStore.setTheme(theme);
		isOpen = false;
	}

	// Theme icons
	const themeIcons: Record<ThemeName, string> = {
		light: 'M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z',
		dark: 'M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z',
		ocean: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
	};
</script>

<div class="theme-switcher relative">
	<button
		type="button"
		class="p-2 rounded-md bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 transition-colors"
		on:click={toggleDropdown}
		aria-label="Select theme"
		aria-expanded={isOpen}
		aria-haspopup="true"
	>
		<!-- Current theme icon -->
		<svg
			class="w-5 h-5 text-neutral-700 dark:text-neutral-300"
			xmlns="http://www.w3.org/2000/svg"
			fill="none"
			viewBox="0 0 24 24"
			stroke="currentColor"
		>
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				stroke-width="2"
				d={themeIcons[currentTheme]}
			/>
		</svg>
	</button>

	{#if isOpen}
		<div
			class="absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 z-dropdown"
			role="menu"
			aria-orientation="vertical"
		>
			<div class="py-1">
				{#each Object.entries(themes) as [name, theme]}
					<button
						type="button"
						class="w-full flex items-center gap-3 px-4 py-2 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors {currentTheme ===
						name
							? 'bg-neutral-50 dark:bg-neutral-900'
							: ''}"
						role="menuitem"
						on:click={() => selectTheme(name as ThemeName)}
					>
						<!-- Theme icon -->
						<svg
							class="w-5 h-5"
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d={themeIcons[name as ThemeName]}
							/>
						</svg>

						<!-- Theme name -->
						<span class="flex-1 text-left">{theme.displayName}</span>

						<!-- Current indicator -->
						{#if currentTheme === name}
							<svg
								class="w-4 h-4 text-brand-600 dark:text-brand-400"
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M5 13l4 4L19 7"
								/>
							</svg>
						{/if}
					</button>
				{/each}
			</div>
		</div>
	{/if}
</div>
