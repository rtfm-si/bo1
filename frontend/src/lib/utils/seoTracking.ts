/**
 * SEO Article Analytics Tracking
 *
 * Utility functions to record article events (views, clicks, signups)
 * for SEO content performance analytics.
 *
 * Uses browser sessionStorage for session tracking to de-duplicate
 * events within the same browsing session.
 */

import { env } from '$env/dynamic/public';
import { browser } from '$app/environment';

const API_URL = env.PUBLIC_API_URL || 'http://localhost:8000';
const SESSION_KEY = 'bo1_seo_session_id';

/**
 * Event types for article analytics
 */
export type ArticleEventType = 'view' | 'click' | 'signup';

/**
 * Event data to record
 */
interface ArticleEventData {
	event_type: ArticleEventType;
	referrer?: string;
	utm_source?: string;
	utm_medium?: string;
	utm_campaign?: string;
	session_id?: string;
}

/**
 * Get or create a session ID for tracking.
 * Uses sessionStorage so it persists across page navigations
 * but clears when the browser tab is closed.
 */
function getSessionId(): string {
	if (!browser) return '';

	let sessionId = sessionStorage.getItem(SESSION_KEY);
	if (!sessionId) {
		sessionId = crypto.randomUUID();
		sessionStorage.setItem(SESSION_KEY, sessionId);
	}
	return sessionId;
}

/**
 * Extract UTM parameters from current URL
 */
function getUtmParams(): { utm_source?: string; utm_medium?: string; utm_campaign?: string } {
	if (!browser) return {};

	const params = new URLSearchParams(window.location.search);
	return {
		utm_source: params.get('utm_source') || undefined,
		utm_medium: params.get('utm_medium') || undefined,
		utm_campaign: params.get('utm_campaign') || undefined
	};
}

/**
 * Record an analytics event for an article.
 *
 * @param articleId - The ID of the article
 * @param eventType - Type of event: 'view', 'click', or 'signup'
 * @returns Promise that resolves when event is recorded (or fails silently)
 */
export async function recordArticleEvent(
	articleId: number,
	eventType: ArticleEventType
): Promise<void> {
	if (!browser) return;

	const utm = getUtmParams();
	const eventData: ArticleEventData = {
		event_type: eventType,
		referrer: document.referrer || undefined,
		utm_source: utm.utm_source,
		utm_medium: utm.utm_medium,
		utm_campaign: utm.utm_campaign,
		session_id: getSessionId()
	};

	try {
		// Use sendBeacon for reliability (fires even on page unload)
		// Falls back to fetch if sendBeacon is not available
		const endpoint = `${API_URL}/api/v1/seo/articles/${articleId}/events`;
		const body = JSON.stringify(eventData);

		if (navigator.sendBeacon) {
			const blob = new Blob([body], { type: 'application/json' });
			navigator.sendBeacon(endpoint, blob);
		} else {
			await fetch(endpoint, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body,
				keepalive: true
			});
		}
	} catch (error) {
		// Fail silently - analytics should not break the user experience
		console.debug('[seoTracking] Failed to record event:', error);
	}
}

/**
 * Track a page view for an article.
 * Should be called when an article page is loaded.
 *
 * @param articleId - The ID of the article being viewed
 */
export function trackArticleView(articleId: number): void {
	recordArticleEvent(articleId, 'view');
}

/**
 * Track a click event for an article.
 * Should be called when a user clicks a CTA within the article.
 *
 * @param articleId - The ID of the article
 */
export function trackArticleClick(articleId: number): void {
	recordArticleEvent(articleId, 'click');
}

/**
 * Track a signup conversion from an article.
 * Should be called when a user signs up after reading an article.
 *
 * @param articleId - The ID of the article that led to signup
 */
export function trackArticleSignup(articleId: number): void {
	recordArticleEvent(articleId, 'signup');
}

/**
 * De-duplicated view tracking using sessionStorage.
 * Only records one view per article per session.
 *
 * @param articleId - The ID of the article being viewed
 */
export function trackUniqueArticleView(articleId: number): void {
	if (!browser) return;

	const viewedKey = `bo1_seo_viewed_${articleId}`;
	if (sessionStorage.getItem(viewedKey)) {
		// Already tracked this article in this session
		return;
	}

	sessionStorage.setItem(viewedKey, '1');
	trackArticleView(articleId);
}
