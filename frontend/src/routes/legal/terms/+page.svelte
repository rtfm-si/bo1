<script lang="ts">
	/**
	 * Terms of Service Page
	 */
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';

	const lastUpdated = '2025-01-19';
</script>

<svelte:head>
	<title>Terms of Service - Board of One</title>
</svelte:head>

<div class="min-h-screen flex flex-col">
	<Header />

	<main class="flex-grow bg-white dark:bg-neutral-900 py-16">
		<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
			<h1 class="text-4xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">
				Terms of Service
			</h1>
			<p class="text-neutral-600 dark:text-neutral-400 mb-12">
				Last updated: {lastUpdated}
			</p>

			<div class="prose prose-neutral dark:prose-invert max-w-none">
				<h2>1. Acceptance of Terms</h2>
				<p>
					By accessing or using Board of One ("the Service"), you agree to be bound by these Terms
					of Service ("Terms"). If you do not agree to these Terms, you may not access or use the
					Service.
				</p>

				<h2>2. Description of Service</h2>
				<p>
					Board of One provides an AI-powered deliberation platform that helps users make better
					decisions through structured multi-perspective analysis. The Service uses proprietary
					algorithms to simulate expert panel discussions and synthesize recommendations.
				</p>

				<h2>3. User Accounts</h2>
				<h3>3.1 Account Creation</h3>
				<p>
					To access certain features of the Service, you must create an account. You agree to
					provide accurate, current, and complete information during the registration process.
				</p>
				<h3>3.2 Account Security</h3>
				<p>
					You are responsible for maintaining the security of your account credentials. You must
					notify us immediately of any unauthorized access to your account.
				</p>
				<h3>3.3 Account Termination</h3>
				<p>
					We reserve the right to suspend or terminate your account at any time for violations of
					these Terms or for any other reason at our sole discretion.
				</p>

				<h2>4. Acceptable Use</h2>
				<p>You agree not to use the Service to:</p>
				<ul>
					<li>Violate any applicable laws or regulations</li>
					<li>Infringe upon the intellectual property rights of others</li>
					<li>
						Transmit harmful, offensive, or unlawful content (including but not limited to:
						harassment, hate speech, illegal activities)
					</li>
					<li>Attempt to reverse engineer, decompile, or extract our proprietary algorithms</li>
					<li>Interfere with or disrupt the Service or servers</li>
					<li>Use the Service for unauthorized commercial purposes</li>
				</ul>

				<h2>5. Intellectual Property</h2>
				<h3>5.1 Our IP</h3>
				<p>
					The Service, including all content, features, algorithms, and functionality, is owned by
					Board of One and is protected by copyright, trademark, and other intellectual property
					laws.
				</p>
				<h3>5.2 Your Content</h3>
				<p>
					You retain ownership of any content you submit to the Service ("User Content"). By
					submitting User Content, you grant us a worldwide, non-exclusive, royalty-free license to
					use, reproduce, and analyze your content solely for the purpose of providing the Service.
				</p>
				<h3>5.3 Proprietary Deliberation Model</h3>
				<p>
					Our deliberation mechanics, persona weighting algorithms, balancer logic, convergence
					detection systems, and all related intellectual property are proprietary and confidential.
					Any attempt to reverse engineer, extract, or replicate these systems is strictly
					prohibited.
				</p>

				<h2>6. Subscription and Payment</h2>
				<h3>6.1 Pricing</h3>
				<p>
					Certain features of the Service require a paid subscription. Current pricing is available
					on our website and may change with 30 days' notice.
				</p>
				<h3>6.2 Billing</h3>
				<p>
					Subscriptions are billed in advance on a monthly or annual basis. You authorize us to
					charge your payment method for all fees incurred.
				</p>
				<h3>6.3 Refunds</h3>
				<p>
					Refunds are provided at our discretion. Unused subscription time is not refundable except
					as required by law.
				</p>
				<h3>6.4 Free Trial</h3>
				<p>
					We may offer a free trial period. You will not be charged until the trial period ends. You
					may cancel before the trial ends to avoid charges.
				</p>

				<h2>7. Data and Privacy</h2>
				<p>
					Your use of the Service is also governed by our <a href="/legal/privacy"
						>Privacy Policy</a
					>, which is incorporated into these Terms by reference. Please review our Privacy Policy
					to understand how we collect, use, and protect your data.
				</p>

				<h2>8. Limitation of Liability</h2>
				<p>
					THE SERVICE IS PROVIDED "AS IS" WITHOUT WARRANTIES OF ANY KIND. TO THE MAXIMUM EXTENT
					PERMITTED BY LAW, BOARD OF ONE SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL,
					CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR ANY LOSS OF PROFITS OR REVENUES.
				</p>

				<h2>9. Indemnification</h2>
				<p>
					You agree to indemnify and hold harmless Board of One from any claims, damages, or
					expenses (including legal fees) arising from your use of the Service or violation of these
					Terms.
				</p>

				<h2>10. Disclaimer of Advice</h2>
				<p>
					Board of One provides decision support tools and is NOT a substitute for professional
					advice. The Service generates recommendations based on AI analysis and should not be
					considered financial, legal, medical, or other professional advice. You are solely
					responsible for your decisions and their outcomes.
				</p>

				<h2>11. Changes to Terms</h2>
				<p>
					We reserve the right to modify these Terms at any time. We will notify users of material
					changes via email or through the Service. Continued use of the Service after changes
					constitutes acceptance of the modified Terms.
				</p>

				<h2>12. Governing Law</h2>
				<p>
					These Terms are governed by the laws of England and Wales. Any disputes arising from these
					Terms or the Service shall be resolved in the courts of England and Wales.
				</p>

				<h2>13. Contact Information</h2>
				<p>
					For questions about these Terms, please contact us at: <a href="mailto:legal@boardof.one"
						>legal@boardof.one</a
					>
				</p>
			</div>
		</div>
	</main>

	<Footer />
</div>

<style>
	:global(.prose h2) {
		@apply text-2xl font-bold text-neutral-900 dark:text-neutral-100 mt-12 mb-4;
	}

	:global(.prose h3) {
		@apply text-xl font-semibold text-neutral-900 dark:text-neutral-100 mt-8 mb-3;
	}

	:global(.prose p) {
		@apply text-neutral-700 dark:text-neutral-300 mb-4 leading-relaxed;
	}

	:global(.prose ul) {
		@apply list-disc pl-6 mb-4 text-neutral-700 dark:text-neutral-300;
	}

	:global(.prose li) {
		@apply mb-2;
	}

	:global(.prose a) {
		@apply text-brand-600 dark:text-brand-400 hover:underline;
	}
</style>
