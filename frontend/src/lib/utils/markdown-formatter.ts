/**
 * Markdown Formatter Utilities
 *
 * Utilities for parsing and converting markdown to HTML.
 * Extracted from pdf-report-generator.ts for reusability.
 */

/**
 * Convert markdown-style formatting to HTML.
 *
 * Supports:
 * - Headers (h2, h3, h4)
 * - Bold and italic text
 * - Numbered and bullet lists
 * - Paragraphs
 *
 * @param text - Markdown text to convert
 * @returns HTML string
 */
export function formatMarkdownToHtml(text: string): string {
	if (!text) return '';

	return (
		text
			// Headers
			.replace(/^### (.+)$/gm, '<h4>$1</h4>')
			.replace(/^## (.+)$/gm, '<h3>$1</h3>')
			.replace(/^# (.+)$/gm, '<h2>$1</h2>')
			// Bold
			.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
			// Italic
			.replace(/\*([^*]+)\*/g, '<em>$1</em>')
			// Numbered lists with bold labels (e.g., "1. **Label:** text")
			.replace(/^\d+\.\s+\*\*([^:*]+):\*\*\s*(.+)$/gm, '<li><strong>$1:</strong> $2</li>')
			// Regular numbered lists
			.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>')
			// Bullet lists
			.replace(/^[-•]\s+(.+)$/gm, '<li>$1</li>')
			// Wrap consecutive li elements in ul
			.replace(/((?:<li>[\s\S]*?<\/li>\s*)+)/g, '<ul>$1</ul>')
			// Paragraphs (double newlines)
			.replace(/\n\n+/g, '</p><p>')
			// Single newlines within paragraphs
			.replace(/\n/g, '<br>')
			// Wrap in paragraph if not already structured
			.replace(/^(?!<[hup])/, '<p>')
			.replace(/(?<![>])$/, '</p>')
	);
}

/**
 * Extract a section from markdown text by header name.
 *
 * Looks for markdown headers (## or #) matching the given section names
 * and extracts the content until the next header or end of text.
 *
 * @param text - Full markdown text
 * @param sectionNames - Array of possible section names to match (case-insensitive)
 * @returns Extracted section content or empty string if not found
 *
 * @example
 * const text = "## Summary\nThis is the summary.\n## Details\nMore details.";
 * extractMarkdownSection(text, ['Summary', 'Overview']); // "This is the summary."
 */
export function extractMarkdownSection(text: string, sectionNames: string[]): string {
	if (!text) return '';

	// Try each section name variant
	for (const name of sectionNames) {
		// Match ## or # followed by section name, capture content until next ## or --- or end
		const pattern = new RegExp(`##?\\s*${name}\\s*\\n+([\\s\\S]*?)(?=\\n##|\\n---(?:\\n|$)|$)`, 'i');
		const match = text.match(pattern);
		if (match) {
			return match[1].trim();
		}
	}

	return '';
}

/**
 * Parse a synthesis document and extract all known sections.
 *
 * Sections: The Bottom Line, Why This Matters, What To Do Next, Key Risks, Board Confidence
 *
 * @param synthesis - Full synthesis markdown text
 * @returns Object with all extracted sections
 */
export interface ParsedAction {
	title: string;
	description: string;
	rationale?: string;
	priority?: string;
	timeline?: string;
	success_metrics?: string[];
	risks?: string[];
}

export interface SynthesisSections {
	bottomLine: string;
	whyItMatters: string;
	nextSteps: string;
	keyRisks: string;
	confidence: string;
	recommendation: string;
	executiveSummary: string;
	recommendedActions?: ParsedAction[];
	considerations?: string[];
}

/**
 * Extract a JSON object substring from text that may have trailing markdown.
 * Uses delimiter detection and brace-counting fallback.
 */
function extractJsonSubstring(text: string): string | null {
	// Try splitting on markdown horizontal rule delimiter
	const delimiterIdx = text.indexOf('\n\n---');
	if (delimiterIdx > 0) {
		const candidate = text.substring(0, delimiterIdx).trim();
		if (candidate.startsWith('{') && candidate.endsWith('}')) return candidate;
	}

	// Brace-counting fallback: find matching closing brace
	let depth = 0;
	let inString = false;
	let escape = false;
	for (let i = 0; i < text.length; i++) {
		const ch = text[i];
		if (escape) { escape = false; continue; }
		if (ch === '\\' && inString) { escape = true; continue; }
		if (ch === '"') { inString = !inString; continue; }
		if (inString) continue;
		if (ch === '{') depth++;
		else if (ch === '}') { depth--; if (depth === 0) return text.substring(0, i + 1); }
	}
	return null;
}

/**
 * Try to parse synthesis as JSON and map fields to SynthesisSections.
 * Returns null if the text is not valid JSON.
 */
function parseJsonSynthesis(text: string): SynthesisSections | null {
	const trimmed = text.trim();
	if (!trimmed.startsWith('{')) return null;

	let json: Record<string, unknown>;
	try {
		json = JSON.parse(trimmed);
	} catch {
		// Synthesis may have markdown footer appended: {JSON}\n\n---\n\n## ...
		// Try extracting JSON substring before the footer
		const jsonStr = extractJsonSubstring(trimmed);
		if (!jsonStr) return null;
		try {
			json = JSON.parse(jsonStr);
		} catch {
			return null;
		}
	}

	const str = (key: string): string => {
		const v = json[key];
		return typeof v === 'string' ? v : '';
	};

	// Map recommended_actions array
	const rawActions = Array.isArray(json.recommended_actions) ? json.recommended_actions : [];
	const recommendedActions: ParsedAction[] = rawActions.map((a: Record<string, unknown>) => ({
		title: (a.action as string) || (a.title as string) || '',
		description: (a.description as string) || (a.rationale as string) || '',
		rationale: (a.rationale as string) || '',
		priority: (a.priority as string) || 'medium',
		timeline: (a.timeline as string) || '',
		success_metrics: Array.isArray(a.success_metrics) ? a.success_metrics : [],
		risks: Array.isArray(a.risks) ? a.risks : []
	}));

	// Map implementation_considerations
	const rawConsiderations = Array.isArray(json.implementation_considerations)
		? json.implementation_considerations
		: [];
	const considerations: string[] = rawConsiderations.map((c: unknown) =>
		typeof c === 'string' ? c : typeof c === 'object' && c !== null ? (c as Record<string, string>).consideration || JSON.stringify(c) : String(c)
	);

	const bottomLine = str('unified_recommendation');
	const executiveSummary = str('synthesis_summary') || bottomLine;
	const whyItMatters = str('synthesis_summary');

	// Build nextSteps from high-priority actions
	const highActions = recommendedActions.filter((a) => a.priority === 'high' || a.priority === 'critical');
	const nextSteps = highActions.length > 0
		? highActions.map((a, i) => `${i + 1}. **${a.title}** — ${a.description}`).join('\n')
		: recommendedActions.slice(0, 3).map((a, i) => `${i + 1}. **${a.title}** — ${a.description}`).join('\n');

	// Build keyRisks from action risks
	const allRisks = recommendedActions.flatMap((a) => a.risks || []);
	const keyRisks = allRisks.length > 0
		? allRisks.slice(0, 5).map((r) => `- ${r}`).join('\n')
		: '';

	return {
		bottomLine,
		whyItMatters,
		nextSteps,
		keyRisks,
		confidence: '',
		recommendation: bottomLine,
		executiveSummary,
		recommendedActions,
		considerations
	};
}

export function parseSynthesisSections(synthesis: string): SynthesisSections {
	// Try JSON parse first
	const jsonResult = parseJsonSynthesis(synthesis);
	if (jsonResult) return jsonResult;

	const getSection = (names: string[]) => extractMarkdownSection(synthesis, names);

	// Extract all sections
	const bottomLine = getSection(['The Bottom Line']);
	const whyItMatters = getSection(['Why This Matters', 'Why It Matters']);
	const nextSteps = getSection(['What To Do Next']);
	const keyRisks = getSection(['Key Risks']);
	const confidence = getSection(['Board Confidence']);

	const executiveSummary = bottomLine || '';
	const recommendation = nextSteps;

	return {
		bottomLine,
		whyItMatters,
		nextSteps,
		keyRisks,
		confidence,
		recommendation,
		executiveSummary
	};
}

/**
 * Truncate text to a maximum length, adding ellipsis if needed.
 *
 * @param text - Text to truncate
 * @param maxLength - Maximum length
 * @returns Truncated text with ellipsis if needed
 */
export function truncateText(text: string, maxLength: number): string {
	if (!text || text.length <= maxLength) return text;
	return text.substring(0, maxLength - 3) + '...';
}
