<script lang="ts">
	/**
	 * GlobalGanttChart - Gantt chart for all user actions across sessions
	 *
	 * Uses frappe-gantt library for rendering.
	 * Features:
	 * - Status-based color coding
	 * - Dependency arrows
	 * - Click to navigate to action details
	 */
	import type { GlobalGanttResponse, GlobalGanttActionData, ActionStatus } from '$lib/api/types';
	import type { Action } from 'svelte/action';

	interface Props {
		data: GlobalGanttResponse;
		onTaskClick?: (actionId: string) => void;
		viewMode?: 'Day' | 'Week' | 'Month' | 'Quarter' | 'Year';
	}

	let {
		data,
		onTaskClick,
		viewMode = 'Week'
	}: Props = $props();

	// Status to color mapping
	const statusColors: Record<ActionStatus, string> = {
		todo: '#9CA3AF', // neutral-400
		in_progress: '#6366F1', // brand-500
		blocked: '#EF4444', // error-500
		in_review: '#A855F7', // purple-500
		done: '#22C55E', // success-500
		cancelled: '#6B7280' // neutral-500
	};

	// Convert global action data to frappe-gantt task format
	function convertToGanttTasks(actions: GlobalGanttActionData[]) {
		return actions.map((action) => ({
			id: action.id,
			name: action.name,
			start: action.start,
			end: action.end,
			progress: action.progress,
			dependencies: action.dependencies,
			custom_class: `gantt-status-${action.status}`
		}));
	}

	function formatDate(date: Date): string {
		return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	}

	function injectStatusStyles() {
		const styleId = 'global-gantt-status-styles';
		if (document.getElementById(styleId)) return;

		const style = document.createElement('style');
		style.id = styleId;
		style.textContent = `
			/* Status bar colors */
			.gantt-status-todo .bar { fill: ${statusColors.todo} !important; }
			.gantt-status-in_progress .bar { fill: ${statusColors.in_progress} !important; }
			.gantt-status-blocked .bar { fill: ${statusColors.blocked} !important; }
			.gantt-status-in_review .bar { fill: ${statusColors.in_review} !important; }
			.gantt-status-done .bar { fill: ${statusColors.done} !important; }
			.gantt-status-cancelled .bar { fill: ${statusColors.cancelled} !important; opacity: 0.6; }

			/* Progress bar fill */
			.gantt-status-todo .bar-progress { fill: ${statusColors.todo}80 !important; }
			.gantt-status-in_progress .bar-progress { fill: ${statusColors.in_progress}CC !important; }
			.gantt-status-blocked .bar-progress { fill: ${statusColors.blocked}80 !important; }
			.gantt-status-in_review .bar-progress { fill: ${statusColors.in_review}CC !important; }
			.gantt-status-done .bar-progress { fill: ${statusColors.done}CC !important; }
			.gantt-status-cancelled .bar-progress { fill: ${statusColors.cancelled}80 !important; }

			/* Popup styles */
			.global-gantt-popup {
				padding: 12px;
				min-width: 200px;
			}
			.global-gantt-popup-title {
				font-weight: 600;
				margin: 0 0 8px 0;
				font-size: 14px;
				color: var(--color-foreground, #1f2937);
			}
			.global-gantt-popup-status {
				display: inline-block;
				padding: 2px 8px;
				border-radius: 4px;
				font-size: 12px;
				font-weight: 500;
				margin-bottom: 8px;
			}
			.global-gantt-popup-status.status-todo { background: ${statusColors.todo}20; color: ${statusColors.todo}; }
			.global-gantt-popup-status.status-in_progress { background: ${statusColors.in_progress}20; color: ${statusColors.in_progress}; }
			.global-gantt-popup-status.status-blocked { background: ${statusColors.blocked}20; color: ${statusColors.blocked}; }
			.global-gantt-popup-status.status-in_review { background: ${statusColors.in_review}20; color: ${statusColors.in_review}; }
			.global-gantt-popup-status.status-done { background: ${statusColors.done}20; color: ${statusColors.done}; }
			.global-gantt-popup-status.status-cancelled { background: ${statusColors.cancelled}20; color: ${statusColors.cancelled}; }

			.global-gantt-popup-dates {
				font-size: 12px;
				color: var(--color-muted, #6b7280);
				display: flex;
				gap: 8px;
				align-items: center;
			}
			.global-gantt-popup-hint {
				font-size: 11px;
				color: var(--color-brand, #6366f1);
				margin-top: 8px;
				font-style: italic;
			}

			/* Dependency arrows */
			.gantt .arrow {
				stroke: var(--color-border, #e5e7eb) !important;
				stroke-width: 1.5 !important;
			}
			.gantt .arrow:hover {
				stroke: var(--color-brand, #6366f1) !important;
			}

			/* Today line */
			.gantt .today-highlight {
				fill: var(--color-brand, #6366f1) !important;
				opacity: 0.1;
			}

			/* Bar hover */
			.gantt .bar-wrapper:hover .bar {
				filter: brightness(1.1);
				cursor: pointer;
			}
		`;
		document.head.appendChild(style);
	}

	type ViewMode = 'Day' | 'Week' | 'Month' | 'Quarter' | 'Year';

	// Svelte action for initializing the Gantt chart
	const ganttAction: Action<HTMLDivElement, {
		data: GlobalGanttResponse;
		viewMode: ViewMode;
		onTaskClick?: (actionId: string) => void;
	}> = (node, params) => {
		let ganttInstance: any = null;

		async function init() {
			if (!params.data.actions.length) return;

			// Dynamic import to avoid SSR issues
			const Gantt = (await import('frappe-gantt')).default;
			const tasks = convertToGanttTasks(params.data.actions);

			if (tasks.length === 0) return;

			// Clear previous content
			node.innerHTML = '';

			ganttInstance = new Gantt(node, tasks, {
				view_mode: params.viewMode,
				date_format: 'YYYY-MM-DD',
				popup_trigger: 'click',
				custom_popup_html: (task: any) => {
					const action = params.data.actions.find((a) => a.id === task.id);
					if (!action) return '';

					const statusLabel = {
						todo: 'To Do',
						in_progress: 'In Progress',
						blocked: 'Blocked',
						in_review: 'In Review',
						done: 'Done',
						cancelled: 'Cancelled'
					}[action.status];

					return `
						<div class="global-gantt-popup">
							<h4 class="global-gantt-popup-title">${task.name}</h4>
							<div class="global-gantt-popup-status status-${action.status}">${statusLabel}</div>
							<div class="global-gantt-popup-dates">
								<span>${formatDate(task._start)}</span>
								<span>&rarr;</span>
								<span>${formatDate(task._end)}</span>
							</div>
							${params.onTaskClick ? '<div class="global-gantt-popup-hint">Click to view details</div>' : ''}
						</div>
					`;
				},
				on_click: (task: any) => {
					if (params.onTaskClick) {
						params.onTaskClick(task.id);
					}
				},
				on_date_change: () => {
					// Read-only in global view
				},
				on_progress_change: () => {
					// Progress changes are handled via action status updates
				}
			});

			injectStatusStyles();
		}

		init();

		return {
			update(newParams) {
				// Reinitialize when data changes
				params = newParams;
				init();
			},
			destroy() {
				if (ganttInstance) {
					node.innerHTML = '';
					ganttInstance = null;
				}
			}
		};
	};

	// Determine if we have any tasks to display
	const hasTasks = $derived(data.actions.length > 0);
