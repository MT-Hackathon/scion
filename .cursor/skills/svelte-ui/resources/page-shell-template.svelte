<!--
  Canonical Rootstock page shell.

  USE THIS as the starting point for every new route page.
  Copy verbatim, then add your content inside the inner div.

  CRITICAL CLASSES — do not omit or reorder:
    scroll-area        → themed scrollbar (defined in app.css, opt-in only)
    h-full             → fills the flex-1 main from +layout.svelte (which is overflow-hidden)
    overflow-y-auto    → page owns its scroll; layout does NOT scroll

  CONTENT CONSTRAINT:
    max-w-6xl          → standard page content width (not max-w-3xl — that's prose only)
    px-4 py-6 sm:px-6 → standard gutter + top padding

  WHEN TO USE FormPage INSTEAD:
    Use FormPage (see settings-page-template.svelte) when the page has:
    - A persistent title + description header
    - Optional sticky action bar at the bottom
    FormPage owns its own scroll internally — wrap it in h-full, not scroll-area.

  LIVE REFERENCES (canonical implementations):
    mcp/+page.svelte:346    — scroll-area page with max-w-6xl
    settings/+page.svelte   — scroll-area page with max-w-3xl (prose-heavy exception)
-->

<script lang="ts">
  import { onMount } from 'svelte';
  import { isTauri } from '$lib/api/transport';

  // Add your state here
  let loading = $state(true);

  onMount(() => {
    if (!isTauri) {
      loading = false;
      return;
    }
    // load data
    loading = false;
  });
</script>

<div class="scroll-area h-full overflow-y-auto">
  <div class="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6 sm:px-6">

    <!-- Page header -->
    <div class="space-y-1">
      <h1 class="text-2xl font-semibold text-text-primary">Page Title</h1>
      <p class="text-sm text-text-secondary">Short description of this page.</p>
    </div>

    <!-- Content sections go here -->

  </div>
</div>
