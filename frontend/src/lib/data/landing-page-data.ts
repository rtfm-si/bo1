/**
 * Landing Page Static Data
 *
 * Contains all static content for the Board of One landing page.
 * Extracted from +page.svelte for better maintainability and type safety.
 */

/**
 * Value block item representing a key benefit
 */
export interface ValueBlock {
	title: string;
	description: string;
	icon: 'users' | 'target' | 'check-circle' | 'zap';
	example: string;
}

/**
 * Metric item for quantified value display
 */
export interface Metric {
	value: string;
	label: string;
	description: string;
}

/**
 * FAQ item with question and answer
 */
export interface FAQ {
	question: string;
	answer: string;
}

/**
 * Core value propositions with examples
 * Displays expert analysis, recommendations, and ongoing support benefits
 */
export const valueBlocks: readonly ValueBlock[] = [
	{
		title: 'Expert-Level Analysis',
		description: 'Complete breakdown with multiple expert perspectives. See blind spots and trade-offs you wouldn\'t find alone.',
		icon: 'users',
		example: 'Identified cap table dilution risk you hadn\'t considered',
	},
	{
		title: 'Clear Recommendations',
		description: 'Not just analysis — decisive recommendations grounded in real-world constraints. Decisions that hold up when stakes are high.',
		icon: 'target',
		example: 'Hire first, spend 30% on ads later',
	},
	{
		title: 'Ongoing Support',
		description: 'Track progress, get follow-up support. Plan B when things change. Minutes, not meetings.',
		icon: 'check-circle',
		example: 'Track 3 KPIs, adjust pricing in Q2',
	},
] as const;

/**
 * Quantified value metrics
 * Shows affordability, speed, expert perspectives, and availability
 */
export const metrics: readonly Metric[] = [
	{
		value: '100x',
		label: 'More Affordable',
		description: 'Than hiring consultants',
	},
	{
		value: '5-15',
		label: 'Minutes',
		description: 'Per decision',
	},
	{
		value: '3-5',
		label: 'Balanced Perspectives',
		description: 'Multiple expert viewpoints',
	},
	{
		value: '24/7',
		label: 'Always Available',
		description: 'No scheduling required',
	},
] as const;

/**
 * Beta program benefits
 * Early access perks for beta users
 */
export const betaBenefits: readonly string[] = [
	'Priority access to new features',
	'Locked-in early-user benefits',
	'Direct influence on the product roadmap',
	'No commitment required',
] as const;

/**
 * Decision types for carousel
 * Realistic strategic decisions Board of One helps with
 */
export const decisionTypes: readonly string[] = [
	'Hiring',
	'Pricing',
	'Positioning',
	'Strategy',
	'Product launches',
	'Fundraising',
	'Runway management',
	'Tool selection',
	'Market expansion',
	'Competitor moves',
	'Prioritization',
	'Partnerships',
	'Marketing channels',
	'Sales approach',
	'Team structure',
	'Product pivots',
	'Feature roadmap',
	'Budget allocation',
	'Vendor selection',
	'Expansion timing',
	'Customer acquisition',
	'Retention strategy',
	'Compensation plans',
	'Equity decisions',
	'Exit planning',
] as const;

/**
 * Frequently asked questions
 * Common questions about Board of One with detailed answers
 */
export const faqs: readonly FAQ[] = [
	{
		question: 'What kind of decisions does Board of One help with?',
		answer: 'Hiring, strategy, pricing, positioning, new opportunities, product choices, competitor moves, prioritization, and more. Any strategic decision where you need clarity.',
	},
	{
		question: 'Is Board of One another AI chat tool?',
		answer: 'No. Board of One analyzes your question, surfaces expert-level insights, and distills everything into a clear recommendation. Most AI tools answer questions. Board of One helps you think.',
	},
	{
		question: 'How does it work?',
		answer: 'Describe your decision in plain language. Board of One breaks it down, analyzes it from multiple expert perspectives, identifies blind spots and trade-offs, then delivers a clear recommendation with next steps. Minutes, not meetings.',
	},
	{
		question: 'Do I need to be technical?',
		answer: 'Not at all. If you can describe your decision, you can use Board of One. It\'s designed for operators, founders, and decision-makers — not engineers.',
	},
	{
		question: 'Is my data safe?',
		answer: 'Yes. Your questions are encrypted in transit and stored securely. You can delete everything with one click. We never share your data.',
	},
	{
		question: 'Will I get in?',
		answer: 'We\'re sending invites in rolling batches throughout Q4 2025. Request access and you\'ll get notified when your spot is ready. First-come, first-served.',
	},
	{
		question: 'Does Board of One cost money right now?',
		answer: 'No. Pricing launches later this year. Beta users get preferential pricing when we launch paid plans.',
	},
	{
		question: 'What if Board of One doesn\'t work for me?',
		answer: 'Leave anytime. No commitment. We focus on operators making real calls, not casual chat.',
	},
] as const;
