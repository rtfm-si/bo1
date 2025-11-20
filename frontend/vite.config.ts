import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
	plugins: [sveltekit(), tailwindcss()],
	server: {
		port: 5173,
		strictPort: false,
		host: true
		// Note: API proxying is handled by hooks.server.ts, not Vite proxy
		// This allows proper SSR support and Docker networking
	}
});
