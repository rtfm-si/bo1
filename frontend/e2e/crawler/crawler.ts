/**
 * Comprehensive Website Crawler
 * Self-discovers routes and tests all interactive elements
 */

import type { Page, BrowserContext, ConsoleMessage, Request, Response } from '@playwright/test';
import type {
	CrawlConfig,
	PageInfo,
	ElementInfo,
	InteractionResult,
	PageValidation,
	NetworkError,
	CrawlIssue,
	PageCrawlResult,
	CrawlReport,
	IssueCategory
} from './types';

const DEFAULT_CONFIG: CrawlConfig = {
	baseUrl: 'https://boardof.one',
	maxDepth: 5,
	maxPages: 100,
	timeout: 30000,
	skipPatterns: [
		/^mailto:/,
		/^tel:/,
		/^javascript:/,
		/\.(pdf|zip|doc|docx|xls|xlsx)$/i,
		/logout/i,
		/^#$/,
		/^#[a-zA-Z]/
	],
	runNewMeeting: false,
	screenshotOnError: true,
	verbose: false,
	delayBetweenPages: 1000  // 1 second delay to prevent rate limiting
};

export class WebsiteCrawler {
	private page: Page;
	private context: BrowserContext;
	private config: CrawlConfig;
	private visitedUrls: Set<string> = new Set();
	private urlQueue: Array<{ url: string; depth: number; parentUrl?: string }> = [];
	private issues: CrawlIssue[] = [];
	private pageResults: PageCrawlResult[] = [];
	private consoleMessages: ConsoleMessage[] = [];
	private networkErrors: NetworkError[] = [];
	private startTime: Date = new Date();
	private screenshotDir: string;

	constructor(page: Page, context: BrowserContext, config: Partial<CrawlConfig> = {}) {
		this.page = page;
		this.context = context;
		this.config = { ...DEFAULT_CONFIG, ...config };
		this.screenshotDir = `./e2e/crawler/screenshots/${Date.now()}`;
	}

	/**
	 * Main crawl entry point
	 */
	async crawl(): Promise<CrawlReport> {
		this.startTime = new Date();
		this.log('Starting comprehensive crawl of', this.config.baseUrl);

		// Setup listeners
		this.setupListeners();

		// Start from base URL
		this.urlQueue.push({ url: this.config.baseUrl, depth: 0 });

		// Add known important routes to ensure coverage
		this.addKnownRoutes();

		// Process queue
		let isFirstPage = true;
		while (
			this.urlQueue.length > 0 &&
			this.visitedUrls.size < this.config.maxPages
		) {
			const next = this.urlQueue.shift();
			if (!next) break;

			if (this.shouldSkipUrl(next.url) || this.visitedUrls.has(this.normalizeUrl(next.url))) {
				continue;
			}

			// Add delay between pages to prevent rate limiting (skip first page)
			if (!isFirstPage && this.config.delayBetweenPages) {
				await new Promise(resolve => setTimeout(resolve, this.config.delayBetweenPages));
			}
			isFirstPage = false;

			try {
				const result = await this.crawlPage(next.url, next.depth, next.parentUrl);
				this.pageResults.push(result);

				// Add discovered links to queue
				for (const link of result.discoveredLinks) {
					if (!this.visitedUrls.has(this.normalizeUrl(link)) && next.depth < this.config.maxDepth) {
						this.urlQueue.push({ url: link, depth: next.depth + 1, parentUrl: next.url });
					}
				}
			} catch (error) {
				this.addIssue({
					severity: 'critical',
					category: 'navigation_error',
					page: next.url,
					message: `Failed to crawl page: ${error instanceof Error ? error.message : String(error)}`,
					timestamp: new Date()
				});
			}
		}

		return this.generateReport();
	}

