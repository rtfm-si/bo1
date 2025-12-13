/**
 * PDF Report Generator
 *
 * Generates HTML reports from meeting session data for PDF export.
 * Extracted from meeting page for reusability and maintainability.
 *
 * CSS styles are in: /src/lib/styles/pdf-report.css
 * Markdown utilities: /src/lib/utils/markdown-formatter.ts
 * Data extraction: /src/lib/utils/report-data-extractor.ts
 */

import type { SSEEvent } from '$lib/api/sse-events';
import type { ActionStatus } from '$lib/api/types';
import { formatMarkdownToHtml, parseSynthesisSections } from './markdown-formatter';
import {
	extractExperts,
	extractSubProblems,
	extractSynthesis,
	countContributionsByExpert,
	calculateRounds,
	calculateDuration,
	getContributionCount,
	formatReportDate,
	getInitials
} from './report-data-extractor';

// Import CSS as raw string for inline embedding in HTML document
import pdfReportCss from '$lib/styles/pdf-report.css?raw';

// Session data interface (compatible with SessionDetailResponse and local SessionData)
interface SessionInfo {
	id: string;
	problem?: {
		statement: string;
		context?: Record<string, unknown>;
	};
	status: string;
	phase?: string | null;
	created_at: string;
}

/**
 * Action data for PDF report
 */
export interface ReportAction {
	id: string;
	title: string;
	description: string;
	status: ActionStatus;
	priority: 'high' | 'medium' | 'low';
	timeline: string;
	target_end_date: string | null;
	// Extended fields for full details
	what_and_how?: string[];
	success_criteria?: string[];
	dependencies?: string[];
	assignee?: string | null;
	progress_value?: number | null;
	progress_type?: 'percentage' | 'points' | 'status' | null;
	estimated_effort_points?: number | null;
	category?: string;
}

/**
 * Parameters for generateReportHTML function
 */
export interface ReportGeneratorParams {
	/** The session data containing problem statement and status */
	session: SessionInfo;
	/** Array of SSE events from the meeting */
	events: SSEEvent[];
	/** Session ID for footer metadata */
	sessionId: string;
	/** Optional actions to include in report */
	actions?: ReportAction[];
}

/**
 * Render an expert card HTML
 */
function renderExpertCard(
	expert: { name: string; displayName: string; archetype: string; expertise: string[] },
	contributionCount: number
): string {
	const initials = getInitials(expert.name);
	return `
		<div class="expert-card">
			<div class="expert-avatar">${initials}</div>
			<div class="expert-name">${expert.name}</div>
			<div class="expert-role">${expert.archetype || 'Domain Expert'}</div>
			<div class="expert-tags">
				<span class="tag tag-contributions">${contributionCount} contribution${contributionCount !== 1 ? 's' : ''}</span>
				${expert.expertise
					?.slice(0, 2)
					.map((e: string) => `<span class="tag">${e}</span>`)
					.join('') || ''}
			</div>
		</div>`;
}

/**
 * Render a focus area item HTML
 */
function renderFocusArea(subProblem: { goal?: string } | string, index: number): string {
	const goal = typeof subProblem === 'string' ? subProblem : subProblem.goal || subProblem;
	return `
		<div class="focus-area">
			<span class="focus-number">${index + 1}</span>
			<div class="focus-content">
				<div class="focus-title">${goal}</div>
			</div>
		</div>`;
}

/**
 * Render a section with header and content
 */
function renderSection(sectionNum: number, title: string, content: string, boxClass: string): string {
	return `
		<div class="section">
			<div class="section-header">
				<span class="section-number">${sectionNum}</span>
				<span class="section-title">${title}</span>
			</div>
			<div class="${boxClass}">
				<div class="${boxClass === 'recommendation-box' ? 'recommendation-content' : 'analysis-content'}">${content}</div>
			</div>
		</div>`;
}

/**
 * Format a date string to a readable format
 */
function formatDate(dateStr: string | null): string {
	if (!dateStr) return 'Not set';
	try {
		return new Date(dateStr).toLocaleDateString('en-GB', {
			day: 'numeric',
			month: 'short',
			year: 'numeric'
		});
	} catch {
		return 'Not set';
	}
}

