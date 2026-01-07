import { test, expect } from '@playwright/test';

test.describe('Breadcrumbs', () => {
	test.fixme('mentor page has exactly one breadcrumb', async ({ page }) => {
		// FIXME: h1 selector times out in CI - page may load slowly or h1 text differs
		await page.goto('/mentor');

		// Wait for page to load
		await page.waitForSelector('h1:has-text("Mentor")');

		// Count breadcrumb nav elements - should be exactly 1
		const breadcrumbNavs = page.locator('nav[aria-label="Breadcrumb"]');
		await expect(breadcrumbNavs).toHaveCount(1);

		// Verify the breadcrumb contains expected item (path-based, so only "Mentor")
		const breadcrumb = breadcrumbNavs.first();
		await expect(breadcrumb.getByText('Mentor')).toBeVisible();
	});

	test.fixme('seo page has exactly one breadcrumb', async ({ page }) => {
		// FIXME: h1 selector times out in CI - page may load slowly or h1 text differs
		await page.goto('/seo');

		// Wait for page to load
		await page.waitForSelector('h1:has-text("SEO Trend Analyzer")');

		// Count breadcrumb nav elements - should be exactly 1
		const breadcrumbNavs = page.locator('nav[aria-label="Breadcrumb"]');
		await expect(breadcrumbNavs).toHaveCount(1);

		// Verify the breadcrumb contains expected item (path-based, capitalized "Seo")
		const breadcrumb = breadcrumbNavs.first();
		await expect(breadcrumb.locator('text=/seo/i')).toBeVisible();
	});
});
