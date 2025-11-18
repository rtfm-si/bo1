<script lang="ts">
	/**
	 * Design System Demo Page
	 * Showcases all components, themes, and new progressive disclosure patterns
	 */

	import {
		Button,
		Card,
		Input,
		Badge,
		Alert,
		ProgressBar,
		Spinner,
		Avatar,
		Tooltip,
		Modal,
		Dropdown,
		Tabs,
		Toast,
		InsightFlag,
		ContributionCard,
	} from '$lib/components/ui';
	import type { DropdownItem, Tab, Persona } from '$lib/components/ui';
	import ThemeSwitcher from '$lib/components/ThemeSwitcher.svelte';
	import { colors } from '$lib/design/tokens';

	// State
	let inputValue = '';
	let emailValue = '';
	let passwordValue = '';
	let errorMessage = '';
	let showSuccessAlert = true;
	let showWarningAlert = true;
	let loading = false;

	// Progress bar demo
	let progress = 65;
	let progressInterval: ReturnType<typeof setInterval> | null = null;

	function startProgressDemo() {
		if (progressInterval) return;
		progress = 0;
		progressInterval = setInterval(() => {
			progress += 5;
			if (progress >= 100) {
				progress = 100;
				if (progressInterval) clearInterval(progressInterval);
				progressInterval = null;
			}
		}, 200);
	}

	// Modal demo
	let showModal = false;

	// Dropdown demo
	const dropdownItems: DropdownItem[] = [
		{ value: 'light', label: 'Light Theme', icon: '☀️' },
		{ value: 'dark', label: 'Dark Theme', icon: '🌙' },
		{ value: 'ocean', label: 'Ocean Theme', icon: '🌊' },
	];
	let selectedTheme = 'light';

	// Tabs demo
	const tabs: Tab[] = [
		{ id: 'overview', label: 'Overview', icon: '📊' },
		{ id: 'contributions', label: 'Contributions', icon: '💬' },
		{ id: 'synthesis', label: 'Synthesis', icon: '✨' },
	];
	let activeTab = 'overview';

	// Toast demo
	let toasts: Array<{ id: number; type: 'success' | 'error' | 'warning' | 'info'; message: string }> =
		[];
	let toastId = 0;

	function showToast(
		type: 'success' | 'error' | 'warning' | 'info',
		message: string
	) {
		const id = toastId++;
		toasts = [...toasts, { id, type, message }];
	}

	function removeToast(id: number) {
		toasts = toasts.filter((t) => t.id !== id);
	}

	// Insight flags demo
	let insights = [
		{
			id: 1,
			type: 'risk' as const,
			message: 'Market volatility detected in Q4 projections',
		},
		{
			id: 2,
			type: 'opportunity' as const,
			message: 'Strategic alignment with emerging AI trends',
		},
	];

	function removeInsight(id: number) {
		insights = insights.filter((i) => i.id !== id);
	}

	// Contribution card demo
	const samplePersona: Persona = {
		name: 'Maria Chen',
		code: 'MARIA',
		expertise: 'Marketing Strategy & Consumer Behavior',
	};

	const sampleTimestamp = new Date(Date.now() - 1000 * 60 * 15); // 15 min ago

	// Form validation
	function handleButtonClick() {
		console.log('Button clicked!');
	}

	async function handleLoadingButton() {
		loading = true;
		await new Promise((resolve) => setTimeout(resolve, 2000));
		loading = false;
	}

	function validateForm() {
		if (!emailValue.includes('@')) {
			errorMessage = 'Please enter a valid email';
		} else {
			errorMessage = '';
		}
	}

	// Color palette helper
	type ColorShade = {
		shade: string;
		hex: string;
	};

	function getColorShades(colorName: keyof typeof colors): ColorShade[] {
		const colorObj = colors[colorName];
		return Object.entries(colorObj).map(([shade, hex]) => ({
			shade,
			hex: hex as string,
		}));
	}
</script>

<svelte:head>
	<title>Design System Demo - Board of One</title>
</svelte:head>

