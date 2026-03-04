<!--
  BLUEPRINT: form-page
  STRUCTURAL: form layout with header/content/actions, async submit guard, loading state, error banner
  ILLUSTRATIVE: prop names, label defaults, slot names (replace with your domain)
-->

<script lang="ts">
	// STRUCTURAL: Svelte 5 snippet type for projected content
	import type { Snippet } from 'svelte';
	// ILLUSTRATIVE: swap Button for your project's button component
	import Button from '$lib/ui/Button.svelte';

	// STRUCTURAL: prop interface — title/children are required; everything else optional with safe defaults
	let {
		title,
		description,
		loading = false,
		error,
		onsubmit,
		oncancel,
		submitLabel = 'Save',
		cancelLabel = 'Cancel',
		children,
		actions
	}: {
		title: string;
		description?: string;
		loading?: boolean;
		error?: string;
		onsubmit?: () => void | Promise<void>;
		oncancel?: () => void;
		submitLabel?: string;
		cancelLabel?: string;
		children: Snippet;
		actions?: Snippet;
	} = $props();

	// STRUCTURAL: separate submitting from external loading so double-submit is prevented
	// regardless of whether the parent drives loading externally
	let submitting = $state(false);

	// STRUCTURAL: async submit guard — prevents double-fire, delegates to parent, resets on settle
	async function handleSubmit(e: Event) {
		e.preventDefault();
		if (!onsubmit || submitting) return;
		submitting = true;
		try {
			await onsubmit();
		} finally {
			submitting = false;
		}
	}
</script>

<!-- STRUCTURAL: flex column + min-h-0 so content area scrolls without overflowing container -->
<form class="flex min-h-0 flex-col" onsubmit={handleSubmit} novalidate>
	<!-- STRUCTURAL: shrink-0 header — always visible -->
	<div class="shrink-0 px-4 py-4 sm:px-6">
		<h1 class="text-xl font-semibold text-[var(--text-primary)]">{title}</h1>
		{#if description}
			<p class="mt-0.5 text-sm text-[var(--text-secondary)]">{description}</p>
		{/if}
	</div>

	<!-- STRUCTURAL: error banner with role="alert" — only rendered when error string is set -->
	{#if error}
		<div
			class="mx-4 rounded-lg border border-status-error/30 bg-[var(--graft-error-50)] px-4 py-3"
			role="alert"
		>
			<p class="text-sm text-[var(--text-primary)]">{error}</p>
		</div>
	{/if}

	<!-- STRUCTURAL: flex-1 + overflow-auto pins action bar at bottom -->
	<div class="flex-1 overflow-auto px-4 py-4 sm:px-6">
		{@render children()}
	</div>

	<!-- STRUCTURAL: actions snippet replaces default cancel/submit pair when provided -->
	<div
		class="flex shrink-0 items-center justify-end gap-3 border-t border-[var(--border-subtle)] px-4 py-3 sm:px-6"
	>
		{#if actions}
			{@render actions()}
		{:else}
			{#if oncancel}
				<Button variant="outline" onclick={oncancel} disabled={submitting}>
					{cancelLabel}
				</Button>
			{/if}
			<!-- STRUCTURAL: disabled by both external loading and internal submitting -->
			<Button variant="primary" type="submit" loading={submitting} disabled={loading || submitting}>
				{submitLabel}
			</Button>
		{/if}
	</div>
</form>
