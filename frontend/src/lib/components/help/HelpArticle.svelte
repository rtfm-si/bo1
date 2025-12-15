<script lang="ts">
	/**
	 * HelpArticle - Renders help article content with markdown-style formatting
	 * XSS protection via DOMPurify sanitization (defense-in-depth alongside escapeHtml)
	 */
	import type { HelpArticle } from '$lib/data/help-content';
	import { helpCategories } from '$lib/data/help-content';
	import DOMPurify from 'isomorphic-dompurify';

	interface Props {
		article: HelpArticle;
	}

	let { article }: Props = $props();

	// Get category label for breadcrumb
	const categoryLabel = $derived(
		helpCategories.find((c) => c.id === article.category)?.label || article.category
	);

	// Simple markdown-ish rendering for our structured content
	// Handles: ## headers, ### subheaders, **bold**, - lists, numbered lists
	function renderContent(content: string): string {
		const lines = content.split('\n');
		let html = '';
		let inList = false;
		let inOrderedList = false;

		for (const line of lines) {
			const trimmed = line.trim();

			// Close lists if needed
			if (inList && !trimmed.startsWith('- ')) {
				html += '</ul>';
				inList = false;
			}
			if (inOrderedList && !/^\d+\.\s/.test(trimmed)) {
				html += '</ol>';
				inOrderedList = false;
			}

			// Headers
			if (trimmed.startsWith('### ')) {
				html += `<h3 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mt-6 mb-3">${escapeHtml(trimmed.slice(4))}</h3>`;
			} else if (trimmed.startsWith('## ')) {
				html += `<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mt-8 mb-4 first:mt-0">${escapeHtml(trimmed.slice(3))}</h2>`;
			}
			// Unordered list
			else if (trimmed.startsWith('- ')) {
				if (!inList) {
					html += '<ul class="list-disc list-inside space-y-2 my-4 text-neutral-700 dark:text-neutral-300">';
					inList = true;
				}
				html += `<li>${formatInline(trimmed.slice(2))}</li>`;
			}
			// Ordered list
			else if (/^\d+\.\s/.test(trimmed)) {
				if (!inOrderedList) {
					html += '<ol class="list-decimal list-inside space-y-2 my-4 text-neutral-700 dark:text-neutral-300">';
					inOrderedList = true;
				}
				html += `<li>${formatInline(trimmed.replace(/^\d+\.\s/, ''))}</li>`;
			}
			// Empty line
			else if (trimmed === '') {
				// Skip
			}
			// Regular paragraph
			else {
				html += `<p class="text-neutral-700 dark:text-neutral-300 leading-relaxed my-3">${formatInline(trimmed)}</p>`;
			}
		}

		// Close any open lists
		if (inList) html += '</ul>';
		if (inOrderedList) html += '</ol>';

		return html;
	}

	function escapeHtml(text: string): string {
		return text
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;');
	}

	function formatInline(text: string): string {
		let result = escapeHtml(text);
		// Bold: **text**
		result = result.replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-neutral-900 dark:text-neutral-100">$1</strong>');
		// Code: `text`
		result = result.replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 bg-neutral-100 dark:bg-neutral-800 rounded text-sm font-mono">$1</code>');
		return result;
	}

	const renderedContent = $derived(DOMPurify.sanitize(renderContent(article.content)));
</script>

<article class="max-w-none">
	<!-- Breadcrumb -->
	<div class="text-sm text-neutral-500 dark:text-neutral-400 mb-4">
		<span>Help</span>
		<span class="mx-2">/</span>
		<span>{categoryLabel}</span>
	</div>

	<!-- Title -->
	<h1 class="text-2xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
		{article.title}
	</h1>

	<!-- Content -->
	<div class="prose-help">
		{@html renderedContent}
	</div>

	<!-- Keywords for SEO/search -->
	<div class="mt-8 pt-6 border-t border-neutral-200 dark:border-neutral-700">
		<p class="text-xs text-neutral-400 dark:text-neutral-500">
			Related: {article.keywords.join(', ')}
		</p>
	</div>
</article>
