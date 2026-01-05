<script lang="ts">
	/**
	 * Privacy Policy Page
	 */
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';

	const lastUpdated = '2025-12-29';
</script>

<svelte:head>
	<title>Privacy Policy - Board of One</title>
</svelte:head>

<div class="min-h-screen flex flex-col">
	<Header />

	<main class="flex-grow bg-white dark:bg-neutral-900 py-16">
		<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
			<h1 class="text-4xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">
				Privacy Policy
			</h1>
			<p class="text-neutral-600 dark:text-neutral-400 mb-12">
				Last updated: {lastUpdated}
			</p>

			<div class="prose prose-neutral dark:prose-invert max-w-none">
				<h2>1. Introduction</h2>
				<p>
					Sico Software Ltd, trading as Board of One ("we", "our", or "us"), is committed to protecting your privacy. This Privacy
					Policy explains how we collect, use, disclose, and safeguard your information when you use
					our Service.
				</p>
				<p>
					This policy complies with the UK General Data Protection Regulation (UK GDPR) and the Data
					Protection Act 2018.
				</p>

				<h2>2. Information We Collect</h2>
				<h3>2.1 Information You Provide</h3>
				<ul>
					<li><strong>Account Information:</strong> Email address, name, password (encrypted)</li>
					<li>
						<strong>Profile Information:</strong> Business context, preferences, subscription tier
					</li>
					<li>
						<strong>Decision Submissions:</strong> Questions and decisions you submit for deliberation
					</li>
					<li><strong>Payment Information:</strong> Billing details (processed via Stripe)</li>
				</ul>

				<h3>2.2 Automatically Collected Information</h3>
				<ul>
					<li><strong>Usage Data:</strong> Pages visited, features used, session duration</li>
					<li>
						<strong>Technical Data:</strong> IP address, browser type, device information, operating
						system
					</li>
					<li><strong>Cookies:</strong> See our <a href="/legal/cookies">Cookie Policy</a></li>
				</ul>

				<h3>2.3 Our Minimal Tracking Stance</h3>
				<p>
					We believe in collecting only what you consciously provide. Our approach to data collection is:
				</p>
				<ul>
					<li><strong>User-Provided Data:</strong> We collect information you explicitly give us (business context, decisions, preferences)</li>
					<li><strong>No Subversive Extraction:</strong> We do not use hidden trackers, fingerprinting, or surveillance techniques to gather data about you</li>
					<li><strong>Privacy-Focused Analytics:</strong> We use Umami, which collects only anonymized page views without cookies or personal identifiers</li>
					<li><strong>No Advertising Profiles:</strong> We do not build profiles about you for advertising purposes or share data with ad networks</li>
				</ul>

				<h3>2.4 AI-Generated Content</h3>
				<ul>
					<li>
						<strong>Deliberation Transcripts:</strong> Expert contributions, facilitator summaries,
						synthesis reports
					</li>
					<li>
						<strong>Analytics:</strong> Convergence scores, session duration (admin-only, not shared
						with end users)
					</li>
				</ul>

				<h2>3. How We Use Your Information</h2>
				<p>We use your information to:</p>
				<ul>
					<li>Provide, maintain, and improve the Service</li>
					<li>Process your deliberations and generate recommendations</li>
					<li>Manage your account and subscriptions</li>
					<li>Send service-related communications (session updates, account notifications)</li>
					<li>Respond to your inquiries and support requests</li>
					<li>
						Analyze usage patterns to improve our deliberation model (anonymized and aggregated data
						only)
					</li>
					<li>Comply with legal obligations</li>
				</ul>

				<h2>4. Legal Basis for Processing (GDPR)</h2>
				<p>We process your personal data under the following legal bases:</p>
				<ul>
					<li>
						<strong>Contract Performance:</strong> To provide the Service you've subscribed to
					</li>
					<li>
						<strong>Legitimate Interests:</strong> To improve our Service and prevent fraud
					</li>
					<li>
						<strong>Consent:</strong> For marketing communications (opt-in only)
					</li>
					<li>
						<strong>Legal Obligation:</strong> To comply with tax, accounting, and regulatory
						requirements
					</li>
				</ul>

				<h2>5. Data Sharing and Disclosure</h2>
				<h3>5.1 Third-Party Service Providers</h3>
				<p>We share data with trusted service providers who assist us in operating the Service:</p>
				<ul>
					<li><strong>Anthropic (Claude API):</strong> AI deliberation processing</li>
					<li><strong>Voyage AI:</strong> Semantic embeddings for research cache</li>
					<li><strong>SuperTokens:</strong> Authentication</li>
					<li><strong>Neon:</strong> Database hosting</li>
					<li><strong>Stripe:</strong> Payment processing</li>
					<li>
						<strong>DigitalOcean:</strong> Cloud infrastructure and file storage
					</li>
				</ul>
				<p>These providers are contractually obligated to protect your data and use it only as instructed.</p>

				<h3>5.2 We Do NOT Share</h3>
				<ul>
					<li>Your decision submissions with other users (unless you explicitly share them)</li>
					<li>Personal data with advertisers or marketers</li>
					<li>Deliberation transcripts with third parties (except service providers necessary to operate the Service)</li>
				</ul>

				<h3>5.3 Protection Against Data Sale</h3>
				<p>
					We commit to protecting your data from commercial exploitation:
				</p>
				<ul>
					<li><strong>No Data Brokering:</strong> We will never sell, rent, or trade your personal data or deliberation content to third parties</li>
					<li><strong>Paying User Protection:</strong> If you are a paying customer, your data will never be sold or monetized beyond providing the Service, even in the event of company acquisition or change of ownership</li>
					<li><strong>No AI Training Data:</strong> Your deliberation content is not used to train external AI models</li>
					<li><strong>Acquisition Safeguard:</strong> In the event of acquisition, your data protections transfer with your account and cannot be weakened without your explicit consent</li>
				</ul>

				<h3>5.4 Legal Disclosures</h3>
				<p>
					We may disclose your information if required by law, court order, or government request,
					or to protect our rights, property, or safety.
				</p>

				<h2>6. Data Retention</h2>
				<ul>
					<li>
						<strong>Account Data:</strong> Retained while your account is active
					</li>
					<li>
						<strong>Deliberation Data:</strong> Retained for 1 year by default (configurable in settings:
						1 year, 2 years, or indefinite)
					</li>
					<li>
						<strong>Anonymized Analytics:</strong> Retained indefinitely for research and improvement
					</li>
					<li>
						<strong>Deleted Accounts:</strong> Personal data anonymized within 30 days of account deletion
						request
					</li>
				</ul>

				<h2>7. Your Rights (GDPR)</h2>
				<p>You have the right to:</p>
				<ul>
					<li>
						<strong>Access:</strong> Request a copy of your personal data
						<a href="/settings/privacy">(Settings → Privacy → Export Data)</a>
					</li>
					<li>
						<strong>Rectification:</strong> Correct inaccurate or incomplete data
						<a href="/settings/account">(Settings → Account)</a>
					</li>
					<li>
						<strong>Erasure ("Right to be Forgotten"):</strong> Request deletion of your account and
						personal data <a href="/settings/privacy">(Settings → Privacy → Delete Account)</a>
					</li>
					<li>
						<strong>Data Portability:</strong> Receive your data in a machine-readable format (JSON export)
					</li>
					<li>
						<strong>Objection:</strong> Object to processing based on legitimate interests
					</li>
					<li>
						<strong>Restriction:</strong> Request temporary restriction of processing
					</li>
					<li>
						<strong>Withdraw Consent:</strong> For marketing communications (unsubscribe link in emails)
					</li>
				</ul>
				<p>
					To exercise these rights, contact us at <a href="mailto:privacy@boardof.one"
						>privacy@boardof.one</a
					> or use the settings page.
				</p>

				<h2>8. Data Security</h2>
				<p>We implement industry-standard security measures to protect your data:</p>
				<ul>
					<li>Encryption in transit (TLS/SSL) and at rest (AES-256)</li>
					<li>Secure authentication (SuperTokens with JWT tokens)</li>
					<li>Regular security audits and penetration testing</li>
					<li>Access controls and role-based permissions</li>
					<li>Automated backups with encryption</li>
				</ul>
				<p>
					However, no method of transmission or storage is 100% secure. We cannot guarantee absolute
					security.
				</p>

				<h2>9. International Data Transfers</h2>
				<p>
					Your data may be transferred to and processed in countries outside the UK/EEA where our
					service providers operate (e.g., United States for Anthropic Claude API). We ensure
					adequate safeguards through:
				</p>
				<ul>
					<li>Standard Contractual Clauses (SCCs) approved by the UK ICO</li>
					<li>Adequacy decisions (where applicable)</li>
					<li>Compliance with GDPR transfer requirements</li>
				</ul>

				<h2>10. Children's Privacy</h2>
				<p>
					The Service is not intended for users under 18 years of age. We do not knowingly collect
					personal data from children. If you believe we have inadvertently collected data from a
					child, contact us immediately.
				</p>

				<h2>11. Changes to This Policy</h2>
				<p>
					We may update this Privacy Policy from time to time. We will notify you of material
					changes via email or through the Service. Continued use after changes constitutes
					acceptance of the updated policy.
				</p>

				<h2>12. Contact and Complaints</h2>
				<p>
					For privacy-related questions or concerns, contact us at: <a
						href="mailto:privacy@boardof.one">privacy@boardof.one</a
					>
				</p>
				<p>
					If you are not satisfied with our response, you have the right to lodge a complaint with
					the UK Information Commissioner's Office (ICO): <a
						href="https://ico.org.uk/make-a-complaint/"
						target="_blank"
						rel="noopener noreferrer">https://ico.org.uk/make-a-complaint/</a
					>
				</p>

				<h2>13. Data Protection Officer</h2>
				<p>
					For data protection inquiries, contact our Data Protection Officer at: <a
						href="mailto:dpo@boardof.one">dpo@boardof.one</a
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
</style>
