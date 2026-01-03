/**
 * Currency formatting utilities.
 * Provides locale-aware currency formatting with abbreviation support.
 */

export type CurrencyCode = 'GBP' | 'USD' | 'EUR';

/** Currency symbol lookup */
const CURRENCY_SYMBOLS: Record<CurrencyCode, string> = {
	GBP: '£',
	USD: '$',
	EUR: '€'
};

/** Currency locale lookup for Intl formatting */
const CURRENCY_LOCALES: Record<CurrencyCode, string> = {
	GBP: 'en-GB',
	USD: 'en-US',
	EUR: 'de-DE'
};

/**
 * Format a number as currency with optional abbreviation.
 *
 * @param value - The numeric value to format
 * @param currency - Currency code (GBP, USD, EUR)
 * @param options - Formatting options
 * @returns Formatted currency string
 *
 * @example
 * formatCurrency(1234.56, 'GBP') // '£1,234.56'
 * formatCurrency(1234567, 'USD', { abbreviated: true }) // '$1.23M'
 * formatCurrency(1000, 'EUR', { abbreviated: true }) // '€1K'
 */
export function formatCurrency(
	value: number | string | null | undefined,
	currency: CurrencyCode = 'GBP',
	options: {
		abbreviated?: boolean;
		decimals?: number;
		showSymbol?: boolean;
	} = {}
): string {
	const { abbreviated = false, decimals = 2, showSymbol = true } = options;

	// Handle null/undefined
	if (value === null || value === undefined) {
		return showSymbol ? `${CURRENCY_SYMBOLS[currency]}—` : '—';
	}

	// Convert string to number if needed
	const numValue = typeof value === 'string' ? parseFloat(value.replace(/[^0-9.-]/g, '')) : value;

	if (isNaN(numValue)) {
		return showSymbol ? `${CURRENCY_SYMBOLS[currency]}—` : '—';
	}

	const symbol = CURRENCY_SYMBOLS[currency];

	if (abbreviated) {
		return formatAbbreviated(numValue, symbol, showSymbol, decimals);
	}

	// Use Intl.NumberFormat for precise locale-aware formatting
	const locale = CURRENCY_LOCALES[currency];
	const formatted = new Intl.NumberFormat(locale, {
		style: showSymbol ? 'currency' : 'decimal',
		currency: currency,
		minimumFractionDigits: decimals,
		maximumFractionDigits: decimals
	}).format(numValue);

	return formatted;
}

/**
 * Format with K/M/B abbreviations.
 */
function formatAbbreviated(
	value: number,
	symbol: string,
	showSymbol: boolean,
	decimals: number
): string {
	const absValue = Math.abs(value);
	const sign = value < 0 ? '-' : '';
	const prefix = showSymbol ? symbol : '';

	if (absValue >= 1_000_000_000) {
		return `${sign}${prefix}${(absValue / 1_000_000_000).toFixed(decimals)}B`;
	}
	if (absValue >= 1_000_000) {
		return `${sign}${prefix}${(absValue / 1_000_000).toFixed(decimals)}M`;
	}
	if (absValue >= 1_000) {
		return `${sign}${prefix}${(absValue / 1_000).toFixed(decimals)}K`;
	}

	return `${sign}${prefix}${absValue.toFixed(decimals)}`;
}

/**
 * Get the currency symbol for a given currency code.
 *
 * @param currency - Currency code
 * @returns Currency symbol
 */
export function getCurrencySymbol(currency: CurrencyCode): string {
	return CURRENCY_SYMBOLS[currency] || '£';
}

/**
 * Parse a currency string to extract the numeric value.
 *
 * @param value - Currency string (e.g., '$1,234.56', '£50K', '€1.5M')
 * @returns Parsed numeric value or null if invalid
 */
export function parseCurrencyValue(value: string): number | null {
	if (!value) return null;

	// Remove currency symbols and whitespace
	let cleaned = value.replace(/[£$€\s,]/g, '');

	// Handle abbreviations
	let multiplier = 1;
	if (cleaned.endsWith('B') || cleaned.endsWith('b')) {
		multiplier = 1_000_000_000;
		cleaned = cleaned.slice(0, -1);
	} else if (cleaned.endsWith('M') || cleaned.endsWith('m')) {
		multiplier = 1_000_000;
		cleaned = cleaned.slice(0, -1);
	} else if (cleaned.endsWith('K') || cleaned.endsWith('k')) {
		multiplier = 1_000;
		cleaned = cleaned.slice(0, -1);
	}

	const num = parseFloat(cleaned);
	return isNaN(num) ? null : num * multiplier;
}

/**
 * Check if a metric name suggests it's a monetary value.
 *
 * @param metricName - The name of the metric
 * @returns True if the metric appears to be monetary
 */
export function isMonetaryMetric(metricName: string): boolean {
	const lowerName = metricName.toLowerCase();
	const monetaryKeywords = [
		'revenue',
		'cost',
		'price',
		'profit',
		'margin',
		'salary',
		'income',
		'expense',
		'budget',
		'spend',
		'mrr',
		'arr',
		'arpu',
		'ltv',
		'cac',
		'aov',
		'gmv',
		'value'
	];

	return monetaryKeywords.some((keyword) => lowerName.includes(keyword));
}
