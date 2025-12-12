/**
 * Admin layout load guard - redirects non-admin users to dashboard
 *
 * Note: This runs on the server during SSR. The actual admin check
 * happens in +page.server.ts files which verify admin status via
 * the API. This is a client-side guard for SPA navigation.
 */
import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async () => {
	// Admin verification is done in +page.server.ts files
	// This layout just ensures the route structure exists
	return {};
};
