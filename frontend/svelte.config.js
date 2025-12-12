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

		// Content Security Policy with nonce-based script loading
		// SvelteKit auto-generates nonces for inline scripts and styles
		csp: {
			mode: 'auto',
			directives: {
				'default-src': ['self'],
				'script-src': dev ? ['self', 'unsafe-inline'] : ['self'],
				'style-src': ['self', 'unsafe-inline'],
				'img-src': ['self', 'data:', 'https:'],
				'font-src': ['self', 'data:'],
				'connect-src': dev
					? ['self', 'https:', 'wss:', 'http://localhost:*', 'ws://localhost:*']
					: ['self', 'https:', 'wss:'],
				'frame-ancestors': ['none'],
				'base-uri': ['self'],
				'form-action': ['self'],
				'report-uri': ['/api/v1/csp-report']
			}
		}
	}
};

export default config;
