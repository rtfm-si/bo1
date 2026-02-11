/**
 * SSE Events Version Checking Tests
 *
 * Tests for version negotiation utilities:
 * - checkEventVersion()
 * - checkServerVersion()
 * - Version constants
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
	EXPECTED_SSE_VERSION,
	checkEventVersion,
	checkServerVersion,
	type SSEEvent
} from './sse-events';

describe('SSE Version Constants', () => {
	it('EXPECTED_SSE_VERSION should be a positive integer', () => {
		expect(typeof EXPECTED_SSE_VERSION).toBe('number');
		expect(EXPECTED_SSE_VERSION).toBeGreaterThanOrEqual(1);
		expect(Number.isInteger(EXPECTED_SSE_VERSION)).toBe(true);
	});

});

describe('checkEventVersion', () => {
	let warnSpy: ReturnType<typeof vi.spyOn>;
	let infoSpy: ReturnType<typeof vi.spyOn>;

	beforeEach(() => {
		warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
		infoSpy = vi.spyOn(console, 'info').mockImplementation(() => {});
	});

	afterEach(() => {
		warnSpy.mockRestore();
		infoSpy.mockRestore();
	});

	it('returns compatible for matching version', () => {
		const event: SSEEvent = {
			event_type: 'contribution',
			data: { event_version: EXPECTED_SSE_VERSION, persona_code: 'CFO' }
		};

		const result = checkEventVersion(event);

		expect(result.isCompatible).toBe(true);
		expect(result.eventVersion).toBe(EXPECTED_SSE_VERSION);
		expect(result.warning).toBeUndefined();
		expect(warnSpy).not.toHaveBeenCalled();
		expect(infoSpy).not.toHaveBeenCalled();
	});

	it('defaults to expected version when event_version missing', () => {
		const event: SSEEvent = {
			event_type: 'contribution',
			data: { persona_code: 'CFO' } // no event_version
		};

		const result = checkEventVersion(event);

		expect(result.isCompatible).toBe(true);
		expect(result.eventVersion).toBe(EXPECTED_SSE_VERSION);
		expect(result.warning).toBeUndefined();
	});

	it('returns compatible with info log for newer version', () => {
		const event: SSEEvent = {
			event_type: 'contribution',
			data: { event_version: EXPECTED_SSE_VERSION + 1, persona_code: 'CFO' }
		};

		const result = checkEventVersion(event);

		expect(result.isCompatible).toBe(true);
		expect(result.warning).toContain('newer than expected');
		expect(infoSpy).toHaveBeenCalled();
	});

	it('handles null data gracefully', () => {
		const event: SSEEvent = {
			event_type: 'error',
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			data: null as any
		};

		const result = checkEventVersion(event);

		expect(result.isCompatible).toBe(true);
		expect(result.eventVersion).toBe(EXPECTED_SSE_VERSION);
	});

	it('includes correct metadata in result', () => {
		const event: SSEEvent = {
			event_type: 'contribution',
			data: { event_version: EXPECTED_SSE_VERSION }
		};

		const result = checkEventVersion(event);

		expect(result.expectedVersion).toBe(EXPECTED_SSE_VERSION);
	});
});

describe('checkServerVersion', () => {
	let warnSpy: ReturnType<typeof vi.spyOn>;
	let infoSpy: ReturnType<typeof vi.spyOn>;

	beforeEach(() => {
		warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
		infoSpy = vi.spyOn(console, 'info').mockImplementation(() => {});
	});

	afterEach(() => {
		warnSpy.mockRestore();
		infoSpy.mockRestore();
	});

	it('returns compatible for matching version', () => {
		const result = checkServerVersion(String(EXPECTED_SSE_VERSION));

		expect(result.isCompatible).toBe(true);
		expect(result.eventVersion).toBe(EXPECTED_SSE_VERSION);
		expect(result.warning).toBeUndefined();
	});

	it('defaults to expected version for null header', () => {
		const result = checkServerVersion(null);

		expect(result.isCompatible).toBe(true);
		expect(result.eventVersion).toBe(EXPECTED_SSE_VERSION);
	});

	it('returns compatible with info for newer version', () => {
		const result = checkServerVersion(String(EXPECTED_SSE_VERSION + 1));

		expect(result.isCompatible).toBe(true);
		expect(result.warning).toContain('newer than client expected');
		expect(infoSpy).toHaveBeenCalled();
	});

	it('handles invalid header value', () => {
		const result = checkServerVersion('invalid');

		expect(result.warning).toContain('Invalid X-SSE-Schema-Version header');
		expect(warnSpy).toHaveBeenCalled();
	});

	it('handles empty string header by defaulting to expected version', () => {
		const result = checkServerVersion('');

		// Empty string is falsy, so defaults to EXPECTED_SSE_VERSION
		expect(result.isCompatible).toBe(true);
		expect(result.eventVersion).toBe(EXPECTED_SSE_VERSION);
		expect(result.warning).toBeUndefined();
	});

	it('parses valid integer string', () => {
		const result = checkServerVersion('1');

		expect(result.eventVersion).toBe(1);
		expect(result.isCompatible).toBe(true);
	});
});
