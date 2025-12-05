/**
 * Centralized Color Mapping Utilities
 *
 * Consolidates all color-related utilities into a single file.
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
	'bg-slate-100 dark:bg-slate-900 text-slate-800 dark:text-slate-200 border-slate-300 dark:border-slate-700';

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
	pending: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
	accepted: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
	in_progress: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
	delayed: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
	rejected: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
	complete: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
	failed: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'
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
	if (ratio >= 0.9) return 'bg-green-500 dark:bg-green-600';
	if (ratio >= 0.7) return 'bg-yellow-500 dark:bg-yellow-600';
	if (ratio >= 0.4) return 'bg-orange-500 dark:bg-orange-600';
	return 'bg-red-500 dark:bg-red-600';
}

export function getProgressTextColor(ratio: number): string {
	if (ratio >= 0.9) return 'text-green-700 dark:text-green-300';
	if (ratio >= 0.7) return 'text-yellow-700 dark:text-yellow-300';
	if (ratio >= 0.4) return 'text-orange-700 dark:text-orange-300';
	return 'text-red-700 dark:text-red-300';
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
	if (confidence >= 0.8) return 'text-green-600 dark:text-green-400';
	if (confidence >= 0.6) return 'text-yellow-600 dark:text-yellow-400';
	return 'text-red-600 dark:text-red-400';
}

// ============================================================================
// QUALITY METRIC COLORS (novelty, conflict, drift)
// ============================================================================

export function getNoveltyColor(score: number | null): string {
	if (score === null || score === undefined) return 'text-neutral-400 dark:text-neutral-500';
	if (score >= 0.7) return 'text-green-600 dark:text-green-400';
	if (score >= 0.4) return 'text-yellow-600 dark:text-yellow-400';
	return 'text-red-600 dark:text-red-400';
}

export function getConflictColor(score: number | null): string {
	if (score === null || score === undefined) return 'text-neutral-400 dark:text-neutral-500';
	if (score >= 0.7) return 'text-orange-600 dark:text-orange-400';
	if (score >= 0.4) return 'text-yellow-600 dark:text-yellow-400';
	return 'text-green-600 dark:text-green-400';
}

export function getDriftColor(events: number): string {
	if (events === 0) return 'text-green-600 dark:text-green-400';
	if (events <= 2) return 'text-yellow-600 dark:text-yellow-400';
	return 'text-red-600 dark:text-red-400';
}

// ============================================================================
// STEP STATUS COLORS (SynthesisProgress)
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
// CONNECTION STATUS COLORS
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
// AVATAR STATUS COLORS
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
// USER/WAITLIST STATUS COLORS
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
// SECTION STYLING (SynthesisComplete, event cards)
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

export function getSectionClasses(type: SectionType): string {
	const style = getSectionStyle(type);
	return `${style.container} ${style.border}`;
}

// ============================================================================
// BADGE COLORS
// ============================================================================

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
// UTILITIES
// ============================================================================

export function getInitials(name: string, maxLength: number = 2): string {
	const parts = name.trim().split(/\s+/);
	if (parts.length >= 2) {
		return (parts[0][0] + parts[1][0]).toUpperCase();
	}
	return name.substring(0, maxLength).toUpperCase();
}
