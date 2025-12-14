import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

// Redirect /pricing to homepage until pricing content is finalized
export const load: PageServerLoad = async () => {
	throw redirect(302, '/');
};