/**
 * Check if a date is overdue (past today)
 */
function isOverdue(dateStr: string | null): boolean {
	if (!dateStr) return false;
	try {
		const dueDate = new Date(dateStr);
		const today = new Date();
		today.setHours(0, 0, 0, 0);
		return dueDate < today;
	} catch {
		return false;
	}
}

/**
 * Truncate text with ellipsis if too long
 */
function truncateText(text: string, maxLength: number): string {
	if (!text || text.length <= maxLength) return text;
	return text.substring(0, maxLength).trim() + '...';
}

/**
 * Format progress value for display
 */
function formatProgress(value: number | null | undefined, type: string | null | undefined): string {
	if (value === null || value === undefined) return '';
	if (type === 'percentage') return `${value}%`;
	if (type === 'points') return `${value} pts`;
	return `${value}`;
}

/**
 * Get status badge class
 */
function getStatusClass(status: ActionStatus): string {
	const statusClasses: Record<ActionStatus, string> = {
		todo: 'status-todo',
		in_progress: 'status-in-progress',
		blocked: 'status-blocked',
		in_review: 'status-in-review',
		done: 'status-done',
		cancelled: 'status-cancelled'
	};
	return statusClasses[status] || 'status-todo';
}

/**
 * Get priority badge class
 */
function getPriorityClass(priority: 'high' | 'medium' | 'low'): string {
	return `priority-${priority}`;
}

/**
 * Render list items HTML (for what_and_how, success_criteria, dependencies)
 */
function renderListItems(items: string[] | undefined, limit: number = 3): string {
	if (!items || items.length === 0) return '';
	const displayItems = items.slice(0, limit);
	const remaining = items.length - limit;
	let html = displayItems.map((item) => `<li>${truncateText(item, 150)}</li>`).join('');
	if (remaining > 0) {
		html += `<li class="more-items">+${remaining} more...</li>`;
	}
	return html;
}

/**
 * Render an action item HTML with full details
 */
function renderActionItem(action: ReportAction): string {
	const statusLabel = action.status.replace('_', ' ');
	const overdue = isOverdue(action.target_end_date) && action.status !== 'done' && action.status !== 'cancelled';
	const description = truncateText(action.description || '', 500);
	const progress = formatProgress(action.progress_value, action.progress_type);

	// Build optional sections
	const whatAndHowHtml = action.what_and_how?.length
		? `<div class="action-section">
			<div class="action-section-label">How to Complete</div>
			<ul class="action-list">${renderListItems(action.what_and_how)}</ul>
		</div>`
		: '';

	const successCriteriaHtml = action.success_criteria?.length
		? `<div class="action-section">
			<div class="action-section-label">Success Criteria</div>
			<ul class="action-list">${renderListItems(action.success_criteria)}</ul>
		</div>`
		: '';

	const dependenciesHtml = action.dependencies?.length
		? `<div class="action-section">
			<div class="action-section-label">Dependencies</div>
			<ul class="action-list action-dependencies">${renderListItems(action.dependencies)}</ul>
		</div>`
		: '';

	return `
		<div class="action-item${overdue ? ' action-overdue' : ''}">
			<div class="action-header">
				<span class="action-title">${action.title}</span>
				<div class="action-badges">
					<span class="action-status ${getStatusClass(action.status)}">${statusLabel}</span>
					<span class="action-priority ${getPriorityClass(action.priority)}">${action.priority}</span>
					${action.category ? `<span class="action-category">${action.category}</span>` : ''}
				</div>
			</div>
			${description ? `<div class="action-description">${description}</div>` : ''}
			${whatAndHowHtml}
			${successCriteriaHtml}
			${dependenciesHtml}
			<div class="action-meta">
				${action.timeline ? `<span class="action-timeline">${action.timeline}</span>` : ''}
				${action.target_end_date ? `<span class="action-due${overdue ? ' overdue' : ''}">Due: ${formatDate(action.target_end_date)}${overdue ? ' (Overdue)' : ''}</span>` : ''}
				${action.assignee ? `<span class="action-assignee">Assigned: ${action.assignee}</span>` : ''}
				${progress ? `<span class="action-progress">Progress: ${progress}</span>` : ''}
				${action.estimated_effort_points ? `<span class="action-effort">Effort: ${action.estimated_effort_points} pts</span>` : ''}
			</div>
		</div>`;
}

