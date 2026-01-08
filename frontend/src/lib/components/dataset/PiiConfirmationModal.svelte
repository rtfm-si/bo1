<script lang="ts">
	/**
	 * PiiConfirmationModal - Modal for confirming PII acknowledgment before dataset upload
	 *
	 * Features:
	 * - Shows detected PII columns with type and masked sample values
	 * - Warning about data privacy obligations
	 * - Checkbox confirmation that no PII is being submitted
	 * - Cancel/Confirm actions
	 */
	import { AlertTriangle, Shield, Check, X } from 'lucide-svelte';
	import { Modal, Button, Alert, Badge } from '$lib/components/ui';

	// PII types matching backend enum
	type PiiType =
		| 'email'
		| 'ssn'
		| 'phone'
		| 'credit_card'
		| 'ip_address'
		| 'name'
		| 'address'
		| 'date_of_birth';

	interface PiiWarning {
		column_name: string;
		pii_type: PiiType;
		confidence: number;
		sample_values: string[];
		match_count: number;
	}

	interface Props {
		open: boolean;
		datasetName: string;
		piiWarnings: PiiWarning[];
		onConfirm: () => void;
		onCancel: () => void;
	}

	let { open = $bindable(), datasetName, piiWarnings, onConfirm, onCancel }: Props = $props();

	let confirmed = $state(false);
	let isSubmitting = $state(false);
	let prevOpen = $state(false);

	// Reset state when modal opens (using previous value pattern to avoid effect malpractice)
	$effect(() => {
		if (open && !prevOpen) {
			// Modal just opened - schedule reset for next tick
			setTimeout(() => {
				confirmed = false;
				isSubmitting = false;
			}, 0);
		}
		prevOpen = open;
	});

	// Human-readable PII type labels
	const piiTypeLabels: Record<PiiType, string> = {
		email: 'Email Address',
		ssn: 'Social Security Number',
		phone: 'Phone Number',
		credit_card: 'Credit Card',
		ip_address: 'IP Address',
		name: 'Personal Name',
		address: 'Physical Address',
		date_of_birth: 'Date of Birth'
	};

	// Confidence level badge variant
	function getConfidenceBadgeVariant(confidence: number): 'error' | 'warning' | 'info' {
		if (confidence >= 0.7) return 'error';
		if (confidence >= 0.4) return 'warning';
		return 'info';
	}

	function getConfidenceLabel(confidence: number): string {
		if (confidence >= 0.7) return 'High';
		if (confidence >= 0.4) return 'Medium';
		return 'Low';
	}

	async function handleConfirm() {
		if (!confirmed) return;
		isSubmitting = true;
		onConfirm();
	}

	function handleCancel() {
		onCancel();
	}
</script>

<Modal {open} title="Privacy Warning" size="lg" closable={false}>
	{#snippet children()}
		<div class="space-y-4">
			<Alert variant="warning">
				<AlertTriangle size={16} />
				<span>Potential personally identifiable information (PII) detected in <strong>{datasetName}</strong></span>
			</Alert>

			<!-- PII Warnings List -->
			<div class="space-y-3">
				<h3 class="font-medium text-sm text-neutral-700 dark:text-neutral-300">
					Detected PII Columns ({piiWarnings.length})
				</h3>

				<div class="border border-neutral-200 dark:border-neutral-700 rounded-lg divide-y divide-neutral-200 dark:divide-neutral-700">
					{#each piiWarnings as warning (warning.column_name)}
						<div class="p-3 space-y-2">
							<div class="flex items-center justify-between">
								<div class="flex items-center gap-2">
									<span class="font-mono text-sm font-medium text-neutral-900 dark:text-neutral-100">
										{warning.column_name}
									</span>
									<Badge variant="neutral" size="sm">
										{piiTypeLabels[warning.pii_type] || warning.pii_type}
									</Badge>
								</div>
								<Badge variant={getConfidenceBadgeVariant(warning.confidence)} size="sm">
									{getConfidenceLabel(warning.confidence)} confidence
								</Badge>
							</div>

							{#if warning.sample_values.length > 0}
								<div class="text-xs text-neutral-500 dark:text-neutral-400">
									<span class="font-medium">Sample matches:</span>
									{warning.sample_values.join(', ')}
								</div>
							{/if}

							<div class="text-xs text-neutral-400 dark:text-neutral-500">
								{warning.match_count} matches found in sample
							</div>
						</div>
					{/each}
				</div>
			</div>

			<!-- Privacy Warning -->
			<div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
				<div class="flex gap-3">
					<Shield class="h-5 w-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
					<div class="space-y-2 text-sm">
						<p class="font-medium text-amber-800 dark:text-amber-200">
							Data Privacy Obligations
						</p>
						<ul class="text-amber-700 dark:text-amber-300 space-y-1 list-disc list-inside">
							<li>Do not upload data containing real personal information</li>
							<li>Anonymize or pseudonymize data before uploading</li>
							<li>You are responsible for compliance with GDPR, CCPA, and other privacy regulations</li>
							<li>Board of One does not store or process personal data for analysis</li>
						</ul>
					</div>
				</div>
			</div>

			<!-- Confirmation Checkbox -->
			<div class="border-t border-neutral-200 dark:border-neutral-700 pt-4">
				<label class="flex items-start gap-3 cursor-pointer">
					<input
						type="checkbox"
						bind:checked={confirmed}
						class="mt-1 h-4 w-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500"
					/>
					<span class="text-sm text-neutral-700 dark:text-neutral-300">
						I confirm that this dataset <strong>does not contain personally identifiable information</strong>.
						If the detected patterns are false positives (e.g., product codes that resemble SSNs), I understand
						this is safe to proceed.
					</span>
				</label>
			</div>
		</div>
	{/snippet}

	{#snippet footer()}
		<div class="flex justify-end gap-3">
			<Button variant="outline" onclick={handleCancel} disabled={isSubmitting}>
				<X size={16} />
				<span>Cancel Upload</span>
			</Button>
			<Button variant="brand" onclick={handleConfirm} disabled={!confirmed || isSubmitting}>
				{#if isSubmitting}
					<span>Confirming...</span>
				{:else}
					<Check size={16} />
					<span>Confirm & Continue</span>
				{/if}
			</Button>
		</div>
	{/snippet}
</Modal>
