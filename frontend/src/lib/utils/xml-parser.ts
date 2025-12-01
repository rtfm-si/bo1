/**
 * XML Parser Utilities
 *
 * Extracts structured data from XML-formatted synthesis reports.
 * Handles both well-formed XML and malformed/plain text gracefully.
 */

export interface SynthesisSection {
	executive_summary?: string;
	recommendation?: string;
	rationale?: string;
	implementation_considerations?: string;
	confidence_assessment?: string;
	open_questions?: string;
	vote_breakdown?: string;
	risks_and_mitigations?: string;
	success_metrics?: string;
	timeline?: string;
	resources_required?: string;
	convergence_point?: string;
	dissenting_views?: string;
	warning?: string; // AI-generated content disclaimer
}

/**
 * Strip <thinking> tags from synthesis content
 * These are internal LLM reasoning that shouldn't be displayed to users
 */
function stripThinkingTags(content: string): string {
	// Remove complete <thinking>...</thinking> blocks
	let cleaned = content.replace(/<thinking>[\s\S]*?<\/thinking>/gi, '');
	// Remove any orphaned opening/closing thinking tags
	cleaned = cleaned.replace(/<\/?thinking>/gi, '');
	return cleaned.trim();
}

/**
 * Extract and remove the AI warning/disclaimer from content
 */
function extractWarning(content: string): { content: string; warning: string | undefined } {
	// Look for the warning pattern at the end
	const warningPatterns = [
		/---\s*\n\s*Warning:[\s\S]*$/i,
		/\n\s*Warning:\s*This content is AI-generated[\s\S]*$/i,
	];

	for (const pattern of warningPatterns) {
		const match = content.match(pattern);
		if (match) {
			const warning = match[0]
				.replace(/^---\s*\n\s*/, '')
				.replace(/^Warning:\s*/i, '')
				.trim();
			return {
				content: content.replace(pattern, '').trim(),
				warning,
			};
		}
	}

	return { content, warning: undefined };
}

/**
 * Map common markdown header names to our section keys
 */
const MARKDOWN_TO_SECTION_KEY: Record<string, keyof SynthesisSection> = {
	'executive summary': 'executive_summary',
	recommendation: 'recommendation',
	rationale: 'rationale',
	'implementation considerations': 'implementation_considerations',
	'confidence assessment': 'confidence_assessment',
	'open questions': 'open_questions',
	'vote breakdown': 'vote_breakdown',
	'risks & mitigations': 'risks_and_mitigations',
	'risks and mitigations': 'risks_and_mitigations',
	'success metrics': 'success_metrics',
	timeline: 'timeline',
	'resources required': 'resources_required',
	'the convergence point': 'convergence_point',
	'convergence point': 'convergence_point',
	'dissenting views': 'dissenting_views',
	// Handle variations
	'the real problem': 'rationale',
	'why community infrastructure matters more': 'rationale',
};

/**
 * Parse markdown-formatted synthesis into sections
 * Handles ## Section Name format
 */
function parseMarkdownSections(content: string): SynthesisSection {
	const sections: SynthesisSection = {};

	// Split by ## headers (level 2)
	const headerRegex = /^##\s+(.+?)$/gm;
	const parts: { header: string; content: string }[] = [];

	let lastIndex = 0;
	let lastHeader = '';
	let match;

	// Find all headers and their positions
	const matches: { header: string; index: number }[] = [];
	while ((match = headerRegex.exec(content)) !== null) {
		matches.push({ header: match[1].trim(), index: match.index });
	}

	// Extract content between headers
	for (let i = 0; i < matches.length; i++) {
		const current = matches[i];
		const nextIndex = i < matches.length - 1 ? matches[i + 1].index : content.length;

		// Get content after the header line
		const headerLineEnd = content.indexOf('\n', current.index);
		const sectionContent = content.slice(headerLineEnd + 1, nextIndex).trim();

		parts.push({ header: current.header, content: sectionContent });
	}

	// Map headers to section keys
	for (const part of parts) {
		const normalizedHeader = part.header.toLowerCase();
		const sectionKey = MARKDOWN_TO_SECTION_KEY[normalizedHeader];

		if (sectionKey) {
			// If we already have content for this section (like rationale), append
			if (sections[sectionKey]) {
				sections[sectionKey] += '\n\n### ' + part.header + '\n\n' + part.content;
			} else {
				sections[sectionKey] = part.content;
			}
		}
	}

	return sections;
}

/**
 * Check if content appears to be markdown-formatted (has ## headers)
 */
export function isMarkdownFormatted(content: string): boolean {
	return /^##\s+/m.test(content);
}

/**
 * Parse synthesis output into structured sections
 * Handles both XML format (<executive_summary>) and Markdown format (## Executive Summary)
 */
