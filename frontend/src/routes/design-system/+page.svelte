<script lang="ts">
	/**
	 * Design System Demo Page
	 * Comprehensive showcase of all design tokens, components, animations, and interactions
	 */
	import { onMount } from 'svelte';
	import { applyTheme, type ThemeName, themes } from '$lib/design/themes';
	import { colors } from '$lib/design/tokens';
	import Button from '$lib/components/ui/Button.svelte';
	import Card from '$lib/components/ui/Card.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';
	import ProgressBar from '$lib/components/ui/ProgressBar.svelte';
	import ColorSwatch from '$lib/components/ui/ColorSwatch.svelte';
	import ShadowDemo from '$lib/components/ui/ShadowDemo.svelte';
	import BorderRadiusDemo from '$lib/components/ui/BorderRadiusDemo.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import Tooltip from '$lib/components/ui/Tooltip.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Dropdown from '$lib/components/ui/Dropdown.svelte';
	import Tabs from '$lib/components/ui/Tabs.svelte';
	import Toast from '$lib/components/ui/Toast.svelte';
	import InsightFlag from '$lib/components/ui/InsightFlag.svelte';
	import ContributionCard from '$lib/components/ui/ContributionCard.svelte';
	import type { DropdownItem, Tab, Persona } from '$lib/components/ui';

	let currentTheme: ThemeName = 'light';
	let progressValue = 65;
	let animatedProgress = 0;
	let loading = false;

	// Form values
	let inputValue = '';
	let emailValue = '';
	let passwordValue = '';
	let errorMessage = '';
	let showSuccessAlert = true;
	let showWarningAlert = true;

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

	onMount(() => {
		// Get current theme from localStorage or default to light
		const stored = localStorage.getItem('theme') as ThemeName | null;
		if (stored && Object.keys(themes).includes(stored)) {
			currentTheme = stored;
			applyTheme(currentTheme);
		}

		// Animate progress bar
		const interval = setInterval(() => {
			animatedProgress = (animatedProgress + 5) % 105;
		}, 200);

		return () => clearInterval(interval);
	});

	function switchTheme(theme: ThemeName) {
		currentTheme = theme;
		applyTheme(theme);
	}

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

	// Color scales to display
	type ColorScale = 'brand' | 'neutral';
	type ColorShade = 50 | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900 | 950;

	// Create a flat color map that works with the tokens structure
	const colorMap = {
		brand: colors.brand,
		neutral: colors.neutral,
	};

	const colorScales: Array<{ name: string; key: ColorScale; description: string }> = [
		{ name: 'Brand (Primary)', key: 'brand', description: 'Main teal from logo' },
		{ name: 'Neutral', key: 'neutral', description: 'Cool grays with teal tint' },
	];

	// Semantic colors don't have shades, they're single values
	const semanticColors = [
		{ name: 'Success', color: colors.semantic.success, description: 'Success states' },
		{ name: 'Warning', color: colors.semantic.warning, description: 'Warning states' },
		{ name: 'Error', color: colors.semantic.error, description: 'Error states' },
		{ name: 'Info', color: colors.semantic.info, description: 'Informational states' },
	];

	const coreShades: ColorShade[] = [400, 500, 600]; // Most commonly used
	const allShades: ColorShade[] = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900];
	const neutralShades: ColorShade[] = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950];

	// Typography scales
	const headingSizes = [
		{ name: '5xl', size: '3rem', usage: 'Hero headlines' },
		{ name: '4xl', size: '2.25rem', usage: 'Section headers' },
		{ name: '3xl', size: '1.875rem', usage: 'Page titles' },
		{ name: '2xl', size: '1.5rem', usage: 'Card titles' },
		{ name: 'xl', size: '1.25rem', usage: 'Subsections' },
	];

	const bodySizes = [
		{ name: 'lg', size: '1.125rem', usage: 'Large body text' },
		{ name: 'base', size: '1rem', usage: 'Standard body' },
		{ name: 'sm', size: '0.875rem', usage: 'Helper text' },
		{ name: 'xs', size: '0.75rem', usage: 'Labels, captions' },
	];

	// Helper to get color value safely
	function getColorValue(key: ColorScale, shade: ColorShade): string {
		const scale = colorMap[key];
		return (scale as any)[shade] as string;
	}
