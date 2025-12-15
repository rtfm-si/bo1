/**
 * E2E test health check endpoint
 * Verifies that E2E mode is properly configured before running tests.
 * Used by CI to ensure environment variables are loaded correctly.
 */
import { json } from '@sveltejs/kit';

// Note: In SvelteKit/Vite, PUBLIC_* env vars are available via import.meta.env
// but we check both process.env and import.meta.env for compatibility
export async function GET() {
	try {
		// Check both possible sources of PUBLIC_* env vars
		const e2eMode =
			process.env.PUBLIC_E2E_MODE === 'true' ||
			(typeof import.meta !== 'undefined' && import.meta.env?.PUBLIC_E2E_MODE === 'true');

		const apiUrl =
			process.env.PUBLIC_API_URL ||
			(typeof import.meta !== 'undefined' && import.meta.env?.PUBLIC_API_URL) ||
			null;

		return json({
			e2e_mode: e2eMode,
			api_url: apiUrl,
			ready: e2eMode,
			timestamp: new Date().toISOString(),
			debug: {
				process_env: !!process.env.PUBLIC_E2E_MODE,
				node_env: process.env.NODE_ENV
			}
		});
	} catch (error) {
		return json({
			e2e_mode: false,
			error: String(error),
			ready: false,
			timestamp: new Date().toISOString()
		}, { status: 200 }); // Return 200 even on error to not break CI flow
	}
}