/**
 * Render actions section HTML
 */
function renderActionsSection(actions: ReportAction[], sectionNum: number, showEmptyState: boolean = true): string {
	// Handle empty state
	if (!actions || actions.length === 0) {
		if (!showEmptyState) return '';
		return `
		<div class="section">
			<div class="section-header">
				<span class="section-number">${sectionNum}</span>
				<span class="section-title">Action Items</span>
			</div>
			<div class="actions-empty">
				<p>No actions were generated for this meeting.</p>
			</div>
		</div>`;
	}

	// Sort by priority (high first) then by status
	const sortedActions = [...actions].sort((a, b) => {
		const priorityOrder = { high: 0, medium: 1, low: 2 };
		const priorityDiff = priorityOrder[a.priority] - priorityOrder[b.priority];
		if (priorityDiff !== 0) return priorityDiff;
		return a.status.localeCompare(b.status);
	});

	// Limit to 50 actions to prevent PDF overflow
	const displayActions = sortedActions.slice(0, 50);
	const hiddenCount = sortedActions.length - 50;

	return `
		<div class="section">
			<div class="section-header">
				<span class="section-number">${sectionNum}</span>
				<span class="section-title">Action Items (${actions.length})</span>
			</div>
			<div class="actions-section">
				${displayActions.map((action) => renderActionItem(action)).join('')}
				${hiddenCount > 0 ? `<div class="actions-truncated">+${hiddenCount} more actions not shown</div>` : ''}
			</div>
		</div>`;
}

/**
 * Generate HTML report from session data and events.
 *
 * Creates a professionally formatted HTML document that can be
 * opened in a new window and printed/saved as PDF.
 *
 * Supports both lean synthesis format (The Bottom Line, Why This Matters, etc.)
 * and legacy format (Executive Summary, Recommendation, Rationale).
 *
 * @param params - Report generation parameters
 * @returns Complete HTML document as a string
 */
