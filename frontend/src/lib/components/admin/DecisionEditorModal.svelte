<script lang="ts">
	/**
	 * DecisionEditorModal - Create and edit published decisions
	 */
	import { Button, Alert } from '$lib/components/ui';
	import { X, Plus, Trash2 } from 'lucide-svelte';
	import {
		adminApi,
		type Decision,
		type DecisionCreate,
		type DecisionUpdate,
		type ExpertPerspective,
		type FAQ,
		DECISION_CATEGORIES,
		type DecisionCategory
	} from '$lib/api/admin';

	interface Props {
		decision: Decision | null;
		onclose: () => void;
		onsave: (decision: Decision) => void;
	}

	let { decision, onclose, onsave }: Props = $props();

	// Form state
	let title = $state('');
	let category = $state<DecisionCategory>('hiring');
	let slug = $state('');
	let metaDescription = $state('');
	let stage = $state('');
	let constraints = $state<string[]>([]);
	let situation = $state('');
	let expertPerspectives = $state<ExpertPerspective[]>([]);
	let synthesis = $state('');
	let faqs = $state<FAQ[]>([]);

	// Sync form state when decision prop changes
	$effect(() => {
		const d = decision;
		setTimeout(() => {
			title = d?.title || '';
			category = d?.category || 'hiring';
			slug = d?.slug || '';
			metaDescription = d?.meta_description || '';
			stage = d?.founder_context?.stage || '';
			constraints = d?.founder_context?.constraints || [];
			situation = d?.founder_context?.situation || '';
			expertPerspectives = d?.expert_perspectives || [];
			synthesis = d?.synthesis || '';
			faqs = d?.faqs || [];
		}, 0);
	});

	let isSubmitting = $state(false);
	let error = $state<string | null>(null);
	let activeTab = $state<'basic' | 'content' | 'seo'>('basic');
	let newConstraint = $state('');

	const isEditing = $derived(!!decision);

	function validate(): string | null {
		if (!title.trim()) return 'Title is required';
		if (title.length < 10) return 'Title must be at least 10 characters';
		if (!category) return 'Category is required';
		if (metaDescription.length > 300) return 'Meta description must be under 300 characters';
		return null;
	}

	function addConstraint() {
		if (newConstraint.trim()) {
			constraints = [...constraints, newConstraint.trim()];
			newConstraint = '';
		}
	}

	function removeConstraint(index: number) {
		constraints = constraints.filter((_, i) => i !== index);
	}

	function addPerspective() {
		expertPerspectives = [...expertPerspectives, { persona_name: '', quote: '' }];
	}

	function removePerspective(index: number) {
		expertPerspectives = expertPerspectives.filter((_, i) => i !== index);
	}

	function addFaq() {
		faqs = [...faqs, { question: '', answer: '' }];
	}

	function removeFaq(index: number) {
		faqs = faqs.filter((_, i) => i !== index);
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
			const founderContext = {
				stage: stage.trim() || undefined,
				constraints: constraints.length > 0 ? constraints : undefined,
				situation: situation.trim() || undefined
			};

			const validPerspectives = expertPerspectives.filter(
				(p) => p.persona_name.trim() && p.quote.trim()
			);
			const validFaqs = faqs.filter((f) => f.question.trim() && f.answer.trim());

			if (isEditing && decision) {
				const updates: DecisionUpdate = {
					title: title.trim(),
					category,
					slug: slug.trim() || undefined,
					meta_description: metaDescription.trim() || undefined,
					founder_context: founderContext,
					expert_perspectives: validPerspectives.length > 0 ? validPerspectives : undefined,
					synthesis: synthesis.trim() || undefined,
					faqs: validFaqs.length > 0 ? validFaqs : undefined
				};
				const updated = await adminApi.updateDecision(decision.id, updates);
				onsave(updated);
			} else {
				const request: DecisionCreate = {
					title: title.trim(),
					category,
					founder_context: founderContext,
					meta_description: metaDescription.trim() || undefined,
					expert_perspectives: validPerspectives.length > 0 ? validPerspectives : undefined,
					synthesis: synthesis.trim() || undefined,
					faqs: validFaqs.length > 0 ? validFaqs : undefined
				};
				const created = await adminApi.createDecision(request);
				onsave(created);
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to save decision';
		} finally {
			isSubmitting = false;
		}
	}
</script>

<div
	class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
	role="dialog"
	aria-modal="true"
