/**
 * Report Generator for Crawler Results
 * Generates comprehensive markdown reports
 */

import * as fs from 'fs';
import * as path from 'path';
import type { CrawlReport, CrawlIssue, PageCrawlResult } from './types';

export class ReportGenerator {
	private report: CrawlReport;
	private outputDir: string;

	constructor(report: CrawlReport, outputDir: string = './e2e/crawler/reports') {
		this.report = report;
		this.outputDir = outputDir;
	}

	/**
	 * Generate all report files
	 */
	async generate(): Promise<string> {
		// Ensure output directory exists
		fs.mkdirSync(this.outputDir, { recursive: true });

		const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
		const reportPath = path.join(this.outputDir, `crawl-report-${timestamp}.md`);
		const jsonPath = path.join(this.outputDir, `crawl-report-${timestamp}.json`);

		// Generate markdown report
		const markdown = this.generateMarkdown();
		fs.writeFileSync(reportPath, markdown);

		// Save raw JSON for later analysis
		fs.writeFileSync(jsonPath, JSON.stringify(this.report, null, 2));

		// Generate summary for console
		this.printSummary();

		return reportPath;
	}

	/**
	 * Generate markdown report
	 */
	private generateMarkdown(): string {
		const { summary, config } = this.report;
		const lines: string[] = [];

		// Header
		lines.push('# Website Crawler Report');
		lines.push('');
		lines.push(`**Site:** ${config.baseUrl}`);
		lines.push(`**Date:** ${this.report.startTime.toISOString()}`);
		lines.push(`**Duration:** ${this.formatDuration(this.report.duration)}`);
		lines.push('');

		// Executive Summary
		lines.push('## Executive Summary');
		lines.push('');
		lines.push('| Metric | Value |');
		lines.push('|--------|-------|');
		lines.push(`| Pages Crawled | ${summary.totalPages} |`);
		lines.push(`| Elements Tested | ${summary.totalElements} |`);
		lines.push(`| Interactions | ${summary.totalInteractions} |`);
		lines.push(`| Successful | ${summary.successfulInteractions} (${this.percent(summary.successfulInteractions, summary.totalInteractions)}%) |`);
		lines.push(`| Failed | ${summary.failedInteractions} |`);
		lines.push(`| Critical Issues | ${summary.issuesBySeverity.critical || 0} |`);
		lines.push(`| Errors | ${summary.issuesBySeverity.error || 0} |`);
		lines.push(`| Warnings | ${summary.issuesBySeverity.warning || 0} |`);
		lines.push('');

		// Health Score
		const healthScore = this.calculateHealthScore();
		lines.push(`### Health Score: ${healthScore}%`);
		lines.push('');
		lines.push(this.getHealthBadge(healthScore));
		lines.push('');

		// Issues by Category
		if (Object.keys(summary.issuesByCategory).length > 0) {
			lines.push('## Issues by Category');
			lines.push('');
			lines.push('| Category | Count |');
			lines.push('|----------|-------|');
			const sortedCategories = Object.entries(summary.issuesByCategory)
				.sort(([, a], [, b]) => b - a);
			for (const [category, count] of sortedCategories) {
				lines.push(`| ${this.formatCategory(category)} | ${count} |`);
			}
			lines.push('');
		}

		// Critical & Error Issues (detailed)
		const criticalAndErrors = this.report.allIssues.filter(
			i => i.severity === 'critical' || i.severity === 'error'
		);
		if (criticalAndErrors.length > 0) {
			lines.push('## Critical & Error Issues');
			lines.push('');
			lines.push('These issues require immediate attention:');
			lines.push('');

			// Group by page
			const byPage = this.groupByPage(criticalAndErrors);
			for (const [page, issues] of Object.entries(byPage)) {
				lines.push(`### ${this.shortenUrl(page)}`);
				lines.push('');
				for (const issue of issues) {
					lines.push(`- **${issue.severity.toUpperCase()}** [${this.formatCategory(issue.category)}]: ${issue.message}`);
					if (issue.element) {
						lines.push(`  - Element: \`${issue.element.selector}\``);
					}
					if (issue.screenshot) {
						lines.push(`  - Screenshot: \`${issue.screenshot}\``);
					}
				}
				lines.push('');
			}
		}

		// Warnings
		const warnings = this.report.allIssues.filter(i => i.severity === 'warning');
		if (warnings.length > 0) {
			lines.push('## Warnings');
			lines.push('');
			lines.push('<details>');
			lines.push('<summary>Click to expand warnings</summary>');
			lines.push('');

			const byPage = this.groupByPage(warnings);
			for (const [page, issues] of Object.entries(byPage)) {
				lines.push(`### ${this.shortenUrl(page)}`);
				lines.push('');
				for (const issue of issues) {
					lines.push(`- [${this.formatCategory(issue.category)}]: ${issue.message}`);
				}
				lines.push('');
			}

			lines.push('</details>');
			lines.push('');
		}

		// Pages with Errors
		if (summary.pagesWithErrors.length > 0) {
			lines.push('## Pages Requiring Attention');
			lines.push('');
			for (const page of summary.pagesWithErrors) {
				const pageResult = this.report.pages.find(p => p.page.url === page);
				const issueCount = pageResult?.issues.length || 0;
				lines.push(`- [ ] [${this.shortenUrl(page)}](${page}) - ${issueCount} issues`);
			}
			lines.push('');
		}

		// Page-by-Page Details
		lines.push('## Page Details');
		lines.push('');
		lines.push('<details>');
		lines.push('<summary>Click to expand full page details</summary>');
		lines.push('');

		for (const pageResult of this.report.pages) {
			lines.push(`### ${pageResult.page.title || this.shortenUrl(pageResult.page.url)}`);
			lines.push('');
			lines.push(`**URL:** ${pageResult.page.url}`);
			lines.push(`**Elements:** ${pageResult.elements.length}`);
			lines.push(`**Interactions:** ${pageResult.interactions.length}`);
			lines.push(`**Duration:** ${this.formatDuration(pageResult.duration)}`);
			lines.push('');

			if (pageResult.validation.consoleErrors.length > 0) {
				lines.push('**Console Errors:**');
				for (const error of pageResult.validation.consoleErrors.slice(0, 5)) {
					lines.push(`- \`${error.slice(0, 200)}\``);
				}
				lines.push('');
			}

			if (pageResult.validation.networkErrors.length > 0) {
				lines.push('**Network Errors:**');
				for (const error of pageResult.validation.networkErrors.slice(0, 5)) {
					lines.push(`- ${error.status} ${error.statusText}: \`${this.shortenUrl(error.url)}\``);
				}
				lines.push('');
			}

			if (pageResult.validation.brokenImages.length > 0) {
				lines.push('**Broken Images:**');
				for (const img of pageResult.validation.brokenImages) {
					lines.push(`- \`${img}\``);
				}
				lines.push('');
			}

			if (pageResult.validation.a11yIssues.length > 0) {
				lines.push('**Accessibility Issues:**');
				for (const issue of pageResult.validation.a11yIssues) {
					lines.push(`- ${issue}`);
				}
				lines.push('');
			}

			// Failed interactions
			const failed = pageResult.interactions.filter(i => !i.success);
			if (failed.length > 0) {
				lines.push('**Failed Interactions:**');
				for (const interaction of failed.slice(0, 10)) {
					lines.push(`- ${interaction.action} on \`${interaction.element.text || interaction.element.selector}\`: ${interaction.error}`);
				}
				lines.push('');
			}

			lines.push('---');
			lines.push('');
		}

		lines.push('</details>');
		lines.push('');

		// Configuration
		lines.push('## Crawl Configuration');
		lines.push('');
		lines.push('```json');
		lines.push(JSON.stringify({
			baseUrl: config.baseUrl,
			maxDepth: config.maxDepth,
			maxPages: config.maxPages,
			timeout: config.timeout,
			runNewMeeting: config.runNewMeeting
		}, null, 2));
		lines.push('```');
		lines.push('');

		// Discovered Routes
		lines.push('## Discovered Routes');
		lines.push('');
		const routes = Array.from(new Set(this.report.pages.map(p => new URL(p.page.url).pathname))).sort();
		for (const route of routes) {
			lines.push(`- \`${route}\``);
		}
		lines.push('');

		// Footer
		lines.push('---');
		lines.push('');
		lines.push(`*Generated by Bo1 Website Crawler on ${new Date().toISOString()}*`);

		return lines.join('\n');
	}

