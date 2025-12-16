<script lang="ts">
	/**
	 * RelationshipDiagram - Visual diagram showing entity relationships
	 *
	 * Displays: Meeting → Actions, Meeting → Projects, Projects → Actions
	 * with interactive hover states explaining each relationship.
	 */

	type RelationKey = 'meeting-actions' | 'meeting-projects' | 'project-actions';

	let hoveredRelation = $state<RelationKey | null>(null);

	const relations: Record<RelationKey, { label: string; description: string }> = {
		'meeting-actions': {
			label: 'Generates',
			description: 'Meetings generate actionable tasks from expert recommendations',
		},
		'meeting-projects': {
			label: 'Linked to',
			description: 'Meetings can be associated with projects for organization',
		},
		'project-actions': {
			label: 'Contains',
			description: 'Projects group related actions together',
		},
	};

	function handleHover(relation: RelationKey | null) {
		hoveredRelation = relation;
	}
</script>

<div class="relationship-diagram">
	<!-- SVG Diagram -->
	<svg
		viewBox="0 0 400 280"
		class="w-full max-w-md mx-auto"
		role="img"
		aria-label="Diagram showing relationships between Meetings, Actions, and Projects"
	>
		<defs>
			<!-- Arrow marker -->
			<marker
				id="arrowhead"
				markerWidth="10"
				markerHeight="7"
				refX="9"
				refY="3.5"
				orient="auto"
				class="fill-neutral-400 dark:fill-neutral-500"
			>
				<polygon points="0 0, 10 3.5, 0 7" />
			</marker>
			<marker
				id="arrowhead-active"
				markerWidth="10"
				markerHeight="7"
				refX="9"
				refY="3.5"
				orient="auto"
				class="fill-brand-500"
			>
				<polygon points="0 0, 10 3.5, 0 7" />
			</marker>
		</defs>

		<!-- Meeting Node (top center) -->
		<g class="node" transform="translate(200, 50)">
			<rect
				x="-60"
				y="-25"
				width="120"
				height="50"
				rx="8"
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

		<!-- Actions Node (bottom left) -->
		<g class="node" transform="translate(100, 220)">
			<rect
				x="-55"
				y="-25"
				width="110"
				height="50"
				rx="8"
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

		<!-- Projects Node (bottom right) -->
		<g class="node" transform="translate(300, 220)">
			<rect
				x="-55"
				y="-25"
				width="110"
				height="50"
				rx="8"
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

		<!-- Meeting → Actions line -->
		<g
			role="button"
			tabindex="0"
			class="cursor-pointer"
			onmouseenter={() => handleHover('meeting-actions')}
			onmouseleave={() => handleHover(null)}
			onfocus={() => handleHover('meeting-actions')}
			onblur={() => handleHover(null)}
		>
			<line
				x1="170"
				y1="75"
				x2="115"
				y2="190"
				class="stroke-2 {hoveredRelation === 'meeting-actions'
					? 'stroke-brand-500'
					: 'stroke-neutral-400 dark:stroke-neutral-500'}"
				marker-end={hoveredRelation === 'meeting-actions'
					? 'url(#arrowhead-active)'
					: 'url(#arrowhead)'}
			/>
			<text
				x="125"
				y="130"
				class="text-xs {hoveredRelation === 'meeting-actions'
					? 'fill-brand-600 dark:fill-brand-400 font-medium'
					: 'fill-neutral-500 dark:fill-neutral-400'}"
				text-anchor="middle"
				transform="rotate(-50, 125, 130)"
			>
				generates
			</text>
		</g>

		<!-- Meeting → Projects line -->
		<g
			role="button"
			tabindex="0"
			class="cursor-pointer"
			onmouseenter={() => handleHover('meeting-projects')}
			onmouseleave={() => handleHover(null)}
			onfocus={() => handleHover('meeting-projects')}
			onblur={() => handleHover(null)}
		>
			<line
				x1="230"
				y1="75"
				x2="285"
				y2="190"
				class="stroke-2 {hoveredRelation === 'meeting-projects'
					? 'stroke-brand-500'
					: 'stroke-neutral-400 dark:stroke-neutral-500'}"
				marker-end={hoveredRelation === 'meeting-projects'
					? 'url(#arrowhead-active)'
					: 'url(#arrowhead)'}
			/>
			<text
				x="275"
				y="130"
				class="text-xs {hoveredRelation === 'meeting-projects'
					? 'fill-brand-600 dark:fill-brand-400 font-medium'
					: 'fill-neutral-500 dark:fill-neutral-400'}"
				text-anchor="middle"
				transform="rotate(50, 275, 130)"
			>
				linked to
			</text>
		</g>

		<!-- Projects → Actions line -->
		<g
			role="button"
			tabindex="0"
			class="cursor-pointer"
			onmouseenter={() => handleHover('project-actions')}
			onmouseleave={() => handleHover(null)}
			onfocus={() => handleHover('project-actions')}
			onblur={() => handleHover(null)}
		>
			<line
				x1="245"
				y1="220"
				x2="160"
				y2="220"
				class="stroke-2 {hoveredRelation === 'project-actions'
					? 'stroke-brand-500'
					: 'stroke-neutral-400 dark:stroke-neutral-500'}"
				marker-end={hoveredRelation === 'project-actions'
					? 'url(#arrowhead-active)'
					: 'url(#arrowhead)'}
			/>
			<text
				x="200"
				y="238"
				class="text-xs {hoveredRelation === 'project-actions'
					? 'fill-brand-600 dark:fill-brand-400 font-medium'
					: 'fill-neutral-500 dark:fill-neutral-400'}"
				text-anchor="middle"
			>
				contains
			</text>
		</g>
	</svg>

	<!-- Relationship description panel -->
	<div
		class="mt-4 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800/50 min-h-[60px] text-center transition-all"
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

	.relationship-diagram :global(line) {
		transition: stroke 0.2s;
	}
</style>
