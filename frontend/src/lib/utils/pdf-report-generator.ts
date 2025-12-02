/**
 * PDF Report Generator
 *
 * Generates HTML reports from meeting session data for PDF export.
 * Extracted from meeting page for reusability and maintainability.
 */

import type { SSEEvent } from '$lib/api/sse-events';

// Session data interface (compatible with SessionDetailResponse and local SessionData)
interface SessionInfo {
	id: string;
	problem?: {
		statement: string;
		context?: Record<string, any>;
	};
	status: string;
	phase?: string | null;
	created_at: string;
}

// Type for persona data in persona_selected events
interface PersonaSelectedData {
	persona?: {
		name?: string;
		display_name?: string;
		archetype?: string;
		domain_expertise?: string[];
	};
	rationale?: string;
}

// Type for synthesis event data
interface SynthesisData {
	synthesis?: string;
}

// Type for decomposition event data
interface DecompositionData {
	sub_problems?: Array<{ goal?: string }>;
}

// Type for contribution event data
interface ContributionData {
	persona_name?: string;
	round?: number;
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
	const { session, events, sessionId } = params;

	if (!session) return '';

	// Find meta-synthesis and synthesis events
	const metaSynthesisEvent = events.find(e => e.event_type === 'meta_synthesis_complete');
	const synthesisCompleteEvent = events.find(e => e.event_type === 'synthesis_complete');

	// Extract synthesis content
	const metaData = metaSynthesisEvent?.data as SynthesisData | undefined;
	const synthData = synthesisCompleteEvent?.data as SynthesisData | undefined;
	const synthesis = metaData?.synthesis || synthData?.synthesis || '';

	// Parse synthesis sections (supports both lean and legacy formats)
	const getSection = (text: string, sectionNames: string[]): string => {
		if (!text) return '';
		// Try each section name variant
		for (const name of sectionNames) {
			const pattern = new RegExp(`##?\\s*${name}\\s*\\n+([\\s\\S]*?)(?=\\n##|\\n---(?:\\n|$)|$)`, 'i');
			const match = text.match(pattern);
			if (match) {
				return match[1].trim();
			}
		}
		return '';
	};

	// Extract sections - supports lean template (new) and legacy format
	const bottomLine = getSection(synthesis, ['The Bottom Line', 'Executive Summary']);
	const whyItMatters = getSection(synthesis, ['Why This Matters', 'Why It Matters']);
	const nextSteps = getSection(synthesis, ['What To Do Next', 'Next Steps', 'Recommendation']);
	const keyRisks = getSection(synthesis, ['Key Risks', 'Risks']);
	const confidence = getSection(synthesis, ['Board Confidence', 'Confidence Assessment']);
	const rationale = getSection(synthesis, ['Rationale']);

	// For executive summary display, use bottom line or first section
	const executiveSummary = bottomLine || rationale?.substring(0, 500) || '';
	// For recommendation, combine next steps or use legacy recommendation
	const recommendation = nextSteps || getSection(synthesis, ['Recommendation']);

	// Extract expert info from persona_selected events
	const expertEvents = events.filter(e => e.event_type === 'persona_selected');
	const experts = expertEvents.map(e => {
		const data = e.data as PersonaSelectedData;
		return {
			name: data.persona?.name || data.persona?.display_name || 'Expert',
			displayName: data.persona?.display_name || data.persona?.name || 'Expert',
			archetype: data.persona?.archetype || '',
			expertise: data.persona?.domain_expertise || [],
			rationale: data.rationale || ''
		};
	});

	// Count contributions per expert (keyed by display_name since that's what contribution events use)
	const contributions = events.filter(e => e.event_type === 'contribution');
	const contributionsByDisplayName = new Map<string, number>();
	contributions.forEach(c => {
		const data = c.data as ContributionData;
		const displayName = data.persona_name || 'Unknown';
		contributionsByDisplayName.set(displayName, (contributionsByDisplayName.get(displayName) || 0) + 1);
	});

	// Get sub-problems
	const decompositionEvent = events.find(e => e.event_type === 'decomposition_complete');
	const decompositionData = decompositionEvent?.data as DecompositionData | undefined;
	const subProblems = decompositionData?.sub_problems || [];

