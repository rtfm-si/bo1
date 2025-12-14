/**
 * Share content generation utility for social media sharing.
 */

export interface ActivityStats {
	meetings: number;
	actionsCompleted: number;
	mentorSessions: number;
	period: string;
}

/**
 * Generate share text from activity stats.
 */
export function generateShareText(stats: ActivityStats): string {
	const parts: string[] = [];

	if (stats.meetings > 0) {
		parts.push(`${stats.meetings} meeting${stats.meetings !== 1 ? 's' : ''}`);
	}
	if (stats.actionsCompleted > 0) {
		parts.push(`${stats.actionsCompleted} action${stats.actionsCompleted !== 1 ? 's' : ''} completed`);
	}
	if (stats.mentorSessions > 0) {
		parts.push(`${stats.mentorSessions} mentor session${stats.mentorSessions !== 1 ? 's' : ''}`);
	}

	if (parts.length === 0) {
		return `Tracking my progress ${stats.period} with Board of One`;
	}

	const statsText = parts.join(', ');
	return `${statsText} ${stats.period} with Board of One`;
}

/**
 * Generate Twitter/X share URL with pre-filled text.
 */
export function getTwitterShareUrl(text: string, url?: string): string {
	const params = new URLSearchParams();
	params.set('text', text);
	if (url) {
		params.set('url', url);
	}
	return `https://twitter.com/intent/tweet?${params.toString()}`;
}

/**
 * Generate LinkedIn share URL.
 * Note: LinkedIn doesn't support pre-filled text, only URLs.
 */
export function getLinkedInShareUrl(url: string, title?: string, summary?: string): string {
	const params = new URLSearchParams();
	params.set('mini', 'true');
	params.set('url', url);
	if (title) {
		params.set('title', title);
	}
	if (summary) {
		params.set('summary', summary);
	}
	return `https://www.linkedin.com/shareArticle?${params.toString()}`;
}

/**
 * Open share URL in a popup window.
 */
export function openSharePopup(url: string, platform: 'twitter' | 'linkedin'): void {
	const width = platform === 'twitter' ? 550 : 600;
	const height = platform === 'twitter' ? 420 : 600;
	const left = (window.screen.width - width) / 2;
	const top = (window.screen.height - height) / 2;

	window.open(
		url,
		`share_${platform}`,
		`width=${width},height=${height},left=${left},top=${top},toolbar=no,menubar=no,scrollbars=yes`
	);
}

/**
 * Copy text to clipboard.
 */
export async function copyToClipboard(text: string): Promise<boolean> {
	try {
		await navigator.clipboard.writeText(text);
		return true;
	} catch {
		// Fallback for older browsers
		const textArea = document.createElement('textarea');
		textArea.value = text;
		textArea.style.position = 'fixed';
		textArea.style.left = '-9999px';
		document.body.appendChild(textArea);
		textArea.select();
		try {
			document.execCommand('copy');
			return true;
		} catch {
			return false;
		} finally {
			document.body.removeChild(textArea);
		}
	}
}

/**
 * Meeting summary data for share text generation.
 */
export interface MeetingSummaryShareData {
	recommendation: string;
	consensusLevel: number;
	expertCount: number;
	problemStatement?: string;
}

/**
 * Action achievement data for share text generation.
 */
export interface ActionAchievementShareData {
	title: string;
	daysToComplete?: number;
	projectName?: string;
}

/**
 * Twitter character limit (280 - buffer for URL).
 */
const TWITTER_CHAR_LIMIT = 250;

/**
 * LinkedIn recommended character limit for post text.
 */
const LINKEDIN_CHAR_LIMIT = 3000;

/**
 * Generate share text for a meeting summary.
 * Optimized for Twitter/X with fallback truncation.
 */
export function generateMeetingShareText(
	data: MeetingSummaryShareData,
	platform: 'twitter' | 'linkedin' | 'generic' = 'generic'
): string {
	const consensusLabel = getConsensusLabel(data.consensusLevel);
	const limit = platform === 'twitter' ? TWITTER_CHAR_LIMIT : LINKEDIN_CHAR_LIMIT;

	// Build the share text
	let text = '';

	if (platform === 'linkedin') {
		// LinkedIn allows longer text
		text = `Just completed a strategic meeting with ${data.expertCount} AI experts.\n\n`;
		if (data.problemStatement) {
			text += `Question: ${truncateWithEllipsis(data.problemStatement, 200)}\n\n`;
		}
		text += `Key recommendation: ${truncateWithEllipsis(data.recommendation, 500)}\n\n`;
		text += `${consensusLabel} among experts.\n\n`;
		text += `#BoardOfOne #DecisionMaking #AIAssisted`;
	} else {
		// Twitter/generic - shorter format
		const prefix = `${consensusLabel} from ${data.expertCount} AI experts: `;
		const suffix = '\n\n#BoardOfOne';

		const availableChars = limit - prefix.length - suffix.length;
		const truncatedRec = truncateWithEllipsis(data.recommendation, availableChars);

		text = `${prefix}${truncatedRec}${suffix}`;
	}

	return text;
}

/**
 * Generate share text for an action achievement.
 * Optimized for Twitter/X with fallback truncation.
 */
export function generateActionShareText(
	data: ActionAchievementShareData,
	platform: 'twitter' | 'linkedin' | 'generic' = 'generic'
): string {
	const limit = platform === 'twitter' ? TWITTER_CHAR_LIMIT : LINKEDIN_CHAR_LIMIT;

	let text = '';

	if (platform === 'linkedin') {
		// LinkedIn allows longer text
		text = `Action completed! `;
		if (data.daysToComplete) {
			text += `Finished in ${data.daysToComplete} day${data.daysToComplete !== 1 ? 's' : ''}.\n\n`;
		} else {
			text += '\n\n';
		}
		text += `${truncateWithEllipsis(data.title, 500)}\n\n`;
		if (data.projectName) {
			text += `Project: ${data.projectName}\n\n`;
		}
		text += `#BoardOfOne #Productivity #TaskComplete`;
	} else {
		// Twitter/generic - shorter format
		const achievementMsg = data.daysToComplete
			? getAchievementMessage(data.daysToComplete)
			: 'Task Completed';

		let prefix = `${achievementMsg}: `;
		let suffix = '';

		if (data.daysToComplete && data.daysToComplete <= 7) {
			suffix = ` (${data.daysToComplete} day${data.daysToComplete !== 1 ? 's' : ''})`;
		}

		suffix += '\n\n#BoardOfOne';

		const availableChars = limit - prefix.length - suffix.length;
		const truncatedTitle = truncateWithEllipsis(data.title, availableChars);

		text = `${prefix}${truncatedTitle}${suffix}`;
	}

	return text;
}

/**
 * Truncate text with ellipsis.
 */
function truncateWithEllipsis(text: string, maxLength: number): string {
	if (text.length <= maxLength) return text;
	return text.slice(0, maxLength - 3).trim() + '...';
}

/**
 * Get consensus label based on level.
 */
function getConsensusLabel(level: number): string {
	if (level >= 0.9) return 'Strong consensus';
	if (level >= 0.7) return 'Good consensus';
	if (level >= 0.5) return 'Moderate agreement';
	return 'Mixed opinions';
}

/**
 * Get achievement message based on completion speed.
 */
function getAchievementMessage(days: number): string {
	if (days <= 1) return 'Lightning fast';
	if (days <= 3) return 'Quick win';
	if (days <= 7) return 'Solid progress';
	if (days <= 14) return 'Mission accomplished';
	return 'Goal achieved';
}
