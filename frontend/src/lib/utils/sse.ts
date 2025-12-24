/**
 * Custom SSE client with credentials support
 *
 * Native EventSource doesn't support:
 * - Setting credentials/cookies
 * - Custom headers
 * - Proper error handling
 *
 * This implementation uses fetch() with ReadableStream for proper auth support.
 */

export interface SSEClientOptions {
	onOpen?: () => void;
	onError?: (error: Event | Error) => void;
	onMessage?: (event: MessageEvent) => void;
	/** Map of event types to handlers */
	eventHandlers?: Record<string, (event: MessageEvent) => void>;
	/** Callback when connection appears stalled (no messages for 30s) */
	onStall?: () => void;
	/** Interval in milliseconds to check for stalled connection (default: 30000) */
	stallDetectionInterval?: number;
	/** Initial Last-Event-ID for resume support */
	lastEventId?: string;
}

export class SSEClient {
	private url: string;
	private options: SSEClientOptions;
	private abortController: AbortController | null = null;
	private reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
	private closed = false;
	private lastMessageTime: number = Date.now();
	private stallCheckInterval: NodeJS.Timeout | null = null;
	private hasWarned = false;
	private _lastEventId: string | null = null;

	constructor(url: string, options: SSEClientOptions = {}) {
		this.url = url;
		this.options = options;
		this._lastEventId = options.lastEventId || null;
	}

	/** Get the last event ID received */
	get lastEventId(): string | null {
		return this._lastEventId;
	}

	async connect(): Promise<void> {
		this.closed = false;
		this.abortController = new AbortController();
		this.lastMessageTime = Date.now();
		this.hasWarned = false;

		// Start stall detection if callback provided
		if (this.options.onStall) {
			this.startStallDetection();
		}

		// Build headers with Last-Event-ID for resume support
		const headers: Record<string, string> = {
			'Accept': 'text/event-stream',
			'Cache-Control': 'no-cache',
		};
		if (this._lastEventId) {
			headers['Last-Event-ID'] = this._lastEventId;
		}

		try {
			const response = await fetch(this.url, {
				method: 'GET',
				headers,
				credentials: 'include', // CRITICAL: Send cookies
				signal: this.abortController.signal,
			});

			if (!response.ok) {
				// For 409 responses, parse body to get reason (paused vs failed)
				if (response.status === 409) {
					try {
						const errorBody = await response.json();
						const detail = errorBody.detail || '';
						// Include status info in error for special handling
						const error = new Error(`SSE connection rejected: ${detail}`) as Error & { status?: number; sessionStatus?: string };
						error.status = 409;
						// Detect if session is paused vs other rejection reasons
						if (detail.toLowerCase().includes('paused')) {
							error.sessionStatus = 'paused';
						} else if (detail.toLowerCase().includes('not been started')) {
							error.sessionStatus = 'created';
						}
						throw error;
					} catch (parseErr) {
						if (parseErr instanceof Error && (parseErr as Error & { status?: number }).status === 409) {
							throw parseErr; // Re-throw our structured error
						}
						throw new Error(`SSE connection failed: ${response.status} ${response.statusText}`);
					}
				}
				throw new Error(`SSE connection failed: ${response.status} ${response.statusText}`);
			}

			if (!response.body) {
				throw new Error('SSE response has no body');
			}

			// Connection established
			this.options.onOpen?.();

			// Read the stream
			this.reader = response.body.getReader();
			const decoder = new TextDecoder();
			let buffer = '';

			while (!this.closed) {
				const { done, value } = await this.reader.read();

				if (done) {
					break;
				}

				// Update last message time on any data received
				this.lastMessageTime = Date.now();
				this.hasWarned = false; // Reset warning flag on new data

				// Decode chunk and add to buffer
				buffer += decoder.decode(value, { stream: true });

				// Process complete SSE messages (separated by double newlines)
				const messages = buffer.split('\n\n');

				// Last element might be incomplete, keep in buffer
				buffer = messages.pop() || '';

				for (const message of messages) {
					if (message.trim()) {
						this.processMessage(message);
					}
				}
			}
		} catch (error) {
			if (!this.closed) {
				// Only trigger error if not manually closed
				this.options.onError?.(error instanceof Error ? error : new Error(String(error)));
			}
		} finally {
			this.cleanup();
		}
	}

	private processMessage(message: string): void {
		const lines = message.split('\n');
		let eventType = 'message'; // Default event type
		let data = '';
		let eventId: string | null = null;

		for (const line of lines) {
			if (line.startsWith('id: ')) {
				eventId = line.slice(4).trim();
			} else if (line.startsWith('event: ')) {
				eventType = line.slice(7).trim();
			} else if (line.startsWith('data: ')) {
				data += line.slice(6);
			}
		}

		// Track last event ID for resume support
		if (eventId) {
			this._lastEventId = eventId;
		}

		if (data) {
			const messageEvent = new MessageEvent(eventType, { data, lastEventId: eventId || undefined });

			// Call specific event handler if registered
			const handler = this.options.eventHandlers?.[eventType];
			if (handler) {
				handler(messageEvent);
			}

			// Also call generic onMessage handler
			this.options.onMessage?.(messageEvent);
		}
	}

	close(): void {
		this.closed = true;
		this.cleanup();
	}

	private startStallDetection(): void {
		const intervalMs = this.options.stallDetectionInterval || 30000; // Default 30s

		this.stallCheckInterval = setInterval(() => {
			if (this.closed) {
				return;
			}

			const timeSinceLastMessage = Date.now() - this.lastMessageTime;

			// Warn if no message received in specified interval and not already warned
			if (timeSinceLastMessage >= intervalMs && !this.hasWarned) {
				this.hasWarned = true;
				this.options.onStall?.();
			}
		}, 5000); // Check every 5 seconds
	}

	private stopStallDetection(): void {
		if (this.stallCheckInterval) {
			clearInterval(this.stallCheckInterval);
			this.stallCheckInterval = null;
		}
	}

	private cleanup(): void {
		this.stopStallDetection();

		if (this.reader) {
			this.reader.cancel().catch((error) => {
				// Log but don't throw - cleanup should be resilient
				console.warn('SSE reader cancellation failed:', error);
			});
			this.reader = null;
		}

		if (this.abortController) {
			try {
				this.abortController.abort();
			} catch (error) {
				// Log but don't throw - cleanup should be resilient
				console.warn('SSE abort controller error:', error);
			}
			this.abortController = null;
		}
	}
}
