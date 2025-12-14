import { describe, it, expect, vi, beforeEach } from 'vitest';
import { dataUrlToBlob, canShareFiles } from './canvas-export';

// Note: exportElementAsImage and downloadImage require DOM/canvas APIs
// which are difficult to test in Node environment. These tests cover
// the utility functions that can be tested without full DOM.

describe('dataUrlToBlob', () => {
	beforeEach(() => {
		vi.stubGlobal('fetch', vi.fn());
	});

	it('converts data URL to blob', async () => {
		const mockBlob = new Blob(['test'], { type: 'image/png' });
		const mockResponse = { blob: () => Promise.resolve(mockBlob) };
		vi.mocked(fetch).mockResolvedValue(mockResponse as Response);

		const dataUrl = 'data:image/png;base64,iVBORw0KGgo=';
		const blob = await dataUrlToBlob(dataUrl);

		expect(fetch).toHaveBeenCalledWith(dataUrl);
		expect(blob).toBe(mockBlob);
	});
});

describe('canShareFiles', () => {
	beforeEach(() => {
		// Reset navigator mock
		vi.stubGlobal('navigator', {});
	});

	it('returns false when navigator.share is not available', () => {
		vi.stubGlobal('navigator', {});
		expect(canShareFiles()).toBe(false);
	});

	it('returns false when only share is available', () => {
		vi.stubGlobal('navigator', {
			share: vi.fn()
		});
		expect(canShareFiles()).toBe(false);
	});

	it('returns true when share and canShare are available', () => {
		vi.stubGlobal('navigator', {
			share: vi.fn(),
			canShare: vi.fn()
		});
		expect(canShareFiles()).toBe(true);
	});
});
