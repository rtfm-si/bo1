/**
 * Sample Decision Data - Example outputs for landing page
 * Shows realistic business decision scenarios across different categories
 */

export interface SampleDecision {
	id: string;
	category: string;
	question: string;
	recommendation: string;
	keyPoints: string[];
	blindSpots: string[];
	nextSteps: string[];
}

export const sampleDecisions: SampleDecision[] = [
	{
		id: 'marketing-ads-vs-content',
		category: 'Marketing',
		question: 'Should I invest $50K in paid ads or hire a content marketer?',
		recommendation:
			'Hire a content marketer first — then allocate 30% of the remaining budget ($15K) to amplify their best content with paid ads.',
		keyPoints: [
			'Content compounds over time; ads stop when budget runs out',
			'Reduces dependency on paid acquisition long-term',
			'Creates owned audience assets (email list, SEO authority)'
		],
		blindSpots: [
			'You may underestimate content production time (3-6 month lag)',
			'Need clear KPIs for content marketer performance'
		],
		nextSteps: [
			'Define content goals: SEO, thought leadership, or conversion?',
			'Write job description with clear 90-day success metrics',
			'Budget $15K for ad testing in Q2 once content is live'
		]
	},
	{
		id: 'hiring-developer-vs-contractors',
		category: 'Hiring',
		question: 'Should I hire a full-time developer or use contractors for my MVP?',
		recommendation:
			'Start with a contract-to-hire arrangement for 3 months — test working relationship and product-market fit before committing to full-time.',
		keyPoints: [
			'Lower financial risk while validating product direction',
			'Built-in trial period to assess technical fit and culture match',
			'Flexibility to pivot technical approach based on early feedback',
			'Clear path to full-time if both sides are aligned'
		],
		blindSpots: [
			'Contractor may have divided attention across multiple clients',
			'Intellectual property agreements must be ironclad from day one',
			'Onboarding time still required — not an instant "plug and play" solution'
		],
		nextSteps: [
			'Draft contract-to-hire agreement with clear IP assignment clause',
			'Define 3-month milestones and decision criteria for full-time conversion',
			'Budget 20% premium over full-time salary to account for contractor rates',
			'Set up weekly 1:1s to build relationship and evaluate cultural fit'
		]
	},
	{
		id: 'product-b2c-to-b2b-pivot',
		category: 'Product',
		question: 'Should I pivot from B2C to B2B, or keep iterating on consumer?',
		recommendation:
			'Run a 6-week B2B pilot with 3-5 enterprise prospects while maintaining your B2C product — let data decide, not assumptions.',
		keyPoints: [
			'B2B feedback cycle is slower but signals are clearer (contracts vs. clicks)',
			'Enterprise customers will tell you exactly what they need to buy',
			'B2C learnings transfer to B2B (UX, value prop clarity)',
			'You can validate B2B demand without burning existing user base'
		],
		blindSpots: [
			'B2B sales cycles can take 6-12 months — do you have runway?',
			'Enterprise customers will demand custom features and SLAs',
			'Team may need new skills (sales, compliance, enterprise support)'
		],
		nextSteps: [
			'Identify 10 target B2B prospects and get 5 intro calls booked this month',
			'Create a simple B2B landing page and pitch deck focused on ROI',
			'Set decision criteria: if 2+ enterprise LOIs by end of Q2, commit to B2B',
			'Keep B2C live but in maintenance mode — no new features until decision made'
		]
	},
	{
		id: 'finance-vc-vs-bootstrap',
		category: 'Finance',
		question: 'Should I raise VC funding now or bootstrap for another 6 months?',
		recommendation:
			'Bootstrap to $30K MRR or 6 months of traction, whichever comes first — then raise a seed round from a position of leverage.',
		keyPoints: [
			'Current valuation likely reflects risk, not progress — wait to capture upside',
			'Proof of organic growth dramatically improves deal terms',
			'Investors pay premium for momentum and founder conviction',
			'6 months buys time to test channels and refine pitch'
		],
		blindSpots: [
			'Runway anxiety may cloud judgment — know your true "zero cash" date',
			'Fundraising takes 3-6 months once you start — factor this into timeline',
			'Some markets require capital to compete (marketplace liquidity, hardware)'
		],
		nextSteps: [
			'Build financial model: how much growth is realistic in 6 months?',
			'Set "go/no-go" metrics: if MRR < $20K by month 4, start fundraising early',
			'Begin informal investor conversations now to warm up relationships',
			'Cut burn by 20% to extend runway — identify 3 non-essential expenses today'
		]
	},
	{
		id: 'growth-expand-vs-focus',
		category: 'Growth',
		question: 'Should I expand to a new market or double down on my existing customer base?',
		recommendation:
			'Double down on existing customers until you hit 30% market penetration or $2M ARR — then expand with a proven playbook.',
		keyPoints: [
			'Easier to grow revenue from happy customers than acquire new ones',
			'Deep market penetration creates network effects and word-of-mouth',
			'Expansion before product-market fit dilutes focus and burns cash',
			'Current customers will fund your expansion through upsells and referrals'
		],
		blindSpots: [
			'Existing market may be smaller than you think — verify TAM assumptions',
			'Competitors may already be moving into adjacent markets',
			'Customer concentration risk if you over-index on single segment'
		],
		nextSteps: [
			'Calculate current market penetration: customers / total addressable market',
			'Survey top 20 customers: "What would make you spend 2x with us?"',
			'Build expansion readiness scorecard: product maturity, team capacity, cash runway',
			'Set trigger: if churn drops below 3% and NPS > 50, greenlight expansion pilot'
		]
	},
	{
		id: 'pricing-freemium-vs-paid',
		category: 'Product',
		question: 'Should I launch with a freemium model or start with paid-only?',
		recommendation:
			'Start paid-only with a 14-day trial — validate willingness to pay before building a free tier that may never convert.',
		keyPoints: [
			'Free users cost money (infrastructure, support) without guaranteed revenue',
			'Paid-first forces clarity on value prop and positioning',
			'Easier to add a free tier later than remove one',
			'Trial period provides conversion data without freemium complexity'
		],
		blindSpots: [
			'Freemium can accelerate top-of-funnel growth and word-of-mouth',
			'Some markets expect free tier (dev tools, productivity apps)',
			'Paid-only may reduce experimentation from price-sensitive early adopters'
		],
		nextSteps: [
			'Research 5 competitors: what pricing model do market leaders use?',
			'Test messaging with 10 target customers: "Would you pay $X for this?"',
			'Set success metrics: 10% trial-to-paid conversion = proceed with paid model',
			'Build simple Stripe integration — avoid complex billing infrastructure early'
		]
	}
];
