/**
 * SSE Client - Server-Sent Events Client for Real-time Deliberation Updates
 *
 * Handles EventSource connection to the FastAPI SSE streaming endpoint.
 * Provides type-safe event handling and automatic reconnection.
 */

import { env } from '$env/dynamic/public';

/**
 * SSE Event Types from backend/api/events.py
 */
export type SSEEventType =
	| 'node_start'
	| 'node_end'
	| 'contribution'
	| 'facilitator_decision'
	| 'convergence'
	| 'complete'
	| 'error'
	| 'clarification_requested'
	| 'clarification_answered';

/**
 * Base SSE Event structure
 */
export interface SSEEvent {
	type: SSEEventType;
	data: unknown;
	timestamp: string;
}

/**
 * Specific event data types
 */
export interface NodeStartEvent extends SSEEvent {
	type: 'node_start';
	data: {
		node: string;
		session_id: string;
	};
}

export interface NodeEndEvent extends SSEEvent {
	type: 'node_end';
	data: {
		node: string;
		session_id: string;
		duration_ms: number;
	};
}

export interface ContributionEvent extends SSEEvent {
	type: 'contribution';
	data: {
		persona_code: string;
		persona_name: string;
		content: string;
		round_number: number;
	};
}

export interface FacilitatorDecisionEvent extends SSEEvent {
	type: 'facilitator_decision';
	data: {
		action: 'continue' | 'vote' | 'moderator' | 'research' | 'clarify';
		speaker?: string;
		reasoning?: string;
	};
}

export interface ConvergenceEvent extends SSEEvent {
	type: 'convergence';
	data: {
		convergence_score: number;
		should_stop: boolean;
		stop_reason?: string;
	};
}

export interface CompleteEvent extends SSEEvent {
	type: 'complete';
	data: {
		session_id: string;
		final_cost: number;
		total_rounds: number;
	};
}

export interface ErrorEvent extends SSEEvent {
	type: 'error';
	data: {
		error: string;
		session_id: string;
	};
}

export interface ClarificationRequestedEvent extends SSEEvent {
	type: 'clarification_requested';
	data: {
		question: string;
		reason: string;
		session_id: string;
	};
}

export interface ClarificationAnsweredEvent extends SSEEvent {
	type: 'clarification_answered';
	data: {
		answer: string;
		session_id: string;
	};
}

/**
 * Union type for all possible events
 */
export type AnySSEEvent =
	| NodeStartEvent
	| NodeEndEvent
	| ContributionEvent
	| FacilitatorDecisionEvent
	| ConvergenceEvent
	| CompleteEvent
	| ErrorEvent
	| ClarificationRequestedEvent
	| ClarificationAnsweredEvent;

/**
 * Event handler function type
 */
export type SSEEventHandler = (event: AnySSEEvent) => void;

/**
 * SSE Client options
 */
export interface SSEClientOptions {
	baseUrl?: string;
	reconnect?: boolean;
	reconnectInterval?: number;
	onOpen?: () => void;
	onError?: (error: Event) => void;
	onClose?: () => void;
}

/**
 * SSE Client for Board of One streaming deliberation events
 */
export class SSEClient {
	private baseUrl: string;
	private eventSource: EventSource | null = null;
	private handlers: Map<SSEEventType | '*', SSEEventHandler[]> = new Map();
	private reconnect: boolean;
	private reconnectInterval: number;
	private sessionId: string | null = null;
	private onOpenCallback?: () => void;
	private onErrorCallback?: (error: Event) => void;
	private onCloseCallback?: () => void;

	constructor(options: SSEClientOptions = {}) {
		this.baseUrl = options.baseUrl || env.PUBLIC_API_URL || 'http://localhost:8000';
		this.reconnect = options.reconnect ?? true;
		this.reconnectInterval = options.reconnectInterval ?? 3000;
		this.onOpenCallback = options.onOpen;
		this.onErrorCallback = options.onError;
		this.onCloseCallback = options.onClose;
	}

