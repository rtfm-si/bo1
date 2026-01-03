/**
 * Redirect from /context/competitors to /reports/competitors
 * The competitors feature is now part of the Reports section.
 */
import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = () => {
	redirect(301, '/reports/competitors');
};
