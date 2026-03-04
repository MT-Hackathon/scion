# Examples: Component Patterns

Concrete usage patterns for the accelerator component library in `$lib/ui/`. These are illustrative — for adaptation-ready skeletons see `blueprints/`.

---

## Button

```svelte
<script lang="ts">
  import Button from '$lib/ui/Button.svelte';

  let saving = $state(false);

  async function handleSave() {
    saving = true;
    await save();
    saving = false;
  }
</script>

<!-- Primary action with branded loading state -->
<Button variant="primary" loading={saving} onclick={handleSave}>
  Save Changes
</Button>

<!-- Destructive action -->
<Button variant="destructive" onclick={handleDelete}>
  Delete
</Button>

<!-- Ghost for secondary navigation actions -->
<Button variant="ghost" size="sm" onclick={handleCancel}>
  Cancel
</Button>
```

## Input

```svelte
<script lang="ts">
  import Input from '$lib/ui/Input.svelte';

  let name = $state('');
  let nameError = $state('');

  function validate() {
    nameError = name.trim() ? '' : 'Name is required';
    return !nameError;
  }
</script>

<Input
  bind:value={name}
  name="name"
  required
  error={nameError}
>
  {#snippet label()}Name{/snippet}
  {#snippet description()}Used as the display name throughout the app.{/snippet}
</Input>
```

## Select

```svelte
<script lang="ts">
  import Select from '$lib/ui/Select.svelte';

  let status = $state('active');
</script>

<Select bind:value={status} label="Status">
  <option value="active">Active</option>
  <option value="inactive">Inactive</option>
</Select>
```

## DataTable

The `DataTable` component accepts typed column definitions and handles keyboard navigation internally. See [`reference-component-catalog.md`](reference-component-catalog.md) for the source pointer.

```svelte
<script lang="ts">
  import DataTable from '$lib/ui/DataTable.svelte';
  import type { Column } from '$lib/ui/DataTable.types';

  const columns: Column<User>[] = [
    { key: 'name',   label: 'Name',   sortable: true },
    { key: 'email',  label: 'Email',  sortable: true },
    { key: 'status', label: 'Status', sortable: false },
  ];
</script>

<DataTable {columns} rows={users} />
```

## Dialog

```svelte
<script lang="ts">
  import Dialog from '$lib/ui/Dialog.svelte';
  import Button from '$lib/ui/Button.svelte';

  let open = $state(false);
</script>

<Button onclick={() => open = true}>Open Dialog</Button>

<Dialog bind:open title="Confirm Action">
  <p>Are you sure you want to proceed?</p>
  {#snippet footer()}
    <Button variant="ghost" onclick={() => open = false}>Cancel</Button>
    <Button variant="primary" onclick={handleConfirm}>Confirm</Button>
  {/snippet}
</Dialog>
```

## DrawerPeek

```svelte
<script lang="ts">
  import DrawerPeek from '$lib/ui/DrawerPeek.svelte';

  let selectedId = $state<string | null>(null);
</script>

<DrawerPeek open={Boolean(selectedId)} onclose={() => selectedId = null}>
  {#if selectedId}
    <DetailView id={selectedId} />
  {/if}
</DrawerPeek>
```

---

## Data Display States Pattern

Every data-backed view must render exactly one primary state. Do not show stale data beneath loading or empty overlays.

```svelte
<script lang="ts">
  let { items, loading } = $props<{ items: Item[]; loading: boolean }>();
</script>

{#if loading}
  <div class="skeleton h-32 w-full" role="status" aria-live="polite" />
{:else if items.length === 0}
  <p class="text-text-tertiary">No items found.</p>
{:else}
  {#each items as item (item.id)}
    <ItemRow {item} />
  {/each}
{/if}
```

## Token Usage

All visual properties flow through CSS variables. Never hardcode hex or per-component colors.

```svelte
<!-- Via Tailwind utility class aliases (preferred) -->
<div class="bg-bg-surface text-text-primary border-border-default">
  Content
</div>

<!-- Via var() for values with no Tailwind alias -->
<div style="box-shadow: var(--elevation-card);">
  Content
</div>
```
