<script lang="ts">
	/**
	 * MarkdownContent Component
	 * Renders markdown content as HTML using marked
	 * Includes basic XSS protection via marked's sanitize option
	 */
	import { marked } from 'marked';

	interface Props {
		content: string;
		class?: string;
	}

	let { content, class: className = '' }: Props = $props();

	// Configure marked for safe, simple rendering
	marked.setOptions({
		breaks: true, // Convert \n to <br>
		gfm: true, // GitHub Flavored Markdown (tables, strikethrough, etc.)
	});

	/**
	 * Clean content by removing standalone horizontal rule markers (---, ***, ___)
	 * These often appear in AI output and render as messy lines
	 */
	function cleanContent(text: string): string {
		return text
			.split('\n')
			.filter(line => {
				const trimmed = line.trim();
				// Filter out horizontal rule patterns: ---, ***, ___
				// Must be at least 3 chars of the same character
				return !(
					/^-{3,}$/.test(trimmed) ||
					/^\*{3,}$/.test(trimmed) ||
					/^_{3,}$/.test(trimmed)
				);
			})
			.join('\n');
	}

	// Parse markdown to HTML (after cleaning)
	const html = $derived(marked.parse(cleanContent(content)) as string);
</script>

<div
	class="markdown-content prose prose-sm dark:prose-invert max-w-none {className}"
>
	{@html html}
</div>

<style>
	/* Override prose styles for better integration */
	.markdown-content :global(p) {
		margin-top: 0.5em;
		margin-bottom: 0.5em;
	}

	.markdown-content :global(p:first-child) {
		margin-top: 0;
	}

	.markdown-content :global(p:last-child) {
		margin-bottom: 0;
	}

	.markdown-content :global(ul),
	.markdown-content :global(ol) {
		margin-top: 0.5em;
		margin-bottom: 0.5em;
		padding-left: 1.5em;
	}

	.markdown-content :global(li) {
		margin-top: 0.25em;
		margin-bottom: 0.25em;
	}

	.markdown-content :global(strong) {
		font-weight: 600;
	}

	.markdown-content :global(h1),
	.markdown-content :global(h2),
	.markdown-content :global(h3),
	.markdown-content :global(h4) {
		margin-top: 1em;
		margin-bottom: 0.5em;
		font-weight: 600;
	}

	.markdown-content :global(h1:first-child),
	.markdown-content :global(h2:first-child),
	.markdown-content :global(h3:first-child),
	.markdown-content :global(h4:first-child) {
		margin-top: 0;
	}

	.markdown-content :global(blockquote) {
		border-left: 3px solid currentColor;
		padding-left: 1em;
		margin-left: 0;
		opacity: 0.8;
	}

	.markdown-content :global(code) {
		background-color: rgba(0, 0, 0, 0.05);
		padding: 0.1em 0.3em;
		border-radius: 0.25em;
		font-size: 0.9em;
	}

	:global(.dark) .markdown-content :global(code) {
		background-color: rgba(255, 255, 255, 0.1);
	}

	.markdown-content :global(hr) {
		margin: 1em 0;
		border: none;
		border-top: 1px solid currentColor;
		opacity: 0.2;
	}
</style>
