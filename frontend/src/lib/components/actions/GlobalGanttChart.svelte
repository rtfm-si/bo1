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

	// Inject frappe-gantt base CSS
	function injectGanttBaseCSS() {
		const styleId = 'frappe-gantt-base-css';
		if (document.getElementById(styleId)) return;

		const style = document.createElement('style');
		style.id = styleId;
		style.textContent = `
			:root{--g-arrow-color: #1f2937;--g-bar-color: #fff;--g-bar-border: #fff;--g-tick-color-thick: #ededed;--g-tick-color: #f3f3f3;--g-actions-background: #f3f3f3;--g-border-color: #ebeff2;--g-text-muted: #7c7c7c;--g-text-light: #fff;--g-text-dark: #171717;--g-progress-color: #dbdbdb;--g-handle-color: #37352f;--g-weekend-label-color: #dcdce4;--g-expected-progress: #c4c4e9;--g-header-background: #fff;--g-row-color: #fdfdfd;--g-row-border-color: #c7c7c7;--g-today-highlight: #37352f;--g-popup-actions: #ebeff2;--g-weekend-highlight-color: #f7f7f7}
			.gantt-container{line-height:14.5px;position:relative;overflow:auto;font-size:12px;height:var(--gv-grid-height);width:100%;border-radius:8px}
			.gantt-container .popup-wrapper{position:absolute;top:0;left:0;background:#fff;box-shadow:0 10px 24px -3px #0003;padding:10px;border-radius:5px;width:max-content;z-index:1000}
			.gantt-container .popup-wrapper .title{margin-bottom:2px;color:var(--g-text-dark);font-size:.85rem;font-weight:650;line-height:15px}
			.gantt-container .popup-wrapper .subtitle{color:var(--g-text-dark);font-size:.8rem;margin-bottom:5px}
			.gantt-container .popup-wrapper .details{color:var(--g-text-muted);font-size:.7rem}
			.gantt-container .popup-wrapper .actions{margin-top:10px;margin-left:3px}
			.gantt-container .popup-wrapper .action-btn{border:none;padding:5px 8px;background-color:var(--g-popup-actions);border-right:1px solid var(--g-text-light)}
			.gantt-container .popup-wrapper .action-btn:hover{background-color:brightness(97%)}
			.gantt-container .popup-wrapper .action-btn:first-child{border-top-left-radius:4px;border-bottom-left-radius:4px}
			.gantt-container .popup-wrapper .action-btn:last-child{border-right:none;border-top-right-radius:4px;border-bottom-right-radius:4px}
			.gantt-container .grid-header{height:calc(var(--gv-lower-header-height) + var(--gv-upper-header-height) + 10px);background-color:var(--g-header-background);position:sticky;top:0;left:0;border-bottom:1px solid var(--g-row-border-color);z-index:1000}
			.gantt-container .lower-text,.gantt-container .upper-text{text-anchor:middle}
			.gantt-container .upper-header{height:var(--gv-upper-header-height)}
			.gantt-container .lower-header{height:var(--gv-lower-header-height)}
			.gantt-container .lower-text{font-size:12px;position:absolute;width:calc(var(--gv-column-width) * .8);height:calc(var(--gv-lower-header-height) * .8);margin:0 calc(var(--gv-column-width) * .1);align-content:center;text-align:center;color:var(--g-text-muted)}
			.gantt-container .upper-text{position:absolute;width:fit-content;font-weight:500;font-size:14px;color:var(--g-text-dark);height:calc(var(--gv-lower-header-height) * .66)}
			.gantt-container .current-upper{position:sticky;left:0!important;padding-left:17px;background:#fff}
			.gantt-container .side-header{position:sticky;top:0;right:0;float:right;z-index:1000;line-height:20px;font-weight:400;width:max-content;margin-left:auto;padding-right:10px;padding-top:10px;background:var(--g-header-background);display:flex}
			.gantt-container .side-header *{transition-property:background-color;transition-timing-function:cubic-bezier(.4,0,.2,1);transition-duration:.15s;background-color:var(--g-actions-background);border-radius:.5rem;border:none;padding:5px 8px;color:var(--g-text-dark);font-size:14px;letter-spacing:.02em;font-weight:420;box-sizing:content-box;margin-right:5px}
			.gantt-container .side-header *:last-child{margin-right:0}
			.gantt-container .side-header *:hover{filter:brightness(97.5%)}
			.gantt-container .side-header select{width:60px;padding-top:2px;padding-bottom:2px}
			.gantt-container .side-header select:focus{outline:none}
			.gantt-container .date-range-highlight{background-color:var(--g-progress-color);border-radius:12px;height:calc(var(--gv-lower-header-height) - 6px);top:calc(var(--gv-upper-header-height) + 5px);position:absolute}
			.gantt-container .current-highlight{position:absolute;background:var(--g-today-highlight);width:1px;z-index:999}
			.gantt-container .current-ball-highlight{position:absolute;background:var(--g-today-highlight);z-index:1001;border-radius:50%}
			.gantt-container .current-date-highlight{background:var(--g-today-highlight);color:var(--g-text-light);border-radius:5px}
			.gantt-container .holiday-label{position:absolute;top:0;left:0;opacity:0;z-index:1000;background:--g-weekend-label-color;border-radius:5px;padding:2px 5px}
			.gantt-container .holiday-label.show{opacity:100}
			.gantt-container .extras{position:sticky;left:0}
			.gantt-container .extras .adjust{position:absolute;left:8px;top:calc(var(--gv-grid-height) - 60px);background-color:#000000b3;color:#fff;border:none;padding:8px;border-radius:3px}
			.gantt-container .hide{display:none}
			.gantt{user-select:none;-webkit-user-select:none;position:absolute}
			.gantt .grid-background{fill:none}
			.gantt .grid-row{fill:var(--g-row-color)}
			.gantt .row-line{stroke:var(--g-border-color)}
			.gantt .tick{stroke:var(--g-tick-color);stroke-width:.4}
			.gantt .tick.thick{stroke:var(--g-tick-color-thick);stroke-width:.7}
			.gantt .arrow{fill:none;stroke:var(--g-arrow-color);stroke-width:1.5}
			.gantt .bar-wrapper .bar{fill:var(--g-bar-color);stroke:var(--g-bar-border);stroke-width:0;transition:stroke-width .3s ease}
			.gantt .bar-progress{fill:var(--g-progress-color);border-radius:4px}
			.gantt .bar-expected-progress{fill:var(--g-expected-progress)}
			.gantt .bar-invalid{fill:transparent;stroke:var(--g-bar-border);stroke-width:1;stroke-dasharray:5}
			:is(.gantt .bar-invalid)~.bar-label{fill:var(--g-text-light)}
			.gantt .bar-label{fill:var(--g-text-dark);dominant-baseline:central;font-family:Helvetica;font-size:13px;font-weight:400}
			.gantt .bar-label.big{fill:var(--g-text-dark);text-anchor:start}
			.gantt .handle{fill:var(--g-handle-color);opacity:0;transition:opacity .3s ease}
			.gantt .handle.active,.gantt .handle.visible{cursor:ew-resize;opacity:1}
			.gantt .handle.progress{fill:var(--g-text-muted)}
			.gantt .bar-wrapper{cursor:pointer}
			.gantt .bar-wrapper .bar{outline:1px solid var(--g-row-border-color);border-radius:3px}
			.gantt .bar-wrapper:hover .bar{transition:transform .3s ease}
			.gantt .bar-wrapper:hover .date-range-highlight{display:block}
		`;
		document.head.appendChild(style);
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

			// Inject base CSS first
			injectGanttBaseCSS();
			injectStatusStyles();

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
