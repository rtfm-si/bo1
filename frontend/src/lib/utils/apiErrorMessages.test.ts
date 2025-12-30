/**
 * Tests for apiErrorMessages utility
 *
 * Verifies:
 * - All ErrorCode values map to user-friendly messages
 * - Default message is returned for unknown codes
 * - Helper functions work correctly
 */

import { describe, it, expect } from 'vitest';
import {
	getErrorMessage,
	isTransientError,
	getRecoveryTime,
	formatRecoveryTime,
	getSeverityClass,
	PROVIDER_FALLBACK_MESSAGE,
	RETRY_IN_PROGRESS_MESSAGE,
	type ErrorCode
} from './apiErrorMessages';

describe('apiErrorMessages', () => {
	describe('getErrorMessage', () => {
		it('returns correct message for LLM_CIRCUIT_OPEN', () => {
			const msg = getErrorMessage('LLM_CIRCUIT_OPEN');
			expect(msg.title).toBe('Switching to Backup Provider');
			expect(msg.isTransient).toBe(true);
			expect(msg.recoveryTimeSeconds).toBe(30);
		});

		it('returns correct message for LLM_RATE_LIMIT', () => {
			const msg = getErrorMessage('LLM_RATE_LIMIT');
			expect(msg.title).toBe('High Demand');
			expect(msg.severity).toBe('info');
			expect(msg.isTransient).toBe(true);
		});

		it('returns correct message for LLM_RETRIES_EXHAUSTED', () => {
			const msg = getErrorMessage('LLM_RETRIES_EXHAUSTED');
			expect(msg.title).toBe('Unable to Complete Request');
			expect(msg.isTransient).toBe(false);
		});

		it('returns correct message for LLM_TIMEOUT', () => {
			const msg = getErrorMessage('LLM_TIMEOUT');
			expect(msg.title).toBe('Request Timed Out');
			expect(msg.recoveryTimeSeconds).toBe(60);
		});

		it('returns correct message for DB_CONNECTION_ERROR', () => {
			const msg = getErrorMessage('DB_CONNECTION_ERROR');
			expect(msg.title).toBe('Database Connection Issue');
			expect(msg.severity).toBe('error');
		});

		it('returns correct message for REDIS_CONNECTION_ERROR', () => {
			const msg = getErrorMessage('REDIS_CONNECTION_ERROR');
			expect(msg.title).toBe('Real-time Updates Interrupted');
			expect(msg.severity).toBe('warning');
		});

		it('returns correct message for SERVICE_UNAVAILABLE', () => {
			const msg = getErrorMessage('SERVICE_UNAVAILABLE');
			expect(msg.title).toBe('Service Unavailable');
			expect(msg.recoveryTimeSeconds).toBe(60);
		});

		it('returns default message for unknown error code', () => {
			const msg = getErrorMessage('UNKNOWN_ERROR_CODE');
			expect(msg.title).toBe('Something Went Wrong');
			expect(msg.isTransient).toBe(true);
		});

		it('returns default message for null', () => {
			const msg = getErrorMessage(null);
			expect(msg.title).toBe('Something Went Wrong');
		});

		it('returns default message for undefined', () => {
			const msg = getErrorMessage(undefined);
			expect(msg.title).toBe('Something Went Wrong');
		});

		it('returns default message for empty string', () => {
			const msg = getErrorMessage('');
			expect(msg.title).toBe('Something Went Wrong');
		});
	});

	describe('isTransientError', () => {
		it('returns true for transient errors', () => {
			expect(isTransientError('LLM_RATE_LIMIT')).toBe(true);
			expect(isTransientError('LLM_TIMEOUT')).toBe(true);
			expect(isTransientError('LLM_CIRCUIT_OPEN')).toBe(true);
			expect(isTransientError('REDIS_CONNECTION_ERROR')).toBe(true);
		});

		it('returns false for non-transient errors', () => {
			expect(isTransientError('LLM_RETRIES_EXHAUSTED')).toBe(false);
			expect(isTransientError('SERVICE_CONFIG_ERROR')).toBe(false);
			expect(isTransientError('CONFIG_ERROR')).toBe(false);
		});

		it('returns true for unknown errors (default)', () => {
			expect(isTransientError('UNKNOWN')).toBe(true);
			expect(isTransientError(null)).toBe(true);
		});
	});

	describe('getRecoveryTime', () => {
		it('returns recovery time for errors with estimates', () => {
			expect(getRecoveryTime('LLM_CIRCUIT_OPEN')).toBe(30);
			expect(getRecoveryTime('LLM_TIMEOUT')).toBe(60);
			expect(getRecoveryTime('LLM_RATE_LIMIT')).toBe(30);
			expect(getRecoveryTime('DB_CONNECTION_ERROR')).toBe(10);
		});

		it('returns undefined for errors without recovery time', () => {
			expect(getRecoveryTime('LLM_RETRIES_EXHAUSTED')).toBeUndefined();
			expect(getRecoveryTime('SERVICE_CONFIG_ERROR')).toBeUndefined();
		});
	});

	describe('formatRecoveryTime', () => {
		it('formats seconds correctly', () => {
			expect(formatRecoveryTime(30)).toBe('~30 seconds');
			expect(formatRecoveryTime(15)).toBe('~15 seconds');
			expect(formatRecoveryTime(5)).toBe('~5 seconds');
		});

		it('formats minutes correctly', () => {
			expect(formatRecoveryTime(60)).toBe('~1 minute');
			expect(formatRecoveryTime(120)).toBe('~2 minutes');
			expect(formatRecoveryTime(90)).toBe('~2 minutes');
		});

		it('returns empty string for undefined', () => {
			expect(formatRecoveryTime(undefined)).toBe('');
		});

		it('returns empty string for zero', () => {
			expect(formatRecoveryTime(0)).toBe('');
		});
	});

	describe('getSeverityClass', () => {
		it('returns severity as class name', () => {
			expect(getSeverityClass('info')).toBe('info');
			expect(getSeverityClass('warning')).toBe('warning');
			expect(getSeverityClass('error')).toBe('error');
			expect(getSeverityClass('critical')).toBe('critical');
		});
	});

	describe('exported constants', () => {
		it('PROVIDER_FALLBACK_MESSAGE has required properties', () => {
			expect(PROVIDER_FALLBACK_MESSAGE.title).toBe('Switching AI Providers');
			expect(PROVIDER_FALLBACK_MESSAGE.icon).toBe('🔄');
			expect(PROVIDER_FALLBACK_MESSAGE.estimatedTime).toBe('~30 seconds');
		});

		it('RETRY_IN_PROGRESS_MESSAGE has required properties', () => {
			expect(RETRY_IN_PROGRESS_MESSAGE.title).toBe('Retrying Request');
			expect(RETRY_IN_PROGRESS_MESSAGE.icon).toBe('🔁');
			expect(RETRY_IN_PROGRESS_MESSAGE.estimatedTime).toBe('~15 seconds');
		});
	});

	describe('ErrorCode coverage', () => {
		// Ensure all documented ErrorCode values have mappings
		const errorCodes: ErrorCode[] = [
			'LLM_API_ERROR',
			'LLM_RATE_LIMIT',
			'LLM_TIMEOUT',
			'LLM_RETRIES_EXHAUSTED',
			'LLM_PARSE_FAILED',
			'LLM_CACHE_ERROR',
			'LLM_CIRCUIT_OPEN',
			'LLM_EMBEDDING_FAILED',
			'DB_CONNECTION_ERROR',
			'DB_QUERY_ERROR',
			'DB_WRITE_ERROR',
			'DB_PARTITION_ERROR',
			'REDIS_CONNECTION_ERROR',
			'REDIS_READ_ERROR',
			'REDIS_WRITE_ERROR',
			'SERVICE_UNAVAILABLE',
			'SERVICE_CONFIG_ERROR',
			'CONFIG_ERROR',
			'SERVICE_DEPENDENCY_ERROR',
			'SERVICE_EXECUTION_ERROR',
			'API_REQUEST_ERROR',
			'API_SSE_ERROR',
			'API_SESSION_ERROR',
			'API_RATE_LIMIT'
		];

		it.each(errorCodes)('has mapping for %s', (code) => {
			const msg = getErrorMessage(code);
			// Should not return the default "Something Went Wrong" title
			expect(msg.title).not.toBe('Something Went Wrong');
			expect(msg.description).toBeDefined();
			expect(msg.severity).toBeDefined();
			expect(typeof msg.isTransient).toBe('boolean');
		});
	});
});