export function generateReportHTML(params: ReportGeneratorParams): string {
	const { session, events, sessionId, actions } = params;

	if (!session) return '';

	// Extract data using utility functions
	const synthesis = extractSynthesis(events);
	const sections = parseSynthesisSections(synthesis);
	const experts = extractExperts(events);
	const contributionsByDisplayName = countContributionsByExpert(events);
	const subProblems = extractSubProblems(events);
	const totalRounds = calculateRounds(events);
	const contributionCount = getContributionCount(events);
	const durationMins = calculateDuration(session.created_at, events);
	const reportDate = formatReportDate();

	// Build synthesis sections HTML and track section count for actions
	let lastSectionNum = 0;
	const buildSynthesisSections = (): string => {
		const sectionStart = subProblems.length > 0 ? 3 : 2;
		let sectionNum = sectionStart;
		let html = '';

		// New lean format sections
		if (sections.bottomLine) {
			html += renderSection(sectionNum++, 'The Bottom Line', formatMarkdownToHtml(sections.bottomLine), 'recommendation-box');
		}

		if (sections.whyItMatters) {
			html += renderSection(sectionNum++, 'Why This Matters', formatMarkdownToHtml(sections.whyItMatters), 'full-analysis');
		}

		if (sections.nextSteps) {
			html += renderSection(sectionNum++, 'What To Do Next', formatMarkdownToHtml(sections.nextSteps), 'full-analysis');
		}

		if (sections.keyRisks) {
			html += renderSection(sectionNum++, 'Key Risks', formatMarkdownToHtml(sections.keyRisks), 'full-analysis');
		}

		if (sections.confidence) {
			html += renderSection(sectionNum++, 'Board Confidence', formatMarkdownToHtml(sections.confidence), 'full-analysis');
		}

		// Legacy format fallback (if no lean sections found)
		if (!sections.bottomLine && !sections.whyItMatters && !sections.nextSteps) {
			if (sections.recommendation) {
				html += renderSection(sectionNum++, 'Recommendation', formatMarkdownToHtml(sections.recommendation), 'recommendation-box');
			}
			if (sections.rationale) {
				html += renderSection(sectionNum++, 'Rationale', formatMarkdownToHtml(sections.rationale), 'full-analysis');
			}
		}

		// Full synthesis fallback (if nothing else parsed)
		if (!html && synthesis) {
			html = renderSection(sectionStart, 'Analysis', formatMarkdownToHtml(synthesis), 'full-analysis');
			sectionNum++;
		}

		// Track the last section number for actions section
		lastSectionNum = sectionNum;
		return html;
	};

	// Build actions section HTML (always show section, with empty state if no actions)
	const buildActionsSection = (): string => {
		return renderActionsSection(actions || [], lastSectionNum, true);
	};

	return `<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<title>Decision Report - ${session.problem?.statement?.substring(0, 50) || 'Strategic Analysis'}</title>
	<style>${pdfReportCss}</style>
</head>
<body>
	<div class="page">
		<!-- Cover Section -->
		<div class="cover">
			<div class="cover-header">
				<div class="logo-section">
					<div class="logo">B1</div>
					<span class="brand-name">Board of One</span>
				</div>
				<span class="report-type">Decision Report</span>
			</div>

			<h1 class="decision-question">${session.problem?.statement || 'Strategic Decision Analysis'}</h1>
			<p class="report-meta">${reportDate}</p>
		</div>

		<!-- Metrics Grid -->
		<div class="metrics-grid">
			<div class="metric-card">
				<div class="metric-value">${experts.length}</div>
				<div class="metric-label">Expert Perspectives</div>
			</div>
			<div class="metric-card">
				<div class="metric-value">${totalRounds}</div>
				<div class="metric-label">Meeting Rounds</div>
			</div>
			<div class="metric-card">
				<div class="metric-value">${contributionCount}</div>
				<div class="metric-label">Key Insights</div>
			</div>
			<div class="metric-card">
				<div class="metric-value">${durationMins}m</div>
				<div class="metric-label">Analysis Time</div>
			</div>
		</div>

		<!-- Executive Summary -->
		${
			sections.executiveSummary
				? `
		<div class="exec-summary">
			<div class="exec-summary-label">Executive Summary</div>
			<div class="exec-summary-text">${sections.executiveSummary}</div>
		</div>
		`
				: ''
		}

		<!-- Expert Panel -->
		<div class="section">
			<div class="section-header">
				<span class="section-number">1</span>
				<span class="section-title">Expert Panel</span>
			</div>
			<div class="expert-grid">
				${experts.map((exp) => renderExpertCard(exp, contributionsByDisplayName.get(exp.displayName) || 0)).join('')}
			</div>
		</div>

		<!-- Focus Areas -->
		${
			subProblems.length > 0
				? `
		<div class="section">
			<div class="section-header">
				<span class="section-number">2</span>
				<span class="section-title">Focus Areas Analyzed</span>
			</div>
			${subProblems.map((sp, i) => renderFocusArea(sp, i)).join('')}
		</div>
		`
				: ''
		}

		<!-- Synthesis Sections (dynamic based on format) -->
		${buildSynthesisSections()}

		<!-- Action Items -->
		${buildActionsSection()}

		<!-- Footer -->
		<div class="footer">
			<div class="footer-brand">
				<div class="footer-logo">B1</div>
				<span class="footer-name">Board of One</span>
			</div>

			<div class="disclaimer">
				<div class="disclaimer-title">AI-Generated Content Disclaimer</div>
				<div class="disclaimer-text">
					This report was generated using AI-assisted deliberation and is intended for learning and knowledge purposes only.
					It does not constitute professional, legal, financial, or medical advice. Always verify recommendations with
					licensed professionals appropriate to your jurisdiction and circumstances before taking action.
				</div>
			</div>

			<div class="session-info">
				Session ID: ${sessionId}<br>
				Generated: ${new Date().toISOString()}
			</div>
		</div>
	</div>
</body>
</html>`;
}
