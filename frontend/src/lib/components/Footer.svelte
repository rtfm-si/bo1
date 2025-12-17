<script lang="ts">
	/**
	 * Footer Component - Reusable footer with legal links and navigation
	 */
	const currentYear = new Date().getFullYear();

	const footerSections = [
		{
			title: 'Product',
			links: [
				{ label: 'How It Works', href: '/#how-it-works' },
				{ label: 'Features', href: '/#features' },
			],
		},
		{
			title: 'Legal',
			links: [
				{ label: 'Terms of Service', href: '/legal/terms' },
				{ label: 'Privacy Policy', href: '/legal/privacy' },
				{ label: 'Cookie Policy', href: '/legal/cookies' },
			],
		},
		{
			title: 'Support',
			links: [{ label: 'Help Center', href: '/help' }],
		},
	];

	const socialLinks = [
		{ label: 'Twitter', href: 'https://twitter.com/boardofone', icon: 'twitter' },
		{ label: 'LinkedIn', href: 'https://linkedin.com/company/boardofone', icon: 'linkedin' },
		{ label: 'GitHub', href: 'https://github.com/boardofone', icon: 'github' },
	];
</script>

<footer class="bg-neutral-50 dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-800">
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
		<!-- Main Footer Content -->
		<div class="grid grid-cols-2 md:grid-cols-3 gap-8 mb-8">
			{#each footerSections as section}
				<div>
					<h3
						class="text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wider mb-4"
					>
						{section.title}
					</h3>
					<ul class="space-y-3">
						{#each section.links as link}
							<li>
								<a
									href={link.href}
									class="text-neutral-600 dark:text-neutral-400 hover:text-brand-600 dark:hover:text-brand-400 transition-colors text-sm"
								>
									{link.label}
								</a>
							</li>
						{/each}
					</ul>
				</div>
			{/each}
		</div>

		<!-- Bottom Bar -->
		<div
			class="pt-8 border-t border-neutral-200 dark:border-neutral-800 flex flex-col md:flex-row justify-between items-center gap-4"
		>
			<!-- Logo & Copyright -->
			<div class="flex items-center gap-3">
				<img src="/logo.svg" alt="Board of One" class="h-8 w-8" />
				<p class="text-sm text-neutral-600 dark:text-neutral-400">
					© {currentYear} Board of One. All rights reserved.
				</p>
			</div>

			<!-- Social Links -->
			<div class="flex items-center gap-4">
				{#each socialLinks as social}
					<a
						href={social.href}
						target="_blank"
						rel="noopener noreferrer"
						aria-label={social.label}
						class="text-neutral-600 dark:text-neutral-400 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
					>
						{#if social.icon === 'twitter'}
							<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
								<path
									d="M23 3a10.9 10.9 0 01-3.14 1.53 4.48 4.48 0 00-7.86 3v1A10.66 10.66 0 013 4s-4 9 5 13a11.64 11.64 0 01-7 2c9 5 20 0 20-11.5a4.5 4.5 0 00-.08-.83A7.72 7.72 0 0023 3z"
								/>
							</svg>
						{:else if social.icon === 'linkedin'}
							<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
								<path
									d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"
								/>
							</svg>
						{:else if social.icon === 'github'}
							<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
								<path
									d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
								/>
							</svg>
						{/if}
					</a>
				{/each}
			</div>
		</div>
	</div>
</footer>
