/**
 * Pricing tier data configuration
 * Mirrors backend TierLimits and TierFeatureFlags from bo1/constants.py
 */

export interface TierLimit {
	meetings_monthly: number; // -1 = unlimited
	datasets_total: number;
	mentor_daily: number;
	api_daily: number;
}

export interface TierFeatures {
	meetings: boolean;
	datasets: boolean;
	mentor: boolean;
	api_access: boolean;
	priority_support: boolean;
	advanced_analytics: boolean;
	custom_personas: boolean;
	session_export: boolean;
	session_sharing: boolean;
}

export interface PricingTier {
	id: 'free' | 'starter' | 'pro';
	name: string;
	description: string;
	price: number | null; // null = contact sales, 0 = free
	priceLabel: string;
	period: string;
	limits: TierLimit;
	features: TierFeatures;
	highlight?: boolean; // Show "Most Popular" badge
	ctaLabel: string;
	ctaHref: string;
	stripePriceId?: string; // Stripe price ID for checkout
}

export const TIER_LIMITS: Record<string, TierLimit> = {
	free: {
		meetings_monthly: 3,
		datasets_total: 5,
		mentor_daily: 10,
		api_daily: 0
	},
	starter: {
		meetings_monthly: 20,
		datasets_total: 25,
		mentor_daily: 50,
		api_daily: 100
	},
	pro: {
		meetings_monthly: -1, // unlimited
		datasets_total: 100,
		mentor_daily: -1, // unlimited
		api_daily: 1000
	}
};

export const TIER_FEATURES: Record<string, TierFeatures> = {
	free: {
		meetings: true,
		datasets: true,
		mentor: true,
		api_access: false,
		priority_support: false,
		advanced_analytics: false,
		custom_personas: false,
		session_export: true,
		session_sharing: true
	},
	starter: {
		meetings: true,
		datasets: true,
		mentor: true,
		api_access: true,
		priority_support: false,
		advanced_analytics: true,
		custom_personas: false,
		session_export: true,
		session_sharing: true
	},
	pro: {
		meetings: true,
		datasets: true,
		mentor: true,
		api_access: true,
		priority_support: true,
		advanced_analytics: true,
		custom_personas: true,
		session_export: true,
		session_sharing: true
	}
};

export const PRICING_TIERS: PricingTier[] = [
	{
		id: 'free',
		name: 'Free',
		description: 'Perfect for trying out Board of One',
		price: 0,
		priceLabel: '$0',
		period: 'forever',
		limits: TIER_LIMITS.free,
		features: TIER_FEATURES.free,
		ctaLabel: 'Get Started',
		ctaHref: '/waitlist'
	},
	{
		id: 'starter',
		name: 'Starter',
		description: 'For growing businesses making regular decisions',
		price: 29,
		priceLabel: '$29',
		period: 'per month',
		limits: TIER_LIMITS.starter,
		features: TIER_FEATURES.starter,
		highlight: true,
		ctaLabel: 'Start Free Trial',
		ctaHref: '/waitlist'
	},
	{
		id: 'pro',
		name: 'Pro',
		description: 'For power users and teams requiring unlimited access',
		price: 99,
		priceLabel: '$99',
		period: 'per month',
		limits: TIER_LIMITS.pro,
		features: TIER_FEATURES.pro,
		ctaLabel: 'Start Free Trial',
		ctaHref: '/waitlist'
	}
];

// Feature row labels for comparison table
export interface FeatureRow {
	key: string;
	label: string;
	description?: string;
	type: 'limit' | 'feature';
	limitKey?: keyof TierLimit;
	featureKey?: keyof TierFeatures;
}

export const FEATURE_ROWS: FeatureRow[] = [
	{
		key: 'meetings',
		label: 'Meetings per month',
		description: 'AI-facilitated deliberation sessions',
		type: 'limit',
		limitKey: 'meetings_monthly'
	},
	{
		key: 'datasets',
		label: 'Active datasets',
		description: 'CSV and Google Sheets data sources',
		type: 'limit',
		limitKey: 'datasets_total'
	},
	{
		key: 'mentor',
		label: 'Mentor chats per day',
		description: 'On-demand AI business advisor',
		type: 'limit',
		limitKey: 'mentor_daily'
	},
	{
		key: 'api_access',
		label: 'API access',
		description: 'Programmatic integration',
		type: 'feature',
		featureKey: 'api_access'
	},
	{
		key: 'api_calls',
		label: 'API calls per day',
		description: 'For external integrations',
		type: 'limit',
		limitKey: 'api_daily'
	},
	{
		key: 'advanced_analytics',
		label: 'Advanced analytics',
		description: 'Detailed usage insights and trends',
		type: 'feature',
		featureKey: 'advanced_analytics'
	},
	{
		key: 'custom_personas',
		label: 'Custom personas',
		description: 'Create your own expert advisors',
		type: 'feature',
		featureKey: 'custom_personas'
	},
	{
		key: 'priority_support',
		label: 'Priority support',
		description: 'Fast-track issue resolution',
		type: 'feature',
		featureKey: 'priority_support'
	},
	{
		key: 'session_export',
		label: 'Session export',
		description: 'Download meetings as JSON/Markdown',
		type: 'feature',
		featureKey: 'session_export'
	},
	{
		key: 'session_sharing',
		label: 'Session sharing',
		description: 'Share meeting results via link',
		type: 'feature',
		featureKey: 'session_sharing'
	}
];

// FAQ items for pricing page
export interface FAQItem {
	question: string;
	answer: string;
}

export const PRICING_FAQ: FAQItem[] = [
	{
		question: 'Can I change plans at any time?',
		answer:
			'Yes, you can upgrade or downgrade your plan at any time. When upgrading, you get immediate access to new features. When downgrading, the change takes effect at your next billing cycle.'
	},
	{
		question: 'What happens if I exceed my meeting limit?',
		answer:
			"You'll receive a notification when approaching your limit. Once reached, you can upgrade your plan or wait until your monthly limit resets."
	},
	{
		question: 'Is there a free trial for paid plans?',
		answer:
			'Yes, all paid plans include a 14-day free trial. No credit card required to start.'
	},
	{
		question: 'What payment methods do you accept?',
		answer:
			'We accept all major credit cards (Visa, Mastercard, American Express) through our secure payment processor.'
	},
	{
		question: 'Can I get a refund?',
		answer:
			"We offer a 30-day money-back guarantee. If you're not satisfied with your purchase, contact support for a full refund."
	},
	{
		question: 'Do you offer team or enterprise pricing?',
		answer:
			'Yes, we offer custom pricing for teams and enterprises. Contact us for volume discounts and dedicated support options.'
	}
];

// Helper to format limit values
export function formatLimit(value: number): string {
	if (value === -1) return 'Unlimited';
	if (value === 0) return '-';
	return value.toString();
}

// Helper to check if a tier has a feature
export function tierHasFeature(tier: PricingTier, featureKey: keyof TierFeatures): boolean {
	return tier.features[featureKey];
}

// Helper to get limit value for display
export function getTierLimitDisplay(tier: PricingTier, limitKey: keyof TierLimit): string {
	return formatLimit(tier.limits[limitKey]);
}
