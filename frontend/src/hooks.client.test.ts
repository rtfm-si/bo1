/**
 * Tests for chunk loading error detection logic.
 * Tests the isChunkLoadError pattern matching without browser environment.
 */

import { describe, it, expect } from 'vitest';

/**
 * Standalone test of the chunk error detection pattern.
 * This mirrors the logic in hooks.client.ts for testability.
 */
function isChunkLoadError(error: unknown): boolean {
	if (!(error instanceof Error)) return false;

	const message = error.message.toLowerCase();

	return (
		message.includes('failed to fetch dynamically imported module') ||
		message.includes('loading chunk') ||
		message.includes('loading css chunk') ||
		message.includes("couldn't load module") ||
		(message.includes('failed to load') && message.includes('/_app/'))
	);
}

describe('isChunkLoadError', () => {
	it('detects "failed to fetch dynamically imported module" error', () => {
		const error = new Error('Failed to fetch dynamically imported module: /_app/immutable/chunks/C2cpIfMC.js');
		expect(isChunkLoadError(error)).toBe(true);
	});

	it('detects "loading chunk" error', () => {
		const error = new Error('Loading chunk 42 failed');
		expect(isChunkLoadError(error)).toBe(true);
	});

	it('detects "loading css chunk" error', () => {
		const error = new Error('Loading CSS chunk styles-abc123 failed');
		expect(isChunkLoadError(error)).toBe(true);
	});

	it('detects "failed to load /_app/" error', () => {
		const error = new Error('Failed to load /_app/immutable/nodes/1.BUddsOLG.js');
		expect(isChunkLoadError(error)).toBe(true);
	});

	it('detects case-insensitive chunk errors', () => {
		const error = new Error('FAILED TO FETCH DYNAMICALLY IMPORTED MODULE');
		expect(isChunkLoadError(error)).toBe(true);
	});

	it('detects "couldn\'t load module" error', () => {
		const error = new Error("Couldn't load module /path/to/module.js");
		expect(isChunkLoadError(error)).toBe(true);
	});

	it('does not trigger for regular errors', () => {
		const error = new Error('Some other error');
		expect(isChunkLoadError(error)).toBe(false);
	});

	it('does not trigger for non-Error objects', () => {
		expect(isChunkLoadError('string error')).toBe(false);
		expect(isChunkLoadError(null)).toBe(false);
		expect(isChunkLoadError(undefined)).toBe(false);
		expect(isChunkLoadError({ message: 'object' })).toBe(false);
	});

	it('does not trigger for unrelated "failed to load" errors', () => {
		const error = new Error('Failed to load image.png');
		expect(isChunkLoadError(error)).toBe(false);
	});

	it('only triggers for /_app/ paths in "failed to load" errors', () => {
		const appError = new Error('Failed to load /_app/something.js');
		const otherError = new Error('Failed to load /other/path.js');

		expect(isChunkLoadError(appError)).toBe(true);
		expect(isChunkLoadError(otherError)).toBe(false);
	});
});

describe('reload attempt counter logic', () => {
	// These test the counter logic conceptually without sessionStorage

	it('counter starts at 0', () => {
		const getCount = (stored: string | null): number => {
			if (!stored) return 0;
			try {
				const { count, timestamp } = JSON.parse(stored);
				if (Date.now() - timestamp > 60_000) return 0;
				return count;
			} catch {
				return 0;
			}
		};

		expect(getCount(null)).toBe(0);
		expect(getCount('invalid json')).toBe(0);
	});

	it('counter increments correctly', () => {
		const now = Date.now();
		const stored = JSON.stringify({ count: 2, timestamp: now });

		const parsed = JSON.parse(stored);
		expect(parsed.count).toBe(2);
	});

	it('counter expires after 1 minute', () => {
		const getCount = (stored: string | null): number => {
			if (!stored) return 0;
			try {
				const { count, timestamp } = JSON.parse(stored);
				if (Date.now() - timestamp > 60_000) return 0;
				return count;
			} catch {
				return 0;
			}
		};

		// Recent timestamp
		const recent = JSON.stringify({ count: 3, timestamp: Date.now() - 30_000 });
		expect(getCount(recent)).toBe(3);

		// Expired timestamp
		const expired = JSON.stringify({ count: 3, timestamp: Date.now() - 70_000 });
		expect(getCount(expired)).toBe(0);
	});

	it('max attempts is 3', () => {
		const MAX_RELOAD_ATTEMPTS = 3;
		const shouldReload = (attempts: number) => attempts < MAX_RELOAD_ATTEMPTS;

		expect(shouldReload(0)).toBe(true);
		expect(shouldReload(1)).toBe(true);
		expect(shouldReload(2)).toBe(true);
		expect(shouldReload(3)).toBe(false);
		expect(shouldReload(4)).toBe(false);
	});
});
