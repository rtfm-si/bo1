/**
 * Frontend health check endpoint
 * Used by deployment workflow to verify frontend is serving correctly
 */
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async () => {
	return json({
		status: 'healthy',
		component: 'frontend',
		timestamp: new Date().toISOString(),
		details: {
			framework: 'SvelteKit',
			node_env: process.env.NODE_ENV || 'production'
		}
	});
};