	/**
	 * Print summary to console
	 */
	private printSummary(): void {
		const { summary } = this.report;
		const healthScore = this.calculateHealthScore();

		console.log('\n' + '='.repeat(60));
		console.log('CRAWL SUMMARY');
		console.log('='.repeat(60));
		console.log(`Pages Crawled:    ${summary.totalPages}`);
		console.log(`Elements Found:   ${summary.totalElements}`);
		console.log(`Interactions:     ${summary.totalInteractions}`);
		console.log(`Success Rate:     ${this.percent(summary.successfulInteractions, summary.totalInteractions)}%`);
		console.log('-'.repeat(60));
		console.log(`Critical Issues:  ${summary.issuesBySeverity.critical || 0}`);
		console.log(`Errors:           ${summary.issuesBySeverity.error || 0}`);
		console.log(`Warnings:         ${summary.issuesBySeverity.warning || 0}`);
		console.log('-'.repeat(60));
		console.log(`Health Score:     ${healthScore}% ${this.getHealthEmoji(healthScore)}`);
		console.log('='.repeat(60) + '\n');

		if (summary.pagesWithErrors.length > 0) {
			console.log('Pages with errors:');
			for (const page of summary.pagesWithErrors.slice(0, 5)) {
				console.log(`  - ${this.shortenUrl(page)}`);
			}
			if (summary.pagesWithErrors.length > 5) {
				console.log(`  ... and ${summary.pagesWithErrors.length - 5} more`);
			}
			console.log('');
		}
	}