	// Calculate rounds - try event-based first, fallback to contribution round numbers
	const roundEvents = events.filter(e =>
		e.event_type === 'round_started' || e.event_type === 'initial_round_started'
	);
	let totalRounds = roundEvents.length;

	// Fallback: calculate max round from contributions if no round events
	if (totalRounds === 0 && contributions.length > 0) {
		const roundNumbers = contributions.map(c => {
			const data = c.data as ContributionData;
			return data.round || 0;
		});
		totalRounds = Math.max(...roundNumbers, 0);
	}

	// Duration
	const durationMs = new Date(session.created_at).getTime();
	const endTime = events.length > 0
		? new Date(events[events.length - 1].timestamp).getTime()
		: new Date().getTime();
	const durationMins = Math.round((endTime - durationMs) / 60000);

	// Format date
	const reportDate = new Date().toLocaleDateString('en-US', {
		year: 'numeric',
		month: 'long',
		day: 'numeric'
	});

	// Convert markdown-style formatting to HTML
	const formatContent = (text: string): string => {
		if (!text) return '';
		return text
			// Headers
			.replace(/^### (.+)$/gm, '<h4>$1</h4>')
			.replace(/^## (.+)$/gm, '<h3>$1</h3>')
			.replace(/^# (.+)$/gm, '<h2>$1</h2>')
			// Bold
			.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
			// Italic
			.replace(/\*([^*]+)\*/g, '<em>$1</em>')
			// Numbered lists
			.replace(/^\d+\.\s+\*\*([^:*]+):\*\*\s*(.+)$/gm, '<li><strong>$1:</strong> $2</li>')
			.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>')
			// Bullet lists
			.replace(/^[-•]\s+(.+)$/gm, '<li>$1</li>')
			// Wrap consecutive li elements in ul/ol
			.replace(/((?:<li>[\s\S]*?<\/li>\s*)+)/g, '<ul>$1</ul>')
			// Paragraphs (double newlines)
			.replace(/\n\n+/g, '</p><p>')
			// Single newlines within paragraphs
			.replace(/\n/g, '<br>')
			// Wrap in paragraph if not already structured
			.replace(/^(?!<[hup])/, '<p>')
			.replace(/(?<![>])$/, '</p>');
	};

	// Brand colors
	const brandTeal = '#00C3D0';
	const brandTealDark = '#03767E';

	return `<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<title>Decision Report - ${session.problem?.statement?.substring(0, 50) || 'Strategic Analysis'}</title>
	<style>
		@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

		:root {
			--brand-teal: ${brandTeal};
			--brand-teal-dark: ${brandTealDark};
			--brand-teal-light: #e6fafb;
			--text-primary: #111827;
			--text-secondary: #4b5563;
			--text-muted: #6b7280;
			--border-color: #e5e7eb;
			--bg-subtle: #f9fafb;
			--bg-card: #ffffff;
		}

		* { box-sizing: border-box; margin: 0; padding: 0; }

		body {
			font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
			font-size: 11pt;
			line-height: 1.6;
			color: var(--text-primary);
			background: white;
		}

		.page {
			max-width: 8.5in;
			margin: 0 auto;
			padding: 0.75in;
		}

		/* Cover Section */
		.cover {
			margin-bottom: 48px;
			padding-bottom: 32px;
			border-bottom: 3px solid var(--brand-teal);
		}

		.cover-header {
			display: flex;
			align-items: center;
			justify-content: space-between;
			margin-bottom: 40px;
		}

		.logo-section {
			display: flex;
			align-items: center;
			gap: 12px;
		}

		.logo {
			width: 48px;
			height: 48px;
			background: linear-gradient(180deg, ${brandTeal} 0%, ${brandTealDark} 100%);
			border-radius: 10px;
			display: flex;
			align-items: center;
			justify-content: center;
			color: white;
			font-weight: 700;
			font-size: 20px;
		}

		.brand-name {
			font-size: 18px;
			font-weight: 600;
			color: var(--text-primary);
		}

		.report-type {
			text-transform: uppercase;
			font-size: 11px;
			font-weight: 600;
			letter-spacing: 1.5px;
			color: var(--brand-teal-dark);
			padding: 6px 12px;
			background: var(--brand-teal-light);
			border-radius: 4px;
		}

		.decision-question {
			font-size: 28px;
			font-weight: 700;
			color: var(--text-primary);
			line-height: 1.3;
			margin-bottom: 16px;
		}

		.report-meta {
			font-size: 13px;
			color: var(--text-muted);
		}

		/* Metrics Grid */
		.metrics-grid {
			display: grid;
			grid-template-columns: repeat(4, 1fr);
			gap: 1px;
			background: var(--border-color);
			border: 1px solid var(--border-color);
			border-radius: 8px;
			overflow: hidden;
			margin: 32px 0;
		}

		.metric-card {
			background: white;
			padding: 20px;
			text-align: center;
		}

		.metric-value {
			font-size: 32px;
			font-weight: 700;
			color: var(--brand-teal-dark);
			line-height: 1;
		}

		.metric-label {
			font-size: 11px;
			font-weight: 600;
			text-transform: uppercase;
			letter-spacing: 0.5px;
			color: var(--text-muted);
			margin-top: 8px;
		}

		/* Executive Summary */
		.exec-summary {
			background: linear-gradient(135deg, var(--brand-teal-light) 0%, #f0fdfa 100%);
			border-left: 4px solid var(--brand-teal);
			padding: 24px 28px;
			border-radius: 0 8px 8px 0;
			margin: 32px 0;
		}

		.exec-summary-label {
			font-size: 11px;
			font-weight: 600;
			text-transform: uppercase;
			letter-spacing: 1px;
			color: var(--brand-teal-dark);
			margin-bottom: 12px;
		}

		.exec-summary-text {
			font-size: 14px;
			line-height: 1.7;
			color: var(--text-primary);
		}

		/* Section Headers */
		.section {
			margin: 40px 0;
		}

		.section-header {
			display: flex;
			align-items: center;
			gap: 12px;
			margin-bottom: 20px;
			padding-bottom: 12px;
			border-bottom: 2px solid var(--border-color);
		}

		.section-number {
			width: 28px;
			height: 28px;
			background: var(--brand-teal);
			color: white;
			border-radius: 50%;
			display: flex;
			align-items: center;
			justify-content: center;
			font-size: 13px;
			font-weight: 600;
		}

		.section-title {
			font-size: 18px;
			font-weight: 700;
			color: var(--text-primary);
		}

		/* Expert Panel */
		.expert-grid {
			display: grid;
			grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
			gap: 16px;
		}

		.expert-card {
			background: var(--bg-subtle);
			border: 1px solid var(--border-color);
			border-radius: 8px;
			padding: 16px;
		}

		.expert-avatar {
			width: 40px;
			height: 40px;
			background: linear-gradient(135deg, var(--brand-teal) 0%, var(--brand-teal-dark) 100%);
			border-radius: 50%;
			display: flex;
			align-items: center;
			justify-content: center;
			color: white;
			font-weight: 600;
			font-size: 16px;
			margin-bottom: 12px;
		}

		.expert-name {
			font-size: 14px;
			font-weight: 600;
			color: var(--text-primary);
			margin-bottom: 4px;
		}

		.expert-role {
			font-size: 12px;
			color: var(--text-secondary);
			margin-bottom: 8px;
		}

		.expert-tags {
			display: flex;
			flex-wrap: wrap;
			gap: 4px;
		}

		.tag {
			font-size: 10px;
			padding: 2px 8px;
			background: white;
			border: 1px solid var(--border-color);
			border-radius: 12px;
			color: var(--text-muted);
		}

		.tag-contributions {
			background: var(--brand-teal-light);
			border-color: var(--brand-teal);
			color: var(--brand-teal-dark);
			font-weight: 500;
		}

		/* Focus Areas */
		.focus-area {
			display: flex;
			align-items: flex-start;
			gap: 16px;
			padding: 16px 0;
			border-bottom: 1px solid var(--border-color);
		}

		.focus-area:last-child {
			border-bottom: none;
		}

		.focus-number {
			width: 32px;
			height: 32px;
			background: var(--brand-teal);
			color: white;
			border-radius: 8px;
			display: flex;
			align-items: center;
			justify-content: center;
			font-weight: 600;
			font-size: 14px;
			flex-shrink: 0;
		}

		.focus-content {
			flex: 1;
		}

		.focus-title {
			font-size: 14px;
			font-weight: 500;
			color: var(--text-primary);
		}

		/* Recommendation Section */
		.recommendation-box {
			background: white;
			border: 2px solid var(--brand-teal);
			border-radius: 12px;
			padding: 28px;
			margin: 24px 0;
		}

		.recommendation-content {
			font-size: 13px;
			line-height: 1.8;
			color: var(--text-primary);
		}

		.recommendation-content h2,
		.recommendation-content h3,
		.recommendation-content h4 {
			margin: 20px 0 12px 0;
			color: var(--text-primary);
		}

		.recommendation-content h2 { font-size: 18px; }
		.recommendation-content h3 { font-size: 15px; }
		.recommendation-content h4 { font-size: 13px; }

		.recommendation-content p {
			margin-bottom: 12px;
		}

		.recommendation-content ul {
			margin: 12px 0;
			padding-left: 24px;
		}

		.recommendation-content li {
			margin-bottom: 8px;
		}

		.recommendation-content strong {
			color: var(--brand-teal-dark);
		}

		/* Full Analysis */
		.full-analysis {
			background: var(--bg-subtle);
			border-radius: 8px;
			padding: 24px;
			margin: 24px 0;
		}

		.analysis-content {
			font-size: 12px;
			line-height: 1.8;
			color: var(--text-secondary);
			white-space: pre-wrap;
		}

		.analysis-content h2,
		.analysis-content h3,
		.analysis-content h4 {
			margin: 16px 0 8px 0;
			color: var(--text-primary);
		}

		.analysis-content ul {
			margin: 8px 0;
			padding-left: 20px;
		}

		.analysis-content li {
			margin-bottom: 6px;
		}

		/* Footer */
		.footer {
			margin-top: 48px;
			padding-top: 24px;
			border-top: 2px solid var(--border-color);
		}

		.footer-brand {
			display: flex;
			align-items: center;
			gap: 8px;
			margin-bottom: 16px;
		}

		.footer-logo {
			width: 24px;
			height: 24px;
			background: linear-gradient(180deg, ${brandTeal} 0%, ${brandTealDark} 100%);
			border-radius: 5px;
			display: flex;
			align-items: center;
			justify-content: center;
			color: white;
			font-weight: 700;
			font-size: 11px;
		}

		.footer-name {
			font-size: 13px;
			font-weight: 600;
			color: var(--text-primary);
		}

		.disclaimer {
			background: #fef3c7;
			border: 1px solid #fcd34d;
			border-radius: 8px;
			padding: 16px;
			margin: 16px 0;
		}

		.disclaimer-title {
			font-size: 11px;
			font-weight: 600;
			text-transform: uppercase;
			letter-spacing: 0.5px;
			color: #92400e;
			margin-bottom: 8px;
		}

		.disclaimer-text {
			font-size: 11px;
			line-height: 1.6;
			color: #78350f;
		}

		.session-info {
			font-size: 10px;
			color: var(--text-muted);
			margin-top: 12px;
		}

		/* Print Styles */
		@media print {
			body {
				-webkit-print-color-adjust: exact !important;
				print-color-adjust: exact !important;
			}
			.page {
				padding: 0.5in;
				max-width: none;
			}
			.section {
				page-break-inside: avoid;
			}
			.expert-grid {
				page-break-inside: avoid;
			}
			.recommendation-box {
				page-break-inside: avoid;
			}
		}

		@page {
			margin: 0.5in;
			size: letter;
		}
	</style>
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
				<div class="metric-value">${contributions.length}</div>
				<div class="metric-label">Key Insights</div>
			</div>
			<div class="metric-card">
				<div class="metric-value">${durationMins}m</div>
				<div class="metric-label">Analysis Time</div>
			</div>
		</div>

		<!-- Executive Summary -->
		${executiveSummary ? `
		<div class="exec-summary">
			<div class="exec-summary-label">Executive Summary</div>
			<div class="exec-summary-text">${executiveSummary}</div>
		</div>
		` : ''}

		<!-- Expert Panel -->
		<div class="section">
			<div class="section-header">
				<span class="section-number">1</span>
				<span class="section-title">Expert Panel</span>
			</div>
			<div class="expert-grid">
				${experts.map(exp => {
					const initials = exp.name.split(' ').map((n: string) => n[0]).join('').substring(0, 2);
					const contribCount = contributionsByDisplayName.get(exp.displayName) || 0;
					return `
					<div class="expert-card">
						<div class="expert-avatar">${initials}</div>
						<div class="expert-name">${exp.name}</div>
						<div class="expert-role">${exp.archetype || 'Domain Expert'}</div>
						<div class="expert-tags">
							<span class="tag tag-contributions">${contribCount} contribution${contribCount !== 1 ? 's' : ''}</span>
							${exp.expertise?.slice(0, 2).map((e: string) => `<span class="tag">${e}</span>`).join('') || ''}
						</div>
					</div>
				`}).join('')}
			</div>
		</div>

		<!-- Focus Areas -->
		${subProblems.length > 0 ? `
		<div class="section">
			<div class="section-header">
				<span class="section-number">2</span>
				<span class="section-title">Focus Areas Analyzed</span>
			</div>
			${subProblems.map((sp: any, i: number) => `
				<div class="focus-area">
					<span class="focus-number">${i + 1}</span>
					<div class="focus-content">
						<div class="focus-title">${sp.goal || sp}</div>
					</div>
				</div>
			`).join('')}
		</div>
		` : ''}

		<!-- Recommendation (supports lean and legacy formats) -->
		${(() => {
			const sectionStart = subProblems.length > 0 ? 3 : 2;
			let sectionNum = sectionStart;
			let html = '';

			// New lean format sections
			if (bottomLine) {
				html += `
				<div class="section">
					<div class="section-header">
						<span class="section-number">${sectionNum++}</span>
						<span class="section-title">The Bottom Line</span>
					</div>
					<div class="recommendation-box">
						<div class="recommendation-content">${formatContent(bottomLine)}</div>
					</div>
				</div>`;
			}

			if (whyItMatters) {
				html += `
				<div class="section">
					<div class="section-header">
						<span class="section-number">${sectionNum++}</span>
						<span class="section-title">Why This Matters</span>
					</div>
					<div class="full-analysis">
						<div class="analysis-content">${formatContent(whyItMatters)}</div>
					</div>
				</div>`;
			}

			if (nextSteps) {
				html += `
				<div class="section">
					<div class="section-header">
						<span class="section-number">${sectionNum++}</span>
						<span class="section-title">What To Do Next</span>
					</div>
					<div class="full-analysis">
						<div class="analysis-content">${formatContent(nextSteps)}</div>
					</div>
				</div>`;
			}

			if (keyRisks) {
				html += `
				<div class="section">
					<div class="section-header">
						<span class="section-number">${sectionNum++}</span>
						<span class="section-title">Key Risks</span>
					</div>
					<div class="full-analysis">
						<div class="analysis-content">${formatContent(keyRisks)}</div>
					</div>
				</div>`;
			}

			if (confidence) {
				html += `
				<div class="section">
					<div class="section-header">
						<span class="section-number">${sectionNum++}</span>
						<span class="section-title">Board Confidence</span>
					</div>
					<div class="full-analysis">
						<div class="analysis-content">${formatContent(confidence)}</div>
					</div>
				</div>`;
			}

			// Legacy format fallback (if no lean sections found)
			if (!bottomLine && !whyItMatters && !nextSteps) {
				if (recommendation) {
					html += `
					<div class="section">
						<div class="section-header">
							<span class="section-number">${sectionNum++}</span>
							<span class="section-title">Recommendation</span>
						</div>
						<div class="recommendation-box">
							<div class="recommendation-content">${formatContent(recommendation)}</div>
						</div>
					</div>`;
				}
				if (rationale) {
					html += `
					<div class="section">
						<div class="section-header">
							<span class="section-number">${sectionNum++}</span>
							<span class="section-title">Rationale</span>
						</div>
						<div class="full-analysis">
							<div class="analysis-content">${formatContent(rationale)}</div>
						</div>
					</div>`;
				}
			}

			// Full synthesis fallback (if nothing else parsed)
			if (!html && synthesis) {
				html = `
				<div class="section">
					<div class="section-header">
						<span class="section-number">${sectionStart}</span>
						<span class="section-title">Analysis</span>
					</div>
					<div class="full-analysis">
						<div class="analysis-content">${formatContent(synthesis)}</div>
					</div>
				</div>`;
			}

			return html;
		})()}

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
