/**
 * Time formatting utilities for relative and absolute time display
 */

/**
 * Format a timestamp as relative time (e.g., "2 minutes ago", "just now")
 */
export function formatRelativeTime(timestamp: string): string {
	const now = new Date();
	const eventTime = new Date(timestamp);
	const diffMs = now.getTime() - eventTime.getTime();
	const diffSec = Math.floor(diffMs / 1000);
	const diffMin = Math.floor(diffSec / 60);
	const diffHour = Math.floor(diffMin / 60);
	const diffDay = Math.floor(diffHour / 24);

	if (diffSec < 10) return 'just now';
	if (diffSec < 60) return `${diffSec} seconds ago`;
	if (diffMin < 60) return `${diffMin} minute${diffMin !== 1 ? 's' : ''} ago`;
	if (diffHour < 24) return `${diffHour} hour${diffHour !== 1 ? 's' : ''} ago`;
	return `${diffDay} day${diffDay !== 1 ? 's' : ''} ago`;
}

/**
 * Format a timestamp as compact relative time (e.g., "2m ago", "3d ago")
 * Used in dashboards and lists where space is limited
 */
export function formatCompactRelativeTime(timestamp: string): string {
	const now = new Date();
	const date = new Date(timestamp);
	const diffMs = now.getTime() - date.getTime();
	const diffMin = Math.floor(diffMs / 60000);
	const diffHour = Math.floor(diffMin / 60);
	const diffDay = Math.floor(diffHour / 24);
	const diffWeek = Math.floor(diffDay / 7);

	if (diffMin < 1) return 'just now';
	if (diffMin < 60) return `${diffMin}m ago`;
	if (diffHour < 24) return `${diffHour}h ago`;
	if (diffDay < 7) return `${diffDay}d ago`;
	return date.toLocaleDateString();
}

/**
 * Format a timestamp as absolute time (e.g., "Jan 21, 10:45:23 AM")
 */
export function formatAbsoluteTime(timestamp: string): string {
	const date = new Date(timestamp);
	return date.toLocaleString('en-US', {
		month: 'short',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit',
		second: '2-digit',
	});
}