	/**
	 * Add known routes to ensure complete coverage
	 */
	private addKnownRoutes(): void {
		// These routes must match actual app routes in src/routes/(app)/
		const knownRoutes = [
			// Core navigation
			'/dashboard',
			'/welcome',
			'/onboarding',
			'/help',

			// Meetings
			'/meeting',           // meetings list (singular, not /meetings)

			// Actions
			'/actions',

			// Datasets
			'/datasets',

			// Settings - all sub-routes
			'/settings',
			'/settings/account',
			'/settings/workspace',
			'/settings/workspace/billing',
			'/settings/privacy',
			'/settings/billing',
			'/settings/integrations',

			// Context - all sub-routes
			'/context',
			'/context/overview',
			'/context/metrics',
			'/context/insights',
			'/context/strategic',
			'/context/key-metrics',
			'/context/peer-benchmarks',

			// Reports - all sub-routes
			'/reports',
			'/reports/meetings',
			'/reports/competitors',
			'/reports/trends',
			'/reports/benchmarks',

			// Projects
			'/projects',
			'/projects/new',

			// Other app pages
			'/mentor',
			'/seo',
			'/analysis'
		];

		for (const route of knownRoutes) {
			const fullUrl = new URL(route, this.config.baseUrl).toString();
			this.urlQueue.push({ url: fullUrl, depth: 1 });
		}

		// Conditionally add new meeting route
		if (this.config.runNewMeeting) {
			this.urlQueue.push({
				url: new URL('/meeting/new', this.config.baseUrl).toString(),
				depth: 1
			});
		}
	}

	/**
	 * Crawl a single page
	 */
	private async crawlPage(url: string, depth: number, parentUrl?: string): Promise<PageCrawlResult> {
		const startTime = Date.now();
		this.log(`Crawling [depth=${depth}]: ${url}`);

		this.visitedUrls.add(this.normalizeUrl(url));
		this.consoleMessages = [];
		this.networkErrors = [];

		// Navigate with timeout protection
		try {
			await this.page.goto(url, {
				waitUntil: 'networkidle',
				timeout: this.config.timeout
			});
		} catch (error) {
			if (String(error).includes('timeout')) {
				this.addIssue({
					severity: 'error',
					category: 'timeout',
					page: url,
					message: `Page load timeout after ${this.config.timeout}ms`,
					timestamp: new Date()
				});
			}
			throw error;
		}

		// Wait for any loading states to clear
		await this.waitForLoadingStates();

		const pageInfo: PageInfo = {
			url: this.page.url(),
			title: await this.page.title(),
			depth,
			parentUrl,
			crawledAt: new Date()
		};

		// Discover all interactive elements
		const elements = await this.discoverElements();
		this.log(`  Found ${elements.length} interactive elements`);

		// Test each element
		const interactions: InteractionResult[] = [];
		for (const element of elements) {
			const result = await this.testElement(element, url);
			if (result) {
				interactions.push(result);

				// If navigation occurred, go back
				if (result.causedNavigation && result.newUrl !== url) {
					await this.page.goto(url, { waitUntil: 'networkidle' });
					await this.waitForLoadingStates();
				}
			}
		}

		// Validate page state
		const validation = await this.validatePage(url);

		// Discover links for further crawling
		const discoveredLinks = await this.discoverLinks();

		// Collect issues from this page
		const pageIssues = this.issues.filter(i => i.page === url);

		return {
			page: pageInfo,
			elements,
			interactions,
			validation,
			issues: pageIssues,
			discoveredLinks,
			duration: Date.now() - startTime
		};
	}

	/**
	 * Wait for loading states to clear
	 */
	private async waitForLoadingStates(): Promise<void> {
		const loadingSelectors = [
			'[data-loading="true"]',
			'.loading',
			'.spinner',
			'[aria-busy="true"]',
			'.skeleton'
		];

		for (const selector of loadingSelectors) {
			try {
				await this.page.waitForSelector(selector, { state: 'hidden', timeout: 5000 });
			} catch {
				// Selector not found or already hidden
			}
		}

		// Additional wait for any animations
		await this.page.waitForTimeout(500);
	}

