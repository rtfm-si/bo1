/**
 * JSON-LD Structured Data Tests
 *
 * Tests the JSON-LD schema generation functions for SEO rich snippets.
 * Validates schema.org compliance and proper handling of edge cases.
 *
 * To run: npm run test
 */

import { describe, it, expect } from 'vitest';
import { createArticleSchema, createBlogSchema, serializeJsonLd } from './jsonld';
import type { PublicBlogPost } from '$lib/api/types';

describe('JSON-LD Utilities', () => {
	describe('createArticleSchema', () => {
		const basePost: PublicBlogPost = {
			id: '123',
			title: 'Test Article Title',
			slug: 'test-article-title',
			status: 'published',
			created_at: '2025-12-01T10:00:00Z',
			updated_at: '2025-12-15T14:30:00Z'
		};

		it('returns valid Article schema structure', () => {
			const schema = createArticleSchema(basePost);
			expect(schema['@context']).toBe('https://schema.org');
			expect(schema['@type']).toBe('Article');
		});

		it('uses title as headline', () => {
			const schema = createArticleSchema(basePost);
			expect(schema.headline).toBe('Test Article Title');
		});

		it('prefers meta_title over title for headline', () => {
			const post = { ...basePost, meta_title: 'SEO Optimized Title' };
			const schema = createArticleSchema(post);
			expect(schema.headline).toBe('SEO Optimized Title');
		});

		it('uses meta_description for description when available', () => {
			const post = { ...basePost, meta_description: 'SEO description text' };
			const schema = createArticleSchema(post);
			expect(schema.description).toBe('SEO description text');
		});

		it('falls back to excerpt for description', () => {
			const post = { ...basePost, excerpt: 'Short excerpt text' };
			const schema = createArticleSchema(post);
			expect(schema.description).toBe('Short excerpt text');
		});

		it('falls back to title for description when no meta or excerpt', () => {
			const schema = createArticleSchema(basePost);
			expect(schema.description).toBe('Test Article Title');
		});

		it('sets author as Organization', () => {
			const schema = createArticleSchema(basePost);
			expect(schema.author['@type']).toBe('Organization');
			expect(schema.author.name).toBe('Board of One');
		});

		it('sets publisher as Organization with URL', () => {
			const schema = createArticleSchema(basePost);
			expect(schema.publisher['@type']).toBe('Organization');
			expect(schema.publisher.name).toBe('Board of One');
			expect(schema.publisher.url).toBe('https://boardof.one');
		});

		it('sets mainEntityOfPage with canonical URL', () => {
			const schema = createArticleSchema(basePost);
			expect(schema.mainEntityOfPage['@type']).toBe('WebPage');
			expect(schema.mainEntityOfPage['@id']).toBe('https://boardof.one/blog/test-article-title');
		});

		it('sets datePublished when published_at is available', () => {
			const post = { ...basePost, published_at: '2025-12-10T12:00:00Z' };
			const schema = createArticleSchema(post);
			expect(schema.datePublished).toBe('2025-12-10T12:00:00Z');
		});

		it('does not set datePublished when published_at is missing', () => {
			const schema = createArticleSchema(basePost);
			expect(schema.datePublished).toBeUndefined();
		});

		it('sets dateModified from updated_at', () => {
			const post = { ...basePost, published_at: '2025-12-10T12:00:00Z' };
			const schema = createArticleSchema(post);
			expect(schema.dateModified).toBe('2025-12-15T14:30:00Z');
		});

		it('falls back to published_at for dateModified when updated_at is missing', () => {
			const post: PublicBlogPost = {
				id: '123',
				title: 'Test',
				slug: 'test',
				status: 'published',
				published_at: '2025-12-10T12:00:00Z',
				created_at: '2025-12-01T10:00:00Z',
				updated_at: '' // empty string
			};
			// With empty updated_at, falls back to published_at
			const schema = createArticleSchema({ ...post, updated_at: undefined } as any);
			expect(schema.dateModified).toBe('2025-12-10T12:00:00Z');
		});

		it('sets keywords from seo_keywords array', () => {
			const post = { ...basePost, seo_keywords: ['ai', 'decision-making', 'startup'] };
			const schema = createArticleSchema(post);
			expect(schema.keywords).toBe('ai, decision-making, startup');
		});

		it('does not set keywords when seo_keywords is empty', () => {
			const post = { ...basePost, seo_keywords: [] };
			const schema = createArticleSchema(post);
			expect(schema.keywords).toBeUndefined();
		});

		it('does not set keywords when seo_keywords is missing', () => {
			const schema = createArticleSchema(basePost);
			expect(schema.keywords).toBeUndefined();
		});
	});

	describe('createBlogSchema', () => {
		it('returns valid Blog schema structure', () => {
			const schema = createBlogSchema();
			expect(schema['@context']).toBe('https://schema.org');
			expect(schema['@type']).toBe('Blog');
		});

		it('sets correct blog name', () => {
			const schema = createBlogSchema();
			expect(schema.name).toBe('Board of One Blog');
		});

		it('sets description', () => {
			const schema = createBlogSchema();
			expect(schema.description).toContain('decision-making');
			expect(schema.description).toContain('startup strategy');
		});

		it('sets correct blog URL', () => {
			const schema = createBlogSchema();
			expect(schema.url).toBe('https://boardof.one/blog');
		});

		it('sets publisher as Organization', () => {
			const schema = createBlogSchema();
			expect(schema.publisher['@type']).toBe('Organization');
			expect(schema.publisher.name).toBe('Board of One');
			expect(schema.publisher.url).toBe('https://boardof.one');
		});
	});

	describe('serializeJsonLd', () => {
		it('serializes article schema to valid JSON string', () => {
			const post: PublicBlogPost = {
				id: '1',
				title: 'Test',
				slug: 'test',
				status: 'published',
				created_at: '2025-01-01T00:00:00Z',
				updated_at: '2025-01-01T00:00:00Z'
			};
			const schema = createArticleSchema(post);
			const json = serializeJsonLd(schema);
			expect(() => JSON.parse(json)).not.toThrow();
		});

		it('serializes blog schema to valid JSON string', () => {
			const schema = createBlogSchema();
			const json = serializeJsonLd(schema);
			expect(() => JSON.parse(json)).not.toThrow();
		});

		it('handles special characters in title safely', () => {
			const post: PublicBlogPost = {
				id: '1',
				title: 'Test <script>alert("xss")</script>',
				slug: 'test',
				status: 'published',
				created_at: '2025-01-01T00:00:00Z',
				updated_at: '2025-01-01T00:00:00Z'
			};
			const schema = createArticleSchema(post);
			const json = serializeJsonLd(schema);
			// JSON.stringify produces valid JSON - the JSON-LD is safely contained
			// in a <script type="application/ld+json"> which browsers don't execute
			expect(() => JSON.parse(json)).not.toThrow();
			const parsed = JSON.parse(json);
			expect(parsed.headline).toBe('Test <script>alert("xss")</script>');
		});

		it('handles unicode characters in content', () => {
			const post: PublicBlogPost = {
				id: '1',
				title: 'Test with emoji: \u{1F600} and special chars: \u00E9\u00E8',
				slug: 'test-unicode',
				status: 'published',
				created_at: '2025-01-01T00:00:00Z',
				updated_at: '2025-01-01T00:00:00Z'
			};
			const schema = createArticleSchema(post);
			const json = serializeJsonLd(schema);
			const parsed = JSON.parse(json);
			expect(parsed.headline).toContain('\u{1F600}');
		});

		it('handles quotes in content', () => {
			const post: PublicBlogPost = {
				id: '1',
				title: 'Test "with quotes" and \'apostrophes\'',
				slug: 'test-quotes',
				status: 'published',
				created_at: '2025-01-01T00:00:00Z',
				updated_at: '2025-01-01T00:00:00Z'
			};
			const schema = createArticleSchema(post);
			const json = serializeJsonLd(schema);
			expect(() => JSON.parse(json)).not.toThrow();
			const parsed = JSON.parse(json);
			expect(parsed.headline).toBe('Test "with quotes" and \'apostrophes\'');
		});
	});
});
