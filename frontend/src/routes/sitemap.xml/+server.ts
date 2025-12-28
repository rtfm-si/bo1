import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/public';

const SITE_URL = 'https://boardof.one';

export const GET: RequestHandler = async ({ fetch }) => {
	// Static pages
	const staticPages = [
		{ url: '/', priority: 1.0, changefreq: 'weekly' },
		{ url: '/blog', priority: 0.9, changefreq: 'daily' },
		{ url: '/pricing', priority: 0.8, changefreq: 'monthly' },
		{ url: '/contact', priority: 0.6, changefreq: 'monthly' }
	];

	// Fetch published blog posts
	let blogPosts: Array<{ slug: string; published_at?: string; updated_at?: string }> = [];
	try {
		const apiUrl = env.PUBLIC_API_URL || 'https://boardof.one';
		const response = await fetch(`${apiUrl}/api/v1/blog/posts?limit=100`);
		if (response.ok) {
			const data = await response.json();
			blogPosts = data.posts || [];
		}
	} catch (e) {
		console.error('Failed to fetch blog posts for sitemap:', e);
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