<div class="min-h-screen p-8" style="background-color: var(--color-background);">
	<!-- Toast Container -->
	<div class="fixed top-4 right-4 z-[1100] space-y-2 max-w-md">
		{#each toasts as toast (toast.id)}
			<Toast
				type={toast.type}
				message={toast.message}
				on:dismiss={() => removeToast(toast.id)}
			/>
		{/each}
	</div>

	<!-- Header -->
	<header class="max-w-7xl mx-auto mb-12">
		<div class="flex items-center justify-between mb-4">
			<div class="flex items-center gap-3">
				<h1 class="text-4xl font-bold text-neutral-900 dark:text-neutral-100">
					Design System Demo
				</h1>
				<Badge variant="info">v2.0</Badge>
			</div>
			<ThemeSwitcher />
		</div>
		<p class="text-neutral-600 dark:text-neutral-400">
			Showcase of all design system components with teal brand color (#00C8B3), progressive
			disclosure patterns, and three themes.
		</p>
	</header>

	<div class="max-w-7xl mx-auto space-y-12">
		<!-- Color Palette Section -->
		<section>
			<h2 class="text-2xl font-bold mb-6 text-neutral-900 dark:text-neutral-100">
				Color Palette
			</h2>
			<p class="text-neutral-600 dark:text-neutral-400 mb-6">
				Based on brand color <code
					class="px-2 py-1 bg-brand-100 dark:bg-brand-900 text-brand-700 dark:text-brand-300 rounded"
					>#00C8B3</code
				>
				(teal) with complementary coral accent and harmonious semantic colors.
			</p>

			<div class="space-y-6">
				<!-- Brand Colors -->
				<div>
					<h3 class="text-lg font-semibold mb-3 text-neutral-800 dark:text-neutral-200">
						Brand (Teal)
					</h3>
					<div class="grid grid-cols-11 gap-2">
						{#each getColorShades('brand') as { shade, hex }}
							<div class="flex flex-col items-center">
								<div
									class="w-full h-16 rounded-md shadow-sm border border-neutral-200 dark:border-neutral-700"
									style="background-color: {hex}"
								></div>
								<span class="text-xs text-neutral-600 dark:text-neutral-400 mt-1">
									{shade}
								</span>
								<span
									class="text-xs font-mono text-neutral-500 dark:text-neutral-500"
								>
									{hex}
								</span>
							</div>
						{/each}
					</div>
				</div>

				<!-- Accent Colors -->
				<div>
					<h3 class="text-lg font-semibold mb-3 text-neutral-800 dark:text-neutral-200">
						Accent (Coral)
					</h3>
					<div class="grid grid-cols-11 gap-2">
						{#each getColorShades('accent') as { shade, hex }}
							<div class="flex flex-col items-center">
								<div
									class="w-full h-16 rounded-md shadow-sm border border-neutral-200 dark:border-neutral-700"
									style="background-color: {hex}"
								></div>
								<span class="text-xs text-neutral-600 dark:text-neutral-400 mt-1">
									{shade}
								</span>
								<span
									class="text-xs font-mono text-neutral-500 dark:text-neutral-500"
								>
									{hex}
								</span>
							</div>
						{/each}
					</div>
				</div>

				<!-- Semantic Colors Grid -->
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
					{#each (['success', 'warning', 'error', 'info'] as const) as colorName}
						<Card variant="bordered">
							<h4
								class="text-sm font-semibold mb-2 text-neutral-800 dark:text-neutral-200 capitalize"
							>
								{colorName}
							</h4>
							<div class="space-y-1">
								{#each getColorShades(colorName) as { shade, hex }}
									<div class="flex items-center gap-2">
										<div
											class="w-8 h-8 rounded border border-neutral-200 dark:border-neutral-700"
											style="background-color: {hex}"
										></div>
										<span class="text-xs font-mono text-neutral-600 dark:text-neutral-400">
											{shade}: {hex}
										</span>
									</div>
								{/each}
							</div>
						</Card>
					{/each}
				</div>
			</div>
		</section>

		<!-- Progressive Disclosure Components -->
		<section>
			<h2 class="text-2xl font-bold mb-6 text-neutral-900 dark:text-neutral-100">
				Progressive Disclosure
			</h2>

			<div class="space-y-8">
				<!-- Progress Bars -->
				<div>
					<h3 class="text-lg font-semibold mb-4 text-neutral-800 dark:text-neutral-200">
						Progress Bars
					</h3>
					<div class="space-y-4 max-w-md">
						<div>
							<div class="flex items-center justify-between mb-2">
								<span class="text-sm text-neutral-600 dark:text-neutral-400">
									Brand variant
								</span>
								<Button size="sm" variant="ghost" on:click={startProgressDemo}>
									Animate
								</Button>
							</div>
							<ProgressBar value={progress} variant="brand" showLabel />
						</div>
						<ProgressBar value={75} variant="accent" />
						<ProgressBar value={100} variant="success" size="sm" />
						<ProgressBar value={50} variant="brand" size="lg" animated={false} />
						<div>
							<span class="text-sm text-neutral-600 dark:text-neutral-400 block mb-2">
								Indeterminate (loading)
							</span>
							<ProgressBar indeterminate variant="brand" />
						</div>
					</div>
				</div>

				<!-- Spinners -->
				<div>
					<h3 class="text-lg font-semibold mb-4 text-neutral-800 dark:text-neutral-200">
						Spinners
					</h3>
					<div class="flex items-center gap-6">
						<div class="text-center">
							<Spinner size="xs" />
							<p class="text-xs text-neutral-600 dark:text-neutral-400 mt-2">XS</p>
						</div>
						<div class="text-center">
							<Spinner size="sm" />
							<p class="text-xs text-neutral-600 dark:text-neutral-400 mt-2">SM</p>
						</div>
						<div class="text-center">
							<Spinner size="md" />
							<p class="text-xs text-neutral-600 dark:text-neutral-400 mt-2">MD</p>
						</div>
						<div class="text-center">
							<Spinner size="lg" variant="accent" />
							<p class="text-xs text-neutral-600 dark:text-neutral-400 mt-2">LG</p>
						</div>
						<div class="text-center">
							<Spinner size="xl" variant="neutral" />
							<p class="text-xs text-neutral-600 dark:text-neutral-400 mt-2">XL</p>
						</div>
					</div>
				</div>

				<!-- Avatars -->
				<div>
					<h3 class="text-lg font-semibold mb-4 text-neutral-800 dark:text-neutral-200">
						Avatars
					</h3>
					<div class="flex items-center gap-4">
						<Avatar name="Maria Chen" size="xs" />
						<Avatar name="Zara Thompson" size="sm" status="online" />
						<Avatar name="Tariq Rahman" size="md" status="typing" />
						<Avatar name="John Doe" size="lg" status="offline" />
						<Avatar name="Board of One" size="xl" />
					</div>
				</div>

				<!-- Tooltips -->
				<div>
					<h3 class="text-lg font-semibold mb-4 text-neutral-800 dark:text-neutral-200">
						Tooltips
					</h3>
					<div class="flex gap-4">
						<Tooltip text="This is a top tooltip" position="top">
							<Button variant="ghost">Hover (Top)</Button>
						</Tooltip>
						<Tooltip text="This is a bottom tooltip" position="bottom">
							<Button variant="ghost">Hover (Bottom)</Button>
						</Tooltip>
						<Tooltip text="Light variant tooltip" position="top" variant="light">
							<Button variant="ghost">Light Tooltip</Button>
						</Tooltip>
					</div>
				</div>

				<!-- Insight Flags -->
				<div>
					<h3 class="text-lg font-semibold mb-4 text-neutral-800 dark:text-neutral-200">
						Insight Flags
					</h3>
					<div class="space-y-3 max-w-2xl">
						{#each insights as insight (insight.id)}
							<InsightFlag
								type={insight.type}
								message={insight.message}
								on:dismiss={() => removeInsight(insight.id)}
							/>
						{/each}
						<InsightFlag
							type="tension"
							message="Conflicting priorities between short-term revenue and long-term growth"
							dismissable={false}
							pulse
						/>
						<InsightFlag
							type="alignment"
							message="Strong consensus emerging around customer-first approach"
							dismissable={false}
						/>
					</div>
				</div>

				<!-- Contribution Card -->
				<div>
					<h3 class="text-lg font-semibold mb-4 text-neutral-800 dark:text-neutral-200">
						Contribution Card
					</h3>
					<div class="max-w-2xl">
						<ContributionCard
							persona={samplePersona}
							content="Based on consumer behavior analysis, I recommend a phased rollout strategy. Start with early adopters (tech-savvy millennials) to build social proof, then expand to broader demographics. This approach reduces market risk while maximizing word-of-mouth amplification."
							timestamp={sampleTimestamp}
							confidence="high"
						>
							<div slot="actions" class="flex gap-2">
								<Button size="sm" variant="ghost">View Analysis</Button>
								<Button size="sm" variant="ghost">Ask Follow-up</Button>
							</div>
						</ContributionCard>
					</div>
				</div>
			</div>
		</section>

		<!-- Interactive Components -->
		<section>
			<h2 class="text-2xl font-bold mb-6 text-neutral-900 dark:text-neutral-100">
				Interactive Components
			</h2>

			<div class="space-y-8">
				<!-- Modal -->
				<div>
					<h3 class="text-lg font-semibold mb-4 text-neutral-800 dark:text-neutral-200">
						Modal
					</h3>
					<Button on:click={() => (showModal = true)}>Open Modal</Button>

					<Modal bind:open={showModal} title="Session Details" size="md">
						<div class="space-y-4">
							<p class="text-neutral-700 dark:text-neutral-300">
								This is a modal dialog demonstrating focus trap, ESC to close, and
								scroll lock.
							</p>
							<div class="grid grid-cols-2 gap-4">
								<div>
									<p class="text-sm font-semibold text-neutral-600 dark:text-neutral-400">
										Session ID
									</p>
									<p class="text-neutral-900 dark:text-neutral-100">
										session-abc123
									</p>
								</div>
								<div>
									<p class="text-sm font-semibold text-neutral-600 dark:text-neutral-400">
										Status
									</p>
									<Badge variant="success">Active</Badge>
								</div>
							</div>
						</div>

						<div slot="footer" class="flex justify-end gap-2">
							<Button variant="ghost" on:click={() => (showModal = false)}>
								Cancel
							</Button>
							<Button variant="brand" on:click={() => (showModal = false)}>
								Confirm
							</Button>
						</div>
					</Modal>
				</div>

				<!-- Dropdown -->
				<div>
					<h3 class="text-lg font-semibold mb-4 text-neutral-800 dark:text-neutral-200">
						Dropdown
					</h3>
					<div class="max-w-xs">
						<Dropdown
							items={dropdownItems}
							bind:value={selectedTheme}
							placeholder="Select theme..."
							searchable
							on:select={(e) => console.log('Selected:', e.detail)}
						/>
					</div>
				</div>

				<!-- Tabs -->
				<div>
					<h3 class="text-lg font-semibold mb-4 text-neutral-800 dark:text-neutral-200">
						Tabs
					</h3>
					<Tabs {tabs} bind:activeTab on:change={(e) => console.log('Tab changed:', e.detail)} let:activeTab>
						{#if activeTab === 'overview'}
							<Card>
								<h4 class="text-lg font-semibold mb-2 text-neutral-900 dark:text-neutral-100">
									Overview Content
								</h4>
								<p class="text-neutral-600 dark:text-neutral-400">
									This is the overview tab content. Session analytics and key metrics
									would appear here.
								</p>
							</Card>
						{:else if activeTab === 'contributions'}
							<Card>
								<h4 class="text-lg font-semibold mb-2 text-neutral-900 dark:text-neutral-100">
									Contributions Content
								</h4>
								<p class="text-neutral-600 dark:text-neutral-400">
									Expert contributions and deliberation messages would be displayed here.
								</p>
							</Card>
						{:else if activeTab === 'synthesis'}
							<Card>
								<h4 class="text-lg font-semibold mb-2 text-neutral-900 dark:text-neutral-100">
									Synthesis Content
								</h4>
								<p class="text-neutral-600 dark:text-neutral-400">
									Final synthesis and recommendations would appear in this section.
								</p>
							</Card>
						{/if}
					</Tabs>
				</div>

				<!-- Toast Triggers -->
				<div>
					<h3 class="text-lg font-semibold mb-4 text-neutral-800 dark:text-neutral-200">
						Toasts
					</h3>
					<div class="flex gap-2">
						<Button
							size="sm"
							variant="brand"
							on:click={() => showToast('success', 'Session started successfully!')}
						>
							Show Success
						</Button>
						<Button
							size="sm"
							variant="accent"
							on:click={() =>
								showToast('error', 'Failed to connect to API. Please try again.')}
						>
							Show Error
						</Button>
						<Button
							size="sm"
							variant="secondary"
							on:click={() =>
								showToast('warning', 'Session will timeout in 5 minutes.')}
						>
							Show Warning
						</Button>
						<Button
							size="sm"
							variant="ghost"
							on:click={() =>
								showToast('info', 'New deliberation features are now available!')}
						>
							Show Info
						</Button>
					</div>
				</div>
			</div>
		</section>

		<!-- Existing Components (Alerts, Buttons, Badges, Inputs, Cards) -->
		<section>
			<h2 class="text-2xl font-bold mb-6 text-neutral-900 dark:text-neutral-100">Alerts</h2>
			<div class="space-y-4">
				{#if showSuccessAlert}
					<Alert
						variant="success"
						title="Success!"
						dismissable
						on:dismiss={() => (showSuccessAlert = false)}
					>
						Your deliberation has been created successfully.
					</Alert>
				{/if}

				{#if showWarningAlert}
					<Alert variant="warning" dismissable on:dismiss={() => (showWarningAlert = false)}>
						This action cannot be undone. Please proceed with caution.
					</Alert>
				{/if}

				<Alert variant="error" title="Error Occurred">
					Failed to connect to the API. Please try again later.
				</Alert>

				<Alert variant="info">
					New features are available! Check out the latest updates.
				</Alert>
			</div>
		</section>

		<section>
			<h2 class="text-2xl font-bold mb-6 text-neutral-900 dark:text-neutral-100">Buttons</h2>
			<div class="space-y-6">
				<div>
					<h3 class="text-lg font-semibold mb-3 text-neutral-800 dark:text-neutral-200">
						Variants
					</h3>
					<div class="flex flex-wrap gap-3">
						<Button variant="brand" on:click={handleButtonClick}>Brand</Button>
						<Button variant="accent" on:click={handleButtonClick}>Accent</Button>
						<Button variant="secondary" on:click={handleButtonClick}>Secondary</Button>
						<Button variant="ghost" on:click={handleButtonClick}>Ghost</Button>
						<Button variant="danger" on:click={handleButtonClick}>Danger</Button>
					</div>
				</div>

				<div>
					<h3 class="text-lg font-semibold mb-3 text-neutral-800 dark:text-neutral-200">
						Sizes
					</h3>
					<div class="flex flex-wrap items-center gap-3">
						<Button size="sm">Small</Button>
						<Button size="md">Medium</Button>
						<Button size="lg">Large</Button>
					</div>
				</div>

				<div>
					<h3 class="text-lg font-semibold mb-3 text-neutral-800 dark:text-neutral-200">
						States
					</h3>
					<div class="flex flex-wrap gap-3">
						<Button variant="brand" {loading} on:click={handleLoadingButton}>
							{loading ? 'Loading...' : 'Click to Load'}
						</Button>
						<Button disabled>Disabled</Button>
					</div>
				</div>
			</div>
		</section>

		<section>
			<h2 class="text-2xl font-bold mb-6 text-neutral-900 dark:text-neutral-100">Badges</h2>
			<div class="space-y-4">
				<div>
					<h3 class="text-lg font-semibold mb-3 text-neutral-800 dark:text-neutral-200">
						Variants
					</h3>
					<div class="flex flex-wrap gap-3">
						<Badge variant="success">Success</Badge>
						<Badge variant="warning">Warning</Badge>
						<Badge variant="error">Error</Badge>
						<Badge variant="info">Info</Badge>
						<Badge variant="neutral">Neutral</Badge>
					</div>
				</div>

				<div>
					<h3 class="text-lg font-semibold mb-3 text-neutral-800 dark:text-neutral-200">
						Sizes
					</h3>
					<div class="flex flex-wrap items-center gap-3">
						<Badge size="sm">Small</Badge>
						<Badge size="md">Medium</Badge>
						<Badge size="lg">Large</Badge>
					</div>
				</div>
			</div>
		</section>

		<section>
			<h2 class="text-2xl font-bold mb-6 text-neutral-900 dark:text-neutral-100">Inputs</h2>
			<div class="max-w-md space-y-4">
				<Input
					label="Text Input"
					type="text"
					placeholder="Enter text..."
					bind:value={inputValue}
				/>

				<Input
					label="Email"
					type="email"
					placeholder="your@email.com"
					bind:value={emailValue}
					error={errorMessage}
					on:blur={validateForm}
					required
				/>

				<Input
					label="Password"
					type="password"
					placeholder="Enter password"
					bind:value={passwordValue}
					helperText="Must be at least 8 characters"
					required
				/>

				<Input label="Disabled Input" type="text" value="Cannot edit this" disabled />
			</div>
		</section>

		<section>
			<h2 class="text-2xl font-bold mb-6 text-neutral-900 dark:text-neutral-100">Cards</h2>
			<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
				<Card>
					<h3 class="text-lg font-bold mb-2 text-neutral-900 dark:text-neutral-100">
						Default Card
					</h3>
					<p class="text-neutral-600 dark:text-neutral-400">
						This is a default card with standard styling.
					</p>
				</Card>

				<Card variant="bordered">
					<h3 class="text-lg font-bold mb-2 text-neutral-900 dark:text-neutral-100">
						Bordered Card
					</h3>
					<p class="text-neutral-600 dark:text-neutral-400">
						This card has a border around it.
					</p>
				</Card>

				<Card variant="elevated">
					<h3 class="text-lg font-bold mb-2 text-neutral-900 dark:text-neutral-100">
						Elevated Card
					</h3>
					<p class="text-neutral-600 dark:text-neutral-400">
						This card has a shadow for elevation.
					</p>
				</Card>
			</div>
		</section>

		<!-- Footer -->
		<footer class="mt-16 pt-8 border-t border-neutral-200 dark:border-neutral-800">
			<p class="text-center text-neutral-600 dark:text-neutral-400">
				Design System v2.0 - Board of One - Brand Color: #00C8B3 (Teal)
			</p>
		</footer>
	</div>
</div>
