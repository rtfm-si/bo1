import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
	plugins: [sveltekit(), tailwindcss()],
	server: {
		port: 5173,
		strictPort: false,
		host: true,
		// Proxy API requests to backend (for client-side browser requests)
		// hooks.server.ts handles server-side SSR requests
		proxy: {
			'/api': {
				target: process.env.INTERNAL_API_URL || 'http://api:8000',
				changeOrigin: true,
				secure: false,
				ws: true, // Enable WebSocket proxying (also helps with SSE)
				// Preserve cookies for authentication
				configure: (proxy, _options) => {
					proxy.on('proxyReq', (proxyReq, req, _res) => {
						// Forward cookies from browser to API
						if (req.headers.cookie) {
							proxyReq.setHeader('Cookie', req.headers.cookie);
						}

						// Log proxied requests for debugging
						console.log(`[Vite Proxy] ${req.method} ${req.url} -> ${proxyReq.path}`);
					});

					proxy.on('proxyRes', (proxyRes, req, _res) => {
						console.log(`[Vite Proxy] Response: ${proxyRes.statusCode} for ${req.url}`);
					});

					proxy.on('error', (err, _req, _res) => {
						console.error('[Vite Proxy] Error:', err.message);
					});
				},
			},
		},
	}
});
