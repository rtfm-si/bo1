<script lang="ts">
	/**
	 * AddPromotionModal - Create new promotion codes
	 */
	import { Button, Alert } from '$lib/components/ui';
	import { X } from 'lucide-svelte';
	import { adminApi, type CreatePromotionRequest, type Promotion } from '$lib/api/admin';

	interface Props {
		open: boolean;
		onClose: () => void;
		onCreated: (promotion: Promotion) => void;
	}

	let { open, onClose, onCreated }: Props = $props();

	let code = $state('');
	let type = $state('goodwill_credits');
	let value = $state(1);
	let maxUses = $state<number | null>(null);
	let expiresAt = $state('');
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);

	const PROMOTION_TYPES = [
		{ value: 'goodwill_credits', label: 'Goodwill Credits', hint: 'Number of free deliberations' },
		{ value: 'extra_deliberations', label: 'Extra Deliberations', hint: 'Additional deliberations beyond tier limit' },
		{ value: 'percentage_discount', label: 'Percentage Discount', hint: 'Discount percentage (1-100)' },
		{ value: 'flat_discount', label: 'Flat Discount', hint: 'Fixed dollar amount off' }
	];

	function resetForm() {
		code = '';
		type = 'goodwill_credits';
		value = 1;
		maxUses = null;
		expiresAt = '';
		error = null;
	}

	function handleClose() {
		resetForm();
		onClose();
	}

	function validate(): string | null {
		if (!code.trim()) return 'Code is required';
		if (!/^[A-Z0-9_]+$/.test(code)) return 'Code must be uppercase letters, numbers, and underscores only';
		if (code.length < 3 || code.length > 50) return 'Code must be 3-50 characters';
		if (value <= 0) return 'Value must be greater than 0';
		if (type === 'percentage_discount' && value > 100) return 'Percentage cannot exceed 100';
		if (maxUses !== null && maxUses <= 0) return 'Max uses must be greater than 0';
		if (expiresAt) {
			const expires = new Date(expiresAt);
			if (expires <= new Date()) return 'Expiration date must be in the future';
		}
		return null;
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();
		error = null;

		const validationError = validate();
		if (validationError) {
			error = validationError;
			return;
		}

		isSubmitting = true;
		try {
			const request: CreatePromotionRequest = {
				code: code.trim().toUpperCase(),
				type,
				value,
				max_uses: maxUses,
				expires_at: expiresAt ? new Date(expiresAt).toISOString() : null
			};

			const promotion = await adminApi.createPromotion(request);
			onCreated(promotion);
			handleClose();
		} catch (err: unknown) {
			if (err && typeof err === 'object' && 'message' in err) {
				error = (err as { message: string }).message;
			} else {
				error = 'Failed to create promotion';
			}
		} finally {
			isSubmitting = false;
		}
	}

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) {
			handleClose();
		}
	}
</script>

{#if open}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
	<div
		class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
		onclick={handleBackdropClick}
		role="presentation"
	>
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<div
			class="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto"
			onclick={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			tabindex="-1"
		>
			<!-- Header -->
			<div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Create Promotion</h2>
				<button
					onclick={handleClose}
					class="p-1 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors"
					aria-label="Close"
				>
					<X class="w-5 h-5" />
				</button>
			</div>

			<!-- Form -->
			<form onsubmit={handleSubmit} class="p-6 space-y-4">
				{#if error}
					<Alert variant="error">
						{#snippet children()}
							{error}
						{/snippet}
					</Alert>
				{/if}

				<!-- Code -->
				<div>
					<label for="promo-code" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						Promo Code <span class="text-error-500">*</span>
					</label>
					<input
						type="text"
						id="promo-code"
						bind:value={code}
						placeholder="e.g., WELCOME10"
						class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 uppercase"
						oninput={(e) => { code = e.currentTarget.value.toUpperCase(); }}
					/>
					<p class="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
						Uppercase letters, numbers, and underscores only
					</p>
				</div>

				<!-- Type -->
				<div>
					<label for="promo-type" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						Type <span class="text-error-500">*</span>
					</label>
					<select
						id="promo-type"
						bind:value={type}
						class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
					>
						{#each PROMOTION_TYPES as promoType}
							<option value={promoType.value}>{promoType.label}</option>
						{/each}
					</select>
					<p class="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
						{PROMOTION_TYPES.find(t => t.value === type)?.hint || ''}
					</p>
				</div>

				<!-- Value -->
				<div>
					<label for="promo-value" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						Value <span class="text-error-500">*</span>
					</label>
					<input
						type="number"
						id="promo-value"
						bind:value={value}
						min="0.01"
						step={type === 'flat_discount' ? '0.01' : '1'}
						class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
					/>
				</div>

				<!-- Max Uses -->
				<div>
					<label for="promo-max-uses" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						Max Uses
					</label>
					<input
						type="number"
						id="promo-max-uses"
						bind:value={maxUses}
						min="1"
						step="1"
						placeholder="Unlimited"
						class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
					/>
					<p class="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
						Leave empty for unlimited uses
					</p>
				</div>

				<!-- Expires At -->
				<div>
					<label for="promo-expires" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
						Expires At
					</label>
					<input
						type="datetime-local"
						id="promo-expires"
						bind:value={expiresAt}
						class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
					/>
					<p class="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
						Leave empty for no expiration
					</p>
				</div>

				<!-- Actions -->
				<div class="flex justify-end gap-3 pt-4">
					<Button variant="secondary" size="md" onclick={handleClose} disabled={isSubmitting}>
						{#snippet children()}Cancel{/snippet}
					</Button>
					<Button variant="brand" size="md" type="submit" disabled={isSubmitting}>
						{#snippet children()}{isSubmitting ? 'Creating...' : 'Create Promotion'}{/snippet}
					</Button>
				</div>
			</form>
		</div>
	</div>
{/if}
