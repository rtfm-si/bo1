/**
 * Centralized Color Mapping Utilities
 *
 * Consolidates duplicated color logic from:
 * - SynthesisProgress.svelte (step status colors)
 * - ConnectionStatus.svelte (connection status colors)
 * - Avatar.svelte (avatar status colors)
 * - admin/waitlist/+page.svelte (user status colors)
 * - SynthesisComplete.svelte (section styling)
 *
 * All functions return Tailwind class strings ready for use.
 */

// ============================================================================
// TYPES
// ============================================================================

export type StepStatus = 'complete' | 'active' | 'pending';
export type ConnectionStatus = 'connecting' | 'connected' | 'retrying' | 'error' | 'disconnected';
export type AvatarStatus = 'online' | 'offline' | 'typing' | 'busy';
export type UserStatus = 'pending' | 'invited' | 'converted' | 'rejected' | 'active' | 'inactive';
export type SectionType = 'executive' | 'recommendation' | 'details' | 'success' | 'warning' | 'error' | 'info' | 'neutral';

export interface StatusColorResult {
	iconColor: string;
	labelColor: string;
	bgColor: string;
	borderColor?: string;
	animate?: boolean;
}

export interface SectionStyleResult {
	container: string;
	border: string;
	icon: string;
	title: string;
}

// ============================================================================
// STEP STATUS COLORS (SynthesisProgress.svelte)
// ============================================================================

const STEP_STATUS_COLORS: Record<StepStatus, StatusColorResult> = {
	complete: {
		iconColor: 'text-green-600 dark:text-green-400',
		labelColor: 'text-green-700 dark:text-green-300',
		bgColor: 'bg-green-100 dark:bg-green-900/30',
		animate: false
	},
	active: {
		iconColor: 'text-blue-600 dark:text-blue-400',
		labelColor: 'text-blue-700 dark:text-blue-300',
		bgColor: 'bg-blue-100 dark:bg-blue-900/30',
		animate: true
	},
	pending: {
		iconColor: 'text-slate-400 dark:text-slate-500',
		labelColor: 'text-slate-500 dark:text-slate-400',
		bgColor: 'bg-slate-100 dark:bg-slate-800/50',
		animate: false
	}
};

export function getStepStatusColor(status: StepStatus): StatusColorResult {
	return STEP_STATUS_COLORS[status] ?? STEP_STATUS_COLORS.pending;
}

// ============================================================================
// CONNECTION STATUS COLORS (ConnectionStatus.svelte)
// ============================================================================

const CONNECTION_STATUS_COLORS: Record<ConnectionStatus, StatusColorResult> = {
	connecting: {
		iconColor: 'text-blue-500',
		labelColor: 'text-blue-600 dark:text-blue-400',
		bgColor: 'bg-blue-50 dark:bg-blue-900/20',
		animate: true
	},
	connected: {
		iconColor: 'text-green-500',
		labelColor: 'text-green-600 dark:text-green-400',
		bgColor: 'bg-green-50 dark:bg-green-900/20',
		animate: false
	},
	retrying: {
		iconColor: 'text-amber-500',
		labelColor: 'text-amber-600 dark:text-amber-400',
		bgColor: 'bg-amber-50 dark:bg-amber-900/20',
		animate: true
	},
	error: {
		iconColor: 'text-red-500',
		labelColor: 'text-red-600 dark:text-red-400',
		bgColor: 'bg-red-50 dark:bg-red-900/20',
		animate: false
	},
	disconnected: {
		iconColor: 'text-slate-400',
		labelColor: 'text-slate-500 dark:text-slate-400',
		bgColor: 'bg-slate-50 dark:bg-slate-800/50',
		animate: false
	}
};

export function getConnectionStatusColor(status: ConnectionStatus): StatusColorResult {
	return CONNECTION_STATUS_COLORS[status] ?? CONNECTION_STATUS_COLORS.disconnected;
}

// ============================================================================
// AVATAR STATUS COLORS (Avatar.svelte)
// ============================================================================

const AVATAR_STATUS_COLORS: Record<AvatarStatus, string> = {
	online: 'bg-green-500',
	offline: 'bg-slate-400',
	typing: 'bg-blue-500',
	busy: 'bg-amber-500'
};

export function getAvatarStatusColor(status: AvatarStatus): string {
	return AVATAR_STATUS_COLORS[status] ?? AVATAR_STATUS_COLORS.offline;
}

