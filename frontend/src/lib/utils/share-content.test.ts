import { describe, it, expect } from 'vitest';
import {
	generateShareText,
	getTwitterShareUrl,
	getLinkedInShareUrl,
	generateMeetingShareText,
	generateActionShareText,
	type ActivityStats
} from './share-content';

describe('generateShareText', () => {
	it('generates text with all stats', () => {
		const stats: ActivityStats = {
			meetings: 5,
			actionsCompleted: 10,
			mentorSessions: 3,
			period: 'this month'
		};
		const text = generateShareText(stats);
		expect(text).toContain('5 meetings');
		expect(text).toContain('10 actions completed');
		expect(text).toContain('3 mentor sessions');
		expect(text).toContain('this month');
		expect(text).toContain('Board of One');
	});

	it('handles singular counts', () => {
		const stats: ActivityStats = {
			meetings: 1,
			actionsCompleted: 1,
			mentorSessions: 1,
			period: 'this week'
		};
		const text = generateShareText(stats);
		expect(text).toContain('1 meeting');
		expect(text).not.toContain('1 meetings');
		expect(text).toContain('1 action completed');
		expect(text).toContain('1 mentor session');
		expect(text).not.toContain('1 mentor sessions');
	});

	it('handles zero stats', () => {
		const stats: ActivityStats = {
			meetings: 0,
			actionsCompleted: 0,
			mentorSessions: 0,
			period: 'this year'
		};
		const text = generateShareText(stats);
		expect(text).toContain('Tracking my progress');
		expect(text).toContain('this year');
	});

	it('handles partial stats', () => {
		const stats: ActivityStats = {
			meetings: 3,
			actionsCompleted: 0,
			mentorSessions: 2,
			period: 'this quarter'
		};
		const text = generateShareText(stats);
		expect(text).toContain('3 meetings');
		expect(text).not.toContain('actions');
		expect(text).toContain('2 mentor sessions');
	});
});

describe('getTwitterShareUrl', () => {
	it('generates valid Twitter intent URL', () => {
		const text = 'Hello world';
		const url = getTwitterShareUrl(text);
		expect(url).toContain('twitter.com/intent/tweet');
		expect(url).toContain('text=Hello+world');
	});

	it('includes optional URL', () => {
		const text = 'Check this out';
		const shareUrl = 'https://example.com';
		const url = getTwitterShareUrl(text, shareUrl);
		expect(url).toContain('twitter.com/intent/tweet');
		expect(url).toContain('url=https');
	});

	it('properly encodes special characters', () => {
		const text = '10 actions & 5 meetings!';
		const url = getTwitterShareUrl(text);
		expect(url).toContain('text=10+actions+%26+5+meetings%21');
	});
});

describe('getLinkedInShareUrl', () => {
	it('generates valid LinkedIn share URL', () => {
		const url = getLinkedInShareUrl('https://example.com');
		expect(url).toContain('linkedin.com/shareArticle');
		expect(url).toContain('mini=true');
		expect(url).toContain('url=https');
	});

	it('includes title and summary', () => {
		const url = getLinkedInShareUrl(
			'https://example.com',
			'My Progress',
			'Check out my activity'
		);
		expect(url).toContain('title=My+Progress');
		expect(url).toContain('summary=Check+out+my+activity');
	});
});

describe('generateMeetingShareText', () => {
	it('generates Twitter-optimized text for meetings', () => {
		const data = {
			recommendation: 'Launch the new product feature next quarter',
			consensusLevel: 0.85,
			expertCount: 5,
			problemStatement: 'Should we launch?'
		};
		const text = generateMeetingShareText(data, 'twitter');
		expect(text).toContain('Good consensus');
		expect(text).toContain('5 AI experts');
		expect(text).toContain('Launch the new product feature');
		expect(text).toContain('#BoardOfOne');
	});

	it('generates LinkedIn-optimized text with more detail', () => {
		const data = {
			recommendation: 'Implement agile methodology across all teams',
			consensusLevel: 0.92,
			expertCount: 4,
			problemStatement: 'How to improve team velocity?'
		};
		const text = generateMeetingShareText(data, 'linkedin');
		expect(text).toContain('strategic meeting');
		expect(text).toContain('4 AI experts');
		expect(text).toContain('Strong consensus');
		expect(text).toContain('#DecisionMaking');
	});

	it('truncates long recommendations for Twitter', () => {
		const data = {
			recommendation: 'A'.repeat(300), // Very long recommendation
			consensusLevel: 0.75,
			expertCount: 3
		};
		const text = generateMeetingShareText(data, 'twitter');
		expect(text.length).toBeLessThanOrEqual(280);
		expect(text).toContain('...');
	});

	it('handles different consensus levels', () => {
		const baseData = {
			recommendation: 'Test recommendation',
			expertCount: 3
		};

		const strongText = generateMeetingShareText({ ...baseData, consensusLevel: 0.95 }, 'generic');
		expect(strongText).toContain('Strong consensus');

		const goodText = generateMeetingShareText({ ...baseData, consensusLevel: 0.75 }, 'generic');
		expect(goodText).toContain('Good consensus');

		const moderateText = generateMeetingShareText({ ...baseData, consensusLevel: 0.55 }, 'generic');
		expect(moderateText).toContain('Moderate agreement');

		const mixedText = generateMeetingShareText({ ...baseData, consensusLevel: 0.3 }, 'generic');
		expect(mixedText).toContain('Mixed opinions');
	});
});

describe('generateActionShareText', () => {
	it('generates Twitter-optimized text for completed actions', () => {
		const data = {
			title: 'Set up continuous integration pipeline',
			daysToComplete: 3,
			projectName: 'DevOps'
		};
		const text = generateActionShareText(data, 'twitter');
		expect(text).toContain('Quick win');
		expect(text).toContain('Set up continuous integration');
		expect(text).toContain('#BoardOfOne');
	});

	it('generates LinkedIn-optimized text with project info', () => {
		const data = {
			title: 'Complete quarterly review',
			daysToComplete: 5,
			projectName: 'Q4 Planning'
		};
		const text = generateActionShareText(data, 'linkedin');
		expect(text).toContain('Action completed!');
		expect(text).toContain('5 days');
		expect(text).toContain('Q4 Planning');
		expect(text).toContain('#Productivity');
	});

	it('handles different completion speeds', () => {
		const baseData = { title: 'Test task' };

		const lightningText = generateActionShareText({ ...baseData, daysToComplete: 1 }, 'generic');
		expect(lightningText).toContain('Lightning fast');

		const quickText = generateActionShareText({ ...baseData, daysToComplete: 3 }, 'generic');
		expect(quickText).toContain('Quick win');

		const solidText = generateActionShareText({ ...baseData, daysToComplete: 7 }, 'generic');
		expect(solidText).toContain('Solid progress');

		const missionText = generateActionShareText({ ...baseData, daysToComplete: 14 }, 'generic');
		expect(missionText).toContain('Mission accomplished');

		const goalText = generateActionShareText({ ...baseData, daysToComplete: 30 }, 'generic');
		expect(goalText).toContain('Goal achieved');
	});

	it('handles action without days to complete', () => {
		const data = { title: 'Task without timing' };
		const text = generateActionShareText(data, 'generic');
		expect(text).toContain('Task Completed');
	});

	it('truncates long titles for Twitter', () => {
		const data = {
			title: 'B'.repeat(300),
			daysToComplete: 5
		};
		const text = generateActionShareText(data, 'twitter');
		expect(text.length).toBeLessThanOrEqual(280);
		expect(text).toContain('...');
	});
});
