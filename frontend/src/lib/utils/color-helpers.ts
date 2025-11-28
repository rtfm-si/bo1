/**
 * Centralized color mapping utilities
 * Eliminates duplicate color functions across components
 */

// Persona color palette for expert avatars
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

// Meeting/session status colors
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

// Task status colors
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

// Subscription tier colors
const TIER_COLORS: Record<string, string> = {
	free: 'bg-neutral-100 text-neutral-800 dark:bg-neutral-900/20 dark:text-neutral-300',
	pro: 'bg-brand-100 text-brand-800 dark:bg-brand-900/20 dark:text-brand-300',
	enterprise: 'bg-accent-100 text-accent-800 dark:bg-accent-900/20 dark:text-accent-300'
};

export function getTierColor(tier: string): string {
	return TIER_COLORS[tier] ?? TIER_COLORS.free;
}

// Progress/convergence colors based on ratio
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

// Confidence colors
export function getConfidenceColor(confidence: number): string {
	if (confidence >= 0.8) return 'text-green-600 dark:text-green-400';
	if (confidence >= 0.6) return 'text-yellow-600 dark:text-yellow-400';
	return 'text-red-600 dark:text-red-400';
}

// Quality metric colors (novelty, conflict, drift)
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

// Initials extraction
export function getInitials(name: string, maxLength: number = 2): string {
	const parts = name.trim().split(/\s+/);
	if (parts.length >= 2) {
		return (parts[0][0] + parts[1][0]).toUpperCase();
	}
	return name.substring(0, maxLength).toUpperCase();
}