// ============================================================================
// USER/WAITLIST STATUS COLORS (admin/waitlist/+page.svelte)
// ============================================================================

const USER_STATUS_COLORS: Record<UserStatus, string> = {
	pending: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
	invited: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
	converted: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
	rejected: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
	active: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
	inactive: 'bg-slate-100 text-slate-800 dark:bg-slate-800/50 dark:text-slate-300'
};

export function getUserStatusColor(status: UserStatus): string {
	return USER_STATUS_COLORS[status] ?? USER_STATUS_COLORS.inactive;
}

// ============================================================================
// SECTION STYLING (SynthesisComplete.svelte, event cards)
// ============================================================================

const SECTION_STYLES: Record<SectionType, SectionStyleResult> = {
	executive: {
		container: 'bg-blue-50 dark:bg-blue-900/20',
		border: 'border-l-4 border-blue-600 dark:border-blue-400',
		icon: 'text-blue-600 dark:text-blue-400',
		title: 'text-blue-900 dark:text-blue-100'
	},
	recommendation: {
		container: 'bg-green-50 dark:bg-green-900/20',
		border: 'border-l-4 border-green-600 dark:border-green-400',
		icon: 'text-green-600 dark:text-green-400',
		title: 'text-green-900 dark:text-green-100'
	},
	details: {
		container: 'bg-slate-50 dark:bg-slate-800/50',
		border: 'border-l-4 border-slate-400 dark:border-slate-600',
		icon: 'text-slate-600 dark:text-slate-400',
		title: 'text-slate-900 dark:text-slate-100'
	},
	success: {
		container: 'bg-green-50 dark:bg-green-900/20',
		border: 'border-l-4 border-green-500',
		icon: 'text-green-600 dark:text-green-400',
		title: 'text-green-900 dark:text-green-100'
	},
	warning: {
		container: 'bg-amber-50 dark:bg-amber-900/20',
		border: 'border-l-4 border-amber-500',
		icon: 'text-amber-600 dark:text-amber-400',
		title: 'text-amber-900 dark:text-amber-100'
	},
	error: {
		container: 'bg-red-50 dark:bg-red-900/20',
		border: 'border-l-4 border-red-500',
		icon: 'text-red-600 dark:text-red-400',
		title: 'text-red-900 dark:text-red-100'
	},
	info: {
		container: 'bg-blue-50 dark:bg-blue-900/20',
		border: 'border-l-4 border-blue-500',
		icon: 'text-blue-600 dark:text-blue-400',
		title: 'text-blue-900 dark:text-blue-100'
	},
	neutral: {
		container: 'bg-slate-50 dark:bg-slate-800/50',
		border: 'border border-slate-200 dark:border-slate-700',
		icon: 'text-slate-500 dark:text-slate-400',
		title: 'text-slate-900 dark:text-slate-100'
	}
};

export function getSectionStyle(type: SectionType): SectionStyleResult {
	return SECTION_STYLES[type] ?? SECTION_STYLES.neutral;
}

/**
 * Get composite section classes (container + border combined).
 * Convenience function for common use case.
 */
export function getSectionClasses(type: SectionType): string {
	const style = getSectionStyle(type);
	return `${style.container} ${style.border}`;
}

// ============================================================================
// BADGE COLORS (reusable across components)
// ============================================================================

export type BadgeVariant = 'success' | 'warning' | 'error' | 'info' | 'neutral';

const BADGE_COLORS: Record<BadgeVariant, string> = {
	success: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
	warning: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
	error: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
	info: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
	neutral: 'bg-slate-100 text-slate-800 dark:bg-slate-800/50 dark:text-slate-300'
};

export function getBadgeColor(variant: BadgeVariant): string {
	return BADGE_COLORS[variant] ?? BADGE_COLORS.neutral;
}

// ============================================================================
// SEMANTIC COLOR HELPERS
// ============================================================================

/**
 * Map boolean/status to semantic badge variant.
 * Useful for converting API responses to display colors.
 */
export function statusToBadgeVariant(
	status: boolean | string | null | undefined
): BadgeVariant {
	if (status === true || status === 'success' || status === 'active' || status === 'complete') {
		return 'success';
	}
	if (status === false || status === 'error' || status === 'failed' || status === 'rejected') {
		return 'error';
	}
	if (status === 'warning' || status === 'pending' || status === 'retrying') {
		return 'warning';
	}
	if (status === 'info' || status === 'connecting' || status === 'processing') {
		return 'info';
	}
	return 'neutral';
}