	/**
	 * Connect to SSE stream for a session
	 */
	connect(sessionId: string): void {
		if (this.eventSource) {
			this.close();
		}

		this.sessionId = sessionId;
		const url = `${this.baseUrl}/api/v1/sessions/${sessionId}/stream`;

		this.eventSource = new EventSource(url);

		// Handle connection open
		this.eventSource.onopen = () => {
			console.log(`[SSE] Connected to session ${sessionId}`);
			this.onOpenCallback?.();
		};

		// Handle messages (default event type)
		this.eventSource.onmessage = (event: MessageEvent) => {
			try {
				const data: AnySSEEvent = JSON.parse(event.data);
				this.handleEvent(data);
			} catch (error) {
				console.error('[SSE] Failed to parse event:', error);
			}
		};

		// Register listeners for named event types
		const eventTypes: SSEEventType[] = [
			'node_start',
			'node_end',
			'contribution',
			'facilitator_decision',
			'convergence',
			'complete',
			'error',
			'clarification_requested',
			'clarification_answered'
		];

		eventTypes.forEach((type) => {
			this.eventSource!.addEventListener(type, (event: Event) => {
				try {
					const messageEvent = event as MessageEvent;
					const parsedData = JSON.parse(messageEvent.data);
					const sseEvent: AnySSEEvent = {
						type,
						data: parsedData,
						timestamp: parsedData.timestamp || new Date().toISOString()
					};
					console.log(`[SSE] Received ${type} event:`, parsedData);
					this.handleEvent(sseEvent);
				} catch (error) {
					console.error(`[SSE] Failed to parse ${type} event:`, error);
				}
			});
		});

		// Handle errors
		this.eventSource.onerror = (error: Event) => {
			console.error('[SSE] Connection error:', error);
			this.onErrorCallback?.(error);

			// Attempt reconnect if enabled
			if (this.reconnect && this.sessionId) {
				console.log(`[SSE] Reconnecting in ${this.reconnectInterval}ms...`);
				setTimeout(() => {
					if (this.sessionId) {
						this.connect(this.sessionId);
					}
				}, this.reconnectInterval);
			}
		};
	}

	/**
	 * Register an event handler
	 * @param eventType - Event type to listen for, or '*' for all events
	 * @param handler - Event handler function
	 */
	on(eventType: SSEEventType | '*', handler: SSEEventHandler): void {
		if (!this.handlers.has(eventType)) {
			this.handlers.set(eventType, []);
		}
		this.handlers.get(eventType)!.push(handler);
	}

	/**
	 * Unregister an event handler
	 */
	off(eventType: SSEEventType | '*', handler: SSEEventHandler): void {
		const handlers = this.handlers.get(eventType);
		if (handlers) {
			const index = handlers.indexOf(handler);
			if (index !== -1) {
				handlers.splice(index, 1);
			}
		}
	}

	/**
	 * Handle incoming event
	 */
	private handleEvent(event: AnySSEEvent): void {
		// Call type-specific handlers
		const typeHandlers = this.handlers.get(event.type);
		if (typeHandlers) {
			typeHandlers.forEach((handler) => handler(event));
		}

		// Call wildcard handlers
		const wildcardHandlers = this.handlers.get('*');
		if (wildcardHandlers) {
			wildcardHandlers.forEach((handler) => handler(event));
		}
	}

	/**
	 * Check if connected
	 */
	isConnected(): boolean {
		return this.eventSource !== null && this.eventSource.readyState === EventSource.OPEN;
	}

	/**
	 * Close connection
	 */
	close(): void {
		if (this.eventSource) {
			this.eventSource.close();
			this.eventSource = null;
			this.sessionId = null;
			console.log('[SSE] Connection closed');
			this.onCloseCallback?.();
		}
	}

	/**
	 * Get current session ID
	 */
	getSessionId(): string | null {
		return this.sessionId;
	}
}

/**
 * Create a new SSE client instance
 */
export function createSSEClient(options?: SSEClientOptions): SSEClient {
	return new SSEClient(options);
}
