<script lang="ts">
	/**
	 * AiDisclaimer Component
	 * Subtle disclaimer for AI-generated content, styled after OpenAI/Anthropic's approach
	 * Small, muted text - present but not intrusive
	 */
	interface Props {
		class?: string;
	}

	let { class: className = '' }: Props = $props();
</script>

<p class="text-xs text-muted-foreground text-center {className}">
	AI-generated content. Verify important information with qualified professionals.
</p>
