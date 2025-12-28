import type { RequestHandler } from './$types';

const SITE_URL = 'https://boardof.one';
const INTERNAL_API_URL = process.env.INTERNAL_API_URL || 'http://api:8000';

export const GET: RequestHandler = async () => {
	// Static pages
	const staticPages = [
		{ url: '/', priority: 1.0, changefreq: 'weekly' },
		{ url: '/blog', priority: 0.9, changefreq: 'daily' },
		{ url: '/pricing', priority: 0.8, changefreq: 'monthly' },
		{ url: '/contact', priority: 0.6, changefreq: 'monthly' }
	];

	// Fetch published blog posts - use internal API URL for server-side
	let blogPosts: Array<{ slug: string; published_at?: string; updated_at?: string }> = [];
	try {
		const url = `${INTERNAL_API_URL}/api/v1/blog/posts?limit=100`;
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
</urlset>`;

	return new Response(xml, {
		headers: {
			'Content-Type': 'application/xml',
			'Cache-Control': 'max-age=3600'
		}
	});
};
