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
 * Supports both lean template format and legacy format:
 * - Lean: The Bottom Line, Why This Matters, What To Do Next, Key Risks, Board Confidence
 * - Legacy: Executive Summary, Recommendation, Rationale
 *
 * @param synthesis - Full synthesis markdown text
 * @returns Object with all extracted sections
 */
export interface SynthesisSections {
	bottomLine: string;
	whyItMatters: string;
	nextSteps: string;
	keyRisks: string;
	confidence: string;
	rationale: string;
	recommendation: string;
	executiveSummary: string;
}

export function parseSynthesisSections(synthesis: string): SynthesisSections {
	const getSection = (names: string[]) => extractMarkdownSection(synthesis, names);

	// Extract all sections (supports lean template and legacy format)
	const bottomLine = getSection(['The Bottom Line', 'Executive Summary']);
	const whyItMatters = getSection(['Why This Matters', 'Why It Matters']);
	const nextSteps = getSection(['What To Do Next', 'Next Steps', 'Recommendation']);
	const keyRisks = getSection(['Key Risks', 'Risks']);
	const confidence = getSection(['Board Confidence', 'Confidence Assessment']);
	const rationale = getSection(['Rationale']);

	// For executive summary display, use bottom line or first section
	const executiveSummary = bottomLine || rationale?.substring(0, 500) || '';
	// For recommendation, combine next steps or use legacy recommendation
	const recommendation = nextSteps || getSection(['Recommendation']);

	return {
		bottomLine,
		whyItMatters,
		nextSteps,
		keyRisks,
		confidence,
		rationale,
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
