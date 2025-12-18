<script lang="ts">
	/**
	 * SendEmailModal - Send branded emails to users from admin panel
	 */
	import { Button, Alert } from '$lib/components/ui';
	import { X, Mail, Check } from 'lucide-svelte';
	import { adminApi, type SendEmailRequest, type SendEmailResponse, type EmailTemplateType } from '$lib/api/admin';

	interface Props {
		open: boolean;
		userId: string;
		userEmail: string;
		onClose: () => void;
		onSent?: (response: SendEmailResponse) => void;
	}

	let { open, userId, userEmail, onClose, onSent }: Props = $props();

	let templateType = $state<EmailTemplateType>('welcome');
	let subject = $state('');
	let body = $state('');
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);
	let success = $state<string | null>(null);

	const TEMPLATE_OPTIONS: { value: EmailTemplateType; label: string; description: string }[] = [
		{
			value: 'welcome',
			label: 'Welcome Email',
			description: 'Standard welcome message with getting started tips'
		},
		{
			value: 'custom',
			label: 'Custom Message',
			description: 'Write a custom message with your own subject and content'
		}
	];

	function resetForm() {
		templateType = 'welcome';
		subject = '';
		body = '';
		error = null;
		success = null;
	}

	function handleClose() {
		resetForm();
		onClose();
	}

	function validate(): string | null {
		if (templateType === 'custom') {
			if (!subject.trim()) return 'Subject is required for custom emails';
			if (subject.length > 200) return 'Subject must be 200 characters or less';
			if (!body.trim()) return 'Body is required for custom emails';
			if (body.length > 5000) return 'Body must be 5000 characters or less';
		}
		return null;
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();
		error = null;
		success = null;

		const validationError = validate();
		if (validationError) {
			error = validationError;
			return;
		}

		isSubmitting = true;
		try {
			const request: SendEmailRequest = {
				template_type: templateType,
				...(templateType === 'custom' && {
					subject: subject.trim(),
					body: body.trim()
				})
			};

			const response = await adminApi.sendUserEmail(userId, request);

			if (response.sent) {
				success = `Email sent successfully to ${response.email}`;
				onSent?.(response);
				// Auto-close after short delay on success
				setTimeout(() => {
					handleClose();
				}, 2000);
			} else {
				error = response.message || 'Failed to send email';
			}
		} catch (err: unknown) {
			if (err && typeof err === 'object' && 'message' in err) {
				error = (err as { message: string }).message;
			} else {
				error = 'Failed to send email';
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
			class="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto"
			onclick={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			tabindex="-1"
		>
			<!-- Header -->
			<div
				class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700"
			>
				<div class="flex items-center gap-2">
					<Mail class="w-5 h-5 text-brand-500" />
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Send Email</h2>
				</div>
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
				<!-- Recipient info -->
				<div class="bg-neutral-50 dark:bg-neutral-900 rounded-md p-3">
					<p class="text-sm text-neutral-600 dark:text-neutral-400">
						Sending to: <span class="font-medium text-neutral-900 dark:text-white">{userEmail}</span>
					</p>
				</div>

				{#if error}
					<Alert variant="error">
						{#snippet children()}
							{error}
						{/snippet}
					</Alert>
				{/if}

				{#if success}
					<Alert variant="success">
						{#snippet children()}
							<span class="flex items-center gap-2">
								<Check class="w-4 h-4" />
								{success}
							</span>
						{/snippet}
					</Alert>
				{/if}

				<!-- Template Type -->
				<div>
					<label class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
						Email Template <span class="text-error-500">*</span>
					</label>
					<div class="space-y-2">
						{#each TEMPLATE_OPTIONS as option}
							<label
								class="flex items-start gap-3 p-3 border rounded-md cursor-pointer transition-colors {templateType ===
								option.value
									? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20'
									: 'border-neutral-200 dark:border-neutral-700 hover:border-neutral-300 dark:hover:border-neutral-600'}"
							>
								<input
									type="radio"
									name="template"
									value={option.value}
									bind:group={templateType}
									class="mt-1"
								/>
								<div>
									<span class="font-medium text-neutral-900 dark:text-white">{option.label}</span>
									<p class="text-sm text-neutral-500 dark:text-neutral-400">{option.description}</p>
								</div>
							</label>
						{/each}
					</div>
				</div>

				<!-- Custom fields (only shown for custom template) -->
				{#if templateType === 'custom'}
					<!-- Subject -->
					<div>
						<label
							for="email-subject"
							class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
						>
							Subject <span class="text-error-500">*</span>
						</label>
						<input
							type="text"
							id="email-subject"
							bind:value={subject}
							placeholder="Enter email subject"
							maxlength="200"
							class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
						/>
						<p class="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
							{subject.length}/200 characters
						</p>
					</div>

					<!-- Body -->
					<div>
						<label
							for="email-body"
							class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
						>
							Message <span class="text-error-500">*</span>
						</label>
						<textarea
							id="email-body"
							bind:value={body}
							placeholder="Enter your message..."
							rows="6"
							maxlength="5000"
							class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 resize-y"
						></textarea>
						<p class="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
							{body.length}/5000 characters. The message will be wrapped in Board of One branding.
						</p>
					</div>
				{/if}

				<!-- Actions -->
				<div class="flex justify-end gap-3 pt-4">
					<Button variant="secondary" size="md" onclick={handleClose} disabled={isSubmitting}>
						{#snippet children()}Cancel{/snippet}
					</Button>
					<Button variant="brand" size="md" type="submit" disabled={isSubmitting || !!success}>
						{#snippet children()}
							{#if isSubmitting}
								Sending...
							{:else if success}
								Sent!
							{:else}
								Send Email
							{/if}
						{/snippet}
					</Button>
				</div>
			</form>
		</div>
	</div>
{/if}
