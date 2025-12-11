/**
 * XML Parser Unit Tests
 *
 * Tests JSON extraction for meta-synthesis with trailing markdown footer.
 * To run: npm run test
 */

import { describe, it, expect } from 'vitest';
import { isJSONFormatted, parseSynthesisXML } from './xml-parser';

describe('xml-parser', () => {
	describe('isJSONFormatted', () => {
		it('detects pure JSON', () => {
			expect(isJSONFormatted('{"key": "value"}')).toBe(true);
		});

		it('detects JSON with trailing markdown footer', () => {
			const content = `{"synthesis_summary": "Test summary", "recommended_actions": []}

---

## Deliberation Summary

- Some footer content`;
			expect(isJSONFormatted(content)).toBe(true);
		});

		it('rejects non-JSON content', () => {
			expect(isJSONFormatted('## The Bottom Line\n\nSome markdown')).toBe(false);
		});

		it('rejects XML content', () => {
			expect(isJSONFormatted('<executive_summary>Test</executive_summary>')).toBe(false);
		});

		it('handles JSON with warning footer', () => {
			const content = `{"problem_statement": "Test"}

---

Warning: This content is AI-generated`;
			expect(isJSONFormatted(content)).toBe(true);
		});
	});

	describe('parseSynthesisXML - JSON meta-synthesis', () => {
		it('parses pure JSON meta-synthesis', () => {
			const json = JSON.stringify({
				problem_statement: 'Should we expand?',
				synthesis_summary: 'The analysis concludes yes.',
				sub_problems_addressed: ['Revenue', 'Operations'],
				recommended_actions: [
					{
						action: 'Hire staff',
						rationale: 'Needed for growth',
						priority: 'high',
						timeline: 'Q1',
						success_metrics: ['Staff count'],
						risks: ['Budget']
					}
				]
			});

			const sections = parseSynthesisXML(json);
			expect(sections.executive_summary).toBe('The analysis concludes yes.');
			expect(sections.recommendation).toContain('Should we expand?');
			expect(sections.recommended_actions).toHaveLength(1);
			expect(sections.recommended_actions![0].action).toBe('Hire staff');
		});

		it('parses JSON with trailing markdown footer', () => {
			const json = {
				problem_statement: 'Market entry',
				synthesis_summary: 'Enter the European market.',
				sub_problems_addressed: [],
				recommended_actions: [
					{
						action: 'Research regulations',
						rationale: 'Compliance required',
						priority: 'critical',
						timeline: 'Month 1',
						success_metrics: ['Compliance checklist'],
						risks: ['Delays']
					}
				]
			};

			const content = `${JSON.stringify(json)}

---

## Deliberation Summary

- **Original problem**: Market entry
- **Sub-problems deliberated**: 2
- **Total cost**: $0.50

Warning: This content is AI-generated for learning purposes only.`;

			const sections = parseSynthesisXML(content);
			expect(sections.executive_summary).toBe('Enter the European market.');
			expect(sections.recommended_actions).toHaveLength(1);
			expect(sections.recommended_actions![0].priority).toBe('critical');
		});

		it('extracts warning from footer', () => {
			const content = `{"synthesis_summary": "Summary"}

---

Warning: This content is AI-generated for learning and knowledge purposes only.`;

			const sections = parseSynthesisXML(content);
			expect(sections.warning).toBeDefined();
			expect(sections.warning).toContain('AI-generated');
		});
	});

	describe('parseSynthesisXML - Markdown format', () => {
		it('parses markdown synthesis', () => {
			const content = `## The Bottom Line

Focus on customer retention first.

## What To Do Next

Implement loyalty program.

## Key Risks

- Budget constraints
- Timeline pressure`;

			const sections = parseSynthesisXML(content);
			expect(sections.executive_summary).toContain('customer retention');
			expect(sections.recommendation).toContain('loyalty program');
			expect(sections.risks_and_mitigations).toContain('Budget constraints');
		});
	});

	describe('parseSynthesisXML - XML format', () => {
		it('parses XML synthesis', () => {
			const content = `<executive_summary>This is the summary.</executive_summary>
<recommendation>Do this action.</recommendation>
<rationale>Because of these reasons.</rationale>`;

			const sections = parseSynthesisXML(content);
			expect(sections.executive_summary).toBe('This is the summary.');
			expect(sections.recommendation).toBe('Do this action.');
			expect(sections.rationale).toBe('Because of these reasons.');
		});
	});

	describe('Edge cases', () => {
		it('handles malformed JSON gracefully', () => {
			const content = `{malformed json here`;
			const sections = parseSynthesisXML(content);
			// Should fall through to treating as plain text
			expect(sections.executive_summary).toBeDefined();
		});

		it('handles empty content', () => {
			const sections = parseSynthesisXML('');
			expect(sections.executive_summary).toBe('');
		});

		it('strips thinking tags', () => {
			const content = `<thinking>Internal reasoning</thinking>

{"synthesis_summary": "Visible content"}`;

			const sections = parseSynthesisXML(content);
			expect(sections.executive_summary).toBe('Visible content');
		});
	});
});
