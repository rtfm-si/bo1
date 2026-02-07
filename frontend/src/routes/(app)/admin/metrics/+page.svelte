<script lang="ts">
	import { onMount } from 'svelte';
	import {
		BarChart3,
		RefreshCw,
		Users,
		TrendingUp,
		Activity,
		UserPlus,
		Calendar,
		Target,
		ChevronRight,
		MessageCircle,
		Database,
		FolderKanban,
		Play,
		CheckCircle,
		XCircle
	} from 'lucide-svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import AdminPageHeader from '$lib/components/admin/AdminPageHeader.svelte';
	import {
		adminApi,
		type UserMetricsResponse,
		type UsageMetricsResponse,
		type OnboardingFunnelResponse,
		type ObservabilityLinksResponse
	} from '$lib/api/admin';
	import ObservabilityLinks from '$lib/components/admin/ObservabilityLinks.svelte';

	// State
	let userMetrics = $state<UserMetricsResponse | null>(null);
	let usageMetrics = $state<UsageMetricsResponse | null>(null);
	let funnelMetrics = $state<OnboardingFunnelResponse | null>(null);
	let observabilityLinks = $state<ObservabilityLinksResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let selectedDays = $state(30);

	// Chart scaling
	let signupMaxValue = $state(0);
	let meetingMaxValue = $state(0);

	async function loadData() {
		try {
			loading = true;
			const [userData, usageData, funnelData, obsLinks] = await Promise.all([
				adminApi.getUserMetrics(selectedDays),
				adminApi.getUsageMetrics(selectedDays),
				adminApi.getOnboardingMetrics(),
				adminApi.getObservabilityLinks()
			]);
			userMetrics = userData;
			usageMetrics = usageData;
			funnelMetrics = funnelData;
			observabilityLinks = obsLinks;
			error = null;

			// Calculate max for chart scaling
			if (userData.daily_signups.length > 0) {
				signupMaxValue = Math.max(...userData.daily_signups.map((d) => d.count), 1);
			}
			if (usageData.daily_meetings.length > 0) {
				meetingMaxValue = Math.max(...usageData.daily_meetings.map((d) => d.count), 1);
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load metrics';
		} finally {
			loading = false;
		}
	}

	function formatDate(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	}

	function getBarHeight(value: number, max: number): number {
		if (max === 0) return 0;
		return (value / max) * 100;
	}

	function getFunnelWidth(index: number, total: number): number {
		// Taper from 100% to 60% across stages
		const minWidth = 60;
		const step = (100 - minWidth) / (total - 1);
		return 100 - step * index;
	}

	onMount(() => {
		loadData();
	});

	// Reload when days change
	$effect(() => {
		if (selectedDays) {
			loadData();
		}
	});
</script>

<svelte:head>
	<title>User & Usage Metrics - Admin</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<AdminPageHeader title="User & Usage Metrics" icon={BarChart3}>
		{#snippet actions()}
			<select
				bind:value={selectedDays}
				class="px-3 py-2 text-sm border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white"
			>
				<option value={7}>Last 7 days</option>
				<option value={30}>Last 30 days</option>
				<option value={90}>Last 90 days</option>
			</select>
			<Button variant="secondary" size="sm" onclick={loadData}>
				<RefreshCw class="w-4 h-4" />
				Refresh
			</Button>
		{/snippet}
	</AdminPageHeader>

	<!-- Main Content -->
	<main class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-8">
		{#if error}
			<Alert variant="error" class="mb-6">{error}</Alert>
		{/if}

		{#if loading}
		<div class="flex items-center justify-center py-12">
		<RefreshCw class="w-8 h-8 text-brand-600 animate-spin" />
		</div>
		{:else}
		<!-- Observability Links -->
		{#if observabilityLinks}
			<ObservabilityLinks {...observabilityLinks} />
		{/if}

		<!-- User Metrics Cards -->
			{#if userMetrics}
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">User Metrics</h2>
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
					>
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Total Users</p>
								<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
									{userMetrics.total_users.toLocaleString()}
								</p>
							</div>
							<div class="p-3 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
								<Users class="w-6 h-6 text-brand-600 dark:text-brand-400" />
							</div>
						</div>
					</div>
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
					>
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">New Today</p>
								<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
									{userMetrics.new_users_today}
								</p>
								<p class="text-xs text-neutral-500 mt-1">
									{userMetrics.new_users_7d} last 7d / {userMetrics.new_users_30d} last 30d
								</p>
							</div>
							<div class="p-3 bg-success-100 dark:bg-success-900/30 rounded-lg">
								<UserPlus class="w-6 h-6 text-success-600 dark:text-success-400" />
							</div>
						</div>
					</div>
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
					>
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">DAU / WAU</p>
								<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
									{userMetrics.dau} / {userMetrics.wau}
								</p>
								<p class="text-xs text-neutral-500 mt-1">Daily / Weekly active</p>
							</div>
							<div class="p-3 bg-warning-100 dark:bg-warning-900/30 rounded-lg">
								<Activity class="w-6 h-6 text-warning-600 dark:text-warning-400" />
							</div>
						</div>
					</div>
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
					>
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">MAU</p>
								<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
									{userMetrics.mau}
								</p>
								<p class="text-xs text-neutral-500 mt-1">Monthly active users</p>
							</div>
							<div class="p-3 bg-info-100 dark:bg-info-900/30 rounded-lg">
								<Calendar class="w-6 h-6 text-info-600 dark:text-info-400" />
							</div>
						</div>
					</div>
				</div>

				<!-- Daily Signups Chart -->
				{#if userMetrics.daily_signups.length > 0}
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6 mb-8"
					>
						<h3 class="text-base font-semibold text-neutral-900 dark:text-white mb-4">
							Daily Signups
						</h3>
						<div class="h-32 flex items-end gap-1">
							{#each userMetrics.daily_signups as day, i (day.date)}
								<div class="flex-1 flex flex-col items-center gap-1 min-w-0">
									<div
										class="w-full bg-success-500 dark:bg-success-400 rounded-t transition-all hover:bg-success-600 dark:hover:bg-success-300"
										style="height: {getBarHeight(day.count, signupMaxValue)}%"
										title="{formatDate(day.date)}: {day.count} signups"
									></div>
									{#if i % Math.ceil(userMetrics.daily_signups.length / 7) === 0 || i === userMetrics.daily_signups.length - 1}
										<span
											class="text-xs text-neutral-500 transform -rotate-45 origin-top-left whitespace-nowrap"
										>
											{formatDate(day.date)}
										</span>
									{/if}
								</div>
							{/each}
						</div>
					</div>
				{/if}
			{/if}

			<!-- Usage Metrics Cards -->
			{#if usageMetrics}
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">Usage Metrics</h2>
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
					>
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Total Meetings</p>
								<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
									{usageMetrics.total_meetings.toLocaleString()}
								</p>
							</div>
							<div class="p-3 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
								<TrendingUp class="w-6 h-6 text-brand-600 dark:text-brand-400" />
							</div>
						</div>
					</div>
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
					>
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Meetings Today</p>
								<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
									{usageMetrics.meetings_today}
								</p>
								<p class="text-xs text-neutral-500 mt-1">
									{usageMetrics.meetings_7d} last 7d / {usageMetrics.meetings_30d} last 30d
								</p>
							</div>
							<div class="p-3 bg-success-100 dark:bg-success-900/30 rounded-lg">
								<Activity class="w-6 h-6 text-success-600 dark:text-success-400" />
							</div>
						</div>
					</div>
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
					>
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Total Actions</p>
								<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
									{usageMetrics.total_actions.toLocaleString()}
								</p>
							</div>
							<div class="p-3 bg-warning-100 dark:bg-warning-900/30 rounded-lg">
								<Target class="w-6 h-6 text-warning-600 dark:text-warning-400" />
							</div>
						</div>
					</div>
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
					>
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Actions (7d)</p>
								<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
									{usageMetrics.actions_created_7d}
								</p>
								<p class="text-xs text-neutral-500 mt-1">Created in last week</p>
							</div>
							<div class="p-3 bg-info-100 dark:bg-info-900/30 rounded-lg">
								<BarChart3 class="w-6 h-6 text-info-600 dark:text-info-400" />
							</div>
						</div>
					</div>
				</div>

				<!-- Daily Meetings Chart -->
				{#if usageMetrics.daily_meetings.length > 0}
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6 mb-8"
					>
						<h3 class="text-base font-semibold text-neutral-900 dark:text-white mb-4">
							Daily Meetings
						</h3>
						<div class="h-32 flex items-end gap-1">
							{#each usageMetrics.daily_meetings as day, i (day.date)}
								<div class="flex-1 flex flex-col items-center gap-1 min-w-0">
									<div
										class="w-full bg-brand-500 dark:bg-brand-400 rounded-t transition-all hover:bg-brand-600 dark:hover:bg-brand-300"
										style="height: {getBarHeight(day.count, meetingMaxValue)}%"
										title="{formatDate(day.date)}: {day.count} meetings"
									></div>
									{#if i % Math.ceil(usageMetrics.daily_meetings.length / 7) === 0 || i === usageMetrics.daily_meetings.length - 1}
										<span
											class="text-xs text-neutral-500 transform -rotate-45 origin-top-left whitespace-nowrap"
										>
											{formatDate(day.date)}
										</span>
									{/if}
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Extended KPIs -->
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">Extended KPIs</h2>
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
					>
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Mentor Sessions</p>
								<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
									{usageMetrics.mentor_sessions_count.toLocaleString()}
								</p>
								<p class="text-xs text-neutral-500 mt-1">AI mentor conversations</p>
							</div>
							<div class="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
								<MessageCircle class="w-6 h-6 text-purple-600 dark:text-purple-400" />
							</div>
						</div>
					</div>
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
					>
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Data Analyses</p>
								<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
									{usageMetrics.data_analyses_count.toLocaleString()}
								</p>
								<p class="text-xs text-neutral-500 mt-1">Dataset analyses run</p>
							</div>
							<div class="p-3 bg-cyan-100 dark:bg-cyan-900/30 rounded-lg">
								<Database class="w-6 h-6 text-cyan-600 dark:text-cyan-400" />
							</div>
						</div>
					</div>
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
					>
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Projects</p>
								<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
									{usageMetrics.projects_count.toLocaleString()}
								</p>
								<p class="text-xs text-neutral-500 mt-1">Active projects</p>
							</div>
							<div class="p-3 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg">
								<FolderKanban class="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
							</div>
						</div>
					</div>
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
					>
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Actions Started</p>
								<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
									{usageMetrics.actions_started_count.toLocaleString()}
								</p>
								<p class="text-xs text-neutral-500 mt-1">In progress</p>
							</div>
							<div class="p-3 bg-info-100 dark:bg-info-900/30 rounded-lg">
								<Play class="w-6 h-6 text-info-600 dark:text-info-400" />
							</div>
						</div>
					</div>
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
					>
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Actions Completed</p>
								<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
									{usageMetrics.actions_completed_count.toLocaleString()}
								</p>
								<p class="text-xs text-neutral-500 mt-1">Done</p>
							</div>
							<div class="p-3 bg-success-100 dark:bg-success-900/30 rounded-lg">
								<CheckCircle class="w-6 h-6 text-success-600 dark:text-success-400" />
							</div>
						</div>
					</div>
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
					>
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Actions Cancelled</p>
								<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
									{usageMetrics.actions_cancelled_count.toLocaleString()}
								</p>
								<p class="text-xs text-neutral-500 mt-1">Cancelled</p>
							</div>
							<div class="p-3 bg-error-100 dark:bg-error-900/30 rounded-lg">
								<XCircle class="w-6 h-6 text-error-600 dark:text-error-400" />
							</div>
						</div>
					</div>
				</div>
			{/if}

			<!-- Onboarding Funnel -->
			{#if funnelMetrics}
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">
					Onboarding Funnel
				</h2>
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6 mb-8"
				>
					<!-- Funnel Visualization -->
					<div class="space-y-3 mb-6">
						{#each funnelMetrics.stages as stage, i (stage.name)}
							<div class="relative">
								<div
									class="h-12 rounded-lg flex items-center justify-between px-4 transition-all {i === 0
										? 'bg-brand-500 dark:bg-brand-600 text-white'
										: i === 1
											? 'bg-brand-400 dark:bg-brand-500 text-white'
											: i === 2
												? 'bg-brand-300 dark:bg-brand-400 text-brand-900 dark:text-white'
												: 'bg-brand-200 dark:bg-brand-300 text-brand-900 dark:text-brand-900'}"
									style="width: {getFunnelWidth(i, funnelMetrics.stages.length)}%; margin-left: {(100 - getFunnelWidth(i, funnelMetrics.stages.length)) / 2}%"
								>
									<span class="font-medium">{stage.name}</span>
									<div class="flex items-center gap-3">
										<span class="font-semibold">{stage.count.toLocaleString()}</span>
										{#if i > 0}
											<span
												class="text-sm opacity-80 flex items-center gap-1"
												title="Conversion from previous stage"
											>
												<ChevronRight class="w-3 h-3" />
												{stage.conversion_rate}%
											</span>
										{/if}
									</div>
								</div>
							</div>
						{/each}
					</div>

					<!-- Conversion Rates Summary -->
					<div class="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-neutral-200 dark:border-neutral-700">
						<div class="text-center">
							<p class="text-sm text-neutral-600 dark:text-neutral-400">Signup → Context</p>
							<p class="text-xl font-semibold text-neutral-900 dark:text-white">
								{funnelMetrics.signup_to_context}%
							</p>
						</div>
						<div class="text-center">
							<p class="text-sm text-neutral-600 dark:text-neutral-400">Context → Meeting</p>
							<p class="text-xl font-semibold text-neutral-900 dark:text-white">
								{funnelMetrics.context_to_meeting}%
							</p>
						</div>
						<div class="text-center">
							<p class="text-sm text-neutral-600 dark:text-neutral-400">Meeting → Complete</p>
							<p class="text-xl font-semibold text-neutral-900 dark:text-white">
								{funnelMetrics.meeting_to_complete}%
							</p>
						</div>
						<div class="text-center">
							<p class="text-sm text-neutral-600 dark:text-neutral-400">Overall</p>
							<p
								class="text-xl font-semibold {funnelMetrics.overall_conversion >= 20
									? 'text-success-600 dark:text-success-400'
									: funnelMetrics.overall_conversion >= 10
										? 'text-warning-600 dark:text-warning-400'
										: 'text-error-600 dark:text-error-400'}"
							>
								{funnelMetrics.overall_conversion}%
							</p>
						</div>
					</div>
				</div>

				<!-- Cohort Comparison -->
				<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6"
					>
						<h3 class="text-base font-semibold text-neutral-900 dark:text-white mb-4">
							7-Day Cohort
						</h3>
						<div class="space-y-3">
							<div class="flex justify-between">
								<span class="text-sm text-neutral-600 dark:text-neutral-400">Signups</span>
								<span class="font-medium text-neutral-900 dark:text-white"
									>{funnelMetrics.cohort_7d.signups}</span
								>
							</div>
							<div class="flex justify-between">
								<span class="text-sm text-neutral-600 dark:text-neutral-400">Context Completed</span
								>
								<span class="font-medium text-neutral-900 dark:text-white"
									>{funnelMetrics.cohort_7d.context_completed}</span
								>
							</div>
							<div class="flex justify-between">
								<span class="text-sm text-neutral-600 dark:text-neutral-400">First Meeting</span>
								<span class="font-medium text-neutral-900 dark:text-white"
									>{funnelMetrics.cohort_7d.first_meeting}</span
								>
							</div>
							<div class="flex justify-between">
								<span class="text-sm text-neutral-600 dark:text-neutral-400">Meeting Completed</span
								>
								<span class="font-medium text-neutral-900 dark:text-white"
									>{funnelMetrics.cohort_7d.meeting_completed}</span
								>
							</div>
						</div>
					</div>
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6"
					>
						<h3 class="text-base font-semibold text-neutral-900 dark:text-white mb-4">
							30-Day Cohort
						</h3>
						<div class="space-y-3">
							<div class="flex justify-between">
								<span class="text-sm text-neutral-600 dark:text-neutral-400">Signups</span>
								<span class="font-medium text-neutral-900 dark:text-white"
									>{funnelMetrics.cohort_30d.signups}</span
								>
							</div>
							<div class="flex justify-between">
								<span class="text-sm text-neutral-600 dark:text-neutral-400">Context Completed</span
								>
								<span class="font-medium text-neutral-900 dark:text-white"
									>{funnelMetrics.cohort_30d.context_completed}</span
								>
							</div>
							<div class="flex justify-between">
								<span class="text-sm text-neutral-600 dark:text-neutral-400">First Meeting</span>
								<span class="font-medium text-neutral-900 dark:text-white"
									>{funnelMetrics.cohort_30d.first_meeting}</span
								>
							</div>
							<div class="flex justify-between">
								<span class="text-sm text-neutral-600 dark:text-neutral-400">Meeting Completed</span
								>
								<span class="font-medium text-neutral-900 dark:text-white"
									>{funnelMetrics.cohort_30d.meeting_completed}</span
								>
							</div>
						</div>
					</div>
				</div>
			{/if}
		{/if}
	</main>
</div>
