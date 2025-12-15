/**
 * Global setup for Playwright E2E tests.
 * Verifies E2E mode is properly configured before running any tests.
 * This prevents silent test skips when auth isn't working.
 */
import { request } from '@playwright/test';

async function globalSetup() {
	const baseURL = process.env.E2E_BASE_URL || 'http://localhost:5173';

	console.log(`\n[E2E Setup] Verifying E2E mode at ${baseURL}...`);

	const context = await request.newContext({ baseURL });

	try {
		// Check E2E health endpoint
		const response = await context.get('/api/e2e-health');

		if (!response.ok()) {
			throw new Error(
				`E2E health endpoint returned ${response.status()}. ` +
					`Ensure frontend is running with PUBLIC_E2E_MODE=true`
			);
		}

		const data = await response.json();

		if (!data.e2e_mode) {
			throw new Error(
				`E2E MODE NOT ACTIVE!\n` +
					`  Expected: PUBLIC_E2E_MODE=true\n` +
					`  Got: ${JSON.stringify(data)}\n\n` +
					`Tests will fail because auth bypass is not working.\n` +
					`Fix: Start frontend with PUBLIC_E2E_MODE=true environment variable.\n` +
					`  Example: PUBLIC_E2E_MODE=true npm run dev`
			);
		}

		console.log(`[E2E Setup] E2E mode verified successfully`);
		console.log(`[E2E Setup] API URL: ${data.api_url || 'not set'}`);
	} catch (error) {
		if (error instanceof Error && error.message.includes('E2E MODE NOT ACTIVE')) {
			throw error;
		}
		// Health endpoint might not exist yet - warn but continue
		console.warn(`[E2E Setup] Warning: Could not verify E2E mode: ${error}`);
		console.warn(`[E2E Setup] Tests may fail if PUBLIC_E2E_MODE is not set`);
	} finally {
		await context.dispose();
	}
}

export default globalSetup;
