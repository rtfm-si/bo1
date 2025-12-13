/**
 * Operation Tracker Service
 *
 * Tracks operation timing, failures, and retry patterns for UX observability.
 * Identifies slow operations, failing flows, and repetition patterns.
 */

export interface TrackedOperation {
	id: string;
	name: string;
	startTime: number;
	endTime?: number;
	duration?: number;
	success?: boolean;
	error?: string;
	retryCount: number;
	metadata?: Record<string, unknown>;
}

export interface OperationStats {
	totalOperations: number;
	successCount: number;
	failureCount: number;
	avgDuration: number;
	p50Duration: number;
	p95Duration: number;
	slowOperations: TrackedOperation[];
	failedOperations: TrackedOperation[];
	retryPatterns: { name: string; retryCount: number }[];
}

const SLOW_THRESHOLD_MS = 3000; // 3 seconds
const MAX_BUFFER_SIZE = 100;
const BATCH_FLUSH_INTERVAL_MS = 30000; // 30 seconds

class OperationTracker {
	private operations: Map<string, TrackedOperation> = new Map();
	private completedOperations: TrackedOperation[] = [];
	private retryCounts: Map<string, number> = new Map();
	private flushTimer: ReturnType<typeof setInterval> | null = null;
	private pendingMetrics: TrackedOperation[] = [];

	constructor() {
		// Setup flush on page unload
		if (typeof window !== 'undefined') {
			window.addEventListener('beforeunload', () => this.flush());
			// Start periodic flush
			this.flushTimer = setInterval(() => this.flush(), BATCH_FLUSH_INTERVAL_MS);
		}
	}

