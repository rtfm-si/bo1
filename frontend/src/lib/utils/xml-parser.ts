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
}

/**
 * Parse synthesis XML output into structured sections
 */
export function parseSynthesisXML(xmlString: string): SynthesisSection {
	const sections: SynthesisSection = {};

	// Try to extract each known section
	const sectionNames = [
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
	] as const;

	for (const sectionName of sectionNames) {
		const content = extractXMLSection(xmlString, sectionName);
		if (content) {
			sections[sectionName] = content;
		}
	}

	// Fallback: Try unified_recommendation for meta-synthesis (maps to recommendation)
	if (!sections.recommendation) {
		const unifiedRec = extractXMLSection(xmlString, 'unified_recommendation');
		if (unifiedRec) {
			sections.recommendation = unifiedRec;
		}
	}

	// Fallback: Try unified_action_plan for meta-synthesis (maps to implementation_considerations)
	if (!sections.implementation_considerations) {
		const actionPlan = extractXMLSection(xmlString, 'unified_action_plan');
		if (actionPlan) {
			sections.implementation_considerations = actionPlan;
		}
	}

	// Fallback: Try integrated_risk_assessment for meta-synthesis (maps to risks_and_mitigations)
	if (!sections.risks_and_mitigations) {
		const riskAssessment = extractXMLSection(xmlString, 'integrated_risk_assessment');
		if (riskAssessment) {
			sections.risks_and_mitigations = riskAssessment;
		}
	}

	// If no sections were extracted, return the raw content as executive_summary
	if (Object.keys(sections).length === 0) {
		sections.executive_summary = xmlString.trim();
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
