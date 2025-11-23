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
}

export class SSEClient {
	private url: string;
	private options: SSEClientOptions;
	private abortController: AbortController | null = null;
	private reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
	private closed = false;

	constructor(url: string, options: SSEClientOptions = {}) {
		this.url = url;
		this.options = options;
	}

	async connect(): Promise<void> {
		this.closed = false;
		this.abortController = new AbortController();

		try {
			const response = await fetch(this.url, {
				method: 'GET',
				headers: {
					'Accept': 'text/event-stream',
					'Cache-Control': 'no-cache',
				},
				credentials: 'include', // CRITICAL: Send cookies
				signal: this.abortController.signal,
			});

			if (!response.ok) {
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

		for (const line of lines) {
			if (line.startsWith('event: ')) {
				eventType = line.slice(7).trim();
			} else if (line.startsWith('data: ')) {
				data += line.slice(6);
			}
		}

		if (data) {
			const messageEvent = new MessageEvent(eventType, { data });

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

	private cleanup(): void {
		if (this.reader) {
			this.reader.cancel().catch(() => {
				// Ignore cancellation errors
			});
			this.reader = null;
		}

		if (this.abortController) {
			this.abortController.abort();
			this.abortController = null;
		}
	}
}
