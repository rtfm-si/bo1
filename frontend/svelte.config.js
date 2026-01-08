import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

const dev = process.env.NODE_ENV !== 'production';

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
			precompress: false
			// NOTE: Do NOT set envPrefix here - it conflicts with runtime env vars
			// The kit.env.publicPrefix setting below is sufficient for $env/dynamic/public
		}),

		// API base URL from environment variable
		env: {
			publicPrefix: 'PUBLIC_'
		},

		// Content Security Policy
		// Note: Production CSP is enforced by nginx, so this is mainly for dev
		// Always allow localhost for local development flexibility
		csp: {
			mode: 'auto',
			directives: {
				'default-src': ['self'],
				'script-src': ['self', 'unsafe-inline', 'https://analytics.boardof.one'],
				'style-src': ['self', 'unsafe-inline'],
				'img-src': ['self', 'data:', 'blob:', 'https:'],
				'font-src': ['self', 'data:'],
				'connect-src': ['self', 'https:', 'wss:', 'http://localhost:*', 'ws://localhost:*'],
				'frame-ancestors': ['none'],
				'base-uri': ['self'],
				'form-action': ['self']
			}
		}
	}
};

export default config;
