/**
 * E2E test health check endpoint
 * Verifies that E2E mode is properly configured before running tests.
 * Used by CI to ensure environment variables are loaded correctly.
 */
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async () => {
	// Use process.env directly in server endpoint (matches /api/health pattern)
	const e2eMode = process.env.PUBLIC_E2E_MODE === 'true';

	return json({
		e2e_mode: e2eMode,
		api_url: process.env.PUBLIC_API_URL || null,
		ready: e2eMode,
		timestamp: new Date().toISOString()
	});
};
