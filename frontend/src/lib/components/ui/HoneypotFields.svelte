<script lang="ts">
	/**
	 * HoneypotFields - Invisible form fields for bot detection
	 *
	 * Usage:
	 *   <HoneypotFields bind:values />
	 *   // Then spread values into your form submission:
	 *   const payload = { ...formData, ...values };
	 *
	 * These fields are hidden from users but filled by bots,
	 * allowing server-side detection of automated submissions.
	 */

	interface Props {
		/** Object to bind honeypot field values for form submission */
		values?: {
			_hp_email?: string;
			_hp_url?: string;
			_hp_phone?: string;
		};
	}

	let { values = $bindable({}) }: Props = $props();

	// Initialize empty values
	let hpEmail = $state('');
	let hpUrl = $state('');
	let hpPhone = $state('');

	// Sync to bound values object
	$effect(() => {
		values = {
			_hp_email: hpEmail || undefined,
			_hp_url: hpUrl || undefined,
			_hp_phone: hpPhone || undefined,
		};
	});
</script>

<!--
  Honeypot fields - hidden from users, filled by bots
  CSS: positioned off-screen and invisible
  Accessibility: aria-hidden, no tabindex, autocomplete off
-->
<div
	class="absolute -left-[9999px] opacity-0 pointer-events-none h-0 w-0 overflow-hidden"
	aria-hidden="true"
>
	<label>
		Email address (leave blank)
		<input
			type="email"
			name="_hp_email"
			bind:value={hpEmail}
			tabindex="-1"
			autocomplete="off"
		/>
	</label>
	<label>
		Website (leave blank)
		<input type="url" name="_hp_url" bind:value={hpUrl} tabindex="-1" autocomplete="off" />
	</label>
	<label>
		Phone (leave blank)
		<input
			type="tel"
			name="_hp_phone"
			bind:value={hpPhone}
			tabindex="-1"
			autocomplete="off"
		/>
	</label>
</div>
