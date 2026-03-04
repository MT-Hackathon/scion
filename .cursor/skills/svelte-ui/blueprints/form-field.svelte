<!-- BLUEPRINT: form-field
     STRUCTURAL: $bindable value, generateId() for stable ARIA wiring, Snippet slots
                 for label/description/error, $derived error state, aria-invalid +
                 aria-describedby linked to error or description, role="alert" on error
     ILLUSTRATIVE: specific CSS classes, token names, input type (text shown; swap freely) -->

<script lang="ts">
	import type { Snippet } from 'svelte';
	import { generateId } from '$lib/ui/utils/id';

	let {
		value = $bindable(''),
		type = 'text',
		id,
		name,
		placeholder = '',
		disabled = false,
		required = false,
		error = '',
		label,
		description,
		class: className = '',
		...restProps
	}: {
		value?: string;
		type?: string;
		id?: string;
		name?: string;
		placeholder?: string;
		disabled?: boolean;
		required?: boolean;
		error?: string;
		label?: Snippet;
		description?: Snippet;
		class?: string;
		[key: string]: unknown;
	} = $props();

	// STRUCTURAL: stable ID derived from passed id > name > generated fallback
	// prevents ARIA linkage from breaking when neither id nor name is provided
	// fallbackId computed once outside $derived — calling generateId() inside would regenerate on each re-evaluation
	const fallbackId = `field-${generateId()}`;
	const inputId = $derived(id ?? name ?? fallbackId);
	const hasError = $derived(Boolean(error));
</script>

<!-- STRUCTURAL: wrapper owns layout; className allows external sizing without re-implementing internals -->
<div class="flex flex-col gap-1.5 {className}">
	{#if label}
		<label for={inputId} class="text-sm font-medium text-[var(--text-primary)]">
			{@render label()}
			<!-- STRUCTURAL: required indicator is presentational; aria-required on the input carries semantic weight -->
			{#if required}<span class="ml-0.5 text-[var(--status-error)]" aria-hidden="true">*</span>{/if}
		</label>
	{/if}

	{#if description}
		<!-- STRUCTURAL: id must match aria-describedby fallback when no error is active -->
		<p class="text-xs text-[var(--text-tertiary)]" id="{inputId}-description">
			{@render description()}
		</p>
	{/if}

	<!-- STRUCTURAL: aria-invalid and aria-describedby switch atomically with error state -->
	<input
		{type}
		id={inputId}
		{name}
		{placeholder}
		{disabled}
		{required}
		bind:value
		aria-invalid={hasError}
		aria-describedby={hasError
			? `${inputId}-error`
			: description
				? `${inputId}-description`
				: undefined}
		class="h-10 w-full rounded-md border bg-[var(--input-bg)] px-3 text-sm
			text-[var(--input-text)] placeholder:text-[var(--input-placeholder)]
			focus:outline-none focus:ring-2 focus:ring-[var(--input-focus-ring)] focus:ring-offset-1
			disabled:cursor-not-allowed disabled:opacity-50
			{hasError ? 'border-[var(--status-error)] focus:ring-[var(--status-error)]' : 'border-[var(--input-border)]'}"
		{...restProps}
	/>

	{#if hasError}
		<!-- STRUCTURAL: role="alert" causes screen readers to announce errors without focus movement -->
		<p class="text-xs text-[var(--status-error)]" id="{inputId}-error" role="alert">
			{error}
		</p>
	{/if}
</div>
