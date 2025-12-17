<script lang="ts">
	/**
	 * RelationshipDiagram - Visual diagram showing entity relationships
	 *
	 * Layout: Input (top) → Core (middle) → Outputs & Organization (bottom)
	 */

	type RelationKey =
		| 'context-meeting'
		| 'context-mentor'
		| 'meeting-actions'
		| 'meeting-projects'
		| 'mentor-actions'
		| 'actions-projects';

	let hoveredRelation = $state<RelationKey | null>(null);

	const relations: Record<RelationKey, { label: string; description: string }> = {
		'context-meeting': {
			label: 'Informs',
			description: 'Context and data help experts provide tailored recommendations',
		},
		'context-mentor': {
			label: 'Q&A',
			description: 'Ask the Mentor questions about your business context and data',
		},
		'meeting-actions': {
			label: 'Generates',
			description: 'Meetings generate actionable tasks from expert recommendations',
		},
		'meeting-projects': {
			label: 'Linked to',
			description: 'Meetings can be associated with projects for organization',
		},
		'mentor-actions': {
			label: 'Advises on',
			description: 'The AI Mentor provides guidance on how to complete actions',
		},
		'actions-projects': {
			label: 'Organized by',
			description: 'Actions can be grouped into projects for better tracking',
		},
	};

	function handleHover(relation: RelationKey | null) {
		hoveredRelation = relation;
	}
</script>

