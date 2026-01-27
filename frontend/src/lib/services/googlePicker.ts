/**
 * Google Picker Service
 * Handles Google Drive file picker for data file selection
 * Supports: Google Sheets, Excel (XLSX/XLS), CSV, TSV, TXT
 * Uses drive.file scope (no Google verification required)
 */

import { env } from '$env/dynamic/public';

const DRIVE_FILE_SCOPE = 'https://www.googleapis.com/auth/drive.file';

// Supported MIME types for data import
const SUPPORTED_MIME_TYPES = [
	'application/vnd.google-apps.spreadsheet', // Google Sheets
	'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // XLSX
	'application/vnd.ms-excel', // XLS
	'text/csv', // CSV
	'text/plain', // TXT
	'text/tab-separated-values' // TSV
].join(',');

// Script URLs
const GAPI_SCRIPT = 'https://apis.google.com/js/api.js';
const GSI_SCRIPT = 'https://accounts.google.com/gsi/client';

let gapiLoaded = false;
let gsiLoaded = false;
let pickerApiLoaded = false;

/**
 * Load a script dynamically
 */
function loadScript(src: string): Promise<void> {
	return new Promise((resolve, reject) => {
		// Check if already loaded
		if (document.querySelector(`script[src="${src}"]`)) {
			resolve();
			return;
		}

		const script = document.createElement('script');
		script.src = src;
		script.async = true;
		script.defer = true;
		script.onload = () => resolve();
		script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
		document.head.appendChild(script);
	});
}

/**
 * Load Google APIs (gapi and gsi)
 */
export async function loadGoogleApis(): Promise<void> {
	if (gapiLoaded && gsiLoaded && pickerApiLoaded) {
		return;
	}

	// Load both scripts in parallel
	await Promise.all([
		loadScript(GAPI_SCRIPT).then(() => {
			gapiLoaded = true;
		}),
		loadScript(GSI_SCRIPT).then(() => {
			gsiLoaded = true;
		})
	]);

	// Load the picker API
	await new Promise<void>((resolve, reject) => {
		window.gapi?.load('picker', () => {
			pickerApiLoaded = true;
			resolve();
		});
		// Add timeout fallback
		setTimeout(() => reject(new Error('Failed to load Google Picker API')), 10000);
	});
}

/**
 * Get OAuth access token via Google Identity Services
 * Prompts user consent if needed
 */
export function getAccessToken(): Promise<string> {
	return new Promise((resolve, reject) => {
		const clientId = env.PUBLIC_GOOGLE_CLIENT_ID;
		if (!clientId) {
			reject(new Error('Google Client ID not configured'));
			return;
		}

		const tokenClient = window.google?.accounts.oauth2.initTokenClient({
			client_id: clientId,
			scope: DRIVE_FILE_SCOPE,
			callback: (response) => {
				if (response.error) {
					reject(new Error(response.error_description || response.error));
					return;
				}
				resolve(response.access_token);
			},
			error_callback: (error) => {
				reject(new Error(error.message || 'OAuth error'));
			}
		});

		if (!tokenClient) {
			reject(new Error('Failed to initialize token client'));
			return;
		}

		// Request token - will show consent popup if needed
		tokenClient.requestAccessToken({ prompt: '' });
	});
}

/**
 * Selected file from Google Picker
 */
export interface PickedFile {
	id: string;
	name: string;
	url: string;
	mimeType: string;
}

/**
 * Open Google Picker to select a data file
 * Supports Google Sheets, Excel, CSV, TSV, and text files
 * Returns selected file info or null if cancelled
 */
export async function openPicker(): Promise<PickedFile | null> {
	// Ensure APIs are loaded
	await loadGoogleApis();

	// Get access token (will prompt consent if needed)
	const accessToken = await getAccessToken();

	const apiKey = env.PUBLIC_GOOGLE_API_KEY;
	if (!apiKey) {
		throw new Error('Google API Key not configured');
	}

	return new Promise((resolve, reject) => {
		try {
			// Create view for spreadsheets and data files
			const view = new window.google!.picker.DocsView(window.google!.picker.ViewId.DOCS);
			view.setMimeTypes(SUPPORTED_MIME_TYPES);
			view.setMode(window.google!.picker.DocsViewMode.LIST);

			// Build picker
			const picker = new window.google!.picker.PickerBuilder()
				.addView(view)
				.setOAuthToken(accessToken)
				.setDeveloperKey(apiKey)
				.setTitle('Select a spreadsheet or data file')
				.setMaxItems(1)
				.enableFeature(window.google!.picker.Feature.SUPPORT_DRIVES)
				.setCallback((data) => {
					if (data.action === window.google!.picker.Action.PICKED && data.docs?.length) {
						const doc = data.docs[0];
						resolve({
							id: doc.id,
							name: doc.name,
							url: doc.url,
							mimeType: doc.mimeType
						});
					} else if (data.action === window.google!.picker.Action.CANCEL) {
						resolve(null);
					}
				})
				.build();

			picker.setVisible(true);
		} catch (error) {
			reject(error instanceof Error ? error : new Error('Failed to open picker'));
		}
	});
}

/**
 * Extract spreadsheet ID from a Google Sheets URL
 */
export function extractSpreadsheetId(url: string): string | null {
	const match = url.match(/\/spreadsheets\/d\/([a-zA-Z0-9_-]+)/);
	return match ? match[1] : null;
}
