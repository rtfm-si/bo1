import { env } from '$env/dynamic/private';
import type { PageServerLoad } from './$types';

interface TermsVersionItem {
	id: string;
	version: string;
	content: string;
	is_active: boolean;
	published_at: string | null;
	created_at: string;
}

interface TermsVersionListResponse {
	items: TermsVersionItem[];
	total: number;
	limit: number;
	offset: number;
	has_more: boolean;
	next_offset: number | null;
}

export const load: PageServerLoad = async ({ url, cookies }) => {
	const limit = parseInt(url.searchParams.get('limit') || '50', 10);
	const offset = parseInt(url.searchParams.get('offset') || '0', 10);

	try {
		const response = await fetch(
			`${env.PRIVATE_API_URL}/api/admin/terms/versions?limit=${limit}&offset=${offset}`,
			{
				headers: {
					Cookie: cookies.get('sAccessToken') ? `sAccessToken=${cookies.get('sAccessToken')}` : ''
				}
			}
		);

		if (!response.ok) {
			console.error('Failed to fetch terms versions:', response.status);
			return {
				versions: [],
				total: 0,
				limit,
				offset,
				hasMore: false
			};
		}

		const data: TermsVersionListResponse = await response.json();

		return {
			versions: data.items,
			total: data.total,
			limit: data.limit,
			offset: data.offset,
			hasMore: data.has_more
		};
	} catch (error) {
		console.error('Error fetching terms versions:', error);
		return {
			versions: [],
			total: 0,
			limit,
			offset,
			hasMore: false
		};
	}
};