	/**
	 * Calculate overall health score (0-100)
	 */
	private calculateHealthScore(): number {
		const { summary } = this.report;

		if (summary.totalInteractions === 0) return 100;

		// Start with success rate
		let score = (summary.successfulInteractions / summary.totalInteractions) * 100;

		// Deduct for issues
		const criticalPenalty = (summary.issuesBySeverity.critical || 0) * 10;
		const errorPenalty = (summary.issuesBySeverity.error || 0) * 3;
		const warningPenalty = (summary.issuesBySeverity.warning || 0) * 0.5;

		score -= criticalPenalty + errorPenalty + warningPenalty;

		return Math.max(0, Math.min(100, Math.round(score)));
	}

	/**
	 * Get health badge markdown
	 */
	private getHealthBadge(score: number): string {
		if (score >= 90) return '![Health](https://img.shields.io/badge/health-excellent-brightgreen)';
		if (score >= 70) return '![Health](https://img.shields.io/badge/health-good-green)';
		if (score >= 50) return '![Health](https://img.shields.io/badge/health-fair-yellow)';
		if (score >= 30) return '![Health](https://img.shields.io/badge/health-poor-orange)';
		return '![Health](https://img.shields.io/badge/health-critical-red)';
	}

	/**
	 * Get health emoji
	 */
	private getHealthEmoji(score: number): string {
		if (score >= 90) return '(Excellent)';
		if (score >= 70) return '(Good)';
		if (score >= 50) return '(Fair)';
		if (score >= 30) return '(Poor)';
		return '(Critical)';
	}

	/**
	 * Format duration in human readable form
	 */
	private formatDuration(ms: number): string {
		if (ms < 1000) return `${ms}ms`;
		if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
		const minutes = Math.floor(ms / 60000);
		const seconds = Math.round((ms % 60000) / 1000);
		return `${minutes}m ${seconds}s`;
	}

	/**
	 * Calculate percentage
	 */
	private percent(value: number, total: number): number {
		if (total === 0) return 100;
		return Math.round((value / total) * 100);
	}

	/**
	 * Format category name
	 */
	private formatCategory(category: string): string {
		return category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
	}

	/**
	 * Shorten URL for display
	 */
	private shortenUrl(url: string): string {
		try {
			const parsed = new URL(url);
			return parsed.pathname + parsed.search;
		} catch {
			return url.length > 60 ? url.slice(0, 57) + '...' : url;
		}
	}

	/**
	 * Group issues by page
	 */
	private groupByPage(issues: CrawlIssue[]): Record<string, CrawlIssue[]> {
		const grouped: Record<string, CrawlIssue[]> = {};
		for (const issue of issues) {
			if (!grouped[issue.page]) {
				grouped[issue.page] = [];
			}
			grouped[issue.page].push(issue);
		}
		return grouped;
	}
}
