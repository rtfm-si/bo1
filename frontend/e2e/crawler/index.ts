/**
 * Website Crawler Module
 *
 * Self-discovering website crawler for comprehensive testing.
 */

export { WebsiteCrawler } from './crawler';
export { ReportGenerator } from './report-generator';
export type {
	CrawlConfig,
	CrawlReport,
	CrawlIssue,
	PageCrawlResult,
	ElementInfo,
	InteractionResult,
	PageValidation
} from './types';
