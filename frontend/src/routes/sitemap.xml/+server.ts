import type { RequestHandler } from './$types';

const SITE_URL = 'https://boardof.one';
const INTERNAL_API_URL = process.env.INTERNAL_API_URL || 'http://api:8000';

export const GET: RequestHandler = async () => {
	// Static pages
	const staticPages = [
		{ url: '/', priority: 1.0, changefreq: 'weekly' },
		{ url: '/blog', priority: 0.9, changefreq: 'daily' },
		{ url: '/decisions', priority: 0.9, changefreq: 'weekly' },
		{ url: '/features', priority: 0.8, changefreq: 'monthly' },
		{ url: '/pricing', priority: 0.8, changefreq: 'monthly' },
		{ url: '/about', priority: 0.7, changefreq: 'monthly' },
		{ url: '/waitlist', priority: 0.6, changefreq: 'monthly' },
		{ url: '/legal/privacy', priority: 0.3, changefreq: 'yearly' },
		{ url: '/legal/terms', priority: 0.3, changefreq: 'yearly' },
		{ url: '/legal/cookies', priority: 0.3, changefreq: 'yearly' }
	];

	// Feature sub-pages (SEO-optimized content pages)
	const featurePages = [
		{ url: '/features/data-analysis', priority: 0.7, changefreq: 'monthly' },
		{ url: '/features/mentor-chat', priority: 0.7, changefreq: 'monthly' },
		{ url: '/features/seo-generation', priority: 0.7, changefreq: 'monthly' },
		{ url: '/features/tailored-to-you', priority: 0.7, changefreq: 'monthly' },
		{ url: '/features/competitor-analysis', priority: 0.7, changefreq: 'monthly' },
		{ url: '/features/project-management', priority: 0.7, changefreq: 'monthly' },
		{ url: '/features/decisions-replanning', priority: 0.7, changefreq: 'monthly' }
	];

	// Use case pages (SEO-optimized content pages)
	const useCasePages = [
		{ url: '/use-cases', priority: 0.8, changefreq: 'monthly' },
		{ url: '/use-cases/delay-management-hires', priority: 0.6, changefreq: 'monthly' },
		{ url: '/use-cases/founder-bottleneck', priority: 0.6, changefreq: 'monthly' },
		{ url: '/use-cases/operating-without-org', priority: 0.6, changefreq: 'monthly' },
		{ url: '/use-cases/strategic-decisions', priority: 0.6, changefreq: 'monthly' },
		{ url: '/use-cases/advisor-alternative', priority: 0.6, changefreq: 'monthly' }
	];

	// Comparison pages (SEO-optimized content pages)
	const comparePages = [
		{ url: '/compare', priority: 0.8, changefreq: 'monthly' },
		{ url: '/compare/board-of-one-vs-coaching', priority: 0.6, changefreq: 'monthly' },
		{ url: '/compare/board-of-one-vs-advisory-board', priority: 0.6, changefreq: 'monthly' },
		{ url: '/compare/board-of-one-vs-chatgpt', priority: 0.6, changefreq: 'monthly' },
		{ url: '/compare/board-of-one-vs-consultants', priority: 0.6, changefreq: 'monthly' },
		{ url: '/compare/board-of-one-vs-masterminds', priority: 0.6, changefreq: 'monthly' }
	];

	// Fetch published blog posts - use internal API URL for server-side
	let blogPosts: Array<{ slug: string; published_at?: string; updated_at?: string }> = [];
	try {
		const url = `${INTERNAL_API_URL}/api/v1/blog/posts?limit=50`;
		console.log('Sitemap: fetching blog posts from', url);
		const response = await fetch(url);
		console.log('Sitemap: response status', response.status);
		if (response.ok) {
			const data = await response.json();
			blogPosts = data.posts || [];
			console.log('Sitemap: found', blogPosts.length, 'blog posts');
		} else {
			console.error('Sitemap: API returned', response.status, response.statusText);
		}
	} catch (e) {
		console.error('Sitemap: Failed to fetch blog posts:', e);
	}

	// Fetch published decisions
	let decisions: Array<{ category: string; slug: string; published_at?: string; updated_at?: string }> = [];
	try {
		const url = `${INTERNAL_API_URL}/api/v1/decisions?limit=100`;
		console.log('Sitemap: fetching decisions from', url);
		const response = await fetch(url);
		console.log('Sitemap: decisions response status', response.status);
		if (response.ok) {
			const data = await response.json();
			decisions = data.decisions || [];
			console.log('Sitemap: found', decisions.length, 'decisions');
		} else {
			console.error('Sitemap: decisions API returned', response.status, response.statusText);
		}
	} catch (e) {
		console.error('Sitemap: Failed to fetch decisions:', e);
	}

	// Get unique decision categories
	const decisionCategories = [...new Set(decisions.map((d) => d.category))];

	// Build XML
	const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${staticPages
	.map(
		(page) => `  <url>
    <loc>${SITE_URL}${page.url}</loc>
    <changefreq>${page.changefreq}</changefreq>
    <priority>${page.priority}</priority>
  </url>`
	)
	.join('\n')}
${featurePages
	.map(
		(page) => `  <url>
    <loc>${SITE_URL}${page.url}</loc>
    <changefreq>${page.changefreq}</changefreq>
    <priority>${page.priority}</priority>
  </url>`
	)
	.join('\n')}
${useCasePages
	.map(
		(page) => `  <url>
    <loc>${SITE_URL}${page.url}</loc>
    <changefreq>${page.changefreq}</changefreq>
    <priority>${page.priority}</priority>
  </url>`
	)
	.join('\n')}
${comparePages
	.map(
		(page) => `  <url>
    <loc>${SITE_URL}${page.url}</loc>
    <changefreq>${page.changefreq}</changefreq>
    <priority>${page.priority}</priority>
  </url>`
	)
	.join('\n')}
${blogPosts
	.map(
		(post) => `  <url>
    <loc>${SITE_URL}/blog/${post.slug}</loc>
    <lastmod>${post.updated_at || post.published_at || new Date().toISOString()}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>`
	)
	.join('\n')}
${decisionCategories
	.map(
		(category) => `  <url>
    <loc>${SITE_URL}/decisions/${category}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>`
	)
	.join('\n')}
${decisions
	.map(
		(decision) => `  <url>
    <loc>${SITE_URL}/decisions/${decision.category}/${decision.slug}</loc>
    <lastmod>${decision.updated_at || decision.published_at || new Date().toISOString()}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>`
	)
	.join('\n')}
</urlset>`;

	return new Response(xml, {
		headers: {
			'Content-Type': 'application/xml',
			'Cache-Control': 'max-age=3600'
		}
	});
};
