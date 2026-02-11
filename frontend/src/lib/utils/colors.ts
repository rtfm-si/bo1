/**
 * Centralized Color Mapping Utilities
 *
 * Consolidates all color-related utilities into a single file.
 * All functions return Tailwind class strings ready for use.
 */

// ============================================================================
// TYPES
// ============================================================================

import type { ConnectionStatus } from '$lib/config/constants';

export type StepStatus = 'complete' | 'active' | 'pending';
export type { ConnectionStatus };
export type AvatarStatus = 'online' | 'offline' | 'typing' | 'busy';
export type UserStatus = 'pending' | 'invited' | 'converted' | 'rejected' | 'active' | 'inactive';
export type SectionType = 'executive' | 'recommendation' | 'details' | 'success' | 'warning' | 'error' | 'info' | 'neutral';
export type BadgeVariant = 'success' | 'warning' | 'error' | 'info' | 'neutral';

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
// PERSONA COLORS (Expert avatars by code)
// ============================================================================

const PERSONA_COLORS: Record<string, string> = {
	fi: 'bg-emerald-100 dark:bg-emerald-900 text-emerald-800 dark:text-emerald-200 border-emerald-300 dark:border-emerald-700',
	co: 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 border-blue-300 dark:border-blue-700',
	cu: 'bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 border-purple-300 dark:border-purple-700',
	bo: 'bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200 border-orange-300 dark:border-orange-700',
	sk: 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 border-red-300 dark:border-red-700',
	sa: 'bg-indigo-100 dark:bg-indigo-900 text-indigo-800 dark:text-indigo-200 border-indigo-300 dark:border-indigo-700',
	le: 'bg-pink-100 dark:bg-pink-900 text-pink-800 dark:text-pink-200 border-pink-300 dark:border-pink-700',
	te: 'bg-cyan-100 dark:bg-cyan-900 text-cyan-800 dark:text-cyan-200 border-cyan-300 dark:border-cyan-700'
};

const DEFAULT_PERSONA_COLOR =
	'bg-neutral-100 dark:bg-neutral-900 text-neutral-800 dark:text-neutral-200 border-neutral-300 dark:border-neutral-700';

export function getPersonaColor(code: string): string {
	return PERSONA_COLORS[code] ?? DEFAULT_PERSONA_COLOR;
}

// ============================================================================
// SESSION STATUS COLORS (Meeting status)
// ============================================================================

const SESSION_STATUS_COLORS: Record<string, string> = {
	active: 'bg-info-100 text-info-800 dark:bg-info-900/20 dark:text-info-300',
	paused: 'bg-warning-100 text-warning-800 dark:bg-warning-900/20 dark:text-warning-300',
	completed: 'bg-success-100 text-success-800 dark:bg-success-900/20 dark:text-success-300',
	failed: 'bg-error-100 text-error-800 dark:bg-error-900/20 dark:text-error-300',
	killed: 'bg-neutral-100 text-neutral-800 dark:bg-neutral-900/20 dark:text-neutral-300'
};

export function getSessionStatusColor(status: string): string {
	return SESSION_STATUS_COLORS[status] ?? 'bg-neutral-100 text-neutral-800';
}

// ============================================================================
// TASK STATUS COLORS
// ============================================================================

const TASK_STATUS_COLORS: Record<string, string> = {
	pending: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300',
	accepted: 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300',
	in_progress: 'bg-info-100 text-info-700 dark:bg-info-900/30 dark:text-info-300',
	delayed: 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300',
	rejected: 'bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-300',
	complete: 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300',
	failed: 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300'
};

export function getTaskStatusColor(status: string): string {
	return TASK_STATUS_COLORS[status] ?? TASK_STATUS_COLORS.pending;
}

// ============================================================================
// TIER COLORS (Subscription tiers)
// ============================================================================

