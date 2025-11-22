import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://svelte.dev/docs/kit/integrations
	// for more information about preprocessors
	preprocess: vitePreprocess(),

	kit: {
		// adapter-node for DigitalOcean deployment
		adapter: adapter({
			// Options passed to adapter
			out: 'build',
			precompress: false,
			envPrefix: 'PUBLIC_' // Allow PUBLIC_ prefixed env vars to be available at runtime
		}),

		// API base URL from environment variable
		env: {
			publicPrefix: 'PUBLIC_'
		}
	}
};

export default config;
