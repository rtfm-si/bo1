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
	// JSON meta-synthesis fields (stored for direct access)
	recommended_actions?: MetaSynthesisAction[];
	problem_statement?: string;
	sub_problems_addressed?: string[];
}

/**
 * Robustly parse JSON that may have LLM-generated issues.
 * Handles: unescaped control chars, trailing commas, truncated JSON.
 */
export function robustJSONParse<T>(jsonStr: string): T | null {
	// 1. Direct parse attempt
	try {
		return JSON.parse(jsonStr) as T;
	} catch {
		// Continue to repair attempts
	}

	// 2. Fix common LLM JSON issues
	let fixed = jsonStr
		// Replace unescaped control characters in strings
		.replace(/[\x00-\x1f]/g, (char) => {
			if (char === '\n') return '\\n';
			if (char === '\r') return '\\r';
			if (char === '\t') return '\\t';
			return '';
		})
		// Remove trailing commas before } or ]
		.replace(/,\s*([\]}])/g, '$1');

	try {
		return JSON.parse(fixed) as T;
	} catch {
		// Continue to truncation repair
	}

	// 3. Try to repair truncated JSON by closing brackets
	let bracketStack: string[] = [];
	let inString = false;
	let escapeNext = false;

	for (const char of fixed) {
		if (escapeNext) {
			escapeNext = false;
			continue;
		}
		if (char === '\\' && inString) {
			escapeNext = true;
			continue;
		}
		if (char === '"') {
			inString = !inString;
			continue;
		}
		if (!inString) {
			if (char === '{') bracketStack.push('}');
			else if (char === '[') bracketStack.push(']');
			else if (char === '}' || char === ']') bracketStack.pop();
		}
	}

	// Close any unclosed brackets
	if (bracketStack.length > 0) {
		// If in string, close it first
		if (inString) fixed += '"';
		// Close all open brackets in reverse order
		fixed += bracketStack.reverse().join('');
		try {
			return JSON.parse(fixed) as T;
		} catch {
			// Give up
		}
	}

	return null;
}

// JSON meta-synthesis format from backend
export interface MetaSynthesisAction {
	action: string;
	rationale: string;
	priority: string;
	timeline: string;
	success_metrics: string[];
	risks: string[];
}

