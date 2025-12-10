/**
 * Due date utilities for action items
 */

export type DueDateStatus = 'overdue' | 'due-today' | 'due-soon' | 'normal' | null;

const HOURS_48_MS = 48 * 60 * 60 * 1000;

/**
 * Get the effective due date from action fields
 * Prioritizes: target_end_date > estimated_end_date > suggested_completion_date
 */
export function getEffectiveDueDate(action: {
	target_end_date?: string | null;
	estimated_end_date?: string | null;
	suggested_completion_date?: string | null;
}): string | null {
	return action.target_end_date || action.estimated_end_date || action.suggested_completion_date || null;
}

/**
 * Check if a date is today (same calendar day)
 */
export function isDueToday(dueDate: string | null | undefined): boolean {
	if (!dueDate) return false;
	try {
		const due = new Date(dueDate);
		const now = new Date();
		return due.getFullYear() === now.getFullYear() &&
			due.getMonth() === now.getMonth() &&
			due.getDate() === now.getDate();
	} catch {
		return false;
	}
}

/**
 * Get the due date status for an action
 * @param dueDate - ISO date string or null
 * @returns 'overdue' | 'due-today' | 'due-soon' | 'normal' | null
 */
export function getDueDateStatus(dueDate: string | null | undefined): DueDateStatus {
	if (!dueDate) return null;

	try {
		const due = new Date(dueDate);
		const now = new Date();

		// Check if overdue (past due date, but not today)
		if (due < now && !isDueToday(dueDate)) {
			return 'overdue';
		}

		// Check if due today
		if (isDueToday(dueDate)) {
			return 'due-today';
		}

		// Check if due soon (within 48 hours)
		const msUntilDue = due.getTime() - now.getTime();
		if (msUntilDue <= HOURS_48_MS) {
			return 'due-soon';
		}

		return 'normal';
	} catch {
		return null;
	}
}

/**
 * Get Tailwind classes for due date badge styling
 */
export function getDueDateBadgeClasses(status: DueDateStatus): string {
	switch (status) {
		case 'overdue':
			return 'bg-error-100 dark:bg-error-900/30 text-error-700 dark:text-error-300 border-error-200 dark:border-error-800';
		case 'due-today':
			return 'bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-300 border-warning-200 dark:border-warning-800';
		case 'due-soon':
			return 'bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-300 border-warning-200 dark:border-warning-800';
		default:
			return '';
	}
}

/**
 * Get the label for a due date status
 */
export function getDueDateLabel(status: DueDateStatus): string {
	switch (status) {
		case 'overdue':
			return 'Overdue';
		case 'due-today':
			return 'Due Today';
		case 'due-soon':
			return 'Due Soon';
		default:
			return '';
	}
}

/**
 * Get icon color classes for due date status
 */
export function getDueDateIconClasses(status: DueDateStatus): string {
	switch (status) {
		case 'overdue':
			return 'text-error-500 dark:text-error-400';
		case 'due-today':
			return 'text-warning-500 dark:text-warning-400';
		case 'due-soon':
			return 'text-warning-500 dark:text-warning-400';
		default:
			return 'text-neutral-400 dark:text-neutral-500';
	}
}

/**
 * Check if action needs attention (overdue or due today)
 */
export function needsAttention(dueDate: string | null | undefined): boolean {
	const status = getDueDateStatus(dueDate);
	return status === 'overdue' || status === 'due-today';
}

/**
 * Get relative time description for due date
 */
export function getDueDateRelativeText(dueDate: string | null | undefined): string {
	if (!dueDate) return '';
	try {
		const due = new Date(dueDate);
		const now = new Date();
		const diffMs = due.getTime() - now.getTime();
		const diffDays = Math.floor(Math.abs(diffMs) / (1000 * 60 * 60 * 24));
		const diffHours = Math.floor(Math.abs(diffMs) / (1000 * 60 * 60));

		if (isDueToday(dueDate)) {
			if (diffMs < 0) return 'Due today (past time)';
			if (diffHours < 1) return 'Due in less than 1 hour';
			return `Due in ${diffHours} hour${diffHours === 1 ? '' : 's'}`;
		}

		if (diffMs < 0) {
			if (diffDays === 0) return 'Due today (past time)';
			if (diffDays === 1) return '1 day overdue';
			return `${diffDays} days overdue`;
		}

		if (diffDays === 1) return 'Due tomorrow';
		return `Due in ${diffDays} days`;
	} catch {
		return '';
	}
}
