<script lang="ts">
	/**
	 * ActivityTimeline - Shows action activity feed (updates, status changes, etc.)
	 */
	import type { ActionUpdateResponse, ActionUpdateType } from '$lib/api/types';

	interface Props {
		updates: ActionUpdateResponse[];
		loading?: boolean;
	}

	let { updates, loading = false }: Props = $props();

	// Format relative time
	function formatRelativeTime(dateString: string): string {
		const date = new Date(dateString);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / 60000);
		const diffHours = Math.floor(diffMs / 3600000);
		const diffDays = Math.floor(diffMs / 86400000);

		if (diffMins < 1) return 'just now';
		if (diffMins < 60) return `${diffMins}m ago`;
		if (diffHours < 24) return `${diffHours}h ago`;
		if (diffDays < 7) return `${diffDays}d ago`;

		return date.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
		});
	}

	// Get icon and color for update type
	function getUpdateStyle(type: ActionUpdateType): { icon: string; color: string; label: string } {
		switch (type) {
			case 'progress':
				return { icon: 'chart-line', color: 'var(--color-brand)', label: 'Progress' };
			case 'blocker':
				return { icon: 'exclamation-triangle', color: 'var(--color-error)', label: 'Blocker' };
			case 'note':
				return { icon: 'comment', color: 'var(--color-muted)', label: 'Note' };
			case 'status_change':
				return { icon: 'arrow-right', color: 'var(--color-warning)', label: 'Status' };
			case 'date_change':
				return { icon: 'calendar', color: 'var(--color-info)', label: 'Date' };
			case 'completion':
				return { icon: 'check-circle', color: 'var(--color-success)', label: 'Completed' };
			default:
				return { icon: 'info-circle', color: 'var(--color-muted)', label: 'Update' };
		}
	}

	// Format status for display
	function formatStatus(status: string | null): string {
		if (!status) return '';
		return status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
	}

	// Get update description
	function getUpdateDescription(update: ActionUpdateResponse): string {
		switch (update.update_type) {
			case 'status_change':
				return `Changed status from ${formatStatus(update.old_status)} to ${formatStatus(update.new_status)}`;
			case 'date_change':
				return `Changed ${update.date_field?.replace(/_/g, ' ')} from ${update.old_date || 'unset'} to ${update.new_date || 'unset'}`;
			case 'progress':
				return update.content || `Progress: ${update.progress_percent}%`;
			case 'completion':
				return update.content || 'Action completed';
			default:
				return update.content || '';
		}
	}
</script>

<div class="activity-timeline">
	{#if loading}
		<div class="loading">Loading activity...</div>
	{:else if updates.length === 0}
		<div class="empty">
			<span class="empty-icon">
				<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<circle cx="12" cy="12" r="10"/>
					<polyline points="12 6 12 12 16 14"/>
				</svg>
			</span>
			<p>No activity yet</p>
			<p class="empty-hint">Updates, notes, and status changes will appear here</p>
		</div>
	{:else}
		<ul class="timeline-list">
			{#each updates as update (update.id)}
				{@const style = getUpdateStyle(update.update_type)}
				<li class="timeline-item" style="--update-color: {style.color}">
					<div class="timeline-marker">
						<span class="marker-dot"></span>
					</div>
					<div class="timeline-content">
						<div class="timeline-header">
							<span class="update-type">{style.label}</span>
							<span class="update-time">{formatRelativeTime(update.created_at)}</span>
						</div>
						<p class="update-description">{getUpdateDescription(update)}</p>
						{#if update.update_type === 'progress' && update.progress_percent !== null}
							<div class="progress-bar">
								<div class="progress-fill" style="width: {update.progress_percent}%"></div>
								<span class="progress-label">{update.progress_percent}%</span>
							</div>
						{/if}
					</div>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.activity-timeline {
		width: 100%;
	}

	.loading {
		text-align: center;
		padding: 1.5rem;
		color: var(--color-muted);
		font-size: 0.875rem;
	}

	.empty {
		text-align: center;
		padding: 2rem 1rem;
		color: var(--color-muted);
	}

	.empty-icon {
		display: inline-block;
		opacity: 0.4;
		margin-bottom: 0.5rem;
	}

	.empty p {
		margin: 0.25rem 0;
		font-size: 0.875rem;
	}

	.empty-hint {
		font-size: 0.75rem;
		opacity: 0.7;
	}

	.timeline-list {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.timeline-item {
		display: flex;
		gap: 0.75rem;
		padding: 0.75rem 0;
		border-bottom: 1px solid var(--color-border);
	}

	.timeline-item:last-child {
		border-bottom: none;
	}

	.timeline-marker {
		display: flex;
		flex-direction: column;
		align-items: center;
		flex-shrink: 0;
		width: 1.5rem;
	}

	.marker-dot {
		width: 0.625rem;
		height: 0.625rem;
		border-radius: 50%;
		background-color: var(--update-color, var(--color-muted));
		margin-top: 0.25rem;
	}

	.timeline-content {
		flex: 1;
		min-width: 0;
	}

	.timeline-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.25rem;
	}

	.update-type {
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.025em;
		color: var(--update-color, var(--color-muted));
	}

	.update-time {
		font-size: 0.75rem;
		color: var(--color-muted);
	}

	.update-description {
		margin: 0;
		font-size: 0.875rem;
		color: var(--color-foreground);
		line-height: 1.4;
		word-break: break-word;
	}

	.progress-bar {
		position: relative;
		height: 0.5rem;
		background-color: var(--color-surface-secondary);
		border-radius: 0.25rem;
		margin-top: 0.5rem;
		overflow: hidden;
	}

	.progress-fill {
		height: 100%;
		background-color: var(--color-brand);
		border-radius: 0.25rem;
		transition: width 0.3s ease;
	}

	.progress-label {
		position: absolute;
		right: 0;
		top: -1.25rem;
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--color-brand);
	}
</style>
