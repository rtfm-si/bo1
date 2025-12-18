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
				{ label: 'Examples', href: '/examples' },
			],
		},
		{
			title: 'Company',
			links: [
				{ label: 'About', href: '/about' },
				{ label: 'Blog', href: '/blog' },
				{ label: 'Contact', href: 'mailto:hello@boardofone.com' },
			],
		},
		{
			title: 'Support',
			links: [
				{ label: 'Help Center', href: '/help' },
				{ label: 'Status', href: '/status' },
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
	];

</script>

<footer class="bg-neutral-50 dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-800">
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
		<!-- Main Footer Content -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
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
					© {currentYear} Sico Software Ltd. All rights reserved.
				</p>
			</div>

		</div>
	</div>
</footer>
