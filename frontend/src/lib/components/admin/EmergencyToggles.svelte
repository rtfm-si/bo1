<script lang="ts">
	/**
	 * EmergencyToggles - Admin panel for emergency security toggles
	 * Allows instant disable/enable of security features without restart
	 */
	import { onMount } from 'svelte';
	import { Shield, AlertTriangle, RefreshCw } from 'lucide-svelte';
	import { BoCard, BoButton, Alert, Badge } from '$lib/components/ui';
	import { adminApi, type RuntimeConfigItem } from '$lib/api/admin';
	import { toast } from '$lib/stores/toast';

	// Config item descriptions for display
	// Grouped by category: Security > LLM/Caching > Features
	const CONFIG_LABELS: Record<
		string,
		{ label: string; description: string; dangerWhenOff: boolean; group: string }
	> = {
		// Security toggles
		prompt_injection_block_suspicious: {
			label: 'Block Prompt Injection',
			description:
				'Blocks requests containing suspicious prompt injection patterns. Disable only in emergencies.',
			dangerWhenOff: true,
			group: 'Security'
		},
		// LLM/Caching toggles
		enable_llm_response_cache: {
			label: 'LLM Response Cache',
			description:
				'Caches LLM responses to reduce API costs by 60-80%. Disable if stale responses are problematic.',
			dangerWhenOff: false,
			group: 'LLM & Caching'
		},
		enable_prompt_cache: {
			label: 'Anthropic Prompt Cache',
			description:
				'Enables Anthropic prompt caching for ~90% input token cost savings. Disable if prompt changes are not taking effect.',
			dangerWhenOff: false,
			group: 'LLM & Caching'
		},
		// Feature toggles
		enable_sse_streaming: {
			label: 'SSE Streaming',
			description:
				'Enables real-time SSE streaming for meetings. Disable if clients experience connection issues.',
			dangerWhenOff: false,
			group: 'Features'
		},
		auto_generate_projects: {
			label: 'Auto-Generate Projects',
			description:
				'Automatically suggests projects from unassigned actions. Disable if suggestions are unwanted.',
			dangerWhenOff: false,
			group: 'Features'
		},
		enable_context_collection: {
			label: 'Context Collection',
			description:
				'Collects business context for improved recommendations. Disable if privacy concerns arise.',
			dangerWhenOff: false,
			group: 'Features'
		}
	};

	// Define group order for display
	const GROUP_ORDER = ['Security', 'LLM & Caching', 'Features'];

	let configItems = $state<RuntimeConfigItem[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let pendingChanges = $state<Set<string>>(new Set());
	let confirmingDisable = $state<string | null>(null);

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

	onMount(loadConfig);
</script>

<BoCard class="border-warning-300 dark:border-warning-700">
	{#snippet header()}
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2">
				<Shield class="w-5 h-5 text-warning-600 dark:text-warning-400" />
				<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Emergency Toggles</h3>
			</div>
			<BoButton variant="ghost" onclick={loadConfig} disabled={loading}>
				<RefreshCw class="w-4 h-4 {loading ? 'animate-spin' : ''}" />
			</BoButton>
		</div>
	{/snippet}

	{#if error}
		<Alert variant="error" class="mb-4">
			{error}
		</Alert>
	{/if}

	{#if loading && configItems.length === 0}
		<div class="flex items-center justify-center py-8">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500"></div>
		</div>
	{:else if configItems.length === 0}
		<p class="text-neutral-500 dark:text-neutral-400 text-center py-4">No configurable items</p>
	{:else}
		<div class="space-y-6">
			{#each groupedItems as [groupName, items] (groupName)}
				<div>
					<h4 class="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-3 uppercase tracking-wide">
						{groupName}
					</h4>
					<div class="space-y-3">
						{#each items as item (item.key)}
							{@const config = CONFIG_LABELS[item.key]}
							{@const isPending = pendingChanges.has(item.key)}
							{@const isConfirming = confirmingDisable === item.key}
							{@const isDanger = config?.dangerWhenOff && !item.effective_value}

							<div
								class="p-4 rounded-lg border {isDanger
									? 'border-error-300 dark:border-error-700 bg-error-50 dark:bg-error-900/20'
									: 'border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800'}"
							>
								<div class="flex items-start justify-between gap-4">
									<div class="flex-1 min-w-0">
										<div class="flex items-center gap-2 mb-1">
											<span class="font-medium text-neutral-900 dark:text-white">
												{config?.label || item.key}
											</span>
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
										<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-2">
											{config?.description || 'No description available'}
										</p>
										<div class="flex items-center gap-4 text-xs text-neutral-500 dark:text-neutral-500">
											<span>Default: <strong>{item.default_value ? 'On' : 'Off'}</strong></span>
											{#if item.is_overridden}
												<span>Override: <strong>{item.override_value ? 'On' : 'Off'}</strong></span>
											{/if}
										</div>
									</div>

									<div class="flex items-center gap-2">
										{#if item.is_overridden}
											<BoButton
												variant="outline"
												onclick={() => clearOverride(item)}
												disabled={isPending}
												class="text-xs"
											>
												Reset
											</BoButton>
										{/if}

										<!-- Toggle Switch -->
										<button
											type="button"
											onclick={() => toggleConfig(item)}
											disabled={isPending}
											class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed {item.effective_value
												? 'bg-brand-600'
												: isDanger
													? 'bg-error-400'
													: 'bg-neutral-300 dark:bg-neutral-600'}"
											aria-label="{config?.label || item.key}: {item.effective_value ? 'enabled' : 'disabled'}"
										>
											<span
												class="inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform {item.effective_value
													? 'tranneutral-x-6'
													: 'tranneutral-x-1'}"
											></span>
										</button>
									</div>
								</div>

								<!-- Confirmation dialog for dangerous toggles -->
								{#if isConfirming}
									<div class="mt-4 p-3 bg-error-100 dark:bg-error-900/40 rounded-lg border border-error-300 dark:border-error-700">
										<div class="flex items-start gap-3">
											<AlertTriangle class="w-5 h-5 text-error-600 dark:text-error-400 flex-shrink-0 mt-0.5" />
											<div class="flex-1">
												<p class="text-sm font-medium text-error-800 dark:text-error-200 mb-2">
													Are you sure you want to disable this security feature?
												</p>
												<p class="text-xs text-error-700 dark:text-error-300 mb-3">
													Disabling prompt injection blocking may allow malicious inputs to manipulate LLM responses.
													Only disable this in emergencies where legitimate requests are being blocked.
												</p>
												<div class="flex gap-2">
													<BoButton variant="danger" onclick={() => toggleConfig(item)} disabled={isPending}>
														{#if isPending}
															<RefreshCw class="w-4 h-4 animate-spin mr-1" />
														{/if}
														Disable Security
													</BoButton>
													<BoButton variant="outline" onclick={cancelConfirm}>Cancel</BoButton>
												</div>
											</div>
										</div>
									</div>
								{/if}
							</div>
						{/each}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</BoCard>
