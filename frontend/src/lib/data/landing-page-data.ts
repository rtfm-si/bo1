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
 * Quantified value metrics - The 4 Pillars
 * Speed, Cost, Quality, Accountability
 */
export const metrics: readonly Metric[] = [
	{
		value: 'Minutes',
		label: 'Not Meetings',
		description: 'No calendars. No pre-reads. No follow-ups.',
	},
	{
		value: '1%',
		label: 'The Cost',
		description: 'Of hiring an advisor or consultant.',
	},
	{
		value: 'Every',
		label: 'Decision Challenged',
		description: 'Logged, documented, revisitable.',
	},
	{
		value: 'One',
		label: 'Owner. One Decision.',
		description: 'What hierarchy pretends to deliver.',
	},
] as const;

/**
 * Beta program benefits
 * Early access perks for beta users
 */
export const betaBenefits: readonly string[] = [
	'Preferential pricing locked in forever',
	'Priority access to new capabilities',
	'Direct influence on the roadmap',
	'No commitment — leave anytime',
] as const;

/**
 * Decision types for carousel - Row 1 (scrolls left)
 * Realistic strategic decisions Board of One helps with
 */
export const decisionTypesRow1: readonly string[] = [
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
] as const;

/**
 * Decision types for carousel - Row 2 (scrolls right)
 */
export const decisionTypesRow2: readonly string[] = [
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
		question: 'Does this replace my management team?',
		answer: 'No. It compresses management work so you can delay management hires. You still own the decisions. Board of One handles the preparation — context, options, risks, trade-offs — so you can focus on the call itself.',
	},
	{
		question: 'Is this just ChatGPT with a fancy prompt?',
		answer: 'No. It\'s a structured deliberation process with named perspectives, documented reasoning, and decision logs. Not chat — a management operating system. The output is a defensible recommendation with next steps, not a wall of text.',
	},
	{
		question: 'What kind of decisions does it help with?',
		answer: 'Hiring, pricing, positioning, strategy, product launches, fundraising, market expansion, tool selection, team structure, budget allocation — any strategic decision where you need clarity and can\'t afford to get it wrong.',
	},
	{
		question: 'How is this different from hiring a consultant?',
		answer: 'Consultants cost £500-2000/day and take weeks. Board of One delivers management-grade analysis in minutes for a fraction of the cost. No scheduling, no waiting, no scope creep.',
	},
	{
		question: 'How does it actually work?',
		answer: 'Describe your decision in plain language. Board of One breaks it down, analyzes it from multiple expert perspectives, surfaces blind spots and trade-offs, then delivers a clear recommendation with documented reasoning and next steps.',
	},
	{
		question: 'Is my data safe?',
		answer: 'Yes. Your decisions are encrypted in transit and stored securely. You can delete everything with one click. We never share or train on your data.',
	},
	{
		question: 'Who is this built for?',
		answer: 'Founders doing £10k–£2m ARR who feel the drag of decisions they shouldn\'t still be making. Solo operators who should hire a Head of X but can\'t justify £100k yet. Anyone scaling without a management layer.',
	},
	{
		question: 'Does it cost money right now?',
		answer: 'Pricing launches later this year. Beta users get preferential rates locked in. No credit card required to join.',
	},
] as const;