export function parseSynthesisXML(xmlString: string): SynthesisSection {
	// First, strip any thinking tags (defense in depth - backend should do this too)
	let cleanedContent = stripThinkingTags(xmlString);

	// Extract warning/disclaimer (will be displayed separately)
	const { content: contentWithoutWarning, warning } = extractWarning(cleanedContent);
	cleanedContent = contentWithoutWarning;

	let sections: SynthesisSection = {};

	// Try XML parsing first
	const xmlSectionNames = [
		'executive_summary',
		'recommendation',
		'rationale',
		'implementation_considerations',
		'confidence_assessment',
		'open_questions',
		'vote_breakdown',
		'risks_and_mitigations',
		'success_metrics',
		'timeline',
		'resources_required',
		'convergence_point',
		'dissenting_views',
	] as const;

	for (const sectionName of xmlSectionNames) {
		const content = extractXMLSection(cleanedContent, sectionName);
		if (content) {
			sections[sectionName] = content;
		}
	}

	// Fallback: Try unified_recommendation for meta-synthesis (maps to recommendation)
	if (!sections.recommendation) {
		const unifiedRec = extractXMLSection(cleanedContent, 'unified_recommendation');
		if (unifiedRec) {
			sections.recommendation = unifiedRec;
		}
	}

	// Fallback: Try unified_action_plan for meta-synthesis (maps to implementation_considerations)
	if (!sections.implementation_considerations) {
		const actionPlan = extractXMLSection(cleanedContent, 'unified_action_plan');
		if (actionPlan) {
			sections.implementation_considerations = actionPlan;
		}
	}

	// Fallback: Try integrated_risk_assessment for meta-synthesis (maps to risks_and_mitigations)
	if (!sections.risks_and_mitigations) {
		const riskAssessment = extractXMLSection(cleanedContent, 'integrated_risk_assessment');
		if (riskAssessment) {
			sections.risks_and_mitigations = riskAssessment;
		}
	}

	// If no XML sections found, try markdown parsing
	if (Object.keys(sections).length === 0 && isMarkdownFormatted(cleanedContent)) {
		sections = parseMarkdownSections(cleanedContent);
	}

	// If still no sections, return the cleaned content as executive_summary
	if (Object.keys(sections).length === 0) {
		sections.executive_summary = cleanedContent;
	}

	// Always include warning if present
	if (warning) {
		sections.warning = warning;
	}

	return sections;
}

/**
 * Extract content from a specific XML tag
 */
function extractXMLSection(xmlString: string, tagName: string): string | undefined {
	// Try strict XML match first
	const strictRegex = new RegExp(`<${tagName}>([\\s\\S]*?)</${tagName}>`, 'i');
	const strictMatch = xmlString.match(strictRegex);

	if (strictMatch && strictMatch[1]) {
		return cleanContent(strictMatch[1]);
	}

	// Try self-closing tag
	const selfClosingRegex = new RegExp(`<${tagName}\\s*/?>`, 'i');
	if (selfClosingRegex.test(xmlString)) {
		return ''; // Tag exists but is empty
	}

	// Try loose match (content between opening tag and next opening tag or end)
	const looseRegex = new RegExp(`<${tagName}[^>]*>([\\s\\S]*?)(?=<[a-z_]+|$)`, 'i');
	const looseMatch = xmlString.match(looseRegex);

	if (looseMatch && looseMatch[1]) {
		return cleanContent(looseMatch[1]);
	}

	return undefined;
}

/**
 * Clean extracted content (trim, decode entities, normalize whitespace)
 */
function cleanContent(content: string): string {
	return content
		.trim()
		// Decode common HTML entities
		.replace(/&lt;/g, '<')
		.replace(/&gt;/g, '>')
		.replace(/&amp;/g, '&')
		.replace(/&quot;/g, '"')
		.replace(/&#39;/g, "'")
		// Normalize whitespace (but preserve line breaks)
		.replace(/[ \t]+/g, ' ')
		// Remove excessive line breaks (more than 2)
		.replace(/\n{3,}/g, '\n\n');
}

/**
 * Convert synthesis sections to markdown for better readability
 */
export function synthesisToMarkdown(sections: SynthesisSection): string {
	const parts: string[] = [];

	if (sections.executive_summary) {
		parts.push(`## Executive Summary\n\n${sections.executive_summary}`);
	}

	if (sections.recommendation) {
		parts.push(`## Recommendation\n\n${sections.recommendation}`);
	}

	if (sections.rationale) {
		parts.push(`## Rationale\n\n${sections.rationale}`);
	}

	if (sections.implementation_considerations) {
		parts.push(`## Implementation Considerations\n\n${sections.implementation_considerations}`);
	}

	if (sections.confidence_assessment) {
		parts.push(`## Confidence Assessment\n\n${sections.confidence_assessment}`);
	}

	if (sections.risks_and_mitigations) {
		parts.push(`## Risks & Mitigations\n\n${sections.risks_and_mitigations}`);
	}

	if (sections.success_metrics) {
		parts.push(`## Success Metrics\n\n${sections.success_metrics}`);
	}

	if (sections.timeline) {
		parts.push(`## Timeline\n\n${sections.timeline}`);
	}

	if (sections.resources_required) {
		parts.push(`## Resources Required\n\n${sections.resources_required}`);
	}

	if (sections.open_questions) {
		parts.push(`## Open Questions\n\n${sections.open_questions}`);
	}

	if (sections.vote_breakdown) {
		parts.push(`## Vote Breakdown\n\n${sections.vote_breakdown}`);
	}

	return parts.join('\n\n---\n\n');
}

/**
 * Check if content appears to be XML-formatted
 */
export function isXMLFormatted(content: string): boolean {
	// Check for XML tags
	return /<[a-z_]+[^>]*>[\s\S]*<\/[a-z_]+>/i.test(content);
}

/**
 * Sanitize HTML to prevent XSS attacks
 * This is a basic implementation - consider using DOMPurify in production
 */
export function sanitizeHTML(html: string): string {
	// Remove script tags
	html = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');

	// Remove event handlers
	html = html.replace(/\s*on\w+\s*=\s*["'][^"']*["']/gi, '');
	html = html.replace(/\s*on\w+\s*=\s*[^\s>]*/gi, '');

	// Remove javascript: protocol
	html = html.replace(/javascript:/gi, '');

	return html;
}