>
	<div
		class="bg-white dark:bg-neutral-800 rounded-xl shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col"
	>
		<!-- Header -->
		<div
			class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700"
		>
			<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
				{isEditing ? 'Edit Decision' : 'New Decision'}
			</h2>
			<button
				onclick={onclose}
				class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
				aria-label="Close"
			>
				<X class="w-5 h-5 text-neutral-500" />
			</button>
		</div>

		<!-- Tabs -->
		<div class="flex border-b border-neutral-200 dark:border-neutral-700 px-6">
			{#each ['basic', 'content', 'seo'] as tab}
				<button
					class="px-4 py-3 text-sm font-medium border-b-2 transition-colors {activeTab === tab
						? 'border-brand-500 text-brand-600 dark:text-brand-400'
						: 'border-transparent text-neutral-500 hover:text-neutral-700'}"
					onclick={() => (activeTab = tab as typeof activeTab)}
				>
					{tab === 'basic' ? 'Basic Info' : tab === 'content' ? 'Content' : 'SEO'}
				</button>
			{/each}
		</div>

		<!-- Form -->
		<form onsubmit={handleSubmit} class="flex-1 overflow-y-auto p-6">
			{#if error}
				<Alert variant="error" class="mb-4">{error}</Alert>
			{/if}

			{#if activeTab === 'basic'}
				<div class="space-y-4">
					<!-- Title -->
					<div>
						<label
							for="title"
							class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
						>
							Decision Question (H1) *
						</label>
						<input
							id="title"
							type="text"
							bind:value={title}
							placeholder="Should I hire my first engineer or use contractors?"
							class="w-full px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400"
						/>
					</div>

					<!-- Category -->
					<div>
						<label
							for="category"
							class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
						>
							Category *
						</label>
						<select
							id="category"
							bind:value={category}
							class="w-full px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white"
						>
							{#each DECISION_CATEGORIES as cat}
								<option value={cat}>{cat.charAt(0).toUpperCase() + cat.slice(1)}</option>
							{/each}
						</select>
					</div>

					{#if isEditing}
						<!-- Slug (only editable when editing) -->
						<div>
							<label
								for="slug"
								class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
							>
								URL Slug
							</label>
							<div class="flex items-center gap-2">
								<span class="text-neutral-500 text-sm">/decisions/{category}/</span>
								<input
									id="slug"
									type="text"
									bind:value={slug}
									class="flex-1 px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white"
								/>
							</div>
						</div>
					{/if}

					<!-- Founder Context -->
					<div class="border-t border-neutral-200 dark:border-neutral-700 pt-4 mt-4">
						<h3 class="text-sm font-medium text-neutral-900 dark:text-white mb-3">
							Founder Context
						</h3>

						<div class="space-y-3">
							<div>
								<label
									for="stage"
									class="block text-sm text-neutral-600 dark:text-neutral-400 mb-1"
								>
									Stage
								</label>
								<input
									id="stage"
									type="text"
									bind:value={stage}
									placeholder="£50-200k ARR"
									class="w-full px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400"
								/>
							</div>

							<div>
								<label class="block text-sm text-neutral-600 dark:text-neutral-400 mb-1">
									Constraints
								</label>
								<div class="flex gap-2 mb-2">
									<input
										type="text"
										bind:value={newConstraint}
										placeholder="Add a constraint..."
										class="flex-1 px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400"
										onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), addConstraint())}
									/>
									<Button type="button" variant="outline" size="sm" onclick={addConstraint}>
										<Plus class="w-4 h-4" />
									</Button>
								</div>
								{#if constraints.length > 0}
									<div class="flex flex-wrap gap-2">
										{#each constraints as constraint, i}
											<span
												class="inline-flex items-center gap-1 px-2 py-1 rounded bg-neutral-100 dark:bg-neutral-700 text-sm text-neutral-700 dark:text-neutral-300"
											>
												{constraint}
												<button
													type="button"
													onclick={() => removeConstraint(i)}
													class="hover:text-error-500"
												>
													<X class="w-3 h-3" />
												</button>
											</span>
										{/each}
									</div>
								{/if}
							</div>

							<div>
								<label
									for="situation"
									class="block text-sm text-neutral-600 dark:text-neutral-400 mb-1"
								>
									Situation
								</label>
								<textarea
									id="situation"
									bind:value={situation}
									placeholder="Paying contractors, considering hiring first FTE"
									rows="2"
									class="w-full px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400"
								></textarea>
							</div>
						</div>
					</div>
				</div>
			{:else if activeTab === 'content'}
				<div class="space-y-6">
					<!-- Expert Perspectives -->
					<div>
						<div class="flex items-center justify-between mb-3">
							<h3 class="text-sm font-medium text-neutral-900 dark:text-white">
								Expert Perspectives
							</h3>
							<Button type="button" variant="outline" size="sm" onclick={addPerspective}>
								<Plus class="w-4 h-4 mr-1" />
								Add
							</Button>
						</div>
						<div class="space-y-3">
							{#each expertPerspectives as perspective, i}
								<div
									class="p-3 border border-neutral-200 dark:border-neutral-600 rounded-lg space-y-2"
								>
									<div class="flex items-center gap-2">
										<input
											type="text"
											bind:value={perspective.persona_name}
											placeholder="Expert name (e.g., Growth Operator)"
											class="flex-1 px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 text-sm"
										/>
										<button
											type="button"
											onclick={() => removePerspective(i)}
											class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg"
										>
											<Trash2 class="w-4 h-4 text-error-500" />
										</button>
									</div>
									<textarea
										bind:value={perspective.quote}
										placeholder="Expert's viewpoint and recommendation..."
										rows="3"
										class="w-full px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 text-sm"
									></textarea>
								</div>
							{/each}
							{#if expertPerspectives.length === 0}
								<p class="text-sm text-neutral-500 dark:text-neutral-400 text-center py-4">
									No perspectives yet. Add expert viewpoints to display on the page.
								</p>
							{/if}
						</div>
					</div>

					<!-- Synthesis -->
					<div>
						<label
							for="synthesis"
							class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
						>
							Synthesis / Recommendation
						</label>
						<textarea
							id="synthesis"
							bind:value={synthesis}
							placeholder="Board synthesis and balanced recommendation..."
							rows="6"
							class="w-full px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400"
						></textarea>
					</div>

					<!-- FAQs -->
					<div>
						<div class="flex items-center justify-between mb-3">
							<h3 class="text-sm font-medium text-neutral-900 dark:text-white">FAQs</h3>
							<Button type="button" variant="outline" size="sm" onclick={addFaq}>
								<Plus class="w-4 h-4 mr-1" />
								Add FAQ
							</Button>
						</div>
						<div class="space-y-3">
							{#each faqs as faq, i}
								<div
									class="p-3 border border-neutral-200 dark:border-neutral-600 rounded-lg space-y-2"
								>
									<div class="flex items-center gap-2">
										<input
											type="text"
											bind:value={faq.question}
											placeholder="Question"
											class="flex-1 px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 text-sm"
										/>
										<button
											type="button"
											onclick={() => removeFaq(i)}
											class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg"
										>
											<Trash2 class="w-4 h-4 text-error-500" />
										</button>
									</div>
									<textarea
										bind:value={faq.answer}
										placeholder="Answer"
										rows="2"
										class="w-full px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 text-sm"
									></textarea>
								</div>
							{/each}
							{#if faqs.length === 0}
								<p class="text-sm text-neutral-500 dark:text-neutral-400 text-center py-4">
									No FAQs yet. Add questions and answers for SEO schema.
								</p>
							{/if}
						</div>
					</div>
				</div>
			{:else if activeTab === 'seo'}
				<div class="space-y-4">
					<div>
						<label
							for="metaDescription"
							class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
						>
							Meta Description
							<span class="font-normal text-neutral-500">({metaDescription.length}/300)</span>
						</label>
						<textarea
							id="metaDescription"
							bind:value={metaDescription}
							placeholder="SEO description for search results (150-160 characters ideal)"
							rows="3"
							maxlength="300"
							class="w-full px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400"
						></textarea>
					</div>

					<div class="bg-neutral-50 dark:bg-neutral-700/50 rounded-lg p-4">
						<h4 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
							Schema Markup Preview
						</h4>
						<p class="text-xs text-neutral-500 dark:text-neutral-400">
							This page will include Article, FAQPage, and BreadcrumbList schema for rich search
							results.
						</p>
						<ul class="mt-2 text-xs text-neutral-600 dark:text-neutral-400 space-y-1">
							<li>• {expertPerspectives.length} expert perspectives</li>
							<li>• {faqs.length} FAQs for FAQ schema</li>
							<li>• Breadcrumb: Home → Decisions → {category} → [Title]</li>
						</ul>
					</div>
				</div>
			{/if}
		</form>

		<!-- Footer -->
		<div
			class="flex items-center justify-end gap-3 px-6 py-4 border-t border-neutral-200 dark:border-neutral-700"
		>
			<Button variant="outline" onclick={onclose} disabled={isSubmitting}>Cancel</Button>
			<Button onclick={handleSubmit} disabled={isSubmitting}>
				{isSubmitting ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Decision'}
			</Button>
		</div>
	</div>
</div>
