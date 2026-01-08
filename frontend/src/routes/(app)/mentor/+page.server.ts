import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

/**
 * Redirect /mentor to appropriate /advisor/* page based on tab query param.
 * Preserves backwards compatibility with old URLs.
 */
export const load: PageServerLoad = ({ url }) => {
	const tab = url.searchParams.get('tab');
	const message = url.searchParams.get('message');
	const persona = url.searchParams.get('persona');

	// Handle Google Sheets callback params - redirect to analyze
	const sheetsConnected = url.searchParams.get('sheets_connected');
	const sheetsError = url.searchParams.get('sheets_error');
	if (sheetsConnected || sheetsError) {
		const params = new URLSearchParams();
		if (sheetsConnected) params.set('sheets_connected', sheetsConnected);
		if (sheetsError) params.set('sheets_error', sheetsError);
		throw redirect(301, `/advisor/analyze?${params.toString()}`);
	}

	// Redirect based on tab param
	if (tab === 'data') {
		throw redirect(301, '/advisor/analyze');
	}
	if (tab === 'seo') {
		throw redirect(301, '/advisor/grow');
	}

	// Default: redirect to discuss (chat)
	// Preserve message and persona params if present
	const params = new URLSearchParams();
	if (message) params.set('message', message);
	if (persona) params.set('persona', persona);
	const queryString = params.toString();
	throw redirect(301, `/advisor/discuss${queryString ? `?${queryString}` : ''}`);
};
