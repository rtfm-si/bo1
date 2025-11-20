<script lang="ts">
	import { onMount } from 'svelte';

	let emails: string[] = [];
	let newEmail = '';
	let isLoading = true;

	onMount(async () => {
		await loadWhitelist();
	});

	async function loadWhitelist() {
		try {
			const response = await fetch('/api/admin/beta-whitelist', {
				credentials: 'include'
			});
			const data = await response.json();
			emails = data.emails || [];
		} catch (err) {
			console.error(err);
		} finally {
			isLoading = false;
		}
	}

	async function addEmail() {
		if (!newEmail.trim()) return;

		try {
			await fetch('/api/admin/beta-whitelist', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				credentials: 'include',
				body: JSON.stringify({ email: newEmail.trim() })
			});

			newEmail = '';
			await loadWhitelist();
		} catch (err) {
			console.error(err);
		}
	}

	async function removeEmail(email: string) {
		if (!confirm(`Remove ${email}?`)) return;

		try {
			await fetch(`/api/admin/beta-whitelist/${email}`, {
				method: 'DELETE',
				credentials: 'include'
			});
			await loadWhitelist();
		} catch (err) {
			console.error(err);
		}
	}
</script>

<div class="p-8">
	<h1 class="text-3xl font-bold mb-6">Admin - Beta Whitelist</h1>

	<div class="mb-6 flex gap-2">
		<input
			type="email"
			bind:value={newEmail}
			placeholder="Email address"
			class="flex-1 px-4 py-2 border rounded-lg"
		/>
		<button
			on:click={addEmail}
			class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
		>
			Add Email
		</button>
	</div>

	{#if isLoading}
		<p>Loading...</p>
	{:else}
		<div class="bg-white dark:bg-slate-800 rounded-lg border p-4">
			<p class="text-sm text-slate-600 mb-4">{emails.length} whitelisted emails</p>
			<ul class="space-y-2">
				{#each emails as email}
					<li class="flex justify-between items-center p-3 bg-slate-50 dark:bg-slate-900 rounded">
						<span>{email}</span>
						<button
							on:click={() => removeEmail(email)}
							class="text-red-600 hover:text-red-700 text-sm"
						>
							Remove
						</button>
					</li>
				{/each}
			</ul>
		</div>
	{/if}
</div>