export interface MetaSynthesisJSON {
	problem_statement: string;
	sub_problems_addressed: string[];
	recommended_actions: MetaSynthesisAction[];
	synthesis_summary: string;
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

// String-only section keys (for markdown parsing - excludes array fields)
type StringSectionKey = Exclude<keyof SynthesisSection, 'recommended_actions' | 'sub_problems_addressed'>;

/**
 * Map common markdown header names to our section keys
 */
const MARKDOWN_TO_SECTION_KEY: Record<string, StringSectionKey> = {
	'executive summary': 'executive_summary',
	'the bottom line': 'executive_summary', // Lean template format
	recommendation: 'recommendation',
	'what to do next': 'recommendation', // Lean template format
	rationale: 'rationale',
	'why this matters': 'rationale', // Lean template format
	'implementation considerations': 'implementation_considerations',
	'confidence assessment': 'confidence_assessment',
	'board confidence': 'confidence_assessment', // Lean template format
	'open questions': 'open_questions',
	'vote breakdown': 'vote_breakdown',
	'risks & mitigations': 'risks_and_mitigations',
	'risks and mitigations': 'risks_and_mitigations',
	'key risks': 'risks_and_mitigations', // Lean template format
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
 * Strip duplicate header text from the beginning of section content.
 * LLMs sometimes repeat the section title as bold/emphasized text.
 * E.g., "## The Bottom Line\n\n**The Bottom Line**\n\nActual content..."
 */
function stripDuplicateHeader(header: string, content: string): string {
	if (!content) return content;

	// Patterns to match the header repeated at the start of content:
	// - **Header** or **Header:**
	// - *Header* or *Header:*
	// - Header (plain text at very start)
	// - ### Header (sub-header)
	const escapedHeader = header.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
	const patterns = [
		new RegExp(`^\\*\\*${escapedHeader}:?\\*\\*\\s*\\n*`, 'i'),
		new RegExp(`^\\*${escapedHeader}:?\\*\\s*\\n*`, 'i'),
		new RegExp(`^###?\\s*${escapedHeader}:?\\s*\\n*`, 'i'),
		new RegExp(`^${escapedHeader}:?\\s*\\n+`, 'i'),
	];

	let cleaned = content;
	for (const pattern of patterns) {
		cleaned = cleaned.replace(pattern, '');
	}

	return cleaned.trim();
}

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
		let sectionContent = content.slice(headerLineEnd + 1, nextIndex).trim();

		// Remove duplicate header text from content (LLM sometimes repeats it)
		sectionContent = stripDuplicateHeader(current.header, sectionContent);

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
 * Check if content appears to be JSON-formatted (meta-synthesis)
 * Handles JSON with trailing markdown footer (e.g., JSON + "---" + footer)
 */
export function isJSONFormatted(content: string): boolean {
	const trimmed = content.trim();
	// Check if starts with { - may have trailing markdown footer
	if (!trimmed.startsWith('{')) return false;
	// Pure JSON ends with }
	if (trimmed.endsWith('}')) return true;
	// JSON + footer pattern: {...}\n\n---
	// Find the last } before any --- delimiter
	const delimiterIndex = trimmed.indexOf('\n\n---');
	if (delimiterIndex > 0) {
		const jsonPart = trimmed.substring(0, delimiterIndex).trim();
		return jsonPart.endsWith('}');
	}
	return false;
}

/**
 * Extract JSON portion from content that may have trailing markdown footer.
 * Uses string-aware brace counting to handle braces inside quoted strings.
 */
function extractJSONFromContent(content: string): string {
	const trimmed = content.trim();

	// Quick check: if pure JSON ending with }, return as-is
	if (trimmed.endsWith('}') && !trimmed.includes('\n\n---')) {
		return trimmed;
	}

	// Look for JSON + footer pattern: {...}\n\n---
	const delimiterIndex = trimmed.indexOf('\n\n---');
	if (delimiterIndex > 0) {
		const candidate = trimmed.substring(0, delimiterIndex).trim();
		// Validate it looks like complete JSON
		if (candidate.startsWith('{') && candidate.endsWith('}')) {
			return candidate;
		}
	}

	// Fallback: string-aware brace counting (handles braces inside strings)
	let braceCount = 0;
	let jsonEnd = -1;
	let inString = false;
	let escapeNext = false;

	for (let i = 0; i < trimmed.length; i++) {
		const char = trimmed[i];

		if (escapeNext) {
			escapeNext = false;
			continue;
		}

		if (char === '\\' && inString) {
			escapeNext = true;
			continue;
		}

		if (char === '"') {
			inString = !inString;
			continue;
		}

		if (!inString) {
			if (char === '{') braceCount++;
			else if (char === '}') {
				braceCount--;
				if (braceCount === 0) {
					jsonEnd = i + 1;
					break;
				}
			}
		}
	}

	return jsonEnd > 0 ? trimmed.substring(0, jsonEnd) : trimmed;
}

/**
 * Parse JSON meta-synthesis format into SynthesisSection
 */
function parseMetaSynthesisJSON(content: string): SynthesisSection {
	const jsonContent = extractJSONFromContent(content);
	const json = robustJSONParse<MetaSynthesisJSON>(jsonContent);
	if (!json) {
		console.warn('[xml-parser] Could not parse meta-synthesis JSON, falling back to text display');
		return {};
	}
	const sections: SynthesisSection = {};

	// Map synthesis_summary to executive_summary
	if (json.synthesis_summary) {
		sections.executive_summary = json.synthesis_summary;
	}

	// Store problem_statement for recommendation context
	if (json.problem_statement) {
		sections.problem_statement = json.problem_statement;
		sections.recommendation = `**Decision:** ${json.problem_statement}`;
	}

	// Store sub_problems_addressed
	if (json.sub_problems_addressed?.length > 0) {
		sections.sub_problems_addressed = json.sub_problems_addressed;
	}

	// Store recommended_actions directly for structured display
	if (json.recommended_actions?.length > 0) {
		sections.recommended_actions = json.recommended_actions;

		// Also format as implementation_considerations for fallback display
		const actionsList = json.recommended_actions.map((action, i) => {
			const parts = [
				`### ${i + 1}. ${action.action.split(':')[0] || 'Action ' + (i + 1)}`,
				'',
				action.action,
				'',
				`**Priority:** ${action.priority}`,
				`**Timeline:** ${action.timeline}`,
				'',
				'**Rationale:**',
				action.rationale,
			];

			if (action.success_metrics?.length > 0) {
				parts.push('', '**Success Metrics:**');
				action.success_metrics.forEach((m) => parts.push(`- ${m}`));
			}

			if (action.risks?.length > 0) {
				parts.push('', '**Risks:**');
				action.risks.forEach((r) => parts.push(`- ${r}`));
			}

			return parts.join('\n');
		});

		sections.implementation_considerations = actionsList.join('\n\n---\n\n');
	}

	return sections;
}

/**
 * Parse synthesis output into structured sections
 * Handles JSON format (meta-synthesis), XML format (<executive_summary>), and Markdown format (## Executive Summary)
 */
export function parseSynthesisXML(xmlString: string): SynthesisSection {
	// First, strip any thinking tags (defense in depth - backend should do this too)
	let cleanedContent = stripThinkingTags(xmlString);

	// Extract warning/disclaimer (will be displayed separately)
	const { content: contentWithoutWarning, warning } = extractWarning(cleanedContent);
	cleanedContent = contentWithoutWarning;

	let sections: SynthesisSection = {};

	// Try JSON parsing first (for meta-synthesis)
	if (isJSONFormatted(cleanedContent)) {
		sections = parseMetaSynthesisJSON(cleanedContent);
		if (Object.keys(sections).length > 0) {
			if (warning) sections.warning = warning;
			return sections;
		}
	}

	// Try XML parsing next
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
