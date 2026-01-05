/**
 * Types for the comprehensive website crawler
 */

export interface CrawlConfig {
	baseUrl: string;
	maxDepth: number;
	maxPages: number;
	timeout: number;
	skipPatterns: RegExp[];
	includePatterns?: RegExp[];
	runNewMeeting: boolean;
	screenshotOnError: boolean;
	verbose: boolean;
	/** Delay between page navigations in ms (prevents rate limiting) */
	delayBetweenPages?: number;
}

export interface PageInfo {
	url: string;
	title: string;
	depth: number;
	parentUrl?: string;
	crawledAt: Date;
}

export interface ElementInfo {
	selector: string;
	tagName: string;
	type: string; // button, link, dropdown, input, etc.
	text: string;
	ariaLabel?: string;
	role?: string;
	href?: string;
	isVisible: boolean;
	isEnabled: boolean;
}

export interface InteractionResult {
	element: ElementInfo;
	action: 'click' | 'hover' | 'select' | 'type' | 'toggle';
	success: boolean;
	error?: string;
	screenshot?: string;
	duration: number;
	causedNavigation: boolean;
	newUrl?: string;
}

export interface PageValidation {
	hasErrors: boolean;
	consoleErrors: string[];
	networkErrors: NetworkError[];
	emptyElements: ElementInfo[];
	brokenImages: string[];
	a11yIssues: string[];
}

export interface NetworkError {
	url: string;
	status: number;
	statusText: string;
	resourceType: string;
}

export interface CrawlIssue {
	severity: 'critical' | 'error' | 'warning' | 'info';
	category: IssueCategory;
	page: string;
	element?: ElementInfo;
	message: string;
	screenshot?: string;
	timestamp: Date;
	details?: Record<string, unknown>;
}

export type IssueCategory =
	| 'console_error'
	| 'network_error'
	| 'empty_content'
	| 'broken_image'
	| 'interaction_failed'
	| 'timeout'
	| 'infinite_loop'
	| 'navigation_error'
	| 'form_error'
	| 'accessibility'
	| 'visual_regression'
	| 'loading_state';

export interface PageCrawlResult {
	page: PageInfo;
	elements: ElementInfo[];
	interactions: InteractionResult[];
	validation: PageValidation;
	issues: CrawlIssue[];
	discoveredLinks: string[];
	duration: number;
}

export interface CrawlReport {
	config: CrawlConfig;
	startTime: Date;
	endTime: Date;
	duration: number;
	pagesVisited: number;
	totalInteractions: number;
	pages: PageCrawlResult[];
	allIssues: CrawlIssue[];
	summary: CrawlSummary;
}

export interface CrawlSummary {
	totalPages: number;
	totalElements: number;
	totalInteractions: number;
	successfulInteractions: number;
	failedInteractions: number;
	issuesBySeverity: Record<CrawlIssue['severity'], number>;
	issuesByCategory: Record<string, number>;
	pagesWithErrors: string[];
	topIssues: CrawlIssue[];
}
