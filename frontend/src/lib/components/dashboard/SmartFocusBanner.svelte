<script lang="ts">
	/**
	 * SmartFocusBanner - Priority-ordered focus suggestions based on user state
	 * Shows the most relevant CTA based on current context (overdue actions, goals, etc.)
	 * Replaces static Quick Actions panel with intelligent, context-aware recommendations
	 */

	export type FocusState =
		| 'no_goal'
		| 'stale_goal'
		| 'overdue_actions'
		| 'due_today'
		| 'stale_context'
		| 'ready';

	interface Props {
		focusState: FocusState;
		overdueCount?: number;
		dueTodayCount?: number;
		daysSinceGoalChange?: number | null;
		hasBusinessContext?: boolean;
		loading?: boolean;
	}

	let {
		focusState,
		overdueCount = 0,
		dueTodayCount = 0,
		daysSinceGoalChange = null,
		hasBusinessContext = true,
		loading = false
	}: Props = $props();

	// Config for each focus state
	const focusConfig: Record<FocusState, {
		icon: string;
		title: string;
		description: string;
		cta: string;
		href: string;
		variant: 'brand' | 'warning' | 'error' | 'neutral';
		secondaryHref?: string;
		secondaryCta?: string;
	}> = {
		no_goal: {
			icon: 'target',
			title: 'Set your north star goal',
			description: 'Define your strategic direction to align decisions and actions.',
			cta: 'Set Goal',
			href: '/context/overview',
			variant: 'brand',
			secondaryHref: '/meeting/new',
			secondaryCta: 'Start Meeting'
		},
		stale_goal: {
			icon: 'refresh',
			title: 'Review your goal',
			description: `Your goal hasn't changed in ${daysSinceGoalChange ?? 30}+ days. Is it still relevant?`,
			cta: 'Review Goal',
			href: '/context/strategic',
			variant: 'warning',
			secondaryHref: '/meeting/new',
			secondaryCta: 'Start Meeting'
		},
		overdue_actions: {
			icon: 'alert',
			title: `${overdueCount} overdue ${overdueCount === 1 ? 'action needs' : 'actions need'} attention`,
			description: 'Address overdue items to stay on track with your objectives.',
			cta: 'View Actions',
			href: '/actions?status=todo&sort=due_date',
			variant: 'error',
			secondaryHref: '/meeting/new',
			secondaryCta: 'Start Meeting'
		},
		due_today: {
			icon: 'clock',
			title: `${dueTodayCount} ${dueTodayCount === 1 ? 'action' : 'actions'} due today`,
			description: 'Stay on top of today\'s priorities.',
			cta: 'View Today\'s Actions',
			href: '/actions?status=todo&sort=due_date',
			variant: 'warning',
			secondaryHref: '/meeting/new',
			secondaryCta: 'Start Meeting'
		},
		stale_context: {
			icon: 'context',
			title: 'Update your business context',
			description: 'Fresh context helps generate better insights and recommendations.',
			cta: 'Update Context',
			href: '/context/overview',
			variant: 'neutral',
			secondaryHref: '/meeting/new',
			secondaryCta: 'Start Meeting'
		},
		ready: {
			icon: 'meeting',
			title: 'Ready to make a decision?',
			description: 'Get expert perspectives on your next strategic choice.',
			cta: 'Start Meeting',
			href: '/meeting/new',
			variant: 'brand',
			secondaryHref: '/actions',
			secondaryCta: 'View Actions'
		}
	};

	const config = $derived(focusConfig[focusState]);

	// Variant styles
	const variantStyles: Record<string, { banner: string; button: string; icon: string }> = {
		brand: {
			banner: 'bg-gradient-to-r from-brand-50 to-brand-100/50 dark:from-brand-900/20 dark:to-brand-800/10 border-brand-200 dark:border-brand-800',
			button: 'bg-brand-600 hover:bg-brand-700 text-white',
			icon: 'bg-brand-100 dark:bg-brand-800/50 text-brand-600 dark:text-brand-400'
		},
		warning: {
			banner: 'bg-gradient-to-r from-amber-50 to-amber-100/50 dark:from-amber-900/20 dark:to-amber-800/10 border-amber-200 dark:border-amber-800',
			button: 'bg-amber-600 hover:bg-amber-700 text-white',
			icon: 'bg-amber-100 dark:bg-amber-800/50 text-amber-600 dark:text-amber-400'
		},
		error: {
			banner: 'bg-gradient-to-r from-red-50 to-red-100/50 dark:from-red-900/20 dark:to-red-800/10 border-red-200 dark:border-red-800',
			button: 'bg-red-600 hover:bg-red-700 text-white',
			icon: 'bg-red-100 dark:bg-red-800/50 text-red-600 dark:text-red-400'
		},
		neutral: {
			banner: 'bg-gradient-to-r from-neutral-50 to-neutral-100/50 dark:from-neutral-800/50 dark:to-neutral-700/30 border-neutral-200 dark:border-neutral-700',
			button: 'bg-neutral-700 hover:bg-neutral-800 dark:bg-neutral-600 dark:hover:bg-neutral-500 text-white',
			icon: 'bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400'
		}
	};

	const styles = $derived(variantStyles[config.variant]);
</script>

{#if loading}
	<!-- Loading skeleton -->
	<div class="mb-6 bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-xl p-5 animate-pulse">
		<div class="flex items-center gap-4">
			<div class="w-12 h-12 rounded-full bg-neutral-200 dark:bg-neutral-700"></div>
			<div class="flex-1 space-y-2">
				<div class="h-5 w-48 bg-neutral-200 dark:bg-neutral-700 rounded"></div>
				<div class="h-4 w-64 bg-neutral-200 dark:bg-neutral-700 rounded"></div>
			</div>
			<div class="h-10 w-28 bg-neutral-200 dark:bg-neutral-700 rounded-lg"></div>
		</div>
	</div>
{:else}
	<div class="mb-6 border rounded-xl p-5 transition-all duration-200 {styles.banner}">
		<div class="flex flex-col sm:flex-row sm:items-center gap-4">
			<!-- Icon -->
			<div class="flex-shrink-0 w-12 h-12 flex items-center justify-center rounded-full {styles.icon}">
				{#if config.icon === 'target'}
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
					</svg>
				{:else if config.icon === 'refresh'}
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
					</svg>
				{:else if config.icon === 'alert'}
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
					</svg>
				{:else if config.icon === 'clock'}
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
				{:else if config.icon === 'context'}
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
					</svg>
				{:else}
					<!-- meeting icon -->
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
					</svg>
				{/if}
			</div>

			<!-- Content -->
			<div class="flex-1 min-w-0">
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
					{config.title}
				</h2>
				<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-0.5">
					{config.description}
				</p>
			</div>

			<!-- CTAs -->
			<div class="flex items-center gap-3 flex-shrink-0">
				{#if config.secondaryHref}
					<a
						href={config.secondaryHref}
						class="text-sm font-medium text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white transition-colors"
					>
						{config.secondaryCta}
					</a>
				{/if}
				<a
					href={config.href}
					class="inline-flex items-center px-4 py-2 text-sm font-semibold rounded-lg transition-colors {styles.button}"
				>
					{config.cta}
					<svg class="w-4 h-4 ml-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
					</svg>
				</a>
			</div>
		</div>
	</div>
{/if}
