/**
 * JSON-LD Structured Data Utilities
 * Creates schema.org markup for SEO rich snippets
 */

import type { PublicBlogPost } from '$lib/api/types';

const SITE_URL = 'https://boardof.one';
const ORG_NAME = 'Board of One';

interface Organization {
	'@type': 'Organization';
	name: string;
	url?: string;
}

interface ArticleSchema {
	'@context': 'https://schema.org';
	'@type': 'Article';
	headline: string;
	description: string;
	datePublished?: string;
	dateModified?: string;
	author: Organization;
	publisher: Organization;
	mainEntityOfPage: {
		'@type': 'WebPage';
		'@id': string;
	};
	keywords?: string;
}

interface BlogSchema {
	'@context': 'https://schema.org';
	'@type': 'Blog';
	name: string;
	description: string;
	url: string;
	publisher: Organization;
}

/**
 * Create Article JSON-LD schema for a blog post
 */
export function createArticleSchema(post: PublicBlogPost): ArticleSchema {
	const canonicalUrl = `${SITE_URL}/blog/${post.slug}`;
	const description = post.meta_description || post.excerpt || post.title;

	const schema: ArticleSchema = {
		'@context': 'https://schema.org',
		'@type': 'Article',
		headline: post.meta_title || post.title,
		description: description,
		author: {
			'@type': 'Organization',
			name: ORG_NAME
		},
		publisher: {
			'@type': 'Organization',
			name: ORG_NAME,
			url: SITE_URL
		},
		mainEntityOfPage: {
			'@type': 'WebPage',
			'@id': canonicalUrl
		}
	};

	// Add dates if available
	if (post.published_at) {
		schema.datePublished = post.published_at;
	}
	if (post.updated_at) {
		schema.dateModified = post.updated_at;
	} else if (post.published_at) {
		schema.dateModified = post.published_at;
	}

	// Add keywords if available
	if (post.seo_keywords && post.seo_keywords.length > 0) {
		schema.keywords = post.seo_keywords.join(', ');
	}

	return schema;
}

/**
 * Create Blog JSON-LD schema for the blog listing page
 */
export function createBlogSchema(): BlogSchema {
	return {
		'@context': 'https://schema.org',
		'@type': 'Blog',
		name: 'Board of One Blog',
		description:
			'Insights on decision-making, startup strategy, and AI-powered advisory for founders and leaders.',
		url: `${SITE_URL}/blog`,
		publisher: {
			'@type': 'Organization',
			name: ORG_NAME,
			url: SITE_URL
		}
	};
}

/**
 * Serialize JSON-LD schema to a safe string for embedding in HTML
 * Uses JSON.stringify which handles escaping special characters
 */
export function serializeJsonLd(schema: ArticleSchema | BlogSchema): string {
	return JSON.stringify(schema);
}
