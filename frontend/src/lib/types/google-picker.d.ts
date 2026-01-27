/**
 * Google Picker API TypeScript Declarations
 * For use with drive.file scope and spreadsheet selection
 */

declare namespace google.picker {
	class PickerBuilder {
		constructor();
		addView(view: DocsView | DocsUploadView): PickerBuilder;
		setOAuthToken(token: string): PickerBuilder;
		setDeveloperKey(key: string): PickerBuilder;
		setCallback(callback: (data: PickerResponse) => void): PickerBuilder;
		setTitle(title: string): PickerBuilder;
		setLocale(locale: string): PickerBuilder;
		enableFeature(feature: Feature): PickerBuilder;
		disableFeature(feature: Feature): PickerBuilder;
		setOrigin(origin: string): PickerBuilder;
		setMaxItems(max: number): PickerBuilder;
		build(): Picker;
	}

	class Picker {
		setVisible(visible: boolean): void;
		dispose(): void;
	}

	class DocsView {
		constructor(viewId?: ViewId);
		setIncludeFolders(include: boolean): DocsView;
		setSelectFolderEnabled(enabled: boolean): DocsView;
		setMimeTypes(mimeTypes: string): DocsView;
		setQuery(query: string): DocsView;
		setMode(mode: DocsViewMode): DocsView;
		setOwnedByMe(ownedByMe: boolean): DocsView;
		setParent(folderId: string): DocsView;
	}

	class DocsUploadView {
		constructor();
		setIncludeFolders(include: boolean): DocsUploadView;
		setParent(folderId: string): DocsUploadView;
	}

	enum ViewId {
		DOCS = 'DOCS',
		DOCS_IMAGES = 'DOCS_IMAGES',
		DOCS_IMAGES_AND_VIDEOS = 'DOCS_IMAGES_AND_VIDEOS',
		DOCS_VIDEOS = 'DOCS_VIDEOS',
		DOCUMENTS = 'DOCUMENTS',
		DRAWINGS = 'DRAWINGS',
		FOLDERS = 'FOLDERS',
		FORMS = 'FORMS',
		PDFS = 'PDFS',
		PRESENTATIONS = 'PRESENTATIONS',
		SPREADSHEETS = 'SPREADSHEETS'
	}

	enum DocsViewMode {
		GRID = 'GRID',
		LIST = 'LIST'
	}

	enum Feature {
		MINE_ONLY = 'MINE_ONLY',
		MULTISELECT_ENABLED = 'MULTISELECT_ENABLED',
		NAV_HIDDEN = 'NAV_HIDDEN',
		SIMPLE_UPLOAD_ENABLED = 'SIMPLE_UPLOAD_ENABLED',
		SUPPORT_DRIVES = 'SUPPORT_DRIVES'
	}

	enum Action {
		CANCEL = 'cancel',
		PICKED = 'picked'
	}

	interface PickerResponse {
		action: Action | string;
		docs?: PickerDocument[];
	}

	interface PickerDocument {
		id: string;
		name: string;
		url: string;
		mimeType: string;
		iconUrl?: string;
		description?: string;
		type?: string;
		lastEditedUtc?: number;
		sizeBytes?: number;
		parentId?: string;
		serviceId?: string;
	}
}

declare namespace gapi {
	function load(api: string, callback: () => void): void;

	namespace client {
		function init(config: {
			apiKey?: string;
			clientId?: string;
			discoveryDocs?: string[];
			scope?: string;
		}): Promise<void>;

		function setToken(token: { access_token: string } | null): void;
		function getToken(): { access_token: string } | null;
	}
}

declare namespace google.accounts.oauth2 {
	interface TokenClient {
		requestAccessToken(config?: { prompt?: string }): void;
		callback: (response: TokenResponse) => void;
	}

	interface TokenResponse {
		access_token: string;
		expires_in: number;
		scope: string;
		token_type: string;
		error?: string;
		error_description?: string;
	}

	function initTokenClient(config: {
		client_id: string;
		scope: string;
		callback: (response: TokenResponse) => void;
		error_callback?: (error: { type: string; message: string }) => void;
		prompt?: string;
	}): TokenClient;
}

interface Window {
	google?: typeof google;
	gapi?: typeof gapi;
}