const TIER_COLORS: Record<string, string> = {
	free: 'bg-neutral-100 text-neutral-800 dark:bg-neutral-900/20 dark:text-neutral-300',
	pro: 'bg-brand-100 text-brand-800 dark:bg-brand-900/20 dark:text-brand-300',
	enterprise: 'bg-accent-100 text-accent-800 dark:bg-accent-900/20 dark:text-accent-300'
};

export function getTierColor(tier: string): string {
	return TIER_COLORS[tier] ?? TIER_COLORS.free;
}

// ============================================================================
// PROGRESS/CONVERGENCE COLORS
// ============================================================================

export function getProgressColor(ratio: number): string {
	if (ratio >= 0.9) return 'bg-success-500 dark:bg-success-600';
	if (ratio >= 0.7) return 'bg-warning-500 dark:bg-warning-600';
	if (ratio >= 0.4) return 'bg-warning-500 dark:bg-warning-600';
	return 'bg-error-500 dark:bg-error-600';
}

export function getProgressTextColor(ratio: number): string {
	if (ratio >= 0.9) return 'text-success-700 dark:text-success-300';
	if (ratio >= 0.7) return 'text-warning-700 dark:text-warning-300';
	if (ratio >= 0.4) return 'text-warning-700 dark:text-warning-300';
	return 'text-error-700 dark:text-error-300';
}

export function getProgressStatusMessage(ratio: number): string {
	if (ratio >= 1.0) return 'Strong consensus achieved';
	if (ratio >= 0.9) return 'Nearly converged';
	if (ratio >= 0.7) return 'Good progress';
	if (ratio >= 0.4) return 'Building consensus';
	return 'Early discussion';
}

// ============================================================================
// CONFIDENCE COLORS
// ============================================================================

export function getConfidenceColor(confidence: number): string {
	if (confidence >= 0.8) return 'text-success-600 dark:text-success-400';
	if (confidence >= 0.6) return 'text-warning-600 dark:text-warning-400';
	return 'text-error-600 dark:text-error-400';
}

// ============================================================================
// QUALITY METRIC COLORS (novelty, conflict, drift)
// ============================================================================

export function getNoveltyColor(score: number | null): string {
	if (score === null || score === undefined) return 'text-neutral-400 dark:text-neutral-500';
	if (score >= 0.7) return 'text-success-600 dark:text-success-400';
	if (score >= 0.4) return 'text-warning-600 dark:text-warning-400';
	return 'text-error-600 dark:text-error-400';
}

export function getConflictColor(score: number | null): string {
	if (score === null || score === undefined) return 'text-neutral-400 dark:text-neutral-500';
	if (score >= 0.7) return 'text-warning-600 dark:text-warning-400';
	if (score >= 0.4) return 'text-warning-600 dark:text-warning-400';
	return 'text-success-600 dark:text-success-400';
}

export function getDriftColor(events: number): string {
	if (events === 0) return 'text-success-600 dark:text-success-400';
	if (events <= 2) return 'text-warning-600 dark:text-warning-400';
	return 'text-error-600 dark:text-error-400';
}

// ============================================================================
// STEP STATUS COLORS (SynthesisProgress)
// ============================================================================

const STEP_STATUS_COLORS: Record<StepStatus, StatusColorResult> = {
	complete: {
		iconColor: 'text-success-600 dark:text-success-400',
		labelColor: 'text-success-700 dark:text-success-300',
		bgColor: 'bg-success-100 dark:bg-success-900/30',
		animate: false
	},
	active: {
		iconColor: 'text-info-600 dark:text-info-400',
		labelColor: 'text-info-700 dark:text-info-300',
		bgColor: 'bg-info-100 dark:bg-info-900/30',
		animate: true
	},
	pending: {
		iconColor: 'text-neutral-400 dark:text-neutral-500',
		labelColor: 'text-neutral-500 dark:text-neutral-400',
		bgColor: 'bg-neutral-100 dark:bg-neutral-800/50',
		animate: false
	}
};

