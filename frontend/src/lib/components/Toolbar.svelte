<script lang="ts">
	import { filtersStore } from '$lib/stores/filters.svelte';
	import { fetchJSON } from '$lib/api';

	interface Community {
		id: number;
		label: string;
		size: number;
	}

	interface Props {
		nodeCount?: number;
		edgeCount?: number;
		contractCount?: number;
		recipeMode?: boolean;
		onToggleRecipe?: () => void;
	}

	let {
		nodeCount = 0,
		edgeCount = 0,
		contractCount = 0,
		recipeMode = false,
		onToggleRecipe
	}: Props = $props();

	let communities = $state<Community[]>([]);
	let loadingCommunities = $state(false);

	let fyMin = $state(filtersStore.fiscalYearMin);
	let fyMax = $state(filtersStore.fiscalYearMax);
	let minDollarsInput = $state(filtersStore.minDollars.toString());
	let selectedCommunity = $state<string>(
		filtersStore.communityFilter !== null ? String(filtersStore.communityFilter) : ''
	);

	$effect(() => {
		loadCommunities();
	});

	async function loadCommunities() {
		loadingCommunities = true;
		try {
			const data = await fetchJSON<Community[]>('/api/communities');
			communities = data;
		} catch {
			// Communities endpoint may not be available yet
			communities = [];
		} finally {
			loadingCommunities = false;
		}
	}

	function handleFyMinChange(e: Event) {
		const val = parseInt((e.target as HTMLInputElement).value);
		if (!isNaN(val)) {
			fyMin = val;
			filtersStore.setFiscalYearRange(val, fyMax);
		}
	}

	function handleFyMaxChange(e: Event) {
		const val = parseInt((e.target as HTMLInputElement).value);
		if (!isNaN(val)) {
			fyMax = val;
			filtersStore.setFiscalYearRange(fyMin, val);
		}
	}

	function handleMinDollarsChange(e: Event) {
		const val = parseFloat((e.target as HTMLInputElement).value);
		if (!isNaN(val)) {
			filtersStore.setMinDollars(val);
		} else {
			filtersStore.setMinDollars(0);
		}
	}

	function handleCommunityChange(e: Event) {
		const val = (e.target as HTMLSelectElement).value;
		selectedCommunity = val;
		if (val === '') {
			filtersStore.setCommunityFilter(null);
		} else {
			filtersStore.setCommunityFilter(parseInt(val));
		}
	}

	function handleToggleRecipe() {
		onToggleRecipe?.();
	}
</script>

<header class="toolbar">
	<div class="toolbar-left">
		<span class="toolbar-title">DOE GraphRAG</span>
		<span class="toolbar-subtitle text-muted">
			{#if contractCount > 0}
				{contractCount.toLocaleString()} contracts
			{/if}
			{#if nodeCount > 0}
				<span class="toolbar-sep">&middot;</span>
				{nodeCount.toLocaleString()} nodes
			{/if}
			{#if edgeCount > 0}
				<span class="toolbar-sep">&middot;</span>
				{edgeCount.toLocaleString()} edges
			{/if}
		</span>
	</div>

	<div class="toolbar-filters">
		<div class="filter-group">
			<label class="filter-label" for="fy-min">FY</label>
			<input
				id="fy-min"
				type="number"
				class="filter-input fy-input"
				min="2007"
				max="2026"
				value={fyMin}
				onchange={handleFyMinChange}
			/>
			<span class="filter-dash">&ndash;</span>
			<input
				id="fy-max"
				type="number"
				class="filter-input fy-input"
				min="2007"
				max="2026"
				value={fyMax}
				onchange={handleFyMaxChange}
				aria-label="Fiscal year maximum"
			/>
		</div>

		<div class="filter-group">
			<label class="filter-label" for="min-dollars">Min $</label>
			<input
				id="min-dollars"
				type="text"
				class="filter-input dollars-input"
				placeholder="0"
				value={minDollarsInput}
				onchange={handleMinDollarsChange}
			/>
		</div>

		<div class="filter-group">
			<label class="filter-label" for="community-filter">Community</label>
			<select
				id="community-filter"
				class="filter-select"
				value={selectedCommunity}
				onchange={handleCommunityChange}
			>
				<option value="">All</option>
				{#each communities as community}
					<option value={String(community.id)}>
						{community.label} ({community.size})
					</option>
				{/each}
			</select>
		</div>
	</div>

	<div class="toolbar-right">
		<button
			class="btn recipe-toggle"
			class:recipe-active={recipeMode}
			onclick={handleToggleRecipe}
		>
			<span class="recipe-icon">{recipeMode ? '&#x2713;' : '&#x26A1;'}</span>
			Deep Research
		</button>
	</div>
</header>

<style>
	.toolbar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		height: var(--toolbar-height);
		min-height: 40px;
		padding: 0 12px;
		background: var(--bg-panel);
		border-bottom: 1px solid var(--border-color);
		flex-shrink: 0;
		gap: 12px;
	}

	.toolbar-left {
		display: flex;
		align-items: center;
		gap: 10px;
		flex-shrink: 0;
	}

	.toolbar-title {
		font-weight: 700;
		font-size: 15px;
		color: var(--text-primary);
		white-space: nowrap;
	}

	.toolbar-subtitle {
		font-size: 11px;
		font-family: var(--font-mono);
		white-space: nowrap;
	}

	.toolbar-sep {
		margin: 0 2px;
	}

	.toolbar-filters {
		display: flex;
		align-items: center;
		gap: 14px;
		flex-wrap: nowrap;
		overflow-x: auto;
	}

	.filter-group {
		display: flex;
		align-items: center;
		gap: 4px;
		flex-shrink: 0;
	}

	.filter-label {
		font-size: 10px;
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		white-space: nowrap;
	}

	.filter-input {
		background: var(--bg-surface);
		border: 1px solid var(--border-accent);
		border-radius: 4px;
		padding: 2px 6px;
		color: var(--text-primary);
		font-size: 12px;
		font-family: var(--font-mono);
		outline: none;
		transition: border-color 0.15s ease;
	}

	.filter-input:focus {
		border-color: var(--accent-blue);
	}

	.fy-input {
		width: 56px;
		text-align: center;
	}

	.dollars-input {
		width: 80px;
	}

	.filter-dash {
		color: var(--text-muted);
		font-size: 12px;
	}

	.filter-select {
		background: var(--bg-surface);
		border: 1px solid var(--border-accent);
		border-radius: 4px;
		padding: 2px 6px;
		color: var(--text-primary);
		font-size: 12px;
		outline: none;
		cursor: pointer;
		max-width: 160px;
		transition: border-color 0.15s ease;
	}

	.filter-select:focus {
		border-color: var(--accent-blue);
	}

	.filter-select option {
		background: var(--bg-panel);
		color: var(--text-primary);
	}

	.toolbar-right {
		display: flex;
		align-items: center;
		flex-shrink: 0;
	}

	.recipe-toggle {
		font-size: 12px;
		padding: 4px 12px;
		border-radius: 4px;
		gap: 4px;
		white-space: nowrap;
		transition: all 0.2s ease;
	}

	.recipe-active {
		background: var(--accent-purple);
		border-color: var(--accent-purple);
		color: white;
	}

	.recipe-active:hover {
		background: var(--accent-purple-light);
		border-color: var(--accent-purple-light);
	}

	.recipe-icon {
		font-size: 13px;
	}
</style>
