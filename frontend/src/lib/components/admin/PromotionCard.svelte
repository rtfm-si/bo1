<script lang="ts">
	/**
	 * PromotionCard - Displays a single promotion with status badge and actions
	 */
	import { Button } from '$lib/components/ui';
	import { Copy, Trash2, Check } from 'lucide-svelte';
	import type { Promotion } from '$lib/api/admin';

	interface Props {
		promotion: Promotion;
		onDelete: (promotion: Promotion) => void;
	}

	let { promotion, onDelete }: Props = $props();
	let copied = $state(false);

	function getStatus(): 'active' | 'expired' | 'upcoming' | 'inactive' {
		if (!promotion.is_active) return 'inactive';
		const now = new Date();
		if (promotion.expires_at) {
			const expiresAt = new Date(promotion.expires_at);
			if (expiresAt < now) return 'expired';
		}
		return 'active';
	}

	function getStatusBadge(status: string): { bg: string; text: string; label: string } {
		switch (status) {
			case 'active':
				return { bg: 'bg-success-100 dark:bg-success-900/20', text: 'text-success-800 dark:text-success-300', label: 'Active' };
			case 'expired':
				return { bg: 'bg-error-100 dark:bg-error-900/20', text: 'text-error-800 dark:text-error-300', label: 'Expired' };
			case 'upcoming':
				return { bg: 'bg-info-100 dark:bg-info-900/20', text: 'text-info-800 dark:text-info-300', label: 'Upcoming' };
			case 'inactive':
				return { bg: 'bg-neutral-100 dark:bg-neutral-700', text: 'text-neutral-600 dark:text-neutral-400', label: 'Inactive' };
			default:
				return { bg: 'bg-neutral-100 dark:bg-neutral-700', text: 'text-neutral-600 dark:text-neutral-400', label: status };
		}
	}

	function formatType(type: string): string {
		switch (type) {
			case 'goodwill_credits':
				return 'Goodwill Credits';
			case 'percentage_discount':
				return 'Percentage Off';
			case 'flat_discount':
				return 'Flat Discount';
			case 'extra_deliberations':
				return 'Extra Deliberations';
			default:
				return type;
		}
	}

	function formatValue(type: string, value: number): string {
		switch (type) {
			case 'percentage_discount':
				return `${value}%`;
			case 'flat_discount':
				return `$${value.toFixed(2)}`;
			case 'goodwill_credits':
			case 'extra_deliberations':
				return `${value}`;
			default:
				return `${value}`;
		}
	}

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return 'Never';
		const date = new Date(dateStr);
		return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
	}

	async function copyCode() {
		await navigator.clipboard.writeText(promotion.code);
		copied = true;
		setTimeout(() => { copied = false; }, 2000);
	}

	const status = $derived(getStatus());
	const statusBadge = $derived(getStatusBadge(status));
	const usageText = $derived(promotion.max_uses ? `${promotion.uses_count} / ${promotion.max_uses}` : `${promotion.uses_count} / Unlimited`);
</script>

<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
	<!-- Header: Code + Status -->
	<div class="flex items-center justify-between mb-3">
		<div class="flex items-center gap-2">
			<code class="text-lg font-mono font-semibold text-neutral-900 dark:text-white">
				{promotion.code}
			</code>
			<button
				onclick={copyCode}
				class="p-1 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors"
				title="Copy code"
			>
				{#if copied}
					<Check class="w-4 h-4 text-success-500" />
				{:else}
					<Copy class="w-4 h-4" />
				{/if}
			</button>
		</div>
		<span class="inline-flex text-xs px-2 py-1 rounded-full {statusBadge.bg} {statusBadge.text}">
			{statusBadge.label}
		</span>
	</div>

	<!-- Details Grid -->
	<div class="grid grid-cols-2 gap-3 mb-4 text-sm">
		<div>
			<span class="text-neutral-500 dark:text-neutral-400">Type</span>
			<p class="text-neutral-900 dark:text-white font-medium">{formatType(promotion.type)}</p>
		</div>
		<div>
			<span class="text-neutral-500 dark:text-neutral-400">Value</span>
			<p class="text-neutral-900 dark:text-white font-medium">{formatValue(promotion.type, promotion.value)}</p>
		</div>
		<div>
			<span class="text-neutral-500 dark:text-neutral-400">Uses</span>
			<p class="text-neutral-900 dark:text-white font-medium">{usageText}</p>
		</div>
		<div>
			<span class="text-neutral-500 dark:text-neutral-400">Expires</span>
			<p class="text-neutral-900 dark:text-white font-medium">{formatDate(promotion.expires_at)}</p>
		</div>
	</div>

	<!-- Usage Progress (if max_uses set) -->
	{#if promotion.max_uses}
		<div class="mb-4">
			<div class="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-2">
				<div
					class="bg-brand-500 h-2 rounded-full transition-all"
					style="width: {Math.min((promotion.uses_count / promotion.max_uses) * 100, 100)}%"
				></div>
			</div>
		</div>
	{/if}

	<!-- Actions -->
	<div class="flex items-center justify-between">
		<span class="text-xs text-neutral-400">
			Created {formatDate(promotion.created_at)}
		</span>
		{#if promotion.is_active}
			<Button
				variant="ghost"
				size="sm"
				onclick={() => onDelete(promotion)}
			>
				{#snippet children()}
					<Trash2 class="w-4 h-4 text-error-500" />
					<span class="text-error-500">Deactivate</span>
				{/snippet}
			</Button>
		{/if}
	</div>
</div>