export function getStepStatusColor(status: StepStatus): StatusColorResult {
	return STEP_STATUS_COLORS[status] ?? STEP_STATUS_COLORS.pending;
}

// ============================================================================
// CONNECTION STATUS COLORS
// ============================================================================

const CONNECTION_STATUS_COLORS: Record<ConnectionStatus, StatusColorResult> = {
	connecting: {
		iconColor: 'text-info-500',
		labelColor: 'text-info-600 dark:text-info-400',
		bgColor: 'bg-info-50 dark:bg-info-900/20',
		animate: true
	},
	connected: {
		iconColor: 'text-success-500',
		labelColor: 'text-success-600 dark:text-success-400',
		bgColor: 'bg-success-50 dark:bg-success-900/20',
		animate: false
	},
	retrying: {
		iconColor: 'text-warning-500',
		labelColor: 'text-warning-600 dark:text-warning-400',
		bgColor: 'bg-warning-50 dark:bg-warning-900/20',
		animate: true
	},
	error: {
		iconColor: 'text-error-500',
		labelColor: 'text-error-600 dark:text-error-400',
		bgColor: 'bg-error-50 dark:bg-error-900/20',
		animate: false
	},
	disconnected: {
		iconColor: 'text-neutral-400',
		labelColor: 'text-neutral-500 dark:text-neutral-400',
		bgColor: 'bg-neutral-50 dark:bg-neutral-800/50',
		animate: false
	}
};

export function getConnectionStatusColor(status: ConnectionStatus): StatusColorResult {
	return CONNECTION_STATUS_COLORS[status] ?? CONNECTION_STATUS_COLORS.disconnected;
}

// ============================================================================
// AVATAR STATUS COLORS
// ============================================================================

const AVATAR_STATUS_COLORS: Record<AvatarStatus, string> = {
	online: 'bg-success-500',
	offline: 'bg-neutral-400',
	typing: 'bg-info-500',
	busy: 'bg-warning-500'
};

export function getAvatarStatusColor(status: AvatarStatus): string {
	return AVATAR_STATUS_COLORS[status] ?? AVATAR_STATUS_COLORS.offline;
}

// ============================================================================
// USER/WAITLIST STATUS COLORS
// ============================================================================

const USER_STATUS_COLORS: Record<UserStatus, string> = {
	pending: 'bg-warning-100 text-warning-800 dark:bg-warning-900/30 dark:text-warning-300',
	invited: 'bg-success-100 text-success-800 dark:bg-success-900/30 dark:text-success-300',
	converted: 'bg-info-100 text-info-800 dark:bg-info-900/30 dark:text-info-300',
	rejected: 'bg-error-100 text-error-800 dark:bg-error-900/30 dark:text-error-300',
	active: 'bg-success-100 text-success-800 dark:bg-success-900/30 dark:text-success-300',
	inactive: 'bg-neutral-100 text-neutral-800 dark:bg-neutral-800/50 dark:text-neutral-300'
};

export function getUserStatusColor(status: UserStatus): string {
	return USER_STATUS_COLORS[status] ?? USER_STATUS_COLORS.inactive;
}

// ============================================================================
// SECTION STYLING (SynthesisComplete, event cards)
// ============================================================================

