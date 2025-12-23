/**
 * Blog Content Sanitization Tests
 *
 * Tests the renderContent function and verifies XSS vectors would be sanitized.
 * The actual DOMPurify sanitization is tested via integration - these tests
 * verify the markdown-to-HTML rendering logic and document expected XSS protections.
 *
 * To run: npm run test
 */

import { describe, it, expect, vi } from 'vitest';

/**
 * Replicates the renderContent function from blog/[slug]/+page.svelte
 */
function renderContent(content: string | undefined): string {
	if (!content) return '';
	return content
		.split('\n\n')
		.map((para) => {
			if (para.startsWith('### ')) {
				return `<h3 class="text-xl font-bold mt-8 mb-4 text-neutral-900 dark:text-neutral-100">${para.slice(4)}</h3>`;
			}
			if (para.startsWith('## ')) {
				return `<h2 class="text-2xl font-bold mt-10 mb-4 text-neutral-900 dark:text-neutral-100">${para.slice(3)}</h2>`;
			}
			if (para.startsWith('# ')) {
				return `<h1 class="text-3xl font-bold mt-12 mb-6 text-neutral-900 dark:text-neutral-100">${para.slice(2)}</h1>`;
			}
			if (para.match(/^[-*] /m)) {
				const items = para.split('\n').map((line) => {
					if (line.match(/^[-*] /)) {
						return `<li class="ml-4">${line.slice(2)}</li>`;
					}
					return line;
				});
				return `<ul class="list-disc list-inside my-4 space-y-2 text-neutral-700 dark:text-neutral-300">${items.join('')}</ul>`;
			}
			return `<p class="my-4 text-neutral-700 dark:text-neutral-300 leading-relaxed">${para}</p>`;
		})
		.join('');
}

/**
 * Mock DOMPurify.sanitize that simulates XSS stripping
 * This allows testing without browser environment
 */
function mockSanitize(html: string): string {
	// Simulate what DOMPurify does - strip dangerous content
	return html
		// Remove script tags and contents
		.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
		// Remove event handlers
		.replace(/\s*on\w+\s*=\s*"[^"]*"/gi, '')
		.replace(/\s*on\w+\s*=\s*'[^']*'/gi, '')
		// Remove javascript: URLs
		.replace(/href\s*=\s*"javascript:[^"]*"/gi, '')
		.replace(/src\s*=\s*"javascript:[^"]*"/gi, '')
		// Remove data: URLs in src
		.replace(/src\s*=\s*"data:[^"]*"/gi, 'src=""')
		// Remove style tags
		.replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '')
		// Remove iframe with javascript
		.replace(/<iframe[^>]*src\s*=\s*"javascript:[^"]*"[^>]*><\/iframe>/gi, '');
}

function sanitizedRender(content: string | undefined): string {
	return mockSanitize(renderContent(content));
}

describe('Blog Content Rendering', () => {
	describe('renderContent - markdown to HTML conversion', () => {
		it('converts H1 headers', () => {
			const result = renderContent('# Main Heading');
			expect(result).toContain('<h1');
			expect(result).toContain('Main Heading');
			expect(result).toContain('class=');
		});

		it('converts H2 headers', () => {
			const result = renderContent('## Second Heading');
			expect(result).toContain('<h2');
			expect(result).toContain('Second Heading');
		});

		it('converts H3 headers', () => {
			const result = renderContent('### Third Heading');
			expect(result).toContain('<h3');
			expect(result).toContain('Third Heading');
		});

		it('converts paragraphs', () => {
			const content = `First paragraph.

Second paragraph.`;
			const result = renderContent(content);
			expect(result).toContain('<p');
			expect(result).toContain('First paragraph');
			expect(result).toContain('Second paragraph');
		});

		it('converts unordered lists with dash', () => {
			const content = `- Item one
- Item two`;
			const result = renderContent(content);
			expect(result).toContain('<ul');
			expect(result).toContain('<li');
			expect(result).toContain('Item one');
			expect(result).toContain('Item two');
		});

		it('converts unordered lists with asterisk', () => {
			const content = `* First
* Second`;
			const result = renderContent(content);
			expect(result).toContain('<ul');
			expect(result).toContain('<li');
		});

		it('handles empty content', () => {
			expect(renderContent('')).toBe('');
			expect(renderContent(undefined)).toBe('');
		});

		it('wraps plain text in paragraph', () => {
			const result = renderContent('Plain text content');
			expect(result).toContain('<p');
			expect(result).toContain('Plain text content');
		});
	});

	describe('XSS vector documentation (what DOMPurify strips)', () => {
		it('documents that script tags are stripped', () => {
			const malicious = `<script>alert('xss')</script>`;
			const result = sanitizedRender(malicious);
			expect(result).not.toContain('<script');
			expect(result).not.toContain('alert');
		});

		it('documents that script tags with src are stripped', () => {
			const malicious = `<script src="https://evil.com/xss.js"></script>`;
			const result = sanitizedRender(malicious);
			expect(result).not.toContain('<script');
			expect(result).not.toContain('evil.com');
		});

		it('documents that onerror handlers are stripped', () => {
			const malicious = `<img src="x" onerror="alert('xss')">`;
			const result = sanitizedRender(malicious);
			expect(result).not.toContain('onerror');
		});

		it('documents that onclick handlers are stripped', () => {
			const malicious = `<button onclick="alert('xss')">Click</button>`;
			const result = sanitizedRender(malicious);
			expect(result).not.toContain('onclick');
		});

		it('documents that javascript: URLs in href are stripped', () => {
			const malicious = `<a href="javascript:alert('xss')">Click</a>`;
			const result = sanitizedRender(malicious);
			expect(result).not.toContain('javascript:');
		});

		it('documents that style tags are stripped', () => {
			const malicious = `<style>body { background: url("javascript:alert()"); }</style>`;
			const result = sanitizedRender(malicious);
			expect(result).not.toContain('<style');
		});
	});

	describe('Safe content preservation', () => {
		it('preserves class attributes', () => {
			const result = renderContent('# Heading');
			expect(result).toContain('class="text-3xl');
		});

		it('preserves safe anchor tags from content', () => {
			const content = `Check <a href="https://example.com">this</a>`;
			const result = sanitizedRender(content);
			expect(result).toContain('href="https://example.com"');
		});

		it('preserves text content after XSS removal', () => {
			const content = `Safe text <script>bad</script> more safe text`;
			const result = sanitizedRender(content);
			expect(result).toContain('Safe text');
			expect(result).toContain('more safe text');
		});
	});

	describe('XSS vectors in markdown context', () => {
		it('strips XSS in list items', () => {
			const content = `- <span onclick="alert('xss')">Item</span>
- Normal item`;
			const result = sanitizedRender(content);
			expect(result).not.toContain('onclick');
			expect(result).toContain('Item');
			expect(result).toContain('Normal item');
		});

		it('strips XSS in headings', () => {
			const content = `# Title <script>alert('xss')</script>`;
			const result = sanitizedRender(content);
			expect(result).toContain('<h1');
			expect(result).toContain('Title');
			expect(result).not.toContain('<script');
		});

		it('handles mixed content', () => {
			const content = `# Welcome

This has <script>evil()</script> in it.

## More Info

- Safe item
- <img onerror="xss"> item`;
			const result = sanitizedRender(content);
			expect(result).toContain('Welcome');
			expect(result).toContain('More Info');
			expect(result).toContain('Safe item');
			expect(result).not.toContain('<script');
			expect(result).not.toContain('onerror');
		});
	});
});
