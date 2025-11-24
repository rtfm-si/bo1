<script lang="ts">
	/**
	 * DeliberationComplete Event Component
	 * HIDDEN - Redundant with SynthesisComplete
	 */
	import type { CompleteEvent } from '$lib/api/sse-events';

	interface Props {
		event: CompleteEvent;
	}

	let { event }: Props = $props();
</script>

<!-- Component hidden - redundant with Synthesis Complete -->
<div style="display: none;"></div>