	/**
	 * Start tracking an operation
	 */
	startOp(name: string, metadata?: Record<string, unknown>): string {
		const id = `${name}-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
		const retryCount = this.retryCounts.get(name) || 0;

		const operation: TrackedOperation = {
			id,
			name,
			startTime: performance.now(),
			retryCount,
			metadata
		};

		this.operations.set(id, operation);
		return id;
	}

	/**
	 * Mark operation as successfully completed
	 */
	endOp(id: string, metadata?: Record<string, unknown>): TrackedOperation | undefined {
		const op = this.operations.get(id);
		if (!op) return undefined;

		op.endTime = performance.now();
		op.duration = op.endTime - op.startTime;
		op.success = true;
		if (metadata) {
			op.metadata = { ...op.metadata, ...metadata };
		}

		// Reset retry count on success
		this.retryCounts.set(op.name, 0);

		this.completeOperation(op);
		return op;
	}

	/**
	 * Mark operation as failed
	 */
	failOp(id: string, error: string, metadata?: Record<string, unknown>): TrackedOperation | undefined {
		const op = this.operations.get(id);
		if (!op) return undefined;

		op.endTime = performance.now();
		op.duration = op.endTime - op.startTime;
		op.success = false;
		op.error = error;
		if (metadata) {
			op.metadata = { ...op.metadata, ...metadata };
		}

		// Increment retry count for this operation name
		const currentRetry = this.retryCounts.get(op.name) || 0;
		this.retryCounts.set(op.name, currentRetry + 1);
		op.retryCount = currentRetry + 1;

		this.completeOperation(op);
		return op;
	}

	/**
	 * Get operations that exceeded slow threshold
	 */
	getSlowOps(threshold: number = SLOW_THRESHOLD_MS): TrackedOperation[] {
		return this.completedOperations.filter(
			(op) => op.duration && op.duration > threshold
		);
	}

	/**
	 * Get failed operations
	 */
	getFailedOps(): TrackedOperation[] {
		return this.completedOperations.filter((op) => op.success === false);
	}

	/**
	 * Get operations with retry patterns
	 */
	getRetryPatterns(): { name: string; retryCount: number }[] {
		const patterns: { name: string; retryCount: number }[] = [];
		this.retryCounts.forEach((count, name) => {
			if (count > 0) {
				patterns.push({ name, retryCount: count });
			}
		});
		return patterns.sort((a, b) => b.retryCount - a.retryCount);
	}

	/**
	 * Get operation statistics
	 */
	getStats(): OperationStats {
		const completed = this.completedOperations;
		const durations = completed
			.filter((op) => op.duration !== undefined)
			.map((op) => op.duration as number)
			.sort((a, b) => a - b);

		const successCount = completed.filter((op) => op.success).length;
		const failureCount = completed.filter((op) => op.success === false).length;

		return {
			totalOperations: completed.length,
			successCount,
			failureCount,
			avgDuration: durations.length > 0
				? durations.reduce((a, b) => a + b, 0) / durations.length
				: 0,
			p50Duration: durations.length > 0
				? durations[Math.floor(durations.length * 0.5)]
				: 0,
			p95Duration: durations.length > 0
				? durations[Math.min(Math.floor(durations.length * 0.95), durations.length - 1)]
				: 0,
			slowOperations: this.getSlowOps(),
			failedOperations: this.getFailedOps(),
			retryPatterns: this.getRetryPatterns()
		};
	}

	/**
	 * Clear all tracked operations
	 */
	clear(): void {
		this.operations.clear();
		this.completedOperations = [];
		this.retryCounts.clear();
		this.pendingMetrics = [];
	}

	/**
	 * Flush pending metrics to backend
	 */
	async flush(): Promise<void> {
		if (this.pendingMetrics.length === 0) return;

		const metricsToSend = [...this.pendingMetrics];
		this.pendingMetrics = [];

		try {
			// Use sendBeacon for reliability on page unload
			if (typeof navigator !== 'undefined' && navigator.sendBeacon) {
				const blob = new Blob([JSON.stringify({ operations: metricsToSend })], {
					type: 'application/json'
				});
				navigator.sendBeacon('/api/v1/metrics/client', blob);
			} else {
				// Fallback to fetch
				await fetch('/api/v1/metrics/client', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					credentials: 'include',
					body: JSON.stringify({ operations: metricsToSend }),
					keepalive: true
				});
			}
		} catch {
			// Re-queue failed metrics for next flush
			this.pendingMetrics.unshift(...metricsToSend);
		}
	}

	/**
	 * Stop the tracker and cleanup
	 */
	destroy(): void {
		if (this.flushTimer) {
			clearInterval(this.flushTimer);
			this.flushTimer = null;
		}
		this.flush();
	}

	private completeOperation(op: TrackedOperation): void {
		this.operations.delete(op.id);

		// Add to completed buffer (circular)
		this.completedOperations.push(op);
		if (this.completedOperations.length > MAX_BUFFER_SIZE) {
			this.completedOperations.shift();
		}

		// Queue for backend submission
		this.pendingMetrics.push(op);

		// Log slow operations in dev mode
		if (import.meta.env.DEV && op.duration && op.duration > SLOW_THRESHOLD_MS) {
			console.warn(
				`[OperationTracker] Slow operation: ${op.name} took ${Math.round(op.duration)}ms`,
				op.metadata
			);
		}

		// Log failed operations in dev mode
		if (import.meta.env.DEV && op.success === false) {
			console.error(
				`[OperationTracker] Failed operation: ${op.name}`,
				op.error,
				op.metadata
			);
		}
	}
}

// Singleton instance
export const operationTracker = new OperationTracker();

/**
 * Helper function to wrap async operations with tracking
 */
export async function trackOperation<T>(
	name: string,
	operation: () => Promise<T>,
	metadata?: Record<string, unknown>
): Promise<T> {
	const opId = operationTracker.startOp(name, metadata);
	try {
		const result = await operation();
		operationTracker.endOp(opId);
		return result;
	} catch (error) {
		operationTracker.failOp(
			opId,
			error instanceof Error ? error.message : String(error)
		);
		throw error;
	}
}
