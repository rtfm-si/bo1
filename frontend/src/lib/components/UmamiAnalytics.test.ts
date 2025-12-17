/**
 * UmamiAnalytics Component Unit Tests
 *
 * Tests the conditional enablement logic based on environment variables
 */

import { describe, it, expect } from 'vitest';

// Test the core logic extracted from the component
function isUmamiEnabled(umamiHost: string | undefined, websiteId: string | undefined): boolean {
	return !!websiteId && !!umamiHost;
}

function getScriptUrl(umamiHost: string): string {
	return `${umamiHost}/script.js`;
}

describe('UmamiAnalytics', () => {
	describe('isUmamiEnabled', () => {
		it('returns false when website ID is empty', () => {
			expect(isUmamiEnabled('http://localhost:3002', '')).toBe(false);
		});

		it('returns false when website ID is undefined', () => {
			expect(isUmamiEnabled('http://localhost:3002', undefined)).toBe(false);
		});

		it('returns false when host is empty', () => {
			expect(isUmamiEnabled('', 'abc-123')).toBe(false);
		});

		it('returns false when host is undefined', () => {
			expect(isUmamiEnabled(undefined, 'abc-123')).toBe(false);
		});

		it('returns false when both are empty', () => {
			expect(isUmamiEnabled('', '')).toBe(false);
		});

		it('returns true when both are configured', () => {
			expect(isUmamiEnabled('http://localhost:3002', 'test-website-id')).toBe(true);
		});

		it('returns true with production URLs', () => {
			expect(isUmamiEnabled('https://analytics.boardof.one', 'prod-website-id')).toBe(true);
		});
	});

	describe('getScriptUrl', () => {
		it('generates correct script URL for localhost', () => {
			expect(getScriptUrl('http://localhost:3002')).toBe('http://localhost:3002/script.js');
		});

		it('generates correct script URL for production', () => {
			expect(getScriptUrl('https://analytics.boardof.one')).toBe('https://analytics.boardof.one/script.js');
		});

		it('handles trailing slash in host', () => {
			// Note: The component doesn't strip trailing slashes, but this documents expected behavior
			expect(getScriptUrl('http://localhost:3002/')).toBe('http://localhost:3002//script.js');
		});
	});
});
