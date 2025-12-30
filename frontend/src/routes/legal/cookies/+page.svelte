<script lang="ts">
	/**
	 * Cookie Policy Page
	 */
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';

	const lastUpdated = '2025-12-29';
</script>

<svelte:head>
	<title>Cookie Policy - Board of One</title>
</svelte:head>

<div class="min-h-screen flex flex-col">
	<Header />

	<main class="flex-grow bg-white dark:bg-neutral-900 py-16">
		<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
			<h1 class="text-4xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">Cookie Policy</h1>
			<p class="text-neutral-600 dark:text-neutral-400 mb-12">
				Last updated: {lastUpdated}
			</p>

			<div class="prose prose-neutral dark:prose-invert max-w-none">
				<h2>1. What Are Cookies?</h2>
				<p>
					Cookies are small text files stored on your device (computer, tablet, or mobile) when you
					visit our website. They help us provide you with a better experience by remembering your
					preferences and enabling certain features.
				</p>

				<h2>2. How We Use Cookies</h2>
				<p>Board of One uses cookies for the following purposes:</p>

				<h3>2.1 Essential Cookies (Always Active)</h3>
				<p>These cookies are necessary for the Service to function and cannot be disabled:</p>
				<table class="min-w-full border border-neutral-300 dark:border-neutral-700 mt-4">
					<thead>
						<tr class="bg-neutral-100 dark:bg-neutral-800">
							<th
								class="border border-neutral-300 dark:border-neutral-700 px-4 py-2 text-left"
								>Cookie Name</th
							>
							<th
								class="border border-neutral-300 dark:border-neutral-700 px-4 py-2 text-left"
								>Purpose</th
							>
							<th
								class="border border-neutral-300 dark:border-neutral-700 px-4 py-2 text-left"
								>Duration</th
							>
						</tr>
					</thead>
					<tbody>
						<tr>
							<td class="border border-neutral-300 dark:border-neutral-700 px-4 py-2"
								><code>sAccessToken</code></td
							>
							<td class="border border-neutral-300 dark:border-neutral-700 px-4 py-2"
								>Authentication (SuperTokens)</td
							>
							<td class="border border-neutral-300 dark:border-neutral-700 px-4 py-2"
								>Session (1 hour)</td
							>
						</tr>
						<tr>
							<td class="border border-neutral-300 dark:border-neutral-700 px-4 py-2"
								><code>sRefreshToken</code></td
							>
							<td class="border border-neutral-300 dark:border-neutral-700 px-4 py-2"
								>Session refresh</td
							>
							<td class="border border-neutral-300 dark:border-neutral-700 px-4 py-2"
								>30 days</td
							>
						</tr>
						<tr>
							<td class="border border-neutral-300 dark:border-neutral-700 px-4 py-2"
								><code>session_id</code></td
							>
							<td class="border border-neutral-300 dark:border-neutral-700 px-4 py-2"
								>Track active deliberation session</td
							>
							<td class="border border-neutral-300 dark:border-neutral-700 px-4 py-2"
								>7 days</td
							>
						</tr>
					</tbody>
				</table>

				<h3>2.2 Functional Cookies (Optional)</h3>
				<p>These cookies enhance your experience but are not essential:</p>
				<table class="min-w-full border border-neutral-300 dark:border-neutral-700 mt-4">
					<thead>
						<tr class="bg-neutral-100 dark:bg-neutral-800">
							<th
								class="border border-neutral-300 dark:border-neutral-700 px-4 py-2 text-left"
								>Cookie Name</th
							>
							<th
								class="border border-neutral-300 dark:border-neutral-700 px-4 py-2 text-left"
								>Purpose</th
							>
							<th
								class="border border-neutral-300 dark:border-neutral-700 px-4 py-2 text-left"
								>Duration</th
							>
						</tr>
					</thead>
					<tbody>
						<tr>
							<td class="border border-neutral-300 dark:border-neutral-700 px-4 py-2"
								><code>theme_preference</code></td
							>
							<td class="border border-neutral-300 dark:border-neutral-700 px-4 py-2"
								>Remember light/dark mode</td
							>
							<td class="border border-neutral-300 dark:border-neutral-700 px-4 py-2"
								>1 year</td
							>
						</tr>
						<tr>
							<td class="border border-neutral-300 dark:border-neutral-700 px-4 py-2"
								><code>cookie_consent</code></td
							>
							<td class="border border-neutral-300 dark:border-neutral-700 px-4 py-2"
								>Remember cookie preferences</td
							>
							<td class="border border-neutral-300 dark:border-neutral-700 px-4 py-2"
								>1 year</td
							>
						</tr>
					</tbody>
				</table>

				<h3>2.3 Analytics Cookies (Privacy-Focused)</h3>
				<p>
					We use Umami, a privacy-focused analytics solution that does not use cookies or track
					personal data. Umami collects only anonymized, aggregated page view data and does not
					store any information on your device.
				</p>
				<p>
					No analytics cookies are set. All analytics data is processed without identifying
					individual users.
				</p>

				<h2>3. Third-Party Cookies</h2>
				<p>Some third-party services we use may also set cookies:</p>
				<ul>
					<li>
						<strong>Stripe:</strong> Payment processing (essential for checkout)
					</li>
				</ul>
				<p>
					Stripe has its own privacy policy. We recommend reviewing it: <a
						href="https://stripe.com/privacy"
						target="_blank"
						rel="noopener noreferrer">Stripe Privacy Policy</a
					>.
				</p>

				<h2>4. Managing Your Cookie Preferences</h2>
				<h3>4.1 Cookie Banner</h3>
				<p>
					When you first visit Board of One, you'll see a cookie consent banner. You can choose to:
				</p>
				<ul>
					<li>Accept all cookies</li>
					<li>Accept only essential cookies</li>
					<li>Customize your preferences</li>
				</ul>

				<h3>4.2 Browser Settings</h3>
				<p>
					You can also manage cookies through your browser settings. Most browsers allow you to:
				</p>
				<ul>
					<li>View and delete cookies</li>
					<li>Block cookies from specific websites</li>
					<li>Block all third-party cookies</li>
					<li>Delete all cookies when you close your browser</li>
				</ul>
				<p>
					Note: Disabling essential cookies may prevent you from using certain features of the
					Service.
				</p>

				<h3>4.3 Update Preferences</h3>
				<p>
					You can update your cookie preferences at any time by clicking the "Cookie Settings" link
					in the footer or visiting <a href="/settings/privacy">Settings → Privacy</a>.
				</p>

				<h2>5. Do Not Track</h2>
				<p>
					Some browsers include a "Do Not Track" (DNT) feature. We respect DNT signals and will not
					load analytics cookies if DNT is enabled.
				</p>

				<h2>6. Changes to This Policy</h2>
				<p>
					We may update this Cookie Policy from time to time. Changes will be reflected in the "Last
					Updated" date above. Continued use of the Service after changes constitutes acceptance of
					the updated policy.
				</p>

				<h2>7. Contact Us</h2>
				<p>
					For questions about our use of cookies, contact us at: <a
						href="mailto:privacy@boardof.one">privacy@boardof.one</a
					>
				</p>
			</div>
		</div>
	</main>

	<Footer />