	/**
	 * Discover all interactive elements on the page
	 */
	private async discoverElements(): Promise<ElementInfo[]> {
		const elements: ElementInfo[] = [];

		// Buttons
		const buttons = await this.page.locator('button:visible, [role="button"]:visible').all();
		for (const btn of buttons) {
			try {
				const info = await this.getElementInfo(btn, 'button');
				if (info) elements.push(info);
			} catch {
				// Element may have become stale
			}
		}

		// Links (internal only)
		const links = await this.page.locator('a[href]:visible').all();
		for (const link of links) {
			try {
				const href = await link.getAttribute('href');
				if (href && this.isInternalLink(href)) {
					const info = await this.getElementInfo(link, 'link');
					if (info) elements.push(info);
				}
			} catch {
				// Element may have become stale
			}
		}

		// Dropdowns / Selects
		const selects = await this.page.locator('select:visible, [role="combobox"]:visible, [role="listbox"]:visible').all();
		for (const select of selects) {
			try {
				const info = await this.getElementInfo(select, 'dropdown');
				if (info) elements.push(info);
			} catch {
				// Element may have become stale
			}
		}

		// Inputs
		const inputs = await this.page.locator('input:visible, textarea:visible').all();
		for (const input of inputs) {
			try {
				const info = await this.getElementInfo(input, 'input');
				if (info) elements.push(info);
			} catch {
				// Element may have become stale
			}
		}

		// Checkboxes and radios
		const toggles = await this.page.locator('[role="checkbox"]:visible, [role="switch"]:visible, [role="radio"]:visible').all();
		for (const toggle of toggles) {
			try {
				const info = await this.getElementInfo(toggle, 'toggle');
				if (info) elements.push(info);
			} catch {
				// Element may have become stale
			}
		}

		// Tabs
		const tabs = await this.page.locator('[role="tab"]:visible').all();
		for (const tab of tabs) {
			try {
				const info = await this.getElementInfo(tab, 'tab');
				if (info) elements.push(info);
			} catch {
				// Element may have become stale
			}
		}

		// Accordion triggers
		const accordions = await this.page.locator('[data-accordion-trigger]:visible, button[aria-expanded]:visible').all();
		for (const acc of accordions) {
			try {
				const info = await this.getElementInfo(acc, 'accordion');
				if (info) elements.push(info);
			} catch {
				// Element may have become stale
			}
		}

		// Menu triggers
		const menuTriggers = await this.page.locator('[aria-haspopup="menu"]:visible, [aria-haspopup="true"]:visible').all();
		for (const menu of menuTriggers) {
			try {
				const info = await this.getElementInfo(menu, 'menu');
				if (info) elements.push(info);
			} catch {
				// Element may have become stale
			}
		}

		return elements;
	}

	/**
	 * Get element info
	 */
	private async getElementInfo(locator: any, type: string): Promise<ElementInfo | null> {
		try {
			const tagName = await locator.evaluate((el: Element) => el.tagName.toLowerCase());
			const text = (await locator.textContent())?.trim() || '';
			const ariaLabel = await locator.getAttribute('aria-label');
			const role = await locator.getAttribute('role');
			const href = type === 'link' ? await locator.getAttribute('href') : undefined;
			const isVisible = await locator.isVisible();
			const isEnabled = await locator.isEnabled();

			// Generate a unique selector
			const selector = await this.generateSelector(locator);

			return {
				selector,
				tagName,
				type,
				text: text.slice(0, 100), // Truncate long text
				ariaLabel: ariaLabel || undefined,
				role: role || undefined,
				href: href || undefined,
				isVisible,
				isEnabled
			};
		} catch {
			return null;
		}
	}

	/**
	 * Generate a stable selector for an element
	 */
	private async generateSelector(locator: any): Promise<string> {
		try {
			const testId = await locator.getAttribute('data-testid');
			if (testId) return `[data-testid="${testId}"]`;

			const id = await locator.getAttribute('id');
			if (id) return `#${id}`;

			const ariaLabel = await locator.getAttribute('aria-label');
			const role = await locator.getAttribute('role');
			if (ariaLabel && role) return `[role="${role}"][aria-label="${ariaLabel}"]`;

			const text = (await locator.textContent())?.trim();
			const tagName = await locator.evaluate((el: Element) => el.tagName.toLowerCase());
			if (text && text.length < 50) return `${tagName}:has-text("${text.slice(0, 30)}")`;

			return await locator.evaluate((el: Element) => {
				const path: string[] = [];
				let current: Element | null = el;
				while (current && current !== document.body) {
					let selector = current.tagName.toLowerCase();
					if (current.id) {
						selector = `#${current.id}`;
						path.unshift(selector);
						break;
					}
					const parent = current.parentElement;
					if (parent) {
						const siblings = Array.from(parent.children).filter(
							c => c.tagName === current!.tagName
						);
						if (siblings.length > 1) {
							const index = siblings.indexOf(current) + 1;
							selector += `:nth-of-type(${index})`;
						}
					}
					path.unshift(selector);
					current = parent;
				}
				return path.join(' > ');
			});
		} catch {
			return 'unknown';
		}
	}