<div class="relationship-diagram">
	<!-- SVG Diagram -->
	<svg
		viewBox="0 0 420 220"
		class="w-full max-w-lg mx-auto"
		role="img"
		aria-label="Diagram showing relationships between Context & Data, Meeting, Mentor, Actions, and Projects"
	>
		<defs>
			<marker
				id="arrowhead"
				markerWidth="8"
				markerHeight="6"
				refX="7"
				refY="3"
				orient="auto"
				class="fill-neutral-400 dark:fill-neutral-500"
			>
				<polygon points="0 0, 8 3, 0 6" />
			</marker>
			<marker
				id="arrowhead-active"
				markerWidth="8"
				markerHeight="6"
				refX="7"
				refY="3"
				orient="auto"
				class="fill-brand-500"
			>
				<polygon points="0 0, 8 3, 0 6" />
			</marker>
		</defs>

		<!-- TOP ROW -->
		<!-- Context & Data Node (top left) -->
		<g class="node" transform="translate(80, 50)">
			<rect
				x="-60"
				y="-25"
				width="120"
				height="50"
				rx="10"
				class="fill-purple-100 dark:fill-purple-900/30 stroke-purple-500 stroke-2"
			/>
			<text
				class="fill-purple-700 dark:fill-purple-300 text-sm font-semibold"
				text-anchor="middle"
				dominant-baseline="middle"
			>
				Context & Data
			</text>
		</g>

		<!-- Meeting Node (top center) -->
		<g class="node" transform="translate(220, 50)">
			<rect
				x="-50"
				y="-25"
				width="100"
				height="50"
				rx="10"
				class="fill-brand-100 dark:fill-brand-900/30 stroke-brand-500 stroke-2"
			/>
			<text
				class="fill-brand-700 dark:fill-brand-300 text-sm font-semibold"
				text-anchor="middle"
				dominant-baseline="middle"
			>
				Meeting
			</text>
		</g>

		<!-- BOTTOM ROW -->
		<!-- Mentor Node (bottom left) -->
		<g class="node" transform="translate(80, 165)">
			<rect
				x="-50"
				y="-25"
				width="100"
				height="50"
				rx="10"
				class="fill-amber-100 dark:fill-amber-900/30 stroke-amber-500 stroke-2"
			/>
			<text
				class="fill-amber-700 dark:fill-amber-300 text-sm font-semibold"
				text-anchor="middle"
				dominant-baseline="middle"
			>
				Mentor
			</text>
		</g>

		<!-- Actions Node (bottom center) -->
		<g class="node" transform="translate(220, 165)">
			<rect
				x="-50"
				y="-25"
				width="100"
				height="50"
				rx="10"
				class="fill-success-100 dark:fill-success-900/30 stroke-success-500 stroke-2"
			/>
			<text
				class="fill-success-700 dark:fill-success-300 text-sm font-semibold"
				text-anchor="middle"
				dominant-baseline="middle"
			>
				Actions
			</text>
		</g>

		<!-- Projects Node (right side) -->
		<g class="node" transform="translate(360, 107)">
			<rect
				x="-50"
				y="-35"
				width="100"
				height="70"
				rx="10"
				class="fill-info-100 dark:fill-info-900/30 stroke-info-500 stroke-2"
			/>
			<text
				class="fill-info-700 dark:fill-info-300 text-sm font-semibold"
				text-anchor="middle"
				dominant-baseline="middle"
			>
				Projects
			</text>
		</g>

		<!-- CONNECTIONS -->

		<!-- Context & Data → Meeting -->
		<g
			role="button"
			tabindex="0"
			class="cursor-pointer"
			onmouseenter={() => handleHover('context-meeting')}
			onmouseleave={() => handleHover(null)}
			onfocus={() => handleHover('context-meeting')}
			onblur={() => handleHover(null)}
		>
			<line x1="140" y1="50" x2="165" y2="50" class="stroke-transparent stroke-[16]" />
			<line
				x1="140"
				y1="50"
				x2="165"
				y2="50"
				class="stroke-2 {hoveredRelation === 'context-meeting'
					? 'stroke-brand-500'
					: 'stroke-neutral-400 dark:stroke-neutral-500'}"
				marker-end={hoveredRelation === 'context-meeting'
					? 'url(#arrowhead-active)'
					: 'url(#arrowhead)'}
			/>
		</g>

		<!-- Context & Data → Mentor -->
		<g
			role="button"
			tabindex="0"
			class="cursor-pointer"
			onmouseenter={() => handleHover('context-mentor')}
			onmouseleave={() => handleHover(null)}
			onfocus={() => handleHover('context-mentor')}
			onblur={() => handleHover(null)}
		>
			<line x1="80" y1="75" x2="80" y2="135" class="stroke-transparent stroke-[16]" />
			<line
				x1="80"
				y1="75"
				x2="80"
				y2="135"
				class="stroke-2 {hoveredRelation === 'context-mentor'
					? 'stroke-brand-500'
					: 'stroke-neutral-400 dark:stroke-neutral-500'}"
				marker-end={hoveredRelation === 'context-mentor'
					? 'url(#arrowhead-active)'
					: 'url(#arrowhead)'}
			/>
		</g>

		<!-- Meeting → Actions -->
		<g
			role="button"
			tabindex="0"
			class="cursor-pointer"
			onmouseenter={() => handleHover('meeting-actions')}
			onmouseleave={() => handleHover(null)}
			onfocus={() => handleHover('meeting-actions')}
			onblur={() => handleHover(null)}
		>
			<line x1="220" y1="75" x2="220" y2="135" class="stroke-transparent stroke-[16]" />
			<line
				x1="220"
				y1="75"
				x2="220"
				y2="135"
				class="stroke-2 {hoveredRelation === 'meeting-actions'
					? 'stroke-brand-500'
					: 'stroke-neutral-400 dark:stroke-neutral-500'}"
				marker-end={hoveredRelation === 'meeting-actions'
					? 'url(#arrowhead-active)'
					: 'url(#arrowhead)'}
			/>
		</g>

		<!-- Meeting → Projects -->
		<g
			role="button"
			tabindex="0"
			class="cursor-pointer"
			onmouseenter={() => handleHover('meeting-projects')}
			onmouseleave={() => handleHover(null)}
			onfocus={() => handleHover('meeting-projects')}
			onblur={() => handleHover(null)}
		>
			<line x1="270" y1="60" x2="305" y2="85" class="stroke-transparent stroke-[16]" />
			<line
				x1="270"
				y1="60"
				x2="305"
				y2="85"
				class="stroke-2 {hoveredRelation === 'meeting-projects'
					? 'stroke-brand-500'
					: 'stroke-neutral-400 dark:stroke-neutral-500'}"
				marker-end={hoveredRelation === 'meeting-projects'
					? 'url(#arrowhead-active)'
					: 'url(#arrowhead)'}
			/>
		</g>

		<!-- Mentor → Actions -->
		<g
			role="button"
			tabindex="0"
			class="cursor-pointer"
			onmouseenter={() => handleHover('mentor-actions')}
			onmouseleave={() => handleHover(null)}
			onfocus={() => handleHover('mentor-actions')}
			onblur={() => handleHover(null)}
		>
			<line x1="130" y1="165" x2="165" y2="165" class="stroke-transparent stroke-[16]" />
			<line
				x1="130"
				y1="165"
				x2="165"
				y2="165"
				class="stroke-2 {hoveredRelation === 'mentor-actions'
					? 'stroke-brand-500'
					: 'stroke-neutral-400 dark:stroke-neutral-500'}"
				marker-end={hoveredRelation === 'mentor-actions'
					? 'url(#arrowhead-active)'
					: 'url(#arrowhead)'}
			/>
		</g>

		<!-- Actions → Projects -->
		<g
			role="button"
			tabindex="0"
			class="cursor-pointer"
			onmouseenter={() => handleHover('actions-projects')}
			onmouseleave={() => handleHover(null)}
			onfocus={() => handleHover('actions-projects')}
			onblur={() => handleHover(null)}
		>
			<line x1="270" y1="155" x2="305" y2="130" class="stroke-transparent stroke-[16]" />
			<line
				x1="270"
				y1="155"
				x2="305"
				y2="130"
				class="stroke-2 {hoveredRelation === 'actions-projects'
					? 'stroke-brand-500'
					: 'stroke-neutral-400 dark:stroke-neutral-500'}"
				marker-end={hoveredRelation === 'actions-projects'
					? 'url(#arrowhead-active)'
					: 'url(#arrowhead)'}
			/>
		</g>
	</svg>

	<!-- Relationship description panel -->
	<div
		class="mt-4 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800/50 h-[72px] text-center flex flex-col justify-center"
	>
		{#if hoveredRelation}
			<p class="text-sm font-medium text-brand-600 dark:text-brand-400">
				{relations[hoveredRelation].label}
			</p>
			<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
				{relations[hoveredRelation].description}
			</p>
		{:else}
			<p class="text-sm text-neutral-500 dark:text-neutral-400">
				Hover or tap a connection to learn more
			</p>
		{/if}
	</div>
</div>

<style>
	.relationship-diagram :global(svg text) {
		user-select: none;
	}

	.relationship-diagram :global(.node rect) {
		transition:
			fill 0.2s,
			stroke 0.2s;
	}

	.relationship-diagram :global(line),
	.relationship-diagram :global(path) {
		transition: stroke 0.2s;
	}
</style>
