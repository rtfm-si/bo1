/**
 * JSON-LD Structured Data Utilities
 * Creates schema.org markup for SEO rich snippets
 */

import type { PublicBlogPost, PublicDecision } from '$lib/api/types';

const SITE_URL = 'https://boardof.one';
const ORG_NAME = 'Board of One';
const ORG_DESCRIPTION =
	'A management operating system for founders making real calls. Compress management work, delay management hires, get senior-team leverage without senior-team overhead.';

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
 * Create BreadcrumbList JSON-LD schema for a blog post
 */
export function createBlogBreadcrumbSchema(post: PublicBlogPost): BreadcrumbSchema {
	return {
		'@context': 'https://schema.org',
		'@type': 'BreadcrumbList',
		itemListElement: [
			{ '@type': 'ListItem', position: 1, name: 'Home', item: SITE_URL },
			{ '@type': 'ListItem', position: 2, name: 'Blog', item: `${SITE_URL}/blog` },
			{ '@type': 'ListItem', position: 3, name: post.title, item: `${SITE_URL}/blog/${post.slug}` }
		]
	};
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
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function serializeJsonLd(schema: any): string {
	return JSON.stringify(schema);
}

// =============================================================================
// Decision Schema Types and Functions
// =============================================================================

interface FAQPageSchema {
	'@context': 'https://schema.org';
	'@type': 'FAQPage';
	mainEntity: Array<{
		'@type': 'Question';
		name: string;
		acceptedAnswer: {
			'@type': 'Answer';
			text: string;
		};
	}>;
}

interface BreadcrumbSchema {
	'@context': 'https://schema.org';
	'@type': 'BreadcrumbList';
	itemListElement: Array<{
		'@type': 'ListItem';
		position: number;
		name: string;
		item: string;
	}>;
}

interface DecisionArticleSchema {
	'@context': 'https://schema.org';
	'@type': 'Article';
	headline: string;
	description: string;
	datePublished?: string;
	author: Organization;
	publisher: Organization;
	mainEntityOfPage: {
		'@type': 'WebPage';
		'@id': string;
	};
}

/**
 * Create Article JSON-LD schema for a decision page
 */
export function createDecisionArticleSchema(
	decision: PublicDecision,
	category: string
): DecisionArticleSchema {
	const canonicalUrl = `${SITE_URL}/decisions/${category}/${decision.slug}`;
	const description = decision.meta_description || decision.title;

	const schema: DecisionArticleSchema = {
		'@context': 'https://schema.org',
		'@type': 'Article',
		headline: decision.title,
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

	if (decision.published_at) {
		schema.datePublished = decision.published_at;
	}

	return schema;
}

/**
 * Create FAQPage JSON-LD schema from decision FAQs
 */
export function createDecisionFAQSchema(
	decision: PublicDecision
): FAQPageSchema | null {
	if (!decision.faqs || decision.faqs.length === 0) {
		return null;
	}

	return {
		'@context': 'https://schema.org',
		'@type': 'FAQPage',
		mainEntity: decision.faqs.map((faq) => ({
			'@type': 'Question',
			name: faq.question,
			acceptedAnswer: {
				'@type': 'Answer',
				text: faq.answer
			}
		}))
	};
}

/**
 * Create BreadcrumbList JSON-LD schema for a decision category page
 */
export function createDecisionCategoryBreadcrumbSchema(category: string): BreadcrumbSchema {
	const categoryTitle = category.charAt(0).toUpperCase() + category.slice(1);
	return {
		'@context': 'https://schema.org',
		'@type': 'BreadcrumbList',
		itemListElement: [
			{ '@type': 'ListItem', position: 1, name: 'Home', item: SITE_URL },
			{ '@type': 'ListItem', position: 2, name: 'Decisions', item: `${SITE_URL}/decisions` },
			{ '@type': 'ListItem', position: 3, name: categoryTitle, item: `${SITE_URL}/decisions/${category}` }
		]
	};
}

/**
 * Create BreadcrumbList JSON-LD schema for a decision page
 */
export function createDecisionBreadcrumbSchema(
	decision: PublicDecision,
	category: string
): BreadcrumbSchema {
	const categoryTitle = category.charAt(0).toUpperCase() + category.slice(1);

	return {
		'@context': 'https://schema.org',
		'@type': 'BreadcrumbList',
		itemListElement: [
			{
				'@type': 'ListItem',
				position: 1,
				name: 'Home',
				item: SITE_URL
			},
			{
				'@type': 'ListItem',
				position: 2,
				name: 'Decisions',
				item: `${SITE_URL}/decisions`
			},
			{
				'@type': 'ListItem',
				position: 3,
				name: categoryTitle,
				item: `${SITE_URL}/decisions/${category}`
			},
			{
				'@type': 'ListItem',
				position: 4,
				name: decision.title,
				item: `${SITE_URL}/decisions/${category}/${decision.slug}`
			}
		]
	};
}

// =============================================================================
// Homepage Schema Types and Functions
// =============================================================================

interface OrganizationSchema {
	'@context': 'https://schema.org';
	'@type': 'Organization';
	name: string;
	url: string;
	description: string;
	logo?: string;
	sameAs?: string[];
}

interface SoftwareApplicationSchema {
	'@context': 'https://schema.org';
	'@type': 'SoftwareApplication';
	name: string;
	description: string;
	url: string;
	applicationCategory: string;
	operatingSystem: string;
	offers: {
		'@type': 'Offer';
		price: string;
		priceCurrency: string;
	};
}

interface HomepageFAQSchema {
	'@context': 'https://schema.org';
	'@type': 'FAQPage';
	mainEntity: Array<{
		'@type': 'Question';
		name: string;
		acceptedAnswer: {
			'@type': 'Answer';
			text: string;
		};
	}>;
}

/**
 * Create Organization JSON-LD schema for homepage
 */
export function createOrganizationSchema(): OrganizationSchema {
	return {
		'@context': 'https://schema.org',
		'@type': 'Organization',
		name: ORG_NAME,
		url: SITE_URL,
		description: ORG_DESCRIPTION,
		logo: `${SITE_URL}/logo.png`
	};
}

/**
 * Create SoftwareApplication JSON-LD schema for homepage
 */
export function createSoftwareApplicationSchema(): SoftwareApplicationSchema {
	return {
		'@context': 'https://schema.org',
		'@type': 'SoftwareApplication',
		name: ORG_NAME,
		description: ORG_DESCRIPTION,
		url: SITE_URL,
		applicationCategory: 'BusinessApplication',
		operatingSystem: 'Web',
		offers: {
			'@type': 'Offer',
			price: '0',
			priceCurrency: 'GBP'
		}
	};
}

/**
 * Create FAQPage JSON-LD schema for homepage FAQs
 */
export function createHomepageFAQSchema(
	faqs: Array<{ question: string; answer: string }>
): HomepageFAQSchema {
	return {
		'@context': 'https://schema.org',
		'@type': 'FAQPage',
		mainEntity: faqs.map((faq) => ({
			'@type': 'Question',
			name: faq.question,
			acceptedAnswer: {
				'@type': 'Answer',
				text: faq.answer
			}
		}))
	};
}

// =============================================================================
// HowTo Schema for Decisions
// =============================================================================

interface HowToSchema {
	'@context': 'https://schema.org';
	'@type': 'HowTo';
	name: string;
	description: string;
	step: Array<{
		'@type': 'HowToStep';
		position: number;
		name: string;
		text: string;
	}>;
}

/**
 * Create HowTo JSON-LD schema for a decision page
 * Returns null if no expert perspectives exist
 */
export function createDecisionHowToSchema(decision: PublicDecision): HowToSchema | null {
	if (!decision.expert_perspectives?.length) return null;

	return {
		'@context': 'https://schema.org',
		'@type': 'HowTo',
		name: `How to decide: ${decision.title}`,
		description: decision.meta_description || decision.title,
		step: decision.expert_perspectives.map((ep, i) => ({
			'@type': 'HowToStep',
			position: i + 1,
			name: `${ep.persona_name}'s Perspective`,
			text: ep.quote
		}))
	};
}
