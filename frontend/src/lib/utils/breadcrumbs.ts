/**
 * Breadcrumb utility functions for generating navigation paths
 */

export interface BreadcrumbItem {
	label: string;
	href: string;
	isCurrent?: boolean;
}

/**
 * Route segment to display name mapping
 */
const SEGMENT_LABELS: Record<string, string> = {
	dashboard: 'Dashboard',
	actions: 'Actions',
	projects: 'Projects',
	meeting: 'Meetings',
	settings: 'Settings',
	account: 'Account',
	context: 'Context',
	overview: 'Overview',
	strategic: 'Strategic',
	metrics: 'Metrics',
	billing: 'Billing',
	intelligence: 'Intelligence',
	competitors: 'Competitors',
	admin: 'Admin',
	users: 'Users',
	whitelist: 'Whitelist',
	waitlist: 'Waitlist',
	new: 'New Meeting'
};

/**
 * Check if a segment looks like a UUID or ID
 */
function isIdSegment(segment: string): boolean {
	// UUID pattern or numeric ID
	const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
	const shortIdPattern = /^[0-9a-f]{8,}$/i;
	const numericPattern = /^\d+$/;

	return uuidPattern.test(segment) || shortIdPattern.test(segment) || numericPattern.test(segment);
}

/**
 * Format an ID for display (truncate UUID)
 */
function formatId(id: string): string {
	if (id.length > 12) {
		return `#${id.slice(0, 8)}...`;
	}
	return `#${id}`;
}

/**
 * Get the parent label for dynamic routes
 */
function getParentLabel(parentSegment: string): string {
	const labels: Record<string, string> = {
		meeting: 'Meeting',
		actions: 'Action',
		projects: 'Project'
	};
	return labels[parentSegment] || 'Detail';
}

/**
 * Generate breadcrumbs from a pathname
 */
export function getBreadcrumbs(pathname: string): BreadcrumbItem[] {
	// Remove leading slash and filter out empty segments
	const segments = pathname
		.split('/')
		.filter((s) => s && s !== '(app)');

	const breadcrumbs: BreadcrumbItem[] = [];
	let currentPath = '';

	for (let i = 0; i < segments.length; i++) {
		const segment = segments[i];
		const prevSegment = i > 0 ? segments[i - 1] : null;
		currentPath += '/' + segment;

		let label: string;

		if (isIdSegment(segment)) {
			// This is a dynamic ID segment
			label = `${getParentLabel(prevSegment || '')} ${formatId(segment)}`;
		} else if (SEGMENT_LABELS[segment]) {
			label = SEGMENT_LABELS[segment];
		} else {
			// Capitalize first letter of unknown segments
			label = segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, ' ');
		}

		breadcrumbs.push({
			label,
			href: currentPath,
			isCurrent: i === segments.length - 1
		});
	}

	return breadcrumbs;
}

/**
 * Get breadcrumbs with dynamic data (for when you have titles/names)
 */
export function getBreadcrumbsWithData(
	pathname: string,
	dynamicLabels?: Record<string, string>
): BreadcrumbItem[] {
	const breadcrumbs = getBreadcrumbs(pathname);

	if (dynamicLabels) {
		return breadcrumbs.map((crumb) => {
			// Check if we have a dynamic label for this path
			const dynamicLabel = dynamicLabels[crumb.href];
			if (dynamicLabel) {
				return { ...crumb, label: dynamicLabel };
			}
			return crumb;
		});
	}

	return breadcrumbs;
}
