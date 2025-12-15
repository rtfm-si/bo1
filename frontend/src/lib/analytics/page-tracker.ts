/**
 * Page Analytics Tracker
 *
 * Tracks page views and conversion events for landing page analytics.
 * Uses navigator.sendBeacon() for reliable unload tracking.
 *
 * Privacy-focused:
 * - No PII stored (uses session fingerprint, not cookies)
 * - Geo data derived server-side from IP
 * - Bot detection happens server-side
 */

import { env } from '$env/dynamic/public';

const API_URL = env.PUBLIC_API_URL || '';

// Generate a session ID using fingerprinting (no cookies needed)
function generateSessionId(): string {
	const canvas = document.createElement('canvas');
	const ctx = canvas.getContext('2d');
	if (ctx) {
		ctx.textBaseline = 'top';
		ctx.font = '14px Arial';
		ctx.fillText('fingerprint', 2, 2);
	}
	const canvasData = canvas.toDataURL();

	const components = [
		navigator.userAgent,
		navigator.language,
		screen.width,
		screen.height,
		screen.colorDepth,
		new Date().getTimezoneOffset(),
		canvasData.slice(0, 100)
	];

	// Simple hash function
	const str = components.join('|');
	let hash = 0;
	for (let i = 0; i < str.length; i++) {
		const char = str.charCodeAt(i);
		hash = (hash << 5) - hash + char;
		hash = hash & hash; // Convert to 32bit integer
	}

	// Add timestamp-based suffix for uniqueness per session
	const sessionSuffix = Math.random().toString(36).substring(2, 10);
	return `${Math.abs(hash).toString(36)}_${sessionSuffix}`;
}

// Get or create session ID (persisted for the browser session)
function getSessionId(): string {
	const key = 'bo1_session_id';
	let sessionId = sessionStorage.getItem(key);
	if (!sessionId) {
		sessionId = generateSessionId();
		sessionStorage.setItem(key, sessionId);
	}
	return sessionId;
}

interface PageViewResponse {
	id: string;
	timestamp: string;
	path: string;
	session_id: string;
}

interface ConversionEvent {
	event_type: 'signup_click' | 'signup_complete' | 'cta_click' | 'waitlist_submit';
	source_path: string;
	element_id?: string;
	element_text?: string;
	metadata?: Record<string, unknown>;
}

// Track scroll depth
let maxScrollDepth = 0;
function updateScrollDepth() {
	const scrollTop = window.scrollY;
	const docHeight = document.documentElement.scrollHeight - window.innerHeight;
	if (docHeight > 0) {
		const depth = Math.round((scrollTop / docHeight) * 100);
		if (depth > maxScrollDepth) {
			maxScrollDepth = depth;
		}
	}
}

// Current page view tracking state
let currentViewId: string | null = null;
let pageStartTime: number | null = null;

/**
 * Initialize page tracking
 * Call this once on page load (typically in +layout.svelte onMount)
 */
export async function initPageTracking(): Promise<void> {
	const sessionId = getSessionId();
	const path = window.location.pathname;

	// Reset tracking state
	maxScrollDepth = 0;
	pageStartTime = Date.now();

	try {
		const response = await fetch(`${API_URL}/api/v1/analytics/page-view`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				path,
				session_id: sessionId,
				referrer: document.referrer || null,
				metadata: {
					screen_width: screen.width,
					screen_height: screen.height,
					viewport_width: window.innerWidth,
					viewport_height: window.innerHeight
				}
			})
		});

		if (response.ok) {
			const data: PageViewResponse = await response.json();
			currentViewId = data.id;
		}
	} catch (error) {
		// Silently fail - analytics should never break the page
		console.debug('[Analytics] Page view tracking failed:', error);
	}

	// Set up scroll tracking
	window.addEventListener('scroll', updateScrollDepth, { passive: true });

	// Set up unload tracking
	window.addEventListener('visibilitychange', handleVisibilityChange);
	window.addEventListener('pagehide', handlePageHide);
}

/**
 * Handle visibility change (tab switch, minimize)
 * Updates page view with duration when page becomes hidden
 */
function handleVisibilityChange() {
	if (document.visibilityState === 'hidden') {
		sendPageUnloadData();
	}
}

/**
 * Handle page hide (navigation, close)
 * Uses sendBeacon for reliable delivery
 */
function handlePageHide() {
	sendPageUnloadData();
}

/**
 * Send page unload data (duration, scroll depth)
 * Uses sendBeacon for reliability
 */
function sendPageUnloadData() {
	if (!currentViewId || !pageStartTime) return;

	const durationMs = Date.now() - pageStartTime;

	// Use sendBeacon for reliable unload tracking
	const data = JSON.stringify({
		duration_ms: durationMs,
		scroll_depth: maxScrollDepth
	});

	try {
		navigator.sendBeacon(
			`${API_URL}/api/v1/analytics/page-view/${currentViewId}`,
			new Blob([data], { type: 'application/json' })
		);
	} catch {
		// Silently fail
	}
}

/**
 * Track a conversion event
 * Call this when user clicks signup button, completes signup, etc.
 */
export async function trackConversion(event: ConversionEvent): Promise<void> {
	const sessionId = getSessionId();

	try {
		await fetch(`${API_URL}/api/v1/analytics/conversion`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				...event,
				session_id: sessionId
			})
		});
	} catch (error) {
		// Silently fail - analytics should never break the page
		console.debug('[Analytics] Conversion tracking failed:', error);
	}
}

/**
 * Track signup button click
 * Convenience wrapper for common conversion event
 */
export function trackSignupClick(elementId?: string, elementText?: string): void {
	trackConversion({
		event_type: 'signup_click',
		source_path: window.location.pathname,
		element_id: elementId,
		element_text: elementText
	});
}

/**
 * Track waitlist form submission
 * Call this when user submits waitlist email
 */
export function trackWaitlistSubmit(email?: string): void {
	trackConversion({
		event_type: 'waitlist_submit',
		source_path: window.location.pathname,
		metadata: {
			// Don't store the actual email - just track that it happened
			email_domain: email ? email.split('@')[1] : undefined
		}
	});
}

/**
 * Track CTA button click
 * For tracking non-signup CTAs
 */
export function trackCTAClick(elementId?: string, elementText?: string): void {
	trackConversion({
		event_type: 'cta_click',
		source_path: window.location.pathname,
		element_id: elementId,
		element_text: elementText
	});
}

/**
 * Cleanup tracking listeners
 * Call this on component destroy if needed
 */
export function cleanupPageTracking(): void {
	if (typeof window === 'undefined') return;

	window.removeEventListener('scroll', updateScrollDepth);
	window.removeEventListener('visibilitychange', handleVisibilityChange);
	window.removeEventListener('pagehide', handlePageHide);

	// Send final data
	sendPageUnloadData();

	// Reset state
	currentViewId = null;
	pageStartTime = null;
	maxScrollDepth = 0;
}