</div>

<style>
	:global(.prose h2) {
		font-size: 1.5rem;
		font-weight: 700;
		margin-top: 3rem;
		margin-bottom: 1rem;
		color: var(--color-textPrimary);
	}

	:global(.prose h3) {
		font-size: 1.25rem;
		font-weight: 600;
		margin-top: 2rem;
		margin-bottom: 0.75rem;
		color: var(--color-textPrimary);
	}

	:global(.prose p) {
		margin-bottom: 1rem;
		line-height: 1.625;
		color: var(--color-textSecondary);
	}

	:global(.prose ul) {
		list-style-type: disc;
		padding-left: 1.5rem;
		margin-bottom: 1rem;
		color: var(--color-textSecondary);
	}

	:global(.prose li) {
		margin-bottom: 0.5rem;
	}

	:global(.prose a) {
		color: var(--color-brand-600, #00a594);
		text-decoration: underline;
	}

	:global(.prose a:hover) {
		text-decoration-style: solid;
	}

	:global(.dark .prose a) {
		color: var(--color-brand-400, #1ad3c0);
	}

	:global(.prose table) {
		width: 100%;
		margin-top: 1.5rem;
		margin-bottom: 1.5rem;
		font-size: 0.875rem;
	}

	:global(.prose th) {
		font-weight: 600;
	}

	:global(.prose code) {
		background-color: var(--color-neutral-100, #f1f4f5);
		padding: 0.25rem 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.875rem;
		font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace;
	}

	:global(.dark .prose code) {
		background-color: var(--color-neutral-800, #2a3b40);
	}
</style>