const SECTION_STYLES: Record<SectionType, SectionStyleResult> = {
	executive: {
		container: 'bg-info-50 dark:bg-info-900/20',
		border: 'border-l-4 border-info-600 dark:border-info-400',
		icon: 'text-info-600 dark:text-info-400',
		title: 'text-info-900 dark:text-info-100'
	},
	recommendation: {
		container: 'bg-success-50 dark:bg-success-900/20',
		border: 'border-l-4 border-success-600 dark:border-success-400',
		icon: 'text-success-600 dark:text-success-400',
		title: 'text-success-900 dark:text-success-100'
	},
	details: {
		container: 'bg-neutral-50 dark:bg-neutral-800/50',
		border: 'border-l-4 border-neutral-400 dark:border-neutral-600',
		icon: 'text-neutral-600 dark:text-neutral-400',
		title: 'text-neutral-900 dark:text-neutral-100'
	},
	success: {
		container: 'bg-success-50 dark:bg-success-900/20',
		border: 'border-l-4 border-success-500',
		icon: 'text-success-600 dark:text-success-400',
		title: 'text-success-900 dark:text-success-100'
	},
	warning: {
		container: 'bg-warning-50 dark:bg-warning-900/20',
		border: 'border-l-4 border-warning-500',
		icon: 'text-warning-600 dark:text-warning-400',
		title: 'text-warning-900 dark:text-warning-100'
	},
	error: {
		container: 'bg-error-50 dark:bg-error-900/20',
		border: 'border-l-4 border-error-500',
		icon: 'text-error-600 dark:text-error-400',
		title: 'text-error-900 dark:text-error-100'
	},
	info: {
		container: 'bg-info-50 dark:bg-info-900/20',
		border: 'border-l-4 border-info-500',
		icon: 'text-info-600 dark:text-info-400',
		title: 'text-info-900 dark:text-info-100'
	},
	neutral: {
		container: 'bg-neutral-50 dark:bg-neutral-800/50',
		border: 'border border-neutral-200 dark:border-neutral-700',
		icon: 'text-neutral-500 dark:text-neutral-400',
		title: 'text-neutral-900 dark:text-neutral-100'
	}
};

export function getSectionStyle(type: SectionType): SectionStyleResult {
	return SECTION_STYLES[type] ?? SECTION_STYLES.neutral;
}

export function getSectionClasses(type: SectionType): string {
	const style = getSectionStyle(type);
	return `${style.container} ${style.border}`;
}

// ============================================================================
// BADGE COLORS
// ============================================================================

const BADGE_COLORS: Record<BadgeVariant, string> = {
	success: 'bg-success-100 text-success-800 dark:bg-success-900/30 dark:text-success-300',
	warning: 'bg-warning-100 text-warning-800 dark:bg-warning-900/30 dark:text-warning-300',
	error: 'bg-error-100 text-error-800 dark:bg-error-900/30 dark:text-error-300',
	info: 'bg-info-100 text-info-800 dark:bg-info-900/30 dark:text-info-300',
	neutral: 'bg-neutral-100 text-neutral-800 dark:bg-neutral-800/50 dark:text-neutral-300'
};

export function getBadgeColor(variant: BadgeVariant): string {
	return BADGE_COLORS[variant] ?? BADGE_COLORS.neutral;
}

// ============================================================================
// SEMANTIC HELPERS
// ============================================================================

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

// ============================================================================
// CATEGORY COLORS (Insight/metric categories)
// ============================================================================

const CATEGORY_COLORS: Record<string, string> = {
	revenue: 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300',
	growth: 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300',
	customers: 'bg-info-100 text-info-700 dark:bg-info-900/30 dark:text-info-300',
	team: 'bg-accent-100 text-accent-700 dark:bg-accent-900/30 dark:text-accent-300',
	product: 'bg-info-100 text-info-700 dark:bg-info-900/30 dark:text-info-300',
	operations: 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300',
	market: 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300',
	competition: 'bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-300',
	funding: 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300',
	costs: 'bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-300',
};

export function getCategoryColor(category: string): string {
	return CATEGORY_COLORS[category] ?? 'bg-neutral-100 text-neutral-700 dark:bg-neutral-700/50 dark:text-neutral-300';
}

// ============================================================================
// UTILITIES
// ============================================================================

export function getInitials(name: string, maxLength: number = 2): string {
	const parts = name.trim().split(/\s+/);
	if (parts.length >= 2) {
		return (parts[0][0] + parts[1][0]).toUpperCase();
	}
	return name.substring(0, maxLength).toUpperCase();
}
