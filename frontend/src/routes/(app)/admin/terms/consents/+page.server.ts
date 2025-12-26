import { env } from '$env/dynamic/private';
import type { PageServerLoad } from './$types';

interface ConsentAuditItem {
	user_id: string;
	email: string | null;
	terms_version: string;
	consented_at: string;
	ip_address: string | null;
}

interface ConsentAuditResponse {
	items: ConsentAuditItem[];
	total: number;
	limit: number;
	offset: number;
	has_more: boolean;
	next_offset: number | null;
	period: string;
}

export const load: PageServerLoad = async ({ url, cookies }) => {
	const period = url.searchParams.get('period') || 'all';
	const limit = parseInt(url.searchParams.get('limit') || '50', 10);
	const offset = parseInt(url.searchParams.get('offset') || '0', 10);

	try {
		const response = await fetch(
			`${env.PRIVATE_API_URL}/api/admin/terms/consents?period=${period}&limit=${limit}&offset=${offset}`,
			{
				headers: {
					Cookie: cookies.get('sAccessToken') ? `sAccessToken=${cookies.get('sAccessToken')}` : ''
				}
			}
		);

		if (!response.ok) {
			console.error('Failed to fetch consent audit:', response.status);
			return {
				consents: [],
				total: 0,
				limit,
				offset,
				hasMore: false,
				period
			};
		}

		const data: ConsentAuditResponse = await response.json();

		return {
			consents: data.items,
			total: data.total,
			limit: data.limit,
			offset: data.offset,
			hasMore: data.has_more,
			period: data.period
		};
	} catch (error) {
		console.error('Error fetching consent audit:', error);
		return {
			consents: [],
			total: 0,
			limit,
			offset,
			hasMore: false,
			period
		};
	}
};
