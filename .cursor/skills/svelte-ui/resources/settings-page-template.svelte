<!--
  Canonical Rootstock settings page shell (FormPage variant).

  USE THIS when the page is a settings/configuration form with:
  - A title + optional description header
  - Form sections (Section, FormSection, FormField)
  - Optional sticky action bar at the bottom

  KEY DIFFERENCE FROM page-shell-template.svelte:
    FormPage owns its own scroll internally (the flex-1 overflow-y-auto inner div).
    The outer wrapper is just h-full — NOT scroll-area + overflow-y-auto.
    Do NOT double-wrap with scroll-area; FormPage already applies scroll-area internally.

  LIVE REFERENCES:
    settings/cloud-sync/+page.svelte — canonical FormPage usage
    lib/ui/frameworks/FormPage.svelte — FormPage implementation
-->

<script lang="ts">
  import { onMount } from 'svelte';
  import { isTauri } from '$lib/api/transport';
  import { toErrorMessage } from '$lib/errors';
  import { Button, FormField, FormPage, FormSection, Input, Section, toast } from '$lib/ui';

  let loading = $state(true);
  let pageError = $state<string | undefined>(undefined);
  let saving = $state(false);

  onMount(() => {
    if (!isTauri) {
      loading = false;
      pageError = 'This feature is only available in the desktop app.';
      return;
    }
    void loadData();
  });

  async function loadData() {
    loading = true;
    pageError = undefined;
    try {
      // await someIpcCall()
    } catch (err) {
      pageError = toErrorMessage(err);
    } finally {
      loading = false;
    }
  }

  async function handleSave() {
    if (saving) return;
    saving = true;
    try {
      // await saveIpcCall()
      toast.success('Saved.');
    } catch (err) {
      pageError = toErrorMessage(err);
      toast.error(pageError ?? 'Save failed.');
    } finally {
      saving = false;
    }
  }
</script>

<!-- Outer wrapper: h-full only — FormPage provides scroll internally -->
<div class="h-full">
  <FormPage
    title="Page Title"
    description="What this page configures, one sentence."
    {loading}
    error={pageError}
  >
    <div class="space-y-6">

      <FormSection
        title="Section Title"
        description="What this section covers."
      >
        <FormField label="Field Label" name="fieldName" required={true}>
          <Input
            id="fieldName"
            name="fieldName"
            bind:value={someValue}
            placeholder="placeholder"
          />
        </FormField>
      </FormSection>

      <Section title="Another Section">
        <div class="px-4 py-4">
          <!-- Section content -->
        </div>
      </Section>

    </div>

    <!-- Optional: sticky action bar (uses FormPage actions snippet) -->
    {#snippet actions()}
      <Button variant="outline" size="sm" onclick={() => {}}>Cancel</Button>
      <Button variant="primary" size="sm" onclick={handleSave} loading={saving} disabled={saving}>
        Save
      </Button>
    {/snippet}
  </FormPage>
</div>