	/**
	 * Test an individual element
	 */
	private async testElement(element: ElementInfo, pageUrl: string): Promise<InteractionResult | null> {
		const startTime = Date.now();

		// Skip disabled elements
		if (!element.isEnabled || !element.isVisible) {
			return null;
		}

		// Skip logout and destructive actions
		if (this.isDestructiveAction(element)) {
			this.log(`  Skipping destructive action: ${element.text || element.selector}`);
			return null;
		}

		// Skip new meeting unless configured
		if (!this.config.runNewMeeting && this.isNewMeetingAction(element)) {
			this.log(`  Skipping new meeting action: ${element.text || element.selector}`);
			return null;
		}

		let result: InteractionResult;
		const action = this.determineAction(element);

		try {
			const locator = this.page.locator(element.selector).first();
			const beforeUrl = this.page.url();

			switch (action) {
				case 'click':
					await locator.click({ timeout: 5000 });
					break;
				case 'hover':
					await locator.hover({ timeout: 5000 });
					break;
				case 'toggle':
					await locator.click({ timeout: 5000 });
					break;
				case 'select':
					// Try to open dropdown
					await locator.click({ timeout: 5000 });
					await this.page.waitForTimeout(300);
					// Close by pressing Escape
					await this.page.keyboard.press('Escape');
					break;
				case 'type':
					// Just focus, don't actually type
					await locator.focus({ timeout: 5000 });
					break;
			}

			await this.page.waitForTimeout(300);
			const afterUrl = this.page.url();
			const causedNavigation = beforeUrl !== afterUrl;

			result = {
				element,
				action,
				success: true,
				duration: Date.now() - startTime,
				causedNavigation,
				newUrl: causedNavigation ? afterUrl : undefined
			};

			// Check for error states after interaction
			const hasError = await this.checkForErrorStates();
			if (hasError) {
				result.success = false;
				result.error = 'Interaction caused error state';
				this.addIssue({
					severity: 'error',
					category: 'interaction_failed',
					page: pageUrl,
					element,
					message: `Element interaction caused error state: ${element.text || element.selector}`,
					timestamp: new Date()
				});
			}

		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : String(error);

			result = {
				element,
				action,
				success: false,
				error: errorMessage,
				duration: Date.now() - startTime,
				causedNavigation: false
			};

			// Only log as issue if it's not a common expected failure
			if (!this.isExpectedFailure(errorMessage)) {
				this.addIssue({
					severity: 'warning',
					category: 'interaction_failed',
					page: pageUrl,
					element,
					message: `Failed to ${action} element: ${errorMessage}`,
					timestamp: new Date()
				});

				if (this.config.screenshotOnError) {
					result.screenshot = await this.takeScreenshot(`error-${Date.now()}`);
				}
			}
		}

		return result;
	}

	/**
	 * Determine the appropriate action for an element
	 */
	private determineAction(element: ElementInfo): InteractionResult['action'] {
		switch (element.type) {
			case 'link':
			case 'button':
			case 'tab':
			case 'accordion':
			case 'menu':
				return 'click';
			case 'toggle':
				return 'toggle';
			case 'dropdown':
				return 'select';
			case 'input':
				return 'type';
			default:
				return 'click';
		}
	}

	/**
	 * Check if element is a destructive action
	 */
	private isDestructiveAction(element: ElementInfo): boolean {
		const text = (element.text + ' ' + (element.ariaLabel || '')).toLowerCase();
		const destructivePatterns = [
			'logout', 'sign out', 'signout', 'log out',
			'delete', 'remove', 'cancel subscription',
			'deactivate', 'close account'
		];
		return destructivePatterns.some(p => text.includes(p));
	}

	/**
	 * Check if element triggers new meeting
	 */
	private isNewMeetingAction(element: ElementInfo): boolean {
		const text = (element.text + ' ' + (element.ariaLabel || '')).toLowerCase();
		const href = element.href?.toLowerCase() || '';
		return (
			text.includes('new meeting') ||
			text.includes('start meeting') ||
			text.includes('create meeting') ||
			href.includes('/meetings/new')
		);
	}

	/**
	 * Check if failure is expected and not an issue
	 */
	private isExpectedFailure(error: string): boolean {
		const expectedPatterns = [
			'element is not attached',
			'element is not visible',
			'element is outside of the viewport',
			'Target closed',
			'Navigation interrupted'
		];
		return expectedPatterns.some(p => error.includes(p));
	}

