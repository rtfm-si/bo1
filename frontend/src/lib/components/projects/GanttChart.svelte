<script lang="ts">
	/**
	 * GanttChart - Interactive Gantt chart visualization for project timelines
	 *
	 * Uses frappe-gantt library for rendering.
	 * Features:
	 * - Status-based color coding
	 * - Dependency arrows
	 * - Drag-to-reschedule (optional)
	 * - Click to navigate to action details
	 */
	import type { GanttResponse, GanttActionData, GanttDependency, ActionStatus } from '$lib/api/types';
	import type { Action } from 'svelte/action';

	interface Props {
		data: GanttResponse;
		onTaskClick?: (actionId: string) => void;
		onDateChange?: (actionId: string, start: Date, end: Date) => Promise<void>;
		viewMode?: 'Day' | 'Week' | 'Month' | 'Quarter' | 'Year';
		readOnly?: boolean;
	}

	let {
		data,
		onTaskClick,
		onDateChange,
		viewMode = 'Week',
		readOnly = false
	}: Props = $props();

	// Status to color mapping
	const statusColors: Record<ActionStatus, string> = {
		todo: '#9CA3AF', // neutral-400
		in_progress: '#6366F1', // brand-500
		blocked: '#EF4444', // error-500
		in_review: '#A855F7', // purple-500
		done: '#22C55E', // success-500
		cancelled: '#6B7280', // neutral-500
		failed: '#EF4444', // error-500
		abandoned: '#6B7280', // neutral-500
		replanned: '#F59E0B' // amber-500
	};

	// Convert our action data to frappe-gantt task format
	function convertToGanttTasks(actions: GanttActionData[], dependencies: GanttDependency[]) {
		// Create a map of action ID to its dependency sources
		// GanttDependency: action_id (target) depends on depends_on_id (source)
		const depMap: Record<string, string[]> = {};
		for (const dep of dependencies) {
			if (!depMap[dep.action_id]) {
				depMap[dep.action_id] = [];
			}
			depMap[dep.action_id].push(dep.depends_on_id);
		}

		return actions
			.filter((action) => action.start && action.end)
			.map((action) => {
				const deps = depMap[action.id] || [];
				return {
					id: action.id,
					name: action.name,
					start: action.start,
					end: action.end,
					progress: action.status === 'done' ? 100 : action.status === 'in_progress' ? 50 : 0,
					dependencies: deps.join(', '),
					custom_class: `gantt-status-${action.status}`
				};
			});
	}

	function formatDate(date: Date): string {
		return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	}

	function injectStatusStyles() {
		const styleId = 'gantt-status-styles';
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
			.gantt-popup {
				padding: 12px;
				min-width: 200px;
			}
			.gantt-popup-title {
				font-weight: 600;
				margin: 0 0 8px 0;
				font-size: 14px;
				color: var(--color-foreground, #1f2937);
			}
			.gantt-popup-status {
				display: inline-block;
				padding: 2px 8px;
				border-radius: 4px;
				font-size: 12px;
				font-weight: 500;
				margin-bottom: 8px;
			}
			.gantt-popup-status.gantt-status-todo { background: ${statusColors.todo}20; color: ${statusColors.todo}; }
			.gantt-popup-status.gantt-status-in_progress { background: ${statusColors.in_progress}20; color: ${statusColors.in_progress}; }
			.gantt-popup-status.gantt-status-blocked { background: ${statusColors.blocked}20; color: ${statusColors.blocked}; }
			.gantt-popup-status.gantt-status-in_review { background: ${statusColors.in_review}20; color: ${statusColors.in_review}; }
			.gantt-popup-status.gantt-status-done { background: ${statusColors.done}20; color: ${statusColors.done}; }
			.gantt-popup-status.gantt-status-cancelled { background: ${statusColors.cancelled}20; color: ${statusColors.cancelled}; }

			.gantt-popup-blocked {
				font-size: 12px;
				color: ${statusColors.blocked};
				margin-bottom: 8px;
				padding: 4px 8px;
				background: ${statusColors.blocked}10;
				border-radius: 4px;
			}
			.gantt-popup-dates {
				font-size: 12px;
				color: var(--color-muted, #6b7280);
				display: flex;
				gap: 8px;
				align-items: center;
			}
			.gantt-popup-hint {
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
			}

			/* Read-only mode */
			.gantt-readonly .bar-wrapper {
				cursor: default !important;
			}
			.gantt-readonly .handle-group {
				display: none !important;
			}
		`;
		document.head.appendChild(style);
	}

	type ViewMode = 'Day' | 'Week' | 'Month' | 'Quarter' | 'Year';

	// Drag detection state - prevents click navigation during drag-to-reschedule
	let dragStartPos: { x: number; y: number } | null = null;
	let wasDragged = false;
	const DRAG_THRESHOLD = 5; // pixels of movement to consider it a drag

	// Svelte action for initializing the Gantt chart
	const ganttAction: Action<HTMLDivElement, {
		data: GanttResponse;
		viewMode: ViewMode;
		readOnly: boolean;
		onTaskClick?: (actionId: string) => void;
		onDateChange?: (actionId: string, start: Date, end: Date) => Promise<void>;
	}> = (node, params) => {
		let ganttInstance: any = null;
		let cleanupListeners: (() => void) | null = null;

		function setupDragDetection() {
			// Track mousedown on bar wrappers
			const handleMouseDown = (e: MouseEvent) => {
				dragStartPos = { x: e.clientX, y: e.clientY };
				wasDragged = false;
			};

			// Track mouse movement to detect drag
			const handleMouseMove = (e: MouseEvent) => {
				if (dragStartPos) {
					const dx = Math.abs(e.clientX - dragStartPos.x);
					const dy = Math.abs(e.clientY - dragStartPos.y);
					if (dx > DRAG_THRESHOLD || dy > DRAG_THRESHOLD) {
						wasDragged = true;
					}
				}
			};

			// Reset on mouseup
			const handleMouseUp = () => {
				// Keep wasDragged state for the click handler, reset after a tick
				setTimeout(() => {
					dragStartPos = null;
					wasDragged = false;
				}, 0);
			};

			node.addEventListener('mousedown', handleMouseDown);
			node.addEventListener('mousemove', handleMouseMove);
			node.addEventListener('mouseup', handleMouseUp);

			return () => {
				node.removeEventListener('mousedown', handleMouseDown);
				node.removeEventListener('mousemove', handleMouseMove);
				node.removeEventListener('mouseup', handleMouseUp);
			};
		}

		async function init() {
			if (!params.data.actions.length) return;

			// Dynamic import to avoid SSR issues
			const Gantt = (await import('frappe-gantt')).default;
			const tasks = convertToGanttTasks(params.data.actions, params.data.dependencies);

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
						cancelled: 'Cancelled',
						failed: 'Failed',
						abandoned: 'Abandoned',
						replanned: 'Replanned'
					}[action.status];

					return `
						<div class="gantt-popup">
							<h4 class="gantt-popup-title">${task.name}</h4>
							<div class="gantt-popup-status gantt-status-${action.status}">${statusLabel}</div>
							<div class="gantt-popup-dates">
								<span>${formatDate(task._start)}</span>
								<span>&rarr;</span>
								<span>${formatDate(task._end)}</span>
							</div>
							${params.onTaskClick ? '<div class="gantt-popup-hint">Click to view details</div>' : ''}
						</div>
					`;
				},
				on_click: (task: any) => {
					// Only navigate if this was a true click, not a drag
					if (params.onTaskClick && !wasDragged) {
						params.onTaskClick(task.id);
					}
				},
				on_date_change: async (task: any, start: Date, end: Date) => {
					if (!params.readOnly && params.onDateChange) {
						await params.onDateChange(task.id, start, end);
					}
				},
				on_progress_change: () => {
					// Progress changes are handled via action status updates
				},
				on_view_change: () => {
					// View mode change handled by parent component
				}
			});

			injectStatusStyles();

			// Setup drag detection after Gantt initializes
			if (cleanupListeners) cleanupListeners();
			cleanupListeners = setupDragDetection();
		}

		init();

		return {
			update(newParams) {
				// Reinitialize when data changes
				params = newParams;
				init();
			},
			destroy() {
				if (cleanupListeners) cleanupListeners();
				if (ganttInstance) {
					node.innerHTML = '';
					ganttInstance = null;
				}
			}
		};
	};

	// Determine if we have any tasks to display
	const hasTasks = $derived(
		data.actions.some((a) => a.start && a.end)
	);
</script>

<div class="gantt-container" class:gantt-readonly={readOnly}>
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
				Actions need estimated dates to appear in the Gantt chart.
				Set target dates or add durations to your actions.
			</p>
		</div>
	{:else}
		<div
			class="gantt-chart"
			use:ganttAction={{ data, viewMode, readOnly, onTaskClick, onDateChange }}
		></div>
	{/if}
</div>

<style>
	.gantt-container {
		width: 100%;
		min-height: 300px;
		background: var(--color-surface, white);
		border-radius: 0.5rem;
		overflow: hidden;
	}

	.gantt-chart {
		width: 100%;
		min-height: 300px;
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
		min-height: 300px;
		padding: 2rem;
		text-align: center;
	}

	.empty-icon {
		color: var(--color-muted, #6b7280);
		margin-bottom: 1rem;
	}

	.empty-title {
		font-size: 1rem;
		font-weight: 500;
		color: var(--color-foreground, #1f2937);
		margin: 0 0 0.5rem 0;
	}

	.empty-hint {
		font-size: 0.875rem;
		color: var(--color-muted, #4b5563);
		margin: 0;
		max-width: 300px;
	}
</style>