</script>

<svelte:head>
	<title>Design System - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900 py-12">
	<!-- Toast Container -->
	<div class="fixed top-4 right-4 z-[1100] space-y-2 max-w-md">
		{#each toasts as toast (toast.id)}
			<Toast
				type={toast.type}
				message={toast.message}
				ondismiss={() => removeToast(toast.id)}
			/>
		{/each}
	</div>

	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
		<!-- Header -->
		<div class="mb-12">
			<div class="flex items-center justify-between mb-6">
				<div>
					<h1 class="text-4xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">
						Design System
					</h1>
					<p class="text-lg text-neutral-600 dark:text-neutral-400">
						Complete visual reference for Board of One
					</p>
				</div>

				<!-- Theme Switcher -->
				<div class="flex gap-2">
					<Button
						variant={currentTheme === 'light' ? 'brand' : 'secondary'}
						size="sm"
						onclick={() => switchTheme('light')}
					>
						☀️ Light
					</Button>
					<Button
						variant={currentTheme === 'dark' ? 'brand' : 'secondary'}
						size="sm"
						onclick={() => switchTheme('dark')}
					>
						🌙 Dark
					</Button>
					<Button
						variant={currentTheme === 'ocean' ? 'brand' : 'secondary'}
						size="sm"
						onclick={() => switchTheme('ocean')}
					>
						🌊 Ocean
					</Button>
				</div>
			</div>

			<Alert variant="info">
				Current theme: <strong>{currentTheme}</strong>. All colors, typography, and components adapt to the selected theme.
			</Alert>
		</div>

		<!-- Core Colors (Most Used) -->
		<section class="mb-16">
			<h2 class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">
				Core Colors
			</h2>
			<p class="text-neutral-600 dark:text-neutral-400 mb-6">Most commonly used shades (400, 500, 600)</p>
			<div class="grid gap-6">
				{#each colorScales as scale}
					<Card class="p-6">
						<div class="flex items-center justify-between mb-4">
							<div>
								<h3 class="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
									{scale.name}
								</h3>
								<p class="text-sm text-neutral-500 dark:text-neutral-500">{scale.description}</p>
							</div>
							<Badge variant={scale.key === 'brand' ? 'brand' : 'neutral'}>
								{scale.key}
							</Badge>
						</div>
						<div class="grid grid-cols-3 gap-4">
							{#each coreShades as shade}
								<ColorSwatch
									color={getColorValue(scale.key, shade)}
									shade={shade}
									label={getColorValue(scale.key, shade)}
								/>
							{/each}
						</div>
					</Card>
				{/each}
			</div>
		</section>

		<!-- Semantic Colors -->
		<section class="mb-16">
			<h2 class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">
				Semantic Colors
			</h2>
			<p class="text-neutral-600 dark:text-neutral-400 mb-6">Single values for status indicators</p>
			<div class="grid md:grid-cols-4 gap-6">
				{#each semanticColors as semantic}
					<Card class="p-6">
						<div class="flex items-center justify-between mb-4">
							<div>
								<h3 class="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
									{semantic.name}
								</h3>
								<p class="text-sm text-neutral-500 dark:text-neutral-500">{semantic.description}</p>
							</div>
						</div>
						<div class="flex items-center gap-3">
							<div
								class="w-16 h-16 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700"
								style="background-color: {semantic.color}"
							></div>
							<div>
								<code class="text-xs font-mono text-neutral-600 dark:text-neutral-400 block">
									{semantic.color}
								</code>
							</div>
						</div>
					</Card>
				{/each}
			</div>
		</section>

		<!-- Full Color Palettes -->
		<section class="mb-16">
			<h2 class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
				Full Color Palettes
			</h2>
			<div class="space-y-6">
				{#each colorScales as scale}
					<details class="group">
						<summary class="cursor-pointer list-none">
							<Card class="p-4 hover:shadow-lg transition-shadow">
								<div class="flex items-center justify-between">
									<span class="font-semibold text-neutral-900 dark:text-neutral-100">
										{scale.name} - All shades (50-950)
									</span>
									<span class="text-neutral-500 dark:text-neutral-500 group-open:rotate-180 transition-transform">
										▼
									</span>
								</div>
							</Card>
						</summary>
						<div class="mt-4">
							<Card class="p-6">
								{#if scale.key === 'neutral'}
									<div class="grid grid-cols-11 gap-2">
										{#each neutralShades as shade}
											<ColorSwatch
												color={getColorValue(scale.key, shade)}
												shade={shade}
												size="sm"
											/>
										{/each}
									</div>
								{:else}
									<div class="grid grid-cols-10 gap-2">
										{#each allShades as shade}
											<ColorSwatch
												color={getColorValue(scale.key, shade)}
												shade={shade}
												size="sm"
											/>
										{/each}
									</div>
								{/if}
							</Card>
						</div>
					</details>
				{/each}
			</div>
		</section>

		<!-- Typography -->
		<section class="mb-16">
			<h2 class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">Typography</h2>

			<!-- Font Family -->
			<Card class="p-6 mb-6">
				<h3 class="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-4">
					Font Family
				</h3>
				<div class="space-y-4">
					<div>
						<p class="text-sm text-neutral-500 dark:text-neutral-500 mb-2">Sans-serif (Default)</p>
						<p class="text-2xl text-neutral-900 dark:text-neutral-100 font-sans">
							The quick brown fox jumps over the lazy dog
						</p>
						<p class="text-xs text-neutral-500 dark:text-neutral-500 mt-1 font-mono">
							-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell
						</p>
					</div>
					<div>
						<p class="text-sm text-neutral-500 dark:text-neutral-500 mb-2">Monospace (Code)</p>
						<p class="text-lg text-neutral-900 dark:text-neutral-100 font-mono">
							The quick brown fox jumps over the lazy dog
						</p>
						<p class="text-xs text-neutral-500 dark:text-neutral-500 mt-1 font-mono">
							ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas
						</p>
					</div>
				</div>
			</Card>

			<!-- Heading Sizes -->
			<Card class="p-6 mb-6">
				<h3 class="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-4">
					Heading Sizes
				</h3>
				<div class="space-y-4">
					{#each headingSizes as fontSize}
						<div class="border-b border-neutral-200 dark:border-neutral-700 pb-4 last:border-0">
							<div class="flex items-baseline gap-4 mb-2">
								<code class="text-sm font-mono text-brand-600 dark:text-brand-400 w-16">
									{fontSize.name}
								</code>
								<span class="text-xs text-neutral-500 dark:text-neutral-500">
									{fontSize.size} • {fontSize.usage}
								</span>
							</div>
							<p
								class="text-neutral-900 dark:text-neutral-100 font-bold"
								style="font-size: {fontSize.size};"
							>
								Making complex decisions simple
							</p>
						</div>
					{/each}
				</div>
			</Card>

			<!-- Body Sizes -->
			<Card class="p-6 mb-6">
				<h3 class="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-4">
					Body Text Sizes
				</h3>
				<div class="space-y-4">
					{#each bodySizes as fontSize}
						<div class="flex items-start gap-4">
							<code class="text-sm font-mono text-brand-600 dark:text-brand-400 w-16 pt-1">
								{fontSize.name}
							</code>
							<div class="flex-1">
								<p
									class="text-neutral-900 dark:text-neutral-100 mb-1"
									style="font-size: {fontSize.size};"
								>
									Board of One gives solo founders the clarity of a full advisory board in minutes, not meetings.
								</p>
								<p class="text-xs text-neutral-500 dark:text-neutral-500">
									{fontSize.size} • {fontSize.usage}
								</p>
							</div>
						</div>
					{/each}
				</div>
			</Card>

			<!-- Font Weights -->
			<Card class="p-6">
				<h3 class="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-4">
					Font Weights
				</h3>
				<div class="space-y-3">
					<p class="text-lg font-light text-neutral-900 dark:text-neutral-100">
						Light (300) - Subtle emphasis, large text only
					</p>
					<p class="text-lg font-normal text-neutral-900 dark:text-neutral-100">
						Normal (400) - Body text, paragraphs
					</p>
					<p class="text-lg font-medium text-neutral-900 dark:text-neutral-100">
						Medium (500) - Button text, emphasis
					</p>
					<p class="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
						Semibold (600) - Subheadings, labels
					</p>
					<p class="text-lg font-bold text-neutral-900 dark:text-neutral-100">
						Bold (700) - Headlines, important text
					</p>
				</div>
			</Card>
		</section>

		<!-- Progressive Disclosure Components -->
		<section class="mb-16">
			<h2 class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
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
									Static Progress (65%)
								</span>
							</div>
							<ProgressBar value={progressValue} variant="brand" showLabel />
						</div>
						<div>
							<span class="text-sm text-neutral-600 dark:text-neutral-400 block mb-2">
								Animated Progress
							</span>
							<ProgressBar value={animatedProgress} variant="brand" animated={true} showLabel={true} />
						</div>
						<div>
							<span class="text-sm text-neutral-600 dark:text-neutral-400 block mb-2">
								Indeterminate (loading)
							</span>
							<ProgressBar indeterminate variant="brand" />
						</div>
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-3">Different Variants</p>
							<div class="space-y-3">
								<ProgressBar value={75} variant="brand" size="md" />
								<ProgressBar value={60} variant="accent" size="md" />
								<ProgressBar value={90} variant="success" size="md" />
							</div>
						</div>
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-3">Different Sizes</p>
							<div class="space-y-3">
								<ProgressBar value={65} variant="brand" size="sm" />
								<ProgressBar value={65} variant="brand" size="md" />
								<ProgressBar value={65} variant="brand" size="lg" />
							</div>
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
								ondismiss={() => removeInsight(insight.id)}
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
							{#snippet actions()}
								<div class="flex gap-2">
									<Button size="sm" variant="ghost">View Analysis</Button>
									<Button size="sm" variant="ghost">Ask Follow-up</Button>
								</div>
							{/snippet}
						</ContributionCard>
					</div>
				</div>
			</div>
		</section>

		<!-- Interactive Components -->
		<section class="mb-16">
			<h2 class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
				Interactive Components
			</h2>

			<div class="space-y-8">
				<!-- Modal -->
				<div>
					<h3 class="text-lg font-semibold mb-4 text-neutral-800 dark:text-neutral-200">
						Modal
					</h3>
					<Button onclick={() => (showModal = true)}>Open Modal</Button>

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

						{#snippet footer()}
							<div class="flex justify-end gap-2">
								<Button variant="ghost" onclick={() => (showModal = false)}>
									Cancel
								</Button>
								<Button variant="brand" onclick={() => (showModal = false)}>
									Confirm
								</Button>
							</div>
						{/snippet}
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
							onselect={(value) => console.log('Selected:', value)}
						/>
					</div>
				</div>

				<!-- Tabs -->
				<div>
					<h3 class="text-lg font-semibold mb-4 text-neutral-800 dark:text-neutral-200">
						Tabs
					</h3>
					<Tabs {tabs} bind:activeTab onchange={(tabId) => console.log('Tab changed:', tabId)}>
						{#snippet children({ activeTab })}
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
						{/snippet}
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
							onclick={() => showToast('success', 'Session started successfully!')}
						>
							Show Success
						</Button>
						<Button
							size="sm"
							variant="accent"
							onclick={() =>
								showToast('error', 'Failed to connect to API. Please try again.')}
						>
							Show Error
						</Button>
						<Button
							size="sm"
							variant="secondary"
							onclick={() =>
								showToast('warning', 'Session will timeout in 5 minutes.')}
						>
							Show Warning
						</Button>
						<Button
							size="sm"
							variant="ghost"
							onclick={() =>
								showToast('info', 'New deliberation features are now available!')}
						>
							Show Info
						</Button>
					</div>
				</div>
			</div>
		</section>

		<!-- Buttons -->
		<section class="mb-16">
			<h2 class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">Buttons</h2>

			<Card class="p-6 mb-6">
				<h3 class="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-4">
					All Variants
				</h3>
				<div class="flex flex-wrap gap-4">
					<Button variant="brand" onclick={handleButtonClick}>Brand</Button>
					<Button variant="secondary" onclick={handleButtonClick}>Secondary</Button>
					<Button variant="accent" onclick={handleButtonClick}>Accent</Button>
					<Button variant="outline">Outline</Button>
					<Button variant="ghost">Ghost</Button>
					<Button variant="danger">Danger</Button>
				</div>
				<p class="text-sm text-neutral-500 dark:text-neutral-500 mt-4">
					Outline and ghost buttons have transparent backgrounds - hover to see effects
				</p>
			</Card>

			<Card class="p-6 mb-6">
				<h3 class="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-4">
					All Sizes
				</h3>
				<div class="flex flex-wrap items-center gap-4">
					<Button variant="brand" size="sm">Small Button</Button>
					<Button variant="brand" size="md">Medium Button</Button>
					<Button variant="brand" size="lg">Large Button</Button>
				</div>
			</Card>

			<Card class="p-6 mb-6">
				<h3 class="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-4">
					Loading States
				</h3>
				<div class="flex flex-wrap gap-4">
					<Button variant="brand" {loading} onclick={handleLoadingButton}>
						{loading ? 'Loading...' : 'Click to Load'}
					</Button>
					<Button variant="secondary" loading={true}>Loading</Button>
					<Button variant="outline" loading={true}>Saving</Button>
				</div>
			</Card>

			<Card class="p-6">
				<h3 class="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-4">
					Disabled States
				</h3>
				<div class="flex flex-wrap gap-4">
					<Button variant="brand" disabled={true}>Disabled Brand</Button>
					<Button variant="secondary" disabled={true}>Disabled Secondary</Button>
					<Button variant="outline" disabled={true}>Disabled Outline</Button>
					<Button variant="danger" disabled={true}>Disabled Danger</Button>
				</div>
			</Card>
		</section>

		<!-- Badges -->
		<section class="mb-16">
			<h2 class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">Badges</h2>
			<Card class="p-6 mb-6">
				<h3 class="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-4">
					Variants
				</h3>
				<div class="flex flex-wrap gap-4">
					<Badge variant="brand">Brand</Badge>
					<Badge variant="success">Success</Badge>
					<Badge variant="warning">Warning</Badge>
					<Badge variant="error">Error</Badge>
					<Badge variant="info">Info</Badge>
					<Badge variant="neutral">Neutral</Badge>
				</div>
			</Card>
			<Card class="p-6">
				<h3 class="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-4">
					Sizes
				</h3>
				<div class="flex flex-wrap items-center gap-4">
					<Badge size="sm">Small</Badge>
					<Badge size="md">Medium</Badge>
					<Badge size="lg">Large</Badge>
				</div>
			</Card>
		</section>

		<!-- Alerts -->
		<section class="mb-16">
			<h2 class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">Alerts</h2>
			<div class="space-y-4">
				{#if showSuccessAlert}
					<Alert
						variant="success"
						title="Success!"
						dismissable
						ondismiss={() => (showSuccessAlert = false)}
					>
						Your deliberation has been completed successfully. Check your results below.
					</Alert>
				{/if}

				{#if showWarningAlert}
					<Alert variant="warning" title="Warning" dismissable ondismiss={() => (showWarningAlert = false)}>
						This action will use credits from your account. Continue?
					</Alert>
				{/if}

				<Alert variant="error" title="Error">
					Failed to connect to the server. Please check your connection and try again.
				</Alert>

				<Alert variant="info" title="Information">
					Your session will expire in 15 minutes. Save your work to avoid losing progress.
				</Alert>
			</div>
		</section>

		<!-- Form Elements -->
		<section class="mb-16">
			<h2 class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
				Form Elements
			</h2>
			<Card class="p-6">
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
						onblur={validateForm}
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
			</Card>
		</section>

		<!-- Cards -->
		<section class="mb-16">
			<h2 class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">Cards</h2>
			<p class="text-neutral-600 dark:text-neutral-400 mb-6">
				Cards use the Card component with built-in variants
			</p>
			<div class="grid md:grid-cols-3 gap-6">
				<div>
					<Card variant="default">
						<h3 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
							Default Card
						</h3>
						<p class="text-neutral-600 dark:text-neutral-400 mb-4">
							Standard card with default padding and clean background.
						</p>
						<div class="flex gap-2">
							<Badge variant="neutral">Default</Badge>
						</div>
					</Card>
					<p class="text-xs text-neutral-500 dark:text-neutral-500 mt-3 font-mono">
						variant="default"
					</p>
				</div>
				<div>
					<Card variant="bordered">
						<h3 class="text-lg font-semibold text-brand-600 dark:text-brand-400 mb-2">
							Bordered Card
						</h3>
						<p class="text-neutral-600 dark:text-neutral-400 mb-4">
							Card with visible border using theme border color.
						</p>
						<div class="flex gap-2">
							<Badge variant="brand">Bordered</Badge>
						</div>
					</Card>
					<p class="text-xs text-neutral-500 dark:text-neutral-500 mt-3 font-mono">
						variant="bordered"
					</p>
				</div>
				<div>
					<Card variant="elevated">
						<h3 class="text-lg font-semibold text-brand-700 dark:text-brand-300 mb-2">
							Elevated Card
						</h3>
						<p class="text-neutral-600 dark:text-neutral-400 mb-4">
							Card with larger shadow for emphasis and depth.
						</p>
						<div class="flex gap-2">
							<Badge variant="brand">Elevated</Badge>
						</div>
					</Card>
					<p class="text-xs text-neutral-500 dark:text-neutral-500 mt-3 font-mono">
						variant="elevated"
					</p>
				</div>
			</div>

			<div class="mt-8 bg-neutral-50 dark:bg-neutral-800 p-6 rounded-lg">
				<h3 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Padding Options</h3>
				<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
					Each card shows the actual padding applied by the Card component
				</p>
				<div class="grid md:grid-cols-4 gap-4">
					<Card padding="none" variant="bordered">
						<code class="text-xs text-neutral-900 dark:text-neutral-100">padding="none"</code>
						<p class="text-xs text-neutral-500 dark:text-neutral-500 mt-1">0px</p>
					</Card>
					<Card padding="sm" variant="bordered">
						<code class="text-xs text-neutral-900 dark:text-neutral-100">padding="sm"</code>
						<p class="text-xs text-neutral-500 dark:text-neutral-500 mt-1">16px (p-4)</p>
					</Card>
					<Card padding="md" variant="bordered">
						<code class="text-xs text-neutral-900 dark:text-neutral-100">padding="md"</code>
						<p class="text-xs text-neutral-500 dark:text-neutral-500 mt-1">24px (p-6)</p>
					</Card>
					<Card padding="lg" variant="bordered">
						<code class="text-xs text-neutral-900 dark:text-neutral-100">padding="lg"</code>
						<p class="text-xs text-neutral-500 dark:text-neutral-500 mt-1">32px (p-8)</p>
					</Card>
				</div>
			</div>
		</section>

		<!-- Shadows -->
		<section class="mb-16">
			<h2 class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">Shadows</h2>
			<p class="text-neutral-600 dark:text-neutral-400 mb-6">
				Elevation levels using Tailwind shadow utilities
			</p>
			<div class="grid grid-cols-2 md:grid-cols-3 gap-8 bg-neutral-100 dark:bg-neutral-800 p-8 rounded-lg">
				<ShadowDemo shadowClass="shadow-sm" label="shadow-sm" description="Subtle" />
				<ShadowDemo shadowClass="shadow" label="shadow" description="Default" />
				<ShadowDemo shadowClass="shadow-md" label="shadow-md" description="Medium" />
				<ShadowDemo shadowClass="shadow-lg" label="shadow-lg" description="Large" />
				<ShadowDemo shadowClass="shadow-xl" label="shadow-xl" description="Extra Large" />
				<ShadowDemo shadowClass="shadow-2xl" label="shadow-2xl" description="Maximum" />
			</div>
		</section>

		<!-- Border Radius -->
		<section class="mb-16">
			<h2 class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
				Border Radius
			</h2>
			<Card class="p-8">
				<div class="flex flex-wrap justify-center gap-8">
					<BorderRadiusDemo roundedClass="rounded-sm" label="rounded-sm" pixelValue="2px" />
					<BorderRadiusDemo roundedClass="rounded" label="rounded" pixelValue="4px" />
					<BorderRadiusDemo roundedClass="rounded-md" label="rounded-md" pixelValue="6px" />
					<BorderRadiusDemo roundedClass="rounded-lg" label="rounded-lg" pixelValue="8px" />
					<BorderRadiusDemo roundedClass="rounded-xl" label="rounded-xl" pixelValue="12px" />
					<BorderRadiusDemo roundedClass="rounded-full" label="rounded-full" pixelValue="Circle" />
				</div>
			</Card>
		</section>

		<!-- Animations -->
		<section class="mb-16">
			<h2 class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
				Animations
			</h2>
			<p class="text-neutral-600 dark:text-neutral-400 mb-6">
				Built-in Tailwind animations for loading states and interactions
			</p>
			<div class="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
				<Card class="text-center">
					<div class="flex items-center justify-center h-40 mb-4 bg-neutral-50 dark:bg-neutral-800 rounded-lg">
						<div class="w-24 h-24 bg-brand-500 rounded-lg animate-pulse"></div>
					</div>
					<code class="text-sm font-mono text-brand-600 dark:text-brand-400 block mb-2">animate-pulse</code>
					<p class="text-xs text-neutral-500 dark:text-neutral-500">Loading state</p>
					<p class="text-xs text-neutral-400 dark:text-neutral-600 mt-1">Opacity fade in/out</p>
				</Card>

				<Card class="text-center">
					<div class="flex items-center justify-center h-40 mb-4 bg-neutral-50 dark:bg-neutral-800 rounded-lg">
						<div class="w-24 h-24 bg-warning-500 dark:bg-warning-400 rounded-lg animate-bounce shadow-lg"></div>
					</div>
					<code class="text-sm font-mono text-brand-600 dark:text-brand-400 block mb-2">animate-bounce</code>
					<p class="text-xs text-neutral-500 dark:text-neutral-500">Attention grabber</p>
					<p class="text-xs text-neutral-400 dark:text-neutral-600 mt-1">Vertical bounce motion</p>
				</Card>

				<Card class="text-center">
					<div class="flex items-center justify-center h-40 mb-4 bg-neutral-50 dark:bg-neutral-800 rounded-lg">
						<Spinner variant="brand" size="xl" />
					</div>
					<code class="text-sm font-mono text-brand-600 dark:text-brand-400 block mb-2">animate-spin</code>
					<p class="text-xs text-neutral-500 dark:text-neutral-500">Processing</p>
					<p class="text-xs text-neutral-400 dark:text-neutral-600 mt-1">Continuous rotation</p>
				</Card>

				<Card class="text-center">
					<div class="flex items-center justify-center h-40 mb-4 bg-neutral-50 dark:bg-neutral-800 rounded-lg">
						<div class="space-y-3 w-24">
							<div class="h-3 bg-success-500 rounded-full animate-pulse" style="animation-delay: 0ms;"></div>
							<div class="h-3 bg-success-500 rounded-full animate-pulse" style="animation-delay: 150ms;"></div>
							<div class="h-3 bg-success-500 rounded-full animate-pulse" style="animation-delay: 300ms;"></div>
							<div class="h-3 bg-success-500 rounded-full animate-pulse" style="animation-delay: 450ms;"></div>
						</div>
					</div>
					<code class="text-sm font-mono text-brand-600 dark:text-brand-400 block mb-2">staggered</code>
					<p class="text-xs text-neutral-500 dark:text-neutral-500">Sequential reveal</p>
					<p class="text-xs text-neutral-400 dark:text-neutral-600 mt-1">Delayed pulse effects</p>
				</Card>
			</div>
		</section>
	</div>
</div>