	/**
	 * Check for error states after interaction
	 */
	private async checkForErrorStates(): Promise<boolean> {
		const errorSelectors = [
			'[role="alert"][data-type="error"]',
			'.error-message',
			'.toast-error',
			'[data-error="true"]'
		];

		for (const selector of errorSelectors) {
			const count = await this.page.locator(selector).count();
			if (count > 0) return true;
		}

		return false;
	}

	/**
	 * Validate page state
	 */
	private async validatePage(url: string): Promise<PageValidation> {
		const validation: PageValidation = {
			hasErrors: false,
			consoleErrors: [],
			networkErrors: [...this.networkErrors],
			emptyElements: [],
			brokenImages: [],
			a11yIssues: []
		};

		// Console errors
		const errorMessages = this.consoleMessages
			.filter(m => m.type() === 'error')
			.map(m => m.text());
		validation.consoleErrors = errorMessages;

		if (errorMessages.length > 0) {
			validation.hasErrors = true;
			for (const error of errorMessages) {
				this.addIssue({
					severity: 'error',
					category: 'console_error',
					page: url,
					message: error,
					timestamp: new Date()
				});
			}
		}

		// Network errors
		if (this.networkErrors.length > 0) {
			validation.hasErrors = true;
			for (const netError of this.networkErrors) {
				this.addIssue({
					severity: 'error',
					category: 'network_error',
					page: url,
					message: `${netError.status} ${netError.statusText}: ${netError.url}`,
					timestamp: new Date(),
					details: { ...netError }
				});
			}
		}

		// Check for empty content areas
		const contentAreas = await this.page.locator('main, [role="main"], .content, article').all();
		for (const area of contentAreas) {
			try {
				const text = (await area.textContent())?.trim() || '';
				if (text.length < 10) {
					const info = await this.getElementInfo(area, 'content');
					if (info) {
						validation.emptyElements.push(info);
						this.addIssue({
							severity: 'warning',
							category: 'empty_content',
							page: url,
							element: info,
							message: 'Content area appears empty',
							timestamp: new Date()
						});
					}
				}
			} catch {
				// Element may be hidden
			}
		}

		// Check for broken images
		const images = await this.page.locator('img').all();
		for (const img of images) {
			try {
				const isLoaded = await img.evaluate((el: HTMLImageElement) => el.complete && el.naturalHeight !== 0);
				if (!isLoaded) {
					const src = await img.getAttribute('src');
					if (src) {
						validation.brokenImages.push(src);
						this.addIssue({
							severity: 'warning',
							category: 'broken_image',
							page: url,
							message: `Broken image: ${src}`,
							timestamp: new Date()
						});
					}
				}
			} catch {
				// Image may be hidden
			}
		}

		// Basic a11y checks
		const a11yIssues = await this.checkAccessibility();
		validation.a11yIssues = a11yIssues;

		return validation;
	}

	/**
	 * Basic accessibility checks
	 */
	private async checkAccessibility(): Promise<string[]> {
		const issues: string[] = [];

		// Images without alt
		const imagesWithoutAlt = await this.page.locator('img:not([alt])').count();
		if (imagesWithoutAlt > 0) {
			issues.push(`${imagesWithoutAlt} images without alt text`);
		}

		// Buttons without accessible name (no aria-label and no text content)
		const buttonsWithoutName = await this.page.evaluate(() => {
			const buttons = document.querySelectorAll('button:not([aria-label])');
			let count = 0;
			buttons.forEach(btn => {
				if (!btn.textContent?.trim()) count++;
			});
			return count;
		});
		if (buttonsWithoutName > 0) {
			issues.push(`${buttonsWithoutName} buttons without accessible name`);
		}

		// Form inputs without labels
		const inputsWithoutLabels = await this.page.locator('input:not([aria-label]):not([aria-labelledby]):not([id])').count();
		if (inputsWithoutLabels > 0) {
			issues.push(`${inputsWithoutLabels} inputs without labels`);
		}

		return issues;
	}

	/**
	 * Discover all links for crawling
	 */
	private async discoverLinks(): Promise<string[]> {
		const links: string[] = [];
		const anchors = await this.page.locator('a[href]').all();

		for (const anchor of anchors) {
			try {
				const href = await anchor.getAttribute('href');
				if (href && this.isInternalLink(href) && !this.shouldSkipUrl(href)) {
					const fullUrl = new URL(href, this.page.url()).toString();
					if (!links.includes(fullUrl)) {
						links.push(fullUrl);
					}
				}
			} catch {
				// Stale element
			}
		}

		return links;
	}

