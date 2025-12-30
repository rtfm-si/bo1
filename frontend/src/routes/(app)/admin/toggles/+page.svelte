<script lang="ts">
	/**
	 * Emergency Toggles Admin Page
	 * Dedicated full-width page for critical system toggles
	 */
	import { onMount } from 'svelte';
	import { Shield, AlertTriangle, RefreshCw, ArrowLeft, Info } from 'lucide-svelte';
	import { BoCard, BoButton, Alert, Badge } from '$lib/components/ui';
	import { adminApi, type RuntimeConfigItem } from '$lib/api/admin';
	import { toast } from '$lib/stores/toast';

	// Config item descriptions for display
	// Grouped by category: Security > LLM/Caching > Features
	const CONFIG_LABELS: Record<
		string,
		{
			label: string;
			description: string;
			dangerWhenOff: boolean;
			group: string;
			whenToUse: string;
		}
	> = {
		// Security toggles
		prompt_injection_block_suspicious: {
			label: 'Block Prompt Injection',
			description:
				'Blocks requests containing suspicious prompt injection patterns.',
			dangerWhenOff: true,
			group: 'Security',
			whenToUse:
				'Disable only in emergencies when legitimate requests are being blocked. Re-enable as soon as possible.'
		},
		// LLM/Caching toggles
		enable_llm_response_cache: {
			label: 'LLM Response Cache',
			description: 'Caches LLM responses to reduce API costs by 60-80%.',
			dangerWhenOff: false,
			group: 'LLM & Caching',
			whenToUse:
				'Disable if stale responses are causing issues or if you need immediate reflection of prompt changes.'
		},
		enable_prompt_cache: {
			label: 'Anthropic Prompt Cache',
			description: 'Enables Anthropic prompt caching for ~90% input token cost savings.',
			dangerWhenOff: false,
			group: 'LLM & Caching',
			whenToUse:
				'Disable if prompt changes are not taking effect. The cache has a TTL, so changes propagate automatically.'
		},
		// Feature toggles
		enable_sse_streaming: {
			label: 'SSE Streaming',
			description: 'Enables real-time Server-Sent Events streaming for meetings.',
			dangerWhenOff: false,
			group: 'Features',
			whenToUse:
				'Off by default. Enable for users who want real-time updates during meetings. Disable if clients experience connection drops or timeout issues.'
		},
		auto_generate_projects: {
			label: 'Auto-Generate Projects',
			description: 'Automatically suggests projects from unassigned actions.',
			dangerWhenOff: false,
			group: 'Features',
			whenToUse: 'Disable if auto-suggestions are creating noise or unwanted projects for users.'
		},
		enable_context_collection: {
			label: 'Context Collection',
			description: 'Collects business context for improved recommendations.',
			dangerWhenOff: false,
			group: 'Features',
			whenToUse: 'Disable if privacy concerns arise or if context collection is causing issues.'
		}
	};

	// Define group order for display
	const GROUP_ORDER = ['Security', 'LLM & Caching', 'Features'];

	let configItems = $state<RuntimeConfigItem[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let pendingChanges = $state<Set<string>>(new Set());
	let confirmingDisable = $state<string | null>(null);
	let expandedInfo = $state<Set<string>>(new Set());

	// Summary stats
	const enabledCount = $derived(configItems.filter((c) => c.effective_value).length);
	const totalCount = $derived(configItems.length);
	const securityEnabled = $derived(
		configItems
			.filter((c) => CONFIG_LABELS[c.key]?.group === 'Security')
			.every((c) => c.effective_value)
	);

	// Group config items by category
	const groupedItems = $derived.by(() => {
		const groups = new Map<string, RuntimeConfigItem[]>();

		// Initialize groups in order
		for (const group of GROUP_ORDER) {
			groups.set(group, []);
		}

		// Assign items to groups
		for (const item of configItems) {
			const config = CONFIG_LABELS[item.key];
			const group = config?.group || 'Other';
			if (!groups.has(group)) {
				groups.set(group, []);
			}
			groups.get(group)!.push(item);
		}

		// Filter out empty groups
		return Array.from(groups.entries()).filter(([, items]) => items.length > 0);
	});

	async function loadConfig() {
		loading = true;
		error = null;
		try {
			const response = await adminApi.getRuntimeConfig();
			configItems = response.items;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load config';
		} finally {
			loading = false;
		}
	}

	async function toggleConfig(item: RuntimeConfigItem) {
		const newValue = !item.effective_value;
		const config = CONFIG_LABELS[item.key];

		// If disabling a dangerous setting, show confirmation
		if (config?.dangerWhenOff && !newValue && confirmingDisable !== item.key) {
			confirmingDisable = item.key;
			return;
		}

		confirmingDisable = null;
		pendingChanges.add(item.key);
		pendingChanges = pendingChanges;

		try {
			const updated = await adminApi.setRuntimeConfig(item.key, newValue);
			// Update local state
			const idx = configItems.findIndex((c) => c.key === item.key);
			if (idx !== -1) {
				configItems[idx] = updated;
				configItems = configItems;
			}
			toast.success(`${config?.label || item.key} ${newValue ? 'enabled' : 'disabled'}`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to update config');
		} finally {
			pendingChanges.delete(item.key);
			pendingChanges = pendingChanges;
		}
	}

	async function clearOverride(item: RuntimeConfigItem) {
		pendingChanges.add(item.key);
		pendingChanges = pendingChanges;

		try {
			const updated = await adminApi.clearRuntimeConfig(item.key);
			const idx = configItems.findIndex((c) => c.key === item.key);
			if (idx !== -1) {
				configItems[idx] = updated;
				configItems = configItems;
			}
			toast.success('Reverted to default value');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to clear override');
		} finally {
			pendingChanges.delete(item.key);
			pendingChanges = pendingChanges;
		}
	}

	function cancelConfirm() {
		confirmingDisable = null;
	}

	function toggleInfo(key: string) {
		if (expandedInfo.has(key)) {
			expandedInfo.delete(key);
		} else {
			expandedInfo.add(key);
		}
		expandedInfo = expandedInfo;
	}

	onMount(loadConfig);
</script>

<svelte:head>
	<title>Emergency Toggles - Admin - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Header -->
	<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<a
						href="/admin"
						class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
						aria-label="Back to admin"
					>
						<ArrowLeft class="w-5 h-5 text-neutral-600 dark:text-neutral-400" />
					</a>
					<div class="flex items-center gap-3">
						<div class="p-2 bg-warning-100 dark:bg-warning-900/30 rounded-lg">
							<Shield class="w-6 h-6 text-warning-600 dark:text-warning-400" />
						</div>
						<div>
							<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">
								Emergency Toggles
							</h1>
							<p class="text-sm text-neutral-600 dark:text-neutral-400">
								Critical system controls with instant effect
							</p>
						</div>
					</div>
				</div>
				<div class="flex items-center gap-3">
					<BoButton variant="outline" onclick={loadConfig} disabled={loading}>
						<RefreshCw class="w-4 h-4 {loading ? 'animate-spin' : ''}" />
						Refresh
					</BoButton>
				</div>
			</div>
		</div>
	</header>

	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		{#if error}
			<Alert variant="error" class="mb-6">
				{error}
			</Alert>
		{/if}

		<!-- Summary Bar -->
		{#if !loading && configItems.length > 0}
			<div
				class="mb-6 p-4 rounded-lg border {securityEnabled
					? 'bg-success-50 dark:bg-success-900/20 border-success-200 dark:border-success-800'
					: 'bg-error-50 dark:bg-error-900/20 border-error-200 dark:border-error-800'}"
			>
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-3">
						{#if securityEnabled}
							<Shield class="w-5 h-5 text-success-600 dark:text-success-400" />
							<span class="font-medium text-success-700 dark:text-success-300">
								All security features enabled
							</span>
						{:else}
							<AlertTriangle class="w-5 h-5 text-error-600 dark:text-error-400" />
							<span class="font-medium text-error-700 dark:text-error-300">
								Security feature disabled - review immediately
							</span>
						{/if}
					</div>
					<span class="text-sm text-neutral-600 dark:text-neutral-400">
						{enabledCount} of {totalCount} toggles enabled
					</span>
				</div>
			</div>
		{/if}

		{#if loading && configItems.length === 0}
			<div class="flex items-center justify-center py-12">
				<RefreshCw class="w-8 h-8 animate-spin text-brand-600" />
			</div>
		{:else if configItems.length === 0}
			<BoCard>
				<p class="text-neutral-500 dark:text-neutral-400 text-center py-8">
					No configurable items available
				</p>
			</BoCard>
		{:else}
			<div class="space-y-8">
				{#each groupedItems as [groupName, items] (groupName)}
					<section>
						<h2
							class="text-lg font-semibold text-neutral-900 dark:text-white mb-4 flex items-center gap-2"
						>
							{groupName}
							<Badge variant={groupName === 'Security' ? 'warning' : 'neutral'}>
								{items.length}
							</Badge>
						</h2>
						<div class="grid gap-4">
							{#each items as item (item.key)}
								{@const config = CONFIG_LABELS[item.key]}
								{@const isPending = pendingChanges.has(item.key)}
								{@const isConfirming = confirmingDisable === item.key}
								{@const isDanger = config?.dangerWhenOff && !item.effective_value}
								{@const isExpanded = expandedInfo.has(item.key)}

								<BoCard
									class="{isDanger
										? 'border-error-300 dark:border-error-700'
										: 'border-neutral-200 dark:border-neutral-700'}"
								>
									<div class="p-6">
										<div class="flex items-start justify-between gap-6">
											<div class="flex-1 min-w-0">
												<div class="flex items-center gap-3 mb-2">
													<h3 class="text-lg font-medium text-neutral-900 dark:text-white">
														{config?.label || item.key}
													</h3>
													{#if item.is_overridden}
														<Badge variant="warning">Override Active</Badge>
													{/if}
													{#if isDanger}
														<Badge variant="error">
															<AlertTriangle class="w-3 h-3 mr-1" />
															Security Off
														</Badge>
													{/if}
												</div>
												<p class="text-neutral-600 dark:text-neutral-400 mb-3">
													{config?.description || 'No description available'}
												</p>

												<!-- Info toggle button -->
												<button
													type="button"
													onclick={() => toggleInfo(item.key)}
													class="inline-flex items-center gap-1.5 text-sm text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300"
												>
													<Info class="w-4 h-4" />
													{isExpanded ? 'Hide details' : 'When to use'}
												</button>

												<!-- Expanded info -->
												{#if isExpanded && config?.whenToUse}
													<div
														class="mt-3 p-3 bg-neutral-100 dark:bg-neutral-700/50 rounded-lg"
													>
														<p class="text-sm text-neutral-700 dark:text-neutral-300">
															{config.whenToUse}
														</p>
													</div>
												{/if}

												<!-- Default value info -->
												<div
													class="mt-3 flex items-center gap-4 text-sm text-neutral-500 dark:text-neutral-500"
												>
													<span>
														Default: <strong>{item.default_value ? 'On' : 'Off'}</strong>
													</span>
													{#if item.is_overridden}
														<span>
															Override: <strong
																>{item.override_value ? 'On' : 'Off'}</strong
															>
														</span>
													{/if}
												</div>
											</div>

											<div class="flex items-center gap-3 flex-shrink-0">
												{#if item.is_overridden}
													<BoButton
														variant="outline"
														onclick={() => clearOverride(item)}
														disabled={isPending}
													>
														Reset to Default
													</BoButton>
												{/if}

												<!-- Toggle Switch -->
												<button
													type="button"
													onclick={() => toggleConfig(item)}
													disabled={isPending}
													class="relative inline-flex h-8 w-14 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed {item.effective_value
														? 'bg-brand-600'
														: isDanger
															? 'bg-error-400'
															: 'bg-neutral-300 dark:bg-neutral-600'}"
													aria-label="{config?.label || item.key}: {item.effective_value
														? 'enabled'
														: 'disabled'}"
												>
													<span
														class="inline-block h-6 w-6 transform rounded-full bg-white shadow transition-transform {item.effective_value
															? 'translate-x-7'
															: 'translate-x-1'}"
													></span>
												</button>
											</div>
										</div>

										<!-- Confirmation dialog for dangerous toggles -->
										{#if isConfirming}
											<div
												class="mt-4 p-4 bg-error-100 dark:bg-error-900/40 rounded-lg border border-error-300 dark:border-error-700"
											>
												<div class="flex items-start gap-3">
													<AlertTriangle
														class="w-5 h-5 text-error-600 dark:text-error-400 flex-shrink-0 mt-0.5"
													/>
													<div class="flex-1">
														<p
															class="text-sm font-medium text-error-800 dark:text-error-200 mb-2"
														>
															Are you sure you want to disable this security feature?
														</p>
														<p class="text-sm text-error-700 dark:text-error-300 mb-4">
															Disabling prompt injection blocking may allow malicious inputs
															to manipulate LLM responses. Only disable this in emergencies
															where legitimate requests are being blocked.
														</p>
														<div class="flex gap-3">
															<BoButton
																variant="danger"
																onclick={() => toggleConfig(item)}
																disabled={isPending}
															>
																{#if isPending}
																	<RefreshCw class="w-4 h-4 animate-spin mr-2" />
																{/if}
																Confirm Disable
															</BoButton>
															<BoButton variant="outline" onclick={cancelConfirm}>
																Cancel
															</BoButton>
														</div>
													</div>
												</div>
											</div>
										{/if}
									</div>
								</BoCard>
							{/each}
						</div>
					</section>
				{/each}
			</div>
		{/if}
	</main>
</div>