</script>

<div class="gantt-container">
	{#if !hasTasks}
		<div class="empty-state">
			<div class="empty-icon">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					width="48"
					height="48"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
				>
					<rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
					<line x1="16" y1="2" x2="16" y2="6" />
					<line x1="8" y1="2" x2="8" y2="6" />
					<line x1="3" y1="10" x2="21" y2="10" />
					<line x1="8" y1="14" x2="16" y2="14" />
					<line x1="8" y1="18" x2="12" y2="18" />
				</svg>
			</div>
			<p class="empty-title">No timeline data available</p>
			<p class="empty-hint">
				Actions need dates to appear in the Gantt chart.
				Complete meetings and extract actions to see them here.
			</p>
		</div>
	{:else}
		<div
			class="gantt-chart"
			use:ganttAction={{ data, viewMode, onTaskClick }}
		></div>
	{/if}
</div>

<style>
	.gantt-container {
		width: 100%;
		min-height: 400px;
		background: var(--color-surface, white);
		border-radius: 0.5rem;
		overflow: hidden;
		border: 1px solid var(--color-border, #e5e7eb);
	}

	.gantt-chart {
		width: 100%;
		min-height: 400px;
	}

	/* Import frappe-gantt styles */
	:global(.gantt-container .gantt) {
		font-family: inherit;
	}

	:global(.gantt-container .gantt .bar-label) {
		font-size: 12px;
		font-weight: 500;
	}

	:global(.gantt-container .gantt .lower-text, .gantt-container .gantt .upper-text) {
		font-size: 11px;
	}

	:global(.gantt-container .gantt .grid-header) {
		fill: var(--color-surface-secondary, #f9fafb);
	}

	:global(.gantt-container .gantt .grid-row) {
		fill: var(--color-surface, white);
	}

	:global(.gantt-container .gantt .grid-row:nth-child(even)) {
		fill: var(--color-surface-secondary, #f9fafb);
	}

	:global(.gantt-container .gantt .row-line) {
		stroke: var(--color-border, #e5e7eb);
	}

	:global(.gantt-container .gantt .tick) {
		stroke: var(--color-border, #e5e7eb);
	}

	/* Popup wrapper */
	:global(.gantt-container .popup-wrapper) {
		background: var(--color-surface, white);
		border: 1px solid var(--color-border, #e5e7eb);
		border-radius: 8px;
		box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
	}

	/* Empty state */
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 400px;
		padding: 2rem;
		text-align: center;
	}

	.empty-icon {
		color: var(--color-muted, #9ca3af);
		margin-bottom: 1rem;
		opacity: 0.5;
	}

	.empty-title {
		font-size: 1rem;
		font-weight: 500;
		color: var(--color-foreground, #1f2937);
		margin: 0 0 0.5rem 0;
	}

	.empty-hint {
		font-size: 0.875rem;
		color: var(--color-muted, #6b7280);
		margin: 0;
		max-width: 300px;
	}
</style>