	/**
	 * Check if URL is internal
	 */
	private isInternalLink(href: string): boolean {
		if (href.startsWith('/') && !href.startsWith('//')) return true;
		try {
			const url = new URL(href, this.config.baseUrl);
			const baseHost = new URL(this.config.baseUrl).host;
			return url.host === baseHost;
		} catch {
			return false;
		}
	}

	/**
	 * Check if URL should be skipped
	 */
	private shouldSkipUrl(url: string): boolean {
		for (const pattern of this.config.skipPatterns) {
			if (pattern.test(url)) return true;
		}

		if (this.config.includePatterns && this.config.includePatterns.length > 0) {
			return !this.config.includePatterns.some(p => p.test(url));
		}

		return false;
	}

	/**
	 * Normalize URL for comparison
	 */
	private normalizeUrl(url: string): string {
		try {
			const parsed = new URL(url, this.config.baseUrl);
			// Remove trailing slash, fragment, and common query params
			let normalized = parsed.origin + parsed.pathname.replace(/\/$/, '');
			return normalized;
		} catch {
			return url;
		}
	}

	/**
	 * Setup page listeners
	 */
	private setupListeners(): void {
		this.page.on('console', (msg) => {
			this.consoleMessages.push(msg);
		});

		this.page.on('response', (response: Response) => {
			const status = response.status();
			if (status >= 400) {
				const url = response.url();
				// Skip auth-related 401s - these are expected during session refresh cycles
				const isAuthEndpoint = /\/api\/(v1\/)?auth\//.test(url) ||
					/\/session\/(refresh|signout)/.test(url);
				if (status === 401 && isAuthEndpoint) {
					return; // Don't count auth 401s as errors
				}
				this.networkErrors.push({
					url,
					status,
					statusText: response.statusText(),
					resourceType: response.request().resourceType()
				});
			}
		});

		this.page.on('pageerror', (error) => {
			this.addIssue({
				severity: 'critical',
				category: 'console_error',
				page: this.page.url(),
				message: `Page error: ${error.message}`,
				timestamp: new Date()
			});
		});
	}

	/**
	 * Take screenshot
	 */
	private async takeScreenshot(name: string): Promise<string> {
		const path = `${this.screenshotDir}/${name}.png`;
		try {
			await this.page.screenshot({ path, fullPage: true });
			return path;
		} catch {
			return '';
		}
	}

	/**
	 * Add issue to collection
	 */
	private addIssue(issue: CrawlIssue): void {
		this.issues.push(issue);
	}

	/**
	 * Generate final report
	 */
	private generateReport(): CrawlReport {
		const endTime = new Date();

		const totalInteractions = this.pageResults.reduce(
			(sum, p) => sum + p.interactions.length, 0
		);
		const successfulInteractions = this.pageResults.reduce(
			(sum, p) => sum + p.interactions.filter(i => i.success).length, 0
		);

		const issuesBySeverity: Record<string, number> = {
			critical: 0,
			error: 0,
			warning: 0,
			info: 0
		};
		const issuesByCategory: Record<string, number> = {};

		for (const issue of this.issues) {
			issuesBySeverity[issue.severity] = (issuesBySeverity[issue.severity] || 0) + 1;
			issuesByCategory[issue.category] = (issuesByCategory[issue.category] || 0) + 1;
		}

		const pagesWithErrors = Array.from(new Set(
			this.issues
				.filter(i => i.severity === 'critical' || i.severity === 'error')
				.map(i => i.page)
		));

		const summary = {
			totalPages: this.pageResults.length,
			totalElements: this.pageResults.reduce((sum, p) => sum + p.elements.length, 0),
			totalInteractions,
			successfulInteractions,
			failedInteractions: totalInteractions - successfulInteractions,
			issuesBySeverity,
			issuesByCategory,
			pagesWithErrors,
			topIssues: this.issues
				.filter(i => i.severity === 'critical' || i.severity === 'error')
				.slice(0, 20)
		};

		return {
			config: this.config,
			startTime: this.startTime,
			endTime,
			duration: endTime.getTime() - this.startTime.getTime(),
			pagesVisited: this.visitedUrls.size,
			totalInteractions,
			pages: this.pageResults,
			allIssues: this.issues,
			summary
		};
	}

	/**
	 * Log message if verbose
	 */
	private log(...args: unknown[]): void {
		if (this.config.verbose) {
			console.log('[Crawler]', ...args);
		}
	}
}
